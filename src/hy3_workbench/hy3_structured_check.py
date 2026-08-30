"""Explicit command for one bounded structured Hy3 compatibility request."""

import json
from datetime import UTC, datetime
from pathlib import Path

from hy3_workbench.config import get_settings
from hy3_workbench.hy3_client import Hy3Client


def _compatibility_output_path(configured_root: Path) -> Path:
    """Resolve the configured data root without permitting project escape."""

    project_root = Path.cwd().resolve(strict=True)
    if configured_root.is_absolute() or ".." in configured_root.parts:
        raise SystemExit("WORKBENCH_DATA_DIR must be project-relative for this command.")
    output_dir = (project_root / configured_root / "compatibility").resolve()
    if not output_dir.is_relative_to(project_root):
        raise SystemExit("WORKBENCH_DATA_DIR escapes the project root.")
    return output_dir / "hy3-structured.json"


def main() -> None:
    settings = get_settings()
    if not settings.hy3_configured:
        raise SystemExit(
            "Hy3 is not configured. Set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY in .env."
        )

    result = Hy3Client(settings).structured_compatibility()
    output_path = _compatibility_output_path(settings.workbench_data_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "hy3-structured-compatibility-v1",
        "checked_at": datetime.now(UTC).isoformat(),
        **result.model_dump(mode="json"),
    }
    temporary_path = output_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)

    print(
        json.dumps(
            {
                "status": "validated",
                "response_format": result.response_format,
                "model": result.model,
                "reasoning_content_received": result.reasoning_content_received,
                "record_path": output_path.relative_to(Path.cwd()).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
