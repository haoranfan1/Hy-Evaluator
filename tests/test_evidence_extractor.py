import hashlib
import json
import shutil
from pathlib import Path

import pytest
from harbor.models.trajectories import (
    Agent,
    Observation,
    ObservationResult,
    Step,
    ToolCall,
    Trajectory,
)

from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evidence_extractor import (
    EvidenceExtractor,
    EvidenceResolver,
    check_atif_structure,
    check_command_failures,
    check_final_claim,
    check_patch_scope,
    check_protected_paths,
    classify_verifier_logs,
    parse_patch,
)

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"


def load_bundle(name: str) -> tuple[TaskManifest, RunRecord]:
    root = FIXTURE_ROOT / name
    return (
        TaskManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
        RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8")),
    )


def make_trajectory(steps: list[Step], session_id: str = "run-x") -> Trajectory:
    return Trajectory(
        schema_version="ATIF-v1.7",
        session_id=session_id,
        agent=Agent(name="mini-swe-agent", version="2.4.6"),
        steps=steps,
    )


def agent_step(
    step_id: int,
    message: str,
    command: str | None = None,
    observation: str | None = None,
    tool_call_id: str | None = None,
) -> Step:
    call_id = tool_call_id or f"call-{step_id}"
    tool_calls = (
        [ToolCall(tool_call_id=call_id, function_name="bash", arguments={"command": command})]
        if command is not None
        else None
    )
    result = (
        Observation(results=[ObservationResult(source_call_id=call_id, content=observation)])
        if observation is not None
        else None
    )
    return Step(
        step_id=step_id,
        source="agent",
        message=message,
        tool_calls=tool_calls,
        observation=result,
    )


class TestFixtureBundles:
    @pytest.mark.parametrize(
        ("name", "status", "outcome"),
        [
            ("valid", "ready", "resolved"),
            ("invalid-first-error", "ready", "unresolved"),
            ("inconclusive-missing-evidence", "inconclusive", "inconclusive"),
        ],
    )
    def test_outcomes_are_reproducible(self, name: str, status: str, outcome: str) -> None:
        manifest, run = load_bundle(name)
        extractor = EvidenceExtractor(PROJECT_ROOT)

        first = extractor.extract(manifest, run)
        second = extractor.extract(manifest, run)

        assert first.status == status
        assert first.outcome_status == outcome
        assert [c.model_dump(exclude={"created_at"}) for c in first.checks] == [
            c.model_dump(exclude={"created_at"}) for c in second.checks
        ]
        assert first.exclusions == second.exclusions

    def test_valid_bundle_has_no_failed_checks_or_hard_flags(self) -> None:
        manifest, run = load_bundle("valid")

        result = EvidenceExtractor(PROJECT_ROOT).extract(manifest, run)

        assert not [c.check_id for c in result.checks if c.status == "fail"]
        assert not [c for c in result.checks if c.hard_process_failure]
        assert result.exclusions == []
        by_id = {c.check_id: c for c in result.checks}
        assert by_id["check-test-fail-to-pass-1"].status == "pass"
        assert by_id["check-final-claim"].status == "pass"

    def test_invalid_bundle_records_failing_test_and_unsupported_claim(self) -> None:
        manifest, run = load_bundle("invalid-first-error")

        result = EvidenceExtractor(PROJECT_ROOT).extract(manifest, run)

        by_id = {c.check_id: c for c in result.checks}
        assert by_id["check-test-fail-to-pass-1"].status == "fail"
        assert by_id["check-test-pass-to-pass-1"].status == "pass"
        assert by_id["check-final-claim"].status == "warning"
        assert "unsupported" in by_id["check-final-claim"].summary
        assert not [c for c in result.checks if c.hard_process_failure]
        patch_files = {e.file for e in by_id["check-patch-scope"].evidence if e.kind == "patch"}
        assert patch_files == {"src/calculator.py"}

    def test_inconclusive_bundle_is_excluded_as_infrastructure(self) -> None:
        manifest, run = load_bundle("inconclusive-missing-evidence")

        result = EvidenceExtractor(PROJECT_ROOT).extract(manifest, run)

        by_id = {c.check_id: c for c in result.checks}
        assert by_id["check-verifier-report"].status == "fail"
        assert by_id["check-verifier-infrastructure"].status == "unknown"
        assert any("infrastructure" in reason for reason in result.exclusions)

    @pytest.mark.parametrize(
        "name", ["valid", "invalid-first-error", "inconclusive-missing-evidence"]
    )
    def test_every_emitted_evidence_reference_resolves(self, name: str) -> None:
        manifest, run = load_bundle(name)
        extractor = EvidenceExtractor(PROJECT_ROOT)
        trajectory = extractor.atif.load(PROJECT_ROOT / run.trajectory.path)
        patch_text = (PROJECT_ROOT / run.patch.path).read_text(encoding="utf-8")
        resolver = EvidenceResolver(
            manifest,
            run,
            trajectory,
            frozenset(item.path for item in parse_patch(patch_text).files),
        )

        result = extractor.extract(manifest, run)

        for check in result.checks:
            for reference in check.evidence:
                resolver.resolve(reference)


