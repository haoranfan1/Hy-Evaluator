# Data

This directory contains tracked, sanitized evaluator inputs. The metadata and review contracts are
defined in [Evaluator Specification](../docs/EVALUATOR_SPEC.md).

Current tracked fixtures:

- `fixtures/valid/`: resolved result with a valid inspected, reproduced, repaired, and verified process.
- `fixtures/invalid-first-error/`: unresolved result with a human-labeled first material error at
  agent step 3 and tool call `call-edit-1`.
- `fixtures/inconclusive-missing-evidence/`: infrastructure interruption with an intentionally
  incomplete verifier report that must remain inconclusive.

Each bundle includes `manifest.json`, Harbor-compatible ATIF v1.7 `trajectory.json`, `run.json`
with project-relative SHA-256 artifact identities, patch and verifier artifacts, `expected.json`,
and an immutable human-review oracle. A future `manifests/swebench_verified.jsonl` will hold the
selected real-task slice and provenance.

Live Harbor jobs, benchmark datasets, raw API output, and mutable review state belong under the
ignored project-local `.local/` directory. The structured Hy3 compatibility record is stored at
`.local/workbench/compatibility/hy3-structured.json`. Final sanitized evaluation evidence belongs
under `results/` and is committed only after validation.

The official gold patch is provenance, not the only valid answer. It must never be exposed to Hy3 during task execution or initial semantic review.

Do not add private, licensed-without-permission, or credential-bearing data.
