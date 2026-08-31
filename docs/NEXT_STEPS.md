# Next Steps

## Status

**Current gate: Day 6 human review and analytics.**

Completed prerequisites:

- Days 1–4: contracts, fixtures, the deterministic lane, the fixed Hy3 semantic judge and merge
  policy, SQLite persistence, and the restart-safe FastAPI workflow with blinded review
  endpoints and byte-stable exports.
- Day 5: the evidence-debugger UI — filterable run list, ordered step timeline with the marked
  first-error step, findings/checks lanes with two-way step cross-highlighting, evidence chips
  navigating to patch/verifier/task views, and honest inconclusive rendering — verified
  end-to-end against the live API with recorded screenshots.
- 85 backend tests, 9 frontend tests, Ruff, typecheck, and the production build pass.

## Single next action

Implement the human-review workflow in the UI and the provenance-aware analytics lane, using
the three persisted fixture evaluations as data. No real benchmark execution.

```text
run detail (review mode)
    -> blinded initial label (semantic verdict hidden, deterministic evidence visible)
    -> reveal -> adjudication + finding decisions (new immutable version)
persisted evaluations + reviews
    -> MetricCalculator (numerator, denominator, exclusions, provenance per metric)
    -> GET /api/analytics/summary -> /analytics page
    -> exports: metrics.csv + summary.json
```

Required behavior:

1. Review mode on the run detail page: until an initial review exists, the semantic verdict,
   findings lane, and first-error banner stay hidden while task, trajectory, patch, and
   verifier evidence remain visible; the reviewer records the initial label from that state.
2. After the initial label is saved, the evaluator output is revealed and an adjudication form
   appends a new immutable review version with accept/edit/reject/needs-more-evidence,
   per-finding decisions, and a final label.
3. A backend `MetricCalculator` derives the required metric set from persisted records only:
   final-answer accuracy, predicted and adjudicated process-correctness rates, incorrect-run
   error-detection accuracy, exact and within-one-step localization accuracy,
   correct-result confirmed-problem and false-positive rates, primary-error distribution, and
   per-difficulty tables. Every metric carries numerator, denominator, exclusions, and label
   provenance (`human` versus `evaluator`).
4. The adjacent-difficulty decline test uses a fixed recorded seed and reports
   `not_established` when the bootstrap interval does not lie fully below zero; it must never
   fabricate an interval from empty difficulty bands.
5. `GET /api/analytics/summary` returns the typed metrics; `POST /api/exports` additionally
   writes `results/metrics.csv` and `results/summary.json` deterministically.
6. The `/analytics` page renders the outcome-versus-process quadrant, primary-error
   distribution, difficulty table with explicit denominators, decline-interval statement,
   excluded/inconclusive runs, and links to the underlying runs, marking each aggregate as
   human- or evaluator-provenance.
7. Backend unit tests cover the metric definitions (including empty and single-run
   denominators) and blinding enforcement; frontend tests cover the blinded review flow and
   the analytics rendering from recorded responses.

## Exit condition

The gate is complete when a reviewer can label the invalid fixture run before seeing the
evaluator verdict, adjudicate after the reveal, and then open `/analytics` and read every
required metric with explicit numerators, denominators, exclusions, and provenance — all
produced from persisted fixture data; blinded initial labels are demonstrably recorded before
reveal timestamps; and the backend suite, frontend tests, Ruff, and both builds pass.

## Explicitly deferred

- Real Hy3/Harbor/SWE-bench execution and the job manager: Day 7.
- The final difficulty-covering evaluation slice and its human labels: Day 8.
- Report/case-study exports and the regression card: Days 9+, only after mandatory evidence.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