def copy_valid_bundle(
    tmp_path: Path,
    mutate_trajectory=None,
    mutate_run=None,
) -> tuple[TaskManifest, RunRecord, Path]:
    """Copy the valid bundle into an isolated root and apply targeted corruption."""

    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURE_ROOT / "valid", bundle)

    if mutate_trajectory is not None:
        trajectory_path = bundle / "trajectory.json"
        data = json.loads(trajectory_path.read_text(encoding="utf-8"))
        mutate_trajectory(data)
        trajectory_path.write_text(json.dumps(data), encoding="utf-8")

    manifest = TaskManifest.model_validate_json(
        (bundle / "manifest.json").read_text(encoding="utf-8")
    )
    run_data = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    if mutate_run is not None:
        mutate_run(run_data, bundle)
    artifacts = [run_data["trajectory"], run_data["patch"], *run_data["verifier"].values()]
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        path = bundle / Path(artifact["path"]).name
        artifact["path"] = f"bundle/{path.name}"
        artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        artifact["byte_size"] = path.stat().st_size
    return manifest, RunRecord.model_validate(run_data), tmp_path


class TestAtifStructure:
    def test_sequential_steps_pass(self) -> None:
        trajectory = make_trajectory(
            [agent_step(1, "look", command="ls", observation="ok"), agent_step(2, "done")]
        )

        assert check_atif_structure(trajectory, "run-x").status == "pass"

    def test_session_mismatch_fails(self) -> None:
        trajectory = make_trajectory([agent_step(1, "done")], session_id="other-run")

        assert check_atif_structure(trajectory, "run-x").status == "fail"

    def test_duplicate_tool_call_ids_fail(self) -> None:
        step = Step(
            step_id=1,
            source="agent",
            message="look",
            tool_calls=[
                ToolCall(tool_call_id="call-a", function_name="bash", arguments={}),
                ToolCall(tool_call_id="call-a", function_name="bash", arguments={}),
            ],
        )

        check = check_atif_structure(make_trajectory([step]), "run-x")

        assert check.status == "fail"
        assert "duplicate tool_call_ids" in check.summary

    @pytest.mark.parametrize(
        ("label", "mutate"),
        [
            (
                "non-sequential step ids",
                lambda data: data["steps"][-1].__setitem__("step_id", 99),
            ),
            (
                "observation references unknown tool call",
                lambda data: data["steps"][1]["observation"]["results"][0].__setitem__(
                    "source_call_id", "call-missing"
                ),
            ),
        ],
    )
    def test_malformed_atif_forces_inconclusive_without_model_call(
        self, tmp_path: Path, label: str, mutate
    ) -> None:
        manifest, run, root = copy_valid_bundle(tmp_path, mutate_trajectory=mutate)

        result = EvidenceExtractor(root).extract(manifest, run)

        assert result.status == "inconclusive"
        assert result.outcome_status == "inconclusive"
        assert any("invalid ATIF trajectory" in reason for reason in result.exclusions)
        by_id = {c.check_id: c for c in result.checks}
        assert by_id["check-atif-structure"].status == "fail"


