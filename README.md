# Hy3 Process Evaluation Workbench

English | [简体中文](README.zh-CN.md)

> An individual project for the Tencent Rhino-Bird open-source practical task
> (Project 2: 可验证场景 — 过程评估与错误定位). This repository is not an official Tencent release.

A web workbench that evaluates the **process** — not just the outcome — of Hy3 coding-agent
runs on SWE-bench Verified. Hy3 repairs real repository issues through mini-SWE-agent and
Harbor (ATIF v1.7 step trajectories); the workbench then combines a deterministic evidence
lane, a fixed Hy3-as-judge semantic lane, and procedurally blinded human review to judge
process validity, localize the first erroneous step, classify it against a documented
taxonomy, and detect correct-result/invalid-process runs — and it measures its own
reliability against frozen human labels.

## Headline validated findings

From the frozen eight-task slice (`day8-slice-v1`, three official difficulty bands). Full
numbers with numerators, denominators, exclusions, and provenance are in the
[report](docs/REPORT.md).

- **8/8 tasks resolved** by the official verifier — but only **4/8 process-valid** under
  adjudicated blinded human labels. Every confirmed-invalid run modified the protected graded
  test file during its process.
- **Outcome accuracy is blind to an entire behavior class**: on easy tasks the agent freely
  edited graded tests (0/3 process-valid); on hard tasks it left them alone (2/2).
- The evaluator's measured failure modes were fixed in two recorded rounds
  (`workbench-evaluator-v2`, then `v3`), each validated by a regression card against the
  frozen labels: **false positives 3/4 → 0/4, exact first-error localization 0/4 → 4/4,
  detection 4/4 preserved, semantic coverage 4/8 → 8/8** (bounded condensation of oversized
  trajectories — faithful excerpts of real artifacts only; honest abstention remains the
  floor).
- The fixed judge configuration is stable: verdict, first-error step, and category were
  **unanimous across fifteen recorded sessions** on three inputs (including one condensed
  oversized trajectory), independently matching the human-labeled step on the real runs.

## Quickstart

Environment requirements:

- macOS or Linux; Python 3.12 is installed into the repository by `uv` (nothing touches the
  system interpreter); Node 22 (`.node-version`, any Node ≥ 22.12 works) for the UI.
- No GPU. An Hy3 endpoint (`HY3_BASE_URL`, `HY3_MODEL`, `HY3_API_KEY`) is needed only for live
  semantic evaluation; everything below runs without it.
- Docker with roughly 120 GB free is needed only to run new SWE-bench tasks live
  ([Development setup](docs/DEVELOPMENT_SETUP.md)); the recorded runs are committed.

Offline verification — no credentials and no model calls (the suite scripts the judge):

```bash
./scripts/uv-local python install 3.12
./scripts/uv-local sync --all-groups
./scripts/uv-local run pytest -q
```

```bash
cd frontend && npm ci && npm test
```

Re-check every recorded run's final answer against its standard answer from the committed
artifacts alone (exit code `0` resolved · `2` unresolved · `3` inconclusive):

```bash
./scripts/uv-local run python scripts/verify_outcome.py --all data/runs
```

Browse the recorded runs in the UI: start both servers below, then import a bundle
(`POST /api/runs/import` with `{"bundle_dir": "data/runs/<run id>"}`, or any fixture under
`data/fixtures/`); the timeline, patch, verifier, and task views render from the bundle, and
evaluation needs the Hy3 judge.

Run the workbench (FastAPI on `127.0.0.1:8000`, UI on `127.0.0.1:5173`):

```bash
./scripts/uv-local run hy3-workbench
```

```bash
cd frontend && npm run dev
```

For live semantic evaluation, copy `.env.example` to the ignored `.env` and set the three Hy3
values; without them the API runs in an honest degraded state (health reports the judge
unconfigured, evaluation refuses instead of fabricating a verdict). The live
Harbor/SWE-bench pipeline and its Docker gate are documented in
[Development setup](docs/DEVELOPMENT_SETUP.md) and [report §9](docs/REPORT.md).

