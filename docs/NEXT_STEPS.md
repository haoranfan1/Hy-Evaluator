# Next Steps

## Status

**Current gate: Day 4 API and persistence.**

Completed prerequisites:

- Day 1: strict contracts, verified fixture bundles, the offline evidence gate, and the recorded
  Hy3 JSON-object compatibility check.
- Day 2: the deterministic lane (`EvidenceExtractor`) with typed, evidence-linked checks, the
  outcome policy, protected-path hard failures, and the guarantee that no emitted evidence
  reference dangles.
- Day 3: the semantic lane (`SemanticReviewer`) with the frozen `process-rubric-v1` and
  `semantic-prompt-v1` versions, evidence-reference rejection, one schema-repair retry,
  persisted raw responses, honest `unavailable`/`context_limit` failure, and the merge policy
  (`ProcessEvaluator`) producing contract-valid `EvaluationResult` records.
- Two bounded live Hy3 semantic reviews are recorded: the invalid fixture localized to step 3
  with `task_interpretation` on the first attempt, and the valid fixture produced no false
  positive.
- 66 backend tests and Ruff pass without Docker; live Hy3 usage stays optional for the tests.

## Single next action

Persist the offline workflow and expose it through FastAPI, without Harbor launching, live
benchmark execution, analytics computation, or UI work.

```text
fixture bundle
    -> POST /api/runs/import (validate, register artifacts, index in SQLite)
    -> POST /api/runs/{run_id}/evaluate (deterministic + semantic + merge, idempotent)
    -> GET  /api/runs, /api/runs/{run_id}, /api/runs/{run_id}/trajectory
    -> GET  /api/evaluations/{evaluation_id}
    -> POST /api/evaluations/{evaluation_id}/initial-review and /adjudications
    -> POST /api/exports (per-run JSON and reviews JSONL from persisted records)
```

Required behavior:

1. Implement `WorkbenchRepository` over stdlib SQLite under the configured
   `WORKBENCH_DATA_DIR`, storing manifests, runs, evaluations, and append-only human-review
   versions; every payload validates against the project contracts on write and on read.
2. Register imported artifacts immutably through `ArtifactStore` and reject imports whose
   paths traverse outside the project or whose hashes do not verify.
3. `POST /api/runs/import` accepts a project-relative bundle directory (manifest plus run
   record); reject traversal, symlink escapes, unsupported layouts, and duplicate run IDs.
4. `POST /api/runs/{run_id}/evaluate` runs the full evaluator; it is idempotent by input and
   judge-configuration digest and re-runs only with `force=true`. A judge failure still
   persists the honest partial result.
5. Human reviews are append-only versions: the initial label is stored before any reveal
   timestamp, adjudications append a new version, and no endpoint mutates or deletes a stored
   review or evaluation.
6. Restart safety: killing and restarting the API process on the same SQLite file loses no
   imported run, evaluation, or review, and interrupted state remains explicit rather than
   silently repaired.
7. `POST /api/exports` rebuilds `results/per_run/*.json` and `results/human_reviews.jsonl`
   from persisted records only. Metric computation stays in Day 6.
8. `GET /api/health` reports database and artifact-root readiness without touching the model.

Deferred inside Day 4: `POST /api/runs` (live Harbor launch, Day 7), `GET /api/analytics/summary`
(Day 6), and every regression-card endpoint.

## Exit condition

The gate is complete when:

1. All three fixture bundles import, evaluate (mocked judge), and read back through FastAPI
   test clients with contract-valid payloads.
2. Repeating `evaluate` without `force` returns the stored result without a second judge call;
   `force=true` re-evaluates and records a new result version or replaces it explicitly.
3. Initial labels and adjudications persist as immutable review versions and reject
   pre-reveal contamination (no adjudication fields before a reveal timestamp).
4. Restarting the app against the same SQLite file preserves every imported run, evaluation,
   and review, and the exports rebuild byte-stable files from persisted state alone.
5. Malicious import paths (absolute, traversal, symlink escape) are rejected with explicit
   errors and no partial writes.
6. The full backend test suite and Ruff pass without Docker or a live benchmark task.

## Explicitly deferred

- Evidence-debugger UI: Day 5.
- Human-review UI and analytics/metrics: Day 6.
- Real Hy3/Harbor/SWE-bench execution and the job manager: Day 7.
- Regression cards, comparison views, and decorative polish: only after mandatory evidence passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