class TestPatchFacts:
    def test_parse_counts_files_and_lines(self) -> None:
        text = (PROJECT_ROOT / "data/fixtures/valid/patch.diff").read_text(encoding="utf-8")

        facts = parse_patch(text)

        assert [item.path for item in facts.files] == ["src/calculator.py"]
        assert facts.files[0].added_lines == 1
        assert facts.files[0].removed_lines == 1
        assert not facts.is_empty

    def test_empty_patch_warns(self) -> None:
        checks = check_patch_scope(parse_patch(""))

        by_id = {c.check_id: c for c in checks}
        assert by_id["check-patch-scope"].status == "warning"
        assert "empty" in by_id["check-patch-scope"].summary

    def test_broad_patch_warns(self) -> None:
        sections = []
        for index in range(7):
            sections.append(
                f"diff --git a/src/mod_{index}.py b/src/mod_{index}.py\n"
                f"--- a/src/mod_{index}.py\n+++ b/src/mod_{index}.py\n"
                "@@ -1,1 +1,1 @@\n-old\n+new\n"
            )

        checks = check_patch_scope(parse_patch("".join(sections)))

        by_id = {c.check_id: c for c in checks}
        assert by_id["check-patch-scope"].status == "warning"
        assert "exceeds" in by_id["check-patch-scope"].summary

    def test_sensitive_files_warn_without_failing(self) -> None:
        text = (
            "diff --git a/tests/test_x.py b/tests/test_x.py\n"
            "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n@@ -1,1 +1,1 @@\n-a\n+b\n"
            "diff --git a/uv.lock b/uv.lock\n"
            "--- a/uv.lock\n+++ b/uv.lock\n@@ -1,1 +1,1 @@\n-a\n+b\n"
            "diff --git a/dist/bundle.min.js b/dist/bundle.min.js\n"
            "--- a/dist/bundle.min.js\n+++ b/dist/bundle.min.js\n@@ -1,1 +1,1 @@\n-a\n+b\n"
        )

        checks = check_patch_scope(parse_patch(text))

        by_id = {c.check_id: c for c in checks}
        assert by_id["check-patch-tests"].status == "warning"
        assert by_id["check-patch-lockfiles"].status == "warning"
        assert by_id["check-patch-generated"].status == "warning"
        assert all(c.status != "fail" and not c.hard_process_failure for c in checks)


class TestProtectedPaths:
    def test_patch_modification_is_a_hard_failure(self) -> None:
        text = (
            "diff --git a/grader_tests/answers.json b/grader_tests/answers.json\n"
            "--- a/grader_tests/answers.json\n+++ b/grader_tests/answers.json\n"
            "@@ -1,1 +1,1 @@\n-a\n+b\n"
        )

        check = check_protected_paths(["grader_tests"], parse_patch(text), None)

        assert check.status == "fail"
        assert check.hard_process_failure is True

    def test_command_access_is_a_hard_failure(self) -> None:
        trajectory = make_trajectory(
            [agent_step(1, "peek", command="cat grader_tests/answers.json", observation="{}")]
        )

        check = check_protected_paths(["grader_tests"], parse_patch(""), trajectory)

        assert check.status == "fail"
        assert check.hard_process_failure is True
        assert any(e.kind == "atif_step" and e.step_id == 1 for e in check.evidence)

    def test_clean_bundle_passes(self) -> None:
        trajectory = make_trajectory(
            [agent_step(1, "test", command="pytest -q tests/test_x.py", observation="1 passed")]
        )

        check = check_protected_paths(["grader_tests"], parse_patch(""), trajectory)

        assert check.status == "pass"
        assert check.hard_process_failure is False


