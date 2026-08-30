"""Offline identity and evidence-readiness gate for fixture bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.atif import AtifAdapter, AtifValidationError
from hy3_workbench.contracts import (
    ArtifactReference,
    OutcomeStatus,
    RunRecord,
    StrictModel,
    TaskManifest,
)


class VerifierTestResult(StrictModel):
    name: str
    status: Literal["passed", "failed"]


class VerifierReport(StrictModel):
    """Small fixture report mirroring the official behavioral-test contract."""

    schema_version: Literal["fixture-verifier-report-v1"]
    outcome_status: OutcomeStatus
    fail_to_pass: list[VerifierTestResult]
    pass_to_pass: list[VerifierTestResult]


class EvidenceGateResult(StrictModel):
    """Whether identity and verifier evidence are sufficient for later evaluation."""

    status: Literal["ready", "inconclusive"]
    outcome_status: OutcomeStatus
    reasons: list[str]


class EvidenceGate:
    """Validate bundle identity without attempting semantic diagnosis."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        self.artifacts = ArtifactStore(self.project_root)
        self.atif = AtifAdapter()

    def assess(self, manifest: TaskManifest, run: RunRecord) -> EvidenceGateResult:
        reasons: list[str] = []
        if run.task_id != manifest.task_id:
            reasons.append("run task_id does not match the task manifest")

        for reference in self._artifact_references(run):
            try:
                self.artifacts.verify(reference)
            except ArtifactIntegrityError as error:
                reasons.append(str(error))

        trajectory = None
        try:
            trajectory = self.atif.load(self.project_root / run.trajectory.path)
        except (AtifValidationError, OSError) as error:
            reasons.append(f"invalid ATIF trajectory: {error}")
        if trajectory is not None and trajectory.session_id != run.run_id:
            reasons.append("trajectory session_id does not match run_id")

        report = self._load_report(run, reasons)
        outcome_status: OutcomeStatus = "inconclusive"
        if report is not None:
            outcome_status = self._validate_report(manifest, run, report, reasons)

        if reasons:
            return EvidenceGateResult(
                status="inconclusive",
                outcome_status="inconclusive",
                reasons=reasons,
            )
        return EvidenceGateResult(status="ready", outcome_status=outcome_status, reasons=[])

    @staticmethod
    def _artifact_references(run: RunRecord) -> list[ArtifactReference]:
        references: list[ArtifactReference] = [run.trajectory, run.patch]
        references.extend(
            reference
            for reference in (
                run.verifier.report,
                run.verifier.test_output,
                run.verifier.run_log,
            )
            if reference is not None
        )
        return references

    def _load_report(
        self,
        run: RunRecord,
        reasons: list[str],
    ) -> VerifierReport | None:
        if run.verifier.report is None:
            reasons.append("verifier report is missing")
            return None
        path = self.project_root / run.verifier.report.path
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return VerifierReport.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            reasons.append(f"verifier report is malformed or incomplete: {error}")
            return None

    @staticmethod
    def _validate_report(
        manifest: TaskManifest,
        run: RunRecord,
        report: VerifierReport,
        reasons: list[str],
    ) -> OutcomeStatus:
        expected_fail_to_pass = set(manifest.standard_answer.fail_to_pass)
        expected_pass_to_pass = set(manifest.standard_answer.pass_to_pass)
        actual_fail_to_pass = {result.name for result in report.fail_to_pass}
        actual_pass_to_pass = {result.name for result in report.pass_to_pass}
        if actual_fail_to_pass != expected_fail_to_pass:
            reasons.append("verifier report does not cover the declared FAIL_TO_PASS tests")
        if actual_pass_to_pass != expected_pass_to_pass:
            reasons.append("verifier report does not cover the declared PASS_TO_PASS tests")

        results = [*report.fail_to_pass, *report.pass_to_pass]
        derived_outcome: OutcomeStatus = (
            "resolved" if all(result.status == "passed" for result in results) else "unresolved"
        )
        if report.outcome_status != derived_outcome:
            reasons.append("verifier outcome does not match its test results")

        expected_verifier_status = "passed" if derived_outcome == "resolved" else "failed"
        if run.verifier.status != expected_verifier_status:
            reasons.append("run verifier status does not match its report")
        return derived_outcome
