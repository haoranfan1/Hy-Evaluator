# Research 01: Agent Domain and User Scenario

- **Research date:** 2026-08-27
- **Status:** Complete
- **Supersedes:** the earlier mathematics-first version of Research 01
- **Scope:** Establish the agent-trajectory direction and identify scenario families for benchmark research. The exact scenario, benchmark, analysis dimensions, Hy3 integration, architecture, and UI technology remain undecided.

## TL;DR

The stable direction is **agent trajectory analysis using an existing verifiable task environment and existing trajectory data**. We should reuse the tasks, outcome checker, traces, and annotations wherever possible instead of constructing a new benchmark.

The exact scenario is deliberately open. Stateful tool/API workflows currently look cheaper to adopt; repository and terminal tasks remain attractive if an existing dataset removes most environment and annotation work.

First-error localization is part of the apparent Project 2 compliance floor, but it does not need to define the product. Propagation, recovery, evidence timelines, context analysis, side effects, efficiency, comparison, intervention, and other analysis dimensions are optional candidates to research later.

**Next decision:** find which existing benchmark or task environment gives us the strongest reusable combination of tasks, executable outcomes, trajectories, annotations, licensing, and practical runtime.

## Executive conclusion

The agent idea can satisfy Project 2, but only after one important correction:

> **An agent harness is the observation layer, not the verifiable domain.**

Codex and DeepSeek Harness can expose prompts, context, tool calls, results, state, approvals, and turn boundaries. Those records make an agent's visible process inspectable. They do not, by themselves, establish which step is wrong or whether the task was completed correctly. The project still needs a constrained task environment with an objective oracle.

### Recommended direction for review

Build a **Hy3-powered analysis workbench for trajectories from an existing, objectively verifiable agent scenario**.

The intended user is an agent developer or evaluator who wants to understand and compare what happened during a run, rather than reading a raw event log or seeing only a final success score.

The workbench must retain a small compliance core—automatic outcome checking and credible process-error evaluation—but its research identity should remain open until we inspect the available data. Possible analysis dimensions include tool behavior, context use, verification discipline, side effects, efficiency, planning, errors, recovery, interventions, and comparisons between successful and failed runs.

**One-sentence user story:** An agent developer runs or imports a Hy3 trajectory from a verifiable task and receives an interactive, evidence-backed analysis of the aspects of that run that matter most for understanding agent behavior.

### Candidate scenario families

- **Stateful tool/API workflows:** currently the lowest benchmark-construction risk because existing environments can provide database states, milestones, policies, and structured tools.
- **Repository/terminal tasks:** closer to coding-agent interests and potentially more compelling, but acceptable only if an existing task and trajectory source removes most setup and annotation work.

Research 02 should decide between them using evidence, rather than treating either as a committed primary or backup.

### Confidence and decision state

Confidence is **high that agent-trajectory analysis is eligible**. Confidence in any precise scenario remains intentionally open because benchmark reuse, not application engineering, is now the deciding constraint.

This recommendation is intentionally in **Review**. It narrows the search space without selecting a benchmark, harness dependency, evaluator architecture, task count, difficulty scheme, or interface stack.

## Why the previous mathematics recommendation is withdrawn

Mathematics was a strong requirement fit, but requirement fit is not the only ten-day constraint. The person building the project must be willing to inspect examples, understand failure labels, and make dozens of judgment calls in that domain. Low interest in mathematics would make annotation quality, iteration speed, and the final explanation worse.

Agent development is not merely a preference-based substitute. Recent harnesses and research provide a credible evidence chain for observable trajectories, executable task outcomes, step-level evaluation, error propagation, and first-failure analysis. The project can therefore pivot without weakening the core Project 2 requirements.

## What Project 2 means in an agent setting

The instruction PDF allows self-defined and code-task directions. It requires a complete visible solution process, an automatic final checker, process-correctness evaluation, first-error localization, error classification, and detection of correct-result/invalid-process cases.

For an agent project, those requirements translate as follows:

