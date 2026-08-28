# Research 04: Final Evaluator and Implementation Decision

- **Research date:** 2026-08-27
- **Status:** Complete — research phase closed
- **Method:** Project requirements, primary papers, official repositories, dataset cards, and official product documentation
- **Not performed:** Installation, cloning, dependency resolution, model calls, container runs, benchmark runs, or smoke tests

## TL;DR

Build one local web application for a coding-agent developer:

```text
SWE-bench Verified task
    -> Hy3 repairs the repository through mini-SWE-agent
    -> Harbor verifies the patch and exports ATIF
    -> deterministic checks extract objective evidence
    -> Hy3 performs a rubric-bound semantic trace review
    -> the application merges both lanes into an evidence-linked diagnosis
    -> a human independently labels and then adjudicates the finding
    -> aggregate analysis reports outcomes, process errors, difficulty, and boundaries
```

The evaluator is the original project contribution. SWE-bench, mini-SWE-agent, Harbor, and ATIF are infrastructure we reuse rather than recreate.

The MVP is an **evidence debugger**, not another benchmark leaderboard and not a generic trace viewer. Its memorable interaction is clicking an evaluator finding and seeing the exact agent step, command output, patch evidence, and verifier result that support it.

Research is now finished. The next work is an offline vertical implementation slice using a recorded ATIF fixture.

## Final product decision

### User

A coding-agent developer investigating why a Hy3 software-engineering run failed, or why a passing run may still be unsafe or unsupported.

### Job to be done

> Given a Hy3 coding trajectory and executable outcome evidence, identify whether the process is valid, locate the earliest observable material error, explain the error with trace evidence, and retain human validation for aggregate analysis.

### Mandatory MVP

- One task source: SWE-bench Verified.
- One agent loop: mini-SWE-agent v2.
- One environment and verifier: Harbor.
- One trace contract: Harbor-compatible ATIF v1.7.
- One hybrid evaluator with deterministic, semantic, and human lanes.
- One local web application with runs, trace diagnosis, review, and analytics.
- One documented evaluation slice preserving the benchmark's released difficulty labels.
- Required localization, false-positive, outcome, process, error, and difficulty analysis.

### Explicit non-goals

- A new benchmark or canonical gold trajectory.
- Multiple benchmarks or harnesses in the MVP.
- Universal trace ingestion.
- Autonomous prompt, tool, policy, or model modification.
- Multi-agent judging, fine-tuning, authentication, teams, or cloud-scale deployment.
- Reproducing Harbor's general-purpose viewer.

## Requirement-to-evidence map

| Project 2 requirement | Implementation | Evidence submitted |
| --- | --- | --- |
| Runnable Hy3 application | Hy3 is the model in mini-SWE-agent and the semantic evaluator | Model/run configuration, source code, example environment file |
| Verifiable code task | SWE-bench Verified issue repair | Task manifest and official verifier artifacts |
| Standard answer | Repository behavior satisfying official `FAIL_TO_PASS` and `PASS_TO_PASS` tests; the gold patch is provenance, not the only valid answer | Test identifiers, verifier configuration, source PR/reference metadata |
| Automatic checker | Harbor SWE-bench adapter and official tests | Per-run report, test output, applied patch, verifier log |
| Complete process | Ordered ATIF trajectory | Validated `agent/trajectory.json` with stable step IDs |
| Difficulty range | Preserve the released SWE-bench Verified `difficulty` field | Manifest value, source, and selection documentation |
| Process correctness | Hybrid evaluator returns `valid`, `invalid`, or `inconclusive` | Versioned structured evaluation result |
| First error | Earliest evidence-supported material agent error | ATIF step ID, optional tool-call ID, human ground truth |
| Error classification | One primary coding-agent category plus optional contributing findings | Versioned taxonomy and per-run label |
| Correct result, invalid process | `resolved` verifier result combined with `invalid` process result | Dedicated flag, evidence, and human audit |
| Localization validation | Compare predicted and human first-error step on gradeable incorrect runs | Exact-step localization data and review records |
| False-positive validation | Audit every selected resolved run flagged process-invalid | Confirmed-problem and evaluator-false-positive proportions |
| Required analysis | Aggregate results by outcome, process, error, difficulty, and decline interval | JSON/CSV outputs, report, dashboard, case studies |
| Runnable open-source materials | Source, pinned manifests, checker/evaluator scripts, example configuration, setup/run instructions | Public repository, README, lockfiles, sanitized tracked results |
| Effectiveness evidence | Immutable evaluator outputs and append-only human records | Localization data, false-positive data, review exports |
| Submission hygiene | Individual/event-project label, environment-only secrets, no PR to the official Hy3 repository | README banner, `.gitignore`, `.env.example`, repository audit |
| No training requirement | Use inference and evaluation only | Training/fine-tuning remains an explicit non-goal |
| Two-minute demo | Replay one completed run from task through review and analysis | Video or GIF no longer than two minutes |

