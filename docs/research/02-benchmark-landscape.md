# Research 02: Established Benchmarks and Reusable Agent Scenarios

- **Research date:** 2026-08-27
- **Status:** Complete
- **Method:** Documentation, papers, official repositories, and released dataset cards only
- **Not performed:** Cloning, installation, environment configuration, dataset download, build, or smoke test

## TL;DR

We should **not build an agent benchmark from scratch**.

The strongest provisional choice is to **curate from the verified release of CodeTraceBench**. It already provides complete coding-agent trajectories, solved/failed outcome labels, difficulty metadata, stable stages, raw artifact pointers, and human-verified incorrect/unuseful step annotations. Its trajectories come from established SWE-bench and Terminal-Bench tasks.

The fallback is to combine the **AgentProcessBench τ² subset** with the official **τ-bench environment**. This gives us a smaller process-labeled trajectory corpus plus an established stateful task environment with policies and automatic end-state scoring.

The companion [industry-practice addendum](02-industry-practice.md) changes the product framing: the public benchmark should bootstrap an industry-style trace-to-evaluation and regression workflow, not become the whole product.

Neither choice is implementation-approved yet. The largest unresolved issue is whether its original outcome checker and task version can be connected to the released trajectory without significant setup or schema repair. That requires a later, explicitly approved feasibility check.

## Research question

> Can we adopt, curate, or combine established agent benchmarks so that tasks, deterministic outcomes, trajectories, and process annotations already exist?

The decision priority is:

1. Reusable ground truth and trajectories.
2. Automatic outcome verification.
3. Ten-day and solo-developer feasibility.
4. Licensing and redistribution clarity.
5. User relevance and differentiation potential.

Repository popularity is supporting evidence, not the main quality criterion.

## Credibility gate

A shortlisted project needed:

- An official university, research-lab, company, or benchmark-team release.
- A paper, technical report, or substantial official documentation.
- Publicly described data, task environments, evaluation code, or trajectories.
- A visible license or an explicitly recorded licensing blocker.
- Evidence of real use: benchmark adoption, maintained releases, conference recognition, substantial repository activity, or dataset downloads.

Personal demos without validated data or executable evaluation were excluded.

## Important distinction

No single asset type solves the project:

| Asset | What it gives us | What it does not give us |
| --- | --- | --- |
| Task environment | Tools, state, instructions, and automatic outcome checker | Human process labels |
| Trajectory corpus | Complete recorded agent actions and observations | Necessarily runnable tasks or verified labels |
| Process dataset | Step labels, error locations, or diagnoses | Necessarily a live environment |
| Evaluation framework | Normalization, scoring, and reports | A domain-specific benchmark |

The best candidate is therefore either an unusually complete corpus or a compatible combination of established assets.

## Candidate comparison

Popularity figures below were observed on 2026-08-27 and will change. They indicate adoption only.

