"""Produce the evaluator regression card for one frozen evaluation slice.

Re-evaluates every slice run in memory under the CURRENT evaluator version and
compares both the stored evaluation and the new one against the frozen human
labels. Stored evaluations and reviews are never modified — the card is a
recorded, versioned comparison, not a replacement.

Usage:
  uv run python scripts/regression_card.py --slice day8-slice-v1 \
    --out results/regression/day9-regression-card.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.config import get_settings  # noqa: E402
from hy3_workbench.evaluator import EVALUATOR_VERSION, ProcessEvaluator  # noqa: E402
from hy3_workbench.hy3_client import Hy3Client  # noqa: E402
from hy3_workbench.metrics import load_slice  # noqa: E402
from hy3_workbench.storage import WorkbenchRepository  # noqa: E402


def _first_error_step(first_error) -> int | None:
    if first_error is None or first_error.location != "located":
        return None
    return first_error.step_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    project_root = Path.cwd().resolve(strict=True)
    settings = get_settings()
    if not settings.hy3_configured:
        print("Hy3 is not configured; the regression card needs the live judge", file=sys.stderr)
        return 1
    scope = load_slice(project_root / settings.slices_dir, args.slice)
    repository = WorkbenchRepository(
        project_root / settings.workbench_data_dir / "workbench.sqlite3"
    )
    evaluator = ProcessEvaluator(project_root, Hy3Client(settings), settings)

    rows = []
    for stored_run in repository.list_runs():
        if stored_run.task_id not in scope.task_ids:
            continue
        run_id = stored_run.run.run_id
        manifest = repository.get_task(stored_run.task_id)
        stored_eval = repository.get_evaluation_for_run(run_id)
        if stored_eval is None:
            print(f"skipping {run_id}: no stored evaluation", file=sys.stderr)
            continue
        reviews = repository.list_reviews(stored_eval.result.evaluation_id)
        adjudicated = [review for review in reviews if review.final_label is not None]
        human = adjudicated[-1].final_label if adjudicated else None
        if human is None:
            print(f"skipping {run_id}: no adjudicated human label", file=sys.stderr)
            continue

        print(f"re-evaluating {run_id} under {EVALUATOR_VERSION}...", flush=True)
        new_result = evaluator.evaluate(manifest, stored_run.run)

        rows.append(
            {
                "run_id": run_id,
                "task_id": stored_run.task_id,
                "human": {
                    "process_status": human.process_status,
                    "first_error_step": human.first_error_step_id,
                },
                "stored": {
                    "evaluator_version": stored_eval.result.evaluator_version,
                    "status": stored_eval.result.status,
                    "process_status": stored_eval.result.process_status,
                    "first_error_step": _first_error_step(stored_eval.result.first_error),
                },
                "reevaluated": {
                    "evaluator_version": new_result.evaluator_version,
                    "status": new_result.status,
                    "process_status": new_result.process_status,
                    "first_error_step": _first_error_step(new_result.first_error),
                    "exclusions": list(new_result.exclusions),
                    "protected_check": next(
                        (
                            {"status": c.status, "summary": c.summary[:200]}
                            for c in new_result.deterministic_checks
                            if c.check_id == "check-protected-paths"
                        ),
                        None,
                    ),
                },
            }
        )

    def score(version_key: str) -> dict:
        valid_rows = [r for r in rows if r["human"]["process_status"] == "valid"]
        invalid_rows = [r for r in rows if r["human"]["process_status"] == "invalid"]
        located = [r for r in invalid_rows if r["human"]["first_error_step"] is not None]
        false_positives = [
            r["run_id"] for r in valid_rows if r[version_key]["process_status"] == "invalid"
        ]
        detected = [
            r["run_id"] for r in invalid_rows if r[version_key]["process_status"] == "invalid"
        ]
        exact = [
            r["run_id"]
            for r in located
            if r[version_key]["first_error_step"] == r["human"]["first_error_step"]
        ]
        within_one = [
            r["run_id"]
            for r in located
            if r[version_key]["first_error_step"] is not None
            and abs(r[version_key]["first_error_step"] - r["human"]["first_error_step"]) <= 1
        ]
        return {
            "false_positives": {
                "runs": false_positives,
                "n": len(false_positives),
                "d": len(valid_rows),
            },
            "detection": {"runs": detected, "n": len(detected), "d": len(invalid_rows)},
            "exact_localization": {"runs": exact, "n": len(exact), "d": len(located)},
            "within_one_localization": {
                "runs": within_one,
                "n": len(within_one),
                "d": len(located),
            },
        }

    card = {
        "schema_version": "regression-card-v1",
        "recorded_at": datetime.now(UTC).isoformat(),
        "slice_id": scope.slice_id,
        "note": (
            "The stored evaluations and reviews are frozen Day 8 evidence; the re-evaluation "
            "ran in memory under the current evaluator with the live judge and was not "
            "persisted to the workbench database. Human labels are the frozen adjudicated "
            "final labels."
        ),
        "stored_version": rows[0]["stored"]["evaluator_version"] if rows else None,
        "reevaluated_version": EVALUATOR_VERSION,
        "scores": {"stored": score("stored"), "reevaluated": score("reevaluated")},
        "runs": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for name in ("false_positives", "detection", "exact_localization", "within_one_localization"):
        old = card["scores"]["stored"][name]
        new = card["scores"]["reevaluated"][name]
        print(f"{name}: {old['n']}/{old['d']} -> {new['n']}/{new['d']}")
    print(f"card written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