class TestCommandFailures:
    def test_failure_markers_become_advisory_warnings(self) -> None:
        trajectory = make_trajectory(
            [
                agent_step(
                    1, "try", command="python x.py", observation="Traceback (most recent call last)"
                ),
                agent_step(2, "retry", command="pytest -q", observation="2 failed, 1 passed"),
                agent_step(3, "ok", command="pytest -q", observation="3 passed"),
            ]
        )

        checks = check_command_failures(trajectory)

        assert [c.check_id for c in checks] == [
            "check-command-failure-1-1",
            "check-command-failure-2-1",
        ]
        assert all(c.status == "warning" and not c.hard_process_failure for c in checks)

    def test_clean_observations_produce_no_checks(self) -> None:
        trajectory = make_trajectory(
            [agent_step(1, "ok", command="pytest -q", observation="4 passed in 0.1s")]
        )

        assert check_command_failures(trajectory) == []


class TestFinalClaim:
    F2P = ["tests/test_normalize.py::test_zero_is_preserved"]

    def test_supported_claim_passes(self) -> None:
        trajectory = make_trajectory(
            [
                agent_step(
                    1, "verify", command="pytest -q tests/test_normalize.py", observation="1 passed"
                ),
                agent_step(2, "Implemented the fix; the required test passes."),
            ]
        )

        check = check_final_claim(trajectory, self.F2P, "resolved")

        assert check is not None
        assert check.status == "pass"

    def test_unsupported_claim_warns(self) -> None:
        trajectory = make_trajectory(
            [
                agent_step(
                    1, "run other", command="pytest -q tests/test_other.py", observation="1 passed"
                ),
                agent_step(2, "Implemented and verified the change."),
            ]
        )

        check = check_final_claim(trajectory, self.F2P, "unresolved")

        assert check is not None
        assert check.status == "warning"
        assert "unsupported" in check.summary

    def test_claim_contradicting_official_outcome_warns(self) -> None:
        trajectory = make_trajectory(
            [
                agent_step(
                    1, "verify", command="pytest -q tests/test_normalize.py", observation="1 passed"
                ),
                agent_step(2, "Fixed; everything passes."),
            ]
        )

        check = check_final_claim(trajectory, self.F2P, "unresolved")

        assert check is not None
        assert check.status == "warning"
        assert "unresolved" in check.summary

    def test_no_claim_passes(self) -> None:
        trajectory = make_trajectory([agent_step(1, "Stopping here; unable to finish.")])

        check = check_final_claim(trajectory, self.F2P, "unresolved")

        assert check is not None
        assert check.status == "pass"


class TestUngradeableClassification:
    def test_patch_application_failure_is_agent_caused(self) -> None:
        assert (
            classify_verifier_logs(["error: patch does not apply", "run aborted"])
            == "agent_patch_failure"
        )

    def test_environment_failure_is_infrastructure(self) -> None:
        assert (
            classify_verifier_logs(["worker connection lost during test execution"])
            == "infrastructure"
        )

    def test_ambiguous_logs_stay_unclassified(self) -> None:
        assert classify_verifier_logs(["run started", "run stopped"]) is None

    def test_missing_report_with_apply_failure_log_is_agent_caused_unresolved(
        self, tmp_path: Path
    ) -> None:
        def drop_report_after_apply_failure(run_data: dict, bundle: Path) -> None:
            (bundle / "run.log").write_text(
                "error: patch does not apply\nrun aborted before tests\n", encoding="utf-8"
            )
            run_data["verifier"]["report"] = None
            run_data["verifier"]["test_output"] = None
            run_data["verifier"]["status"] = "failed"

        manifest, run, root = copy_valid_bundle(
            tmp_path, mutate_run=drop_report_after_apply_failure
        )

        result = EvidenceExtractor(root).extract(manifest, run)

        assert result.status == "ready"
        assert result.outcome_status == "unresolved"
        by_id = {c.check_id: c for c in result.checks}
        assert by_id["check-patch-application"].status == "fail"
        assert "agent-caused" in by_id["check-patch-application"].summary
