# Project 2 Requirements: Process-Level Evaluation and Error Localization

## Source and scope

This document extracts the requirements for the second practical project, **"可验证场景：过程评估与错误定位"** (*Hy3 application with process-level evaluation and error localization*), from [犀牛鸟开源-实战任务-混元大语言模型项目.pdf](../犀牛鸟开源-实战任务-混元大语言模型项目.pdf).

The keywords **must** and **required** below identify explicit requirements from the instruction PDF. Examples are illustrative rather than mandatory unless stated otherwise.

## 1. Project objective

Build a runnable AI application with Hy3 for a domain in which each task has a verifiable standard answer.

The project must evaluate more than final-answer correctness. It must also:

1. Evaluate whether the reasoning or implementation process is valid.
2. Locate the step where an error first occurs.
3. Classify the error.
4. Detect cases where the final answer is correct but the preceding process cannot support that answer.

The application must produce a complete solution process for each question or task rather than only a final answer.

## 2. Domain selection

Choose one verifiable domain. The PDF suggests the following directions, but a self-defined direction is allowed:

- **Mathematics:** competition problems, higher mathematics, or applied/word problems; evaluate the completeness and correctness of derivations.
- **Physics:** mechanics, electromagnetism, or other calculation problems; evaluate modeling assumptions, formula selection, units, and dimensions.
- **Competitive programming:** given a problem and test data, evaluate the solution approach, complexity analysis, and boundary handling.
- **Code tasks:** given requirements and test cases, evaluate whether the implementation logic is correct rather than only whether the supplied tests pass.

Whichever domain is selected must provide:

- A clear standard answer for every task.
- An automatically executable or automatically checkable correctness criterion.

## 3. Evaluation dataset

Construct a dedicated evaluation set with the following properties:

- Every item must have an unambiguous standard answer.
- Every item must have an automatic answer-validation method.
- Items must be divided into difficulty levels covering a range from basic to advanced.
- The project documentation must explain:
  - The source of the items.
  - How the items were collected or constructed.
  - The basis used to assign difficulty levels.

The instruction PDF does **not** specify a minimum dataset size, a required train/test split, or a required number of difficulty levels.

## 4. Process evaluator requirements

The process evaluator must implement all four capabilities below.

### 4.1 Process-correctness judgment

Determine whether the reasoning chain or implementation process is valid. The evaluator should be able to identify issues such as:

- Missing or skipped steps.
- Circular reasoning.
- Misused theorems, formulas, or rules.
- Omitted assumptions or conditions.
- Hallucinated facts, claims, or steps.

### 4.2 First-error localization

When a solution is incorrect, identify the step at which the error first appears.

The solution representation therefore needs stable step identifiers so that the predicted error location can be compared with the annotated or verified error location.

### 4.3 Error classification

Define and document an error taxonomy. Suggested categories include:

- Problem-statement or intent misreading.
- Conceptual misunderstanding.
- Calculation error.
- Missing condition.
- Invalid skipped-step derivation.
- Formatting noncompliance.

The taxonomy may be adapted to the selected domain, but the evaluator must assign detected errors to documented categories.

### 4.4 Correct-result/invalid-process detection

Detect samples whose final answer is correct even though their reasoning or implementation process is invalid. Examples include:

- Guessing the correct option.
- Reaching the right number by coincidence.
- Misusing a theorem but obtaining the correct result.
- Passing the supplied tests even though the implementation contains a logical defect.

## 5. Permitted evaluation techniques

The implementation method is flexible. The PDF explicitly permits approaches such as:

- Rule-based validation.
- Step-by-step LLM review.
- Sandbox execution and verification.
- Multi-agent cross-review.
- A hybrid of these methods.

No particular framework, programming language, user-interface technology, or evaluator architecture is mandated.

## 6. Evaluator effectiveness validation

Use the standard answers and annotated/verified processes to demonstrate that the process evaluator is reliable. At least the following two evaluations are required.

### 6.1 Localization accuracy

On samples with incorrect answers, evaluate whether the process evaluator:

1. Correctly detects that the process contains a problem.
2. Locates the step where the actual error begins.

Report the resulting localization-accuracy data and describe how the ground-truth error step was established.

### 6.2 False-positive analysis

