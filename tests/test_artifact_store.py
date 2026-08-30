from pathlib import Path

import pytest

from hy3_workbench.artifact_store import ArtifactIntegrityError, ArtifactStore


def test_register_and_verify_immutable_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("stable evidence\n", encoding="utf-8")
    store = ArtifactStore(tmp_path)

    reference = store.register("artifact.txt")

    assert reference.path == "artifact.txt"
    assert len(reference.sha256) == 64
    assert reference.byte_size == len("stable evidence\n")
    store.verify(reference)


def test_verify_rejects_changed_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("first\n", encoding="utf-8")
    store = ArtifactStore(tmp_path)
    reference = store.register("artifact.txt")
    artifact.write_text("second\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="mismatch"):
        store.verify(reference)


def test_register_rejects_path_outside_project(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    with pytest.raises(ArtifactIntegrityError, match="project-relative"):
        store.register("../outside.txt")
