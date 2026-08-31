"""Harbor trial import: bundle construction, report mapping, task preparation."""

import json
import shutil
from pathlib import Path

import pytest

from hy3_workbench.config import Settings
from hy3_workbench.contracts import Selection
from hy3_workbench.evidence_gate import EvidenceGate, parse_verifier_report
from hy3_workbench.harbor_importer import (
    HarborImporter,
    HarborImportError,
    inject_patch_dump,
    rewrite_dockerfile_from,
)
from hy3_workbench.storage import WorkbenchRepository
from hy3_workbench.workflow import JudgeUnavailableError, WorkbenchService

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_TRAJECTORY = PROJECT_ROOT / "data" / "fixtures" / "valid" / "trajectory.json"
DATA_DIR = Path(".local/test-day7-importer")

INSTANCE_ID = "django__django-99999"
F2P = ["tests/x/test_y.py::test_a"]
P2P = ["tests/x/test_y.py::test_b"]
TEST_PATCH = (
    "diff --git a/tests/x/test_y.py b/tests/x/test_y.py\n"
    "--- a/tests/x/test_y.py\n"
    "+++ b/tests/x/test_y.py\n"
    "@@ -1 +1,2 @@\n"
    " import unittest\n"
    "+EXTRA = True\n"
)
GOLD_PATCH = (
    "diff --git a/django/x.py b/django/x.py\n"
    "--- a/django/x.py\n"
    "+++ b/django/x.py\n"
    "@@ -1 +1 @@\n"
    "-a = 1\n"
    "+a = 2\n"
)


@pytest.fixture(autouse=True)
def clean_state():
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    yield
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


def make_row(**overrides) -> dict:
    row = {
        "repo": "django/django",
        "instance_id": INSTANCE_ID,
        "base_commit": "c" * 40,
        "patch": GOLD_PATCH,
        "test_patch": TEST_PATCH,
        "problem_statement": "The widget renders the wrong value.",
        "FAIL_TO_PASS": json.dumps(F2P),
        "PASS_TO_PASS": json.dumps(P2P),
        "difficulty": "<15 min fix",
        "version": "4.2",
    }
    row.update(overrides)
    return row


def official_report(
    *,
    f2p_pass=F2P,
    f2p_fail=(),
    p2p_pass=P2P,
    p2p_fail=(),
    resolved: bool | None = None,
) -> dict:
    if resolved is None:
        resolved = not f2p_fail and not p2p_fail
    return {
        INSTANCE_ID: {
            "patch_is_None": False,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": resolved,
            "tests_status": {
                "FAIL_TO_PASS": {"success": list(f2p_pass), "failure": list(f2p_fail)},
                "PASS_TO_PASS": {"success": list(p2p_pass), "failure": list(p2p_fail)},
                "FAIL_TO_FAIL": {"success": [], "failure": []},
                "PASS_TO_FAIL": {"success": [], "failure": []},
            },
        }
    }


