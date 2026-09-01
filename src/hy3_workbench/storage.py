"""SQLite persistence for manifests, runs, evaluations, and review versions.

Every payload is a contract-validated JSON document. Reviews are append-only
versions; evaluations are replaced only through an explicit force path that is
refused once a human review exists.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hy3_workbench.contracts import (
    EvaluationResult,
    HumanReview,
    RunRecord,
    TaskManifest,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS task_manifests (
    task_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES task_manifests(task_id),
    bundle_dir TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id),
    input_digest TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS human_reviews (
    review_id TEXT PRIMARY KEY,
    evaluation_id TEXT NOT NULL REFERENCES evaluations(evaluation_id),
    review_version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (evaluation_id, review_version)
);
"""


class RepositoryConflictError(ValueError):
    """The requested write would overwrite or contradict persisted evidence."""


class RepositoryNotFoundError(LookupError):
    """The referenced record does not exist."""


class StoredRun:
    """One persisted run with its linkage metadata."""

    def __init__(self, run: RunRecord, task_id: str, bundle_dir: str) -> None:
        self.run = run
        self.task_id = task_id
        self.bundle_dir = bundle_dir


class StoredEvaluation:
    """One persisted evaluation and the digest it was produced under."""

    def __init__(self, result: EvaluationResult, input_digest: str) -> None:
        self.result = result
        self.input_digest = input_digest