On samples whose final answers are correct:

1. Collect the samples that the evaluator flags as having process problems.
2. Manually inspect those flagged samples.
3. Report what proportion contains genuine process problems.
4. Report what proportion consists of evaluator false positives.

The submission must include the validation data and the human-inspection records.

The PDF does not prescribe exact formulas, thresholds, confidence intervals, or a minimum human-inspection sample size. These choices must therefore be documented by the project.

## 7. Required result analysis

Run the complete evaluation and report:

- Final-answer accuracy.
- Process-correctness rate.
- Error-type distribution.
- Results broken down by difficulty level.
- The difficulty interval at which model performance begins to decline significantly.

The analysis must also cover:

- The rationale behind the process-evaluation method.
- The definition and rationale of the error taxonomy.
- Representative case studies.
- The model's capability boundaries.
- Critical difficulty points or thresholds where performance changes materially.

## 8. Required deliverables

### 8.1 Public open-source repository

The repository must contain:

- Runnable application source code.
- The process-evaluation module.
- A README.
- An example environment configuration.
- Setup and execution instructions.

### 8.2 Evaluation materials

Include:

- The difficulty-layered evaluation set.
- Standard answers.
- The final-answer validation script.
- The process-evaluation script.

### 8.3 Complete results

Include:

- Final-answer accuracy.
- Process-correctness rate.
- Error-type distribution.
- Difficulty-stratified results.

### 8.4 Effectiveness-validation evidence

Include:

- Localization-accuracy validation data.
- False-positive validation data.
- Human-inspection records.

### 8.5 Analysis report

Include:

- Process-evaluation design rationale.
- Error-taxonomy documentation.
- Representative case analysis.
- Model capability-boundary analysis.
- Critical-point or failure-threshold analysis.

### 8.6 Demonstration

Provide a video or GIF no longer than two minutes. It must demonstrate one complete workflow from solving a task through process evaluation.

## 9. Submission and repository rules

These rules apply to both practical projects and therefore also apply to Project 2:

- Create and maintain a new public repository on GitHub or a similar platform.
- Submit the repository link when the project is complete.
- Do not submit a pull request to the official Hy3 repository.
- The README must explain the project, how to run it, and its environment requirements.
- Do not hard-code or commit API keys or other secrets. Supply them through environment variables or configuration files.
- Clearly mark the repository name and README as an individual/event project so it is not mistaken for an official Tencent release.
- Invoke model capabilities through Hy3.
- Model training or fine-tuning is not required.

Hy3 reference repository: <https://github.com/Tencent-Hunyuan/Hy3>

## 10. Acceptance checklist

- [ ] A verifiable domain has been selected and justified.
- [ ] The Hy3 application runs and outputs a step-by-step solution.
- [ ] Every evaluation item has a standard answer and automatic checker.
- [ ] The evaluation set spans documented difficulty levels.
- [ ] Item sources, construction, and difficulty criteria are documented.
- [ ] The evaluator judges process correctness.
- [ ] The evaluator identifies the first erroneous step.
- [ ] A domain-appropriate error taxonomy is documented and implemented.
- [ ] Correct-answer/invalid-process cases are detected.
- [ ] Localization accuracy is measured on incorrect-answer samples.
- [ ] False positives are manually audited on correct-answer samples.
- [ ] Human-inspection records are retained.
- [ ] Final-answer accuracy is reported.
- [ ] Process-correctness rate is reported.
- [ ] Error-type distribution is reported.
- [ ] Results are analyzed by difficulty.
- [ ] The model's decline interval, capability boundary, and critical points are analyzed.
- [ ] Source code, scripts, dataset, answers, configuration example, and documentation are in the public repository.
- [ ] Secrets are excluded from the repository.
- [ ] The repository is labeled as an individual/event project.
- [ ] A complete demo video or GIF is provided and is no longer than two minutes.

## 11. Minimum end-to-end workflow

```text
Question or task
    -> Hy3 generates a step-by-step solution
    -> final-answer checker verifies the result
    -> process evaluator validates each step
    -> evaluator identifies the first error, if any
    -> evaluator assigns an error category
    -> results are aggregated by metric and difficulty
    -> validation evidence and analysis report are produced
```
