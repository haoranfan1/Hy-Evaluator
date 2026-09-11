"""The committed real-run bundles under data/runs are complete, verifiable evidence."""

import json
from pathlib import Path

import pytest
from harbor.utils.trajectory_validator import TrajectoryValidator

from hy3_workbench.artifact_store import ArtifactStore
from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evidence_gate import EvidenceGate

PROJECT_ROOT = Path(__file__).parents[1]
RUNS_ROOT = PROJECT_ROOT / "data" / "runs"
BUNDLES = sorted(p.name for p in RUNS_ROOT.iterdir() if p.is_dir())
DAY8_SLICE = json.loads(
    (PROJECT_ROOT / "data/evaluation-slices/day8-slice-v1.json").read_text(encoding="utf-8")
)


def load(name: str) -> tuple[TaskManifest, RunRecord]:
    root = RUNS_ROOT / name
    return (
        TaskManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
        RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8")),
    )


def test_every_day8_slice_task_has_a_committed_run() -> None:
    selected = {
        item["instance_id"]
        for stratum in DAY8_SLICE["strata"].values()
        for item in stratum["selected"]
    }
    committed_tasks = {load(name)[0].task_id for name in BUNDLES}

    assert selected <= committed_tasks
    assert len(BUNDLES) == 12  # 8 day8 + 1 integration + 3 guardrail reruns


@pytest.mark.parametrize("name", BUNDLES)
def test_bundle_identity_and_gate(name: str) -> None:
    manifest, run = load(name)
    assert run.run_id == name
    assert run.task_id == manifest.task_id
    assert manifest.standard_answer.fail_to_pass, "the standard answer must be declared"

    # The Harbor trial log (run.log) was not retained in the public copy of these
    # bundles; the record says so honestly instead of pointing at a missing file.
    assert run.verifier.run_log is None

    store = ArtifactStore(PROJECT_ROOT)
    for reference in (
        run.trajectory,
        run.patch,
        run.verifier.report,
        run.verifier.test_output,
        manifest.reference_patch.artifact if manifest.reference_patch else None,
    ):
        assert reference is not None
        assert not Path(reference.path).is_absolute()
        assert reference.path.startswith(f"data/runs/{name}/")
        store.verify(reference)

    result = EvidenceGate(PROJECT_ROOT).assess(manifest, run)
    assert result.status == "ready"
    assert result.outcome_status == "resolved"


@pytest.mark.parametrize("name", BUNDLES)
def test_bundle_trajectory_is_valid_atif(name: str) -> None:
    validator = TrajectoryValidator()

    assert validator.validate(RUNS_ROOT / name / "trajectory.json"), validator.get_errors()


def test_bundles_import_into_a_fresh_workbench() -> None:
    from test_semantic_reviewer import FakeJudge
    from test_storage import make_service

    service = make_service(FakeJudge([]))
    for name in BUNDLES:
        stored = service.import_bundle(f"data/runs/{name}")
        assert stored.run.run_id == name
    assert len(service.repository.list_runs()) == len(BUNDLES)


def test_bundles_contain_no_machine_paths_or_secret_fields() -> None:
    for path in RUNS_ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        assert "/home/" not in text, path
        assert "/users/" not in text, path
        assert "api_key" not in text, path
        assert "authorization:" not in text, path
        assert "bearer " not in text, path
        assert ".local/" not in text, path
