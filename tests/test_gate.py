import shutil
from pathlib import Path

import pytest
from test_semantic_reviewer import FakeJudge, invalid_response, valid_response
from test_storage import make_service

from hy3_workbench.gate import (
    EXIT_INCONCLUSIVE,
    EXIT_INVALID,
    EXIT_NOT_EVALUATED,
    EXIT_UNKNOWN_RUN,
    EXIT_VALID,
    run_gate,
)

PROJECT_ROOT = Path(__file__).parents[1]
DATA_DIR = Path(".local/test-day4-storage")


@pytest.fixture(autouse=True)
def clean_state():
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)
    yield
    shutil.rmtree(PROJECT_ROOT / DATA_DIR, ignore_errors=True)


def test_gate_maps_each_stored_verdict_to_its_exit_code() -> None:
    service = make_service(FakeJudge([valid_response(), invalid_response()]))
    for name in ("valid", "invalid-first-error", "inconclusive-missing-evidence"):
        service.import_bundle(f"data/fixtures/{name}")
        service.evaluate_run(f"run-fixture-{name}")

    lines: list[str] = []
    assert run_gate(service.repository, "run-fixture-valid", out=lines.append) == EXIT_VALID
    assert (
        run_gate(service.repository, "run-fixture-invalid-first-error", out=lines.append)
        == EXIT_INVALID
    )
    assert (
        run_gate(service.repository, "run-fixture-inconclusive-missing-evidence", out=lines.append)
        == EXIT_INCONCLUSIVE
    )
    assert "process valid" in lines[0]
    assert "process invalid" in lines[1]
    assert "first error at step 3" in lines[1]
    assert "exclusions" in lines[2]


def test_gate_never_invents_a_verdict() -> None:
    service = make_service(FakeJudge([]))
    service.import_bundle("data/fixtures/valid")

    lines: list[str] = []
    assert run_gate(service.repository, "run-fixture-valid", out=lines.append) == (
        EXIT_NOT_EVALUATED
    )
    assert run_gate(service.repository, "no-such-run", out=lines.append) == EXIT_UNKNOWN_RUN
    assert lines == [
        "run-fixture-valid: not evaluated yet",
        "no-such-run: unknown run id",
    ]


def test_gate_json_output_is_machine_readable() -> None:
    import json

    service = make_service(FakeJudge([invalid_response()]))
    service.import_bundle("data/fixtures/invalid-first-error")
    service.evaluate_run("run-fixture-invalid-first-error")

    lines: list[str] = []
    code = run_gate(
        service.repository,
        "run-fixture-invalid-first-error",
        json_output=True,
        out=lines.append,
    )

    payload = json.loads("".join(lines))
    assert code == EXIT_INVALID
    assert payload["process_status"] == "invalid"
    assert payload["first_error"]["step_id"] == 3
    assert payload["exit_code"] == EXIT_INVALID
