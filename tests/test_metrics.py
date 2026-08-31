import shutil
from pathlib import Path

import pytest
from test_semantic_reviewer import FakeJudge, invalid_response, valid_response
from test_storage import initial_label, make_service

from hy3_workbench.contracts import FirstError, HumanLabel
from hy3_workbench.metrics import (
    MetricCalculator,
    RunAnalysisRow,
    list_slices,
    load_slice,
    summarize_rows,
)

PROJECT_ROOT = Path(__file__).parents[1]
DATA_DIR = Path(".local/test-day4-storage")


@pytest.fixture(autouse=True)
def clean_state():
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    yield
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


def make_row(
    run_id: str,
    task_id: str | None = None,
    difficulty: str = "easy",
    outcome: str | None = "unresolved",
    evaluator_process: str | None = "invalid",
    evaluator_step: int | None = 3,
    human_step: int | None = None,
    human_process: str | None = None,
    final: bool = False,
    adjudication: str | None = None,
    exclusions: list[str] | None = None,
) -> RunAnalysisRow:
    first_error = None
    if evaluator_process == "invalid":
        first_error = (
            FirstError(
                location="located",
                step_id=evaluator_step,
                primary_category="task_interpretation",
            )
            if evaluator_step is not None
            else FirstError(location="unlocatable", primary_category="task_interpretation")
        )
    elif evaluator_process == "valid":
        first_error = FirstError(location="none")

    label = None
    if human_process is not None:
        label = HumanLabel(
            process_status=human_process,  # type: ignore[arg-type]
            first_error_location="located"
            if human_step is not None
            else ("unlocatable" if human_process == "invalid" else "none"),
            first_error_step_id=human_step,
            primary_category=("task_interpretation" if human_process == "invalid" else None),
        )
    return RunAnalysisRow(
        run_id=run_id,
        task_id=task_id or f"task-{run_id}",
        evaluation_id=f"evaluation-{run_id}" if outcome is not None else None,
        difficulty=difficulty,
        outcome_status=outcome,  # type: ignore[arg-type]
        evaluator_process_status=evaluator_process,  # type: ignore[arg-type]
        evaluator_first_error=first_error,
        correct_result_invalid_process=(
            None
            if outcome == "inconclusive" or evaluator_process == "inconclusive"
            else outcome == "resolved" and evaluator_process == "invalid"
        ),
        human_initial=label,
        human_final=label if final else None,
        adjudication=adjudication,
        exclusion_reasons=exclusions or [],
    )


def metric(summary, metric_id):
    return next(item for item in summary.metrics if item.metric_id == metric_id)


