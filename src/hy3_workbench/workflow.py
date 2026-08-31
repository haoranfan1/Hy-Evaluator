"""Offline workbench workflow: import, evaluate, review, and export."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.config import Settings
from hy3_workbench.contracts import (
    EvaluationResult,
    FindingDecision,
    HumanLabel,
    HumanReview,
    ProjectRelativePath,
    RunRecord,
    TaskManifest,
    utc_now,
)
from hy3_workbench.evaluator import EVALUATOR_VERSION, ProcessEvaluator
from hy3_workbench.metrics import MetricCalculator
from hy3_workbench.rubric import RUBRIC_VERSION, SEMANTIC_PROMPT_VERSION
from hy3_workbench.semantic_reviewer import SemanticJudge
from hy3_workbench.storage import StoredRun, WorkbenchRepository

_relative_path_adapter = TypeAdapter(ProjectRelativePath)


class WorkflowError(ValueError):
    """A request was well-formed but cannot be satisfied as asked."""


class ImportRejectedError(WorkflowError):
    """The bundle path, layout, contracts, or artifact identity are invalid."""


class JudgeUnavailableError(WorkflowError):
    """No semantic judge is configured for this process."""


def evaluation_input_digest(manifest: TaskManifest, run: RunRecord, settings: Settings) -> str:
    """Digest every input and configuration that determines an evaluation."""

    payload = {
        "manifest": manifest.model_dump(mode="json"),
        "run": run.model_dump(mode="json"),
        "evaluator_version": EVALUATOR_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "semantic_prompt_version": SEMANTIC_PROMPT_VERSION,
        "judge": {
            "model": settings.hy3_model,
            "reasoning_effort": settings.hy3_reasoning_effort,
            "temperature": settings.hy3_temperature,
            "top_p": settings.hy3_top_p,
            "context_limit_chars": settings.semantic_context_limit_chars,
        },
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class WorkbenchService:
    """Coordinate persistence, the evaluator, and file exports for the API."""

    def __init__(
        self,
        project_root: Path,
        settings: Settings,
        repository: WorkbenchRepository,
        judge_provider: Callable[[], SemanticJudge],
    ) -> None:
        self.project_root = project_root.resolve(strict=True)
        self.settings = settings
        self.repository = repository
        self.judge_provider = judge_provider
        self.artifacts = ArtifactStore(self.project_root)

    # Import ------------------------------------------------------------------

    def import_bundle(self, bundle_dir: str) -> StoredRun:
        try:
            canonical = _relative_path_adapter.validate_python(bundle_dir)
        except ValidationError as error:
            raise ImportRejectedError(f"bundle_dir is not project-relative: {error}") from error

        candidate = self.project_root / canonical
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise ImportRejectedError(f"bundle directory does not exist: {canonical}") from error
        if not resolved.is_relative_to(self.project_root):
            raise ImportRejectedError(f"bundle directory escapes the project: {canonical}")
        if not resolved.is_dir():
            raise ImportRejectedError(f"bundle path is not a directory: {canonical}")

        manifest_path = resolved / "manifest.json"
        run_path = resolved / "run.json"
        if not manifest_path.is_file() or not run_path.is_file():
            raise ImportRejectedError("a bundle directory must contain manifest.json and run.json")
        try:
            manifest = TaskManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            run = RunRecord.model_validate_json(run_path.read_text(encoding="utf-8"))
        except (ValidationError, ValueError) as error:
            raise ImportRejectedError(f"bundle contracts are invalid: {error}") from error

        if run.task_id != manifest.task_id:
            raise ImportRejectedError("run task_id does not match the bundle manifest")
        for reference in (
            run.trajectory,
            run.patch,
            run.verifier.report,
            run.verifier.test_output,
            run.verifier.run_log,
        ):
            if reference is None:
                continue
            try:
                self.artifacts.verify(reference)
            except ArtifactIntegrityError as error:
                raise ImportRejectedError(f"artifact identity failed: {error}") from error

        self.repository.save_imported_bundle(manifest, run, canonical)
        return StoredRun(run, manifest.task_id, canonical)

    # Evaluate ----------------------------------------------------------------

    def evaluate_run(self, run_id: str, force: bool = False) -> tuple[EvaluationResult, bool]:
        """Return the stored or newly produced evaluation plus whether it ran."""

        stored_run = self.repository.get_run(run_id)
        manifest = self.repository.get_task(stored_run.task_id)
        digest = evaluation_input_digest(manifest, stored_run.run, self.settings)

        stored = self.repository.get_evaluation_for_run(run_id)
        if stored is not None and not force:
            if stored.input_digest == digest:
                return stored.result, False
            raise WorkflowError(
                "the stored evaluation used a different input or judge configuration; "
                "re-run with force=true to replace it"
            )
        if stored is not None and self.repository.list_reviews(stored.result.evaluation_id):
            raise WorkflowError("the stored evaluation has human reviews and cannot be replaced")

        evaluator = ProcessEvaluator(self.project_root, self.judge_provider(), self.settings)
        result = evaluator.evaluate(manifest, stored_run.run)
        self.repository.save_evaluation(result, digest, replace=stored is not None)
        return result, True

    # Reviews -----------------------------------------------------------------

    def record_initial_review(
        self,
        evaluation_id: str,
        reviewer_alias: str,
        rubric_version: str,
        initial_label: HumanLabel,
        notes: str = "",
    ) -> HumanReview:
        self.repository.get_evaluation(evaluation_id)
        if self.repository.list_reviews(evaluation_id):
            raise WorkflowError("an initial review already exists; append an adjudication instead")
        review = HumanReview(
            review_id=f"review-{evaluation_id}-v1",
            evaluation_id=evaluation_id,
            review_version=1,
            reviewer_alias=reviewer_alias,
            rubric_version=rubric_version,
            initial_label=initial_label,
            notes=notes,
        )
        self.repository.append_review(review)
        return review

    def record_adjudication(
        self,
        evaluation_id: str,
        reviewer_alias: str,
        rubric_version: str,
        adjudication: str,
        final_label: HumanLabel,
        finding_decisions: list[FindingDecision],
        notes: str = "",
    ) -> HumanReview:
        existing = self.repository.list_reviews(evaluation_id)
        if not existing:
            raise WorkflowError(
                "record the evaluator-hidden initial review before any adjudication"
            )
        version = existing[-1].review_version + 1
        review = HumanReview(
            review_id=f"review-{evaluation_id}-v{version}",
            evaluation_id=evaluation_id,
            review_version=version,
            reviewer_alias=reviewer_alias,
            rubric_version=rubric_version,
            initial_label=existing[0].initial_label,
            evaluator_revealed_at=utc_now(),
            adjudication=adjudication,  # type: ignore[arg-type]
            final_label=final_label,
            finding_decisions=finding_decisions,
            notes=notes,
        )
        self.repository.append_review(review)
        return review

    # Exports -----------------------------------------------------------------

    def export_results(self) -> list[str]:
        """Rebuild per-run and review exports from persisted records only."""

        results_root = self.project_root / self.settings.results_dir
        per_run = results_root / "per_run"
        per_run.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        for stored in self.repository.all_evaluations():
            payload = {
                "input_digest": stored.input_digest,
                "evaluation": stored.result.model_dump(mode="json"),
            }
            path = per_run / f"{stored.result.run_id}.json"
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            written.append(path.relative_to(self.project_root).as_posix())

        reviews_path = results_root / "human_reviews.jsonl"
        lines = [
            json.dumps(review.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
            for review in self.repository.all_reviews()
        ]
        reviews_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        written.append(reviews_path.relative_to(self.project_root).as_posix())

        summary = MetricCalculator(self.repository).summarize()
        summary_path = results_root / "summary.json"
        summary_payload = summary.model_dump(mode="json")
        summary_path.write_text(
            json.dumps(summary_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(summary_path.relative_to(self.project_root).as_posix())

        metrics_path = results_root / "metrics.csv"
        header = "metric_id,value,numerator,denominator,provenance,exclusions"
        csv_lines = [header]
        for metric in summary.metrics:
            value = "" if metric.value is None else f"{metric.value:.6f}"
            exclusions = "; ".join(metric.exclusions).replace('"', "'")
            csv_lines.append(
                f"{metric.metric_id},{value},{metric.numerator},{metric.denominator},"
                f'{metric.provenance},"{exclusions}"'
            )
        metrics_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")
        written.append(metrics_path.relative_to(self.project_root).as_posix())
        return written
