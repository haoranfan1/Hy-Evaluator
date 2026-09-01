"""Import one completed Harbor SWE-bench trial into the workbench.

Builds an immutable evidence bundle from the trial directory plus the pinned
dataset row, then registers it through the standard import workflow (identity
verification, atomic storage). Evaluation stays a separate, explicit step.

Usage:
  uv run python scripts/import_harbor_trial.py \
    --row-file .local/workbench/swebench/row-<instance>.json \
    --dataset-revision <hf dataset git sha> \
    --task-dir .local/workbench/swebench/tasks/<instance> \
    --trial-dir .local/harbor/jobs/<job>/<trial> \
    --selection-reason "why this task was selected"
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.config import get_settings  # noqa: E402
from hy3_workbench.contracts import Selection  # noqa: E402
from hy3_workbench.harbor_importer import HarborImporter, HarborImportError  # noqa: E402
from hy3_workbench.storage import WorkbenchRepository  # noqa: E402
from hy3_workbench.workflow import JudgeUnavailableError, WorkbenchService  # noqa: E402

DEFAULT_DATASET_URL = "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified"


def _no_judge():
    raise JudgeUnavailableError("importing does not use the semantic judge")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row-file", required=True, type=Path)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--dataset-source-url", default=DEFAULT_DATASET_URL)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--trial-dir", required=True, type=Path)
    parser.add_argument("--bundle-root", type=Path, default=None)
    parser.add_argument("--selection-method", default="single-task integration gate")
    parser.add_argument("--selection-reason", required=True)
    parser.add_argument(
        "--slice-id",
        default=None,
        help="Frozen slice this run belongs to; recorded on the run for scoped analytics.",
    )
    args = parser.parse_args()

    project_root = Path.cwd().resolve(strict=True)
    settings = get_settings()
    bundle_root = args.bundle_root or (settings.workbench_data_dir / "bundles")

    row = json.loads(args.row_file.read_text(encoding="utf-8"))
    importer = HarborImporter(project_root)
    try:
        built = importer.build_bundle(
            dataset_row=row,
            dataset_revision=args.dataset_revision,
            dataset_source_url=args.dataset_source_url,
            task_dir=args.task_dir.resolve(strict=True),
            trial_dir=args.trial_dir.resolve(strict=True),
            bundle_root=bundle_root,
            selection=Selection(method=args.selection_method, reason=args.selection_reason),
            harness_version=metadata.version("harbor"),
            slice_id=args.slice_id,
        )
    except HarborImportError as error:
        print(f"import rejected: {error}", file=sys.stderr)
        return 1

    repository = WorkbenchRepository(
        project_root / settings.workbench_data_dir / "workbench.sqlite3"
    )
    service = WorkbenchService(project_root, settings, repository, _no_judge)
    stored = service.import_bundle(built.bundle_dir)
    print(f"imported run {stored.run.run_id} (task {stored.task_id})")
    print(f"  bundle: {built.bundle_dir}")
    print(f"  verifier status: {stored.run.verifier.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
