import json
from pathlib import Path

import pytest
from harbor.utils.trajectory_validator import TrajectoryValidator

from hy3_workbench.artifact_store import ArtifactStore
from hy3_workbench.atif import AtifAdapter
from hy3_workbench.contracts import (
    AtifStepEvidence,
    EvaluationResult,
    HumanReview,
    RunRecord,
    TaskManifest,
)
from hy3_workbench.evidence_gate import EvidenceGate

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"


def load_bundle(name: str) -> tuple[TaskManifest, RunRecord, EvaluationResult, HumanReview]:
    root = FIXTURE_ROOT / name
    return (
        TaskManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
        RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8")),
        EvaluationResult.model_validate_json((root / "expected.json").read_text(encoding="utf-8")),
        HumanReview.model_validate_json((root / "human-review.json").read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize(
    ("name", "gate_status", "outcome_status"),
    [
        ("valid", "ready", "resolved"),
        ("invalid-first-error", "ready", "unresolved"),
        ("invalid-relative-path", "ready", "resolved"),
        ("inconclusive-missing-evidence", "inconclusive", "inconclusive"),
    ],
)
def test_fixture_identity_and_evidence_gate(
    name: str,
    gate_status: str,
    outcome_status: str,
) -> None:
    manifest, run, expected, review = load_bundle(name)

    result = EvidenceGate(PROJECT_ROOT).assess(manifest, run)

    assert result.status == gate_status
    assert result.outcome_status == outcome_status
    assert expected.outcome_status == outcome_status
    assert expected.run_id == run.run_id
    assert review.evaluation_id == expected.evaluation_id


@pytest.mark.parametrize("name", ["valid", "invalid-first-error", "invalid-relative-path"])
def test_harbor_accepts_gradeable_atif_fixtures(name: str) -> None:
    validator = TrajectoryValidator()

    assert validator.validate(FIXTURE_ROOT / name / "trajectory.json"), validator.get_errors()


def test_missing_verifier_evidence_is_inconclusive() -> None:
    manifest, run, _, _ = load_bundle("inconclusive-missing-evidence")

    result = EvidenceGate(PROJECT_ROOT).assess(manifest, run)

    assert result.status == "inconclusive"
    assert any("malformed or incomplete" in reason for reason in result.reasons)


@pytest.mark.parametrize(
    "name",
    ["valid", "invalid-first-error", "invalid-relative-path", "inconclusive-missing-evidence"],
)
def test_fixture_artifacts_are_project_relative_and_match_hashes(name: str) -> None:
    _, run, _, _ = load_bundle(name)
    store = ArtifactStore(PROJECT_ROOT)
    references = [
        run.trajectory,
        run.patch,
        run.verifier.report,
        run.verifier.test_output,
        run.verifier.run_log,
    ]

    for reference in references:
        assert reference is not None
        assert not Path(reference.path).is_absolute()
        store.verify(reference)


def test_invalid_oracle_references_real_first_error_evidence() -> None:
    _, run, expected, review = load_bundle("invalid-first-error")
    trajectory = AtifAdapter().load(PROJECT_ROOT / run.trajectory.path)
    first_error = expected.first_error

    assert first_error.step_id == 3
    assert first_error.tool_call_id == "call-edit-1"
    assert review.initial_label.first_error_step_id == 3
    AtifAdapter.validate_step_evidence(
        trajectory,
        AtifStepEvidence(
            kind="atif_step",
            step_id=first_error.step_id,
            tool_call_id=first_error.tool_call_id,
        ),
    )


def test_relative_path_oracle_references_real_first_error_evidence() -> None:
    _, run, expected, review = load_bundle("invalid-relative-path")
    trajectory = AtifAdapter().load(PROJECT_ROOT / run.trajectory.path)
    first_error = expected.first_error

    assert expected.outcome_status == "resolved"
    assert expected.process_status == "invalid"
    assert expected.correct_result_invalid_process is True
    assert first_error.step_id == 4
    assert first_error.tool_call_id == "call-edit-1"
    assert review.initial_label.first_error_step_id == 4
    AtifAdapter.validate_step_evidence(
        trajectory,
        AtifStepEvidence(
            kind="atif_step",
            step_id=first_error.step_id,
            tool_call_id=first_error.tool_call_id,
        ),
    )


def test_fixtures_contain_no_absolute_machine_paths_or_secret_fields() -> None:
    for path in FIXTURE_ROOT.rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(payload)
        assert "/home/" not in serialized
        assert "/tmp/" not in serialized
        assert "api_key" not in serialized.lower()
        assert "authorization" not in serialized.lower()