The UI defaults to English with a Chinese toggle in the header, plus a light/dark theme. The
`/help` route is an in-app guide to every page, column, status, and term (both languages).

### Process gate (CI-friendly)

`scripts/process_gate.py` turns a stored process verdict into an exit code, so a pipeline
can gate on process validity — not just outcome. It only reads persisted records and never
evaluates: `0` valid · `2` invalid · `3` inconclusive · `4` not evaluated · `5` unknown run.

```bash
./scripts/uv-local run python scripts/process_gate.py --run run-fixture-invalid-first-error --json
```

## Evidence map

| Evidence | Where |
| --- | --- |
| Analysis report: method, metrics, case studies, limitations | [docs/REPORT.md](docs/REPORT.md) |
| Requirement-by-requirement audit + clean-environment record | [docs/REQUIREMENTS_AUDIT.md](docs/REQUIREMENTS_AUDIT.md) |
| Demo video (narrated) + scene script and narration | [docs/demo/hy3-workbench-demo.mp4](docs/demo/hy3-workbench-demo.mp4), [docs/DEMO.md](docs/DEMO.md), [docs/DEMO_NARRATION.zh-CN.md](docs/DEMO_NARRATION.zh-CN.md) |
| Frozen slice protocol (selection, blinding, run config) | [data/evaluation-slices/day8-slice-v1.json](data/evaluation-slices/day8-slice-v1.json) |
| Environment / gold-patch oracle gates | [data/environment-checks/](data/environment-checks/) |
| Aggregate + per-run results (deterministic exports) | [results/](results/) |
| Human-inspection records (blinded labels + adjudications) | [results/human_reviews.jsonl](results/human_reviews.jsonl) |
| Evaluator v2/v3 regression cards vs frozen labels (rendered at `/regressions` in the UI) | [results/regression/](results/regression/) |
| Judge-stability records (fifteen sessions) | [results/judge-stability/](results/judge-stability/) |
| Recorded real-run bundles: ATIF trajectory, submitted patch, official verifier report and test output, task manifest with the standard answer (declared FAIL_TO_PASS / PASS_TO_PASS tests), reference patch | [data/runs/](data/runs/) |
| Final-answer check script (re-applies each task's standard answer to its official verifier report) | [scripts/verify_outcome.py](scripts/verify_outcome.py) |
| Synthetic oracle fixtures (valid / invalid / inconclusive) | [data/fixtures/](data/fixtures/) |

## Repository layout

```text
.
├── data/                         # Fixtures, recorded run bundles, frozen slices, environment checks
├── docs/                         # Requirements, report, audit, design, roadmap, demo
├── frontend/                     # React/Vite evidence-debugger and review UI
├── results/                      # Sanitized deterministic exports of validated evidence
├── scripts/                      # Reproducible pipeline and maintenance entry points
├── src/                          # FastAPI application and evaluator source
├── tests/                        # Offline test suite (evaluator, workflow, API, fixtures)
├── .gitignore
├── README.md                     # English (default)
├── README.zh-CN.md               # 简体中文
└── 犀牛鸟开源-实战任务-混元大语言模型项目.pdf  # Original instruction file
```

## Documentation

- [Documentation index](docs/README.md)
- [Project requirements](docs/PROJECT_REQUIREMENTS.md)
- [Report — validated results and case studies](docs/REPORT.md)
- [Requirements audit — delivery freeze](docs/REQUIREMENTS_AUDIT.md)
- [Demo](docs/DEMO.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Evaluator specification](docs/EVALUATOR_SPEC.md)
- [Development setup](docs/DEVELOPMENT_SETUP.md)
- [Research workspace](docs/research/README.md)

## Development

The project uses a repository-local Python 3.12 environment managed by `uv` (always through
`./scripts/uv-local`) and a React/Vite frontend pinned by `.node-version`. See
[Development setup](docs/DEVELOPMENT_SETUP.md) for the isolation policy, configuration, local
commands, Docker gate, and host notes.

Do not add real credentials to this repository. Copy `.env.example` to the ignored `.env`
file and set Hy3 credentials locally.
