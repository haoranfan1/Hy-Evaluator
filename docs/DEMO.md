# Demo Script — One Complete Workflow in Under Two Minutes

The submission requires a video or GIF of at most two minutes showing one complete workflow
from solving a task through process evaluation. **The recording is produced by the operator**
during the final human review pass; when it exists, place it at
`docs/demo/hy3-workbench-demo.webm` (or `.mp4`/`.gif`) and link it here.

This document fixes the scene-by-scene script, the state-isolation protocol the recording
must follow, and an optional automated driver. A scripted rehearsal recording (≈65 seconds,
1280×720) validated the scene flow, the selectors, and the isolation protocol end to end.

## Preparation — record against a copy of the workbench state

Any label saved on camera must never touch the frozen validated evidence, so the API serves
a **copy** of the state for the whole recording. In the copy, the synthetic invalid fixture's
reviews are reset so it opens blinded again:

```bash
cd /path/to/Hy-Evaluator
mkdir -p .local/workbench-demo
cp .local/workbench/workbench.sqlite3 .local/workbench-demo/
./scripts/uv-local run python -c "
import sqlite3
con = sqlite3.connect('.local/workbench-demo/workbench.sqlite3')
con.execute(\"DELETE FROM human_reviews WHERE evaluation_id = (SELECT evaluation_id FROM evaluations WHERE run_id = 'run-fixture-invalid-first-error')\")
con.commit()"
```

Serve the copy and the UI (two terminals):

```bash
WORKBENCH_DATA_DIR=.local/workbench-demo ./scripts/uv-local run hy3-workbench
```

```bash
cd frontend && npm run dev
```

Use a self-describing reviewer alias on camera (for example `operator-demo`), and record at
1280×720 or larger.

## Scenes (target ≈65–110 seconds total)

1. **Run list** — `http://localhost:5173/runs` (~7 s). The imported runs: real SWE-bench
   Verified tasks solved by Hy3 through mini-SWE-agent/Harbor, with official difficulty
   bands, verifier outcomes (all `resolved`), process verdicts, first errors, and review
   counts. Do not scroll to the fixture rows — their verdicts belong after scene 2's reveal.
2. **The blinded human workflow** — `/runs/run-fixture-invalid-first-error` (~20 s). The run
   opens **blinded**: evidence and the step timeline visible, semantic findings and verdict
   hidden. Fill the initial label (invalid, first error located, step `3`,
   `task_interpretation`, a short note), save — the verdict is revealed: the evaluator
   independently localized the same step 3, and the timeline marks the first-error call.
3. **The flagship real case** — `/runs/django__django-16899__yJvk3qg__agent` (~15 s).
   Resolved by the official verifier, human-labeled invalid at **step 13**, where the agent
   rewrote the graded FAIL_TO_PASS assertions inside the protected test file (show the
   `sed -i` command at step 13, then the review history: blinded label and adjudicated
   final label at step 13; the stored v1 evaluation anchored at step 9 — the measured gap).
4. **Validated slice analytics** — `/analytics?scope=day8-slice-v1` (~16 s). Metrics with
   numerator/denominator/provenance chips, the difficulty table with the process-validity
   inversion, and the representative cases annotated by adjudication — including the three
   evaluator flags **rejected as false positives**.
5. **The regression card in the published report** — [REPORT.md §6](REPORT.md) rendered on
   the public repository (~10 s): false positives 3/4 → 0/4, detection 4/4 preserved, exact
   localization 0/4 → 3/4 against the frozen human labels.

## Optional automated recording

[`frontend/scripts/record_demo.mjs`](../frontend/scripts/record_demo.mjs) drives the exact
scene sequence headlessly and writes the video plus per-scene screenshots:

```bash
cd frontend && node scripts/record_demo.mjs demo-recording
```

## After recording

Verify the real store is untouched, then stop the demo API and restart the normal one:

```bash
curl -s http://127.0.0.1:8000/api/runs/run-fixture-invalid-first-error | grep -o '"review_version"' | wc -l
```

Against the **real** state this must report the fixture's original review count (2), and
`/api/analytics/summary?scope=day8-slice-v1` must still report `adjudicated_count` 8.
