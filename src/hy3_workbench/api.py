"""FastAPI application exposing the offline import/evaluate/review workflow."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from harbor.models.trajectories import Trajectory
from pydantic import BaseModel, Field

from hy3_workbench import __version__
from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.atif import AtifAdapter, AtifValidationError
from hy3_workbench.config import Settings, get_settings
from hy3_workbench.contracts import (
    ArtifactReference,
    EvaluationResult,
    FindingDecision,
    FirstError,
    HumanLabel,
    HumanReview,
    RunRecord,
    TaskManifest,
)
from hy3_workbench.hy3_client import Hy3Client
from hy3_workbench.metrics import AnalyticsSummary, MetricCalculator, list_slices, load_slice
from hy3_workbench.semantic_reviewer import SemanticJudge
from hy3_workbench.storage import (
    RepositoryConflictError,
    RepositoryNotFoundError,
    WorkbenchRepository,
)
from hy3_workbench.validation_records import ValidationRecords, load_validation_records
from hy3_workbench.workflow import (
    ImportRejectedError,
    JudgeUnavailableError,
    WorkbenchService,
    WorkflowError,
)


class ComponentHealth(BaseModel):
    status: Literal["ready", "not_configured", "unavailable"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ready", "degraded"]
    version: str
    components: dict[str, ComponentHealth]


class ImportRequest(BaseModel):
    bundle_dir: str = Field(min_length=1)


class ImportResponse(BaseModel):
    run_id: str
    task_id: str
    bundle_dir: str


class EvaluateRequest(BaseModel):
    force: bool = False


class EvaluateResponse(BaseModel):
    evaluated: bool
    evaluation: EvaluationResult


class RunSummary(BaseModel):
    run_id: str
    task_id: str
    repository: str
    difficulty: str
    run_status: str
    outcome_status: str | None
    process_status: str | None
    first_error: FirstError | None
    evaluation_id: str | None
    review_count: int


class RunListResponse(BaseModel):
    runs: list[RunSummary]


class TaskListResponse(BaseModel):
    tasks: list[TaskManifest]


class ArtifactTexts(BaseModel):
    """Verified artifact contents the debugger renders directly."""

    patch: str | None
    test_output: str | None
    run_log: str | None


class RunDetailResponse(BaseModel):
    run: RunRecord
    task: TaskManifest
    evaluation: EvaluationResult | None
    reviews: list[HumanReview]
    artifacts: ArtifactTexts


class EvaluationDetailResponse(BaseModel):
    evaluation: EvaluationResult
    reviews: list[HumanReview]


class InitialReviewRequest(BaseModel):
    reviewer_alias: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    initial_label: HumanLabel
    notes: str = ""


class AdjudicationRequest(BaseModel):
    reviewer_alias: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    adjudication: Literal["accept", "edit", "reject", "needs_more_evidence"]
    final_label: HumanLabel
    finding_decisions: list[FindingDecision] = Field(default_factory=list)
    notes: str = ""


class ExportResponse(BaseModel):
    files: list[str]


app = FastAPI(
    title="Hy3 Process Evaluation Workbench",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_project_root() -> Path:
    """The server always runs from the repository root."""

    return Path.cwd().resolve(strict=True)


ProjectRootDependency = Annotated[Path, Depends(get_project_root)]


def get_repository(
    settings: SettingsDependency,
    project_root: ProjectRootDependency,
) -> WorkbenchRepository:
    return WorkbenchRepository(project_root / settings.workbench_data_dir / "workbench.sqlite3")


RepositoryDependency = Annotated[WorkbenchRepository, Depends(get_repository)]


def get_judge_provider(settings: SettingsDependency):
    def provide() -> SemanticJudge:
        if not settings.hy3_configured:
            raise JudgeUnavailableError(
                "Hy3 is not configured; set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY."
            )
        return Hy3Client(settings)

    return provide


JudgeProviderDependency = Annotated[Callable[[], SemanticJudge], Depends(get_judge_provider)]


def get_service(
    settings: SettingsDependency,
    project_root: ProjectRootDependency,
    repository: RepositoryDependency,
    judge_provider: JudgeProviderDependency,
) -> WorkbenchService:
    return WorkbenchService(project_root, settings, repository, judge_provider)


ServiceDependency = Annotated[WorkbenchService, Depends(get_service)]


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, RepositoryNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, JudgeUnavailableError):
        return HTTPException(status_code=503, detail=str(error))
    if isinstance(error, ImportRejectedError):
        return HTTPException(status_code=400, detail=str(error))
    if isinstance(error, RepositoryConflictError | WorkflowError):
        return HTTPException(status_code=409, detail=str(error))
    raise error


@app.get("/api/health", response_model=HealthResponse)
def health(settings: SettingsDependency, repository: RepositoryDependency) -> HealthResponse:
    """Report configuration and storage readiness without touching the model."""

    hy3_ready = settings.hy3_configured
    database_ready = repository.is_ready()
    return HealthResponse(
        status="ready" if (hy3_ready and database_ready) else "degraded",
        version=__version__,
        components={
            "api": ComponentHealth(status="ready", detail="API process is responsive."),
            "database": ComponentHealth(
                status="ready" if database_ready else "unavailable",
                detail=f"SQLite index at {settings.workbench_data_dir}/workbench.sqlite3.",
            ),
            "hy3": ComponentHealth(
                status="ready" if hy3_ready else "not_configured",
                detail=(
                    "Hy3 endpoint, model, and API key are configured."
                    if hy3_ready
                    else "Set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY locally."
                ),
            ),
        },
    )


@app.get("/api/tasks", response_model=TaskListResponse)
def list_tasks(repository: RepositoryDependency) -> TaskListResponse:
    return TaskListResponse(tasks=repository.list_tasks())


@app.get("/api/runs", response_model=RunListResponse)
def list_runs(repository: RepositoryDependency) -> RunListResponse:
    summaries = []
    for stored in repository.list_runs():
        task = repository.get_task(stored.task_id)
        evaluation = repository.get_evaluation_for_run(stored.run.run_id)
        summaries.append(
            RunSummary(
                run_id=stored.run.run_id,
                task_id=stored.task_id,
                repository=task.repository,
                difficulty=task.difficulty.label,
                run_status=stored.run.status,
                outcome_status=evaluation.result.outcome_status if evaluation else None,
                process_status=evaluation.result.process_status if evaluation else None,
                first_error=evaluation.result.first_error if evaluation else None,
                evaluation_id=evaluation.result.evaluation_id if evaluation else None,
                review_count=(
                    len(repository.list_reviews(evaluation.result.evaluation_id))
                    if evaluation
                    else 0
                ),
            )
        )
    return RunListResponse(runs=summaries)


@app.post("/api/runs/import", response_model=ImportResponse, status_code=201)
def import_run(request: ImportRequest, service: ServiceDependency) -> ImportResponse:
    try:
        stored = service.import_bundle(request.bundle_dir)
    except (WorkflowError, RepositoryConflictError) as error:
        raise _http_error(error) from error
    return ImportResponse(
        run_id=stored.run.run_id, task_id=stored.task_id, bundle_dir=stored.bundle_dir
    )


@app.post("/api/runs/{run_id}/evaluate", response_model=EvaluateResponse)
def evaluate_run(
    run_id: str, request: EvaluateRequest, service: ServiceDependency
) -> EvaluateResponse:
    try:
        result, evaluated = service.evaluate_run(run_id, force=request.force)
    except (WorkflowError, RepositoryConflictError, RepositoryNotFoundError) as error:
        raise _http_error(error) from error
    return EvaluateResponse(evaluated=evaluated, evaluation=result)


@app.get("/api/runs/{run_id}", response_model=RunDetailResponse)
def run_detail(
    run_id: str,
    repository: RepositoryDependency,
    project_root: ProjectRootDependency,
) -> RunDetailResponse:
    try:
        stored = repository.get_run(run_id)
        task = repository.get_task(stored.task_id)
    except RepositoryNotFoundError as error:
        raise _http_error(error) from error
    evaluation = repository.get_evaluation_for_run(run_id)

    store = ArtifactStore(project_root)

    def verified_text(reference: ArtifactReference | None) -> str | None:
        if reference is None:
            return None
        try:
            store.verify(reference)
        except ArtifactIntegrityError:
            return None
        return (project_root / reference.path).read_text(encoding="utf-8")

    return RunDetailResponse(
        run=stored.run,
        task=task,
        evaluation=evaluation.result if evaluation else None,
        reviews=(repository.list_reviews(evaluation.result.evaluation_id) if evaluation else []),
        artifacts=ArtifactTexts(
            patch=verified_text(stored.run.patch),
            test_output=verified_text(stored.run.verifier.test_output),
            run_log=verified_text(stored.run.verifier.run_log),
        ),
    )


@app.get("/api/runs/{run_id}/trajectory")
def run_trajectory(
    run_id: str,
    repository: RepositoryDependency,
    project_root: ProjectRootDependency,
) -> Trajectory:
    try:
        stored = repository.get_run(run_id)
    except RepositoryNotFoundError as error:
        raise _http_error(error) from error
    try:
        return AtifAdapter().load(project_root / stored.run.trajectory.path)
    except (AtifValidationError, OSError) as error:
        raise HTTPException(
            status_code=409, detail=f"stored trajectory failed validation: {error}"
        ) from error


@app.get("/api/evaluations/{evaluation_id}", response_model=EvaluationDetailResponse)
def evaluation_detail(
    evaluation_id: str, repository: RepositoryDependency
) -> EvaluationDetailResponse:
    try:
        stored = repository.get_evaluation(evaluation_id)
    except RepositoryNotFoundError as error:
        raise _http_error(error) from error
    return EvaluationDetailResponse(
        evaluation=stored.result, reviews=repository.list_reviews(evaluation_id)
    )


@app.post(
    "/api/evaluations/{evaluation_id}/initial-review",
    response_model=HumanReview,
    status_code=201,
)
def create_initial_review(
    evaluation_id: str, request: InitialReviewRequest, service: ServiceDependency
) -> HumanReview:
    try:
        return service.record_initial_review(
            evaluation_id,
            reviewer_alias=request.reviewer_alias,
            rubric_version=request.rubric_version,
            initial_label=request.initial_label,
            notes=request.notes,
        )
    except (WorkflowError, RepositoryConflictError, RepositoryNotFoundError) as error:
        raise _http_error(error) from error


@app.post(
    "/api/evaluations/{evaluation_id}/adjudications",
    response_model=HumanReview,
    status_code=201,
)
def create_adjudication(
    evaluation_id: str, request: AdjudicationRequest, service: ServiceDependency
) -> HumanReview:
    try:
        return service.record_adjudication(
            evaluation_id,
            reviewer_alias=request.reviewer_alias,
            rubric_version=request.rubric_version,
            adjudication=request.adjudication,
            final_label=request.final_label,
            finding_decisions=request.finding_decisions,
            notes=request.notes,
        )
    except (WorkflowError, RepositoryConflictError, RepositoryNotFoundError) as error:
        raise _http_error(error) from error


class SliceListResponse(BaseModel):
    slices: list[str]


@app.get("/api/analytics/slices", response_model=SliceListResponse)
def analytics_slices(
    settings: SettingsDependency, project_root: ProjectRootDependency
) -> SliceListResponse:
    return SliceListResponse(slices=list_slices(project_root / settings.slices_dir))


@app.get("/api/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(
    repository: RepositoryDependency,
    settings: SettingsDependency,
    project_root: ProjectRootDependency,
    scope: str | None = None,
) -> AnalyticsSummary:
    slice_scope = None
    if scope is not None and scope != "all":
        try:
            slice_scope = load_slice(project_root / settings.slices_dir, scope)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
    return MetricCalculator(repository).summarize(scope=slice_scope)


@app.get("/api/regressions", response_model=ValidationRecords)
def regression_records(
    settings: SettingsDependency, project_root: ProjectRootDependency
) -> ValidationRecords:
    """Serve the committed regression cards and judge-stability records read-only."""

    return load_validation_records(
        project_root / settings.results_dir, display_base=settings.results_dir.as_posix()
    )


@app.post("/api/exports", response_model=ExportResponse)
def export_results(service: ServiceDependency) -> ExportResponse:
    return ExportResponse(files=service.export_results())
