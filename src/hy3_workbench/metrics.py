"""Provenance-aware aggregate metrics derived from persisted records only.

Every metric carries an explicit numerator, denominator, exclusion list, and
label provenance. Human ground truth is the latest adjudicated final label
when present, otherwise the blinded initial label; evaluator predictions are
never silently merged with human labels.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Literal

from hy3_workbench.contracts import (
    FirstError,
    HumanLabel,
    OutcomeStatus,
    ProcessStatus,
    StrictModel,
)
from hy3_workbench.evaluator import EVALUATOR_VERSION
from hy3_workbench.rubric import RUBRIC_VERSION, SEMANTIC_PROMPT_VERSION
from hy3_workbench.storage import WorkbenchRepository

BOOTSTRAP_SEED = 20260830
BOOTSTRAP_RESAMPLES = 2000

# Preserve the benchmark's own ordered difficulty labels; fixture labels first.
DIFFICULTY_ORDER = [
    "easy",
    "medium",
    "hard",
    "<15 min fix",
    "15 min - 1 hour",
    "1-4 hours",
    ">4 hours",
]

Provenance = Literal["human", "evaluator", "mixed", "official"]


class RunAnalysisRow(StrictModel):
    """One run's persisted facts, predictions, and human labels."""

    run_id: str
    task_id: str
    evaluation_id: str | None
    difficulty: str
    outcome_status: OutcomeStatus | None
    evaluator_process_status: ProcessStatus | None
    evaluator_first_error: FirstError | None
    correct_result_invalid_process: bool | None
    human_initial: HumanLabel | None
    human_final: HumanLabel | None
    adjudication: str | None
    exclusion_reasons: list[str]

    @property
    def human_label(self) -> HumanLabel | None:
        """Ground truth: adjudicated final label, else the blinded initial label."""

        return self.human_final or self.human_initial

    @property
    def effective_process_status(self) -> ProcessStatus | None:
        if self.human_final is not None:
            return self.human_final.process_status
        return self.evaluator_process_status

    @property
    def effective_provenance(self) -> Provenance:
        return "human" if self.human_final is not None else "evaluator"


class MetricValue(StrictModel):
    metric_id: str
    value: float | None
    numerator: int
    denominator: int
    provenance: Provenance
    definition: str
    exclusions: list[str]


class DistributionEntry(StrictModel):
    category: str
    count: int
    human_count: int
    evaluator_count: int


class DifficultyRow(StrictModel):
    label: str
    total_runs: int
    gradeable_runs: int
    resolved_runs: int
    outcome_rate: float | None
    process_gradeable_runs: int
    process_valid_runs: int
    process_valid_rate: float | None
    inconclusive_runs: int
    provenance: Provenance


class QuadrantCell(StrictModel):
    outcome_status: str
    process_status: str
    run_ids: list[str]
    provenance: Provenance


class CaseLink(StrictModel):
    run_id: str
    evaluation_id: str | None
    kind: Literal["correct_result_invalid_process", "located_first_error", "excluded"]
    note: str


class ExcludedRun(StrictModel):
    run_id: str
    reasons: list[str]


class SliceDefinition(StrictModel):
    """One frozen evaluation slice: the task ids validation metrics scope to."""

    slice_id: str
    task_ids: list[str]


_SLICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def load_slice(slices_dir: Path, slice_id: str) -> SliceDefinition:
    """Load one committed slice record and extract its selected task ids.

    Raises ``ValueError`` for unknown ids, malformed records, or ids that do
    not match the conservative slice-id pattern (which also keeps the id safe
    to use as a filename).
    """

    if not _SLICE_ID_PATTERN.fullmatch(slice_id):
        raise ValueError(f"invalid slice id: {slice_id!r}")
    path = slices_dir / f"{slice_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"unknown evaluation slice: {slice_id}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"evaluation slice {slice_id} is unreadable: {error}") from error
    if not isinstance(payload, dict) or payload.get("slice_id") != slice_id:
        raise ValueError(f"evaluation slice {slice_id} does not declare its own id")
    strata = payload.get("strata")
    if not isinstance(strata, dict) or not strata:
        raise ValueError(f"evaluation slice {slice_id} has no strata")
    task_ids: list[str] = []
    for band, stratum in strata.items():
        selected = stratum.get("selected") if isinstance(stratum, dict) else None
        if not isinstance(selected, list):
            raise ValueError(f"evaluation slice {slice_id} stratum {band!r} has no selected list")
        for item in selected:
            instance_id = item.get("instance_id") if isinstance(item, dict) else None
            if not isinstance(instance_id, str) or not instance_id:
                raise ValueError(f"evaluation slice {slice_id} stratum {band!r} is malformed")
            task_ids.append(instance_id)
    if len(task_ids) != len(set(task_ids)):
        raise ValueError(f"evaluation slice {slice_id} selects a task more than once")
    return SliceDefinition(slice_id=slice_id, task_ids=sorted(task_ids))


def list_slices(slices_dir: Path) -> list[str]:
    """Slice ids available under the committed slices directory, sorted."""

    if not slices_dir.is_dir():
        return []
    return sorted(
        path.stem for path in slices_dir.glob("*.json") if _SLICE_ID_PATTERN.fullmatch(path.stem)
    )


class AnalyticsSummary(StrictModel):
    schema_version: Literal["analytics-summary-v1"] = "analytics-summary-v1"
    run_count: int
    evaluated_count: int
    reviewed_count: int
    adjudicated_count: int
    configuration: dict[str, str | int | float]
    metrics: list[MetricValue]
    primary_error_distribution: list[DistributionEntry]
    difficulty_table: list[DifficultyRow]
    quadrant: list[QuadrantCell]
    observed_decline_interval: str
    statistically_supported_decline_interval: str
    excluded_runs: list[ExcludedRun]
    cases: list[CaseLink]


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _metric(
    metric_id: str,
    numerator: int,
    denominator: int,
    provenance: Provenance,
    definition: str,
    exclusions: list[str],
) -> MetricValue:
    return MetricValue(
        metric_id=metric_id,
        value=_rate(numerator, denominator),
        numerator=numerator,
        denominator=denominator,
        provenance=provenance,
        definition=definition,
        exclusions=exclusions,
    )


def build_rows(repository: WorkbenchRepository) -> list[RunAnalysisRow]:
    """Assemble analysis rows purely from persisted records."""

    rows: list[RunAnalysisRow] = []
    for stored in repository.list_runs():
        task = repository.get_task(stored.task_id)
        evaluation = repository.get_evaluation_for_run(stored.run.run_id)
        if evaluation is None:
            rows.append(
                RunAnalysisRow(
                    run_id=stored.run.run_id,
                    task_id=stored.task_id,
                    evaluation_id=None,
                    difficulty=task.difficulty.label,
                    outcome_status=None,
                    evaluator_process_status=None,
                    evaluator_first_error=None,
                    correct_result_invalid_process=None,
                    human_initial=None,
                    human_final=None,
                    adjudication=None,
                    exclusion_reasons=["the run has not been evaluated"],
                )
            )
            continue
        result = evaluation.result
        reviews = repository.list_reviews(result.evaluation_id)
        initial = reviews[0].initial_label if reviews else None
        adjudicated = [review for review in reviews if review.final_label is not None]
        final = adjudicated[-1].final_label if adjudicated else None
        adjudication = adjudicated[-1].adjudication if adjudicated else None
        rows.append(
            RunAnalysisRow(
                run_id=result.run_id,
                task_id=stored.task_id,
                evaluation_id=result.evaluation_id,
                difficulty=task.difficulty.label,
                outcome_status=result.outcome_status,
                evaluator_process_status=result.process_status,
                evaluator_first_error=result.first_error,
                correct_result_invalid_process=result.correct_result_invalid_process,
                human_initial=initial,
                human_final=final,
                adjudication=adjudication,
                exclusion_reasons=list(result.exclusions),
            )
        )
    return rows


