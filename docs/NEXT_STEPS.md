# Next Steps

## Status

**Current gate: Day 3 semantic evaluator and merge policy.**

Completed prerequisites:

- Strict contracts, verified fixture bundles, the offline evidence gate, and the recorded Hy3
  JSON-object compatibility check from Day 1.
- The Day 2 deterministic lane (`EvidenceExtractor`): identity and hash verification, ATIF
  structure validation, per-test verifier records, coverage/consistency rules, the
  resolved/unresolved/inconclusive outcome policy, patch scope and sensitive-file warnings,
  protected-path hard process failures, advisory command-failure facts, and final-claim
  comparison.
- Ungradeable-run classification from verifier logs: evidenced patch-application failure is
  agent-caused unresolved; infrastructure markers become inconclusive exclusions.
- `EvidenceResolver` guarantees every emitted evidence reference resolves to a real task field,
  ATIF step/tool call, patch file, verifier artifact, or declared test.
- 53 backend tests and Ruff pass without Docker, Harbor execution, or a model call.

## Single next action

Implement the semantic lane and the merge policy against the fixture bundles, using mocked judge
responses in tests and at most bounded, recorded live Hy3 checks stored under ignored `.local/`
state.

```text
deterministic evidence (ready)
    -> versioned rubric + masked bundle evidence -> fixed Hy3 judge (JSON object)
    -> SemanticReviewOutput validation -> evidence-reference validation
    -> one schema-repair retry -> merge precedence
    -> typed EvaluationResult with provenance
```

Required behavior:

1. Define frozen `rubric_version` and `semantic_prompt_version` values and record them in every
   result.
2. Build the judge input from the problem statement and allowed task metadata, complete ATIF
   steps in order, the generated patch, verifier evidence, and deterministic checks. Mask the
   generating model identity and never include the reference patch.
3. Request one JSON object, validate it against `SemanticReviewOutput`, and reject any finding
   or first error whose reference fails `EvidenceResolver`.
4. On validation failure, send exactly one repair retry containing the validation errors and no
   new task evidence; persist both raw responses under ignored `.local/` state.
5. If both attempts fail, mark the semantic lane unavailable and return the deterministic facts
   in a `partial` result. Never fabricate a semantic verdict.
6. Skip the judge entirely when the deterministic lane is `inconclusive` or the rendered input
   exceeds the configured context limit (`inconclusive: context_limit`).
7. Apply the merge precedence from `EVALUATOR_SPEC.md`: inconclusive forcing, deterministic hard
   failures forcing `invalid`, validated semantic material findings, contradiction handling as
   `partial`, and lowest-validated-step first-error selection.
8. Derive `correct_result_invalid_process` only from conclusive outcome and process statuses.

## Exit condition

The gate is complete when:

1. The valid fixture merges to `completed` with `process_status=valid`, no first error, and
   `correct_result_invalid_process=false` under a mocked valid judge response.
2. The invalid fixture merges to `completed` with `process_status=invalid`, the first error at
   step 3 with a primary category, and evidence-linked findings under a mocked judge response.
3. A mocked judge response citing a nonexistent step, tool call, file, or test is rejected,
   repaired at most once, and otherwise yields an honest `partial` result without a semantic
   verdict.
4. The inconclusive fixture produces no judge call and stays `inconclusive`.
5. Merged results validate against `EvaluationResult`, and raw judge responses are persisted
   only under ignored `.local/` paths.
6. The full backend test suite and Ruff pass without Docker or a live benchmark task; any live
   Hy3 usage is bounded, recorded, and optional for the tests.

## Explicitly deferred

- SQLite/API workflow: Day 4.
- Evidence-debugger UI: Day 5.
- Human-review UI and analytics: Day 6.
- Real Hy3/Harbor/SWE-bench execution: Day 7.
- Regression cards, comparison views, and decorative polish: only after mandatory evidence passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
