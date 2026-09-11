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
- `evaluation-slices/guardrail-slice-v1.json`: the frozen guardrail intervention rerun of the
  day8 easy stratum — fixed comparison set, the verbatim guardrail text, run configuration,
  and the blinding/comparison protocol, recorded before any environment rebuild or run.
- `agent-configs/guardrail-v1.yaml`: the intervention agent configuration — the recorded day8
  baseline system template plus exactly one appended constraint paragraph.
- `environment-checks/`: recorded oracle/environment gates (host, images, commands, outcomes)
  showing every selected task resolved under its gold patch on the source-built ARM64 images
  before any agent run.

Recorded real-run bundles (`runs/<run_id>/`, one per imported Harbor trial; twelve at `v1.0`:
the eight `day8-slice-v1` runs, the Day 7 integration run on django-15851, and the three
`guardrail-slice-v1` reruns):

- `manifest.json`: the task contract — repository, base commit, problem statement, source
  issue/PR, official difficulty, protected paths, and the **standard answer** (declared
  `FAIL_TO_PASS` / `PASS_TO_PASS` tests), plus the reference patch as adjudication-only
  provenance.
- `trajectory.json` (ATIF v1.7), `patch.diff`, `verifier-report.json` (the official
  `swebench` `report.json`, unmodified), `test-output.txt`, `reference-patch.diff`, and
  `run.json` with the SHA-256 identity of every artifact.
- The Harbor trial log (`run.log`) was not retained in the public copy; `run.json` records
  `run_log: null` rather than pointing at a missing file. Every other artifact hash matches
  the recording host's bundle byte for byte.
- These bundles are the raw evidence behind `results/`; `scripts/verify_outcome.py --all
  data/runs` re-applies each standard answer to its official report, and any bundle imports
  into a fresh workbench through `POST /api/runs/import`.

Live Harbor jobs, benchmark datasets, raw API output, and mutable review state belong under the
ignored project-local `.local/` directory. The structured Hy3 compatibility record is stored at
`.local/workbench/compatibility/hy3-structured.json`. Final sanitized evaluation evidence belongs
under `results/` and is committed only after validation.

The official gold patch is provenance, not the only valid answer. It must never be exposed to Hy3 during task execution or initial semantic review.

Do not add private, licensed-without-permission, or credential-bearing data.
