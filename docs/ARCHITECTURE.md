# Architecture

## Status

**Approved MVP architecture.** Research is complete. See [Research 04](research/04-evaluator-and-implementation.md) for evidence and [Evaluator Specification](EVALUATOR_SPEC.md) for evaluator semantics.

## Product boundary

The application is a local web workbench for inspecting and validating Hy3 coding-agent processes.

```text
SWE-bench Verified task
        |
        v
Harbor 0.22.0 -> mini-SWE-agent 2.4.6 -> Hy3 Chat Completions
        |                                      |
        +-> official verifier artifacts        |
        +-> ATIF-v1.7 trajectory ---------------+
                         |
                         v
             workbench artifact importer
                         |
             +-----------+-----------+
             |                       |
     deterministic evidence     Hy3 semantic review
             |                       |
             +-----------+-----------+
                         v
              merged evaluator result
                         |
              human review/adjudication
                         |
                 aggregate analysis
                         |
                    React web UI
```

Harbor owns execution and objective verification. The workbench owns process evaluation, human validation, analysis, and the evaluator-centered user experience.

## Technology stack

### Backend

- Python 3.12.
- `uv` with a locked `pyproject.toml`/`uv.lock`.
- FastAPI and Pydantic v2.
- Harbor's trajectory models and validator for ATIF v1.7.
- Official OpenAI Python client configured with the Hy3 base URL for semantic evaluation.
- SQLite through the Python standard library for mutable indexes and reviews.
- pandas and SciPy for result exports and uncertainty analysis.
- pytest, pytest-asyncio, and Ruff.

### Frontend

- React 19 and TypeScript.
- Vite 7 with npm and a committed lockfile.
- React Router 7.
- TanStack Query and TanStack Table.
- Tailwind CSS 4 with shadcn/Radix component patterns.
- Shiki for code, command, and diff presentation.
- Recharts for required charts.
- Vitest, React Testing Library, and one Playwright critical-flow test.

Build the SPA to static assets and serve them from FastAPI in production. Development uses Vite's proxy to the local API. Do not add Next.js, a Node server, Redis, Celery, Postgres, or a hosted platform to the MVP.

## Backend components

### `adapters`

- `HarborImporter` discovers or imports a completed Harbor trial under a configured jobs root.
- `AtifAdapter` validates ATIF and exposes normalized step/evidence access.
- `Hy3Client` wraps chat completions, nested reasoning configuration, timeout, structured-output validation, and one repair retry.
- `HarborRunner` launches validated `harbor run` arguments with `asyncio.create_subprocess_exec`; it never passes arbitrary text to a shell.

### `evaluator`

- `EvidenceExtractor` creates deterministic checks and facts from task, ATIF, patch, and verifier artifacts.
- `SemanticReviewer` sends the versioned rubric and evidence to Hy3.
- `EvaluationMerger` applies the precedence and inconclusive policies in `EVALUATOR_SPEC.md`.
- `MetricCalculator` produces per-run and aggregate metrics with provenance and exclusions.

### `storage`

- `ArtifactStore` registers immutable files by path and SHA-256; source Harbor artifacts are never edited.
- `WorkbenchRepository` maintains task, run, evaluation, review, and optional regression-card indexes in SQLite.
- `ExportService` writes versioned JSON/JSONL/CSV/Markdown results for the public repository.

### `api`

- Pydantic request/response models are the source of truth for both validation and generated OpenAPI.
- Long-running Harbor jobs are external subprocesses monitored by an in-process job manager. FastAPI `BackgroundTasks` is not used for container/model execution.
- Job state is persisted before launch. On server restart, a previously running job becomes `interrupted` until explicitly reconciled or retried.

## API surface

All endpoints are under `/api`.