This satisfies the extracted [Project 2 requirements](../PROJECT_REQUIREMENTS.md) without treating every passing patch as a valid process.

## Reusable stack decision

| Layer | Final choice | Reuse boundary | Why |
| --- | --- | --- | --- |
| Runtime | Python 3.12 managed with `uv` | Project backend and scripts | Harbor currently requires Python 3.12 and already uses Pydantic/FastAPI |
| Model | Hy3 through an OpenAI-compatible chat-completions endpoint | Inference only; credentials remain external | The official Hy3 repository documents chat completions and `high` reasoning for coding |
| Task | SWE-bench Verified | Statements, commits, official tests, gold provenance, difficulty | Existing expert-verified tasks and executable checker |
| Agent | mini-SWE-agent 2.4.6 target | Linear bash-only coding loop | Small observable surface and current Harbor adapter support |
| Environment | Harbor 0.22.0 target | Containers, task adapter, agent invocation, verifier, artifacts | Avoids building a sandbox or benchmark adapter |
| Trace | ATIF v1.7 | Harbor-produced trajectory and validator | Current Harbor converter emits v1.7 even though the RFC changelog has reached v1.8 |
| Evaluator | Thin project-specific Python package using Pydantic | Rules, semantic rubric, merge policy, metrics | Generic eval frameworks do not provide our causal coding policy and would duplicate Harbor |
| Semantic client | Official OpenAI Python client pointed at Hy3 | One chat-completions call and one schema-repair retry | Matches Hy3's documented interface and avoids another agent framework |
| API | FastAPI with Pydantic models | REST API and static frontend serving | Shared Python schemas, JSON Schema/OpenAPI, low integration cost |
| Mutable state | SQLite through Python's standard library | Run index, evaluation index, append-only human-review versions | Local, portable, no service dependency |
| Raw evidence | Filesystem artifact store with hashes | ATIF, patch, verifier output, raw judge output | Preserves immutable source evidence and reproducible exports |
| Web | React 19, TypeScript, Vite 7, React Router 7 | Custom evaluator-centered SPA | Required interaction is more custom than a notebook-style data app |
| Web support | TanStack Query/Table, Tailwind CSS 4, shadcn/Radix patterns, Shiki, Recharts | Fetching, tables, components, code/diff rendering, charts | Closely matches Harbor's maintained viewer stack without copying the viewer |
| Analysis | pandas plus SciPy | Aggregation, CSV/JSON/Markdown report, bootstrap intervals | Reproducible required analysis; frontend consumes summary JSON |
| Tests | pytest, Vitest/Testing Library, one Playwright flow | Evaluator, API, components, critical browser workflow | Covers deterministic correctness and the evidence navigation story |

Pin these versions in lockfiles at implementation time. Harbor's repository and published documentation are moving quickly, so the first integration spike must confirm the pins rather than silently upgrading them.

### Hy3 adapter constraint

