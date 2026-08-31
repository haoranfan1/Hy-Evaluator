# Next Steps

## Status

**Current gate: Day 8 frozen evaluation slice with blinded validation labels.**

Completed prerequisites:

- Days 1–7 are complete: the offline evaluator stack, the blinded review flow, analytics, and
  one real SWE-bench Verified run end to end on the source-built ARM64 path.
- The recorded oracle/environment check passed
  (`data/environment-checks/arm64-oracle-django__django-15851.json`), `HarborImporter` maps
  real trials into immutable bundles with strict rejection rules, and the first real run
  produced a correct-result/invalid-process diagnosis (protected test file rewritten at step
  12) confirmed by the live Hy3 judge.
- Reproduction tooling exists: `scripts/prepare_swebench_task.py` (pinned task copy with the
  ARM64 image swap and pre-grading patch dump) and `scripts/import_harbor_trial.py` (bundle
  build plus workflow import). Agent-phase credentials go through
  `OPENAI_API_KEY`/`OPENAI_BASE_URL` in the Harbor `--env-file`.

## Single next action

Freeze a small difficulty-covering SWE-bench Verified slice, run it sequentially with the
pinned configuration, and produce blinded validation labels for the required run classes.

```text
freeze the slice (recorded selection rule + seed, committed under data/)
    -> per task: build ARM64 instance image -> prepare pinned task copy
    -> harbor run (mini-swe-agent 2.4.6 + Hy3, sequential, -n 1)
    -> import -> evaluate (verdict stored, NOT viewed)
    -> blinded UI label BEFORE any verdict reveal -> reveal -> adjudicate flagged runs
    -> analytics + exports produce the required validation evidence
```

Required behavior:

1. The slice is frozen before any run starts: a committed selection record lists every
   instance id, its official difficulty label, the selection rule, and the environment
   constraint (source-buildable ARM64). Cover at least three official difficulty bands;
   staying within repositories that build reliably on aarch64 is acceptable and must be
   stated in the record.
2. Every task passes the same recorded oracle/environment gate as Day 7 before its agent run
   (gold patch resolves in the locally built image; record appended under
   `data/environment-checks/`).
3. Runs are sequential with the pinned agent, model, and judge configuration; failed trials
   (harness exceptions) are recorded and rerun at most once, with both trials kept.
4. Blinding is procedural and auditable: after import, evaluation runs without the operator
   viewing the verdict (no API reads of the evaluation before labeling); the initial label is
   entered through the blinded UI, then revealed and adjudicated. The Day 7 reveal review is
   already marked non-blinded and stays excluded from validation metrics.
5. Every gradeable incorrect run gets a blinded process/first-error label; every resolved run
   flagged process-invalid gets an adjudicated audit (confirmed problem vs false positive).
6. Analytics and exports must state the resulting localization accuracy, detection accuracy,
   and false-positive evidence with explicit numerators, denominators, exclusions, and
   provenance; thin slices report honest small-n numbers, never smoothed ones.

## Exit condition

The gate is complete when the frozen slice has recorded oracle checks, completed sequential
runs, imported evidence bundles, blinded initial labels for every gradeable incorrect run,
adjudicated audits for every resolved-and-flagged run, and the analytics/exports present the
required validation metrics from those records — with the full test suite still passing.

## Explicitly deferred

- Final metrics/report/case-study exports and differentiation features (judge-stability
  table, adversarial robustness case, regression card): Day 9.
- Delivery freeze, clean-environment run, and demo recording: Day 10.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
