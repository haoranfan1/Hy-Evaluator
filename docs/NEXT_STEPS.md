# Next Steps

## Status

**Current gate: Day 9 final analysis, report, case studies, and differentiation.**

Completed prerequisites:

- Days 1–8 are complete. The frozen day8-slice-v1 slice has recorded oracle checks, eight
  completed sequential runs, blinded initial labels, adjudications for every evaluator-flagged
  run, and slice-scoped analytics with explicit numerators, denominators, exclusions, and
  provenance (`results/summary-day8-slice-v1.json`, `results/metrics-day8-slice-v1.csv`).
- Headline validated findings: final-answer accuracy 8/8 with adjudicated process correctness
  4/8; confirmed-problem rate 4/7 vs evaluator false-positive rate 3/7 (all three false
  positives from the protected-path check firing on read-only references); confirmed-invalid
  localization 0/4 exact because the deterministic lane anchors at the first protected-path
  reference while humans anchor at the first modification.

## Single next action

Turn the recorded evidence into the submission-grade analysis, in this priority order:

1. **Evaluator fix with a regression card.** Rework `check_protected_paths` to separate
   modification evidence (patch-file intersection, write-command detection) from read-only
   references (which become an advisory note at most), and anchor the cited first error at
   the first modifying step. Bump the evaluator version, re-evaluate the slice under the new
   version WITHOUT touching the reviewed Day 8 evaluations (new evaluations require force and
   are refused once reviews exist — so record the re-run as a separate versioned comparison,
   not a replacement), and publish a before/after regression card: false positives 3 → ?,
   exact localization 0/4 → ?/4 against the same frozen human labels.
2. **Report and case studies** under `docs/` (or `results/report/`): the validation story
   (blinded protocol, metrics with provenance), plus three case studies — the graded-assertion
   rewrite (django-16899), the read-only false positive the semantic judge contradicted
   (django-15022), and the modify-then-revert with harness-awareness narration
   (django-14631). Include the difficulty inversion observation and the honest
   context-limit abstention (django-14017).
3. **Judge-stability table.** Re-run the semantic review N times on one fixture and one real
   run (bounded, recorded) and tabulate verdict/step stability across sessions, extending the
   existing recorded live checks.
4. **UI polish only after the above**: annotate analytics case links with their adjudication
   outcome (confirmed vs rejected) so the case list distinguishes them, and surface the
   scope selector.

## Exit condition

The gate is complete when the submission artifacts — README, report, case studies, the
regression card, and deterministic exports — tell one coherent story from task selection
through diagnosis to validated analysis, with every number carrying its provenance and the
full test suite passing.

## Explicitly deferred

- Delivery freeze, clean-environment reproduction run, and the ≤2-minute demo recording:
  Day 10.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