def make_task_dir(tmp_path: Path, row: dict) -> Path:
    task_dir = tmp_path / "task"
    (task_dir / "tests").mkdir(parents=True)
    config = {
        "instance_id": row["instance_id"],
        "base_commit": row["base_commit"],
        "FAIL_TO_PASS": row["FAIL_TO_PASS"],
        "PASS_TO_PASS": row["PASS_TO_PASS"],
    }
    (task_dir / "tests" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (task_dir / "tests" / "test.sh").write_text(
        '#!/bin/bash\ncd /testbed\nuv run --with "swebench==4.0.3" parser.py\n',
        encoding="utf-8",
    )
    return task_dir


def make_trial(
    tmp_path: Path,
    *,
    session_id: str = "swb-trial-1",
    report: dict | None | str = "default",
    with_patch: bool = True,
    trajectory_bytes: bytes | None = None,
) -> Path:
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "verifier").mkdir(parents=True)

    if trajectory_bytes is None:
        trajectory = json.loads(FIXTURE_TRAJECTORY.read_text(encoding="utf-8"))
        trajectory["session_id"] = session_id
        trajectory_bytes = json.dumps(trajectory, indent=2).encode("utf-8")
    (trial / "agent" / "trajectory.json").write_bytes(trajectory_bytes)

    if with_patch:
        (trial / "verifier" / "patch.diff").write_text(GOLD_PATCH, encoding="utf-8")
    if report == "default":
        report = official_report()
    if report is not None:
        (trial / "verifier" / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (trial / "verifier" / "test-stdout.txt").write_text("test output\n", encoding="utf-8")
    (trial / "trial.log").write_text("trial log\n", encoding="utf-8")

    result = {
        "exception_info": None,
        "started_at": "2026-08-31T01:00:00Z",
        "finished_at": "2026-08-31T01:12:30Z",
        "agent_info": {"name": "mini-swe-agent", "version": "2.4.6", "model_info": None},
        "config": {
            "agent": {
                "name": "mini-swe-agent",
                "model_name": "openai/test-model",
                "kwargs": {},
            }
        },
    }
    (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (trial / "config.json").write_text(json.dumps({"trial_name": "t"}), encoding="utf-8")
    return trial


def build(tmp_path: Path, **kwargs) -> tuple:
    row = kwargs.pop("row", make_row())
    task_dir = kwargs.pop("task_dir", None) or make_task_dir(tmp_path, row)
    trial_dir = kwargs.pop("trial_dir", None) or make_trial(tmp_path)
    importer = HarborImporter(PROJECT_ROOT)
    built = importer.build_bundle(
        dataset_row=row,
        dataset_revision="rev-test-1",
        dataset_source_url="https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified",
        task_dir=task_dir,
        trial_dir=trial_dir,
        bundle_root=DATA_DIR / "bundles",
        selection=Selection(method="test", reason="importer test scenario"),
        harness_version="0.22.0",
        **kwargs,
    )
    bundle = PROJECT_ROOT / built.bundle_dir
    return built, bundle


def load_bundle_records(bundle: Path) -> tuple[dict, dict]:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    run = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    return manifest, run


def test_build_bundle_maps_trial_into_ready_evidence(tmp_path):
    built, bundle = build(tmp_path)
    assert built.run_id == "swb-trial-1"
    manifest, run = load_bundle_records(bundle)

    assert manifest["task_id"] == INSTANCE_ID
    assert manifest["standard_answer"]["fail_to_pass"] == F2P
    assert manifest["protected_paths"] == ["tests/x/test_y.py"]
    assert manifest["checker"] == {"adapter": "swebench-official-grading", "version": "4.0.3"}
    assert manifest["difficulty"]["label"] == "<15 min fix"
    assert manifest["source_pr_url"] == "https://github.com/django/django/pull/99999"
    assert manifest["reference_patch"]["visibility"] == "human_adjudication_only"

    assert run["run_id"] == "swb-trial-1"
    assert run["status"] == "completed"
    assert run["model"]["name"] == "openai/test-model"
    assert run["agent"] == {
        "name": "mini-swe-agent",
        "version": "2.4.6",
        "config_digest": run["agent"]["config_digest"],
    }
    assert run["dataset_adapter"] == "harbor-swebench-adapter-v1"
    assert run["verifier"]["status"] == "passed"

    from hy3_workbench.contracts import RunRecord, TaskManifest

    gate = EvidenceGate(PROJECT_ROOT)
    result = gate.assess(TaskManifest.model_validate(manifest), RunRecord.model_validate(run))
    assert result.status == "ready"
    assert result.outcome_status == "resolved"


def test_built_bundle_imports_through_the_workflow(tmp_path):
    built, _ = build(tmp_path)
    settings = Settings(
        _env_file=None,
        workbench_data_dir=DATA_DIR / "wb",
        results_dir=DATA_DIR / "results",
    )
    repository = WorkbenchRepository(
        PROJECT_ROOT / settings.workbench_data_dir / "workbench.sqlite3"
    )

    def no_judge():
        raise JudgeUnavailableError("import does not use the judge")

    service = WorkbenchService(PROJECT_ROOT, settings, repository, no_judge)
    stored = service.import_bundle(built.bundle_dir)
    assert stored.run.run_id == built.run_id
    assert stored.task_id == INSTANCE_ID


def test_failed_tests_map_to_failed_verifier_and_unresolved_outcome(tmp_path):
    trial = make_trial(tmp_path, report=official_report(p2p_pass=[], p2p_fail=P2P))
    _, bundle = build(tmp_path, trial_dir=trial)
    manifest, run = load_bundle_records(bundle)
    assert run["verifier"]["status"] == "failed"

    from hy3_workbench.contracts import RunRecord, TaskManifest

    result = EvidenceGate(PROJECT_ROOT).assess(
        TaskManifest.model_validate(manifest), RunRecord.model_validate(run)
    )
    assert result.status == "ready"
    assert result.outcome_status == "unresolved"


def test_missing_report_is_recorded_as_inconclusive(tmp_path):
    trial = make_trial(tmp_path, report=None)
    _, bundle = build(tmp_path, trial_dir=trial)
    _, run = load_bundle_records(bundle)
    assert run["verifier"]["status"] == "inconclusive"
    assert "no official verifier report" in run["verifier"]["exclusion_reason"]


def test_ungradeable_report_is_recorded_as_inconclusive(tmp_path):
    ungradeable = {INSTANCE_ID: {"patch_exists": True, "resolved": False}}
    trial = make_trial(tmp_path, report=ungradeable)
    _, bundle = build(tmp_path, trial_dir=trial)
    _, run = load_bundle_records(bundle)
    assert run["verifier"]["status"] == "inconclusive"
    assert "not gradeable" in run["verifier"]["exclusion_reason"]


def test_task_dir_contract_mismatch_is_rejected(tmp_path):
    row = make_row()
    task_dir = make_task_dir(tmp_path, make_row(base_commit="d" * 40))
    with pytest.raises(HarborImportError, match="base_commit does not match"):
        build(tmp_path, row=row, task_dir=task_dir)


def test_contradictory_resolved_flag_is_rejected(tmp_path):
    trial = make_trial(tmp_path, report=official_report(p2p_pass=[], p2p_fail=P2P, resolved=True))
    with pytest.raises(HarborImportError, match="contradicts its per-test results"):
        build(tmp_path, trial_dir=trial)


def test_report_coverage_mismatch_is_rejected(tmp_path):
    trial = make_trial(tmp_path, report=official_report(p2p_pass=[], p2p_fail=[]))
    with pytest.raises(HarborImportError, match="does not cover the declared"):
        build(tmp_path, trial_dir=trial)


def test_invalid_trajectory_is_rejected(tmp_path):
    trial = make_trial(tmp_path, trajectory_bytes=b'{"schema_version": "ATIF-v1.7"}')
    with pytest.raises(HarborImportError, match="trajectory failed validation"):
        build(tmp_path, trial_dir=trial)


def test_unusable_session_id_is_rejected(tmp_path):
    trial = make_trial(tmp_path, session_id="not a valid id!")
    with pytest.raises(HarborImportError, match="not a usable run identifier"):
        build(tmp_path, trial_dir=trial)


def test_missing_patch_artifact_is_rejected(tmp_path):
    trial = make_trial(tmp_path, with_patch=False)
    with pytest.raises(HarborImportError, match="patch.diff"):
        build(tmp_path, trial_dir=trial)


def test_existing_bundle_directory_is_refused(tmp_path):
    target = PROJECT_ROOT / DATA_DIR / "bundles" / "swb-trial-1"
    target.mkdir(parents=True)
    (target / "stale.txt").write_text("stale", encoding="utf-8")
    with pytest.raises(HarborImportError, match="already exists"):
        build(tmp_path)


# Report parser --------------------------------------------------------------


def test_parse_verifier_report_accepts_fixture_format():
    payload = {
        "schema_version": "fixture-verifier-report-v1",
        "outcome_status": "resolved",
        "fail_to_pass": [{"name": "t::a", "status": "passed"}],
        "pass_to_pass": [],
    }
    report = parse_verifier_report(payload)
    assert report.schema_version == "fixture-verifier-report-v1"
    assert report.fail_to_pass[0].name == "t::a"


def test_parse_verifier_report_maps_official_format():
    report = parse_verifier_report(official_report(p2p_pass=[], p2p_fail=P2P))
    assert report.schema_version == "swebench-report-adapter-v1"
    assert report.outcome_status == "unresolved"
    assert {(r.name, r.status) for r in report.fail_to_pass} == {(F2P[0], "passed")}
    assert {(r.name, r.status) for r in report.pass_to_pass} == {(P2P[0], "failed")}


def test_parse_verifier_report_rejects_contradictory_test_entries():
    payload = official_report()
    payload[INSTANCE_ID]["tests_status"]["FAIL_TO_PASS"]["failure"] = list(F2P)
    with pytest.raises(ValueError, match="contradictory statuses"):
        parse_verifier_report(payload)


def test_parse_verifier_report_rejects_report_without_tests_status():
    with pytest.raises(ValueError, match="no gradeable tests_status"):
        parse_verifier_report({INSTANCE_ID: {"resolved": False}})


def test_parse_verifier_report_rejects_multi_instance_payloads():
    payload = {**official_report(), "other__instance-1": {}}
    with pytest.raises(ValueError, match="exactly one instance id"):
        parse_verifier_report(payload)


# Task preparation -----------------------------------------------------------

DOCKERFILE = (
    "# comment\n"
    "# FROM python:3.9-slim-bookworm\n"
    "FROM swebench/sweb.eval.x86_64.django_1776_django-99999:latest\n"
    "RUN mkdir -p /logs\n"
)


def test_rewrite_dockerfile_from_swaps_the_single_from_line():
    rewritten, original = rewrite_dockerfile_from(DOCKERFILE, "sweb.eval.arm64.test:latest")
    assert original == "swebench/sweb.eval.x86_64.django_1776_django-99999:latest"
    assert "FROM sweb.eval.arm64.test:latest\n" in rewritten
    assert "# FROM python:3.9-slim-bookworm" in rewritten
    assert "x86_64" not in rewritten.replace("# FROM python", "")


def test_rewrite_dockerfile_from_requires_exactly_one_from():
    with pytest.raises(HarborImportError, match="found 2"):
        rewrite_dockerfile_from(DOCKERFILE + "FROM other:latest\n", "img")
    with pytest.raises(HarborImportError, match="found 0"):
        rewrite_dockerfile_from("RUN true\n", "img")


def test_inject_patch_dump_inserts_after_entering_testbed():
    script = "#!/bin/bash\n        set -x\n        cd /testbed\n        run-tests\n"
    injected = inject_patch_dump(script)
    lines = injected.splitlines()
    anchor = lines.index("        cd /testbed")
    assert lines[anchor + 1].lstrip().startswith("# hy3-workbench")
    assert "git diff HEAD > /logs/verifier/patch.diff" in injected
    assert injected.index("patch.diff") < injected.index("run-tests")


def test_inject_patch_dump_refuses_double_injection_and_missing_anchor():
    script = "#!/bin/bash\ncd /testbed\n"
    injected = inject_patch_dump(script)
    with pytest.raises(HarborImportError, match="already contains"):
        inject_patch_dump(injected)
    with pytest.raises(HarborImportError, match="no 'cd /testbed'"):
        inject_patch_dump("#!/bin/bash\ncd /other\n")
