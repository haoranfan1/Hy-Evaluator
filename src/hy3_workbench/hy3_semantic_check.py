"""Explicit command for one bounded live semantic review of a fixture bundle.

This makes at most two Hy3 requests (one review plus at most one schema-repair
retry) and stores the sanitized result under ignored project-local state.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from hy3_workbench.config import get_settings
from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evaluator import ProcessEvaluator
from hy3_workbench.hy3_client import Hy3Client


def _record_output_path(configured_root: Path, project_root: Path, fixture: str) -> Path:
    if configured_root.is_absolute() or ".." in configured_root.parts:
        raise SystemExit("WORKBENCH_DATA_DIR must be project-relative for this command.")
    output_dir = (project_root / configured_root / "compatibility").resolve()
    if not output_dir.is_relative_to(project_root):
        raise SystemExit("WORKBENCH_DATA_DIR escapes the project root.")
    return output_dir / f"hy3-semantic-review-{fixture}.json"


def main() -> None:
    settings = get_settings()
    if not settings.hy3_configured:
        raise SystemExit(
            "Hy3 is not configured. Set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY in .env."
        )

    fixture = sys.argv[1] if len(sys.argv) > 1 else "invalid-first-error"
    project_root = Path.cwd().resolve(strict=True)
    bundle = project_root / "data" / "fixtures" / fixture
    manifest = TaskManifest.model_validate_json(
        (bundle / "manifest.json").read_text(encoding="utf-8")
    )
    run = RunRecord.model_validate_json((bundle / "run.json").read_text(encoding="utf-8"))

    evaluator = ProcessEvaluator(project_root, Hy3Client(settings), settings)
    result = evaluator.evaluate(manifest, run)

    record = {
        "schema_version": "hy3-semantic-review-check-v1",
        "checked_at": datetime.now(UTC).isoformat(),
        "fixture": fixture,
        "judge_model": settings.hy3_model,
        "evaluation": result.model_dump(mode="json"),
    }
    output_path = _record_output_path(Path(settings.workbench_data_dir), project_root, fixture)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", "utf-8")
    temporary_path.replace(output_path)

    print(
        json.dumps(
            {
                "fixture": fixture,
                "status": result.status,
                "outcome_status": result.outcome_status,
                "process_status": result.process_status,
                "first_error": result.first_error.model_dump(mode="json"),
                "finding_count": len(result.findings),
                "exclusions": result.exclusions,
                "raw_semantic_output_path": result.raw_semantic_output_path,
                "record_path": output_path.relative_to(project_root).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
