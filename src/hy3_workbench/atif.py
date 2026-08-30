"""Thin adapter around Harbor's pinned ATIF v1.7 trajectory model."""

from __future__ import annotations

from pathlib import Path

from harbor.models.trajectories import Trajectory
from harbor.utils.trajectory_validator import TrajectoryValidator

from hy3_workbench.contracts import AtifStepEvidence


class AtifValidationError(ValueError):
    """ATIF validation failed before semantic evaluation could run."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


class AtifAdapter:
    """Load ATIF with Harbor and expose stable evidence relationships."""

    supported_schema_version = "ATIF-v1.7"

    def load(self, path: Path) -> Trajectory:
        validator = TrajectoryValidator()
        if not validator.validate(path):
            raise AtifValidationError(validator.get_errors())

        trajectory = Trajectory.model_validate_json(path.read_text(encoding="utf-8"))
        if trajectory.schema_version != self.supported_schema_version:
            raise AtifValidationError(
                [
                    f"unsupported schema version {trajectory.schema_version}; "
                    f"expected {self.supported_schema_version}"
                ]
            )
        return trajectory

    @staticmethod
    def validate_step_evidence(
        trajectory: Trajectory,
        evidence: AtifStepEvidence,
    ) -> None:
        """Reject evidence that cites a nonexistent step or tool call."""

        step = next((item for item in trajectory.steps if item.step_id == evidence.step_id), None)
        if step is None:
            raise AtifValidationError([f"evidence references missing step {evidence.step_id}"])
        if evidence.tool_call_id is None:
            return
        tool_call_ids = {call.tool_call_id for call in step.tool_calls or []}
        if evidence.tool_call_id not in tool_call_ids:
            raise AtifValidationError(
                [
                    f"evidence references missing tool call {evidence.tool_call_id} "
                    f"on step {evidence.step_id}"
                ]
            )
