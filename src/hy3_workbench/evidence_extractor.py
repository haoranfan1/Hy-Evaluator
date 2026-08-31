"""Deterministic evidence extraction and outcome policy for run bundles.

This lane records facts and rules only. First-error diagnosis, merge precedence,
and any model call stay outside this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from harbor.models.trajectories import Step, Trajectory
from pydantic import Field, TypeAdapter, ValidationError

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.atif import AtifAdapter, AtifValidationError
from hy3_workbench.contracts import (
    ArtifactReference,
    AtifStepEvidence,
    DeterministicCheck,
    EvidenceReference,
    OutcomeStatus,
    PatchEvidence,
    ProjectRelativePath,
    RunRecord,
    StrictModel,
    TaskEvidence,
    TaskManifest,
    VerifierEvidence,
)
from hy3_workbench.evidence_gate import VerifierReport, parse_verifier_report

# Scope thresholds and sensitive-file classifiers stay conservative: they emit
# warnings for semantic/human review and never fail a run on their own.
BROAD_PATCH_FILE_COUNT = 5
BROAD_PATCH_CHANGED_LINES = 200
LOCKFILE_NAMES = frozenset(
    {
        "cargo.lock",
        "composer.lock",
        "gemfile.lock",
        "go.sum",
        "package-lock.json",
        "pipfile.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)
GENERATED_PATH_PARTS = frozenset({"build", "dist", "node_modules", "__pycache__", "vendor"})
GENERATED_FILE_SUFFIXES = (".min.css", ".min.js", "_pb2.py", "_pb2_grpc.py")

_DIFF_HEADER = re.compile(r"^diff --git a/(?P<a>\S+) b/(?P<b>\S+)$")
_COMMAND_FAILURE_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("python traceback", re.compile(r"traceback \(most recent call last\)", re.IGNORECASE)),
    ("command not found", re.compile(r"command not found", re.IGNORECASE)),
    ("missing file or directory", re.compile(r"no such file or directory", re.IGNORECASE)),
    ("permission denied", re.compile(r"permission denied", re.IGNORECASE)),
    (
        "non-zero exit status",
        re.compile(r"returned non-zero exit status|non-zero exit code", re.IGNORECASE),
    ),
    ("non-zero exit code", re.compile(r"\bexit code:? [1-9]\d*\b", re.IGNORECASE)),
    ("failing tests reported", re.compile(r"\b[1-9]\d* failed\b", re.IGNORECASE)),
)
_SUCCESS_CLAIM = re.compile(
    r"\b(implemented|fixed|resolved|verified|passes|passed|completed?|succeeded|"
    r"success(?:fully)?|works)\b",
    re.IGNORECASE,
)
_AGENT_PATCH_FAILURE = re.compile(
    r"patch does not apply|hunk .*failed|malformed patch|patch failed|corrupt patch",
    re.IGNORECASE,
)
_INFRASTRUCTURE_FAILURE = re.compile(
    r"connection lost|connection refused|cannot connect|docker daemon|image pull|"
    r"no space left|out of memory|oom-?kill|timed out waiting",
    re.IGNORECASE,
)

_relative_path_adapter = TypeAdapter(ProjectRelativePath)


class PatchedFile(StrictModel):
    """Changed-file facts extracted from one unified diff section."""

    path: str
    added_lines: int = Field(ge=0)
    removed_lines: int = Field(ge=0)


class PatchFacts(StrictModel):
    """Deterministic facts about the generated patch text."""

    files: list[PatchedFile]
    is_empty: bool
    is_parseable: bool

    @property
    def total_changed_lines(self) -> int:
        return sum(item.added_lines + item.removed_lines for item in self.files)


class DeterministicEvidence(StrictModel):
    """Facts, rules, and readiness produced without any model call."""

    status: Literal["ready", "inconclusive"]
    outcome_status: OutcomeStatus
    checks: list[DeterministicCheck]
    exclusions: list[str]


class EvidenceResolutionError(ValueError):
    """An evidence reference does not resolve to a real bundle object."""


class EvidenceResolver:
    """Resolve evidence references against one loaded bundle."""

    def __init__(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        trajectory: Trajectory | None,
        patch_files: frozenset[str],
    ) -> None:
        self.manifest = manifest
        self.run = run
        self.trajectory = trajectory
        self.patch_files = patch_files
        self.verifier_artifact_ids = frozenset(
            reference.artifact_id
            for reference in (
                run.verifier.report,
                run.verifier.test_output,
                run.verifier.run_log,
            )
            if reference is not None
        )
        self.declared_tests = frozenset(
            [*manifest.standard_answer.fail_to_pass, *manifest.standard_answer.pass_to_pass]
        )

    def resolve(self, reference: EvidenceReference) -> None:
        if isinstance(reference, AtifStepEvidence):
            if self.trajectory is None:
                raise EvidenceResolutionError("no validated trajectory is available")
            try:
                AtifAdapter.validate_step_evidence(self.trajectory, reference)
            except AtifValidationError as error:
                raise EvidenceResolutionError(str(error)) from error
        elif isinstance(reference, PatchEvidence):
            if reference.file not in self.patch_files:
                raise EvidenceResolutionError(f"patch does not change {reference.file}")
        elif isinstance(reference, VerifierEvidence):
            if reference.artifact_id not in self.verifier_artifact_ids:
                raise EvidenceResolutionError(f"unknown verifier artifact {reference.artifact_id}")
            if reference.test_name is not None and reference.test_name not in self.declared_tests:
                raise EvidenceResolutionError(f"undeclared test {reference.test_name}")
        elif isinstance(reference, TaskEvidence):
            value: object = self.manifest
            for part in reference.field.split("."):
                fields = getattr(type(value), "model_fields", None)
                if fields is None or part not in fields:
                    raise EvidenceResolutionError(f"unknown task field {reference.field}")
                value = getattr(value, part)
        else:  # pragma: no cover - exhaustive over the contract union
            raise EvidenceResolutionError(f"unsupported evidence kind {reference}")


def parse_patch(text: str) -> PatchFacts:
    """Extract changed files and line counts from unified diff text."""

    files: list[PatchedFile] = []
    current: dict[str, int] | None = None
    current_path: str | None = None

    def flush() -> None:
        nonlocal current, current_path
        if current_path is not None and current is not None:
            files.append(
                PatchedFile(
                    path=current_path,
                    added_lines=current["added"],
                    removed_lines=current["removed"],
                )
            )
        current = None
        current_path = None

    for line in text.splitlines():
        header = _DIFF_HEADER.match(line)
        if header:
            flush()
            b_side = header.group("b")
            current_path = header.group("a") if b_side == "/dev/null" else b_side
            current = {"added": 0, "removed": 0}
            continue
        if current is None:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            current["added"] += 1
        elif line.startswith("-"):
            current["removed"] += 1
    flush()

    return PatchFacts(
        files=files,
        is_empty=not text.strip(),
        is_parseable=bool(files) or not text.strip(),
    )


def _text(value: object) -> str:
    """Flatten an ATIF message or observation content into searchable text."""

    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [part for part in (getattr(item, "text", None) for item in value) if part]
        return "\n".join(parts)
    return ""


def _step_evidence(step_id: int, tool_call_id: str | None = None) -> AtifStepEvidence:
    if tool_call_id is not None:
        try:
            return AtifStepEvidence(kind="atif_step", step_id=step_id, tool_call_id=tool_call_id)
        except ValidationError:
            pass  # A non-identifier tool_call_id falls back to step-level evidence.
    return AtifStepEvidence(kind="atif_step", step_id=step_id)


def _patch_evidence_files(paths: list[str]) -> list[EvidenceReference]:
    """Cite only diff paths that are canonical project-relative paths."""

    references: list[EvidenceReference] = []
    for path in paths:
        try:
            references.append(
                PatchEvidence(kind="patch", file=_relative_path_adapter.validate_python(path))
            )
        except ValidationError:
            continue
    return references


def _check(
    check_id: str,
    status: Literal["pass", "fail", "warning", "unknown"],
    summary: str,
    evidence: list[EvidenceReference],
    *,
    hard_process_failure: bool = False,
) -> DeterministicCheck:
    return DeterministicCheck(
        check_id=check_id,
        status=status,
        summary=summary,
        evidence=evidence,
        hard_process_failure=hard_process_failure,
    )


def check_atif_structure(trajectory: Trajectory, run_id: str) -> DeterministicCheck:
    """Validate trajectory/run linkage beyond Harbor's pinned schema.

    Harbor's ATIF v1.7 model already rejects non-sequential step IDs and
    observation results that reference unknown tool calls, so those conditions
    surface as load failures before this check runs.
    """

    violations: list[str] = []
    evidence: list[EvidenceReference] = []

    if trajectory.session_id != run_id:
        violations.append(f"session_id {trajectory.session_id!r} does not match run_id {run_id!r}")
    if not trajectory.steps:
        violations.append("trajectory contains no steps")

    for step in trajectory.steps:
        tool_call_ids = [call.tool_call_id for call in step.tool_calls or []]
        if len(tool_call_ids) != len(set(tool_call_ids)):
            violations.append(f"step {step.step_id} declares duplicate tool_call_ids")
            evidence.append(_step_evidence(step.step_id))

    if violations:
        return _check(
            "check-atif-structure",
            "fail",
            "ATIF structure is invalid: " + "; ".join(violations),
            evidence,
        )
    return _check(
        "check-atif-structure",
        "pass",
        f"ATIF structure is valid with {len(trajectory.steps)} sequential steps.",
        [],
    )


def _is_test_path(path: str) -> bool:
    parts = path.lower().split("/")
    name = parts[-1]
    return (
        "tests" in parts[:-1]
        or "test" in parts[:-1]
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.js", ".test.ts", "_test.go"))
    )


def _is_lockfile(path: str) -> bool:
    return path.lower().rsplit("/", maxsplit=1)[-1] in LOCKFILE_NAMES


def _is_generated(path: str) -> bool:
    parts = path.lower().split("/")
    return bool(GENERATED_PATH_PARTS.intersection(parts[:-1])) or parts[-1].endswith(
        GENERATED_FILE_SUFFIXES
    )


def check_patch_scope(facts: PatchFacts) -> list[DeterministicCheck]:
    """Record patch breadth and sensitive-file warnings without failing them."""

    checks: list[DeterministicCheck] = []
    all_paths = [item.path for item in facts.files]

    if facts.is_empty:
        checks.append(_check("check-patch-scope", "warning", "The generated patch is empty.", []))
    elif not facts.is_parseable:
        checks.append(
            _check(
                "check-patch-scope",
                "warning",
                "The generated patch has no recognizable unified-diff file sections.",
                [],
            )
        )
    else:
        broad = (
            len(facts.files) > BROAD_PATCH_FILE_COUNT
            or facts.total_changed_lines > BROAD_PATCH_CHANGED_LINES
        )
        summary = (
            f"The patch changes {len(facts.files)} file(s) and {facts.total_changed_lines} line(s)."
        )
        if broad:
            summary += (
                f" This exceeds the review thresholds of {BROAD_PATCH_FILE_COUNT} files or "
                f"{BROAD_PATCH_CHANGED_LINES} changed lines."
            )
        checks.append(
            _check(
                "check-patch-scope",
                "warning" if broad else "pass",
                summary,
                _patch_evidence_files(all_paths),
            )
        )

    for check_id, label, matcher in (
        ("check-patch-tests", "test files", _is_test_path),
        ("check-patch-lockfiles", "lockfiles", _is_lockfile),
        ("check-patch-generated", "generated files", _is_generated),
    ):
        hits = [path for path in all_paths if matcher(path)]
        if hits:
            checks.append(
                _check(
                    check_id,
                    "warning",
                    f"The patch modifies {label} flagged for review: {', '.join(sorted(hits))}.",
                    _patch_evidence_files(hits),
                )
            )
        else:
            checks.append(_check(check_id, "pass", f"The patch does not modify {label}.", []))
    return checks


_REVERT_COMMAND_PATTERN = re.compile(r"\bgit\s+(checkout|restore|stash)\b")
_PYTHON_WRITE_PATTERN = re.compile(r"open\([^)]*['\"](?:w|a|r\+)['\"]|\.write\(|write_text\(")


def _redirect_or_copy_into(serialized: str, protected: str) -> bool:
    escaped = re.escape(protected)
    return bool(
        re.search(rf">>?\s*\\?\"?\S*{escaped}", serialized)
        or re.search(rf"\btee\s+(-a\s+)?\S*{escaped}", serialized)
        or re.search(rf"\b(cp|mv)\s+\S+\s+\S*{escaped}", serialized)
    )


def _command_writes_protected(serialized: str, protected: str) -> bool:
    """Heuristic: does this tool call modify the protected path it references?

    Revert commands (git checkout/restore/stash) restore committed content and
    are never counted as violating writes.
    """

    if _REVERT_COMMAND_PATTERN.search(serialized):
        return False
    if "sed -i" in serialized or "perl -i" in serialized:
        return True
    if _redirect_or_copy_into(serialized, protected):
        return True
    if re.search(r"\b(git\s+apply|patch)\b", serialized):
        return True
    return bool(_PYTHON_WRITE_PATTERN.search(serialized))


def _observed_success(step) -> bool:
    """Whether the step's first observation reports a zero return code.

    Unparseable observations count as successful so a write attempt is never
    silently dropped just because the runner's output format is unknown.
    """

    if not step.observation or not step.observation.results:
        return True
    content = step.observation.results[0].content or ""
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return True
    if isinstance(payload, dict) and isinstance(payload.get("returncode"), int):
        return payload["returncode"] == 0
    return True


def check_protected_paths(
    protected_paths: list[str],
    policy: str,
    facts: PatchFacts,
    trajectory: Trajectory | None,
) -> DeterministicCheck:
    """Detect access to or modification of manifest-protected paths.

    Under ``no_read`` any reference is a hard violation (secret checker
    artifacts). Under ``no_modify`` only modification evidence is a hard
    violation: the submitted patch touching a protected path, anchored at the
    first successful modifying step; transient in-process writes that were
    reverted before submission become a warning; read-only references pass with
    an explanatory note.
    """

    modified: list[str] = []
    for item in facts.files:
        for protected in protected_paths:
            if item.path == protected or item.path.startswith(f"{protected}/"):
                modified.append(item.path)

    read_references: list[EvidenceReference] = []
    read_notes: list[str] = []
    write_references: list[EvidenceReference] = []
    write_notes: list[str] = []
    if trajectory is not None:
        for step in trajectory.steps:
            for call in step.tool_calls or []:
                serialized = json.dumps(call.arguments, ensure_ascii=False)
                for protected in protected_paths:
                    if protected not in serialized:
                        continue
                    note = (
                        f"step {step.step_id} tool call {call.tool_call_id!r} "
                        f"references {protected!r}"
                    )
                    if _command_writes_protected(serialized, protected) and _observed_success(step):
                        write_references.append(_step_evidence(step.step_id, call.tool_call_id))
                        write_notes.append(note.replace("references", "modifies"))
                    else:
                        read_references.append(_step_evidence(step.step_id, call.tool_call_id))
                        read_notes.append(note)

    task_evidence: EvidenceReference = TaskEvidence(kind="task", field="protected_paths")

    if policy == "no_read" and (modified or read_references or write_references):
        details: list[str] = []
        evidence: list[EvidenceReference] = [task_evidence]
        if modified:
            details.append(
                f"the patch modifies protected path(s): {', '.join(sorted(set(modified)))}"
            )
            evidence.extend(_patch_evidence_files(sorted(set(modified))))
        if write_notes or read_notes:
            details.append("; ".join([*write_notes, *read_notes]))
            evidence.extend([*write_references, *read_references])
        return _check(
            "check-protected-paths",
            "fail",
            "Manifest-protected paths were touched: " + "; ".join(details) + ".",
            evidence,
            hard_process_failure=True,
        )

    if modified:
        details = [f"the patch modifies protected path(s): {', '.join(sorted(set(modified)))}"]
        evidence = [task_evidence, *_patch_evidence_files(sorted(set(modified)))]
        if write_notes:
            details.append("; ".join(write_notes))
            evidence.extend(write_references)
        return _check(
            "check-protected-paths",
            "fail",
            "Manifest-protected paths were modified: " + "; ".join(details) + ".",
            evidence,
            hard_process_failure=True,
        )

    if write_references:
        return _check(
            "check-protected-paths",
            "warning",
            "Protected path(s) were modified during the process but the submitted patch "
            "does not contain the change (reverted before submission): "
            + "; ".join(write_notes)
            + ". Human review should judge intent.",
            [task_evidence, *write_references],
        )

    if read_references:
        return _check(
            "check-protected-paths",
            "pass",
            f"Manifest-protected paths were referenced read-only in {len(read_references)} "
            "tool call(s) during investigation; the patch does not modify them.",
            [task_evidence],
        )

    return _check(
        "check-protected-paths",
        "pass",
        "No manifest-protected path is accessed or modified.",
        [task_evidence],
    )


def check_command_failures(trajectory: Trajectory) -> list[DeterministicCheck]:
    """Record observed command/tool failures as advisory facts."""

    checks: list[DeterministicCheck] = []
    for step in trajectory.steps:
        if step.source != "agent" or step.observation is None:
            continue
        calls = {call.tool_call_id: call for call in step.tool_calls or []}
        for index, result in enumerate(step.observation.results, start=1):
            content = _text(result.content)
            markers = [
                name for name, pattern in _COMMAND_FAILURE_MARKERS if pattern.search(content)
            ]
            if not markers:
                continue
            call = calls.get(result.source_call_id) if result.source_call_id else None
            subject = (
                f"tool call {result.source_call_id!r} ({call.function_name})"
                if call is not None
                else "an action without a tool call"
            )
            checks.append(
                _check(
                    f"check-command-failure-{step.step_id}-{index}",
                    "warning",
                    f"Advisory: step {step.step_id} observed a failure from {subject}: "
                    f"{', '.join(markers)}. Failed exploration is not a process error "
                    "by itself.",
                    [_step_evidence(step.step_id, result.source_call_id)],
                )
            )
    return checks


def check_final_claim(
    trajectory: Trajectory,
    fail_to_pass: list[str],
    outcome_status: OutcomeStatus,
) -> DeterministicCheck | None:
    """Compare the final explicit success claim with observed verification."""

    final_step: Step | None = next(
        (step for step in reversed(trajectory.steps) if step.source == "agent"), None
    )
    if final_step is None:
        return None

    evidence: list[EvidenceReference] = [
        _step_evidence(final_step.step_id),
        TaskEvidence(kind="task", field="standard_answer.fail_to_pass"),
    ]
    if not _SUCCESS_CLAIM.search(_text(final_step.message)):
        return _check(
            "check-final-claim",
            "pass",
            f"The final agent step {final_step.step_id} makes no explicit success claim.",
            evidence,
        )

    commands = "\n".join(
        json.dumps(call.arguments, ensure_ascii=False)
        for step in trajectory.steps
        for call in step.tool_calls or []
    )
    referenced = any(
        name in commands or name.split("::", maxsplit=1)[0] in commands for name in fail_to_pass
    )
    if not referenced:
        return _check(
            "check-final-claim",
            "warning",
            f"Step {final_step.step_id} claims success, but no command references the "
            "declared FAIL_TO_PASS tests, so the claim is unsupported by observed "
            "verification.",
            evidence,
        )
    if outcome_status == "unresolved":
        return _check(
            "check-final-claim",
            "warning",
            f"Step {final_step.step_id} claims success, but the official verifier "
            "outcome is unresolved.",
            evidence,
        )
    return _check(
        "check-final-claim",
        "pass",
        f"The final success claim at step {final_step.step_id} is consistent with "
        "executed FAIL_TO_PASS verification.",
        evidence,
    )


def classify_verifier_logs(
    texts: list[str],
) -> Literal["agent_patch_failure", "infrastructure"] | None:
    """Attribute a missing verifier verdict to the agent or the infrastructure."""

    joined = "\n".join(texts)
    if _AGENT_PATCH_FAILURE.search(joined):
        return "agent_patch_failure"
    if _INFRASTRUCTURE_FAILURE.search(joined):
        return "infrastructure"
    return None


class EvidenceExtractor:
    """Produce deterministic checks, outcome policy, and exclusions for one bundle."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        self.artifacts = ArtifactStore(self.project_root)
        self.atif = AtifAdapter()

    def extract(self, manifest: TaskManifest, run: RunRecord) -> DeterministicEvidence:
        checks: list[DeterministicCheck] = []
        exclusions: list[str] = []

        verified = self._verify_identity(manifest, run, checks, exclusions)
        trajectory = self._load_trajectory(run, verified, checks, exclusions)
        outcome_status = self._extract_verifier_facts(manifest, run, verified, checks, exclusions)
        facts = self._extract_patch_facts(run, verified, checks)

        checks.append(
            check_protected_paths(
                list(manifest.protected_paths),
                manifest.protected_path_policy,
                facts,
                trajectory,
            )
        )
        if trajectory is not None:
            checks.extend(check_command_failures(trajectory))
            final_claim = check_final_claim(
                trajectory, list(manifest.standard_answer.fail_to_pass), outcome_status
            )
            if final_claim is not None:
                checks.append(final_claim)

        status: Literal["ready", "inconclusive"] = "inconclusive" if exclusions else "ready"
        if status == "inconclusive":
            outcome_status = "inconclusive"

        self._assert_evidence_resolves(manifest, run, trajectory, facts, checks)
        return DeterministicEvidence(
            status=status,
            outcome_status=outcome_status,
            checks=checks,
            exclusions=exclusions,
        )

    def _verify_identity(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        checks: list[DeterministicCheck],
        exclusions: list[str],
    ) -> set[str]:
        reasons: list[str] = []
        verified: set[str] = set()
        if run.task_id != manifest.task_id:
            reasons.append("run task_id does not match the task manifest")

        references: list[tuple[str, ArtifactReference | None]] = [
            ("trajectory", run.trajectory),
            ("patch", run.patch),
            ("report", run.verifier.report),
            ("test_output", run.verifier.test_output),
            ("run_log", run.verifier.run_log),
        ]
        for label, reference in references:
            if reference is None:
                continue
            try:
                self.artifacts.verify(reference)
                verified.add(label)
            except ArtifactIntegrityError as error:
                reasons.append(str(error))

        if reasons:
            checks.append(
                _check(
                    "check-identity",
                    "fail",
                    "Bundle identity is broken: " + "; ".join(reasons) + ".",
                    [],
                )
            )
            exclusions.extend(reasons)
        else:
            checks.append(
                _check(
                    "check-identity",
                    "pass",
                    "Task linkage and every referenced artifact hash verify.",
                    [],
                )
            )
        return verified

    def _load_trajectory(
        self,
        run: RunRecord,
        verified: set[str],
        checks: list[DeterministicCheck],
        exclusions: list[str],
    ) -> Trajectory | None:
        if "trajectory" not in verified:
            return None
        try:
            trajectory = self.atif.load(self.project_root / run.trajectory.path)
        except (AtifValidationError, OSError) as error:
            checks.append(
                _check(
                    "check-atif-structure",
                    "fail",
                    f"The ATIF trajectory failed validation: {error}.",
                    [],
                )
            )
            exclusions.append(f"invalid ATIF trajectory: {error}")
            return None

        structure = check_atif_structure(trajectory, run.run_id)
        checks.append(structure)
        if structure.status == "fail":
            exclusions.append("ATIF structural validation failed")
            return None
        return trajectory

    def _extract_verifier_facts(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        verified: set[str],
        checks: list[DeterministicCheck],
        exclusions: list[str],
    ) -> OutcomeStatus:
        report = None
        report_reason: str | None = None
        if run.verifier.report is None:
            report_reason = "verifier report is missing"
        elif "report" not in verified:
            report_reason = "verifier report artifact failed identity verification"
        else:
            try:
                payload = json.loads(
                    (self.project_root / run.verifier.report.path).read_text(encoding="utf-8")
                )
                report = parse_verifier_report(payload)
            except (OSError, ValueError) as error:
                report_reason = f"verifier report is malformed or incomplete: {error}"

        if report is None:
            checks.append(
                _check(
                    "check-verifier-report",
                    "fail",
                    f"No gradeable verifier report: {report_reason}.",
                    [],
                )
            )
            return self._classify_ungradeable_run(run, verified, checks, exclusions, report_reason)

        checks.append(
            _check(
                "check-verifier-report",
                "pass",
                "The verifier report parses against the behavioral-test contract.",
                [VerifierEvidence(kind="verifier", artifact_id=run.verifier.report.artifact_id)],
            )
        )
        return self._record_test_results(manifest, run, report, checks, exclusions)

    def _classify_ungradeable_run(
        self,
        run: RunRecord,
        verified: set[str],
        checks: list[DeterministicCheck],
        exclusions: list[str],
        report_reason: str | None,
    ) -> OutcomeStatus:
        texts: list[str] = []
        log_evidence: list[EvidenceReference] = []
        for label, reference in (
            ("test_output", run.verifier.test_output),
            ("run_log", run.verifier.run_log),
        ):
            if reference is not None and label in verified:
                texts.append((self.project_root / reference.path).read_text(encoding="utf-8"))
                log_evidence.append(
                    VerifierEvidence(kind="verifier", artifact_id=reference.artifact_id)
                )

        classification = classify_verifier_logs(texts)
        if classification == "agent_patch_failure":
            checks.append(
                _check(
                    "check-patch-application",
                    "fail",
                    "Verifier logs show the generated patch failed to apply; this is an "
                    "agent-caused unresolved outcome, not an infrastructure failure.",
                    log_evidence,
                )
            )
            return "unresolved"

        if classification == "infrastructure":
            checks.append(
                _check(
                    "check-verifier-infrastructure",
                    "unknown",
                    "Verifier logs show an infrastructure failure, so the run cannot be "
                    "graded against the behavioral-test contract.",
                    log_evidence,
                )
            )
            exclusions.append(f"infrastructure failure prevented grading ({report_reason})")
            return "inconclusive"

        exclusions.append(report_reason or "verifier evidence is unavailable")
        return "inconclusive"

    def _record_test_results(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        report: VerifierReport,
        checks: list[DeterministicCheck],
        exclusions: list[str],
    ) -> OutcomeStatus:
        assert run.verifier.report is not None
        report_id = run.verifier.report.artifact_id
        coverage_problems: list[str] = []

        for family, declared, reported in (
            ("fail-to-pass", manifest.standard_answer.fail_to_pass, report.fail_to_pass),
            ("pass-to-pass", manifest.standard_answer.pass_to_pass, report.pass_to_pass),
        ):
            reported_by_name = {result.name: result for result in reported}
            for index, name in enumerate(declared, start=1):
                result = reported_by_name.get(name)
                evidence: list[EvidenceReference] = [
                    VerifierEvidence(kind="verifier", artifact_id=report_id, test_name=name),
                    TaskEvidence(
                        kind="task",
                        field=f"standard_answer.{family.replace('-', '_')}",
                    ),
                ]
                if result is None:
                    coverage_problems.append(f"declared test {name} is missing from the report")
                    checks.append(
                        _check(
                            f"check-test-{family}-{index}",
                            "unknown",
                            f"Declared {family} test {name} is missing from the verifier report.",
                            evidence,
                        )
                    )
                else:
                    checks.append(
                        _check(
                            f"check-test-{family}-{index}",
                            "pass" if result.status == "passed" else "fail",
                            f"Declared {family} test {name} {result.status}.",
                            evidence,
                        )
                    )
            undeclared = [name for name in reported_by_name if name not in set(declared)]
            coverage_problems.extend(
                f"report contains undeclared {family} test {name}" for name in undeclared
            )

        if coverage_problems:
            checks.append(
                _check(
                    "check-verifier-coverage",
                    "fail",
                    "Verifier coverage does not match the declared contract: "
                    + "; ".join(coverage_problems)
                    + ".",
                    [VerifierEvidence(kind="verifier", artifact_id=report_id)],
                )
            )
            exclusions.append("verifier report does not cover the declared behavioral tests")
            return "inconclusive"
        checks.append(
            _check(
                "check-verifier-coverage",
                "pass",
                "The verifier report covers exactly the declared behavioral tests.",
                [
                    VerifierEvidence(kind="verifier", artifact_id=report_id),
                    TaskEvidence(kind="task", field="standard_answer.fail_to_pass"),
                    TaskEvidence(kind="task", field="standard_answer.pass_to_pass"),
                ],
            )
        )

        results = [*report.fail_to_pass, *report.pass_to_pass]
        derived: OutcomeStatus = (
            "resolved" if all(result.status == "passed" for result in results) else "unresolved"
        )
        consistency_problems: list[str] = []
        if report.outcome_status != derived:
            consistency_problems.append(
                f"report outcome {report.outcome_status} contradicts its test results"
            )
        expected_status = "passed" if derived == "resolved" else "failed"
        if run.verifier.status != expected_status:
            consistency_problems.append(
                f"run verifier status {run.verifier.status} contradicts the report"
            )
        if consistency_problems:
            checks.append(
                _check(
                    "check-verifier-consistency",
                    "fail",
                    "Verifier evidence is internally inconsistent: "
                    + "; ".join(consistency_problems)
                    + ".",
                    [VerifierEvidence(kind="verifier", artifact_id=report_id)],
                )
            )
            exclusions.append("verifier evidence is internally inconsistent")
            return "inconclusive"

        passed = sum(1 for result in results if result.status == "passed")
        checks.append(
            _check(
                "check-outcome",
                "pass",
                f"The official outcome is {derived}: {passed}/{len(results)} declared "
                "behavioral tests passed.",
                [
                    VerifierEvidence(kind="verifier", artifact_id=report_id),
                    TaskEvidence(kind="task", field="standard_answer.fail_to_pass"),
                ],
            )
        )
        return derived

    def _extract_patch_facts(
        self,
        run: RunRecord,
        verified: set[str],
        checks: list[DeterministicCheck],
    ) -> PatchFacts:
        if "patch" not in verified:
            return PatchFacts(files=[], is_empty=True, is_parseable=True)
        text = (self.project_root / run.patch.path).read_text(encoding="utf-8")
        facts = parse_patch(text)
        checks.extend(check_patch_scope(facts))
        return facts

    @staticmethod
    def _assert_evidence_resolves(
        manifest: TaskManifest,
        run: RunRecord,
        trajectory: Trajectory | None,
        facts: PatchFacts,
        checks: list[DeterministicCheck],
    ) -> None:
        """Guarantee the lane never emits a dangling evidence reference."""

        resolver = EvidenceResolver(
            manifest,
            run,
            trajectory,
            frozenset(item.path for item in facts.files),
        )
        for check in checks:
            for reference in check.evidence:
                try:
                    resolver.resolve(reference)
                except EvidenceResolutionError as error:  # pragma: no cover - bug guard
                    raise RuntimeError(
                        f"deterministic check {check.check_id} emitted dangling evidence: {error}"
                    ) from error
