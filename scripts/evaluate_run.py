"""Evaluate one imported run with the verdict suppressed for blinded labeling.

By default this prints only whether an evaluation ran and was stored — never
the process status, findings, or first error — so an operator can produce
evaluations before entering blinded initial labels without seeing the verdict.
Pass --show-verdict only after the corresponding label is saved.

Usage:
  uv run python scripts/evaluate_run.py --run-id <run_id> [--force] [--show-verdict]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.config import get_settings  # noqa: E402
from hy3_workbench.hy3_client import Hy3Client  # noqa: E402
from hy3_workbench.storage import WorkbenchRepository  # noqa: E402
from hy3_workbench.workflow import JudgeUnavailableError, WorkbenchService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--show-verdict", action="store_true")
    args = parser.parse_args()

    project_root = Path.cwd().resolve(strict=True)
    settings = get_settings()

    def judge_provider():
        if not settings.hy3_configured:
            raise JudgeUnavailableError("Hy3 is not configured")
        return Hy3Client(settings)

    repository = WorkbenchRepository(
        project_root / settings.workbench_data_dir / "workbench.sqlite3"
    )
    service = WorkbenchService(project_root, settings, repository, judge_provider)
    try:
        result, evaluated = service.evaluate_run(args.run_id, force=args.force)
    except Exception as error:
        print(f"evaluation failed: {error}", file=sys.stderr)
        return 1

    print(f"run {args.run_id}: evaluation {'ran' if evaluated else 'already stored'}")
    if args.show_verdict:
        print(f"  outcome: {result.outcome_status} | process: {result.process_status}")
        print(f"  first_error: {result.first_error}")
    else:
        print("  verdict suppressed for blinded labeling (--show-verdict reveals it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
