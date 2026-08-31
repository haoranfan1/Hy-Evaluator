# 10-Day Build Roadmap

Research is complete. The fixed direction is a web-based Hy3 coding-agent process evaluator using SWE-bench Verified, mini-SWE-agent, Harbor, and ATIF.

The schedule is outcome-based. If a day slips, cut optional scope in the documented order rather than cutting evaluator validation, reproducibility, result analysis, or the final delivery window.

## Current checkpoint — 2026-08-30

Completed:

- Research, requirements extraction, architecture, evaluator semantics, and taxonomy are fixed.
- The isolated Python 3.12/FastAPI and Node 24/React foundations build and test successfully.
- Python dependencies are locked; the frontend lockfile has been generated.
- The ignored local Hy3 configuration is present.
- The Hy3 Chat Completions handshake passed with authentication, content, reasoning content, and
  nested `chat_template_kwargs.reasoning_effort=high`.
- Harbor 0.22.0 completed a native ARM64 container lifecycle smoke test with reward `1.0` and no
  exceptions.
- The selected official SWE-bench smoke image was confirmed to be AMD64-only; a native ARM64 pull
  failed at manifest negotiation without downloading its large layers.
- Strict, versioned contracts now cover task manifests, runs, artifact/evidence references,
  deterministic checks, findings, evaluation results, semantic output, and immutable human-review
  versions.
- Three tracked synthetic bundles cover a valid resolved process, an unresolved process with an
  exact first error, and an infrastructure-ambiguous run with incomplete verifier evidence.
- Harbor's pinned ATIF v1.7 models accept the gradeable trajectories; every bundle artifact has a
  project-relative path and verified SHA-256 identity.
- The offline evidence gate returns `ready/resolved`, `ready/unresolved`, and
  `inconclusive/inconclusive` for the three bundles respectively.
- One bounded live Hy3 response passed JSON-object mode and local `SemanticReviewOutput`
  validation. The sanitized result is stored in ignored project-local state; native server-side
  JSON Schema enforcement is not assumed.
- The deterministic lane (`EvidenceExtractor`) produces typed, evidence-linked checks for
  identity/hash verification, ATIF structure, per-test verifier records, coverage and
  consistency, the resolved/unresolved/inconclusive outcome policy, patch scope and
  sensitive-file warnings, protected-path hard process failures, advisory command failures,
  and final-claim-versus-evidence comparison — all without a model call.
- Ungradeable runs are classified from verifier logs: an evidenced patch-application failure is
  an agent-caused unresolved outcome; infrastructure markers become an inconclusive exclusion.
- Every emitted evidence reference is checked against a bundle resolver; a dangling reference
  is a hard internal error, and corrupted-bundle tests prove malformed ATIF forces
  `inconclusive` before any model call.
- Recorded implementation evidence: Harbor's pinned ATIF v1.7 model already rejects
  non-sequential step IDs and observation results referencing unknown tool calls at load time,
  so the workbench validates those through `AtifAdapter.load` failures instead of duplicating
  the checks on parsed objects.
- The semantic lane is implemented with the frozen `process-rubric-v1` rubric and
  `semantic-prompt-v1` prompt: masked generating-model identity, no reference patch, one
  JSON-object request, Pydantic validation, rejection of any finding or first error citing a
  nonexistent step, tool call, patch file, test, or task field, exactly one schema-repair
  retry, and both raw responses persisted under ignored `.local/` state. Failure stays honest
  (`unavailable` / `context_limit`) and never fabricates a verdict.
- The merge policy produces contract-valid `EvaluationResult` records: deterministic
  inconclusive evidence skips the judge, hard process failures force `invalid` and outrank a
  contradicting semantic `valid` verdict (which becomes `partial` plus a human-review
  exclusion), the first error is the lowest validated material step restricted to
  agent-authored steps, and `correct_result_invalid_process` derives only from conclusive
  statuses.
- Two bounded live Hy3 semantic reviews are recorded under `.local/workbench/compatibility/`:
  the invalid fixture produced `invalid` with the first error at step 3 / `call-edit-1` /
  `task_interpretation` on the first attempt, matching the human oracle exactly, and the valid
  fixture produced `valid` with zero findings, so neither direction shows a schema failure or a
  false positive.

- SQLite persistence (`WorkbenchRepository`) stores manifests, runs, evaluations, and
  append-only human-review versions as contract-validated payloads; bundle imports are atomic
  with no partial writes, review versions are strictly sequential, and a stored evaluation is
  replaced only through an explicit `force` path that is refused once any review exists.
