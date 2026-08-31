"""Prepare a local ARM64-runnable copy of one pinned Harbor SWE-bench task.

The official task directories build FROM the AMD64-only SWE-bench images. This
script copies one pinned task, swaps the base image for a locally built ARM64
instance image, and injects the patch-dump block into the verifier script so
the agent-authored diff is recorded before grading. Every modification is
written to task-provenance.json inside the copy.

Usage:
  uv run python scripts/prepare_swebench_task.py \
    --source-task-dir .local/workbench/swebench/harbor-datasets/datasets/swebench-verified/<id> \
    --output-task-dir .local/workbench/swebench/tasks/<id> \
    --image sweb.eval.arm64.<id>:latest \
    --source-git-url https://github.com/laude-institute/harbor-datasets.git \
    --source-git-commit <pinned commit>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hy3_workbench.harbor_importer import (  # noqa: E402
    HarborImportError,
    inject_patch_dump,
    rewrite_dockerfile_from,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-task-dir", required=True, type=Path)
    parser.add_argument("--output-task-dir", required=True, type=Path)
    parser.add_argument("--image", required=True, help="Locally built ARM64 image reference")
    parser.add_argument("--source-git-url", required=True)
    parser.add_argument("--source-git-commit", required=True)
    args = parser.parse_args()

    source: Path = args.source_task_dir.resolve(strict=True)
    output: Path = args.output_task_dir.resolve()
    if output.exists():
        print(f"refusing to overwrite existing task copy: {output}", file=sys.stderr)
        return 1

    shutil.copytree(source, output)

    dockerfile_path = output / "environment" / "Dockerfile"
    test_script_path = output / "tests" / "test.sh"
    try:
        rewritten, original_image = rewrite_dockerfile_from(
            dockerfile_path.read_text(encoding="utf-8"), args.image
        )
        dockerfile_path.write_text(rewritten, encoding="utf-8")
        test_script_path.write_text(
            inject_patch_dump(test_script_path.read_text(encoding="utf-8")), encoding="utf-8"
        )
    except (HarborImportError, OSError) as error:
        shutil.rmtree(output, ignore_errors=True)
        print(f"task preparation failed: {error}", file=sys.stderr)
        return 1

    provenance = {
        "source_git_url": args.source_git_url,
        "source_git_commit": args.source_git_commit,
        "source_task_dir": str(source),
        "original_from_image": original_image,
        "replacement_image": args.image,
        "modifications": [
            "environment/Dockerfile: FROM swapped to the locally built ARM64 instance image",
            "tests/test.sh: agent working-tree diff dumped to /logs/verifier/patch.diff "
            "before the official grading flow resets test files",
        ],
        "prepared_at": datetime.now(UTC).isoformat(),
    }
    (output / "task-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"prepared task copy at {output}")
    print(f"  original image: {original_image}")
    print(f"  replacement:    {args.image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
