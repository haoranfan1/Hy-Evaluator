import json
import shutil
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from test_semantic_reviewer import FakeJudge, invalid_response, valid_response

from hy3_workbench.api import app, get_judge_provider, get_settings
from hy3_workbench.config import Settings
from hy3_workbench.workflow import JudgeUnavailableError

PROJECT_ROOT = Path(__file__).parents[1]
DATA_DIR = Path(".local/test-day4-api")

INITIAL_LABEL = {
    "process_status": "invalid",
    "first_error_location": "located",
    "first_error_step_id": 3,
    "primary_category": "task_interpretation",
    "notes": "Zero was grouped with None against the explicit requirement.",
}


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        workbench_data_dir=DATA_DIR / "wb",
        results_dir=DATA_DIR / "results",
    )


@pytest.fixture()
def judge() -> FakeJudge:
    return FakeJudge([])


@pytest.fixture()
def client(judge: FakeJudge):
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    app.dependency_overrides[get_settings] = make_settings
    app.dependency_overrides[get_judge_provider] = lambda: lambda: judge
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


async def test_full_offline_workflow_via_the_api(client: AsyncClient, judge: FakeJudge) -> None:
    judge.contents = [valid_response(), invalid_response()]

    async with client:
        for name in ("valid", "invalid-first-error", "inconclusive-missing-evidence"):
            imported = await client.post(
                "/api/runs/import", json={"bundle_dir": f"data/fixtures/{name}"}
            )
            assert imported.status_code == 201, imported.text

        tasks = (await client.get("/api/tasks")).json()
        assert len(tasks["tasks"]) == 3

        for run_id, expected_process in (
            ("run-fixture-valid", "valid"),
            ("run-fixture-invalid-first-error", "invalid"),
            ("run-fixture-inconclusive-missing-evidence", "inconclusive"),
        ):
            evaluated = await client.post(f"/api/runs/{run_id}/evaluate", json={})
            assert evaluated.status_code == 200, evaluated.text
            body = evaluated.json()
            assert body["evaluated"] is True
            assert body["evaluation"]["process_status"] == expected_process

        assert judge.contents == []  # The inconclusive run never reached the judge.

        runs = (await client.get("/api/runs")).json()["runs"]
        by_id = {entry["run_id"]: entry for entry in runs}
        assert by_id["run-fixture-valid"]["outcome_status"] == "resolved"
        assert by_id["run-fixture-invalid-first-error"]["process_status"] == "invalid"
        assert by_id["run-fixture-invalid-first-error"]["difficulty"] == "easy"
        assert by_id["run-fixture-invalid-first-error"]["first_error"]["step_id"] == 3

        detail = (await client.get("/api/runs/run-fixture-invalid-first-error")).json()
        assert detail["task"]["task_id"] == "fixture-invalid-first-error"
        assert detail["evaluation"]["first_error"]["step_id"] == 3
        assert detail["artifacts"]["patch"].startswith("diff --git")
        assert "FAIL_TO_PASS" in detail["artifacts"]["test_output"]

        trajectory = (
            await client.get("/api/runs/run-fixture-invalid-first-error/trajectory")
        ).json()
        assert trajectory["schema_version"] == "ATIF-v1.7"
        assert len(trajectory["steps"]) == 5

        evaluation_id = detail["evaluation"]["evaluation_id"]
        initial = await client.post(
            f"/api/evaluations/{evaluation_id}/initial-review",
            json={
                "reviewer_alias": "reviewer-1",
                "rubric_version": "process-rubric-v1",
                "initial_label": INITIAL_LABEL,
            },
        )
        assert initial.status_code == 201, initial.text

        adjudication = await client.post(
            f"/api/evaluations/{evaluation_id}/adjudications",
            json={
                "reviewer_alias": "reviewer-1",
                "rubric_version": "process-rubric-v1",
                "adjudication": "accept",
                "final_label": INITIAL_LABEL,
            },
        )
        assert adjudication.status_code == 201, adjudication.text
        assert adjudication.json()["review_version"] == 2

        stored = (await client.get(f"/api/evaluations/{evaluation_id}")).json()
        assert [review["review_version"] for review in stored["reviews"]] == [1, 2]

        analytics = (await client.get("/api/analytics/summary")).json()
        assert analytics["run_count"] == 3
        assert analytics["adjudicated_count"] == 1
        assert analytics["configuration"]["scope"] == "all"
        assert any(
            entry["metric_id"] == "exact_first_error_localization_accuracy"
            and entry["numerator"] == 1
            for entry in analytics["metrics"]
        )

        efficiency = analytics["efficiency"]
        assert sum(row["run_count"] for row in efficiency) == 3
        # The API passes the project root, so every stored trajectory is counted.
        assert all(row["runs_with_trajectory"] == row["run_count"] for row in efficiency)
        assert all(row["provenance"] == "official" for row in efficiency)

        slices = (await client.get("/api/analytics/slices")).json()["slices"]
        assert "day8-slice-v1" in slices

        scoped = await client.get("/api/analytics/summary", params={"scope": "day8-slice-v1"})
        assert scoped.status_code == 200, scoped.text
        scoped_body = scoped.json()
        assert scoped_body["configuration"]["scope"] == "day8-slice-v1"
        assert scoped_body["run_count"] == 0  # fixture runs are outside the frozen slice
        assert scoped_body["configuration"]["scope_out_of_scope_runs"] == 3
        unknown = await client.get("/api/analytics/summary", params={"scope": "no-such-slice"})
        assert unknown.status_code == 404

        exported = (await client.post("/api/exports")).json()["files"]
        assert f"{DATA_DIR.as_posix()}/results/human_reviews.jsonl" in exported
        assert f"{DATA_DIR.as_posix()}/results/summary.json" in exported
        assert f"{DATA_DIR.as_posix()}/results/metrics.csv" in exported
        assert f"{DATA_DIR.as_posix()}/results/summary-day8-slice-v1.json" in exported
        assert f"{DATA_DIR.as_posix()}/results/metrics-day8-slice-v1.csv" in exported
        assert f"{DATA_DIR.as_posix()}/results/summary-guardrail-slice-v1.json" in exported
        first_bytes = [(PROJECT_ROOT / name).read_bytes() for name in sorted(exported)]
        again = (await client.post("/api/exports")).json()["files"]
        second_bytes = [(PROJECT_ROOT / name).read_bytes() for name in sorted(again)]
        assert first_bytes == second_bytes
        # per-run files plus reviews, then summary/metrics for "all" and per committed slice
        committed_slices = len(list((PROJECT_ROOT / "data/evaluation-slices").glob("*.json")))
        assert len(exported) == 3 + 1 + 2 * (1 + committed_slices)


