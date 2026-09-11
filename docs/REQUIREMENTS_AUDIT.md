# Requirements Audit — Delivery Freeze

Audited 2026-08-31 (Day 10) against every item of
[PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md), using its §10 acceptance checklist as the
walk order. Each row records where the requirement is satisfied and the committed evidence.
Gaps found by this audit and their fixes are listed at the end.

Re-walked 2026-09-11 at the delivery tag `v1.0`: rows whose evidence moved after Day 10
(evaluator v3, the narrated demo, test counts) were updated in place; the Day 10
clean-environment record is kept as recorded and a second record at `v1.0` follows it.

## Acceptance checklist walk

| # | Requirement (§10) | Status | Where satisfied / evidence |
| --- | --- | --- | --- |
| 1 | Verifiable domain selected and justified | Satisfied | Code tasks on SWE-bench Verified; each task's official behavioral tests are the automatic criterion. [REPORT §2](REPORT.md), [research workspace](research/README.md) |
| 2 | Hy3 application runs and outputs a step-by-step solution | Satisfied | mini-swe-agent 2.4.6 driven by Hy3 through Harbor 0.22.0 emits ATIF v1.7 step trajectories; the workbench renders the step timeline. Nine real runs in `results/per_run/`; pipeline scripts `scripts/prepare_swebench_task.py`, `scripts/import_harbor_trial.py` |
| 3 | Every item has a standard answer and automatic checker | Satisfied | Standard answer = the declared FAIL_TO_PASS/PASS_TO_PASS tests, committed per task in `data/runs/*/manifest.json`; graded by `swebench==4.0.3` in-container through Harbor's verifier, and re-checkable from the committed official reports with `scripts/verify_outcome.py` (12/12 resolved). Gold patch retained as adjudication-only provenance. Oracle gates: `data/environment-checks/` (8/8 slice tasks + the integration task gold-resolved) |
| 4 | Evaluation set spans documented difficulty levels | Satisfied | Official SWE-bench Verified difficulty annotations; slice stratified over `<15 min` / `15 min–1 h` / `1–4 h`. `data/evaluation-slices/day8-slice-v1.json`; difficulty tables in [REPORT §4](REPORT.md) and `results/summary-day8-slice-v1.json` |
| 5 | Item sources, construction, difficulty criteria documented | Satisfied | Pinned dataset revision `c104f840…`, seeded stratified selection with full recorded candidate order, frame constraints, substitution rule. `data/evaluation-slices/day8-slice-v1.json`, [data/README.md](../data/README.md), [REPORT §2](REPORT.md) |
| 6 | Evaluator judges process correctness | Satisfied | Deterministic + fixed Hy3 semantic + blinded human lanes under fixed merge precedence. `src/hy3_workbench/{evidence_extractor,semantic_reviewer,evaluator}.py`; [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md); 213 offline backend tests and 51 frontend tests at `v1.0.1` (167 backend at `v1.0`, before the `data/runs` and answer-check suites) |
| 7 | Evaluator identifies the first erroneous step | Satisfied | `first_error` contract over stable ATIF step ids; v2 anchors at the first successful write. `src/hy3_workbench/contracts.py`; [REPORT §6](REPORT.md) |
| 8 | Domain-appropriate error taxonomy documented and implemented | Satisfied | [EVALUATOR_SPEC.md §Error taxonomy](EVALUATOR_SPEC.md); `ErrorCategory` literal in `contracts.py`; `process-rubric-v1` |
| 9 | Correct-answer/invalid-process cases detected | Satisfied | Four confirmed cases (all modified the protected graded test file); quadrant + `correct_result_confirmed_problem_rate` in exports. [REPORT §1/§4/§5](REPORT.md) |
| 10 | Localization accuracy measured on incorrect-answer samples | Satisfied, mapping documented | The frozen slice contains no unresolved runs, so the incorrect-run metrics are honestly 0/0; localization is validated on human-confirmed invalid processes (v1 0/4 → v2 3/4 → v3 4/4 exact vs frozen labels) plus the synthetic unresolved fixture with a known step-3 oracle (judge unanimous 5/5). [REPORT §4/§6/§7](REPORT.md); `results/regression/day9-regression-card.json`, `results/regression/day11-regression-card-v3.json`; `results/judge-stability/` |
| 11 | False positives manually audited on correct-answer samples | Satisfied | Every flagged correct-answer run adjudicated: v1 flagged 7, 3 rejected as false positives (all read-only references); v2 and v3 regression cards 0/4 false positives. [REPORT §4/§6](REPORT.md); `results/human_reviews.jsonl` |
| 12 | Human-inspection records retained | Satisfied | Append-only review versions (blinded initial + adjudications) exported to `results/human_reviews.jsonl`; blinding protocol frozen in the slice file; fixture oracles in `data/fixtures/*/human-review.json` |
| 13 | Final-answer accuracy reported | Satisfied | 8/8 resolved (official verifier). `results/summary-day8-slice-v1.json`, `results/metrics-day8-slice-v1.csv`, [REPORT §1](REPORT.md) |
| 14 | Process-correctness rate reported | Satisfied | Adjudicated 4/8 (human); predicted 0/7 (evaluator v1) — both with provenance. Same exports; [REPORT §4](REPORT.md) |
| 15 | Error-type distribution reported | Satisfied | `primary_error_distribution` in the summary exports (all four confirmed first errors: `process_integrity`); stated in [REPORT §4](REPORT.md) |
| 16 | Results analyzed by difficulty | Satisfied | Difficulty table per band; the process-validity inversion (easy 0/3 valid, hard 2/2) is the headline qualitative finding. [REPORT §1/§4](REPORT.md) |
| 17 | Decline interval, capability boundary, critical points analyzed | Satisfied | Outcome decline `not_observed` (100% every band; bootstrap verdict `not_established`, seed 20260830) — reported honestly rather than invented; capability boundaries analyzed via the four case studies (graded-test tampering, harness awareness, context-limit abstention). [REPORT §1/§4/§5/§8](REPORT.md) |
| 18 | Code, scripts, dataset, answers, config example, docs public | Satisfied | Full source + tests + scripts + docs in the repository; `.env.example`; the evaluation set with its standard answers and every recorded run's raw artifacts are committed under `data/runs/` (re-walk gap 6); the pinned public dataset revision remains the provenance |
| 19 | Secrets excluded | Satisfied | This audit scanned every committed file for the real key, endpoint, token patterns, and personal data: none present. `/home/` and machine names appear only inside the hygiene test's own assertion. Enforced continuously by `tests/test_fixtures.py::test_fixtures_contain_no_absolute_machine_paths_or_secret_fields` and the export tests |
| 20 | Repository labeled as an individual/event project | Satisfied | README banner line; not an official Tencent release |
| 21 | Demo ≤ 2 minutes | Provided; length exceeds the brief | [demo/hy3-workbench-demo.mp4](demo/hy3-workbench-demo.mp4) (4 min 22 s, 1920×1080, Chinese voice-over per [DEMO_NARRATION.zh-CN.md](DEMO_NARRATION.zh-CN.md)), recorded 2026-09-11 by the operator against an isolated copy of the workbench state; shows one complete workflow (task → process evaluation → validation) with a narrated introduction of the problem and each view. The operator chose to exceed the two-minute bound for the sake of the introduction; the [DEMO.md](DEMO.md) driver still yields a ≈63-second cut of the same scenes if a strict-length version is requested. Frozen store verified untouched afterwards (fixture review count 2, 20 review versions, `results/` and `data/` unchanged) |

