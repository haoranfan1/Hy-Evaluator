# Next Steps

## Status

**Current gate: Day 7 real Hy3/Harbor/SWE-bench integration.**

Completed prerequisites:

- Stage A is finished: contracts, fixtures, the deterministic lane, the fixed Hy3 judge with
  merge policy, SQLite persistence, the FastAPI workflow, the evidence-debugger UI, the blinded
  review flow, and provenance-aware analytics with deterministic exports.
- 94 backend tests, 14 frontend tests, Ruff, typecheck, and both builds pass; live checks
  reproduced the fixture oracles with the real Hy3 judge and exercised the blinded review and
  analytics pages end to end.
- Recorded environment facts: Harbor 0.22.0 passed a native ARM64 lifecycle smoke test; the
  official SWE-bench smoke image is AMD64-only; qemu binfmt is not registered on this host.

## Single next action

Produce one real SWE-bench Verified run end to end, gated behind a passing oracle check.

```text
select one SWE-bench Verified task (prefer a source-buildable ARM64 candidate)
    -> oracle/environment check: gold patch satisfies FAIL_TO_PASS + PASS_TO_PASS
    -> Harbor + mini-SWE-agent + Hy3 run (sequential, concurrency 1)
    -> ATIF v1.7 trajectory + generated patch + official verifier artifacts
    -> HarborImporter: dataset row + trial -> manifest/run bundle under .local
    -> workbench import -> deterministic + semantic evaluation -> debugger diagnosis
```

Required behavior:

1. No live benchmark run starts before one oracle/environment check passes and is recorded
   (task id, image or build provenance, host, and the check output). Environment paths in
   preference order: a source-built ARM64 task image on this host; qemu binfmt emulation
   (requires a user-approved system change); a short-lived x86-64 host with artifacts copied
   back into `.local/` (requires user-approved cost).
2. Run the selected task through Harbor with mini-SWE-agent and the configured Hy3 model,
   sequentially, with project-scoped names and paths; never store benchmark data outside the
   repository's configured `.local/` locations.
3. Implement `HarborImporter`: build the `TaskManifest` from the pinned dataset row
   (behavioral-test contract, official difficulty label, problem statement, source links,
   protected paths) and the `RunRecord` from the completed trial (ATIF trajectory, generated
   patch, verifier report and logs, hashed artifact identities); reject trials whose ATIF or
   artifacts fail validation.
4. Map the official verifier output into the report contract the deterministic lane reads, or
   extend the lane with a clearly versioned adapter — without weakening the
   inconclusive-before-model-call policy.
5. Import and evaluate the run through the existing API and inspect it in the debugger; the
   semantic review runs against live Hy3 with the recorded judge configuration.
6. Record the full reproduction path (commands, versions, digests, configuration) so the run
   can be repeated on a compatible host.

## Exit condition

The gate is complete when one real SWE-bench Verified task has a recorded passing oracle
check, a completed Hy3 agent run with an ATIF v1.7 trajectory, generated patch, and official
verifier artifacts stored under `.local/`, and the imported run produces a full workbench
diagnosis (deterministic checks, semantic review, merged result) visible in the debugger —
with the reproduction path documented and the entire test suite still passing.

## Explicitly deferred

- The frozen difficulty-covering evaluation slice and its blinded human labels: Day 8.
- Final metrics/report/case-study exports and differentiation features: Day 9.
- Delivery freeze, clean-environment run, and demo recording: Day 10.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