class TestFixtureScenario:
    def test_summary_covers_every_required_metric_with_provenance(self) -> None:
        service = make_service(FakeJudge([valid_response(), invalid_response()]))
        for name in ("valid", "invalid-first-error", "inconclusive-missing-evidence"):
            service.import_bundle(f"data/fixtures/{name}")
        service.evaluate_run("run-fixture-valid")
        result, _ = service.evaluate_run("run-fixture-invalid-first-error")
        service.evaluate_run("run-fixture-inconclusive-missing-evidence")
        service.record_initial_review(
            result.evaluation_id, "reviewer-1", "process-rubric-v1", initial_label()
        )
        service.record_adjudication(
            result.evaluation_id,
            "reviewer-1",
            "process-rubric-v1",
            "accept",
            initial_label(),
            [],
        )

        summary = MetricCalculator(service.repository).summarize()

        assert summary.run_count == 3
        assert summary.evaluated_count == 3
        assert summary.reviewed_count == 1
        assert summary.adjudicated_count == 1

        accuracy = metric(summary, "final_answer_accuracy")
        assert (accuracy.numerator, accuracy.denominator) == (1, 2)
        assert accuracy.provenance == "official"
        assert any("inconclusive" in reason for reason in accuracy.exclusions)

        predicted = metric(summary, "predicted_process_correctness_rate")
        assert (predicted.numerator, predicted.denominator) == (1, 2)

        adjudicated = metric(summary, "adjudicated_process_correctness_rate")
        assert (adjudicated.numerator, adjudicated.denominator) == (0, 1)
        assert adjudicated.provenance == "human"

        detection = metric(summary, "incorrect_run_error_detection_accuracy")
        assert (detection.numerator, detection.denominator) == (1, 1)

        exact = metric(summary, "exact_first_error_localization_accuracy")
        assert (exact.numerator, exact.denominator) == (1, 1)
        within = metric(summary, "within_one_step_localization_accuracy")
        assert (within.numerator, within.denominator) == (1, 1)

        confirmed = metric(summary, "correct_result_confirmed_problem_rate")
        assert confirmed.value is None
        assert confirmed.denominator == 0

        assert len(summary.primary_error_distribution) == 1
        entry = summary.primary_error_distribution[0]
        assert entry.category == "task_interpretation"
        assert (entry.count, entry.human_count, entry.evaluator_count) == (1, 1, 0)

        assert len(summary.difficulty_table) == 1
        band = summary.difficulty_table[0]
        assert band.label == "easy"
        assert band.total_runs == 3
        assert band.gradeable_runs == 2
        assert band.resolved_runs == 1
        assert band.inconclusive_runs == 1

        assert summary.observed_decline_interval == "not_observed"
        assert summary.statistically_supported_decline_interval == "not_established"
        assert [item.run_id for item in summary.excluded_runs] == [
            "run-fixture-inconclusive-missing-evidence"
        ]
        assert any(case.kind == "located_first_error" for case in summary.cases)

    def test_blinded_initial_label_precedes_the_reveal_timestamp(self) -> None:
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

        assert first.evaluator_revealed_at is None
        assert second.evaluator_revealed_at is not None
        assert first.created_at <= second.evaluator_revealed_at
        stored = service.repository.list_reviews(result.evaluation_id)
        assert stored[0].initial_label == stored[1].initial_label