- The offline workflow is callable through FastAPI: health with database readiness, task/run
  listings, bundle import (canonical relative paths only; traversal, symlink escapes, layout
  errors, contract violations, hash mismatches, and duplicates are rejected), digest-idempotent
  evaluation (input plus evaluator/rubric/prompt versions plus judge configuration; changed
  configuration requires `force=true`), run/trajectory/evaluation reads, blinded initial
  reviews before adjudication versions, and deterministic exports.
- Exports rebuild `results/per_run/*.json` and `results/human_reviews.jsonl` from persisted
  records only and are byte-stable across repeated export calls.
- A restarted process on the same SQLite file preserves every imported run, evaluation, and
  review; an unconfigured judge returns an explicit 503 instead of a fabricated result.

- The evidence-debugger UI is implemented against the Day 4 API: a filterable run list with
  outcome/process/first-error columns, and a run detail page with an ordered ATIF step
  timeline, a marked first-error step and tool call, separate findings and deterministic-check
  lanes, finding-to-step and step-to-finding cross-highlighting, clickable evidence chips that
  navigate to the patch/verifier/task views, a colored diff, a per-test verifier table, and
  explicit exclusions for inconclusive runs instead of an invented verdict.
- Run-list and run-detail responses were extended in place (difficulty, first error, verified
  artifact texts); no new endpoint was added for the UI.
- Frontend tests run against recorded API responses captured from the real backend; nine
  Vitest tests cover the run list, filters, timeline order, first-error marking, both
  cross-highlight directions, the verifier and patch tabs, and inconclusive rendering.
- A full live check was recorded: the served backend imported the three bundles through the
  API, live Hy3 evaluations reproduced all three oracles again (first error at step 3,
  `call-edit-1`, `task_interpretation`; this time the judge also independently flagged the
  unsupported step-5 success claim as a second finding), and headless-browser screenshots
  confirmed the debugger renders the first error without raw JSON.

- The blinded review workflow is live in the UI: an unreviewed run hides the evaluator process
  verdict, first-error banner, and semantic findings while task, trajectory, patch, verifier,
  and deterministic-check evidence stay visible; saving the initial label reveals the verdict
  and offers adjudication with per-finding decisions; adjudicated runs show the immutable
  version history. Recorded initial labels demonstrably precede reveal timestamps.
- `MetricCalculator` derives every required metric from persisted records only — final-answer
  accuracy, predicted and adjudicated process-correctness rates, incorrect-run error-detection
  accuracy, exact and within-one-step localization, correct-result confirmed-problem and
  false-positive rates, primary-error distribution, and per-difficulty tables — each with an
  explicit numerator, denominator, exclusion list, and human/evaluator/mixed/official
  provenance. Empty denominators yield null values, never fabricated zeros.
- The adjacent-difficulty decline test bootstraps with a fixed recorded seed and reports
  `not_established` unless the full interval lies below zero; empty bands can never fabricate
  an interval.
- `GET /api/analytics/summary` serves the typed summary, `/analytics` renders the quadrant,
  distribution, difficulty table with denominators, decline statement, exclusions, and case
  links, and exports now include deterministic `results/summary.json` and
  `results/metrics.csv`.
- A live browser check recorded the full flow on real judge data: blinded label at step 3,
  reveal, adjudication, and the analytics page computing 100% exact localization for the
  labeled run with the inconclusive run explicitly excluded.

Current phase:

- **Day 7 — real Hy3/Harbor/SWE-bench integration.**
- Days 1–6 are complete. Stage A (the controlled offline evaluator) is finished; Stages B and
  C (real recorded validation data and the reproducible live workflow) remain.

## Fixed execution decisions

These decisions prevent scope drift. Change one only when implementation evidence is recorded in
this file and the affected specification is updated.

1. **Offline first, but not fixture-only at submission.** Controlled fixtures build and validate
   the evaluator. The final evidence includes a small difficulty-covering slice of recorded real
   Hy3 runs and at least one reproducible live task workflow.
2. **SWE-bench Verified remains the primary real-world benchmark.** A task's deterministic standard
   answer is its pinned behavioral test contract (`FAIL_TO_PASS` plus `PASS_TO_PASS`), not exact
   patch text. The reference patch proves solvability and supports later human adjudication; it is
   hidden from the agent and initial semantic judge.
3. **ATIF v1.7 is the only process format.** Harbor converts mini-SWE-agent's native trace to
   `agent/trajectory.json`; the workbench does not invent a competing trajectory schema.
4. **Evaluation is hybrid.** Deterministic code establishes facts, one fixed Hy3 semantic-judge
   configuration evaluates meaning, and human review establishes validation ground truth.
5. **Human review is mandatory.** Every gradeable incorrect run receives a human process/first-error
   label, and every resolved run flagged process-invalid is manually audited. Initial labels are
   captured before the Hy3 verdict is revealed.
