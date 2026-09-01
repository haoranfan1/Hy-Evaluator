import shutil
from pathlib import Path

import pytest
from test_evidence_extractor import copy_valid_bundle
from test_semantic_reviewer import FakeJudge, invalid_response, valid_response

from hy3_workbench.config import Settings
from hy3_workbench.contracts import EvaluationResult, RunRecord, TaskManifest
from hy3_workbench.evaluator import EVALUATOR_VERSION, ProcessEvaluator
from hy3_workbench.rubric import RUBRIC_VERSION, SEMANTIC_PROMPT_VERSION

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"
DATA_DIR = Path(".local/test-workbench")


def load_bundle(name: str) -> tuple[TaskManifest, RunRecord]:
    root = FIXTURE_ROOT / name
    return (
        TaskManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
        RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8")),
    )


def make_settings() -> Settings:
    return Settings(_env_file=None, workbench_data_dir=DATA_DIR)


@pytest.fixture()
def evaluator_factory():
    def build(judge: FakeJudge, project_root: Path = PROJECT_ROOT) -> ProcessEvaluator:
        return ProcessEvaluator(project_root, judge, make_settings())

    yield build
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


class TestMergedEvaluation:
    def test_valid_fixture_merges_to_completed_valid(self, evaluator_factory) -> None:
        manifest, run = load_bundle("valid")
        judge = FakeJudge([valid_response()])

        result = evaluator_factory(judge).evaluate(manifest, run)

        assert result.status == "completed"
        assert result.outcome_status == "resolved"
        assert result.process_status == "valid"
        assert result.correct_result_invalid_process is False
        assert result.first_error.location == "none"
        assert result.findings == []
        assert result.deterministic_checks
        assert result.evaluator_version == EVALUATOR_VERSION
        assert result.rubric_version == RUBRIC_VERSION
        assert result.semantic_prompt_version == SEMANTIC_PROMPT_VERSION
        assert result.raw_semantic_output_path == (
            f"{DATA_DIR.as_posix()}/semantic/{run.run_id}/attempt-1.json"
        )

    def test_invalid_fixture_merges_to_located_first_error(self, evaluator_factory) -> None:
        manifest, run = load_bundle("invalid-first-error")
        judge = FakeJudge([invalid_response()])

        result = evaluator_factory(judge).evaluate(manifest, run)

        assert result.status == "completed"
        assert result.outcome_status == "unresolved"
        assert result.process_status == "invalid"
        assert result.correct_result_invalid_process is False
        assert result.first_error.location == "located"
        assert result.first_error.step_id == 3
        assert result.first_error.tool_call_id == "call-edit-1"
        assert result.first_error.primary_category == "task_interpretation"
        assert [finding.source for finding in result.findings] == ["semantic"]

    def test_relative_path_fixture_localizes_despite_a_contradicting_verdict(
        self, evaluator_factory
    ) -> None:
        manifest, run = load_bundle("invalid-relative-path")
        judge = FakeJudge([valid_response()])

        result = evaluator_factory(judge).evaluate(manifest, run)

        assert result.status == "partial"
        assert result.outcome_status == "resolved"
        assert result.process_status == "invalid"
        assert result.correct_result_invalid_process is True
        assert result.first_error.location == "located"
        assert result.first_error.step_id == 4
        assert result.first_error.tool_call_id == "call-edit-1"
        assert result.first_error.primary_category == "process_integrity"
        assert [finding.source for finding in result.findings] == ["deterministic"]
        assert any("contradicts" in reason for reason in result.exclusions)

    def test_inconclusive_fixture_never_calls_the_judge(self, evaluator_factory) -> None:
        manifest, run = load_bundle("inconclusive-missing-evidence")
        judge = FakeJudge([])

        result = evaluator_factory(judge).evaluate(manifest, run)

        assert result.status == "inconclusive"
        assert result.outcome_status == "inconclusive"
        assert result.process_status == "inconclusive"
        assert result.correct_result_invalid_process is None
        assert result.first_error.location == "none"
        assert result.raw_semantic_output_path is None
        assert judge.calls == []
        assert result.exclusions

    def test_semantic_failure_yields_partial_result_without_verdict(
        self, evaluator_factory
    ) -> None:
        manifest, run = load_bundle("invalid-first-error")
        bad = invalid_response(step_id=99, tool_call_id=None)
        judge = FakeJudge([bad, bad])

        result = evaluator_factory(judge).evaluate(manifest, run)

        assert result.status == "partial"
        assert result.outcome_status == "unresolved"
        assert result.process_status == "inconclusive"
        assert result.correct_result_invalid_process is None
        assert result.findings == []
        assert result.deterministic_checks
        assert any("semantic lane unavailable" in reason for reason in result.exclusions)
        assert result.raw_semantic_output_path == (
            f"{DATA_DIR.as_posix()}/semantic/{run.run_id}/attempt-2.json"
        )

    def test_hard_failure_overrides_a_contradicting_valid_verdict(
        self, evaluator_factory, tmp_path: Path
    ) -> None:
        def access_protected_path(data: dict) -> None:
            data["steps"][1]["tool_calls"][0]["arguments"]["command"] = (
                "cat grader_tests/answers.json"
            )

        manifest, run, root = copy_valid_bundle(tmp_path, mutate_trajectory=access_protected_path)
        judge = FakeJudge([valid_response()])

        result = evaluator_factory(judge, project_root=root).evaluate(manifest, run)

        assert result.status == "partial"
        assert result.outcome_status == "resolved"
        assert result.process_status == "invalid"
        assert result.correct_result_invalid_process is True
        assert result.first_error.location == "located"
        assert result.first_error.step_id == 2
        assert result.first_error.primary_category == "process_integrity"
        assert [finding.source for finding in result.findings] == ["deterministic"]
        assert result.findings[0].severity == "critical"
        assert any("contradicts" in reason for reason in result.exclusions)

    def test_condensed_semantic_review_is_marked_in_the_result(self, evaluator_factory) -> None:
        from hy3_workbench.contracts import SemanticReviewOutput
        from hy3_workbench.semantic_reviewer import SemanticReviewResult

        manifest, run = load_bundle("valid")
        evaluator = evaluator_factory(FakeJudge([]))
        condensation = "semantic-condense-v1: compact serialization"

        class CondensingReviewer:
            def review(self, *args, **kwargs):
                return SemanticReviewResult(
                    status="completed",
                    output=SemanticReviewOutput.model_validate_json(valid_response()),
                    attempts=1,
                    condensation=condensation,
                )

        evaluator.reviewer = CondensingReviewer()

        result = evaluator.evaluate(manifest, run)

        assert result.status == "completed"
        assert result.process_status == "valid"
        assert result.semantic_condensation == condensation
        restored = EvaluationResult.model_validate_json(result.model_dump_json())
        assert restored.semantic_condensation == condensation

    def test_merged_results_survive_contract_round_trip(self, evaluator_factory) -> None:
        manifest, run = load_bundle("invalid-first-error")
        judge = FakeJudge([invalid_response()])

        result = evaluator_factory(judge).evaluate(manifest, run)

        restored = EvaluationResult.model_validate_json(result.model_dump_json())
        assert restored == result