class TestSyntheticRows:
    def test_empty_repository_yields_null_values_not_zero_rates(self) -> None:
        summary = summarize_rows([])

        assert all(item.value is None and item.denominator == 0 for item in summary.metrics)
        assert summary.observed_decline_interval == "not_observed"
        assert summary.statistically_supported_decline_interval == "not_established"
        assert summary.difficulty_table == []

    def test_correct_result_flag_adjudications_split_confirmed_and_false_positive(self) -> None:
        rows = [
            make_row(
                "run-accept",
                outcome="resolved",
                human_process="invalid",
                final=True,
                adjudication="accept",
            ),
            make_row(
                "run-reject",
                outcome="resolved",
                human_process="valid",
                human_step=None,
                final=True,
                adjudication="reject",
            ),
            make_row(
                "run-edit",
                outcome="resolved",
                human_process="invalid",
                final=True,
                adjudication="edit",
            ),
            make_row("run-unreviewed", outcome="resolved"),
        ]

        summary = summarize_rows(rows)

        confirmed = metric(summary, "correct_result_confirmed_problem_rate")
        false_positive = metric(summary, "correct_result_evaluator_false_positive_rate")
        assert (confirmed.numerator, confirmed.denominator) == (2, 3)
        assert (false_positive.numerator, false_positive.denominator) == (1, 3)
        assert any("awaits adjudication" in reason for reason in confirmed.exclusions)

    def test_within_one_step_localization_is_looser_than_exact(self) -> None:
        rows = [
            make_row("run-exact", evaluator_step=3, human_step=3, human_process="invalid"),
            make_row("run-near", evaluator_step=4, human_step=3, human_process="invalid"),
            make_row("run-far", evaluator_step=9, human_step=3, human_process="invalid"),
        ]

        summary = summarize_rows(rows)

        exact = metric(summary, "exact_first_error_localization_accuracy")
        within = metric(summary, "within_one_step_localization_accuracy")
        assert (exact.numerator, exact.denominator) == (1, 3)
        assert (within.numerator, within.denominator) == (2, 3)
        assert exact.provenance == "mixed"

    def test_total_decline_between_bands_is_statistically_supported(self) -> None:
        rows = [
            *[
                make_row(f"run-easy-{i}", outcome="resolved", evaluator_process="valid")
                for i in range(4)
            ],
            *[make_row(f"run-hard-{i}", difficulty="hard") for i in range(4)],
        ]

        summary = summarize_rows(rows)

        assert summary.observed_decline_interval == "easy -> hard"
        assert summary.statistically_supported_decline_interval == "easy -> hard"

    def test_small_noisy_decline_stays_not_established(self) -> None:
        rows = [
            make_row("run-easy-1", outcome="resolved", evaluator_process="valid"),
            make_row("run-easy-2", outcome="resolved", evaluator_process="valid"),
            make_row("run-easy-3"),
            make_row(
                "run-hard-1", difficulty="hard", outcome="resolved", evaluator_process="valid"
            ),
            make_row("run-hard-2", difficulty="hard"),
            make_row("run-hard-3", difficulty="hard"),
        ]

        summary = summarize_rows(rows)

        assert summary.observed_decline_interval == "easy -> hard"
        assert summary.statistically_supported_decline_interval == "not_established"

    def test_empty_bands_never_fabricate_an_interval(self) -> None:
        rows = [
            make_row("run-a", outcome="inconclusive", evaluator_process="inconclusive"),
            make_row(
                "run-b",
                difficulty="hard",
                outcome="inconclusive",
                evaluator_process="inconclusive",
            ),
        ]

        summary = summarize_rows(rows)

        assert summary.observed_decline_interval == "not_observed"
        assert summary.statistically_supported_decline_interval == "not_established"

    def test_human_final_labels_override_evaluator_provenance(self) -> None:
        rows = [
            make_row(
                "run-human",
                outcome="unresolved",
                human_process="invalid",
                human_step=5,
                final=True,
                adjudication="edit",
            ),
            make_row("run-evaluator", outcome="unresolved"),
        ]

        summary = summarize_rows(rows)

        distribution = {entry.category: entry for entry in summary.primary_error_distribution}
        entry = distribution["task_interpretation"]
        assert entry.count == 2
        assert entry.human_count == 1
        assert entry.evaluator_count == 1
        band = summary.difficulty_table[0]
        assert band.provenance == "mixed"


class TestSliceScope:
    SLICES_DIR = PROJECT_ROOT / "data" / "evaluation-slices"

    def test_committed_day8_slice_loads_with_eight_unique_tasks(self) -> None:
        scope = load_slice(self.SLICES_DIR, "day8-slice-v1")
        assert scope.slice_id == "day8-slice-v1"
        assert len(scope.task_ids) == 8
        assert scope.task_ids == sorted(set(scope.task_ids))
        assert all(task.startswith("django__django-") for task in scope.task_ids)
        assert "django__django-15851" not in scope.task_ids
        assert "day8-slice-v1" in list_slices(self.SLICES_DIR)

    def test_load_slice_rejects_unknown_and_unsafe_ids(self) -> None:
        with pytest.raises(ValueError, match="unknown evaluation slice"):
            load_slice(self.SLICES_DIR, "no-such-slice")
        with pytest.raises(ValueError, match="invalid slice id"):
            load_slice(self.SLICES_DIR, "../day8-slice-v1")
        with pytest.raises(ValueError, match="invalid slice id"):
            load_slice(self.SLICES_DIR, "Day8")

    def test_scoped_summary_filters_rows_and_records_coverage(self, tmp_path) -> None:
        slices_dir = tmp_path / "slices"
        slices_dir.mkdir()
        (slices_dir / "mini-slice.json").write_text(
            """
            {
              "slice_id": "mini-slice",
              "strata": {
                "easy": {"selected": [{"instance_id": "task-in-1"}]},
                "hard": {"selected": [{"instance_id": "task-in-2"}]}
              }
            }
            """,
            encoding="utf-8",
        )
        scope = load_slice(slices_dir, "mini-slice")
        rows = [
            make_row(
                "run-a",
                task_id="task-in-1",
                outcome="resolved",
                evaluator_process="valid",
                evaluator_step=None,
            ),
            make_row("run-b", task_id="task-out", outcome="unresolved"),
        ]
        summary = summarize_rows(rows, scope=scope)
        assert summary.run_count == 1
        assert summary.configuration["scope"] == "mini-slice"
        assert summary.configuration["scope_task_count"] == 2
        assert summary.configuration["scope_out_of_scope_runs"] == 1
        assert summary.configuration["scope_tasks_without_runs"] == "task-in-2"
        assert all("run-b" not in cell.run_ids for cell in summary.quadrant)

    def test_unscoped_summary_declares_scope_all(self) -> None:
        summary = summarize_rows([make_row("run-a")])
        assert summary.configuration["scope"] == "all"
        assert "scope_task_count" not in summary.configuration


