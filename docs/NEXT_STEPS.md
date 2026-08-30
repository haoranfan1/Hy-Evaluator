# Next Steps

## Status

**Current gate: Day 2 deterministic evidence extraction and outcome policy.**

Completed prerequisites:

- Python 3.12/FastAPI and Node 24/React environments build and test successfully with locked
  dependencies.
- The bounded Hy3 handshake, native ARM64 Harbor smoke test, and AMD64 image compatibility check
  are recorded.
- Strict contracts cover manifests, runs, artifacts, evidence, findings, results, semantic output,
  and immutable human-review versions.
- The tracked valid, invalid-first-error, and inconclusive-missing-evidence bundles parse against
  the project contracts and Harbor ATIF v1.7 models.
- Every fixture artifact is project-relative and verified by SHA-256.
- The offline gate produces resolved, unresolved, and inconclusive outcomes without a model call.
- One live Hy3 JSON-object response validated locally against `SemanticReviewOutput`; the
  sanitized compatibility record remains under ignored project-local `.local/` state.

## Single next action

Implement the deterministic lane without Docker, Harbor execution, a live benchmark task, or
another model request.

```text
validated fixture bundle
    -> identity and ATIF checks
    -> verifier-contract outcome
    -> patch and command facts
    -> integrity warnings or hard failures
    -> typed deterministic checks and exclusions
```

Required behavior:

1. Validate ATIF v1.7, sequential step IDs, and tool/observation references.
2. Verify manifest, run, trajectory, patch, and verifier artifact identity and hashes.
3. Classify `resolved`, `unresolved`, or `inconclusive` from the behavioral-test evidence.
4. Record each declared `FAIL_TO_PASS` and `PASS_TO_PASS` result and any missing tests.
5. Extract changed files and patch breadth; warn on tests, generated files, lockfiles, and broad scope.
6. Detect manifest-protected path access or modification as an evidence-backed hard process failure.
7. Extract command/tool failures and compare explicit final success claims with observed evidence.
8. Keep ordinary failed exploration advisory unless later evidence makes it materially relevant.

Outputs remain deterministic facts and rules. First-error semantic diagnosis and merge precedence stay
out of this gate.

## Exit condition

The gate is complete when:

1. All three fixtures produce stable deterministic checks and the expected outcome status.
2. Missing, malformed, or identity-mismatched evidence forces `inconclusive` before any model call.
3. Every emitted evidence reference resolves to a real task field, ATIF step/tool call, patch file,
   verifier artifact, or declared test.
4. Patch breadth, command failures, protected-path behavior, and final success claims have focused
   unit tests.
5. Only evidence-backed process-integrity conditions set `hard_process_failure=true`.
6. The full backend test suite and Ruff pass without Docker or a live benchmark task.

## Explicitly deferred

- Full semantic reviewer, evidence-reference repair retry, and merger: Day 3.
- SQLite/API workflow: Day 4.
- Evidence-debugger UI: Day 5.
- Human-review UI and analytics: Day 6.
- Real Hy3/Harbor/SWE-bench execution: Day 7.
- Regression cards, comparison views, and decorative polish: only after mandatory evidence passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