| Method and path | Behavior |
| --- | --- |
| `GET /health` | API, database, jobs-root, and artifact-root readiness; never tests the model implicitly |
| `GET /tasks` | List pinned task manifests and filters |
| `GET /runs` | List runs with outcome, process, difficulty, and review status |
| `POST /runs/import` | Import one ATIF fixture or one completed trial path below the configured Harbor jobs root |
| `POST /runs` | Launch one pinned task through Harbor/mini-SWE-agent/Hy3 |
| `GET /runs/{run_id}` | Task, configuration, artifacts, outcome, and latest evaluation summary |
| `GET /runs/{run_id}/trajectory` | Validated ATIF steps and evidence relationships |
| `POST /runs/{run_id}/evaluate` | Run deterministic extraction, semantic review, and merge; idempotent by input/config digest unless `force=true` |
| `GET /evaluations/{evaluation_id}` | Full typed result, checks, findings, evidence, and review status |
| `POST /evaluations/{evaluation_id}/initial-review` | Save evaluator-hidden initial human label |
| `POST /evaluations/{evaluation_id}/adjudications` | Append accept/edit/reject/needs-evidence decision |
| `GET /analytics/summary` | Required metrics, provenance, denominators, exclusions, difficulty, and case links |
| `POST /exports` | Rebuild public result artifacts from persisted records |
| `GET/POST /regression-cards` | Optional; list or create a human-approved card after core completion |

`POST /runs/import` accepts either an uploaded ATIF JSON fixture with optional artifacts or a **relative** completed-trial path. Resolve trial paths under the configured root and reject traversal, symlinks escaping the root, unsupported files, and oversized uploads.

## Web routes and interactions

### `/runs`

- Show task/run, repository, official difficulty, execution status, outcome, process status, first error, and human-review status.
- Filter by difficulty, outcome, process category, and review state.
- Keep inconclusive runs visibly separate from failures.

### `/runs/:runId`

- Header: task, model/harness versions, official outcome, process status, first error, and provenance.
- Task tab: issue and standard-answer test contract.
- Timeline: stable ATIF steps with agent message, tool calls, observations, timestamps, and metrics.
- Evidence panel: deterministic checks, semantic findings, and human decisions in separate lanes.
- Patch/test tabs: generated diff, verifier tests, output, and logs.
- Clicking a finding highlights every cited step; clicking a step lists every finding citing it.
- Review flow records an initial label before revealing semantic output, then allows adjudication.

### `/analytics`

- Final-result versus process-status quadrant.
- Primary error distribution.
- Results by official difficulty with denominators and intervals.
- Observed and statistically supported decline interval.
- Excluded/inconclusive runs.
- Linked representative cases and capability-boundary notes.

### `/regressions` — optional

- Human-approved regression cards.
- Expected outcome, process assertions, failure evidence, and versions.
- Later-run comparison without automatic self-modification.

## Persistence and artifacts

Use this logical layout when implementation creates the directories:

```text
data/
  manifests/swebench_verified.jsonl       # tracked selection and provenance
  fixtures/                               # tracked synthetic/dev ATIF fixtures
.local/                                   # ignored mutable local state
  workbench.db
  harbor/jobs/
  artifacts/{run_id}/
    trajectory.json
    patch.diff
    verifier-report.json
    test-output.txt
    run.log
    semantic-raw-1.json
    semantic-raw-2.json
results/                                  # tracked final competition evidence
  per_run/*.json
  human_reviews.jsonl
  metrics.csv
  summary.json
  report.md
frontend/
src/hy3_workbench/
tests/
```

Store artifact paths and hashes in SQLite. Copy an artifact into `.local/artifacts` only when its source path is temporary; otherwise register an immutable path. Final exports contain no secrets or absolute local paths.

SQLite holds:

- Task-manifest index.
- Run state and configuration digests.
- Evaluation index and artifact references.
- Append-only human-review versions.
- Optional regression-card versions.

Raw ATIF, diffs, logs, judge responses, and final public exports remain files rather than opaque database blobs.

## Execution flow

### Offline import and evaluation

