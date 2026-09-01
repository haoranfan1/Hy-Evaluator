"""Gate on a stored run's process verdict with an exit code.

Reads the persisted evaluation only — it never evaluates. Exit codes:
0 valid · 2 invalid · 3 inconclusive · 4 not evaluated · 5 unknown run.

Usage:
  uv run python scripts/process_gate.py --run <run-id> [--json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.config import get_settings  # noqa: E402
from hy3_workbench.gate import run_gate  # noqa: E402
from hy3_workbench.storage import WorkbenchRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run id as shown in the workbench")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    settings = get_settings()
    project_root = Path.cwd().resolve(strict=True)
    repository = WorkbenchRepository(
        project_root / settings.workbench_data_dir / "workbench.sqlite3"
    )
    return run_gate(repository, args.run, json_output=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
