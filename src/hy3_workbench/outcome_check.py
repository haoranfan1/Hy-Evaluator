"""Final-answer check over a recorded run bundle.

Re-applies a task's behavioral-test contract — the standard answer: the declared
FAIL_TO_PASS and PASS_TO_PASS tests — to the official verifier report stored in the
bundle and reports ``resolved``, ``unresolved``, or ``inconclusive``. Grading itself
happens inside the SWE-bench harness that Harbor's verifier runs in the task
container; this module makes that result re-checkable from the committed evidence
without a container, and it never guesses: a report that is missing, fails identity
verification, does not cover the declared tests, or contradicts itself is
``inconclusive`` with the reason recorded.

Exit codes: 0 resolved · 2 unresolved · 3 inconclusive · 4 bundle unreadable.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore
from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evidence_gate import VerifierTestResult, parse_verifier_report

EXIT_RESOLVED = 0
EXIT_UNRESOLVED = 2
EXIT_INCONCLUSIVE = 3
EXIT_UNREADABLE = 4

_STATUS_EXIT = {
    "resolved": EXIT_RESOLVED,
    "unresolved": EXIT_UNRESOLVED,
    "inconclusive": EXIT_INCONCLUSIVE,
}


class BundleUnreadableError(Exception):
    """The bundle directory or its manifest/run records cannot be read."""


@dataclass(frozen=True)
class TestOutcome:
    name: str
    status: str  # passed | failed | missing


@dataclass(frozen=True)
class OutcomeCheck:
    bundle_dir: str
    run_id: str
    task_id: str
    status: str  # resolved | unresolved | inconclusive
    reasons: list[str]
    fail_to_pass: list[TestOutcome]
    pass_to_pass: list[TestOutcome]

    @property
    def exit_code(self) -> int:
        return _STATUS_EXIT[self.status]

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["exit_code"] = self.exit_code
        return payload


def _apply_contract(
    declared: Sequence[str], results: Sequence[VerifierTestResult]
) -> list[TestOutcome]:
    observed = {result.name: result.status for result in results}
    return [TestOutcome(name=name, status=observed.get(name, "missing")) for name in declared]


def check_bundle(project_root: Path, bundle_dir: str) -> OutcomeCheck:
    """Check one bundle's final answer against its declared behavioral contract."""

    root = project_root / bundle_dir
    try:
        manifest = TaskManifest.model_validate_json(
            (root / "manifest.json").read_text(encoding="utf-8")
        )
        run = RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as error:
        raise BundleUnreadableError(f"{bundle_dir}: {error}") from error

    declared_fail_to_pass = list(manifest.standard_answer.fail_to_pass)
    declared_pass_to_pass = list(manifest.standard_answer.pass_to_pass)
    reasons: list[str] = []
    report = None
    reference = run.verifier.report
    if reference is None:
        reasons.append("no verifier report artifact is recorded")
    else:
        try:
            ArtifactStore(project_root).verify(reference)
            payload = json.loads((project_root / reference.path).read_text(encoding="utf-8"))
            report = parse_verifier_report(payload)
        except ArtifactIntegrityError as error:
            reasons.append(f"verifier report failed identity verification: {error}")
        except (OSError, ValueError, ValidationError) as error:
            reasons.append(f"verifier report is malformed or incomplete: {error}")

    fail_to_pass = _apply_contract(declared_fail_to_pass, report.fail_to_pass if report else [])
    pass_to_pass = _apply_contract(declared_pass_to_pass, report.pass_to_pass if report else [])
    status = "inconclusive"
    if report is not None:
        missing = [t.name for t in [*fail_to_pass, *pass_to_pass] if t.status == "missing"]
        declared = set(declared_fail_to_pass) | set(declared_pass_to_pass)
        undeclared = [
            r.name for r in [*report.fail_to_pass, *report.pass_to_pass] if r.name not in declared
        ]
        if missing:
            reasons.append(f"declared tests absent from the verifier report: {', '.join(missing)}")
        if undeclared:
            reasons.append(f"verifier report lists undeclared tests: {', '.join(undeclared)}")
        if not missing and not undeclared:
            derived = (
                "resolved"
                if all(t.status == "passed" for t in [*fail_to_pass, *pass_to_pass])
                else "unresolved"
            )
            if report.outcome_status != derived:
                reasons.append(
                    f"report outcome {report.outcome_status} contradicts its own test results"
                )
            expected = "passed" if derived == "resolved" else "failed"
            if run.verifier.status != expected:
                reasons.append(f"run verifier status {run.verifier.status} contradicts the report")
            if not reasons:
                status = derived

    return OutcomeCheck(
        bundle_dir=bundle_dir,
        run_id=run.run_id,
        task_id=manifest.task_id,
        status=status,
        reasons=reasons,
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
    )


def _summarize(check: OutcomeCheck) -> str:
    def passed(tests: list[TestOutcome]) -> str:
        return f"{sum(t.status == 'passed' for t in tests)}/{len(tests)}"

    line = (
        f"{check.run_id}: {check.status}  FAIL_TO_PASS {passed(check.fail_to_pass)}  "
        f"PASS_TO_PASS {passed(check.pass_to_pass)}"
    )
    if check.reasons:
        # Keep the one-line summary one line; full reasons are in --json output.
        line += "  (" + "; ".join(r.splitlines()[0] for r in check.reasons) + ")"
    return line


def main(argv: Sequence[str] | None = None, *, out: Callable[[str], None] = print) -> int:
    """CLI entry point: check bundles and return the worst exit code seen."""

    parser = argparse.ArgumentParser(
        description=(
            "Re-apply each bundle's declared FAIL_TO_PASS / PASS_TO_PASS contract to its "
            "official verifier report and report resolved / unresolved / inconclusive."
        )
    )
    parser.add_argument("bundles", nargs="*", help="project-relative bundle directories")
    parser.add_argument("--all", metavar="DIR", help="check every bundle directory under DIR")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    project_root = Path.cwd().resolve(strict=True)
    bundle_dirs = list(args.bundles)
    if args.all:
        parent = project_root / args.all
        bundle_dirs.extend(
            (Path(args.all) / child.name).as_posix()
            for child in sorted(parent.iterdir())
            if (child / "run.json").is_file()
        )
    if not bundle_dirs:
        parser.error("give at least one bundle directory or --all DIR")

    worst = EXIT_RESOLVED
    results: list[dict] = []
    for bundle_dir in bundle_dirs:
        try:
            check = check_bundle(project_root, bundle_dir)
        except BundleUnreadableError as error:
            worst = max(worst, EXIT_UNREADABLE)
            if args.json:
                results.append(
                    {"bundle_dir": bundle_dir, "status": "unreadable", "error": str(error)}
                )
            else:
                out(f"{bundle_dir}: unreadable ({error})")
            continue
        worst = max(worst, check.exit_code)
        if args.json:
            results.append(check.to_json())
        else:
            out(_summarize(check))
    if args.json:
        out(json.dumps(results, indent=2, sort_keys=True))
    return worst