| Project | Established signal | Outcome oracle | Released trajectories/process labels | Main limitation | Disposition |
| --- | --- | --- | --- | --- | --- |
| [CodeTraceBench / CodeTracer](https://github.com/NJU-LINK/CodeTracer) | Nanjing University paper and code; 88 GitHub stars; [dataset reports substantial monthly downloads](https://huggingface.co/datasets/NJU-LINK/CodeTraceBench) | `solved` outcome inherited from SWE-bench or Terminal-Bench; artifact pointers preserve source run data | Full action-observation artifacts; stages; incorrect and unuseful steps; difficulty metadata | New release; source checker re-execution and annotation reliability still need validation | **Leading candidate** |
| [τ-bench](https://github.com/sierra-research/tau2-bench) + [AgentProcessBench](https://github.com/RUCBM/AgentProcessBench) | Actively maintained Sierra benchmark plus multi-university process dataset | Database end-state and communication scoring; policies and reference actions | τ-bench publishes historical trajectories; AgentProcessBench provides a labeled τ² subset | Exact source version/task-ID alignment and difficulty strategy are undocumented | **Fallback combination** |
| [BFCL](https://github.com/ShishirPatil/gorilla) + AgentProcessBench BFCL subset | Berkeley project; about 12.9k GitHub stars; Apache 2.0 | Executable function-call and multi-turn state evaluation | AgentProcessBench provides a process-labeled BFCL subset | More function-calling-centric; version alignment remains unverified | Strong alternative |
| [AppWorld](https://github.com/StonyBrookNLP/appworld) | ACL 2024 Best Resource Paper; about 491 GitHub stars | Database-state unit tests check required changes and collateral damage | Environment I/O and API-call logs; released experiment outputs | No established step-label corpus found; protected bundles have redistribution conditions | Environment/reference only |
| [Terminal-Bench / Harbor](https://github.com/harbor-framework/terminal-bench) | ICLR 2026; older benchmark about 2.5k stars; Harbor about 2.2k | Container tests over final state; oracle solutions | Harbor emits standardized trajectories; public result logs exist | Full execution is expensive; no native human process labels | Source environment, not standalone choice |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) | ICLR 2024 oral; about 5.7k GitHub stars | Dockerized repository tests | Official experiments repository publishes logs and trajectories | Documented local evaluation is resource intensive; outcome tests do not locate process errors | Source environment, not standalone choice |
| [ToolSandbox](https://github.com/apple/ToolSandbox) | Apple; NAACL 2025; about 251 GitHub stars | Milestone DAG and state-snapshot similarities | Conversation/tool traces and milestone mapping | Maintainers state that future development is limited; no compatible human step labels found | Evaluation-design reference |
| [AgentRx](https://github.com/microsoft/AgentRx) | Microsoft Research; about 137 GitHub stars | Constraint violations support diagnosis, not task success | CC BY 4.0 dataset of annotated failed trajectories | Failed trajectories only; “first unrecoverable failure” differs from first local error; access requires agreement | Evaluator/taxonomy reference |
| [TUA-Bench](https://github.com/facebookresearch/TUA-Bench) | Meta research release | Deterministic setup and execution-based scoring | Run artifacts are supported | Very new; CC BY-NC; additional assets required; no process annotations found | Parked |
| [CLI-Universe](https://arxiv.org/abs/2606.22883) | Multi-institution preprint and substantial methodology | Paper describes multi-stage executable verification | Paper describes a trajectory dataset | No official public repository or reusable release found in this pass | Idea reference only |

## Leading candidate: CodeTraceBench

### What is already released

The current [CodeTraceBench dataset card](https://huggingface.co/datasets/NJU-LINK/CodeTraceBench) describes:

- A verified split curated from SWE-bench and Terminal-Bench trajectories.
- Complete compressed trajectory artifacts rather than final patches alone.
- Multiple established coding-agent formats, including OpenHands, mini-SWE-agent, Terminus2, and SWE-agent.
- Outcome status through a `solved` field.
- Stable stage boundaries and step counts.
- Incorrect and unuseful step annotations with written reasoning.
- Existing easy/medium/hard metadata and task categories.
- An MIT license.

The dataset card also publishes direct artifact paths, so an eventual curated evaluation slice would not require downloading the entire multi-gigabyte corpus.

### Why it matches this project unusually well

It combines the user's preferred coding-agent domain with most of the expensive research artifacts:

```text
established task -> executed agent trajectory -> outcome label
                 -> stable stages -> process annotations
```

We would not need to invent tasks, collect trajectories from several agent frameworks, or label every step from zero. The existing `solved`, `difficulty`, `category`, `stages`, and `incorrect_stages` fields also map directly to several required analyses.

### Important limitations

- The [paper](https://arxiv.org/abs/2604.11641) and current dataset release report slightly different corpus sizes. A later implementation must pin one dataset revision and use the release manifest as the source of truth.
- The stored `solved` value is an outcome label, not by itself an automatic checker. Executable rechecking depends on the retained SWE-bench or Terminal-Bench artifacts and remains unverified.
- The current dataset card exposes difficulty labels but does not fully explain their derivation. We cannot adopt them blindly.
- “Incorrect” and “unuseful” are not a complete error taxonomy.
- Documentation does not establish whether enough solved trajectories also contain genuine process problems for the correct-result/invalid-process analysis.
- The project is recent. The institutional release and dataset activity are strong signals, but broad long-term adoption is not yet established.

### Proposed adoption strategy

**Curate**, do not adopt the entire corpus.

Selection should later preserve diversity across source environment, outcome, difficulty metadata, task category, trajectory length, and agent format. This research does not choose a sample count or difficulty-tier definition.

## Fallback: τ-bench plus AgentProcessBench

### Reusable environment

The maintained [τ-bench repository](https://github.com/sierra-research/tau2-bench) provides:

- Stateful retail, airline, telecom, and related domains.
- Domain policies, structured tools, tasks, and databases.
- Automatic end-state and communication scoring.
- Historical trajectories and a public trajectory visualizer.
- A base split retained for compatibility with the earlier benchmark structure.
- An MIT license and active fixes.

Its [evaluation documentation](https://github.com/sierra-research/tau2-bench/blob/main/docs/evaluation.md) explicitly accepts any trajectory that reaches an equivalent end state; its listed actions are a reference path, not the only valid sequence. This is preferable to exact trajectory matching.

### Reusable process data

[AgentProcessBench](https://arxiv.org/abs/2603.14465) releases human step labels over trajectories from four established sources, including τ². Its [dataset card](https://huggingface.co/datasets/LulaCola/AgentProcessBench) contains complete messages, tool definitions, ground truth, final labels, and step labels under an MIT license. The paper reports dual annotation and strong inter-annotator agreement.

### Why it is the fallback rather than the leader

- It is a combination, so exact τ² version and task-ID compatibility must be confirmed.
- AgentProcessBench is a static verifier benchmark rather than a live task environment.
- The released τ² subset does not expose an immediately defensible difficulty scheme in its dataset card.
- It is less aligned with the builder's coding-agent interest.

It remains attractive because the data is much smaller than CodeTraceBench and τ-bench already owns the task, policy, database, tools, and outcome checker.

## Strong alternative: BFCL plus AgentProcessBench

[BFCL](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) is the most widely adopted repository screened here. Current releases cover multi-turn, multi-step, stateful, and agentic categories with executable evaluation. AgentProcessBench includes a BFCL-derived process-labeled subset with ground-truth action groups.

This could be easier to integrate than a conversational user simulator, but it risks becoming a function-calling benchmark rather than a broader trajectory-analysis application. Keep it as the next alternative if τ-bench compatibility fails.

## Valuable references that should not determine the scenario

### AppWorld

AppWorld's strongest idea is state-difference testing: expected changes must occur and unrelated state must remain unchanged. Its [official documentation](https://github.com/StonyBrookNLP/appworld) also exposes difficulty indicators, API-call logs, checkpoints, and existing experiment outputs. These are excellent design references for correct-outcome/undesirable-process analysis.

The protected benchmark bundles impose redistribution conditions, and no compatible established step-label dataset was found. It is therefore not the lowest-work foundation.

### ToolSandbox

ToolSandbox's milestone DAG accepts multiple valid action sequences while preserving required partial-order constraints. This is more defensible than comparing against one gold path. However, Apple states in its [contribution guide](https://github.com/apple/ToolSandbox/blob/main/CONTRIBUTING.md) that the repository was released mainly for paper reproducibility and has limited future-development plans.

### AgentRx

AgentRx contributes a useful pipeline concept:

```text
raw trace -> normalized trace -> invariants -> evidence log -> diagnosis
```

Its official [Microsoft repository](https://github.com/microsoft/AgentRx) and [dataset card](https://huggingface.co/datasets/microsoft/AgentRx) are valuable references for normalization, guarded constraints, evidence-backed findings, and taxonomy design. It cannot serve alone because its public benchmark contains failed trajectories and labels the first unrecoverable critical failure rather than every task's general process quality.

### Harbor trajectory format

[Harbor](https://github.com/harbor-framework/harbor) is worth studying later as an integration reference because it standardizes task outputs and can export trajectories from several agent harnesses. It does not eliminate the need to choose a scenario and ground truth.

## Compatibility assessment

No compatibility was practically tested.

| Combination | Documentation evidence | Confidence now | Blocking unknown |
| --- | --- | --- | --- |
| CodeTraceBench + preserved source artifacts | Dataset names SWE-bench/Terminal-Bench sources and publishes artifact pointers | Plausible | Can the original verifier be rerun from each selected artifact without reconstructing the environment? |
| AgentProcessBench τ² + τ-bench | Process paper explicitly states τ² provenance; both publish schemas and MIT data | Plausible | Which τ² revision generated the trajectories, and do task IDs map to the current base split? |
| AgentProcessBench BFCL + BFCL | Process dataset explicitly contains a BFCL subset and ground-truth action groups | Plausible | Which BFCL release and state evaluator produced the records? |
| AgentRx τ retail + τ-bench | Microsoft documents τ-bench retail provenance | Limited/supplemental | Dataset is failed-only and uses a different failure target |
| AppWorld + an established process dataset | None found | Unsupported | Would require new process annotation |
| ToolSandbox + an established process dataset | None found | Unsupported | Would require new process annotation |

“Plausible” is not permission to implement. It means a later feasibility check has a concrete hypothesis to validate.

## Recommendation

### Primary

**Curate a project-specific evaluation slice from CodeTraceBench's verified release.**

Use its existing coding-agent trajectories, outcome metadata, difficulty metadata, stages, and human-verified step annotations. Treat SWE-bench and Terminal-Bench as the inherited sources of executable outcome truth rather than attempting to run their complete benchmarks.

Treat that slice as the initial regression corpus for a Hy3 agent-evaluation workbench, not as a new leaderboard or the only trajectory source the eventual product could understand.

### Fallback

**Use the AgentProcessBench τ² subset with the compatible τ-bench task environment.**

This trades coding-agent specificity for a smaller dataset and a cleaner stateful tool/API oracle.

### Stop condition

If a later feasibility check shows that neither candidate can connect trajectories to executable outcome verification without substantial reconstruction, do not create a new benchmark. Reconsider the agent direction or reduce the project to a clearly labeled static trajectory-evaluator study only if that still satisfies the competition interpretation.

## What we would reuse versus create

| Reuse | Still project-specific |
| --- | --- |
| Task statements and source provenance | A documented selection policy for the curated slice |
| Existing agent trajectories | A small normalized schema or importer |
| Outcome labels and source verifier artifacts | Confirmation that selected outcomes are automatically reproducible |
| Step/stage annotations | Mapping to the final evaluator outputs and metrics |
| Existing difficulty metadata where defensible | Justification or replacement if metadata is inadequately defined |
| Licenses and citation information | Required manual false-positive audit records |
| Existing benchmark metrics as baselines | Hy3 integration and the eventual standout analysis feature |

This is curation and integration, not original benchmark construction.

## Confirmed findings versus inferences

### Confirmed from released documentation

- CodeTraceBench publishes coding-agent outcome, difficulty, stage, annotation, and artifact metadata under MIT.
- τ-bench publishes stateful tasks, policies, tools, outcome scoring, historical trajectories, and MIT-licensed code.
- AgentProcessBench publishes complete process-labeled trajectories from τ² and BFCL under MIT.
- AppWorld provides state-based unit tests, difficulty indicators, and log artifacts, with redistribution conditions on protected bundles.
- SWE-bench and Terminal-Bench provide executable outcome verification but require substantial container infrastructure.
- AgentRx contains failed trajectories and uses a first-unrecoverable-failure target.

### Inferences requiring later validation

- A selected CodeTraceBench artifact can be rechecked without rebuilding the full source benchmark.
- AgentProcessBench records map cleanly to a runnable historical τ² or BFCL release.
- CodeTraceBench's difficulty metadata is defensible for the competition's difficulty analysis.
- Hy3 can consume these long trajectories reliably and economically.
- Either source contains enough correct-outcome/process-problem cases for the required audit.

## Deferred questions

Research 03 should examine only Hy3 feasibility, including long-context limits, structured output, model/tool invocation, and whether Hy3 should generate, evaluate, or both generate and evaluate trajectories.

The later task decision selected SWE-bench Verified directly rather than CodeTraceBench, and [Research 04](04-evaluator-and-implementation.md) consolidated evaluator, differentiation, and scope decisions. Version and endpoint checks are now bounded implementation spikes.

## Review decision

Approve, reject, or modify this provisional order:

1. **Product framing — industry-style trajectory evaluation and regression workbench.**
2. **Bootstrap corpus — CodeTraceBench verified release.**
3. **Fallback corpus/environment — AgentProcessBench τ² + τ-bench.**
4. **Alternative corpus/environment — AgentProcessBench BFCL + BFCL.**

No repository setup or benchmark execution should begin during this review.
