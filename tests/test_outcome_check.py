import json
import shutil
from pathlib import Path

import pytest

from hy3_workbench.outcome_check import (
    EXIT_INCONCLUSIVE,
    EXIT_RESOLVED,
    EXIT_UNREADABLE,
    EXIT_UNRESOLVED,
    BundleUnreadableError,
    check_bundle,
    main,
)

PROJECT_ROOT = Path(__file__).parents[1]
RUNS_ROOT = PROJECT_ROOT / "data" / "runs"
TAMPER_DIR = Path(".local/test-outcome-tamper")


@pytest.fixture(autouse=True)
def clean_state():
    shutil.rmtree(PROJECT_ROOT / TAMPER_DIR, ignore_errors=True)
    yield
    shutil.rmtree(PROJECT_ROOT / TAMPER_DIR, ignore_errors=True)


@pytest.mark.parametrize(
    ("name", "status", "exit_code"),
    [
        ("valid", "resolved", EXIT_RESOLVED),
        ("invalid-first-error", "unresolved", EXIT_UNRESOLVED),
        ("inconclusive-missing-evidence", "inconclusive", EXIT_INCONCLUSIVE),
    ],
)
def test_fixture_oracles_reproduce_their_declared_outcome(
    name: str, status: str, exit_code: int
) -> None:
    check = check_bundle(PROJECT_ROOT, f"data/fixtures/{name}")

    assert check.status == status
    assert check.exit_code == exit_code
    assert check.fail_to_pass, "every task declares at least one FAIL_TO_PASS test"
    if status == "inconclusive":
        assert any("malformed or incomplete" in reason for reason in check.reasons)
    else:
        assert check.reasons == []


@pytest.mark.parametrize("bundle", sorted(p.name for p in RUNS_ROOT.iterdir() if p.is_dir()))
def test_every_committed_real_run_is_resolved_by_the_official_contract(bundle: str) -> None:
    check = check_bundle(PROJECT_ROOT, f"data/runs/{bundle}")

    assert check.status == "resolved", check.reasons
    assert check.run_id == bundle
    assert check.fail_to_pass and all(t.status == "passed" for t in check.fail_to_pass)
    assert check.pass_to_pass and all(t.status == "passed" for t in check.pass_to_pass)


def test_a_tampered_verifier_report_is_inconclusive_not_resolved() -> None:
    tamper = PROJECT_ROOT / TAMPER_DIR
    tamper.mkdir(parents=True)
    fixture = PROJECT_ROOT / "data" / "fixtures" / "valid"
    shutil.copyfile(fixture / "manifest.json", tamper / "manifest.json")
    run = json.loads((fixture / "run.json").read_text(encoding="utf-8"))
    run["verifier"]["report"]["sha256"] = "0" * 64
    (tamper / "run.json").write_text(json.dumps(run), encoding="utf-8")

    check = check_bundle(PROJECT_ROOT, TAMPER_DIR.as_posix())

    assert check.status == "inconclusive"
    assert any("identity verification" in reason for reason in check.reasons)
    assert all(t.status == "missing" for t in check.fail_to_pass)


def test_unreadable_bundle_is_reported_not_guessed() -> None:
    with pytest.raises(BundleUnreadableError):
        check_bundle(PROJECT_ROOT, "data/fixtures/does-not-exist")


def test_cli_reports_every_bundle_and_returns_the_worst_exit_code(monkeypatch) -> None:
    monkeypatch.chdir(PROJECT_ROOT)
    lines: list[str] = []

    code = main(
        ["data/fixtures/valid", "data/fixtures/invalid-first-error", "data/fixtures/missing"],
        out=lines.append,
    )

    assert code == EXIT_UNREADABLE
    assert lines[0].startswith("run-fixture-valid: resolved  FAIL_TO_PASS ")
    assert lines[1].startswith("run-fixture-invalid-first-error: unresolved")
    assert lines[2].startswith("data/fixtures/missing: unreadable")


def test_cli_all_mode_covers_the_committed_runs_as_json(monkeypatch) -> None:
    monkeypatch.chdir(PROJECT_ROOT)
    lines: list[str] = []

    code = main(["--all", "data/runs", "--json"], out=lines.append)

    payload = json.loads("".join(lines))
    assert code == EXIT_RESOLVED
    assert len(payload) == len([p for p in RUNS_ROOT.iterdir() if p.is_dir()])
    assert {entry["status"] for entry in payload} == {"resolved"}
    assert all(entry["exit_code"] == EXIT_RESOLVED for entry in payload)
