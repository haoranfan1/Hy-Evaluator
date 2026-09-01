"""Fixed Hy3 semantic judge with evidence validation and one repair retry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Protocol

from harbor.models.trajectories import Trajectory
from pydantic import ValidationError

from hy3_workbench.contracts import (
    AtifStepEvidence,
    Finding,
    ProjectRelativePath,
    RunRecord,
    SemanticReviewOutput,
    StrictModel,
    TaskManifest,
)
from hy3_workbench.evidence_extractor import (
    DeterministicEvidence,
    EvidenceResolutionError,
    EvidenceResolver,
    parse_patch,
)
from hy3_workbench.hy3_client import Hy3JsonResponse
from hy3_workbench.rubric import (
    RUBRIC_VERSION,
    SEMANTIC_PROMPT_VERSION,
    SEMANTIC_SYSTEM_PROMPT,
    condense_semantic_input,
    render_repair_input,
    render_semantic_input,
)

MAX_SEMANTIC_ATTEMPTS = 2  # One initial request plus exactly one schema-repair retry.


class SemanticJudge(Protocol):
    """The minimal judge surface the reviewer depends on."""

    def complete_json(self, messages: list[dict[str, str]]) -> Hy3JsonResponse: ...


class SemanticReviewResult(StrictModel):
    """Honest semantic-lane outcome, including failure without a verdict."""

    status: Literal["completed", "unavailable", "context_limit"]
    rubric_version: Literal["process-rubric-v1"] = RUBRIC_VERSION
    prompt_version: Literal["semantic-prompt-v2"] = SEMANTIC_PROMPT_VERSION
    output: SemanticReviewOutput | None = None
    attempts: int = 0
    failure_reasons: list[str] = []
    raw_response_paths: list[ProjectRelativePath] = []
    condensation: str | None = None


def validate_semantic_output(
    output: SemanticReviewOutput,
    resolver: EvidenceResolver,
    trajectory: Trajectory,
) -> list[str]:
    """Collect every reason the judge output cites nonexistent or invalid evidence."""

    errors: list[str] = []
    agent_steps = {step.step_id for step in trajectory.steps if step.source == "agent"}

    def check_step(step_id: int | None, tool_call_id: str | None, subject: str) -> None:
        if step_id is None:
            return
        try:
            resolver.resolve(
                AtifStepEvidence(kind="atif_step", step_id=step_id, tool_call_id=tool_call_id)
            )
        except (EvidenceResolutionError, ValidationError) as error:
            errors.append(f"{subject}: {error}")
            return
        if step_id not in agent_steps:
            errors.append(f"{subject}: step {step_id} is not agent-authored")

    check_step(output.first_error.step_id, output.first_error.tool_call_id, "first_error")
    if output.process_status == "invalid" and output.first_error.primary_category is None:
        errors.append("first_error: an invalid process requires primary_category")

    for finding in output.findings:
        subject = f"finding {finding.finding_id}"
        check_step(finding.step_id, finding.tool_call_id, subject)
        for step_id in finding.downstream_step_ids:
            check_step(step_id, None, f"{subject} downstream_step_ids")
        check_step(finding.recovery_step_id, None, f"{subject} recovery_step_id")
        for reference in finding.evidence:
            try:
                resolver.resolve(reference)
            except EvidenceResolutionError as error:
                errors.append(f"{subject} evidence: {error}")
    return errors


class SemanticReviewer:
    """Run the fixed judge over one bundle and refuse to fabricate a verdict."""

    def __init__(
        self,
        project_root: Path,
        judge: SemanticJudge,
        semantic_dir: Path,
        context_limit_chars: int,
    ) -> None:
        if semantic_dir.is_absolute() or ".." in semantic_dir.parts:
            raise ValueError("semantic_dir must be a project-relative path")
        self.project_root = project_root.resolve(strict=True)
        self.judge = judge
        self.semantic_dir = semantic_dir
        self.context_limit_chars = context_limit_chars

    def review(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        trajectory: Trajectory,
        patch_text: str,
        deterministic: DeterministicEvidence,
    ) -> SemanticReviewResult:
        user_input = render_semantic_input(manifest, run, trajectory, patch_text, deterministic)
        condensation: str | None = None
        if len(SEMANTIC_SYSTEM_PROMPT) + len(user_input) > self.context_limit_chars:
            condensed, condensation = condense_semantic_input(
                manifest,
                run,
                trajectory,
                patch_text,
                deterministic,
                budget=self.context_limit_chars - len(SEMANTIC_SYSTEM_PROMPT),
            )
            if condensed is None:
                return SemanticReviewResult(
                    status="context_limit",
                    failure_reasons=[
                        "rendered judge input exceeds the configured context limit even "
                        "after bounded condensation"
                    ],
                )
            user_input = condensed

        resolver = EvidenceResolver(
            manifest,
            run,
            trajectory,
            frozenset(item.path for item in parse_patch(patch_text).files),
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SEMANTIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
        failure_reasons: list[str] = []
        raw_paths: list[str] = []

        for attempt in range(1, MAX_SEMANTIC_ATTEMPTS + 1):
            try:
                response = self.judge.complete_json(messages)
            except Exception as error:
                # A transport-level judge failure (timeout, connection, HTTP
                # error) consumes one bounded attempt and then degrades to an
                # honest unavailable result instead of crashing the evaluation.
                failure_reasons.append(
                    f"attempt {attempt}: judge request failed: {type(error).__name__}: {error}"
                )
                if attempt == MAX_SEMANTIC_ATTEMPTS:
                    return SemanticReviewResult(
                        status="unavailable",
                        attempts=attempt,
                        failure_reasons=failure_reasons,
                        raw_response_paths=raw_paths,
                        condensation=condensation,
                    )
                continue
            errors = self._validate_response(response.content, resolver, trajectory)
            raw_paths.append(self._persist_attempt(run.run_id, attempt, response, errors))
            if not errors:
                output = SemanticReviewOutput.model_validate_json(response.content)
                return SemanticReviewResult(
                    status="completed",
                    output=output,
                    attempts=attempt,
                    raw_response_paths=raw_paths,
                    condensation=condensation,
                )
            failure_reasons.append(f"attempt {attempt}: " + "; ".join(errors))
            messages = [
                *messages,
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": render_repair_input(errors)},
            ]

        return SemanticReviewResult(
            status="unavailable",
            attempts=MAX_SEMANTIC_ATTEMPTS,
            failure_reasons=failure_reasons,
            raw_response_paths=raw_paths,
            condensation=condensation,
        )

    @staticmethod
    def _validate_response(
        content: str,
        resolver: EvidenceResolver,
        trajectory: Trajectory,
    ) -> list[str]:
        if not content.strip():
            return ["response contained no JSON content"]
        try:
            output = SemanticReviewOutput.model_validate_json(content)
        except ValidationError as error:
            return [
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            ]
        return validate_semantic_output(output, resolver, trajectory)

    def _persist_attempt(
        self,
        run_id: str,
        attempt: int,
        response: Hy3JsonResponse,
        errors: list[str],
    ) -> str:
        relative = self.semantic_dir / run_id / f"attempt-{attempt}.json"
        path = self.project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": "semantic-raw-response-v1",
            "attempt": attempt,
            "response_id": response.response_id,
            "model": response.model,
            "content": response.content,
            "validation_errors": errors,
        }
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return relative.as_posix()


def semantic_findings(result: SemanticReviewResult) -> list[Finding]:
    """Return the validated semantic findings, or none when the lane failed."""

    if result.output is None:
        return []
    return list(result.output.findings)