def _difficulty_sort_key(label: str) -> tuple[int, str]:
    if label in DIFFICULTY_ORDER:
        return (DIFFICULTY_ORDER.index(label), label)
    return (len(DIFFICULTY_ORDER), label)


def _scalar_metrics(rows: list[RunAnalysisRow]) -> list[MetricValue]:
    metrics: list[MetricValue] = []

    gradeable = [row for row in rows if row.outcome_status in ("resolved", "unresolved")]
    outcome_excluded = [
        f"{row.run_id}: {'; '.join(row.exclusion_reasons) or 'outcome inconclusive'}"
        for row in rows
        if row.outcome_status not in ("resolved", "unresolved")
    ]
    metrics.append(
        _metric(
            "final_answer_accuracy",
            sum(1 for row in gradeable if row.outcome_status == "resolved"),
            len(gradeable),
            "official",
            "Resolved runs over gradeable (resolved plus unresolved) runs, from the official "
            "behavioral-test verifier.",
            outcome_excluded,
        )
    )

    predicted_conclusive = [
        row for row in rows if row.evaluator_process_status in ("valid", "invalid")
    ]
    metrics.append(
        _metric(
            "predicted_process_correctness_rate",
            sum(1 for row in predicted_conclusive if row.evaluator_process_status == "valid"),
            len(predicted_conclusive),
            "evaluator",
            "Evaluator-predicted valid processes over conclusive evaluator process verdicts.",
            [
                f"{row.run_id}: evaluator process status is inconclusive or missing"
                for row in rows
                if row.evaluator_process_status not in ("valid", "invalid")
            ],
        )
    )

    adjudicated = [
        row
        for row in rows
        if row.human_final is not None and row.human_final.process_status in ("valid", "invalid")
    ]
    metrics.append(
        _metric(
            "adjudicated_process_correctness_rate",
            sum(1 for row in adjudicated if row.human_final.process_status == "valid"),  # type: ignore[union-attr]
            len(adjudicated),
            "human",
            "Human-adjudicated valid processes over conclusive adjudicated final labels.",
            [
                f"{row.run_id}: no conclusive adjudicated final label"
                for row in rows
                if row not in adjudicated and row.evaluation_id is not None
            ],
        )
    )

    incorrect_human_invalid = [
        row
        for row in rows
        if row.outcome_status == "unresolved"
        and row.human_label is not None
        and row.human_label.process_status == "invalid"
    ]
    metrics.append(
        _metric(
            "incorrect_run_error_detection_accuracy",
            sum(1 for row in incorrect_human_invalid if row.evaluator_process_status == "invalid"),
            len(incorrect_human_invalid),
            "mixed",
            "On human-labeled-invalid unresolved runs, how often the evaluator also judged "
            "the process invalid.",
            [
                f"{row.run_id}: unresolved but without a human process-invalid label"
                for row in rows
                if row.outcome_status == "unresolved" and row not in incorrect_human_invalid
            ],
        )
    )

    localizable = [
        row
        for row in rows
        if row.outcome_status == "unresolved"
        and row.human_label is not None
        and row.human_label.first_error_location == "located"
        and row.human_label.first_error_step_id is not None
    ]
    located_exclusions = [
        f"{row.run_id}: no human-located first error on an unresolved run"
        for row in rows
        if row.outcome_status == "unresolved" and row not in localizable
    ]

    def evaluator_step(row: RunAnalysisRow) -> int | None:
        if row.evaluator_first_error is None:
            return None
        if row.evaluator_first_error.location != "located":
            return None
        return row.evaluator_first_error.step_id

    metrics.append(
        _metric(
            "exact_first_error_localization_accuracy",
            sum(
                1
                for row in localizable
                if evaluator_step(row) == row.human_label.first_error_step_id  # type: ignore[union-attr]
            ),
            len(localizable),
            "mixed",
            "On human-located incorrect runs, evaluator first-error step equals the human "
            "step exactly.",
            located_exclusions,
        )
    )
    metrics.append(
        _metric(
            "within_one_step_localization_accuracy",
            sum(
                1
                for row in localizable
                if evaluator_step(row) is not None
                and abs(evaluator_step(row) - row.human_label.first_error_step_id) <= 1  # type: ignore[operator,union-attr]
            ),
            len(localizable),
            "mixed",
            "On human-located incorrect runs, evaluator first-error step within one step of "
            "the human step.",
            located_exclusions,
        )
    )

    # Localization on every human-confirmed invalid run, regardless of outcome.
    # The incorrect-run metrics above stay faithful to their original
    # definition; correct-result-invalid-process runs land here instead of
    # silently vanishing from localization evidence.
    confirmed_located = [
        row
        for row in rows
        if row.human_label is not None
        and row.human_label.process_status == "invalid"
        and row.human_label.first_error_location == "located"
    ]
    confirmed_exclusions = [
        f"{row.run_id}: human confirmed invalid without a locatable step"
        for row in rows
        if row.human_label is not None
        and row.human_label.process_status == "invalid"
        and row.human_label.first_error_location != "located"
    ]
    metrics.append(
        _metric(
            "confirmed_invalid_exact_localization_accuracy",
            sum(
                1
                for row in confirmed_located
                if evaluator_step(row) == row.human_label.first_error_step_id  # type: ignore[union-attr]
            ),
            len(confirmed_located),
            "mixed",
            "On every human-labeled invalid run with a located step (any outcome), evaluator "
            "first-error step equals the human step exactly.",
            confirmed_exclusions,
        )
    )
    metrics.append(
        _metric(
            "confirmed_invalid_within_one_step_localization_accuracy",
            sum(
                1
                for row in confirmed_located
                if evaluator_step(row) is not None
                and abs(evaluator_step(row) - row.human_label.first_error_step_id) <= 1  # type: ignore[operator,union-attr]
            ),
            len(confirmed_located),
            "mixed",
            "On every human-labeled invalid run with a located step (any outcome), evaluator "
            "first-error step within one step of the human step.",
            confirmed_exclusions,
        )
    )

    flagged = [
        row
        for row in rows
        if row.outcome_status == "resolved" and row.evaluator_process_status == "invalid"
    ]
    flagged_reviewed = [row for row in flagged if row.adjudication is not None]
    flagged_unreviewed = [
        f"{row.run_id}: resolved-and-flagged run awaits adjudication"
        for row in flagged
        if row.adjudication is None
    ]
    confirmed = sum(
        1
        for row in flagged_reviewed
        if row.adjudication == "accept"
        or (
            row.adjudication == "edit"
            and row.human_final is not None
            and row.human_final.process_status == "invalid"
        )
    )
    rejected = sum(1 for row in flagged_reviewed if row.adjudication == "reject")
    metrics.append(
        _metric(
            "correct_result_confirmed_problem_rate",
            confirmed,
            len(flagged_reviewed),
            "human",
            "Adjudicated resolved-and-flagged runs confirmed (accepted or edited to invalid) "
            "as genuine process problems.",
            flagged_unreviewed,
        )
    )
    metrics.append(
        _metric(
            "correct_result_evaluator_false_positive_rate",
            rejected,
            len(flagged_reviewed),
            "human",
            "Adjudicated resolved-and-flagged runs rejected by the reviewer, so the "
            "evaluator flag was a false positive.",
            flagged_unreviewed,
        )
    )
    return metrics


