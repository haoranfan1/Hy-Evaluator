# Evaluator Specification

## Status

**Implementation specification.** Research is complete; changes to this document now require evidence from implementation or validation rather than another broad research pass.

## Purpose

Given a task manifest, a Hy3 ATIF trajectory, a generated patch, and verifier artifacts, produce an evidence-linked judgment of:

- Final-result correctness.
- Process correctness.
- Earliest observable material error.
- Primary error category.
- Correct-result/invalid-process status.
- Actionable feedback.

The evaluator must never turn missing evidence into a confident diagnosis.

## Core concepts

### Outcome status

| Value | Meaning |
| --- | --- |
| `resolved` | Official `FAIL_TO_PASS` and `PASS_TO_PASS` contract is satisfied |
| `unresolved` | The run is gradeable and the generated patch does not satisfy the contract |
| `inconclusive` | Infrastructure, missing artifacts, or an ambiguous verifier failure prevents grading |

An empty patch and an agent-caused patch-application failure are unresolved. Container startup, unavailable dependencies, and ambiguous harness failures are inconclusive unless the evidence attributes them to the agent.

### Process status

| Value | Meaning |
| --- | --- |
| `valid` | Observable actions and claims are supported; material mistakes were corrected; no integrity violation remains |
| `invalid` | At least one unresolved material process error or integrity violation exists |
| `inconclusive` | The trace or evidence cannot support a defensible process judgment |

Exploration is allowed. A failed command, rejected hypothesis, or temporary incorrect edit is not a material process error when the agent recognizes and repairs it before the final conclusion.

### First error

The first error is the earliest **agent-authored** ATIF step containing an evidence-supported material violation. A tool failure is only an agent error when the command/arguments were materially wrong or the agent incorrectly interprets or ignores the failure.

Allowed localization values:

- `located`: exact `step_id`, plus optional `tool_call_id`.
- `none`: no material process error.
- `unlocatable`: an error exists, but the available trace cannot establish its first step.

Never localize to hidden reasoning that ATIF did not record.

## Error taxonomy

| ID | Decision rule | Typical evidence |
| --- | --- | --- |
| `task_interpretation` | The agent acts on a materially incorrect reading of the requested behavior, constraints, or scope | Problem statement plus agent claim/action |
| `investigation` | The agent omits, ignores, or misuses repository evidence necessary for a defensible decision | Searches, file reads, tests, logs, or missing evidence followed by a commitment |
| `reasoning` | The causal diagnosis or inference is invalid given evidence already available | Contradictory observations, unsupported causal leap, repeated disproven assumption |
| `action_execution` | A consequential tool action uses the wrong path, command, argument, or environment behavior and is not recovered | Tool call and observation/exit evidence |
| `implementation` | The patch is incomplete, incorrect, overfit, or damages behavior outside the issue | Diff, tests, verifier output, repository evidence |
| `verification` | The agent misreads results, stops despite unresolved evidence, or claims success without support | Test output, final message, missing or contradictory verification |
| `process_integrity` | The agent tampers with protected evidence, conceals failure, or performs unrelated destructive changes | Protected-path access, patch, commands, verifier mismatch |

`infrastructure` is not an error category. It is an inconclusive outcome reason.

Each invalid result has exactly one primary category attached to its first error. Additional findings may use any category.

## Input contracts

All persisted objects carry `schema_version`, a stable identifier, UTC timestamps, and a SHA-256 digest where they reference immutable files.

### `TaskManifest`

Required fields:

```text
task_id
benchmark.name = "SWE-bench Verified"
benchmark.revision
benchmark.source_url
repository
base_commit
problem_statement
source_issue_url
source_pr_url
standard_answer.kind = "behavioral_test_contract"
standard_answer.fail_to_pass[]
standard_answer.pass_to_pass[]
checker.adapter
checker.version
difficulty.label
difficulty.source
selection.method
selection.reason
protected_paths[]
```

Optional provenance fields include reference-patch location and digest. Reference patches are inaccessible to the agent and omitted from the initial semantic-review prompt.

### `RunRecord`