1. Import a recorded fixture or completed Harbor trial.
2. Validate paths, hashes, identity, and ATIF v1.7.
3. Extract official outcome and deterministic evidence.
4. If identity or trace validation is fatal, return inconclusive without a model call.
5. Send allowed evidence and the versioned rubric to Hy3.
6. Validate all semantic labels and evidence references; retry schema repair once.
7. Merge results and persist immutable evaluator artifacts.
8. Collect initial human label and later adjudication.
9. Recompute aggregate analysis using human labels where available.

### Live task execution

1. Resolve a pinned task ID and safe configuration.
2. Persist a queued run.
3. Launch Harbor locally with one trial and validated argument lists.
4. Harbor provisions the SWE-bench environment, installs the pinned mini-SWE-agent, calls Hy3, verifies the patch, and writes trial artifacts.
5. Import the finished trial through the same offline path.

The evaluator never reads the gold patch during initial automatic review. A human may use reference provenance during ground-truth adjudication.

## Hy3 configuration

Expected non-secret configuration:

```text
HY3_BASE_URL
HY3_MODEL
HY3_REASONING_EFFORT=high
HY3_TEMPERATURE=0.9
HY3_TOP_P=1.0
WORKBENCH_DATA_DIR=.local
HARBOR_JOBS_DIR=.local/harbor/jobs
```

Secret configuration:

```text
HY3_API_KEY
```

For mini-SWE-agent through Harbor, map the key/base URL to the environment names expected by Harbor and pass Hy3's reasoning mode inside `model_kwargs.extra_body.chat_template_kwargs`. Do not set Harbor's top-level OpenAI reasoning option until an implementation test proves the endpoint supports the Responses API.

Record non-secret model parameters, package versions, prompt/rubric versions, and configuration digests in every run. Redact authorization headers and environment values from logs and exports.

## Failure handling

| Failure | Application behavior |
| --- | --- |
| Invalid ATIF or bad step references | Inconclusive; no semantic call |
| Missing verifier report | Inspect logs; classify agent-caused patch failure as unresolved, infrastructure ambiguity as inconclusive |
| Semantic JSON invalid | One repair retry; then partial/inconclusive with raw responses retained |
| Semantic evidence reference nonexistent | Reject semantic output and retry once |
| Rule/semantic contradiction | Preserve both, mark partial, require human review |
| Server restart during job | Mark interrupted; never claim failure or success automatically |
| Hy3 endpoint unavailable | Retry only bounded transient errors; expose failed job and preserve logs |
| Context too large | Inconclusive `context_limit`; no silent truncation in MVP |
| Human disagrees | Append adjudication; never overwrite evaluator output |

## Security and reproducibility

- Agent execution remains inside Harbor's task environment.
- Build subprocess commands with argument arrays, never interpolated shell input.
- Restrict imported paths to configured roots and validate upload sizes/types.
- Never expose secrets to the frontend or public exports.
- Keep gold/reference patches outside agent-visible paths.
- Pin Python and frontend dependencies with lockfiles.
- Store content hashes, task revision, package versions, rubric/prompt versions, and metric seed.
- Attribute any Apache-licensed Harbor code if implementation copies it; prefer APIs and formats over source copying.

## Implementation order

1. Hy3 endpoint handshake and typed schemas.
2. Recorded ATIF fixture, validator, artifact store, and deterministic evidence.
3. Semantic review and merge policy.
4. FastAPI import/evaluate/read endpoints.
5. Evidence-linked run page.
6. Human review and analytics.
7. Live Harbor execution and one SWE-bench task.
8. Final slice, validation, result export, documentation, and demo.
9. Regression card only if the mandatory path is complete.

## Fallback and stop conditions

- If Harbor's mini-SWE adapter is the only blocker, invoke the same pinned mini-SWE-agent directly and retain the official SWE-bench verifier plus ATIF conversion. Do not add a second harness.
- If current mini-SWE-agent is incompatible, try Harbor's documented parity version before changing architecture.
- If no Hy3 endpoint can produce both a coding trajectory and semantic review, the project is blocked; another model cannot silently replace the required Hy3 capability.
- If full SWE-bench execution exceeds resources, reduce the documented slice, not the evaluator validation or evidence requirements.