| Project 2 concept | Agent interpretation |
| --- | --- |
| Verifiable domain | A controlled task environment whose terminal state can be checked automatically |
| Complete solution process | The model-visible trajectory: observations, decisions, tool calls, tool results, and checkpoints |
| Standard answer | Expected repository or application state, expressed through tests and invariants |
| Process step | A stable, inspectable agent action or decision unit with evidence and resulting state |
| First error | The earliest step that violates the task, relies on an unsupported premise, corrupts state, or makes failure unavoidable under the documented labeling rule |
| Error category | A documented agent-specific class such as specification neglect, false premise, invalid tool use, missed evidence, unsafe side effect, or verification failure |
| Correct result, invalid process | A task that passes the outcome checker despite prohibited changes, unsupported actions, accidental success, unnecessary damage, or an invalid explanation |

The phrase **model-visible trajectory** matters. The project should analyze observable events and evidence, not claim access to hidden chain-of-thought or the model's private mental state.

This table is the **minimum compliance interpretation**, not the product thesis. In particular, propagation, recovery, lock-in, evidence timelines, and counterfactual replay came from the surrounding research rather than the PDF's core wording. They should compete with other differentiation ideas instead of constraining the project now.

## Research method and eligibility gates

### Mandatory gates

Each candidate direction was checked for:

1. An unambiguous terminal success condition.
2. Automatic or executable final-state checking.
3. Meaningful intermediate actions.
4. A defensible first-error annotation rule.
5. Useful error categories.
6. A defensible path to difficulty stratification.
7. Accessible tasks, environments, or construction methods.
8. A complete two-minute demonstration and plausible ten-day implementation.
9. A real user problem beyond producing another leaderboard score.

### Priority order

Surviving directions were compared by:

1. Project 2 compliance and verification credibility.
2. Quality of process-level evidence and first-error labels.
3. Ten-day implementation and validation risk.
4. User value and differentiation potential.

No composite score was invented. The sources establish feasibility and known limitations; the final recommendation is a project inference.

## Confirmed evidence

### 1. Modern harnesses expose the process we want to inspect

OpenAI describes Codex as an open-source agent harness that manages state, streaming, tools, sandbox and approval boundaries, and multi-turn work. Its platform guidance also separates the harness from the host application: the host controls the interface, supplied context and tools, operational boundaries, and observation of the run. This supports using a harness trajectory as inspectable evidence, but it does not supply process correctness labels. See [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform).

