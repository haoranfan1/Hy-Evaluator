# 10-Day Build Roadmap

Research is complete. The fixed direction is a web-based Hy3 coding-agent process evaluator using SWE-bench Verified, mini-SWE-agent, Harbor, and ATIF.

The schedule is outcome-based. If a day slips, cut optional scope in the documented order rather than cutting evaluator validation, reproducibility, result analysis, or the final delivery window.

## Fixed MVP

```text
task or recorded run
    -> Hy3 coding trajectory
    -> official patch verification
    -> deterministic and semantic process evaluation
    -> evidence-linked web diagnosis
    -> human validation
    -> required aggregate analysis
```

Only one benchmark, harness, trace format, semantic judge configuration, and local web application are in scope.

## Schedule

| Day | Objective | Exit condition |
| --- | --- | --- |
| **1 — Contracts and critical handshake** | Scaffold Python/React projects; implement typed core schemas; confirm one Hy3 chat completion and nested reasoning payload; create a recorded ATIF development fixture. | Hy3 connectivity is known, schemas validate, and one fixture can be loaded without Harbor. |
| **2 — Deterministic evaluator** | Validate ATIF/artifact identity; extract verifier, patch, command, and integrity facts; implement outcome/inconclusive policies and unit tests. | The fixture produces reproducible deterministic checks without a model call. |
| **3 — Semantic evaluator** | Implement versioned rubric, Hy3 structured review, evidence-reference validation, one schema-repair retry, and merge policy. | One invalid and one valid fixture produce typed, evidence-linked results; failures remain honest and inspectable. |
| **4 — API and persistence** | Add SQLite indexes, immutable artifact registration, import/evaluate/read/review endpoints, exports, and restart/interruption behavior. | The offline workflow is callable through FastAPI and survives process restart without corrupting evidence. |
| **5 — Evidence debugger UI** | Build run list and run detail; connect findings to ATIF steps, command observations, patch, and verifier artifacts. | A user can understand the first error without reading raw JSON. |
| **6 — Human review and analytics** | Implement evaluator-hidden initial labels, adjudication, provenance-aware metrics, difficulty/error views, exclusions, and case links. | Required human records and aggregate metrics can be produced from fixtures. |
| **7 — Live Harbor integration** | Pin Harbor/mini-SWE-agent; validate ATIF v1.7 conversion; run one minimal task and one selected SWE-bench Verified task through Hy3. | One real Hy3 run produces a patch, official verifier artifacts, an ATIF trajectory, and a workbench diagnosis. |
| **8 — Evaluation and validation** | Freeze the affordable task slice; run sequentially; label every gradeable incorrect run and audit every resolved-and-flagged run. | Required localization and false-positive evidence exists with explicit denominators and exclusions. |
| **9 — Analysis and differentiation** | Export final metrics/report/case studies; implement the regression card only if core evidence is complete; finish README and setup documentation. | Submission artifacts tell one coherent task-to-diagnosis-to-analysis story. |
| **10 — Delivery freeze** | Clean-environment run, tests/build, requirement/security/reproducibility audits, UI polish, demo rehearsal and recording, public-repository preparation. | A reviewer can set up the project, inspect evidence, reproduce the documented path, and view a demo under two minutes. |

## Daily control rule

At the end of each day:

1. Record the achieved exit condition and failed assumptions.
2. Update only the next day in [NEXT_STEPS.md](NEXT_STEPS.md).
3. Preserve raw errors and evidence instead of hiding incomplete integration.
4. Do not open another research topic; unresolved external behavior becomes a bounded implementation spike.

## Cut order

Cut in this order if the schedule slips:

1. Custom animation and decorative chart polish.
2. Error-propagation overlay.
3. Before/after trajectory comparison.
4. Regression-card feature.
5. Extra evaluation tasks beyond the documented, difficulty-covering slice.

Do not cut:

- Automatic final-result verification.
- Process correctness, first-error localization, taxonomy, or correct-result/invalid-process handling.
- Human localization and false-positive records.
- Difficulty and capability-boundary analysis.
- Evidence provenance and reproducible exports.
- README, setup/configuration instructions, or the two-minute demo.

## No-go decisions

- No new benchmark construction.
- No second harness or benchmark unless the primary direction is formally abandoned.
- No authentication, team collaboration, cloud deployment, fine-tuning, or autonomous self-evolution.
- No optional feature begins while a mandatory acceptance scenario is failing.
