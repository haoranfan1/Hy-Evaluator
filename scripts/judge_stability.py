"""Measure semantic-judge stability by repeating the review on one bundle.

Runs the fixed Hy3 judge N times over the same rendered input and tabulates
verdict, first-error step, category, and finding counts across attempts. Raw
responses persist under the ignored .local semantic state like any live review.

Usage:
  uv run python scripts/judge_stability.py --run-id <stored run id> --repeats 5 \
    --out results/judge-stability/<name>.json
  uv run python scripts/judge_stability.py --fixture invalid-first-error --repeats 5 \
    --out results/judge-stability/fixture-invalid.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.atif import AtifAdapter  # noqa: E402
from hy3_workbench.config import get_settings  # noqa: E402
from hy3_workbench.contracts import RunRecord, TaskManifest  # noqa: E402
from hy3_workbench.evidence_extractor import EvidenceExtractor  # noqa: E402
from hy3_workbench.hy3_client import Hy3Client  # noqa: E402
from hy3_workbench.rubric import RUBRIC_VERSION, SEMANTIC_PROMPT_VERSION  # noqa: E402
from hy3_workbench.semantic_reviewer import SemanticReviewer  # noqa: E402
from hy3_workbench.storage import WorkbenchRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-id")
    source.add_argument("--fixture")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    project_root = Path.cwd().resolve(strict=True)
    settings = get_settings()
    if not settings.hy3_configured:
        print("Hy3 is not configured", file=sys.stderr)
        return 1

    if args.run_id:
        repository = WorkbenchRepository(
            project_root / settings.workbench_data_dir / "workbench.sqlite3"
        )
        stored = repository.get_run(args.run_id)
        manifest = repository.get_task(stored.task_id)
        run = stored.run
        subject = args.run_id
    else:
        bundle = project_root / "data" / "fixtures" / args.fixture
        manifest = TaskManifest.model_validate_json(
            (bundle / "manifest.json").read_text(encoding="utf-8")
        )
        run = RunRecord.model_validate_json((bundle / "run.json").read_text(encoding="utf-8"))
        subject = f"fixture-{args.fixture}"

    extractor = EvidenceExtractor(project_root)
    deterministic = extractor.extract(manifest, run)
    trajectory = AtifAdapter().load(project_root / run.trajectory.path)
    patch_text = (project_root / run.patch.path).read_text(encoding="utf-8")

    attempts = []
    for index in range(1, args.repeats + 1):
        reviewer = SemanticReviewer(
            project_root,
            Hy3Client(settings),
            settings.workbench_data_dir / "semantic" / f"stability-{subject}" / f"attempt-{index}",
            settings.semantic_context_limit_chars,
        )
        print(f"attempt {index}/{args.repeats}...", flush=True)
        result = reviewer.review(manifest, run, trajectory, patch_text, deterministic)
        output = result.output
        first_error = output.first_error if output is not None else None
        attempts.append(
            {
                "attempt": index,
                "status": result.status,
                "process_status": output.process_status if output else None,
                "first_error_location": first_error.location if first_error else None,
                "first_error_step": (
                    first_error.step_id
                    if first_error is not None and first_error.location == "located"
                    else None
                ),
                "primary_category": (
                    first_error.primary_category if first_error is not None else None
                ),
                "finding_count": len(output.findings) if output else None,
                "repair_retries": result.attempts - 1 if result.attempts else 0,
            }
        )

    completed = [a for a in attempts if a["status"] == "completed"]
    verdicts = {a["process_status"] for a in completed}
    steps = {a["first_error_step"] for a in completed}
    report = {
        "schema_version": "judge-stability-v1",
        "recorded_at": datetime.now(UTC).isoformat(),
        "subject": subject,
        "repeats": args.repeats,
        "judge": {
            "model": settings.hy3_model,
            "reasoning_effort": settings.hy3_reasoning_effort,
            "temperature": settings.hy3_temperature,
            "top_p": settings.hy3_top_p,
            "rubric_version": RUBRIC_VERSION,
            "semantic_prompt_version": SEMANTIC_PROMPT_VERSION,
        },
        "summary": {
            "completed": len(completed),
            "verdict_unanimous": len(verdicts) == 1,
            "verdicts": sorted(v for v in verdicts if v is not None),
            "first_error_steps": sorted(s for s in steps if s is not None),
            "step_unanimous": len(steps) == 1,
        },
        "attempts": attempts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for a in attempts:
        print(
            f"  attempt {a['attempt']}: {a['status']} process={a['process_status']} "
            f"step={a['first_error_step']} category={a['primary_category']} "
            f"findings={a['finding_count']} retries={a['repair_retries']}"
        )
    print(f"stability report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
