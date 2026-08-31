# Next Steps

## Status

**Current gate: Day 10 delivery freeze and demo.**

Completed prerequisites:

- Days 1–9 are complete: the validated Day 8 slice with blinded labels and adjudications,
  evaluator v2 with its recorded regression card (false positives 3/4 → 0/4, exact
  localization 0/4 → 3/4, detection preserved), judge-stability records (verdict and step
  unanimous across ten sessions), the submission report (`docs/REPORT.md`), and
  adjudication-aware analytics.

## Single next action

Freeze and package the delivery so a reviewer can verify everything quickly.

1. **Requirement audit.** Walk `docs/PROJECT_REQUIREMENTS.md` item by item and record where
   each requirement is satisfied (code, evidence file, report section); fix any gap found.
2. **Clean-environment verification.** From a fresh clone (no `.local`, no `.env`): backend
   install + full pytest, frontend install + tests + build, API start with the degraded
   (judge-unconfigured) health state, fixture import + deterministic evaluation. Record the
   exact commands and outcomes in `docs/DEVELOPMENT_SETUP.md` if anything differs.
3. **Security and hygiene audit.** Confirm no secrets, tokens, or absolute host paths in any
   committed file; confirm `.local/` isolation held; confirm exports and fixtures pass the
   existing secret-scan tests.
4. **README final pass.** Lead with what the project is, the headline validated findings,
   the quickstart, and the evidence map (report, results, slices, environment checks).
5. **Demo (≤2 minutes).** Script and record: open the run list → open the django-16899 run
   blinded → save a label → reveal the confirmed diagnosis at step 13 → show the
   scoped analytics with the false-positive chips → show the regression card numbers in the
   report. Store the recording path and the script in `docs/`.
6. **Delivery tag.** Final commit, tag, and push; verify the repository renders correctly on
   the host (README, report, images).

## Exit condition

A reviewer starting from the public repository can set up the project, run the offline test
suite, inspect the validated evidence, reproduce the documented pipeline on a compatible
host, and watch the demo in under two minutes.

## Explicitly deferred

- Widening the slice beyond Django and adding inter-rater agreement: future work recorded in
  the report's limitations.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
