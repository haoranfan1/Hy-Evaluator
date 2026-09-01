import json
import shutil
from pathlib import Path

import pytest

from hy3_workbench.contracts import RunRecord, TaskManifest
from hy3_workbench.evidence_extractor import EvidenceExtractor
from hy3_workbench.hy3_client import Hy3JsonResponse
from hy3_workbench.rubric import (
    MASKED_MODEL_NAME,
    RUBRIC_VERSION,
    SEMANTIC_PROMPT_VERSION,
    SEMANTIC_SYSTEM_PROMPT,
    condense_semantic_input,
    render_semantic_input,
)
from hy3_workbench.semantic_reviewer import SemanticReviewer

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures"
SEMANTIC_DIR = Path(".local/test-semantic")


class FakeJudge:
    def __init__(self, contents: list[str]) -> None:
        self.contents = list(contents)
        self.calls: list[list[dict[str, str]]] = []

    def complete_json(self, messages: list[dict[str, str]]) -> Hy3JsonResponse:
        assert self.contents, "judge called more times than scripted"
        self.calls.append(messages)
        return Hy3JsonResponse(
            response_id=f"chatcmpl-fake-{len(self.calls)}",
            model="hy3-judge",
            content=self.contents.pop(0),
            reasoning_content_received=True,
        )


def valid_response() -> str:
    return json.dumps(
        {
            "schema_version": "semantic-review-v1",
            "process_status": "valid",
            "first_error": {
                "location": "none",
                "step_id": None,
                "tool_call_id": None,
                "primary_category": None,
            },
            "findings": [],
            "summary": "The recorded process defensibly supports the final conclusion.",
        }
    )


def invalid_response(step_id: int = 3, tool_call_id: str | None = "call-edit-1") -> str:
    return json.dumps(
        {
            "schema_version": "semantic-review-v1",
            "process_status": "invalid",
            "first_error": {
                "location": "located",
                "step_id": step_id,
                "tool_call_id": tool_call_id,
                "primary_category": "task_interpretation",
            },
            "findings": [
                {
                    "finding_id": "finding-reversed-requirement",
                    "source": "semantic",
                    "category": "task_interpretation",
                    "severity": "error",
                    "summary": "The agent reversed the explicit requirement to preserve zero.",
                    "explanation": (
                        "The task distinguishes zero from None, but the edit groups them "
                        "and the declared FAIL_TO_PASS test still fails."
                    ),
                    "feedback": (
                        "Translate the requirement into a None-only condition and run the "
                        "declared FAIL_TO_PASS test before concluding."
                    ),
                    "step_id": step_id,
                    "tool_call_id": tool_call_id,
                    "evidence": [
                        {"kind": "atif_step", "step_id": step_id, "tool_call_id": tool_call_id},
                        {"kind": "task", "field": "problem_statement"},
                        {"kind": "patch", "file": "src/calculator.py", "line": 2},
                    ],
                    "downstream_step_ids": [],
                    "recovered": False,
                    "recovery_step_id": None,
                    "evidence_strength": "strong",
                }
            ],
            "summary": "The process fails at the requirement-interpretation step.",
        }
    )


def load_review_inputs(name: str):
    root = FIXTURE_ROOT / name
    manifest = TaskManifest.model_validate_json(
        (root / "manifest.json").read_text(encoding="utf-8")
    )
    run = RunRecord.model_validate_json((root / "run.json").read_text(encoding="utf-8"))
    extractor = EvidenceExtractor(PROJECT_ROOT)
    deterministic = extractor.extract(manifest, run)
    trajectory = extractor.atif.load(PROJECT_ROOT / run.trajectory.path)
    patch_text = (PROJECT_ROOT / run.patch.path).read_text(encoding="utf-8")
    return manifest, run, trajectory, patch_text, deterministic