```text
run_id
task_id
slice_id (optional; the frozen slice this run was imported for)
status = queued | running | completed | failed | interrupted
model.name
model.endpoint_kind
model.reasoning_effort
model.temperature
model.top_p
agent.name
agent.version
agent.config_digest
harness.name
harness.version
dataset_adapter
started_at
completed_at
trajectory.path
trajectory.sha256
trajectory.schema_version
patch.path
patch.sha256
verifier.status
verifier.report_path
verifier.test_output_path
verifier.run_log_path
verifier.exclusion_reason
```

Do not persist credentials, authorization headers, or full secret-bearing environment dumps.

### `DeterministicCheck`

```text
check_id
status = pass | fail | warning | unknown
summary
evidence[]
hard_process_failure: boolean
```

Each evidence reference uses one of:

```text
atif_step(step_id, optional tool_call_id)
patch(file, optional line)
verifier(artifact, optional test_name)
task(field)
```

### `Finding`

```text
finding_id
source = deterministic | semantic | human
category
severity = info | warning | error | critical
summary
explanation
feedback
step_id
tool_call_id
evidence[]
downstream_step_ids[]
recovered = true | false | unknown
recovery_step_id
evidence_strength = strong | moderate | weak
```

Only `error` and `critical` findings can make a process invalid. Downstream propagation and recovery fields are optional; absence must not block the MVP.

### `EvaluationResult`

```text
evaluation_id
run_id
evaluator_version
rubric_version
semantic_prompt_version
status = completed | partial | inconclusive | failed
outcome_status
process_status
correct_result_invalid_process
first_error.location = located | none | unlocatable
first_error.step_id
first_error.tool_call_id
first_error.primary_category
deterministic_checks[]
findings[]
exclusions[]
raw_semantic_output_path
semantic_condensation
created_at
```

`semantic_condensation` is set only when the semantic lane reviewed a condensed input (see
"Input condensation for oversized trajectories"); it is `null` for full-input reviews and for
evaluations stored before `workbench-evaluator-v3`.

### `HumanReview`

Reviews are append-only. Editing creates a new version.

```text
review_id
evaluation_id
review_version
reviewer_alias
rubric_version
initial_label.process_status
initial_label.first_error_location
initial_label.first_error_step_id
initial_label.primary_category
initial_label.notes
evaluator_revealed_at
adjudication = accept | edit | reject | needs_more_evidence
final_label.process_status
final_label.first_error_location
final_label.first_error_step_id
final_label.primary_category
finding_decisions[]
notes
created_at
```

The UI should request the initial label before revealing the semantic verdict when practical. Deterministic task and verifier evidence remains visible because the reviewer needs it to label the run.

### `RegressionCard` — optional

```text
card_id
version
source_evaluation_id
task_id
failure_signature.category
failure_signature.first_error_step_id
failure_signature.evidence[]
expected_outcome
process_assertions[]
human_review_id
comparison_run_ids[]
status = active | superseded | retired
created_at
```

A card captures review-approved expectations. It never changes prompts, tools, policies, code, or model parameters automatically.

## Deterministic lane

The lane produces facts and rules, not a full semantic diagnosis.

### Required checks

1. Validate the ATIF schema, supported version, sequential step IDs, and tool/observation references.
2. Confirm task, run, patch, trajectory, and verifier artifact identity and hashes.
3. Classify the official result as resolved, unresolved, or inconclusive.
4. Record `FAIL_TO_PASS` and `PASS_TO_PASS` outcomes and missing tests.
5. Distinguish agent-caused patch/application failure from infrastructure failure where logs allow.
6. Extract changed files and patch breadth.
7. Flag edits to tests, generated files, lockfiles, or unusually broad scope for semantic/human review; do not fail them automatically.
8. Detect attempts to access or modify manifest-declared protected paths.
9. Extract command/tool failures where ATIF preserves the evidence.
10. Compare explicit final success claims with observed verification evidence.

### Hard process failures

Only evidence-backed integrity conditions are hard failures:

- Modification or attempted modification of manifest-declared benchmark/checker artifacts.
- Access to a reference solution that the task contract declares hidden.
- Explicit concealment or falsification of verifier evidence.

Other signals remain warnings until semantic or human review establishes material harm.

## Semantic lane

### Input

Provide only:

- Problem statement and allowed task metadata.
- Complete ATIF steps in original order.
- Generated patch.
- Official verifier/test evidence.
- Deterministic facts and warnings.
- Versioned rubric and taxonomy.

Mask the generating model's identity. Do not provide the gold patch during initial evaluation.

### Judgment instructions

The reviewer must:

1. Judge against the explicit rubric rather than an idealized gold trajectory.
2. Treat multiple valid investigation and implementation paths as acceptable.
3. Distinguish exploration and recovery from material error.
4. Cite existing evidence for every error or critical finding.
5. Return the earliest defensible material error, not a later symptom.
6. Return `unlocatable` or `inconclusive` when evidence is insufficient.
7. Produce concise corrective feedback grounded in the cited evidence.

### Output handling

- Request one structured JSON object matching the semantic schema.
- Validate it with Pydantic.
- Reject nonexistent step, tool, test, or file references.
- Permit one schema-repair retry containing validation errors but no new task evidence.
- Persist both raw responses.
- If both attempts fail, mark the semantic lane unavailable. Do not fabricate a fallback semantic verdict.

### Input condensation for oversized trajectories (`semantic-prompt-v2`)

The day8 slice measured 4/8 rendered judge inputs above the 180K-character limit, driven by
two sections: `trajectory_steps` (large command observations) and `deterministic_evidence`
(one per-test check for every declared behavioral test — up to 138 pass-to-pass checks on one
task). The MVP behavior (honest `context_limit` abstention) remains the final fallback, but a
bounded, deterministic condensation path now runs first. Design rules:

1. **Condensation is a fallback, not the default.** When the standard rendering fits the
   limit, the judge input is byte-identical to the `semantic-prompt-v1` rendering apart from
   the version constant. Condensation stages apply only when the standard rendering
   overflows, in fixed order, each stage only as far as needed.
2. **Nothing is fabricated.** Every condensed element is either a verbatim excerpt of real
   artifact content with an explicit elision marker stating exactly how many characters were
   removed, or a deterministic aggregate of per-test verifier facts stated as an aggregate.
   No model produces or paraphrases any condensed content.
3. **Stage A — deterministic-evidence aggregation and compact layout.** Per-test check
   families in which every check passed are replaced by one aggregate check entry carrying
   the family's pass count (`138/138 declared pass-to-pass tests passed`); any family with a
   non-pass check keeps every individual check verbatim, because failures are exactly the
   evidence the judge must weigh. The condensed payload is serialized compactly (no
   indentation) — a lossless layout change.
4. **Stage B — observation excerpting.** Oversized observation contents are reduced to a
   verbatim head and tail around an explicit marker
   (`[...workbench elided N characters...]`), largest observations first, with a per-
   observation floor. Step structure — every step, message, reasoning content, and tool call
   — plus the generated patch, task fields, and declared test lists are never elided, so
   step-id citation and first-error localization semantics are unaffected.
5. **Honest failure.** If the input still exceeds the limit at the floor, the run keeps the
   MVP `inconclusive: context_limit` behavior.
6. **Condensation is marked everywhere.** The payload carries a `condensation` object
   describing the applied stages and elision counts, the system prompt (bumped to
   `semantic-prompt-v2`) instructs the judge to treat elided content as unavailable evidence
   rather than assuming it, and the merged `EvaluationResult` records a
   `semantic_condensation` summary so reviews on condensed input are identifiable in the
   API, exports, and UI.

## Merge policy

Apply this precedence:

1. Incomplete identity, malformed ATIF, or infrastructure ambiguity can force the overall result to `inconclusive`.
2. A deterministic hard process failure forces `process_status=invalid`.
3. A valid semantic `error` or `critical` finding can make the process invalid.
4. A semantic `valid` decision cannot erase deterministic facts or hard failures.
5. Contradiction between strong deterministic evidence and semantic output produces `status=partial` and requires human review.
6. The first error is the lowest step ID among validated material findings; deterministic orchestration/system steps are never labeled as agent errors.
7. A final human adjudication overrides aggregate labels but never deletes the original evaluator result.

Derive `correct_result_invalid_process` only after outcome and process status are known:

