"""Check a recorded run's final answer against the task's standard answer.

The standard answer of a SWE-bench Verified task is its behavioral-test contract:
the declared FAIL_TO_PASS tests must pass after the agent's patch and the declared
PASS_TO_PASS tests must keep passing. Live grading runs the official swebench harness
inside the task container through Harbor's verifier (command recorded in the slice
file); this script re-applies the same contract to the official verifier report
stored in a bundle, so the outcome is re-checkable from the committed evidence.

Exit codes: 0 resolved · 2 unresolved · 3 inconclusive · 4 bundle unreadable
(the worst code across all bundles checked).

Usage:
  uv run python scripts/verify_outcome.py data/runs/django__django-16899__yJvk3qg__agent
  uv run python scripts/verify_outcome.py --all data/runs [--json]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.outcome_check import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
