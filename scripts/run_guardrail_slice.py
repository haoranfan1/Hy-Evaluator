"""Run guardrail-slice-v1 sequentially: harbor run -> import -> blinded evaluation.

For each task in the frozen slice this driver launches one Harbor trial with the
frozen guardrail agent configuration, imports the completed trial as an immutable
bundle, and evaluates it with the verdict suppressed so blinded labeling can
follow. It never prints a process verdict, finding, or first error, and it
refuses to reuse an existing job name: an agent-phase retry (allowed at most once
per the slice's substitution rule) must pass an explicit --retry-suffix so both
trials stay recorded.

Usage:
  ./scripts/uv-local run python scripts/run_guardrail_slice.py [--retry-suffix r2]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SLICE_FILE = PROJECT_ROOT / "data/evaluation-slices/guardrail-slice-v1.json"
ENV_FILE = PROJECT_ROOT / ".local/workbench/swebench/agent.env"
JOBS_DIR = PROJECT_ROOT / ".local/harbor/jobs"
ROW_DIR = PROJECT_ROOT / ".local/workbench/swebench"
TASKS_DIR = PROJECT_ROOT / ".local/workbench/swebench/tasks"


def run(command: list[str]) -> str:
    print("+", " ".join(str(part) for part in command), flush=True)
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(f"command failed with exit code {completed.returncode}")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retry-suffix",
        default=None,
        help="Suffix for a documented one-time agent-phase retry (e.g. r2).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse an existing job's recorded trial instead of refusing: skip the "
            "agent run and continue with import and blinded evaluation."
        ),
    )
    args = parser.parse_args()

    slice_data = json.loads(SLICE_FILE.read_text(encoding="utf-8"))
    config_file = slice_data["intervention"]["config_file"]
    revision = slice_data["dataset"]["revision"]
    instances = [
        selected["instance_id"]
        for stratum in slice_data["strata"].values()
        for selected in stratum["selected"]
    ]
    if not ENV_FILE.exists():
        raise SystemExit(f"missing agent env file: {ENV_FILE}")
    if not (PROJECT_ROOT / config_file).exists():
        raise SystemExit(f"missing guardrail config: {config_file}")

    imported: list[tuple[str, str, str]] = []
    for instance in instances:
        job_name = f"swb-guardrail-{instance}"
        if args.retry_suffix:
            job_name = f"{job_name}-{args.retry_suffix}"
        job_dir = JOBS_DIR / job_name
        if job_dir.exists() and not args.resume:
            raise SystemExit(
                f"job {job_name} already exists; pass --resume to import its recorded "
                "trial, or --retry-suffix for the documented one-time retry"
            )

        if job_dir.exists():
            print(f"\n=== {instance}: reusing recorded trial in {job_name} ===", flush=True)
        else:
            print(f"\n=== {instance}: agent run ===", flush=True)
            run(
                [
                    "harbor",
                    "run",
                    "-p",
                    str(TASKS_DIR / instance),
                    "--agent",
                    "mini-swe-agent",
                    "--model",
                    "openai/hy3",
                    "--ak",
                    "version=2.4.6",
                    "--ak",
                    f"config_file={config_file}",
                    "--env-file",
                    str(ENV_FILE),
                    "--job-name",
                    job_name,
                    "--jobs-dir",
                    str(JOBS_DIR),
                    "-n",
                    "1",
                    "--quiet",
                ]
            )

        trial_dirs = [path for path in job_dir.iterdir() if path.is_dir()]
        if len(trial_dirs) != 1:
            raise SystemExit(f"expected exactly one trial dir in {job_dir}, found {trial_dirs}")

        print(f"=== {instance}: import ===", flush=True)
        stdout = run(
            [
                sys.executable,
                "scripts/import_harbor_trial.py",
                "--row-file",
                str(ROW_DIR / f"row-{instance}.json"),
                "--dataset-revision",
                revision,
                "--task-dir",
                str(TASKS_DIR / instance),
                "--trial-dir",
                str(trial_dirs[0]),
                "--selection-method",
                "guardrail-slice-v1 intervention rerun",
                "--selection-reason",
                "Fixed comparison set: day8-slice-v1 easy stratum rerun under the "
                "frozen guardrail agent configuration (see the slice file).",
                "--slice-id",
                slice_data["slice_id"],
            ]
        )
        match = re.search(r"imported run (\S+)", stdout)
        if match is None:
            raise SystemExit("import output did not name the imported run")
        run_id = match.group(1)

        print(f"=== {instance}: blinded evaluation ===", flush=True)
        run([sys.executable, "scripts/evaluate_run.py", "--run-id", run_id])
        status_match = re.search(r"verifier status: (\S+)", stdout)
        imported.append((instance, run_id, status_match.group(1) if status_match else "?"))

    print("\n=== guardrail-slice-v1 runs complete (verdicts suppressed) ===")
    for instance, run_id, verifier_status in imported:
        print(f"  {instance}: run {run_id} (verifier {verifier_status})")
    print(
        "Next: enter blinded initial labels in the UI as operator-blinded-guardrail "
        "for every run above BEFORE any reveal."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
