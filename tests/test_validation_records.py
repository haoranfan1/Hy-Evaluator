import json
from pathlib import Path

from hy3_workbench.validation_records import load_validation_records

PROJECT_ROOT = Path(__file__).parents[1]


def minimal_card(recorded_at: str = "2026-09-01T00:00:00+00:00") -> dict:
    score = {"runs": [], "n": 0, "d": 4}
    return {
        "schema_version": "regression-card-v1",
        "recorded_at": recorded_at,
        "slice_id": "day8-slice-v1",
        "note": "test card",
        "stored_version": "workbench-evaluator-v1",
        "reevaluated_version": "workbench-evaluator-v3",
        "scores": {
            "stored": {"false_positives": score},
            "reevaluated": {"false_positives": score},
        },
        "runs": [
            {
                "run_id": "run-a",
                "task_id": "task-a",
                "human": {"process_status": "invalid", "first_error_step": 27},
                "stored": {
                    "evaluator_version": "workbench-evaluator-v1",
                    "status": "partial",
                    "process_status": "invalid",
                    "first_error_step": None,
                },
                # No semantic_condensation key: cards recorded before v3 lack it.
                "reevaluated": {
                    "evaluator_version": "workbench-evaluator-v3",
                    "status": "completed",
                    "process_status": "invalid",
                    "first_error_step": 27,
                    "exclusions": [],
                    "protected_check": {"status": "fail", "summary": "protected path modified"},
                },
            }
        ],
    }


class TestCommittedEvidence:
    """The frozen files under results/ must keep parsing as committed."""

    def test_all_committed_records_parse(self) -> None:
        records = load_validation_records(PROJECT_ROOT / "results", display_base="results")

        assert records.unreadable == []
        assert len(records.regression_cards) >= 2
        assert len(records.judge_stability) >= 3

    def test_cards_are_chronological_and_carry_the_v3_exit_numbers(self) -> None:
        records = load_validation_records(PROJECT_ROOT / "results", display_base="results")

        files = [entry.file for entry in records.regression_cards]
        day9 = files.index("results/regression/day9-regression-card.json")
        day11 = files.index("results/regression/day11-regression-card-v3.json")
        assert day9 < day11

        v3 = records.regression_cards[day11].card
        assert v3.reevaluated_version == "workbench-evaluator-v3"
        assert v3.scores["reevaluated"]["exact_localization"].n == 4
        assert v3.scores["reevaluated"]["exact_localization"].d == 4
        assert v3.scores["reevaluated"]["false_positives"].n == 0
        row_15278 = next(r for r in v3.runs if r.task_id == "django__django-15278")
        assert row_15278.reevaluated.first_error_step == row_15278.human.first_error_step == 27
        assert row_15278.stored.first_error_step is None

    def test_condensed_stability_record_is_present(self) -> None:
        records = load_validation_records(PROJECT_ROOT / "results", display_base="results")

        condensed = next(
            entry.record
            for entry in records.judge_stability
            if entry.file == "results/judge-stability/day11-condensed-14017.json"
        )
        assert condensed.judge.semantic_prompt_version == "semantic-prompt-v2"
        assert condensed.summary.verdict_unanimous is True
        assert len(condensed.attempts) == 5


class TestLoader:
    def test_missing_directories_yield_an_empty_library(self, tmp_path: Path) -> None:
        records = load_validation_records(tmp_path / "results", display_base="results")

        assert records.regression_cards == []
        assert records.judge_stability == []
        assert records.unreadable == []

    def test_unreadable_files_are_listed_not_dropped(self, tmp_path: Path) -> None:
        regression = tmp_path / "regression"
        regression.mkdir(parents=True)
        (regression / "good.json").write_text(json.dumps(minimal_card()), encoding="utf-8")
        (regression / "broken.json").write_text("{not json", encoding="utf-8")
        wrong = minimal_card()
        wrong["schema_version"] = "regression-card-v99"
        (regression / "wrong-schema.json").write_text(json.dumps(wrong), encoding="utf-8")

        records = load_validation_records(tmp_path, display_base="results")

        assert [entry.file for entry in records.regression_cards] == [
            "results/regression/good.json"
        ]
        reasons = {entry.file: entry.reason for entry in records.unreadable}
        assert "not valid JSON" in reasons["results/regression/broken.json"]
        assert "schema_version" in reasons["results/regression/wrong-schema.json"]

    def test_pre_v3_rows_default_the_condensation_field(self, tmp_path: Path) -> None:
        regression = tmp_path / "regression"
        regression.mkdir(parents=True)
        (regression / "card.json").write_text(json.dumps(minimal_card()), encoding="utf-8")

        records = load_validation_records(tmp_path, display_base="results")

        row = records.regression_cards[0].card.runs[0]
        assert row.reevaluated.semantic_condensation is None
        assert row.reevaluated.protected_check is not None
        assert row.reevaluated.protected_check.status == "fail"
