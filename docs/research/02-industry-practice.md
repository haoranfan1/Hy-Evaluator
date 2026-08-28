# Research 02 Addendum: How Industry Evaluates Agents

- **Research date:** 2026-08-27
- **Status:** Complete
- **Method:** Public product documentation, engineering articles, one industry survey, and disclosed production cases
- **Not performed:** Product setup, vendor trials, interviews, or access to private company evaluation data

## TL;DR

Industry generally does **not** begin by creating a large academic benchmark with one canonical trajectory.

The recurring production workflow is:

```text
instrument real traces
    -> score outcomes, tool behavior, quality, safety, cost, and latency
    -> inspect or sample failures
    -> promote valuable traces into a versioned regression dataset
    -> compare a new agent version against the old one
    -> gate deployment
    -> monitor sampled production traffic
    -> feed new failures back into the dataset
```

This changes how we should view CodeTraceBench: it should be the **bootstrap dataset**, not the identity of the product.

A stronger product direction is a small **Hy3 agent-evaluation workbench** that turns trajectories into scorecards, lets a developer inspect evidence, compares agent versions, and promotes failures into a reusable regression set. The exact analysis dimensions remain open.

## Evidence warning

Public industry evidence is incomplete:

- Most detailed sources are written by evaluation-platform vendors or cloud providers describing their own products.
- Companies rarely publish private failure corpora, internal quality thresholds, or evaluator-calibration results.
- Case studies are selected success stories rather than representative samples.
- Several cloud agent-evaluation features are still preview or recently released.

The sources are useful for identifying implemented workflows. They do not prove that every production agent team follows them or that every advertised evaluator is reliable.

## The common operating model

### 1. Trace the observable execution

Production platforms model an agent run as nested units such as sessions, traces, and spans. They record model calls, tool names and arguments, tool results, retrieval, state changes, timing, tokens, and errors.

