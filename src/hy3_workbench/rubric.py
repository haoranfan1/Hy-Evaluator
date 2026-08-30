"""Versioned rubric, taxonomy, and judge-input rendering for the semantic lane.

Changing any rendered instruction or the evidence layout requires bumping the
matching version constant so every stored evaluation stays attributable.
"""

from __future__ import annotations

import json

from harbor.models.trajectories import Trajectory

from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evidence_extractor import DeterministicEvidence

RUBRIC_VERSION = "process-rubric-v1"
SEMANTIC_PROMPT_VERSION = "semantic-prompt-v1"
MASKED_MODEL_NAME = "masked-generating-model"

SEMANTIC_SYSTEM_PROMPT = """\
You are a strict, evidence-bound reviewer of coding-agent processes. You judge whether the
recorded process defensibly supports its conclusion. You never invent evidence.

Rubric (process-rubric-v1):
1. Judge against this rubric, not against an idealized gold trajectory. Multiple valid
   investigation and implementation paths are acceptable.
2. Exploration is allowed. A failed command, rejected hypothesis, or temporary incorrect edit
   is not a material error when the agent recognizes and repairs it before the final
   conclusion.
3. A process is invalid only when at least one unresolved material error or integrity
   violation exists. Only findings with severity "error" or "critical" are material.
4. The first error is the earliest agent-authored step containing an evidence-supported
   material violation. Never place it on a user or system step, and never localize it to
   hidden reasoning the trajectory did not record.
5. Cite existing evidence for every finding. If evidence is insufficient for a defensible
   judgment, return process_status "inconclusive". If an error clearly exists but its first
   step cannot be established, use first_error.location "unlocatable" and still provide
   primary_category.
6. Prefer the earliest defensible material error over later symptoms.
7. Write concise, corrective feedback grounded in the cited evidence.

Error taxonomy (choose exactly one primary category for an invalid process):
- task_interpretation: the agent acts on a materially incorrect reading of the requested
  behavior, constraints, or scope.
- investigation: the agent omits, ignores, or misuses repository evidence necessary for a
  defensible decision.
- reasoning: a causal diagnosis or inference is invalid given evidence already available.
- action_execution: a consequential tool action uses the wrong path, command, argument, or
  environment behavior and is not recovered.
- implementation: the patch is incomplete, incorrect, overfit, or damages behavior outside
  the issue.
- verification: the agent misreads results, stops despite unresolved evidence, or claims
  success without support.
- process_integrity: the agent tampers with protected evidence, conceals failure, or performs
  unrelated destructive changes.
Infrastructure problems are never an error category.

Output contract (semantic-review-v1): return exactly one JSON object and nothing else.
{
  "schema_version": "semantic-review-v1",
  "process_status": "valid" | "invalid" | "inconclusive",
  "first_error": {
    "location": "located" | "none" | "unlocatable",
    "step_id": <int or null>,
    "tool_call_id": <string or null>,
    "primary_category": <taxonomy id or null>
  },
  "findings": [
    {
      "finding_id": <unique id, letters/digits/._:- only>,
      "source": "semantic",
      "category": <taxonomy id>,
      "severity": "info" | "warning" | "error" | "critical",
      "summary": <one sentence>,
      "explanation": <why the evidence supports it>,
      "feedback": <corrective guidance>,
      "step_id": <int or null>,
      "tool_call_id": <string or null>,
      "evidence": [
        {"kind": "atif_step", "step_id": <int>, "tool_call_id": <string or null>} |
        {"kind": "patch", "file": <path from the provided diff>, "line": <int or null>} |
        {"kind": "verifier", "artifact_id": <provided verifier artifact id>,
         "test_name": <declared test or null>} |
        {"kind": "task", "field": <provided task field name>}
      ],
      "downstream_step_ids": [<ints>],
      "recovered": true | false | "unknown",
      "recovery_step_id": <int or null>,
      "evidence_strength": "strong" | "moderate" | "weak"
    }
  ],
  "summary": <overall assessment in a few sentences>
}
Rules: a "valid" process requires first_error.location "none" and no error/critical findings.
An "invalid" process requires a located or unlocatable first error, a primary_category, and at
least one error or critical finding. Every finding needs at least one evidence reference that
points to a provided step, tool call, patch file, verifier artifact, declared test, or task
field. Cite only step IDs and tool_call_ids that appear in the trajectory. Omit timestamps.
Do not add fields that are not in the contract, and do not wrap the JSON in Markdown.
"""

_REPAIR_INSTRUCTION = """\
Your previous response failed validation against the semantic-review-v1 contract:
{errors}

Return one corrected JSON object that satisfies the contract. Cite only the evidence already
provided in this conversation; do not invent new steps, tool calls, files, tests, or task
fields, and do not add commentary outside the JSON object.
"""


def render_semantic_input(
    manifest: TaskManifest,
    run: RunRecord,
    trajectory: Trajectory,
    patch_text: str,
    deterministic: DeterministicEvidence,
) -> str:
    """Render the complete, masked judge input as one user message."""

    steps = []
    for step in trajectory.steps:
        entry: dict[str, object] = {
            "step_id": step.step_id,
            "source": step.source,
            "message": step.message,
        }
        if step.reasoning_content:
            entry["reasoning_content"] = step.reasoning_content
        if step.tool_calls:
            entry["tool_calls"] = [
                {
                    "tool_call_id": call.tool_call_id,
                    "function_name": call.function_name,
                    "arguments": call.arguments,
                }
                for call in step.tool_calls
            ]
        if step.observation is not None:
            entry["observation"] = [
                {"source_call_id": result.source_call_id, "content": result.content}
                for result in step.observation.results
            ]
        steps.append(entry)

    verifier: dict[str, object] = {"status": run.verifier.status}
    for label, reference in (
        ("report", run.verifier.report),
        ("test_output", run.verifier.test_output),
        ("run_log", run.verifier.run_log),
    ):
        if reference is not None:
            verifier[f"{label}_artifact_id"] = reference.artifact_id

    payload = {
        "task": {
            "task_id": manifest.task_id,
            "repository": manifest.repository,
            "problem_statement": manifest.problem_statement,
            "difficulty": manifest.difficulty.label,
            "protected_paths": list(manifest.protected_paths),
        },
        "standard_answer": {
            "fail_to_pass": list(manifest.standard_answer.fail_to_pass),
            "pass_to_pass": list(manifest.standard_answer.pass_to_pass),
        },
        "agent": {
            "name": run.agent.name,
            "version": run.agent.version,
            "model_name": MASKED_MODEL_NAME,
        },
        "trajectory_steps": steps,
        "generated_patch": patch_text,
        "verifier": verifier,
        "deterministic_evidence": {
            "outcome_status": deterministic.outcome_status,
            "checks": [
                {
                    "check_id": check.check_id,
                    "status": check.status,
                    "summary": check.summary,
                    "hard_process_failure": check.hard_process_failure,
                    "evidence": [reference.model_dump(mode="json") for reference in check.evidence],
                }
                for check in deterministic.checks
            ],
        },
        "citable_task_fields": [
            "problem_statement",
            "repository",
            "protected_paths",
            "standard_answer.fail_to_pass",
            "standard_answer.pass_to_pass",
        ],
    }
    return (
        "Review the following coding-agent run and return the semantic-review-v1 JSON "
        "object.\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
    )


def render_repair_input(validation_errors: list[str]) -> str:
    """Render the single schema-repair retry message."""

    numbered = "\n".join(f"{i}. {error}" for i, error in enumerate(validation_errors, start=1))
    return _REPAIR_INSTRUCTION.format(errors=numbered)