@pytest.fixture()
def reviewer_factory():
    def build(judge: FakeJudge, context_limit_chars: int = 180_000) -> SemanticReviewer:
        return SemanticReviewer(PROJECT_ROOT, judge, SEMANTIC_DIR, context_limit_chars)

    yield build
    shutil.rmtree(PROJECT_ROOT / SEMANTIC_DIR, ignore_errors=True)


class TestSemanticReviewer:
    def test_valid_response_completes_in_one_attempt(self, reviewer_factory) -> None:
        judge = FakeJudge([invalid_response()])
        reviewer = reviewer_factory(judge)

        result = reviewer.review(*load_review_inputs("invalid-first-error"))

        assert result.status == "completed"
        assert result.attempts == 1
        assert result.output is not None
        assert result.output.process_status == "invalid"
        assert result.output.first_error.step_id == 3
        assert result.rubric_version == RUBRIC_VERSION
        assert result.prompt_version == SEMANTIC_PROMPT_VERSION
        assert len(judge.calls) == 1
        assert judge.calls[0][0]["role"] == "system"

    def test_dangling_reference_triggers_one_repair_retry(self, reviewer_factory) -> None:
        judge = FakeJudge([invalid_response(step_id=99, tool_call_id=None), invalid_response()])
        reviewer = reviewer_factory(judge)

        result = reviewer.review(*load_review_inputs("invalid-first-error"))

        assert result.status == "completed"
        assert result.attempts == 2
        assert len(judge.calls) == 2
        repair_message = judge.calls[1][-1]
        assert repair_message["role"] == "user"
        assert "failed validation" in repair_message["content"]
        assert "99" in repair_message["content"]
        assert "do not invent new steps" in repair_message["content"]
        assert len(result.raw_response_paths) == 2

    def test_two_failures_leave_the_lane_unavailable(self, reviewer_factory) -> None:
        bad = invalid_response(step_id=99, tool_call_id=None)
        judge = FakeJudge([bad, bad])
        reviewer = reviewer_factory(judge)

        result = reviewer.review(*load_review_inputs("invalid-first-error"))

        assert result.status == "unavailable"
        assert result.output is None
        assert result.attempts == 2
        assert len(result.failure_reasons) == 2
        assert len(judge.calls) == 2

    def test_raw_responses_are_persisted_under_local_state(self, reviewer_factory) -> None:
        judge = FakeJudge([valid_response()])
        reviewer = reviewer_factory(judge)
        inputs = load_review_inputs("valid")

        result = reviewer.review(*inputs)

        assert result.status == "completed"
        assert result.raw_response_paths == [
            f"{SEMANTIC_DIR.as_posix()}/{inputs[1].run_id}/attempt-1.json"
        ]
        record = json.loads(
            (PROJECT_ROOT / result.raw_response_paths[0]).read_text(encoding="utf-8")
        )
        assert record["schema_version"] == "semantic-raw-response-v1"
        assert record["validation_errors"] == []
        assert json.loads(record["content"])["process_status"] == "valid"

    def test_context_limit_skips_the_judge(self, reviewer_factory) -> None:
        judge = FakeJudge([])
        reviewer = reviewer_factory(judge, context_limit_chars=1_000)

        result = reviewer.review(*load_review_inputs("valid"))

        assert result.status == "context_limit"
        assert result.output is None
        assert judge.calls == []


class TestRenderedJudgeInput:
    def test_input_masks_the_generating_model(self) -> None:
        manifest, run, trajectory, patch_text, deterministic = load_review_inputs("valid")
        secret_run = run.model_copy(
            update={"model": run.model.model_copy(update={"name": "hy3-secret-model"})}
        )

        rendered = render_semantic_input(
            manifest, secret_run, trajectory, patch_text, deterministic
        )

        assert "hy3-secret-model" not in rendered
        assert MASKED_MODEL_NAME in rendered

    def test_input_contains_the_complete_allowed_evidence(self) -> None:
        manifest, run, trajectory, patch_text, deterministic = load_review_inputs("valid")

        rendered = render_semantic_input(manifest, run, trajectory, patch_text, deterministic)

        assert manifest.problem_statement in rendered
        assert manifest.standard_answer.fail_to_pass[0] in rendered
        assert "diff --git" in rendered
        assert all(str(step.step_id) in rendered for step in trajectory.steps)
        assert "check-outcome" in rendered
        assert "reference_patch" not in rendered