- [OpenAI trace grading](https://developers.openai.com/api/docs/guides/trace-grading) assigns structured scores or labels to end-to-end agent traces and runs those graders across groups of traces.
- [AWS AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html) converts OpenTelemetry/OpenInference traces into a unified format for evaluation.
- [Microsoft Foundry tracing](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept) records tool arguments/results and links evaluation runs to traces.
- [Phoenix](https://arize.com/docs/phoenix) uses OpenTelemetry and OpenInference to capture model, retrieval, tool, and custom-logic spans.

The evaluated object is the observable execution record, not hidden chain-of-thought.

### 2. Evaluate at several granularities

Industry tools rarely force one universal “process correctness” number.

| Level | Typical questions |
| --- | --- |
| Tool/span | Was the correct tool selected? Were its parameters valid? Did it execute successfully? |
| Trace/turn | Did the agent complete this request, follow constraints, and avoid unnecessary work? |
| Session/thread | Did it maintain context and eventually satisfy the user's larger goal? |
| Operations | What did success cost in latency, tokens, retries, and external calls? |

[Microsoft Foundry's agent evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/agent-evaluators) separately measure tool selection, input accuracy, call success, output utilization, task adherence, and navigation efficiency. [AWS](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-terminology.html) similarly distinguishes session, trace, and tool-call scopes. [LangSmith](https://www.langchain.com/resources/agent-evals) describes run-, trace-, and thread-level evaluation.

### 3. Mix deterministic checks, model judges, and humans

The public platforms consistently expose multiple scorer types:

- Code or rules for exact state, schema, tool, policy, latency, and cost checks.
- LLM-as-judge for semantic or rubric-based quality.
- Human review for ambiguous, high-stakes, or newly discovered cases.

[Braintrust](https://www.braintrust.dev/docs/evaluate/write-scorers) explicitly separates custom-code, LLM-judge, and built-in scorers. [Phoenix](https://arize.com/docs/phoenix/evaluation/llm-evals/evaluator-traces) applies deterministic or model-based evaluators to production traces, experiments, or datasets and traces the evaluator itself for debugging. [AWS AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluators.html) supports managed model judges and Lambda-based deterministic evaluators.

Industry practice therefore supports a hybrid evaluator, but not blind trust in an LLM judge.

### 4. Separate offline regression from online monitoring

Two modes recur across platforms:

- **Offline:** run a fixed, curated dataset before release to compare models, prompts, tools, and orchestration changes.
- **Online:** asynchronously score a filtered or sampled portion of real production traces to detect new failures and drift.

[LangSmith's evaluation workflow](https://docs.langchain.com/langsmith/evaluation) connects offline experiments with online evaluators and feeds failing production traces back into datasets. [Braintrust online scoring](https://www.braintrust.dev/docs/evaluate/score-online) supports trace- or span-level scoring, filters, and sampling without adding request latency. [AWS](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html) exposes online, on-demand, and batch evaluation. [Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluate-agent) connects evaluation to CI/CD gates and continuous production monitoring.

### 5. Turn production failures into regression cases

This is the most consistent and useful industry pattern.

- [LangSmith](https://docs.langchain.com/langsmith/evaluation) recommends adding failed production traces to a dataset, writing targeted evaluators, testing fixes offline, and redeploying.
- [Braintrust datasets](https://www.braintrust.dev/docs/annotate/datasets) can promote selected production spans directly into evaluation rows linked to their original trace.
- [Phoenix datasets and experiments](https://arize.com/docs/phoenix/datasets-and-experiments/overview-datasets) collect cases from production or staging and apply the same attached evaluators to future experiments.

The dataset is therefore a living regression asset built from real incidents, not only a one-time benchmark written before the product exists.

### 6. Compare versions and gate releases

Experiments replay the same cases across agent configurations and compare quality with operational tradeoffs.

- [OpenAI's legacy eval guidance](https://developers.openai.com/api/docs/guides/evals), which is itself marked for retirement, frames evals as repeated tests of specified behavior when changing an application. The current [trace-grading documentation](https://developers.openai.com/api/docs/guides/trace-grading) applies graders to agent traces and supports evaluation runs filtered by model, date range, and tool calls.
- [Braintrust](https://www.braintrust.dev/docs/evaluate) treats experiments as immutable comparisons and supports CI/CD regression gates.
- [Phoenix experiments](https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments/run-experiments) compare agent versions on identical examples and encourage encoding discovered failure modes as evaluators.
- [AWS batch evaluation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html) is designed for baselines, pre/post comparisons, regression testing, and periodic audits.

This is closer to ordinary engineering than building a leaderboard.

## Industry platform comparison

| Platform | Production traces | Offline datasets/experiments | Online evaluation | Agent-process focus |
| --- | --- | --- | --- | --- |
| OpenAI | Agent traces and trace grading | Eval criteria and runs | Trace groups can be graded and filtered | End-to-end structured trace labels |
| LangSmith | Runs, traces, and threads | Datasets, experiments, annotation queues | Filtered/sampled online evaluators | Final response, single step, trajectory, and thread |
| Braintrust | Nested LLM/tool/function spans | Immutable experiments and production-derived datasets | Async trace/span scoring | Custom code and model-based trace scorers |
| Phoenix/Arize | OpenTelemetry/OpenInference traces | Datasets, reusable evaluators, comparison experiments | Production scoring through Arize | Tool, retrieval, output, evaluator, and operational traces |
| AWS AgentCore | Session/trace/span telemetry | On-demand and batch evaluation with ground truth | Sampled continuous evaluation and dashboards | Goal success, tool selection, correctness, custom rules |
| Google Cloud | Responses plus `intermediate_events` | Final-response and reference-trajectory evaluation | Public docs emphasize managed evaluation runs | Tool trajectory and rubric-based quality |
| Microsoft Foundry | OpenTelemetry/Application Insights traces | Dataset, synthetic, and historical-trace evaluation | Continuous evaluation and monitoring dashboard | Tool selection/input/success/output use plus task quality |

Google's current [agent-evaluation documentation](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-agents) evaluates final responses and predicted/reference tool trajectories. Its [engineering guidance](https://cloud.google.com/blog/topics/developers-practitioners/from-vibe-checks-to-continuous-evaluation-engineering-reliable-ai-agents) also recommends fetching live tool schemas rather than copying them into eval code, reducing schema drift.

## Evidence of actual adoption

### Survey evidence

LangChain's [State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering) reports a self-selected public survey of 1,340 respondents collected in late 2025. It reports much higher adoption for observability than formal offline or online evaluation, and shows organizations mixing human review with LLM judges.

This is useful directional evidence, but the sample is vendor-adjacent, dominated by technology respondents, and not a controlled industry census.

### Disclosed production case

AWS and Motorway publish a [production evaluation blueprint](https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents-a-production-blueprint-with-strands-and-agentcore/) combining build-time tests, tool/reasoning/output layers, deployment quality gates, and sampled production monitoring. They report a reduction in incorrect results and faster issue detection.

This is the clearest public implementation case found in this pass, but it is still a jointly published cloud-provider success story rather than independently audited evidence.

## What industry usually does not publish

- Large public corpora of genuine production failures.
- Complete user data, prompts, policies, and internal tool results.
- A universal first-error taxonomy shared across companies.
- Human-labeling disagreement and judge-calibration data.
- Exact release thresholds for quality, cost, or safety.
- Proof that an LLM evaluator remains reliable after model or prompt changes.

This explains why academic benchmarks remain useful: they supply public, shareable ground truth that companies normally keep private. The two evidence worlds solve different problems.

## Implication for our project

### Revised product framing

Do not present the project as “another coding-agent benchmark” or as a clone of CodeTracer.

Present it as a compact **agent evaluation workbench**:

```text
import or generate a trajectory
    -> attach objective outcome evidence
    -> run a small evaluator scorecard
    -> inspect findings and supporting trace spans
    -> compare two agent configurations
    -> promote a failure into the regression set
```

This reflects the industry feedback loop while staying small enough for the competition.

### Role of the public benchmark

CodeTraceBench or the τ² combination should bootstrap the project because we do not yet have production traffic:

- It supplies initial tasks, traces, outcomes, and labels.
- It validates the evaluator before real Hy3 traces accumulate.
- It provides reproducible competition metrics.
- It is not treated as the future product's only accepted input.

### Candidate scorecard dimensions

The final evaluator research selected a small number from:

- Objective task outcome.
- Tool selection and argument correctness.
- Tool execution success and output utilization.
- Constraint, policy, or side-effect compliance.
- Verification behavior.
- Efficiency: steps, retries, latency, tokens, or cost.
- Final-response quality.
- Process-error localization and classification.

First-error localization can satisfy the competition floor without becoming the product's central story.

### Potential differentiation

The strongest industry-grounded idea is **trace-to-regression**:

> A developer can turn a surprising or failed trajectory into a reusable evaluation case, rerun it against another Hy3 configuration, and see whether the fix improves quality without causing another regression.

Research 04 retained this as the first optional differentiator after the mandatory evidence debugger and evaluator validation are complete.

## Conclusion

The industry evidence does not invalidate Research 02's benchmark choice. It changes its role:

- **Academic/public benchmark:** initial reproducible ground truth.
- **Industry-style product:** continuous trace analysis, version comparison, and regression curation.

That combination is more credible and useful than either a benchmark-only submission or a trace viewer with no evaluation discipline.