6. **No judge-model chooser in the MVP UI.** The agent model and semantic-judge model remain
   separately configurable internally, and every evaluation records the judge configuration.
7. **All project data stays inside the repository.** Small sanitized inputs live under `data/`;
   mutable or large benchmark data, trajectories, verifier artifacts, and reviews live under the
   ignored `.local/`; sanitized final evidence lives under `results/`. Machine-level developer
   tools such as uv, Node, fnm, Docker, and Git are not project data.
8. **ARM64 is valid for application and offline work, not assumed for official images.** Native
   Harbor tasks work on the DGX Spark. A selected SWE-bench task must pass a source-built ARM64
   oracle check or run on a short-lived native x86-64 host before the real evaluation slice begins.

## Delivery strategy

```text
Stage A — controlled offline evaluator
    typed contracts -> fixture bundles -> deterministic evidence
    -> structured Hy3 review -> merge -> API -> evidence debugger

Stage B — recorded real validation data
    small difficulty-covering SWE-bench slice -> ATIF + verifier artifacts
    -> evaluator predictions -> blinded human labels -> adjudication

Stage C — reproducible final workflow
    one live Hy3 task -> official verification -> ATIF import
    -> process diagnosis -> human review -> aggregate evidence and demo
```

Stage A requires no benchmark container. Stages B and C may generate runs on a compatible host, but
the resulting project data is copied into this repository's configured `.local/` paths before
evaluation. A development fixture proves software behavior; it is not counted as final benchmark
evidence unless its source, checker, difficulty, Hy3 trajectory, and human label meet the final
evaluation-set contract.

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

## Outcome sequence

| Status | Day | Objective | Exit condition |
| --- | --- | --- | --- |
| Complete | **1 — Contracts and fixtures** | Implement typed core schemas, immutable artifact identity, controlled ATIF fixture bundles, and one structured Hy3 compatibility response. | Hy3 JSON-object behavior is recorded; valid, invalid, and inconclusive fixture bundles validate offline; artifact hashes and human expected labels are stable. |
| Complete | **2 — Deterministic evaluator** | Validate ATIF/artifact identity; extract verifier, patch, command, and integrity facts; implement outcome/inconclusive policies and unit tests. | Fixtures produce reproducible deterministic checks without a model call, and malformed/missing evidence becomes inconclusive. |
| Complete | **3 — Semantic evaluator** | Implement the versioned rubric, fixed Hy3 judge, evidence-reference validation, one schema-repair retry, and merge policy. | Invalid and valid fixtures produce typed, evidence-linked results; semantic failure remains honest and inspectable. |
| Complete | **4 — API and persistence** | Add SQLite indexes, immutable artifact registration, import/evaluate/read/review endpoints, exports, and restart/interruption behavior. | The offline workflow is callable through FastAPI and survives process restart without corrupting evidence. |
| Complete | **5 — Evidence debugger UI** | Build run list and run detail; connect findings to ATIF steps, command observations, patch, and verifier artifacts. | A user can understand the first error without reading raw JSON. |
| Complete | **6 — Human review and analytics** | Implement evaluator-hidden initial labels, adjudication, provenance-aware metrics, difficulty/error views, exclusions, and case links. | Required human records and aggregate metrics can be produced from fixtures without contaminating blinded labels. |
| **Current** | **7 — Real Hy3/Harbor integration** | Validate one compatible environment/oracle, run a minimal task and one selected SWE-bench Verified task through Hy3, and confirm ATIF v1.7 conversion. | One real Hy3 run produces a patch, official verifier artifacts, an ATIF trajectory, and a workbench diagnosis. |
| Pending | **8 — Evaluation and validation** | Freeze a small difficulty-covering task slice; run sequentially; label every gradeable incorrect run and audit every resolved-and-flagged run. | Required localization and false-positive evidence exists with explicit numerators, denominators, exclusions, and label provenance. |
| Pending | **9 — Analysis and differentiation** | Export final metrics/report/case studies; implement the regression card only if core evidence is complete; finish README and setup documentation. | Submission artifacts tell one coherent task-to-diagnosis-to-analysis story. |
| Pending | **10 — Delivery freeze** | Perform a clean-environment run, tests/build, requirement/security/reproducibility audits, UI polish, demo rehearsal and recording, and public-repository preparation. | A reviewer can set up the project, inspect evidence, reproduce the documented path, and view a demo under two minutes. |

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
- No fixture-only result is presented as the final benchmark evaluation.
- No semantic finding is accepted when it cites a nonexistent step, tool call, file, test, or task field.
- No live benchmark batch begins before one compatible oracle/environment check passes.
- No project benchmark data, trajectory, verifier artifact, or review record is stored outside this repository.