def _primary_error_distribution(rows: list[RunAnalysisRow]) -> list[DistributionEntry]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        if row.effective_process_status != "invalid":
            continue
        if row.human_final is not None:
            category = row.human_final.primary_category
            source = "human"
        elif row.evaluator_first_error is not None:
            category = row.evaluator_first_error.primary_category
            source = "evaluator"
        else:
            continue
        if category is None:
            continue
        bucket = counts.setdefault(category, {"human": 0, "evaluator": 0})
        bucket[source] += 1
    return [
        DistributionEntry(
            category=category,
            count=bucket["human"] + bucket["evaluator"],
            human_count=bucket["human"],
            evaluator_count=bucket["evaluator"],
        )
        for category, bucket in sorted(counts.items())
    ]


def _difficulty_table(rows: list[RunAnalysisRow]) -> list[DifficultyRow]:
    by_label: dict[str, list[RunAnalysisRow]] = {}
    for row in rows:
        by_label.setdefault(row.difficulty, []).append(row)

    table: list[DifficultyRow] = []
    for label in sorted(by_label, key=_difficulty_sort_key):
        band = by_label[label]
        gradeable = [row for row in band if row.outcome_status in ("resolved", "unresolved")]
        resolved = sum(1 for row in gradeable if row.outcome_status == "resolved")
        process_conclusive = [
            row for row in band if row.effective_process_status in ("valid", "invalid")
        ]
        valid = sum(1 for row in process_conclusive if row.effective_process_status == "valid")
        provenance: Provenance = (
            "human"
            if all(row.human_final is not None for row in process_conclusive) and process_conclusive
            else (
                "mixed"
                if any(row.human_final is not None for row in process_conclusive)
                else "evaluator"
            )
        )
        table.append(
            DifficultyRow(
                label=label,
                total_runs=len(band),
                gradeable_runs=len(gradeable),
                resolved_runs=resolved,
                outcome_rate=_rate(resolved, len(gradeable)),
                process_gradeable_runs=len(process_conclusive),
                process_valid_runs=valid,
                process_valid_rate=_rate(valid, len(process_conclusive)),
                inconclusive_runs=len(band) - len(gradeable),
                provenance=provenance,
            )
        )
    return table