The official [Hy3 quickstart](https://github.com/Tencent-Hunyuan/Hy3#quickstart) puts `reasoning_effort` under `extra_body.chat_template_kwargs` on the Chat Completions API. Harbor's current [mini-SWE-agent adapter](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/mini_swe_agent.py) routes an `openai/*` model with its top-level `reasoning_effort` option through the Responses API.

Therefore the initial integration will:

- Use a configurable `HY3_MODEL`, defaulting to `hy3` only when the endpoint agrees.
- Configure the agent as `openai/<HY3_MODEL>` against `HY3_BASE_URL`.
- Leave Harbor's top-level `reasoning_effort` option unset.
- Pass Hy3's nested reasoning configuration through mini-SWE-agent's `model_kwargs.extra_body`.
- Use Hy3's documented `temperature=0.9`, `top_p=1.0`, and `high` reasoning as the initial configuration.

This is a source-backed compatibility hypothesis, not a confirmed integration. A single-turn endpoint check and one minimal Harbor task are implementation spikes.

## Why a thin evaluator instead of another framework

[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) is a credible MIT-licensed UK AI Security Institute evaluation framework with model-graded evaluation, transcripts, tools, and a web viewer. LangSmith provides final-response, trajectory, and single-step evaluators plus annotation queues. Neither supplies our definition of a material coding-process error, our first-error labels, or our correct-result/invalid-process policy. Adding either as a runtime would also create a second task/logging system beside Harbor.

The decision is therefore:

- Reuse their evaluation patterns.
- Do not add Inspect, LangSmith, Braintrust, Phoenix, or the retiring OpenAI Evals platform as a product dependency.
- Implement a small typed evaluator whose behavior is completely visible in this repository.

OpenAI's [evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) recommend task-specific metrics, automated scoring where possible, logging, and human calibration. LangSmith's [judge-alignment workflow](https://docs.langchain.com/langsmith/improve-judge-evaluator-feedback) similarly compares judge outputs with human labels and iterates on disagreements. These patterns are adopted locally without their hosted platforms.

## Evaluator decision

### Three evidence lanes

1. **Deterministic lane** validates ATIF and artifact identity, establishes verifier outcome, extracts patch/tool/test facts, and raises integrity or contradiction signals.
2. **Semantic lane** asks Hy3 for a rubric-bound absolute judgment using only the task, trace, patch, verifier evidence, and deterministic facts. It must return typed labels and existing evidence references.
3. **Human lane** records an initial label before revealing the semantic verdict when practical, then accepts, edits, rejects, or marks the result unresolved.

The same model may generate and semantically review a run, so the semantic lane is not treated as independent ground truth. Tests and human records prevent Hy3 from being the sole judge. The primary LLM-as-judge study documents position, verbosity, and possible self-enhancement bias; this project uses absolute rubric classification, masks model identity from the review prompt, requires evidence, and reports human agreement rather than claiming objective truth from the judge alone ([Zheng et al.](https://arxiv.org/abs/2306.05685)).

### Process correctness

A process is **valid** when its observable actions and claims are consistent with the task and evidence, material mistakes are corrected before the final result, no integrity rule is violated, and the final conclusion is adequately supported.

A process is **invalid** when at least one material unresolved error or integrity violation exists. Exploratory hypotheses, failed commands, and recovered mistakes are not automatically errors.

A process is **inconclusive** when missing evidence, malformed traces, infrastructure failures, or evaluator failure prevent a defensible judgment. Inconclusive runs are reported but excluded from correctness denominators.

### First error

The first error is:

> The earliest observable agent-authored ATIF step that contains an evidence-supported material violation of the rubric.

It is not hidden chain-of-thought, the earliest tool failure, or the earliest unsuccessful experiment. Store `step_id` and, when useful, `tool_call_id`. If no defensible step exists, return `unlocatable` rather than inventing one.

### Error taxonomy

| Category | Meaning |
| --- | --- |
| `task_interpretation` | Misreads the issue, expected behavior, constraints, or scope |
| `investigation` | Omits or misuses available code, tests, logs, or repository evidence |
| `reasoning` | Makes an invalid causal diagnosis or inference despite the observed evidence |
| `action_execution` | Uses a wrong path, argument, command, or environment action and fails to recover |
| `implementation` | Introduces an incomplete, incorrect, overfit, or damaging code change |
| `verification` | Misreads results, stops with unresolved evidence, or makes an unsupported success claim |
| `process_integrity` | Tampers with protected evaluation evidence, conceals failure, or makes unrelated destructive changes |

One primary category is assigned to the first error. Additional findings may use other categories. Infrastructure failure is an outcome state, not an agent error category.

### Correct result, invalid process

This condition is exactly:

```text
official outcome == resolved AND adjudicated process status == invalid
```

Potential evidence includes attempts to modify protected benchmark artifacts, unsupported claims contradicted by the trace, confirmed hard-coding, concealed failures, or unrelated destructive changes. Editing repository tests is a review signal, not an automatic violation, because some legitimate software changes include tests. Not running a visible test is also not automatically invalid unless the agent makes a claim the available evidence cannot support.

The complete merge policy, schemas, review rules, and metrics are in [EVALUATOR_SPEC.md](../EVALUATOR_SPEC.md).

## Data and validation decision

### Dataset strategy

- Create a pinned manifest of SWE-bench Verified task IDs; do not copy the full benchmark.
- Preserve the official difficulty value rather than inventing tiers.
- Store source URL, selection reason, verifier contract, and task metadata.
- Treat the official behavior tests as the standard-answer contract; keep the gold patch as restricted provenance and never expose it to Hy3 during the run or initial semantic review.
- Determine the final slice size after the endpoint and environment cost spikes. Reduce the slice rather than sample human validation incompletely.

### Human-validation scope

- Independently label every gradeable incorrect run in the final selected slice for process status and first error.
- Audit every resolved run that the evaluator flags as process-invalid.
- If time remains, spot-check resolved runs not flagged to estimate missed process problems; report this separately because the PDF does not require it.
- Preserve the initial human label, evaluator output, and final adjudication as separate immutable records.
- State clearly that the project uses a single primary reviewer unless another reviewer actually contributes.

### Metrics

- `final_answer_accuracy = resolved / gradeable_runs`.
- `predicted_process_correctness = predicted_valid / evaluator_gradeable_runs`.
- `adjudicated_process_correctness = human_valid / human_reviewed_runs`.
- `incorrect_run_error_detection_accuracy` compares predicted versus human error presence on incorrect outcomes.
- `exact_first_error_accuracy` requires an exact ATIF step match on human-locatable incorrect runs.
- `within_one_step_accuracy` is a secondary diagnostic, never a replacement for exact accuracy.
- `correct_result_confirmed_problem_rate` and `correct_result_false_positive_rate` divide the audited resolved-and-flagged cases.
- Error distribution uses the adjudicated primary category where available and the predicted category otherwise, with provenance visible.
- Difficulty analysis reports denominators and 95% bootstrap intervals. The first adjacent released difficulty pair with a lower point estimate is the observed decline interval; it is called statistically supported only if the bootstrap interval for the difference excludes zero. Otherwise report that no supported decline was established.

## Web decision

### Required routes

- `/runs`: task/run table with outcome, process, difficulty, and review filters.
- `/runs/:runId`: task, patch, verifier, evidence-linked ATIF timeline, evaluator findings, and human review.
- `/analytics`: final/process outcome quadrant, errors, difficulty curves, decline interval, exclusions, and representative cases.
- `/regressions`: optional only after the mandatory workflow is complete.

The run page is the center of the product. Selecting a finding scrolls to and highlights its evidence steps; selecting a step shows its command, observation, patch/test relationship, and all findings that cite it. Deterministic facts, semantic judgment, and human decisions remain visually distinct.

Streamlit was rejected for the final UI. Its official documentation describes a top-to-bottom script rerun on widget interaction, which is excellent for fast data apps but less suitable for the linked, persistent, multi-panel debugger interaction we need. React/Vite costs more initially but directly supports the competition's main demonstration surface. Harbor's own maintained viewer independently uses React, React Router, TanStack, Tailwind, shadcn, and Shiki ([viewer README](https://github.com/harbor-framework/harbor/tree/main/apps/viewer)).

## Differentiation ranking

| Feature | Status | Effort after core | Value | Cut condition |
| --- | --- | --- | --- | --- |
| Evidence-linked process debugger | Mandatory MVP | Large | Makes the evaluator legible and demoable | Cut polish, never evidence links |
| Transparent deterministic/semantic/human lanes | Mandatory MVP | Medium | Makes evaluator credibility inspectable | Reduce visuals, keep provenance |
| Human-approved regression card | First optional | Medium | Turns a diagnosed failure into reusable engineering memory | Cut if validation or reports are unfinished by Day 8 |
| Before/after regression comparison | Second optional | Medium-large | Shows whether a later configuration improved | Cut before the regression card |
| Error-propagation visual overlay | Third optional | Medium | Memorable causal story when evidence is strong | Cut if findings lack reliable downstream links |
| Enhanced capability-boundary charts | Polish | Small-medium | Improves presentation of required analysis | Keep basic charts; cut custom animation |

The regression card is supported by an established industry pattern: LangSmith's [assertions](https://docs.langchain.com/langsmith/assertions) turn a human-reviewed run into reusable acceptance criteria evaluated on later outputs. Our optional card adapts that pattern to coding-agent outcome evidence and ATIF step constraints. It never modifies Hy3 automatically.

## Two-minute demonstration

Use a completed, cached Hy3 run so the video is not dominated by inference or container startup:

1. **0–15 seconds:** task, repository, difficulty, and official verifier outcome.
2. **15–60 seconds:** trajectory timeline and the evaluator's first-error diagnosis.
3. **60–95 seconds:** click evidence across command output, patch, and tests; show deterministic versus semantic reasoning.
4. **95–110 seconds:** reveal or edit the human adjudication.
5. **110–120 seconds:** show aggregate boundary/error analysis and, only if implemented, the saved regression card.

The repository must still support real execution; the video itself need not wait for it.

## Implementation spikes and stop conditions

These are engineering work, not more research:

1. **Hy3 handshake:** confirm endpoint, model ID, authentication, nested reasoning body, response parsing, and structured JSON behavior.
2. **Harbor compatibility:** pin Harbor and mini-SWE-agent, run one minimal task, validate the ATIF output, and confirm all needed artifacts.
3. **SWE-bench cost:** run one selected task and record wall time, disk, API use, and cleanup behavior before fixing the slice size.
4. **Semantic calibration:** compare the first judge prompt against independently labeled fixtures and version the rubric.

Stop or pivot within the same stack if the Harbor mini-SWE adapter fails: invoke mini-SWE-agent directly, retain the official SWE-bench checker, and reuse Harbor's documented conversion model only if doing so is smaller than fixing the adapter. Do not introduce a second harness.

The project is blocked if no usable Hy3 endpoint exists or if neither the primary path nor that direct mini-SWE fallback can produce a complete Hy3 trajectory and automatically checked patch.

## Source catalogue

### Task, model, harness, and trace

- [Hy3 official repository](https://github.com/Tencent-Hunyuan/Hy3)
- [SWE-bench dataset guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/datasets.md)
- [SWE-bench evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md)
- [SWE-bench Verified dataset card](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)
- [mini-SWE-agent repository](https://github.com/SWE-agent/mini-swe-agent)
- [mini-SWE-agent package release](https://pypi.org/project/mini-swe-agent/)
- [mini-SWE-agent local/custom model guide](https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/models/local_models.md)
- [Harbor repository](https://github.com/harbor-framework/harbor)
- [Harbor package release](https://pypi.org/project/harbor/)
- [Harbor SWE-bench Verified adapter](https://hub.harborframework.com/datasets/swe-bench/swe-bench-verified/latest)
- [Harbor mini-SWE-agent adapter](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/mini_swe_agent.py)
- [ATIF RFC](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md)
- [Harbor ATIF documentation](https://github.com/harbor-framework/harbor/blob/main/docs-mintlify/core-concepts/agents/atif.mdx)
- [Harbor Viewer](https://github.com/harbor-framework/harbor/tree/main/apps/viewer)

### Evaluation and industry practice

- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [LangSmith complex-agent evaluation](https://docs.langchain.com/langsmith/evaluate-complex-agent)
- [LangSmith judge alignment with human feedback](https://docs.langchain.com/langsmith/improve-judge-evaluator-feedback)
- [LangSmith assertions](https://docs.langchain.com/langsmith/assertions)
- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)
- [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)
- Prior local research: [industry agent-evaluation practice](02-industry-practice.md)

### Application stack

- [FastAPI official documentation](https://fastapi.tiangolo.com/)
- [Vite official guide](https://vite.dev/guide/)
- [React official documentation](https://react.dev/learn)
- [Streamlit execution model](https://docs.streamlit.io/get-started/fundamentals/main-concepts)

## Confirmed findings and remaining execution uncertainty

### Confirmed

- SWE-bench Verified publishes expert-verified tasks, official tests, gold provenance, and difficulty metadata.
- Harbor publishes a SWE-bench Verified adapter, verifier artifacts, mini-SWE-agent integration, an ATIF converter, and a viewer.
- Harbor's current mini-SWE adapter emits ATIF v1.7 with stable sequential steps.
- mini-SWE-agent v2 has a linear bash-oriented history and custom OpenAI-compatible endpoint configuration.
- Hy3 documents an OpenAI-compatible Chat Completions interface and coding-oriented high reasoning mode.
- Established evaluator guidance separates final, trajectory, and step evaluation and calibrates model judges with humans.
- Harbor's viewer already supports generic trace browsing, so evaluator evidence and adjudication—not a timeline alone—must distinguish this project.

### Execution uncertainty

- The available Hy3 endpoint's exact URL, model ID, authentication, payload support, limits, and cost.
- Whether Hy3's nested reasoning configuration passes through Harbor and mini-SWE-agent unchanged.
- Whether current Harbor 0.22.0 and mini-SWE-agent 2.4.6 work together on the selected host despite rapid upstream changes.
- Whether all command exit status and patch/verifier evidence needed by deterministic checks survives ATIF conversion.
- The final evaluation-set size affordable within time, disk, and API limits.
- How well Hy3's semantic judge agrees with the project's human labels.

None of these requires another research topic. Each has an explicit implementation spike, observable result, and fallback or stop condition.
