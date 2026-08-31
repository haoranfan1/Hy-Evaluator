"""Offline identity and evidence-readiness gate for fixture bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.atif import AtifAdapter, AtifValidationError
from hy3_workbench.contracts import (
    ArtifactReference,
    OutcomeStatus,
    RunRecord,
    StrictModel,
    TaskManifest,
)

SWEBENCH_REPORT_ADAPTER_VERSION = "swebench-report-adapter-v1"


class VerifierTestResult(StrictModel):
    name: str
    status: Literal["passed", "failed"]


class VerifierReport(StrictModel):
    """Canonical per-test verifier evidence mirroring the behavioral-test contract.

    ``schema_version`` records which parser produced the in-memory report: the
    fixture format is read verbatim, while raw official SWE-bench ``report.json``
    files are mapped by the versioned adapter without rewriting the artifact.
    """

    schema_version: Literal["fixture-verifier-report-v1", "swebench-report-adapter-v1"]
    outcome_status: OutcomeStatus
    fail_to_pass: list[VerifierTestResult]
    pass_to_pass: list[VerifierTestResult]


def parse_verifier_report(payload: object) -> VerifierReport:
    """Parse a verifier report artifact in either supported format.

    Raises ``ValueError`` (or pydantic ``ValidationError``) when the payload is
    neither a fixture report nor a gradeable official SWE-bench report.
    """

    if isinstance(payload, dict) and payload.get("schema_version") is not None:
        return VerifierReport.model_validate(payload)
    return _parse_swebench_report(payload)


def _parse_swebench_report(payload: object) -> VerifierReport:
    """Map one official SWE-bench ``report.json`` into the canonical report.

    The official file is keyed by exactly one instance id and carries a
    ``tests_status`` block whose FAIL_TO_PASS/PASS_TO_PASS families each list
    ``success`` and ``failure`` test names (grading counts a declared test that
    is missing from the log as a failure, so the two lists cover the declared
    contract). A report without ``tests_status`` — the official marker that the
    test run produced no gradeable output — is rejected here so the caller
    records an honest exclusion instead of a fabricated outcome.
    """

    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError("swebench report must be keyed by exactly one instance id")
    ((instance_id, body),) = payload.items()
    if not isinstance(body, dict):
        raise ValueError(f"swebench report body for {instance_id} is not an object")
    tests_status = body.get("tests_status")
    if not isinstance(tests_status, dict):
        raise ValueError(
            f"swebench report for {instance_id} has no gradeable tests_status "
            "(the official grader found no parseable test output)"
        )
    resolved = body.get("resolved")
    if not isinstance(resolved, bool):
        raise ValueError(f"swebench report for {instance_id} has no boolean resolved flag")

    def family(name: str) -> list[VerifierTestResult]:
        block = tests_status.get(name)
        if not isinstance(block, dict):
            raise ValueError(f"swebench report for {instance_id} is missing {name} results")
        results: list[VerifierTestResult] = []
        seen: set[str] = set()
        for status, key in (("passed", "success"), ("failed", "failure")):
            tests = block.get(key)
            if not isinstance(tests, list) or any(not isinstance(t, str) for t in tests):
                raise ValueError(
                    f"swebench report for {instance_id} has a malformed {name}.{key} list"
                )
            for test in tests:
                if test in seen:
                    raise ValueError(
                        f"swebench report for {instance_id} lists {name} test "
                        f"{test} with contradictory statuses"
                    )
                seen.add(test)
                results.append(VerifierTestResult(name=test, status=status))
        return results

    return VerifierReport(
        schema_version=SWEBENCH_REPORT_ADAPTER_VERSION,
        outcome_status="resolved" if resolved else "unresolved",
        fail_to_pass=family("FAIL_TO_PASS"),
        pass_to_pass=family("PASS_TO_PASS"),
    )


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
            return parse_verifier_report(payload)
        except (OSError, ValueError) as error:
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