## Deliverables (§8)

- **8.1 Public repository**: runnable source, evaluator module, README, `.env.example`,
  [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md). Satisfied.
- **8.2 Evaluation materials**: `data/evaluation-slices/day8-slice-v1.json` (difficulty-layered
  set); standard answers per task in `data/runs/*/manifest.json`; final-answer validation by
  the official in-container grader (recorded task copies + Harbor verifier) and
  `scripts/verify_outcome.py` over the committed official reports; `scripts/evaluate_run.py` +
  the workbench API (process evaluation). Satisfied.
- **8.3 Complete results**: `results/summary*.json`, `results/metrics*.csv`, per-run exports;
  final-answer accuracy, process-correctness rates, error distribution, difficulty breakdown.
  Satisfied.
- **8.4 Effectiveness-validation evidence**: `results/regression/day9-regression-card.json`
  (localization + false positives vs frozen labels), `results/human_reviews.jsonl`
  (human-inspection records), `results/judge-stability/`. Satisfied.
- **8.5 Analysis report**: [REPORT.md](REPORT.md) — method rationale, taxonomy, case studies,
  capability boundaries, critical points, limitations. Satisfied.
- **8.6 Demonstration**: [demo/hy3-workbench-demo.mp4](demo/hy3-workbench-demo.mp4) (4 min 22 s, narrated; over the two-minute brief, see row 21)
  plus the [DEMO.md](DEMO.md) script and isolation protocol. Satisfied.

## Submission rules (§9)

Public repository (user-hosted), no PR to the official Hy3 repository, README explains the
project/run/environment, secrets only via environment variables, individual-project labeling,
model capabilities invoked through Hy3 (both the coding agent and the fixed judge), no
training or fine-tuning. All satisfied.

## Gaps found by this audit, and their fixes

