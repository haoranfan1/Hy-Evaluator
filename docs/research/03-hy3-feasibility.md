# Research 03: Exact Hy3 Task and Harness Feasibility

- **Research date:** 2026-08-27
- **Status:** Complete
- **Method:** Official documentation, repositories, specifications, and released benchmark metadata only
- **Not performed:** Installation, model calls, endpoint authentication, cloning, builds, container execution, or benchmark runs

## TL;DR

### Exact task for Hy3

Hy3 should act as a **software-engineering agent repairing a real SWE-bench Verified issue**:

> Given a frozen repository at the issue's base commit and its natural-language problem statement, inspect the code, run commands and tests, modify the repository, and submit a patch that passes the official fail-to-pass and pass-to-pass tests.

This is a direct code-task interpretation of Project 2. The final result is automatically verifiable, the complete agent process is observable, and SWE-bench Verified already provides expert-validated tasks plus released difficulty metadata.

### Recommended execution stack

```text
SWE-bench Verified task
    -> Harbor task environment and official verifier
    -> mini-SWE-agent using a Hy3 OpenAI-compatible endpoint
    -> ATIF trajectory
    -> independent process evaluator
    -> evidence-backed failure report and human-reviewed regression case
```

- **Agent loop:** [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent).
- **Environment, verification, and trace normalization:** [Harbor](https://github.com/harbor-framework/harbor).
- **Trace representation:** Harbor's [Agent Trajectory Interchange Format](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md) (ATIF).
- **Outcome source:** [SWE-bench Verified](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/datasets.md).

### Important boundary

Hy3 is the **agent being evaluated**, not the sole judge of its own trajectory. The evaluator may use a model for semantic judgments, but executable tests, deterministic checks, and human validation remain independent evidence.

Autonomous self-evolution is parked. The retained product loop is human-reviewed failure-to-regression curation; it does not automatically rewrite prompts, tools, policies, or code.

## Research question

> What exact verifiable coding task should Hy3 perform, which durable harness should record it, and how can the resulting application remain compliant and distinctive without constructing a new benchmark?

## Requirement-fit conclusion

The direction has **strong requirement alignment** and does not materially shift from Project 2.

| Project 2 requirement | Proposed realization | Status after research |
| --- | --- | --- |
| Hy3 application | Hy3 is the model inside the coding-agent loop | Strong fit; endpoint integration unverified |
| Verifiable domain | Real repository issue repair | Strong fit |
| Standard answer | A repository state satisfying official tests, not one exact gold patch | Strong fit |
| Automatic checker | SWE-bench fail-to-pass and pass-to-pass tests | Existing |
| Complete solution process | Ordered ATIF agent trajectory | Existing format; conversion unverified |
| Process correctness | Independent evaluator over commands, observations, edits, and verification | Research 04 must select method |
| First-error localization | Stable ATIF step identifiers plus annotated validation records | Ground-truth work remains |
| Error classification | Code-agent taxonomy applied to trace steps | Research 04 must define it |
| Correct result, invalid process | Passing patch with suspicious, unrelated, unsafe, or unsupported process | Plausible; needs explicit policy and audit |
| Difficulty levels | SWE-bench Verified's released `difficulty` field | Existing; labeling protocol must be cited in final data documentation |
| Capability boundary | Analyze Hy3 results by difficulty, repository, error type, and trajectory behavior | Supported |
| Two-minute demo | One issue from failed tests through Hy3 patch, verification, and trajectory diagnosis | Credible |

The unresolved first-error labels do not require a new task benchmark. They require a limited validation layer over selected Hy3 trajectories, which the PDF already requires through human inspection records.

## Why SWE-bench Verified is the primary task source

The [official dataset guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/datasets.md) describes expert-verified solvable issues with:

- Frozen repository and base-commit identifiers.
- Natural-language GitHub issue statements.
- Gold and test patches retained as evaluation metadata.
- Explicit fail-to-pass and pass-to-pass tests.
- A difficulty field supplied for Verified instances.

The official [evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md) applies a generated patch in a Dockerized repository environment and executes the repository tests. Multiple valid patches can therefore pass; the project does not need one canonical implementation trajectory.

The official dataset exposes difficulty metadata. Research 03 recommends preserving those values rather than inventing new tiers, while requiring the final data documentation to pin and cite the original annotation protocol.

### Why only a curated slice

The full Verified benchmark is unnecessary and its documented local infrastructure can be resource intensive. The project should select a documented slice using existing difficulty, repository, and task metadata without setting an arbitrary size during Research 03.

The slice is the fixed competition evaluation set. The application remains a trajectory-evaluation workbench rather than a leaderboard.

## Task-source comparison

| Task source | Verification | Durability | Process value | Main issue | Disposition |
| --- | --- | --- | --- | --- | --- |
| SWE-bench Verified | Official Docker tests with fail-to-pass/pass-to-pass | Widely adopted, maintained, ICLR-recognized ecosystem | Real issue investigation, edits, tests, and recovery | Resource requirements and contamination | **Primary** |
| [Defects4J](https://github.com/rjust/defects4j) | Reproducible buggy/fixed Java revisions and triggering tests | Long-running project with semantic versioning and MIT license | Strong debugging process | Java/toolchain setup; no ready competition difficulty field | **Fallback** |
| [Aider Polyglot](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md) | Exercism unit tests in Docker | Established Aider/Exercism ecosystem | Clear edit-test loop | Mostly implementation exercises rather than real bug diagnosis | Low-cost alternative |
| [BugsInPy](https://github.com/soarsmu/BugsInPy) | Real Python bugs and tests | Academic release with continued activity | Strong domain match | Repository has unresolved licensing and reproducibility concerns | Rejected |
| [QuixBugs](https://github.com/jkoppel/QuixBugs) | Tests over small Python/Java programs | Long-lived | Simple and understandable | Synthetic, small, and weakly representative of agentic repository work | Rejected |
| Terminal-Bench coding tasks | Container state tests | Strong current adoption through Harbor | Rich terminal behavior | Broader and less semantically consistent than issue repair | Parked |

Defects4J is retained because it has genuinely stood the test of time. Aider Polyglot is retained only as an emergency low-cost path if real repository environments prove infeasible.

## Hy3 feasibility

### Confirmed capabilities

The official [Hy3 repository](https://github.com/Tencent-Hunyuan/Hy3) documents:

- An OpenAI-compatible chat-completions interface.
- A 256K context window.
- `high`, `low`, and `no_think` reasoning modes, with `high` recommended for coding and complex reasoning.
- Tool-call and reasoning parsers through supported vLLM and SGLang deployment recipes.
- Reported improvements in tool-call stability, format adherence, error recovery, and cross-scaffold consistency.
- Apache 2.0 model licensing.

These properties are compatible in principle with an agent harness that supports a custom OpenAI-style endpoint.

### Deployment constraint

The official self-hosting recipe recommends eight large-memory GPUs. Self-hosting should therefore **not** be the default plan for this solo project.

The intended path is a hosted or event-provided Hy3 API endpoint. The public main repository does not fully establish hosted endpoint availability, authentication, rate limits, or whether the event account supports the required tool/reasoning payloads. These remain the most important technical blockers for the later vertical prototype.

### Harness compatibility hypothesis

[mini-SWE-agent's model documentation](https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/models/local_models.md) supports custom OpenAI-compatible endpoints through LiteLLM `api_base` configuration and documents generating SWE-bench trajectories through vLLM. This makes Hy3 integration plausible.

Still unverified:

- The exact Hy3 model identifier and hosted base URL.
- How Hy3's reasoning-mode payload passes through LiteLLM and Harbor.
- Whether native tool calls or the simpler text/bash action loop is more reliable.
- Maximum usable output and context limits through the actual endpoint.
- Cost, rate limits, retries, and concurrency.

The first implementation experiment must validate one Hy3 turn before any UI or evaluator work.

## Harness decision

### Primary agent loop: mini-SWE-agent

The Princeton/Stanford SWE-agent organization now recommends [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) as its default for most use cases. Its advantages here are:

- A deliberately small, linear agent loop.
- Direct support for SWE-bench runs and trajectory generation.
- Custom OpenAI-compatible and local-model endpoints.
- Straightforward command/observation history.
- Multiple sandbox backends and an MIT license.
- Lower integration surface than full SWE-agent or OpenHands.

The older SWE-agent is not selected because its own documentation says current development has shifted to mini-SWE-agent.

### Environment and evaluation wrapper: Harbor

Harbor is not replacing mini-SWE-agent's reasoning loop. It supplies:

- A published [SWE-bench Verified dataset adapter](https://hub.harborframework.com/datasets/swe-bench/swe-bench-verified/latest).
- Task environments, agent execution, verifier results, and artifacts under one trial.
- Existing integrations for mini-SWE-agent, OpenHands, Codex, and other agents.
- A web results/trajectory viewer.
- ATIF output and validation.

This combination avoids writing our own sandbox, task adapter, or cross-agent trace schema.

### Fallback: OpenHands Software Agent SDK

[OpenHands SDK](https://docs.openhands.dev/sdk/arch/overview) is the fallback if mini-SWE-agent cannot drive Hy3 reliably. It offers a provider-agnostic model layer, typed tools, security policies, persistence, and a mature append-only [event system](https://docs.openhands.dev/sdk/arch/events).

It is not primary because its richer runtime and persistence model create more integration work than the project currently needs.

## Minimum trajectory contract

Do not invent another trace format. Adopt the relevant subset of Harbor's active **ATIF v1.7** specification.

The application needs:

- Schema and trajectory identifiers.
- Agent, harness, model, and version metadata.
- Ordered stable step identifiers.
- User/system/agent messages.
- Tool or shell actions with arguments.
- Environment observations, outputs, and errors.
- Optional visible reasoning summaries where actually available.
- Per-step timing and token/cost metrics where available.
- Final verifier reward and outcome artifacts.
- Benchmark instance ID, repository, base commit, and difficulty in provenance metadata.

ATIF already provides extensible fields and Pydantic validation. Project-specific evaluator findings and human-review records should reference ATIF step IDs rather than alter the source trace.

## Codex and DeepSeek Harness decision

### Codex

Official OpenAI documentation describes [Codex app-server](https://learn.chatgpt.com/docs/app-server) as a documented client protocol for threads, turns, events, and approvals, backed by the open Codex harness. It is valuable evidence for observable agent-runtime design.

It is not the primary runtime because this competition must evaluate Hy3, and official documentation does not establish Codex app-server as a general arbitrary-model harness. Harbor already supports converting Codex runs to ATIF, so future comparison can occur at the trace boundary without making Codex a core dependency.

### DeepSeek Harness

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) exposes replaceable model, tool, loop, persistence, and UI plugins plus an append-only session log. Architecturally, it could host a Hy3 model adapter or export its session events.

However, its official repository labels the current release a developer preview and warns of compatibility-breaking changes. A DSH plugin is therefore parked. Its append-only log, replay, and plugin boundaries remain design references for future adapters.

### Integration outcome

- MVP: Hy3 + mini-SWE-agent + Harbor/ATIF.
- Optional later comparison: import Codex ATIF produced by Harbor.
- Future work: DSH-to-ATIF adapter after DSH stabilizes.
- Explicit non-goal: universal cross-harness ingestion.

## Standout feature with self-evolution parked

The strongest compliant hypothesis is a **human-reviewed regression card**:

1. The evaluator highlights a process problem and supporting ATIF steps.
2. A human accepts, edits, or rejects the finding.
3. The accepted finding becomes a versioned regression artifact containing task provenance, outcome expectations, relevant process constraints, evidence, and review status.
4. A later Hy3 configuration can be compared against the same artifact.

This is not autonomous self-evolution. The application does not modify Hy3, prompts, tools, or harness settings by itself.

The regression card could stand out because it joins three normally separate surfaces:

- Deterministic test evidence.
- Process-evaluator judgment.
- Human review and reusable regression coverage.

[Research 04](04-evaluator-and-implementation.md) made evaluator transparency part of the MVP, retained the regression card as the first optional feature, and ranked before/after comparison below it.

## Requirement risks and no-go conditions

### Unavoidable remaining work

- Select a documented SWE-bench Verified slice; do not author new tasks.
- Confirm the official difficulty values and preserve them unchanged.
- Generate Hy3 trajectories for the selected tasks.
- Create a limited human-annotated validation subset for first-error localization and false-positive analysis.
- Define process labels and error taxonomy in Research 04.

### No-go conditions

Stop or pivot if:

- No usable Hy3 endpoint is available.
- Hy3 cannot operate reliably through mini-SWE-agent or the OpenHands fallback.
- Selected SWE-bench environments cannot run within the available compute/storage budget.
- ATIF conversion loses actions, observations, or stable step identity needed for validation.
- The project would require relabeling a large public corpus rather than a limited validation subset.

## Confirmed findings versus inference

### Confirmed

- SWE-bench Verified has automatic tests and released difficulty metadata.
- Hy3 exposes an OpenAI-compatible interface and documents coding-oriented reasoning and tool-use capabilities.
- mini-SWE-agent supports custom OpenAI-compatible endpoints and SWE-bench trajectory generation.
- Harbor supports SWE-bench Verified, mini-SWE-agent, Codex, OpenHands, verifier artifacts, and ATIF trajectories.
- Codex app-server exposes a documented event protocol.
- DSH provides rich append-only sessions but is explicitly unstable today.

### Inference requiring later execution

- The event-provided Hy3 endpoint works with mini-SWE-agent through Harbor.
- Hy3 reasoning and action parsing remain reliable over long SWE-bench trajectories.
- Harbor's SWE-bench adapter and prebuilt environment are affordable on the available machine.
- The final selected slice can be fully human-labeled for the required localization and false-positive validation within the available time.
- Human-reviewed regression cards provide enough differentiation for the competition.

## Accepted decision

Research 04 accepted this stack with the following final roles:

1. **Task:** real Python issue repair from SWE-bench Verified.
2. **Agent:** Hy3 through mini-SWE-agent.
3. **Environment and verifier:** Harbor's SWE-bench Verified adapter.
4. **Trace:** ATIF v1.7.
5. **Evaluator:** deterministic evidence, rubric-bound Hy3 semantic review, and human adjudication.
6. **Standout candidate:** human-reviewed failure-to-regression card.
7. **Parked:** autonomous self-evolution and direct DSH plugin work.

No installation or model call occurred during Research 03. The remaining compatibility claims are now bounded implementation spikes documented in [Research 04](04-evaluator-and-implementation.md) and the [architecture](../ARCHITECTURE.md).