def _decline_intervals(
    table: list[DifficultyRow],
    seed: int,
    resamples: int,
) -> tuple[str, str]:
    """Observed and bootstrap-supported adjacent-band outcome-rate declines."""

    populated = [row for row in table if row.gradeable_runs > 0 and row.outcome_rate is not None]
    observed = "not_observed"
    supported = "not_established"
    rng = random.Random(seed)

    for earlier, later in zip(populated, populated[1:], strict=False):
        difference = later.outcome_rate - earlier.outcome_rate  # type: ignore[operator]
        if difference >= 0:
            continue
        if observed == "not_observed":
            observed = f"{earlier.label} -> {later.label}"
        if supported != "not_established":
            continue
        diffs: list[float] = []
        for _ in range(resamples):
            resampled_earlier = sum(
                1
                for _ in range(earlier.gradeable_runs)
                if rng.random() < earlier.outcome_rate  # type: ignore[operator]
            )
            resampled_later = sum(
                1
                for _ in range(later.gradeable_runs)
                if rng.random() < later.outcome_rate  # type: ignore[operator]
            )
            diffs.append(
                resampled_later / later.gradeable_runs - resampled_earlier / earlier.gradeable_runs
            )
        diffs.sort()
        upper = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
        if upper < 0:
            supported = f"{earlier.label} -> {later.label}"
    return observed, supported


def _quadrant(rows: list[RunAnalysisRow]) -> list[QuadrantCell]:
    cells: dict[tuple[str, str], list[RunAnalysisRow]] = {}
    for row in rows:
        outcome = row.outcome_status or "not_evaluated"
        process = row.effective_process_status or "not_evaluated"
        cells.setdefault((outcome, process), []).append(row)
    return [
        QuadrantCell(
            outcome_status=outcome,
            process_status=process,
            run_ids=sorted(item.run_id for item in members),
            provenance=(
                "human"
                if all(item.human_final is not None for item in members)
                else (
                    "mixed"
                    if any(item.human_final is not None for item in members)
                    else "evaluator"
                )
            ),
        )
        for (outcome, process), members in sorted(cells.items())
    ]


