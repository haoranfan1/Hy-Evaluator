# Data

This directory contains tracked, sanitized evaluator inputs. The metadata and review contracts are
defined in [Evaluator Specification](../docs/EVALUATOR_SPEC.md).

Current tracked fixtures:

- `fixtures/valid/`: resolved result with a valid inspected, reproduced, repaired, and verified process.
- `fixtures/invalid-first-error/`: unresolved result with a human-labeled first material error at
  agent step 3 and tool call `call-edit-1`.
- `fixtures/invalid-relative-path/`: resolved result whose process modifies the protected graded
  test file through a path relative to a `cd`-established working directory — the day8
  django-15278 evasion pattern — with a human-labeled first error at agent step 4 and tool call
  `call-edit-1` (added with `workbench-evaluator-v3`).
- `fixtures/inconclusive-missing-evidence/`: infrastructure interruption with an intentionally
  incomplete verifier report that must remain inconclusive.

Each bundle includes `manifest.json`, Harbor-compatible ATIF v1.7 `trajectory.json`, `run.json`
with project-relative SHA-256 artifact identities, patch and verifier artifacts (including
`run.log`, tracked by an explicit `.gitignore` negation), `expected.json`, and an immutable
human-review oracle.

Real-task records:

- `evaluation-slices/day8-slice-v1.json`: the frozen eight-task SWE-bench Verified slice —
  dataset revision pin, seeded difficulty-stratified selection with the full candidate order,
  frame constraints, substitution rule, run configuration, and the blinding protocol, all
  recorded before any run.
- `environment-checks/`: recorded oracle/environment gates (host, images, commands, outcomes)
  showing every selected task resolved under its gold patch on the source-built ARM64 images
  before any agent run.

Live Harbor jobs, benchmark datasets, raw API output, and mutable review state belong under the
ignored project-local `.local/` directory. The structured Hy3 compatibility record is stored at
`.local/workbench/compatibility/hy3-structured.json`. Final sanitized evaluation evidence belongs
under `results/` and is committed only after validation.

The official gold patch is provenance, not the only valid answer. It must never be exposed to Hy3 during task execution or initial semantic review.

Do not add private, licensed-without-permission, or credential-bearing data.
