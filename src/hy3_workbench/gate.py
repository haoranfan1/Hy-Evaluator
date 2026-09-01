"""Exit-code process gate over stored workbench evaluations.

Maps a stored run's process verdict to an exit code so CI or scripts can gate
on process validity, not just outcome. The gate only reads persisted records —
it never evaluates, so the verdict it reports is exactly the stored one.

Exit codes:
  0  process valid
  2  process invalid
  3  inconclusive (honest abstention — the caller decides whether to retry)
  4  the run exists but has no stored evaluation yet
  5  unknown run id
"""

import json
from collections.abc import Callable

from hy3_workbench.storage import RepositoryNotFoundError, WorkbenchRepository

EXIT_VALID = 0
EXIT_INVALID = 2
EXIT_INCONCLUSIVE = 3
EXIT_NOT_EVALUATED = 4
EXIT_UNKNOWN_RUN = 5

_STATUS_EXIT = {
    "valid": EXIT_VALID,
    "invalid": EXIT_INVALID,
    "inconclusive": EXIT_INCONCLUSIVE,
}


def run_gate(
    repository: WorkbenchRepository,
    run_id: str,
    *,
    json_output: bool = False,
    out: Callable[[str], None] = print,
) -> int:
    """Report the stored process verdict for ``run_id`` and return its exit code."""

    try:
        repository.get_run(run_id)
    except RepositoryNotFoundError:
        out(f"{run_id}: unknown run id")
        return EXIT_UNKNOWN_RUN
    stored = repository.get_evaluation_for_run(run_id)
    if stored is None:
        out(f"{run_id}: not evaluated yet")
        return EXIT_NOT_EVALUATED

    result = stored.result
    if json_output:
        out(
            json.dumps(
                {
                    "run_id": run_id,
                    "evaluator_version": result.evaluator_version,
                    "status": result.status,
                    "outcome_status": result.outcome_status,
                    "process_status": result.process_status,
                    "correct_result_invalid_process": result.correct_result_invalid_process,
                    "first_error": result.first_error.model_dump(mode="json"),
                    "exclusions": list(result.exclusions),
                    "exit_code": _STATUS_EXIT[result.process_status],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        line = (
            f"{run_id}: outcome {result.outcome_status} · process {result.process_status}"
            f" ({result.evaluator_version})"
        )
        if result.first_error.location == "located":
            line += f" · first error at step {result.first_error.step_id}"
        elif result.first_error.location == "unlocatable":
            line += " · first error unlocatable"
        if result.exclusions:
            line += f" · exclusions: {'; '.join(result.exclusions)}"
        out(line)
    return _STATUS_EXIT[result.process_status]