def _cases(rows: list[RunAnalysisRow]) -> list[CaseLink]:
    cases: list[CaseLink] = []
    for row in rows:
        if row.correct_result_invalid_process is True:
            cases.append(
                CaseLink(
                    run_id=row.run_id,
                    evaluation_id=row.evaluation_id,
                    kind="correct_result_invalid_process",
                    note="Resolved outcome with an invalid process.",
                )
            )
        elif (
            row.evaluator_first_error is not None
            and row.evaluator_first_error.location == "located"
        ):
            cases.append(
                CaseLink(
                    run_id=row.run_id,
                    evaluation_id=row.evaluation_id,
                    kind="located_first_error",
                    note=(
                        f"First error located at step {row.evaluator_first_error.step_id} "
                        f"({row.evaluator_first_error.primary_category})."
                    ),
                )
            )
        elif row.outcome_status not in ("resolved", "unresolved"):
            cases.append(
                CaseLink(
                    run_id=row.run_id,
                    evaluation_id=row.evaluation_id,
                    kind="excluded",
                    note="; ".join(row.exclusion_reasons) or "excluded from grading",
                )
            )
    return cases


def summarize_rows(
    rows: list[RunAnalysisRow],
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    scope: SliceDefinition | None = None,
) -> AnalyticsSummary:
    """Produce the complete provenance-aware summary from analysis rows.

    With a ``scope``, only rows whose task belongs to the frozen slice count;
    the configuration records the scope, how many runs fell outside it, and
    any slice tasks that have no run yet, so a scoped summary can never
    silently pass off partial coverage as complete.
    """

    configuration: dict[str, str | int | float] = {
        "evaluator_version": EVALUATOR_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "semantic_prompt_version": SEMANTIC_PROMPT_VERSION,
        "bootstrap_seed": seed,
        "bootstrap_resamples": resamples,
        "scope": scope.slice_id if scope is not None else "all",
    }
    if scope is not None:
        in_scope = set(scope.task_ids)
        scoped_rows = [row for row in rows if row.task_id in in_scope]
        missing = sorted(in_scope - {row.task_id for row in scoped_rows})
        configuration["scope_task_count"] = len(scope.task_ids)
        configuration["scope_out_of_scope_runs"] = len(rows) - len(scoped_rows)
        configuration["scope_tasks_without_runs"] = ", ".join(missing) if missing else "none"
        rows = scoped_rows

    table = _difficulty_table(rows)
    observed, supported = _decline_intervals(table, seed, resamples)
    return AnalyticsSummary(
        run_count=len(rows),
        evaluated_count=sum(1 for row in rows if row.evaluation_id is not None),
        reviewed_count=sum(1 for row in rows if row.human_initial is not None),
        adjudicated_count=sum(1 for row in rows if row.human_final is not None),
        configuration=configuration,
        metrics=_scalar_metrics(rows),
        primary_error_distribution=_primary_error_distribution(rows),
        difficulty_table=table,
        quadrant=_quadrant(rows),
        observed_decline_interval=observed,
        statistically_supported_decline_interval=supported,
        excluded_runs=[
            ExcludedRun(run_id=row.run_id, reasons=row.exclusion_reasons)
            for row in rows
            if row.outcome_status not in ("resolved", "unresolved")
        ],
        cases=_cases(rows),
    )


class MetricCalculator:
    """Summarize one repository's persisted evidence."""

    def __init__(self, repository: WorkbenchRepository) -> None:
        self.repository = repository

    def summarize(self, scope: SliceDefinition | None = None) -> AnalyticsSummary:
        return summarize_rows(build_rows(self.repository), scope=scope)