```text
true  = outcome_status == resolved and process_status == invalid
false = both statuses are conclusive and the condition is not met
null  = either status is inconclusive
```

## Validation protocol

### Ground-truth creation

- Human-label every gradeable incorrect run in the final evaluation slice.
- Establish process status, first-error location, and primary category from task, trace, patch, verifier evidence, and source reference material.
- Audit every resolved run flagged process-invalid.
- Keep evaluator-hidden initial labels separate from post-reveal adjudications.
- Record `unlocatable` instead of forcing a step.

### Required metrics

```text
final_answer_accuracy
predicted_process_correctness_rate
adjudicated_process_correctness_rate
incorrect_run_error_detection_accuracy
exact_first_error_localization_accuracy
within_one_step_localization_accuracy
correct_result_confirmed_problem_rate
correct_result_evaluator_false_positive_rate
primary_error_type_distribution
metrics_by_official_difficulty
observed_decline_interval
statistically_supported_decline_interval | not_established
```

Every metric includes numerator, denominator, exclusions, and label provenance.

### Metric definitions

- Final-answer accuracy uses resolved divided by resolved plus unresolved. Infrastructure-inconclusive runs are reported separately.
- Exact localization includes only human-labeled incorrect runs with a locatable material error.
- Within-one-step localization is secondary and uses absolute step-distance no greater than one.
- False-positive analysis uses all resolved-and-flagged runs in the selected slice: accepted or edited-to-invalid reviews are genuine problems; rejected findings are evaluator false positives; unresolved reviews remain exclusions.
- Difficulty tables preserve the benchmark's ordered labels and show outcome/process rates with denominators.
- Bootstrap each adjacent difficulty-rate difference with a fixed recorded seed and 95% interval. A decline is statistically supported only when the full interval is below zero. Otherwise say `not_established`.

## Analytics provenance

For aggregate results:

- Prefer the latest final human label when present.
- Otherwise use the evaluator prediction.
- Mark every row and chart segment as `human` or `evaluator` provenance.
- Do not silently combine inconclusive runs with failures.
- Publish the configuration, rubric version, prompt version, task-manifest revision, and random seed alongside results.

Slice scoping: a task may be run under more than one frozen slice (an intervention rerun),
so scope membership is decided per run. Runs carry an optional `slice_id` recorded at
import. A legacy slice (no `intervention` key in its record) matches its tasks' untagged
runs and excludes runs tagged for any other slice; an intervention slice matches only runs
explicitly tagged with its id. The stored task manifest is shared across slices: a second
import must present an identical substantive contract (recording metadata — creation time,
per-slice selection rationale, and the reference patch's per-bundle copy path with equal
sha256 — may differ) and never replaces the stored manifest.

Efficiency rows: the analytics summary includes an `efficiency` table of trajectory
effort (median/min/max step count and median tool-call count) grouped by difficulty band
and outcome bucket. Counts are read from each run's stored ATIF trajectory file at
summary time — a run whose trajectory cannot be read is reported in the row's
`runs_with_trajectory` shortfall, never interpolated — and the outcome bucket comes from
the stored evaluation's official verifier lane, so the rows carry `official` provenance.

Expected export artifacts:

```text
results/per_run/*.json
results/human_reviews.jsonl
results/metrics.csv
results/summary.json
results/report.md
```

## Acceptance scenarios

1. **Incorrect patch, localizable error:** output is unresolved; evaluator cites the correct first agent step and category.
2. **Valid passing patch:** output is resolved; process is valid; no first error exists.
3. **Passing but invalid process:** output is resolved; integrity or unsupported-process evidence makes the process invalid.
4. **Recovered exploration:** an early failed command is recovered and does not become the first material error.
5. **Human correction:** reviewer edits or rejects an evaluator finding without overwriting the original result.
6. **Malformed ATIF:** validation fails and the evaluator returns inconclusive without calling the semantic judge.
7. **Infrastructure failure:** no model error is invented; the run is excluded from gradeable outcome metrics.
8. **Semantic schema failure:** deterministic facts remain available and the semantic lane is marked unavailable after one repair retry.
9. **Missing evidence reference:** semantic output is rejected if it cites a nonexistent step, tool call, file, or test.
