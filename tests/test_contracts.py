from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from hy3_workbench.contracts import (
    EvaluationResult,
    FirstError,
    HumanLabel,
    HumanReview,
    SemanticReviewOutput,
)


def test_evaluation_result_derives_correct_result_invalid_process() -> None:
    with pytest.raises(ValidationError, match="correct_result_invalid_process"):
        EvaluationResult(
            created_at=datetime.now(UTC),
            evaluation_id="evaluation-test",
            run_id="run-test",
            evaluator_version="test",
            rubric_version="test",
            semantic_prompt_version="test",
            status="completed",
            outcome_status="resolved",
            process_status="invalid",
            correct_result_invalid_process=False,
            first_error=FirstError(
                location="unlocatable",
                primary_category="reasoning",
            ),
            deterministic_checks=[],
            findings=[],
            exclusions=[],
        )


def test_human_review_is_an_immutable_append_only_version() -> None:
    review = HumanReview(
        created_at=datetime.now(UTC),
        review_id="review-test-v1",
        evaluation_id="evaluation-test",
        review_version=1,
        reviewer_alias="human-test",
        rubric_version="test",
        initial_label=HumanLabel(
            process_status="valid",
            first_error_location="none",
        ),
    )

    with pytest.raises(ValidationError, match="Instance is frozen"):
        review.notes = "mutated"  # type: ignore[misc]


def test_semantic_schema_rejects_invalid_without_a_material_finding() -> None:
    with pytest.raises(ValidationError, match="material finding"):
        SemanticReviewOutput(
            process_status="invalid",
            first_error=FirstError(
                location="unlocatable",
                primary_category="investigation",
            ),
            findings=[],
            summary="Evidence suggests an investigation failure.",
        )


def test_semantic_json_schema_is_strict() -> None:
    schema = SemanticReviewOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "semantic-review-v1"
