"""Read-only access to the committed validation evidence under ``results/``.

Regression cards (``scripts/regression_card.py``) and judge-stability records
(``scripts/judge_stability.py``) are frozen, versioned comparison files. This
module parses them for display in the API and frontend; it never writes,
regenerates, or reorders anything on disk. Files that fail to parse are
reported explicitly instead of being silently dropped.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class ScoreCount(BaseModel):
    """One scored check family: which runs counted, over which denominator."""

    runs: list[str]
    n: int
    d: int


class HumanLabelRow(BaseModel):
    process_status: str
    first_error_step: int | None


class StoredEvaluationRow(BaseModel):
    evaluator_version: str
    status: str
    process_status: str
    first_error_step: int | None


class ProtectedCheckRow(BaseModel):
    status: str
    summary: str


class ReevaluatedRow(StoredEvaluationRow):
    exclusions: list[str] = Field(default_factory=list)
    # Cards recorded before evaluator v3 predate this field.
    semantic_condensation: str | None = None
    protected_check: ProtectedCheckRow | None = None


class RegressionRunRow(BaseModel):
    run_id: str
    task_id: str
    human: HumanLabelRow
    stored: StoredEvaluationRow
    reevaluated: ReevaluatedRow


class RegressionCard(BaseModel):
    schema_version: Literal["regression-card-v1"]
    recorded_at: str
    slice_id: str
    note: str
    stored_version: str
    reevaluated_version: str
    scores: dict[str, dict[str, ScoreCount]]
    runs: list[RegressionRunRow]


class JudgeConfigRecord(BaseModel):
    model: str
    reasoning_effort: str
    temperature: float
    top_p: float
    rubric_version: str
    semantic_prompt_version: str


class StabilitySummaryRecord(BaseModel):
    completed: int
    verdict_unanimous: bool
    verdicts: list[str]
    first_error_steps: list[int]
    step_unanimous: bool


class StabilityAttemptRecord(BaseModel):
    attempt: int
    status: str
    process_status: str | None = None
    first_error_location: str | None = None
    first_error_step: int | None = None
    primary_category: str | None = None
    finding_count: int | None = None
    repair_retries: int | None = None


class JudgeStabilityRecord(BaseModel):
    schema_version: Literal["judge-stability-v1"]
    recorded_at: str
    subject: str
    repeats: int
    judge: JudgeConfigRecord
    summary: StabilitySummaryRecord
    attempts: list[StabilityAttemptRecord]


class RegressionCardFile(BaseModel):
    file: str
    card: RegressionCard


class JudgeStabilityFile(BaseModel):
    file: str
    record: JudgeStabilityRecord


class UnreadableRecord(BaseModel):
    file: str
    reason: str


class ValidationRecords(BaseModel):
    """Every committed validation record, oldest first, plus parse failures."""

    regression_cards: list[RegressionCardFile]
    judge_stability: list[JudgeStabilityFile]
    unreadable: list[UnreadableRecord]


def _parse_error_reason(error: Exception) -> str:
    if isinstance(error, ValidationError):
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or "(root)"
        return f"schema mismatch at {location}: {first['msg']}"
    return f"not valid JSON: {error}"


def load_validation_records(results_dir: Path, *, display_base: str) -> ValidationRecords:
    """Parse every committed record under ``results_dir``.

    ``display_base`` is the repo-relative results path used in the ``file``
    fields so the UI can point at the exact committed file.
    """

    cards: list[RegressionCardFile] = []
    stability: list[JudgeStabilityFile] = []
    unreadable: list[UnreadableRecord] = []

    def scan(subdir: str, parse) -> None:
        directory = results_dir / subdir
        if not directory.is_dir():
            return
        for path in sorted(directory.glob("*.json")):
            display = f"{display_base}/{subdir}/{path.name}"
            try:
                parse(display, json.loads(path.read_text(encoding="utf-8")))
            except (ValidationError, ValueError) as error:
                unreadable.append(UnreadableRecord(file=display, reason=_parse_error_reason(error)))

    scan(
        "regression",
        lambda display, payload: cards.append(
            RegressionCardFile(file=display, card=RegressionCard.model_validate(payload))
        ),
    )
    scan(
        "judge-stability",
        lambda display, payload: stability.append(
            JudgeStabilityFile(file=display, record=JudgeStabilityRecord.model_validate(payload))
        ),
    )

    cards.sort(key=lambda entry: (entry.card.recorded_at, entry.file))
    stability.sort(key=lambda entry: (entry.record.recorded_at, entry.file))
    return ValidationRecords(
        regression_cards=cards, judge_stability=stability, unreadable=unreadable
    )
