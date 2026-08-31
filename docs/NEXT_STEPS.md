# Next Steps

## Status

**Day 1–10 engineering is complete and audited.** The validated Day 8 slice with blinded
labels and adjudications, evaluator v2 with its recorded regression card, judge-stability
records, the submission report ([REPORT.md](REPORT.md)), the delivery-freeze requirement
audit with the clean-environment verification record
([REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md)), and the demo script with its isolation
protocol ([DEMO.md](DEMO.md)) all exist.

## Single next action

The operator's final human review pass:

1. **Use the workbench end to end by hand** (run list, run detail with the evidence lanes,
   blinded review flow on the demo state copy, analytics with and without slice scope) and
   note every bug, confusing behavior, or broken rendering found. Findings become the next
   fix slice before submission.
2. **Record the ≤2-minute demo** following [DEMO.md](DEMO.md) — in particular the
   state-isolation protocol (serve the `.local/workbench-demo` copy while recording) and the
   post-recording check that the real store is untouched. Place the video at
   `docs/demo/` and link it from [DEMO.md](DEMO.md).
3. **Tag and submit** once the review pass is clean: create the annotated delivery tag,
   push it with the branch, verify the repository renders correctly on GitHub (README
   links, report tables, demo video), and submit the repository link through the
   Rhino-Bird channel.

To start the servers for the review:

```bash
./scripts/uv-local run hy3-workbench
```

```bash
cd frontend && npm run dev
```

## Maintenance notes

- The offline gate for any change stays the same:
  `./scripts/uv-local run pytest -q`, `ruff check .`, `ruff format --check .`,
  `cd frontend && npm test && npm run typecheck && npm run build`.
- Committed evidence under `results/` and `data/` is frozen validation output; regenerate
  it only alongside a new recorded evaluation round, never casually.
- The evaluator version, rubric version, and prompt version must be bumped together with
  any behavior change, with a new regression card against the frozen labels.

## Explicitly deferred (future work, recorded in the report's limitations)

- Widening the slice beyond the Django family and beyond eight tasks.
- A second independent blinded labeler and an inter-rater agreement measure.
- Closing the relative-path write-detection gap (the django-15278 localization miss).
- Raising semantic-lane coverage past the 180K-character context limit (4/8 slice runs
  abstained honestly).