1. **Fixture run logs untracked.** The blanket `*.log` ignore rule silently excluded
   `data/fixtures/*/run.log`, so a fresh clone failed 28 offline tests on missing artifacts
   whose hashes `run.json` declares. Found by the clean-environment verification; fixed by a
   scoped `.gitignore` negation and tracking the three logs (commit `d741524`).
2. **Stale slice pointer in `data/README.md`.** It still promised a "future
   `manifests/swebench_verified.jsonl`"; replaced with the real
   `evaluation-slices/` + `environment-checks/` records.
3. **Error-type distribution not named in the report.** Present in the exports but not stated
   in [REPORT §4](REPORT.md); one sentence added.
4. **Node pin never matched the verified runtime.** `.node-version` said 24.20.0 while every
   frontend test, typecheck, and build ran on 22.23.2; the pin now records the verified
   version and [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) states the supported range.
5. **Degraded-state behavior undocumented.** Without `.env`, the API health endpoint reports
   Hy3 unconfigured and `evaluate` refuses honestly instead of fabricating a verdict; now
   documented in [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md).

## Gaps found by the 2026-09-11 re-walk against the instruction PDF, and their fixes

6. **Standard answers and raw run artifacts were not in the public repository.** The
   task manifests (with the declared FAIL_TO_PASS/PASS_TO_PASS tests), trajectories,
   patches, and official verifier reports lived only under the ignored `.local/` on the
   recording host, so §8.2 "标准答案" was satisfied by pointer only and the case studies
   could not be verified from the clone. Fixed: the twelve recorded bundles are committed
   under `data/runs/` with project-relative paths (hashes byte-identical to the recording
   host's copies; the Harbor trial log was not retained and is recorded as `null`), covered
   by `tests/test_run_bundles.py` (identity, ATIF validity, evidence gate, secret/path
   hygiene, import into a fresh workbench).
7. **No answer-check script.** §8.2 asks for a "答案校验脚本"; grading ran only inside the
   Harbor verifier. Fixed: `scripts/verify_outcome.py` (`hy3_workbench.outcome_check`)
   re-applies each task's standard answer to its committed official report with exit codes
   0 resolved · 2 unresolved · 3 inconclusive · 4 unreadable, refuses to guess on missing,
   tampered, or non-covering reports, and is covered by `tests/test_outcome_check.py`.

## Clean-environment verification record

Host: the ARM64 DGX Spark (aarch64, Linux), system Node 22.23.2, `uv` on PATH; fresh
`git clone` of the local repository into an empty directory with **no `.env` and no `.local`**
(confirmed by the script before any step).

| Step | Command | Outcome |
| --- | --- | --- |
| Interpreter | `./scripts/uv-local python install 3.12` | cold-installed CPython 3.12.14 into the clone's `.local/uv/` |
| Dependencies | `./scripts/uv-local sync --all-groups` | resolved from committed `uv.lock` |
| Backend tests | `./scripts/uv-local run pytest -q` | first run: 28 failed on the untracked fixture logs (gap 1); after `d741524`: **128 passed** |
| Lint/format | `ruff check .` / `ruff format --check .` | clean |
| Frontend | `npm ci && npm test && npm run typecheck && npm run build` | **14 tests passed**, typecheck and production build clean |
| Degraded API | `WORKBENCH_PORT=8010 ./scripts/uv-local run hy3-workbench` with no `.env` | health endpoint up and honest about the unconfigured judge |
| Fixture import | `POST /api/runs/import` with `data/fixtures/valid` | imported with verified artifact hashes |
| Evaluation without judge | `POST /api/runs/{run_id}/evaluate` | honest 503 refusal: "Hy3 is not configured; set HY3_BASE_URL, HY3_MODEL, and HY3_API_KEY." (no fabricated verdict) |
| Reads | `GET /api/runs`, `GET /api/runs/{run_id}`, `GET /api/analytics/slices` | all serve committed/imported data |

## Clean-environment verification record — delivery tag `v1.0` (2026-09-11)

Host: Apple Silicon macOS (arm64), `uv` 0.11.8 and `fnm` on PATH, Node 22.23.2 selected from
`.node-version`; fresh `git clone` of the public GitHub repository at tag `v1.0` (commit
`1d189c3`) into an empty directory with **no `.env` and no `.local`** (checked before any step).

| Step | Command | Outcome |
| --- | --- | --- |
| Interpreter | `./scripts/uv-local python install 3.12` | cold-installed into the clone's `.local/uv/` |
| Dependencies | `./scripts/uv-local sync --all-groups` | resolved from the committed `uv.lock` |
| Backend tests | `./scripts/uv-local run pytest -q` | **167 passed** |
| Lint | `./scripts/uv-local run ruff check .` | clean |
| Frontend | `npm ci && npm test && npm run typecheck && npm run build` | **51 tests passed**, typecheck and production build clean |
