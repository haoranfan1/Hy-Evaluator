"""Strict, versioned contracts for evaluator inputs, outputs, and reviews."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def _project_relative_path(value: str) -> str:
    """Require one canonical POSIX path that cannot leave the project root."""

    path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise ValueError("path must be a canonical project-relative POSIX path")
    return value


ProjectRelativePath = Annotated[str, AfterValidator(_project_relative_path)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
ErrorCategory = Literal[
    "task_interpretation",
    "investigation",
    "reasoning",
    "action_execution",
    "implementation",
    "verification",
    "process_integrity",
]
OutcomeStatus = Literal["resolved", "unresolved", "inconclusive"]
ProcessStatus = Literal["valid", "invalid", "inconclusive"]


class StrictModel(BaseModel):
    """Base contract that rejects undeclared data."""

    model_config = ConfigDict(extra="forbid")


class PersistedModel(StrictModel):
    """Base for records persisted by the workbench."""

    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at")
    @classmethod
    def require_utc_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a UTC offset")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("created_at must be UTC")
        return value.astimezone(UTC)


class ArtifactReference(StrictModel):
    """Identity for one immutable file stored inside this project."""

    artifact_id: Identifier
    path: ProjectRelativePath
    sha256: Sha256
    byte_size: int = Field(ge=0)
    media_type: str | None = None


class TrajectoryReference(ArtifactReference):
    """Immutable ATIF trajectory identity."""

    schema_version: Literal["ATIF-v1.7"]


class BenchmarkIdentity(StrictModel):
    name: Literal["SWE-bench Verified"]
    revision: str = Field(min_length=1)
    source_url: HttpUrl


class BehavioralTestContract(StrictModel):
    kind: Literal["behavioral_test_contract"]
    fail_to_pass: list[str] = Field(min_length=1)
    pass_to_pass: list[str]


class CheckerIdentity(StrictModel):
    adapter: str = Field(min_length=1)
    version: str = Field(min_length=1)


class Difficulty(StrictModel):
    label: str = Field(min_length=1)
    source: str = Field(min_length=1)


class Selection(StrictModel):
    method: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReferencePatchProvenance(StrictModel):
    """Optional protected provenance, never included in initial judge input."""

    artifact: ArtifactReference
    visibility: Literal["human_adjudication_only"] = "human_adjudication_only"


class TaskManifest(PersistedModel):
    """Pinned benchmark task and its deterministic behavioral contract."""

    schema_version: Literal["task-manifest-v1"] = "task-manifest-v1"
    task_id: Identifier
    benchmark: BenchmarkIdentity
    repository: str = Field(min_length=1)
    base_commit: str = Field(min_length=7)
    problem_statement: str = Field(min_length=1)
    source_issue_url: HttpUrl
    source_pr_url: HttpUrl
    standard_answer: BehavioralTestContract
    checker: CheckerIdentity
    difficulty: Difficulty
    selection: Selection
    protected_paths: list[ProjectRelativePath] = Field(min_length=1)
    reference_patch: ReferencePatchProvenance | None = None


class ModelConfiguration(StrictModel):
    name: str = Field(min_length=1)
    endpoint_kind: str = Field(min_length=1)
    reasoning_effort: str | float | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)


class AgentConfiguration(StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    config_digest: Sha256


class HarnessConfiguration(StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class VerifierRecord(StrictModel):
    status: Literal["passed", "failed", "inconclusive", "not_run"]
    report: ArtifactReference | None = None
    test_output: ArtifactReference | None = None
    run_log: ArtifactReference | None = None
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def require_inconclusive_reason(self) -> VerifierRecord:
        if self.status == "inconclusive" and not self.exclusion_reason:
            raise ValueError("inconclusive verifier status requires exclusion_reason")
        return self


class RunRecord(PersistedModel):
    """One agent execution and the immutable files it produced."""

    schema_version: Literal["run-record-v1"] = "run-record-v1"
    run_id: Identifier
    task_id: Identifier
    status: Literal["queued", "running", "completed", "failed", "interrupted"]
    model: ModelConfiguration
    agent: AgentConfiguration
    harness: HarnessConfiguration
    dataset_adapter: str = Field(min_length=1)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trajectory: TrajectoryReference
    patch: ArtifactReference
    verifier: VerifierRecord

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_utc_run_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("run timestamps must include a UTC offset")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("run timestamps must be UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_run_times(self) -> RunRecord:
        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be earlier than started_at")
        return self


class AtifStepEvidence(StrictModel):
    kind: Literal["atif_step"]
    step_id: int = Field(ge=1)
    tool_call_id: Identifier | None = None


class PatchEvidence(StrictModel):
    kind: Literal["patch"]
    file: ProjectRelativePath
    line: int | None = Field(default=None, ge=1)


class VerifierEvidence(StrictModel):
    kind: Literal["verifier"]
    artifact_id: Identifier
    test_name: str | None = None


class TaskEvidence(StrictModel):
    kind: Literal["task"]
    field: str = Field(min_length=1)


EvidenceReference = Annotated[
    AtifStepEvidence | PatchEvidence | VerifierEvidence | TaskEvidence,
    Field(discriminator="kind"),
]


class DeterministicCheck(PersistedModel):
    """One evidence-linked fact or rule from the deterministic lane."""

    schema_version: Literal["deterministic-check-v1"] = "deterministic-check-v1"
    check_id: Identifier
    status: Literal["pass", "fail", "warning", "unknown"]
    summary: str = Field(min_length=1)
    evidence: list[EvidenceReference]
    hard_process_failure: bool = False


class Finding(PersistedModel):
    """One material or advisory process finding."""

    schema_version: Literal["finding-v1"] = "finding-v1"
    finding_id: Identifier
    source: Literal["deterministic", "semantic", "human"]
    category: ErrorCategory
    severity: Literal["info", "warning", "error", "critical"]
    summary: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    feedback: str = Field(min_length=1)
    step_id: int | None = Field(default=None, ge=1)
    tool_call_id: Identifier | None = None
    evidence: list[EvidenceReference] = Field(min_length=1)
    downstream_step_ids: list[int] = Field(default_factory=list)
    recovered: bool | Literal["unknown"] = "unknown"
    recovery_step_id: int | None = Field(default=None, ge=1)
    evidence_strength: Literal["strong", "moderate", "weak"]

    @model_validator(mode="after")
    def validate_step_relationships(self) -> Finding:
        if self.tool_call_id and self.step_id is None:
            raise ValueError("tool_call_id requires step_id")
        if self.recovered is True and self.recovery_step_id is None:
            raise ValueError("recovered findings require recovery_step_id")
        if self.recovered is not True and self.recovery_step_id is not None:
            raise ValueError("recovery_step_id is only valid when recovered is true")
        return self


class FirstError(StrictModel):
    location: Literal["located", "none", "unlocatable"]
    step_id: int | None = Field(default=None, ge=1)
    tool_call_id: Identifier | None = None
    primary_category: ErrorCategory | None = None

    @model_validator(mode="after")
    def validate_location(self) -> FirstError:
        if self.location == "located":
            if self.step_id is None or self.primary_category is None:
                raise ValueError("located first errors require step_id and primary_category")
        elif self.step_id is not None or self.tool_call_id is not None:
            raise ValueError("only located first errors can cite a step or tool call")
        if self.location == "none" and self.primary_category is not None:
            raise ValueError("a nonexistent first error cannot have a category")
        if self.tool_call_id and self.step_id is None:
            raise ValueError("tool_call_id requires step_id")
        return self


class EvaluationResult(PersistedModel):
    """Merged evaluator output with deterministic and semantic provenance."""

    schema_version: Literal["evaluation-result-v1"] = "evaluation-result-v1"
    evaluation_id: Identifier
    run_id: Identifier
    evaluator_version: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    semantic_prompt_version: str = Field(min_length=1)
    status: Literal["completed", "partial", "inconclusive", "failed"]
    outcome_status: OutcomeStatus
    process_status: ProcessStatus
    correct_result_invalid_process: bool | None
    first_error: FirstError
    deterministic_checks: list[DeterministicCheck]
    findings: list[Finding]
    exclusions: list[str]
    raw_semantic_output_path: ProjectRelativePath | None = None

    @model_validator(mode="after")
    def validate_derived_labels(self) -> EvaluationResult:
        expected: bool | None
        if self.outcome_status == "inconclusive" or self.process_status == "inconclusive":
            expected = None
        else:
            expected = self.outcome_status == "resolved" and self.process_status == "invalid"
        if self.correct_result_invalid_process is not expected:
            raise ValueError("correct_result_invalid_process does not match the two statuses")
        if self.process_status == "valid" and self.first_error.location != "none":
            raise ValueError("a valid process cannot have a first error")
        if self.process_status == "invalid" and self.first_error.location == "none":
            raise ValueError("an invalid process must have a located or unlocatable first error")
        if self.process_status == "invalid" and self.first_error.primary_category is None:
            raise ValueError("an invalid process requires a primary error category")
        if self.process_status == "valid" and any(
            finding.severity in {"error", "critical"} for finding in self.findings
        ):
            raise ValueError("a valid process cannot contain material findings")
        return self


class HumanLabel(StrictModel):
    process_status: ProcessStatus
    first_error_location: Literal["located", "none", "unlocatable"]
    first_error_step_id: int | None = Field(default=None, ge=1)
    primary_category: ErrorCategory | None = None
    notes: str = ""

    @model_validator(mode="after")
    def validate_label(self) -> HumanLabel:
        if self.first_error_location == "located":
            if self.first_error_step_id is None or self.primary_category is None:
                raise ValueError("located human labels require a step and category")
        elif self.first_error_step_id is not None:
            raise ValueError("only located human labels can cite a step")
        if self.first_error_location == "none" and self.primary_category is not None:
            raise ValueError("a nonexistent first error cannot have a category")
        if self.process_status == "valid" and self.first_error_location != "none":
            raise ValueError("a valid human label cannot have a first error")
        if self.process_status == "invalid" and self.first_error_location == "none":
            raise ValueError("an invalid human label must identify or acknowledge an error")
        return self


class FindingDecision(StrictModel):
    finding_id: Identifier
    decision: Literal["accept", "edit", "reject", "needs_more_evidence"]
    notes: str = ""


class HumanReview(PersistedModel):
    """Immutable review version; corrections are represented by a new record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["human-review-v1"] = "human-review-v1"
    review_id: Identifier
    evaluation_id: Identifier
    review_version: int = Field(ge=1)
    reviewer_alias: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    initial_label: HumanLabel
    evaluator_revealed_at: datetime | None = None
    adjudication: Literal["accept", "edit", "reject", "needs_more_evidence"] | None = None
    final_label: HumanLabel | None = None
    finding_decisions: list[FindingDecision] = Field(default_factory=list)
    notes: str = ""

    @field_validator("evaluator_revealed_at")
    @classmethod
    def require_utc_reveal_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluator_revealed_at must include a UTC offset")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("evaluator_revealed_at must be UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_review_phase(self) -> HumanReview:
        adjudicated = self.adjudication is not None
        if adjudicated and (self.evaluator_revealed_at is None or self.final_label is None):
            raise ValueError("adjudication requires reveal time and a final label")
        if not adjudicated and (
            self.evaluator_revealed_at is not None or self.final_label is not None
        ):
            raise ValueError("pre-reveal reviews cannot contain adjudication fields")
        return self


class SemanticReviewOutput(StrictModel):
    """The exact JSON object requested from the Hy3 semantic judge."""

    schema_version: Literal["semantic-review-v1"] = "semantic-review-v1"
    process_status: ProcessStatus
    first_error: FirstError
    findings: list[Finding]
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_semantic_decision(self) -> SemanticReviewOutput:
        if any(finding.source != "semantic" for finding in self.findings):
            raise ValueError("semantic output can only contain semantic findings")
        if self.process_status == "valid" and self.first_error.location != "none":
            raise ValueError("a valid semantic decision cannot have a first error")
        if self.process_status == "invalid":
            if self.first_error.location == "none":
                raise ValueError("an invalid semantic decision must identify an error")
            if not any(f.severity in {"error", "critical"} for f in self.findings):
                raise ValueError("an invalid semantic decision requires a material finding")
        return self