async def test_regression_records_are_served_from_the_results_dir(
    client: AsyncClient, judge: FakeJudge
) -> None:
    from test_validation_records import minimal_card

    regression_dir = PROJECT_ROOT / DATA_DIR / "results" / "regression"
    regression_dir.mkdir(parents=True)
    (regression_dir / "card.json").write_text(json.dumps(minimal_card()), encoding="utf-8")

    async with client:
        response = await client.get("/api/regressions")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["unreadable"] == []
    assert body["judge_stability"] == []
    [entry] = body["regression_cards"]
    assert entry["file"] == f"{DATA_DIR.as_posix()}/results/regression/card.json"
    assert entry["card"]["reevaluated_version"] == "workbench-evaluator-v3"
    assert entry["card"]["runs"][0]["reevaluated"]["semantic_condensation"] is None


async def test_evaluate_is_idempotent_and_force_respects_reviews(
    client: AsyncClient, judge: FakeJudge
) -> None:
    judge.contents = [invalid_response(), invalid_response()]

    async with client:
        await client.post(
            "/api/runs/import", json={"bundle_dir": "data/fixtures/invalid-first-error"}
        )
        first = await client.post("/api/runs/run-fixture-invalid-first-error/evaluate", json={})
        repeat = await client.post("/api/runs/run-fixture-invalid-first-error/evaluate", json={})
        assert repeat.json()["evaluated"] is False
        assert len(judge.calls) == 1

        forced = await client.post(
            "/api/runs/run-fixture-invalid-first-error/evaluate", json={"force": True}
        )
        assert forced.json()["evaluated"] is True
        assert len(judge.calls) == 2

        evaluation_id = first.json()["evaluation"]["evaluation_id"]
        await client.post(
            f"/api/evaluations/{evaluation_id}/initial-review",
            json={
                "reviewer_alias": "reviewer-1",
                "rubric_version": "process-rubric-v1",
                "initial_label": INITIAL_LABEL,
            },
        )
        blocked = await client.post(
            "/api/runs/run-fixture-invalid-first-error/evaluate", json={"force": True}
        )
        assert blocked.status_code == 409
        assert "human reviews" in blocked.json()["detail"]


async def test_error_paths_are_explicit(client: AsyncClient, judge: FakeJudge) -> None:
    async with client:
        for bundle_dir in ("/etc/passwd", "../outside", "data/fixtures/missing"):
            response = await client.post("/api/runs/import", json={"bundle_dir": bundle_dir})
            assert response.status_code == 400, bundle_dir

        duplicate_target = await client.post(
            "/api/runs/import", json={"bundle_dir": "data/fixtures/valid"}
        )
        assert duplicate_target.status_code == 201
        duplicate = await client.post(
            "/api/runs/import", json={"bundle_dir": "data/fixtures/valid"}
        )
        assert duplicate.status_code == 409

        missing_run = await client.post("/api/runs/unknown-run/evaluate", json={})
        assert missing_run.status_code == 404

        missing_evaluation = await client.get("/api/evaluations/unknown-evaluation")
        assert missing_evaluation.status_code == 404

        premature = await client.post(
            "/api/evaluations/unknown-evaluation/adjudications",
            json={
                "reviewer_alias": "reviewer-1",
                "rubric_version": "process-rubric-v1",
                "adjudication": "accept",
                "final_label": INITIAL_LABEL,
            },
        )
        assert premature.status_code == 409


async def test_unconfigured_judge_returns_503(judge: FakeJudge) -> None:
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    app.dependency_overrides[get_settings] = make_settings

    def unavailable_provider():
        def provide():
            raise JudgeUnavailableError("Hy3 is not configured for this test.")

        return provide

    app.dependency_overrides[get_judge_provider] = unavailable_provider
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/runs/import", json={"bundle_dir": "data/fixtures/valid"})
            response = await client.post("/api/runs/run-fixture-valid/evaluate", json={})
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


async def test_health_reports_database_component() -> None:
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    app.dependency_overrides[get_settings] = make_settings
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health")
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)

    assert response.status_code == 200
    payload = response.json()
    assert payload["components"]["database"]["status"] == "ready"
    assert payload["components"]["hy3"]["status"] == "not_configured"
    assert payload["status"] == "degraded"