class TestConfirmedInvalidLocalization:
    def test_counts_human_located_invalid_runs_regardless_of_outcome(self) -> None:
        rows = [
            # Resolved but human-confirmed invalid: evaluator exact match.
            make_row(
                "run-a",
                outcome="resolved",
                evaluator_step=5,
                human_step=5,
                human_process="invalid",
                final=True,
                adjudication="edit",
            ),
            # Resolved, human step 28 vs evaluator step 16: miss.
            make_row(
                "run-b",
                outcome="resolved",
                evaluator_step=16,
                human_step=28,
                human_process="invalid",
                final=True,
                adjudication="edit",
            ),
            # Unresolved with within-one localization.
            make_row(
                "run-c",
                outcome="unresolved",
                evaluator_step=4,
                human_step=3,
                human_process="invalid",
            ),
            # Human-valid run contributes nothing.
            make_row(
                "run-d",
                outcome="resolved",
                evaluator_process="valid",
                evaluator_step=None,
                human_process="valid",
                final=True,
                adjudication="reject",
            ),
        ]
        summary = summarize_rows(rows)
        exact = metric(summary, "confirmed_invalid_exact_localization_accuracy")
        assert (exact.numerator, exact.denominator) == (1, 3)
        within = metric(summary, "confirmed_invalid_within_one_step_localization_accuracy")
        assert (within.numerator, within.denominator) == (2, 3)

    def test_unlocatable_human_labels_are_listed_as_exclusions(self) -> None:
        rows = [
            make_row(
                "run-a",
                outcome="resolved",
                evaluator_step=None,
                human_process="invalid",
                final=True,
                adjudication="edit",
            ),
        ]
        summary = summarize_rows(rows)
        exact = metric(summary, "confirmed_invalid_exact_localization_accuracy")
        assert exact.denominator == 0 and exact.value is None
        assert any("without a locatable step" in reason for reason in exact.exclusions)


class TestCaseAdjudicationAnnotation:
    def test_rejected_flag_is_not_presented_as_a_confirmed_problem(self) -> None:
        rows = [
            make_row(
                "run-fp",
                outcome="resolved",
                evaluator_step=5,
                human_process="valid",
                final=True,
                adjudication="reject",
            ),
            make_row(
                "run-tp",
                outcome="resolved",
                evaluator_step=5,
                human_step=5,
                human_process="invalid",
                final=True,
                adjudication="edit",
            ),
        ]
        summary = summarize_rows(rows)
        cases = {case.run_id: case for case in summary.cases}
        assert cases["run-fp"].adjudication == "reject"
        assert "false positive" in cases["run-fp"].note
        assert cases["run-tp"].adjudication == "edit"
        assert "human-confirmed" in cases["run-tp"].note