class RaisingJudge:
    """Judge whose first N calls raise a transport error, then delegates."""

    def __init__(self, raise_count: int, then: FakeJudge | None = None) -> None:
        self.raise_count = raise_count
        self.then = then
        self.calls = 0

    def complete_json(self, messages):
        self.calls += 1
        if self.calls <= self.raise_count:
            raise TimeoutError("simulated judge transport timeout")
        assert self.then is not None
        return self.then.complete_json(messages)


class TestJudgeTransportFailures:
    def test_persistent_transport_failure_degrades_to_unavailable(self, reviewer_factory) -> None:
        reviewer = reviewer_factory(RaisingJudge(raise_count=2))

        result = reviewer.review(*load_review_inputs("valid"))

        assert result.status == "unavailable"
        assert result.attempts == 2
        assert all("judge request failed" in reason for reason in result.failure_reasons)
        assert "TimeoutError" in result.failure_reasons[0]

    def test_single_transport_failure_retries_and_completes(self, reviewer_factory) -> None:
        judge = RaisingJudge(raise_count=1, then=FakeJudge([valid_response()]))
        reviewer = reviewer_factory(judge)

        result = reviewer.review(*load_review_inputs("valid"))

        assert result.status == "completed"
        assert judge.calls == 2


def big_trajectory(n_agent_steps: int = 5, observation_chars: int = 30_000):
    from harbor.models.trajectories import (
        Agent,
        Observation,
        ObservationResult,
        Step,
        ToolCall,
        Trajectory,
    )

    steps = [Step(step_id=1, source="user", message="task statement")]
    line = "x" * 97 + "\n"
    for step_id in range(2, n_agent_steps + 2):
        content = json.dumps({"returncode": 0, "output": line * (observation_chars // len(line))})
        steps.append(
            Step(
                step_id=step_id,
                source="agent",
                message=f"inspect part {step_id}",
                tool_calls=[
                    ToolCall(
                        tool_call_id=f"call-{step_id}",
                        function_name="bash",
                        arguments={"command": f"cat part_{step_id}.txt"},
                    )
                ],
                observation=Observation(
                    results=[ObservationResult(source_call_id=f"call-{step_id}", content=content)]
                ),
            )
        )
    return Trajectory(
        schema_version="ATIF-v1.7",
        session_id="run-big",
        agent=Agent(name="mini-swe-agent", version="2.4.6"),
        steps=steps,
    )


class TestCondensation:
    LIMIT = 100_000

    def oversized_inputs(self):
        manifest, run, _, patch_text, deterministic = load_review_inputs("valid")
        return manifest, run, big_trajectory(), patch_text, deterministic

    def test_oversized_input_is_condensed_and_reviewed(self, reviewer_factory) -> None:
        judge = FakeJudge([valid_response()])
        reviewer = reviewer_factory(judge, context_limit_chars=self.LIMIT)
        inputs = self.oversized_inputs()
        assert len(render_semantic_input(*inputs)) > self.LIMIT

        result = reviewer.review(*inputs)

        assert result.status == "completed"
        assert result.condensation is not None
        assert result.condensation.startswith("semantic-condense-v1:")
        assert "excerpted observations" in result.condensation
        assert len(judge.calls) == 1
        sent = judge.calls[0][1]["content"]
        assert len(judge.calls[0][0]["content"]) + len(sent) <= self.LIMIT
        assert "workbench elided" in sent
        assert '"condensation"' in sent

    def test_condensed_input_preserves_steps_commands_and_patch(self, reviewer_factory) -> None:
        judge = FakeJudge([valid_response()])
        reviewer = reviewer_factory(judge, context_limit_chars=self.LIMIT)
        manifest, run, trajectory, patch_text, deterministic = self.oversized_inputs()

        reviewer.review(manifest, run, trajectory, patch_text, deterministic)

        payload = json.loads(judge.calls[0][1]["content"].split("\n\n", 1)[1])
        rendered_steps = {entry["step_id"] for entry in payload["trajectory_steps"]}
        assert rendered_steps == {step.step_id for step in trajectory.steps}
        commands = [
            call["arguments"]["command"]
            for entry in payload["trajectory_steps"]
            for call in entry.get("tool_calls", [])
        ]
        assert commands == [f"cat part_{i}.txt" for i in range(2, 7)]
        assert payload["generated_patch"] == patch_text
        assert payload["standard_answer"]["fail_to_pass"] == list(
            manifest.standard_answer.fail_to_pass
        )
        assert payload["condensation"]["applied"] is True
        assert payload["condensation"]["policy"] == "semantic-condense-v1"

    def test_condensation_is_deterministic(self) -> None:
        manifest, run, trajectory, patch_text, deterministic = self.oversized_inputs()
        budget = self.LIMIT - len(SEMANTIC_SYSTEM_PROMPT)

        first = condense_semantic_input(
            manifest, run, trajectory, patch_text, deterministic, budget
        )
        second = condense_semantic_input(
            manifest, run, trajectory, patch_text, deterministic, budget
        )

        assert first == second
        assert first[0] is not None

    def test_aggregation_collapses_only_all_passing_families(self) -> None:
        from hy3_workbench.contracts import DeterministicCheck
        from hy3_workbench.evidence_extractor import DeterministicEvidence

        checks = [
            DeterministicCheck(
                check_id=f"check-test-pass-to-pass-{index}",
                status="pass",
                summary=f"Declared pass-to-pass test t{index} passed.",
                evidence=[],
                hard_process_failure=False,
            )
            for index in range(1, 7)
        ] + [
            DeterministicCheck(
                check_id="check-test-fail-to-pass-1",
                status="pass",
                summary="Declared fail-to-pass test a passed.",
                evidence=[],
                hard_process_failure=False,
            ),
            DeterministicCheck(
                check_id="check-test-fail-to-pass-2",
                status="fail",
                summary="Declared fail-to-pass test b failed.",
                evidence=[],
                hard_process_failure=False,
            ),
        ]
        deterministic = DeterministicEvidence(
            status="ready", outcome_status="unresolved", checks=checks, exclusions=[]
        )
        manifest, run, _, patch_text, _ = load_review_inputs("valid")

        text, summary = condense_semantic_input(
            manifest, run, big_trajectory(1, 2_000), patch_text, deterministic, 200_000
        )

        assert text is not None and summary is not None
        payload = json.loads(text.split("\n\n", 1)[1])
        ids = [check["check_id"] for check in payload["deterministic_evidence"]["checks"]]
        assert "check-test-pass-to-pass-aggregate" in ids
        assert not any(
            item.startswith("check-test-pass-to-pass-") and item[-1].isdigit() for item in ids
        )
        assert "check-test-fail-to-pass-1" in ids
        assert "check-test-fail-to-pass-2" in ids
        aggregate = next(
            check
            for check in payload["deterministic_evidence"]["checks"]
            if check["check_id"] == "check-test-pass-to-pass-aggregate"
        )
        assert "6/6" in aggregate["summary"]
        assert "aggregated 6 all-passing per-test checks" in summary

    def test_impossible_budget_stays_an_honest_context_limit(self, reviewer_factory) -> None:
        judge = FakeJudge([])
        reviewer = reviewer_factory(judge, context_limit_chars=6_000)

        result = reviewer.review(*self.oversized_inputs())

        assert result.status == "context_limit"
        assert result.output is None
        assert judge.calls == []
        assert any("after bounded condensation" in reason for reason in result.failure_reasons)
