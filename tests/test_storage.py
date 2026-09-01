import shutil
from pathlib import Path

import pytest
from test_semantic_reviewer import FakeJudge, invalid_response, valid_response

from hy3_workbench.config import Settings
from hy3_workbench.contracts import HumanLabel, RunRecord, TaskManifest
from hy3_workbench.storage import (
    RepositoryConflictError,
    WorkbenchRepository,
)
from hy3_workbench.workflow import (
    ImportRejectedError,
    WorkbenchService,
    WorkflowError,
    evaluation_input_digest,
)

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"
DATA_DIR = Path(".local/test-day4-storage")


def load_bundle(name: str) -> tuple[TaskManifest, RunRecord]:
    root = FIXTURE_ROOT / name
    return (
        TaskManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
        RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8")),
    )


def make_settings(**overrides) -> Settings:
    values = {
        "workbench_data_dir": DATA_DIR / "wb",
        "results_dir": DATA_DIR / "results",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_service(judge: FakeJudge, settings: Settings | None = None) -> WorkbenchService:
    settings = settings or make_settings()
    repository = WorkbenchRepository(
        PROJECT_ROOT / settings.workbench_data_dir / "workbench.sqlite3"
    )
    return WorkbenchService(PROJECT_ROOT, settings, repository, lambda: judge)


@pytest.fixture(autouse=True)
def clean_state():
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    yield
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


def initial_label() -> HumanLabel:
    return HumanLabel(
        process_status="invalid",
        first_error_location="located",
        first_error_step_id=3,
        primary_category="task_interpretation",
    )


class TestRepositoryRestartSafety:
    def test_all_records_survive_a_new_process_on_the_same_file(self) -> None:
        service = make_service(FakeJudge([invalid_response()]))
        service.import_bundle("data/fixtures/invalid-first-error")
        result, evaluated = service.evaluate_run("run-fixture-invalid-first-error")
        assert evaluated
        review = service.record_initial_review(
            result.evaluation_id, "reviewer-1", "process-rubric-v1", initial_label()
        )

        restarted = WorkbenchRepository(service.repository.db_path)

        stored_run = restarted.get_run("run-fixture-invalid-first-error")
        assert stored_run.task_id == "fixture-invalid-first-error"
        stored_evaluation = restarted.get_evaluation(result.evaluation_id)
        assert stored_evaluation.result == result
        assert restarted.list_reviews(result.evaluation_id) == [review]

    def test_duplicate_import_is_rejected_without_partial_writes(self) -> None:
        service = make_service(FakeJudge([]))
        service.import_bundle("data/fixtures/valid")

        with pytest.raises(RepositoryConflictError, match="already imported"):
            service.import_bundle("data/fixtures/valid")

        assert len(service.repository.list_runs()) == 1


class TestReviewImmutability:
    def test_review_versions_are_append_only(self) -> None:
        service = make_service(FakeJudge([invalid_response()]))
        service.import_bundle("data/fixtures/invalid-first-error")
        result, _ = service.evaluate_run("run-fixture-invalid-first-error")
        first = service.record_initial_review(
            result.evaluation_id, "reviewer-1", "process-rubric-v1", initial_label()
        )
        second = service.record_adjudication(
            result.evaluation_id,
            "reviewer-1",
            "process-rubric-v1",
            "accept",
            initial_label(),
            [],
        )

        stored = service.repository.list_reviews(result.evaluation_id)
        assert [review.review_version for review in stored] == [1, 2]
        assert stored[0] == first
        assert stored[1] == second
        assert second.initial_label == first.initial_label
        assert second.evaluator_revealed_at is not None

        with pytest.raises(RepositoryConflictError, match="next review version"):
            service.repository.append_review(first)

    def test_adjudication_requires_an_initial_review_first(self) -> None:
        service = make_service(FakeJudge([invalid_response()]))
        service.import_bundle("data/fixtures/invalid-first-error")
        result, _ = service.evaluate_run("run-fixture-invalid-first-error")

        with pytest.raises(WorkflowError, match="initial review"):
            service.record_adjudication(
                result.evaluation_id,
                "reviewer-1",
                "process-rubric-v1",
                "accept",
                initial_label(),
                [],
            )

    def test_reviewed_evaluation_cannot_be_replaced(self) -> None:
        service = make_service(FakeJudge([invalid_response(), invalid_response()]))
        service.import_bundle("data/fixtures/invalid-first-error")
        result, _ = service.evaluate_run("run-fixture-invalid-first-error")
        service.record_initial_review(
            result.evaluation_id, "reviewer-1", "process-rubric-v1", initial_label()
        )

        with pytest.raises(WorkflowError, match="human reviews"):
            service.evaluate_run("run-fixture-invalid-first-error", force=True)


class TestEvaluationIdempotency:
    def test_same_digest_returns_stored_result_without_judge_call(self) -> None:
        judge = FakeJudge([valid_response()])
        service = make_service(judge)
        service.import_bundle("data/fixtures/valid")

        first, evaluated_first = service.evaluate_run("run-fixture-valid")
        second, evaluated_second = service.evaluate_run("run-fixture-valid")

        assert evaluated_first is True
        assert evaluated_second is False
        assert second == first
        assert len(judge.calls) == 1

    def test_changed_judge_configuration_requires_force(self) -> None:
        judge = FakeJudge([valid_response(), valid_response()])
        service = make_service(judge)
        service.import_bundle("data/fixtures/valid")
        service.evaluate_run("run-fixture-valid")

        changed = make_service(judge, make_settings(semantic_context_limit_chars=90_000))

        with pytest.raises(WorkflowError, match="force=true"):
            changed.evaluate_run("run-fixture-valid")
        result, evaluated = changed.evaluate_run("run-fixture-valid", force=True)
        assert evaluated is True
        assert result.process_status == "valid"

    def test_digest_covers_judge_configuration(self) -> None:
        manifest, run = load_bundle("valid")

        base = evaluation_input_digest(manifest, run, make_settings())
        same = evaluation_input_digest(manifest, run, make_settings())
        different = evaluation_input_digest(
            manifest, run, make_settings(hy3_reasoning_effort="low")
        )

        assert base == same
        assert base != different


class TestImportRejection:
    @pytest.mark.parametrize(
        "bundle_dir",
        ["/etc", "../outside", "data/../data/fixtures/valid", "data/fixtures/missing"],
    )
    def test_invalid_paths_are_rejected(self, bundle_dir: str) -> None:
        service = make_service(FakeJudge([]))

        with pytest.raises(ImportRejectedError):
            service.import_bundle(bundle_dir)
        assert service.repository.list_runs() == []

    def test_symlink_escaping_the_project_is_rejected(self, tmp_path: Path) -> None:
        service = make_service(FakeJudge([]))
        outside = tmp_path / "outside-bundle"
        shutil.copytree(FIXTURE_ROOT / "valid", outside)
        link_parent = PROJECT_ROOT / DATA_DIR
        link_parent.mkdir(parents=True, exist_ok=True)
        link = link_parent / "escape"
        link.symlink_to(outside, target_is_directory=True)

        with pytest.raises(ImportRejectedError, match="escapes the project"):
            service.import_bundle(f"{DATA_DIR.as_posix()}/escape")

    def test_hash_mismatch_is_rejected(self, tmp_path: Path) -> None:
        from test_evidence_extractor import copy_valid_bundle

        manifest, run, root = copy_valid_bundle(tmp_path)
        bundle = root / "bundle"
        (bundle / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
        (bundle / "run.json").write_text(run.model_dump_json(), encoding="utf-8")
        (bundle / "patch.diff").write_text("tampered\n", encoding="utf-8")
        settings = make_settings()
        repository = WorkbenchRepository(
            PROJECT_ROOT / settings.workbench_data_dir / "workbench.sqlite3"
        )
        service = WorkbenchService(root, settings, repository, lambda: FakeJudge([]))

        with pytest.raises(ImportRejectedError, match="mismatch for bundle/patch.diff"):
            service.import_bundle("bundle")


class TestMultiSliceTaskReuse:
    def _seeded_repository(self):
        from hy3_workbench.contracts import ReferencePatchProvenance

        manifest, run = load_bundle("valid")
        gold_a = ReferencePatchProvenance(
            artifact=run.patch.model_copy(update={"path": "bundle/a/reference.diff"})
        )
        repository = make_service(FakeJudge([])).repository
        repository.save_imported_bundle(
            manifest.model_copy(update={"reference_patch": gold_a}), run, "bundle/a"
        )
        return repository, manifest, run, gold_a

    def test_second_import_reuses_manifest_when_only_recording_metadata_differs(
        self,
    ) -> None:
        from datetime import UTC, datetime

        from hy3_workbench.contracts import ReferencePatchProvenance, Selection

        repository, manifest, run, gold_a = self._seeded_repository()
        # Same gold-patch content (sha256) copied into a different bundle path
        # counts as recording metadata, not a substantive conflict.
        gold_b = ReferencePatchProvenance(
            artifact=run.patch.model_copy(update={"path": "bundle/b/reference.diff"})
        )
        rerun_manifest = manifest.model_copy(
            update={
                "created_at": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
                "selection": Selection(method="intervention rerun", reason="second frozen slice"),
                "reference_patch": gold_b,
            }
        )
        rerun_run = run.model_copy(
            update={"run_id": "run-fixture-valid-rerun", "slice_id": "some-intervention"}
        )

        repository.save_imported_bundle(rerun_manifest, rerun_run, "bundle/b")

        stored_manifest = repository.get_task(run.task_id)
        assert stored_manifest.selection == manifest.selection
        assert stored_manifest.reference_patch == gold_a
        assert repository.get_run("run-fixture-valid-rerun").run.slice_id == "some-intervention"

    def test_second_import_with_substantive_difference_still_conflicts(self) -> None:
        repository, manifest, run, gold_a = self._seeded_repository()
        tampered = manifest.model_copy(
            update={"problem_statement": "a different task", "reference_patch": gold_a}
        )
        rerun_run = run.model_copy(update={"run_id": "run-fixture-valid-rerun"})

        with pytest.raises(RepositoryConflictError):
            repository.save_imported_bundle(tampered, rerun_run, "bundle/b")

    def test_second_import_with_different_gold_patch_content_conflicts(self) -> None:
        from hy3_workbench.contracts import ReferencePatchProvenance

        repository, manifest, run, _ = self._seeded_repository()
        different_gold = ReferencePatchProvenance(
            artifact=run.patch.model_copy(update={"sha256": "ab" * 32})
        )
        rerun_run = run.model_copy(update={"run_id": "run-fixture-valid-rerun"})

        with pytest.raises(RepositoryConflictError):
            repository.save_imported_bundle(
                manifest.model_copy(update={"reference_patch": different_gold}),
                rerun_run,
                "bundle/b",
            )
