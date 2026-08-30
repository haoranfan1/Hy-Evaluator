# Next Steps

## Status

**Current gate: Day 5 evidence debugger UI.**

Completed prerequisites:

- Days 1–3: strict contracts, verified fixture bundles, the deterministic lane, the fixed Hy3
  semantic judge with one repair retry and honest failure, and the merge policy, with two
  recorded live Hy3 reviews reproducing the fixture oracles.
- Day 4: SQLite persistence with atomic imports and append-only review versions, plus the
  FastAPI workflow — import, digest-idempotent evaluate, run/trajectory/evaluation reads,
  blinded initial reviews, adjudications, and byte-stable exports — all restart-safe.
- 85 backend tests and Ruff pass without Docker; live Hy3 usage stays optional for the tests.

## Single next action

Build the evidence-debugger frontend against the Day 4 API, using the three imported fixture
bundles as data. No human-review forms, analytics charts, or live execution controls yet.

```text
GET /api/runs                    -> run list with outcome, process, first error, review state
GET /api/runs/{id}               -> run detail header and evaluation summary
GET /api/runs/{id}/trajectory    -> ordered ATIF step timeline
GET /api/evaluations/{id}        -> deterministic checks, findings, evidence references
```

Required behavior:

1. `/runs` lists imported runs with task, difficulty, execution status, outcome status,
   process status, first-error summary, and review state, with simple client-side filters for
   outcome and process status.
2. `/runs/{run_id}` shows the trajectory as an ordered step timeline: step source, message,
   tool calls with arguments, and observations, with the first-error step visually marked.
3. An evidence panel presents deterministic checks and semantic findings in separate lanes,
   each showing status/severity, summary, and its evidence references.
4. Selecting a finding highlights every ATIF step it cites, and selecting a step lists every
   check and finding citing it; evidence references to the patch, verifier artifacts, and task
   fields navigate to the matching tab or panel.
5. Patch and verifier tabs render the generated diff and the per-test verifier results with
   pass/fail state; inconclusive runs surface their exclusions instead of an invented verdict.
6. The frontend uses the established stack (React 19, TypeScript, Vite, React Router,
   TanStack Query) served by Vite dev proxy against the local API; no new backend endpoints
   are added for the UI.
7. Frontend unit tests cover the run list, the step timeline, and the finding-to-step
   cross-highlighting against recorded API fixtures; `npm run build` and the backend suite
   both pass.

## Exit condition

The gate is complete when a reviewer, starting from `/runs`, can open the invalid fixture run
and understand — without reading raw JSON — that the run is unresolved, the process is invalid,
the first error is at step 3 (`call-edit-1`, `task_interpretation`), which evidence supports
it, what the patch changed, and which declared test still fails; the valid and inconclusive
fixtures render correctly (no first error / explicit exclusions); and frontend tests, the
frontend build, the backend suite, and Ruff all pass.

## Explicitly deferred

- Human-review forms (blinded initial label, adjudication) and analytics: Day 6.
- Real Hy3/Harbor/SWE-bench execution and the job manager: Day 7.
- Regression cards, comparison views, and decorative polish: only after mandatory evidence passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