[DeepSeek Harness](https://www.deepseek.com/harness/en/) is even more explicit about observability. Its append-only session log records model-visible prompts, reasoning events, tool calls and results, subagent scheduling, and context injection. Its [architecture documentation](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) describes durable turn, step, assistant, and tool events that can reconstruct a session and support resume, fork, search, and replay.

The [OpenTelemetry semantic conventions for generative-AI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md) are still under development, but they independently show the emerging observability vocabulary: agent invocation, plans, tool execution, workflows, and memory operations.

**Implication:** collecting a structured trajectory is feasible. It is not the novel contribution on its own.

### 2. Plain trace visualization is already a crowded product category

[LangSmith](https://docs.langchain.com/langsmith/view-traces) and [Phoenix](https://arize.com/docs/phoenix/tracing/tutorial/your-first-traces) already let developers inspect agent traces. LangSmith also documents trajectory evaluators, while warning that exact trajectory matching is brittle because several paths can be valid and a sequence match may ignore tool arguments. See [LangSmith evaluation approaches](https://docs.langchain.com/langsmith/evaluation-approaches) and [trajectory evaluations](https://docs.langchain.com/langsmith/trajectory-evals).

**Implication:** a beautiful timeline helps the demonstration, but “we display tool calls” is not sufficient differentiation. The project should add a genuinely useful form of analysis, chosen only after the scenario, available data, and user workflow are understood.

### 3. Agent process evaluation and first-error research now exist

[AgentProcessBench](https://arxiv.org/html/2603.14465v2) evaluates individual steps in web, command-line, and API trajectories. It distinguishes correct/effective, neutral/exploratory, and incorrect/harmful steps, includes an error-propagation rule, and reports both step accuracy and first-error accuracy. The paper also exposes a central difficulty for this project: exploration is not automatically wrong, and later steps may inherit an earlier error until the agent recovers.

[Failure as a Process](https://arxiv.org/html/2607.09510) studies command-line coding agents on executable terminal tasks. It separates a decisive error, the later point where the run becomes locked into failure, and the first observable failure signal. Its taxonomy includes false premises, specification neglect, output misreading, ignored signals, premature action, competence failures, and environment failures.

This separation is highly relevant to the proposed UI and evaluator, but its “decisive error” is a retrospective causal label and should not automatically be equated with the PDF's “first error.” The project must write its own annotation rule before measuring localization accuracy.

[AgentLens: Evaluating AI Coding Agents from Trajectory Data](https://arxiv.org/abs/2607.06624) argues for combining formal verification where available with written reviews of full interactive trajectories, including tool use, verification, recovery, and user-facing quality. This supports a hybrid evaluator rather than an unsupported single-model verdict.

For multi-agent systems, [Who&When](https://arxiv.org/abs/2505.00212) reports that attributing a failure to both the responsible agent and decisive step remains difficult. [Who&When Pro](https://arxiv.org/abs/2607.09996) builds controlled failure cases by replaying a successful prefix and then injecting a failure, which is useful evidence for a future ground-truth strategy.

**Implication:** agent-process evaluation is a legitimate and current research direction. Controlled fault injection after a known-good prefix may offer defensible first-error labels, but adopting that method is a Research 02/04 decision.

### 4. Repository and terminal tasks can provide objective outcome oracles

[Terminal-Bench](https://github.com/harbor-framework/terminal-bench) packages tasks in controlled environments with instructions and executable tests. Its [original announcement](https://www.tbench.ai/news/announcement) describes task containers, reference solutions, agent action logs, and verification of the final environment state.

[TUA-Bench](https://arxiv.org/abs/2606.28480) provides deterministic terminal environments and execution-based scoring across several terminal task families. [CLI-Universe](https://arxiv.org/abs/2606.22883) uses Dockerized environments and multi-stage verification, and reports that creating reliable executable tasks requires aggressive filtering. These sources support the domain while warning that benchmark construction is substantial work.

[SWE-bench](https://arxiv.org/abs/2310.06770) demonstrates test-based evaluation of real repository issues. It is evidence that repository repair has an objective outcome layer, not a recommendation to run the full benchmark in this project.

**Implication:** tests and state invariants can ground the final answer. They still do not reveal the first bad reasoning step; process annotations require a separate design.

### 5. Deterministic tool workflows are an unusually clean fallback

[ToolSandbox](https://github.com/apple/ToolSandbox/blob/main/README.md) evaluates stateful tool use with explicit state checks and critical milestones. Instead of requiring one exact gold trajectory, it represents valid task progress using milestone dependencies, which accommodates several legitimate action sequences.

[tau-bench](https://taubench.com/) evaluates agents interacting with simulated users and tools against database outcomes and policies. [AppWorld](https://arxiv.org/abs/2407.18901) offers stateful application APIs and uses programmatic checks for expected state changes and collateral damage. [Berkeley Function-Calling Leaderboard](https://proceedings.mlr.press/v267/patil25a.html) supplies further official evidence for multi-turn and stateful function-calling evaluation.

**Implication:** tool/API workflows make correct-result/invalid-process cases especially concrete: the requested state may be reached while the agent also performs an unauthorized or harmful side effect.

## Candidate directions

| Candidate direction | Objective oracle | Process opportunity | Main problem | Disposition |
| --- | --- | --- | --- | --- |
| Existing stateful tool/API workflows | Database state, policy rules, and milestone checks | Tool selection, arguments, dependencies, side effects | Must verify whether an existing benchmark also supplies suitable trajectories and annotations | **Research 02 candidate; lower construction risk** |
| Existing repository/terminal tasks | Tests plus filesystem and state invariants | Commands, edits, observations, verification, context use | Environment and annotation costs remain high unless existing assets are reusable | **Research 02 candidate; stronger personal fit** |
| Repository context-acquisition debugger | Gold relevant files/lines and retrieval metrics | Searches, reads, context additions, efficiency | Evaluates only one phase; weak on complete task success and lucky final answers | Possible evaluator component, not the domain |
| General SWE-bench-style issue repair | Repository tests | Rich and realistic long-horizon trajectories | Setup, runtime, task variance, and annotation are too large for ten days | Reject at full scale |
| Browser/GUI agent debugger | Site or application end state | Visual observations, clicks, forms, recovery | Reproducibility, credentials, visual ambiguity, and infrastructure risk | Reject for this schedule |
| Multi-agent failure attribution | Task-specific oracle | Agent handoffs, messages, responsibility | Adds responsible-agent attribution to already difficult step localization | Reject for this schedule |
| Security/prompt-injection agent evaluation | Task outcome plus security policy | Trust boundaries, tool misuse, data exfiltration | Could become a separate security benchmark and dilute the required evaluator | Park as an optional later dimension |
| Harness-agnostic universal trace analyzer | Depends on imported run | Broad event ingestion | No single oracle or stable semantics; integration scope dominates evaluation | Reject as the primary project |

### Context acquisition is promising but incomplete

[ContextBench](https://arxiv.org/abs/2602.05892), [Agent Retrieval Bench](https://arxiv.org/abs/2607.24882), and [SWE-Explore](https://github.com/Qiushao-E/SWE-Explore-Bench/blob/main/README.md) provide evidence for evaluating which repository context an agent retrieves before editing. Gold files or lines can support recall, precision, and efficiency analysis.

This could become a distinctive sub-view—showing which evidence entered the model-visible context before an error—but it is not a complete Project 2 scenario. Retrieving the right file does not prove that the final implementation or the full process is correct.

## Shortlist comparison

| Decision question | Repository/terminal tasks | Mocked tool/API workflows |
| --- | --- | --- |
| Who uses it? | Coding-agent developers and evaluators debugging a run | Tool-agent developers validating business workflows |
| What is the narrow task? | Complete a controlled local repository maintenance task using terminal and file tools | Reach a requested application state through a controlled API while obeying policy |
| What is the standard result? | Expected tests, files, configuration, and permitted-change invariants | Expected database state, milestone completion, and prohibited-side-effect checks |
| What is one step? | Observation or intent, tool call, result, state change, and verification evidence | Tool selection, arguments, result, state transition, and policy evidence |
| Why is first-error labeling credible? | Curated human review plus tests/state diffs; potentially injected faults after a known-good prefix | Earliest violated precondition, policy, or milestone dependency; potentially injected faulty tool action |
| Can multiple valid paths be accepted? | Yes, if evaluation uses state invariants and evidence instead of exact command matching | Yes, using milestone graphs and state checks rather than one action sequence |
| Correct result but invalid process? | Passing tests with prohibited files changed, hidden defect, fabricated claim, or missing verification | Requested update completed with unauthorized access, collateral change, or policy violation |
| Demonstration appeal | High: a familiar coding-agent trace becomes an explainable failure story | High: state changes and policy violations are visually clear |
| Main ten-day risk | Sandbox/task setup and trustworthy process labels | Building or adapting the simulated application and policies |
| Why keep it under consideration? | Stronger personal fit and contemporary coding-agent narrative | Cleaner oracle and potentially much lower benchmark-construction cost |

## Candidate card: repository and terminal agents

### Domain and precise task

**Domain:** constrained, containerized repository and command-line maintenance.

**Task:** Hy3 operates an agent that receives a small repository task, inspects the environment, uses terminal and file tools, modifies state, and verifies its work. After the run, the application checks the final repository state and analyzes the visible trajectory along the dimensions selected after benchmark and differentiation research.

Candidate task families for Research 02 to screen include targeted code repair, configuration repair, structured file transformation, and local build or dependency troubleshooting. Research 01 does not choose among them.

### Intended user

- An agent developer diagnosing why a run failed.
- An evaluator comparing agent behaviors that have the same final score.
- A reviewer checking whether a successful-looking run is safe and well-supported.

The core user problem is not “show me the log.” It is:

> Help me understand the important behavior in this run, why it succeeded or failed, and what I should inspect or improve.

### Standard answer and automatic checker

Each task needs an expected terminal state expressed through several independent checks where appropriate:

- executable tests or commands;
- filesystem and structured-state assertions;
- allowed-change or forbidden-change checks;
- task-specific invariants;
- optional static or runtime checks.

These checks define outcome correctness. They are not treated as complete process truth.

### Process representation

A future schema should give every visible step a stable identifier and preserve at least:

- the current task and relevant constraints;
- the agent's stated intent or action summary, without requiring hidden chain-of-thought;
- tool name and normalized arguments;
- tool output, error, or observation;
- relevant repository or environment state change;
- evidence consulted before the action;
- verification or recovery evidence after the action.

This is a semantic requirement, not an architecture decision. Codex and DeepSeek Harness are reference implementations of observable event streams; neither is selected as a dependency here.

### Plausible first-error ground truth

Research 02 and Research 04 should compare two compatible evidence sources:

1. **Curated natural failures:** reviewers locate the earliest step satisfying a written error rule and record the evidence.
2. **Controlled failures:** begin with a reproducibly successful trajectory or prefix, inject one known faulty decision or action, and preserve the injected location as a strong label while checking whether the run later recovers.

The label definition must distinguish:

- the first locally invalid step;
- the decisive causal error;
- the point where recovery becomes unlikely or impossible;
- the first observable failure signal.

Project 2 requires the first error. The other points are optional explanatory annotations, not substitutes for that metric.

### Initial error-taxonomy direction

The following source-backed families are plausible but **not finalized**:

- specification or constraint neglect;
- false premise or unsupported assumption;
- missed, misread, or ignored environment evidence;
- invalid tool choice or arguments;
- incorrect code or state mutation;
- premature action without sufficient inspection;
- unsafe or irrelevant side effect;
- missing or invalid verification;
- environment or infrastructure failure not attributable to agent reasoning.

Research 04 must consolidate these into a documented, reliably annotatable taxonomy.

### Correct-result/invalid-process cases

This requirement can be stronger in the agent setting than in answer-only tasks. Examples include:

- tests pass but an unrelated file was damaged;
- the requested state is reached through a prohibited operation;
- the agent claims verification that it did not perform;
- an underpowered test suite misses a defect;
- a faulty change is later overwritten, leaving a correct endpoint but an inefficient or risky process;
- the agent exposes or accesses information outside the allowed task scope.

The exact permitted-process policy must be part of each task's ground truth, or the evaluator cannot distinguish a creative solution from an invalid one.

### Illustrative two-minute workflow

1. Select a reproducible repository task.
2. Run a Hy3-powered agent and stream its visible actions.
3. Execute the final tests and state checks.
4. Open the trajectory analysis.
5. Explore the selected analysis dimensions and their supporting trace evidence.
6. Inspect a representative success, failure, or surprising process case.
7. Compare what the outcome checker says with what the process analysis reveals.

This is a product story, not a commitment to a frontend framework.

### Open differentiation space

The application should do more than replay logs, but Research 01 should not decide what “more” means. Failure timelines are one option. Context quality, redundant work, tool efficiency, verification behavior, side effects, policy adherence, trajectory comparison, intervention suggestions, and other forms of agent analysis may prove more useful or distinctive after we inspect the available scenarios and data.

## Candidate card: stateful tool/API agents

### Domain and task

**Domain:** deterministic tool/API workflows in a small mocked application.

**Task:** Hy3 receives a user request and policy, calls structured tools to inspect and update application state, and finishes with a user-facing response. The evaluator checks the requested final state, required milestones, forbidden side effects, step validity, and first error.

### Why it is credible

- Database state can be checked exactly.
- Tool arguments and return values are structured.
- Preconditions and milestone dependencies make some first errors machine-grounded.
- Policy violations create clear correct-result/invalid-process cases.
- ToolSandbox, tau-bench, AppWorld, and BFCL demonstrate relevant evaluation patterns.

### Main limitation

The environment may feel less connected to coding-agent development. However, if existing tasks already provide states, policies, milestones, trajectories, and reusable annotations, this direction may be substantially more credible for a solo ten-day project than repository benchmarking.

## Differentiation options considered later

These hypotheses were carried forward. The final comparison and selection now live in [Research 04](04-evaluator-and-implementation.md).

1. **Context analysis:** examine what information the agent retrieved, retained, ignored, or overused.
2. **Tool-use analysis:** inspect tool selection, arguments, ordering, redundancy, and unnecessary work.
3. **Verification analysis:** reveal whether claims and changes were actually checked.
4. **Side-effect and policy analysis:** expose undesirable behavior even when the requested outcome succeeds.
5. **Failure and recovery analysis:** locate errors, propagation, intervention windows, or recovery when useful.
6. **Trajectory comparison:** align runs and reveal meaningful behavioral differences.
7. **Counterfactual replay:** change a decision, context item, or action and compare the resulting run.
8. **Cost and efficiency analysis:** relate trajectory length, tool calls, latency, or token use to outcome quality.
9. **Evaluator transparency:** attach conclusions to tests, state changes, tool outputs, rules, or calibrated judgments.
10. **Polished interaction and visualization:** make complex runs understandable and memorable.

Each option requires its own light research because several already exist partially in observability and evaluation products.

## Important criticisms and failure modes

### Harness does not equal ground truth

A complete log only tells us what occurred. It does not establish what should have occurred. Every task still needs a final-state oracle and documented process constraints.

### The first failed command is not necessarily the first error

An agent may form a false premise, ignore a test result, or edit too early several steps before a command visibly fails. Conversely, exploratory commands may fail harmlessly. Localization labels must follow a written causal rule.

### One gold trajectory is too brittle

Agents can solve the same task using different valid searches, tools, and edit sequences. Exact sequence matching would punish legitimate alternatives. Milestones, invariants, evidence sufficiency, and state checks are more defensible.

### A model judge alone is not enough

Project 2 asks us to validate localization accuracy and audit false positives. A second LLM's confident explanation is not ground truth. The evaluator should combine executable evidence, deterministic rules, and human-reviewed or controlled labels; any model judgment should be traceable and tested.

### Universal scope would destroy the ten-day project

Supporting arbitrary harnesses, tools, websites, repositories, and multi-agent systems would make ingestion and normalization the project. The first version should own one trajectory format and one constrained task family. Import adapters can remain a future possibility.

### Hy3 must remain central

Codex and DeepSeek Harness are useful references and potential future trace sources, but a project that merely analyzes their existing runs could fail the explicit requirement to invoke model capabilities through Hy3. The runnable demonstration must visibly use Hy3 in the solution or evaluation workflow; Research 03 will determine the reliable integration boundary.

## Explicit non-goals for the first implementation

- Hidden chain-of-thought evaluation.
- A universal cross-harness observability platform.
- Full SWE-bench, Terminal-Bench, browser, desktop, or multi-agent coverage.
- General attribution of blame across multiple agents.
- A complete agent-security benchmark.
- Training or fine-tuning a process reward model.
- Selecting architecture, UI stack, task count, or difficulty tiers in Research 01.

## Confirmed findings versus project inferences

### Confirmed by sources

- Codex and DeepSeek Harness expose rich, reconstructable agent event streams.
- Existing observability tools already provide trace inspection and trajectory evaluation workflows.
- Recent benchmarks evaluate step correctness, first errors, failure propagation, or coding-agent trajectories.
- Reproducible terminal, repository, and tool-workflow environments can verify final state programmatically.
- Multiple valid trajectories make exact-path matching unreliable.
- Controlled failure injection has been used to obtain golden failure-step labels.

### Project inferences requiring review

- The domain should remain agent trajectories, while the exact existing scenario is selected by benchmark feasibility.
- Reusing and converting a suitable evaluation slice is more credible in ten days than authoring a benchmark from scratch.
- Stateful tool/API workflows may have lower adoption cost, while repository/terminal work may offer stronger personal fit and presentation value.
- The standout analysis feature should be selected only after the available trace fields, labels, and user workflow are understood.

## Questions deferred to Research 02

Research 02 should not survey every agent benchmark. It should answer these decision-blocking questions:

1. Which existing scenario provides the best reusable combination of tasks, trajectories, deterministic outcome checks, process annotations, and practical runtime?
2. Can one source satisfy most needs, or can two compatible existing sources be combined without substantial reconstruction?
3. Does the source contain successful, failed, and process-problematic runs suitable for the required validation?
4. Which process dimensions are already observable or labeled, and which would require expensive new annotation?
5. How can several valid trajectories be accepted without using one gold sequence?
6. What existing metadata could support a defensible difficulty analysis?
7. How much integration work is required to run or evaluate Hy3 on the same scenario?
8. What license, redistribution, runtime, and contamination risks would affect an open-source submission?

Research 02 should still avoid selecting the evaluator architecture; that belongs to Research 04.

## Source catalogue

### Harnesses and observability

- OpenAI, [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform).
- DeepSeek, [DeepSeek Harness](https://www.deepseek.com/harness/en/).
- DeepSeek, [Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md).
- OpenTelemetry, [Semantic conventions for generative-AI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md).
- LangChain, [View traces](https://docs.langchain.com/langsmith/view-traces), [evaluation approaches](https://docs.langchain.com/langsmith/evaluation-approaches), and [trajectory evaluations](https://docs.langchain.com/langsmith/trajectory-evals).
- Arize, [Phoenix tracing tutorial](https://arize.com/docs/phoenix/tracing/tutorial/your-first-traces) and [agent trajectory evaluations](https://arize.com/docs/ax/cookbooks/agents/agent-trajectory-evaluations).

### Process evaluation and failure localization

- [AgentProcessBench: Benchmarking Process Evaluation for Agentic Tasks](https://arxiv.org/html/2603.14465v2).
- [Failure as a Process: Learning from the Failure Trajectories of Coding Agents](https://arxiv.org/html/2607.09510).
- [AgentLens: Evaluating AI Coding Agents from Trajectory Data](https://arxiv.org/abs/2607.06624).
- [Who&When: Beyond Outcome Attribution in Multi-Agent Systems](https://arxiv.org/abs/2505.00212).
- [Who&When Pro: Towards Golden Failure Attribution in Multi-Agent Systems](https://arxiv.org/abs/2607.09996).
- [AgentRewardBench: Evaluating Automatic Evaluations of Web Agent Trajectories](https://arxiv.org/abs/2504.08942).

### Executable agent-task environments

- [Terminal-Bench repository](https://github.com/harbor-framework/terminal-bench) and [announcement](https://www.tbench.ai/news/announcement).
- [TUA-Bench: A Benchmark for Tool-Using Agents in Real-World Terminal Environments](https://arxiv.org/abs/2606.28480).
- [CLI-Universe](https://arxiv.org/abs/2606.22883).
- [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770).
- Apple, [ToolSandbox](https://github.com/apple/ToolSandbox/blob/main/README.md).
- [tau-bench](https://taubench.com/).
- [AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents](https://arxiv.org/abs/2407.18901).
- [Berkeley Function-Calling Leaderboard](https://proceedings.mlr.press/v267/patil25a.html).
- [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352).

### Context acquisition

- [ContextBench: A Benchmark for Context Retrieval in Coding Agents](https://arxiv.org/abs/2602.05892).
- [Agent Retrieval Bench](https://arxiv.org/abs/2607.24882).
- [SWE-Explore](https://github.com/Qiushao-E/SWE-Explore-Bench/blob/main/README.md).

## Review decision

Before Research 02 starts, review the following proposal:

> Build a Hy3-powered agent-trajectory analysis project on top of the most reusable existing verifiable scenario. Keep both stateful tool/API and repository/terminal environments under consideration until benchmark feasibility is compared.

The exact analysis dimensions and standout feature remain open. No benchmark or implementation decision should be made until that comparison is complete.