class WorkbenchRepository:
    """Own the SQLite file and enforce append-only review semantics."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    # Imports -----------------------------------------------------------------

    def save_imported_bundle(
        self,
        manifest: TaskManifest,
        run: RunRecord,
        bundle_dir: str,
    ) -> None:
        """Persist one manifest/run pair atomically; nothing is written on conflict."""

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT payload FROM task_manifests WHERE task_id = ?",
                (manifest.task_id,),
            ).fetchone()
            manifest_payload = manifest.model_dump_json()
            if existing is None:
                connection.execute(
                    "INSERT INTO task_manifests (task_id, payload) VALUES (?, ?)",
                    (manifest.task_id, manifest_payload),
                )
            elif existing["payload"] != manifest_payload:
                # A task may be run under more than one frozen slice. Recording
                # metadata may differ across imports — creation time, per-slice
                # selection rationale, and the reference patch's per-bundle copy
                # path (its content identity must still match by sha256) — but
                # the substantive task contract must not. The stored manifest
                # stays authoritative and is never replaced.
                recording_only = {"created_at", "selection", "reference_patch"}
                stored = TaskManifest.model_validate_json(existing["payload"])
                stored_gold = (
                    stored.reference_patch.artifact.sha256
                    if stored.reference_patch is not None
                    else None
                )
                new_gold = (
                    manifest.reference_patch.artifact.sha256
                    if manifest.reference_patch is not None
                    else None
                )
                if stored_gold != new_gold or stored.model_dump(
                    exclude=recording_only
                ) != manifest.model_dump(exclude=recording_only):
                    raise RepositoryConflictError(
                        f"task {manifest.task_id} is already stored with different content"
                    )

            duplicate = connection.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (run.run_id,)
            ).fetchone()
            if duplicate is not None:
                raise RepositoryConflictError(f"run {run.run_id} is already imported")
            connection.execute(
                "INSERT INTO runs (run_id, task_id, bundle_dir, payload) VALUES (?, ?, ?, ?)",
                (run.run_id, manifest.task_id, bundle_dir, run.model_dump_json()),
            )

    # Reads -------------------------------------------------------------------

    def list_tasks(self) -> list[TaskManifest]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM task_manifests ORDER BY task_id"
            ).fetchall()
        return [TaskManifest.model_validate_json(row["payload"]) for row in rows]

    def get_task(self, task_id: str) -> TaskManifest:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM task_manifests WHERE task_id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise RepositoryNotFoundError(f"task {task_id} is not stored")
        return TaskManifest.model_validate_json(row["payload"])

    def list_runs(self) -> list[StoredRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, task_id, bundle_dir, payload FROM runs ORDER BY run_id"
            ).fetchall()
        return [
            StoredRun(
                RunRecord.model_validate_json(row["payload"]),
                row["task_id"],
                row["bundle_dir"],
            )
            for row in rows
        ]

    def get_run(self, run_id: str) -> StoredRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id, task_id, bundle_dir, payload FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise RepositoryNotFoundError(f"run {run_id} is not imported")
        return StoredRun(
            RunRecord.model_validate_json(row["payload"]), row["task_id"], row["bundle_dir"]
        )

    # Evaluations -------------------------------------------------------------

    def get_evaluation_for_run(self, run_id: str) -> StoredEvaluation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, input_digest FROM evaluations WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredEvaluation(
            EvaluationResult.model_validate_json(row["payload"]), row["input_digest"]
        )

    def get_evaluation(self, evaluation_id: str) -> StoredEvaluation:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, input_digest FROM evaluations WHERE evaluation_id = ?",
                (evaluation_id,),
            ).fetchone()
        if row is None:
            raise RepositoryNotFoundError(f"evaluation {evaluation_id} is not stored")
        return StoredEvaluation(
            EvaluationResult.model_validate_json(row["payload"]), row["input_digest"]
        )

    def save_evaluation(
        self,
        result: EvaluationResult,
        input_digest: str,
        replace: bool = False,
    ) -> None:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT evaluation_id FROM evaluations WHERE run_id = ?",
                (result.run_id,),
            ).fetchone()
            if existing is not None:
                if not replace:
                    raise RepositoryConflictError(
                        f"run {result.run_id} already has a stored evaluation"
                    )
                reviews = connection.execute(
                    "SELECT COUNT(*) AS total FROM human_reviews WHERE evaluation_id = ?",
                    (existing["evaluation_id"],),
                ).fetchone()
                if reviews["total"]:
                    raise RepositoryConflictError(
                        "the stored evaluation has human reviews and cannot be replaced"
                    )
                connection.execute(
                    "DELETE FROM evaluations WHERE evaluation_id = ?",
                    (existing["evaluation_id"],),
                )
            connection.execute(
                "INSERT INTO evaluations (evaluation_id, run_id, input_digest, payload) "
                "VALUES (?, ?, ?, ?)",
                (result.evaluation_id, result.run_id, input_digest, result.model_dump_json()),
            )

    # Reviews -----------------------------------------------------------------

    def list_reviews(self, evaluation_id: str) -> list[HumanReview]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM human_reviews WHERE evaluation_id = ? ORDER BY review_version",
                (evaluation_id,),
            ).fetchall()
        return [HumanReview.model_validate_json(row["payload"]) for row in rows]

    def append_review(self, review: HumanReview) -> None:
        """Append one immutable review version; existing versions are never touched."""

        with self._connect() as connection:
            evaluation = connection.execute(
                "SELECT evaluation_id FROM evaluations WHERE evaluation_id = ?",
                (review.evaluation_id,),
            ).fetchone()
            if evaluation is None:
                raise RepositoryNotFoundError(f"evaluation {review.evaluation_id} is not stored")
            latest = connection.execute(
                "SELECT MAX(review_version) AS latest FROM human_reviews WHERE evaluation_id = ?",
                (review.evaluation_id,),
            ).fetchone()
            expected_version = (latest["latest"] or 0) + 1
            if review.review_version != expected_version:
                raise RepositoryConflictError(
                    f"next review version for {review.evaluation_id} is "
                    f"{expected_version}, not {review.review_version}"
                )
            connection.execute(
                "INSERT INTO human_reviews (review_id, evaluation_id, review_version, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    review.review_id,
                    review.evaluation_id,
                    review.review_version,
                    review.model_dump_json(),
                ),
            )

    def all_reviews(self) -> list[HumanReview]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM human_reviews ORDER BY evaluation_id, review_version"
            ).fetchall()
        return [HumanReview.model_validate_json(row["payload"]) for row in rows]

    def all_evaluations(self) -> list[StoredEvaluation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload, input_digest FROM evaluations ORDER BY run_id"
            ).fetchall()
        return [
            StoredEvaluation(
                EvaluationResult.model_validate_json(row["payload"]), row["input_digest"]
            )
            for row in rows
        ]

    def is_ready(self) -> bool:
        """Confirm the schema answers a trivial query without mutating anything."""

        try:
            with self._connect() as connection:
                connection.execute("SELECT COUNT(*) FROM runs").fetchone()
        except sqlite3.Error:
            return False
        return True
