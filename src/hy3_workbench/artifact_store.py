"""Read-only registration and integrity checks for project-local artifacts."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from pydantic import TypeAdapter

from hy3_workbench.contracts import ArtifactReference, ProjectRelativePath


class ArtifactIntegrityError(ValueError):
    """Raised when an artifact is outside the project or no longer immutable."""


class ArtifactStore:
    """Register immutable files by project-relative path and SHA-256."""

    _path_adapter = TypeAdapter(ProjectRelativePath)

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        if not self.project_root.is_dir():
            raise ValueError("project_root must be a directory")

    def register(self, relative_path: str) -> ArtifactReference:
        """Hash one existing project-local file without modifying it."""

        canonical_path, resolved_path = self._resolve_file(relative_path)
        digest, byte_size = self._hash_stable_file(resolved_path)
        media_type, _ = mimetypes.guess_type(canonical_path)
        return ArtifactReference(
            artifact_id=f"artifact-{digest[:24]}",
            path=canonical_path,
            sha256=digest,
            byte_size=byte_size,
            media_type=media_type or "application/octet-stream",
        )

    def verify(self, reference: ArtifactReference) -> None:
        """Raise if a registered file's path, size, or digest no longer matches."""

        canonical_path, resolved_path = self._resolve_file(reference.path)
        digest, byte_size = self._hash_stable_file(resolved_path)
        if canonical_path != reference.path:
            raise ArtifactIntegrityError("artifact path is not canonical")
        if byte_size != reference.byte_size:
            raise ArtifactIntegrityError(
                f"artifact size mismatch for {reference.path}: "
                f"expected {reference.byte_size}, got {byte_size}"
            )
        if digest != reference.sha256:
            raise ArtifactIntegrityError(
                f"artifact SHA-256 mismatch for {reference.path}: "
                f"expected {reference.sha256}, got {digest}"
            )

    def _resolve_file(self, relative_path: str) -> tuple[str, Path]:
        try:
            canonical_path = self._path_adapter.validate_python(relative_path)
        except ValueError as error:
            raise ArtifactIntegrityError(str(error)) from error

        candidate = self.project_root / canonical_path
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise ArtifactIntegrityError(f"artifact does not exist: {canonical_path}") from error

        if not resolved.is_relative_to(self.project_root):
            raise ArtifactIntegrityError(f"artifact escapes project root: {canonical_path}")
        if not resolved.is_file():
            raise ArtifactIntegrityError(f"artifact is not a regular file: {canonical_path}")
        return canonical_path, resolved

    @staticmethod
    def _hash_stable_file(path: Path) -> tuple[str, int]:
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ArtifactIntegrityError(f"artifact changed while hashing: {path.name}")
        return digest.hexdigest(), after.st_size
