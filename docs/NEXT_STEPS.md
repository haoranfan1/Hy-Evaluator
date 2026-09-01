# Next Steps

## Status

**Day 1–10 engineering is complete and audited** ([REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md)).
The delivery freeze holds: every acceptance item is satisfied except the demo recording,
which is deliberately deferred until the differentiation work below is finished.

This phase (Day 11+) works the prioritized backlog below **strictly in order**. An item
starts only after the previous item's exit condition is recorded here. The backlog was
selected from the parked differentiation ideas in the research docs
([01 §Differentiation options](research/01-domain-and-user.md),
[02 §Potential differentiation](research/02-industry-practice.md),
[04 §Differentiation ranking](research/04-evaluator-and-implementation.md)) plus the
measured gaps in [REPORT §8](REPORT.md). All UI work is consolidated into the last
development item (P4) so the evidence-producing work lands first and any schedule
trimming happens in presentation, never in validation.

## Standing rules for every backlog item

- Frozen evidence under `results/` and `data/` is never regenerated or edited. New
  evidence lands alongside it under new versioned names (new slice ids, new card files).
- Any evaluator behavior change bumps the evaluator, rubric, and prompt versions
  together and must produce a new regression card against the frozen day8 human labels
  before the item is called done.
- The offline gate for any change is unchanged:
  `./scripts/uv-local run pytest -q`, `ruff check .`, `ruff format --check .`,
  `cd frontend && npm test && npm run typecheck && npm run build`.
- Any new recorded runs follow the day8-slice-v1 protocol: frozen slice file before any
  run, blinded initial labels before any reveal, adjudication versions append-only.

## Prioritized backlog

### P1 — Evaluator v3: close the two measured gaps

Fix the two failure modes that [REPORT §8](REPORT.md) already quantifies, then prove the
fix the same way v2 was proven.

1. **P1a — Relative-path write detection.** Command-level write detection misses
   relative-path edits (the django-15278 localization miss, where v2 honestly reports
   unlocatable instead of guessing). First reproduce the miss as a fixture, then extend
   the deterministic lane to resolve edit targets against the recorded working state so
   the first modifying write is locatable.
2. **P1b — Semantic coverage past the context limit.** 4/8 slice trajectories exceeded
   the 180K-character judge limit and abstained honestly. Design and implement a bounded
   condensation path for oversized trajectories (design recorded before code): the judge
   must only ever see faithful excerpts of real artifacts, never summaries that could
   smuggle in fabricated content, and condensed reviews are marked as such in the result.

**Exit condition:** a recorded `workbench-evaluator-v3` regression card against the
frozen day8 human labels — target exact localization 4/4 with detection 4/4 and false
positives 0/4 preserved — plus semantic verdicts on all eight slice runs (or an honest
documented reason where condensation cannot help), and judge-stability repeats recorded
for at least one previously-abstaining run. Honest shortfalls are reported, not hidden.

**Progress — P1a landed.** The deterministic lane now resolves protected-path
references written relative to a `cd`-established working directory (proper
path-suffix joined to the tracked directory, accepted only on a component-aligned
match; an unknown working directory is never guessed). Verified against the real
bundles in memory: django-15278 now cites writes at steps 27 and 29 and anchors the
first error at step 27, matching the frozen human label; all four confirmed-invalid
runs anchor at their human-labeled steps (27/21/28/13); the three adjudicated-valid
runs, the modify-then-revert warning (14631 step 37), and the day7 integration run
are byte-identical to v2 behavior. The evasion is reproduced as the tracked fixture
`data/fixtures/invalid-relative-path/` with a step-4 oracle, and
`EVALUATOR_VERSION` is bumped to `workbench-evaluator-v3` (rubric/prompt bumps and
the recorded regression card follow with P1b).

### P2 — Guardrail intervention experiment (completing trace-to-regression)

The headline finding: on easy tasks the agent edited graded test files (0/3
process-valid). Rerun those three tasks with **one documented guardrail** added to the
agent configuration (an explicit instruction never to modify test files), as a new
frozen mini-slice evaluated under v3 with the same blinded labeling and adjudication
protocol. This completes the trace-to-regression vision from
[research 02](research/02-industry-practice.md): diagnosis → intervention → measured
re-verification, entirely through Hy3.

**Exit condition:** committed slice file, run records, blinded labels, and a
before/after comparison (day8 baseline vs guardrail) with explicit numerators and
denominators. The result — improved, unchanged, or worsened — is reported honestly
either way.

### P3 — Non-UI amplifiers

1. Chinese summary (摘要) at the top of the README and report for Rhino-Bird reviewers,
   reusing the report's existing bilingual term mapping (定位准确率 / 误报率 / 结果对、过程有问题).
2. Optional: package the evaluator as a standalone process-gate CLI (nonzero exit on
   invalid process) with a short README section. Cut first if the schedule tightens.

**Exit condition:** the summary is faithful to the frozen numbers (no new claims), and
the CLI — if built — is covered by the offline test suite.

### P4 — UI phase (deliberately last)

All frontend work in one item, ordered internally by value:

1. **Evidence views** — the `/regressions` route (interactive regression cards and
   judge-stability records, planned in research 04 but never built), the before/after
   comparison view (v1 vs v2/v3 evaluation of the same run; baseline vs guardrail runs
   of the same task), and the error-propagation overlay on the run timeline (each
   downstream link backed by cited evidence — no invented causality).
2. **Efficiency analytics** on `/analytics` from existing ATIF data: steps and tool
   calls per outcome and difficulty band, feeding the capability-boundary analysis.
3. **Internationalization (required):** two UI languages — English (default) and
   Chinese — with a visible toggle and persisted choice. Scope is UI chrome (labels,
   headings, filters, empty states, banners). Evidence content is data, not chrome:
   trajectory text, commands, judge findings, and operator notes stay in their original
   language, untranslated.
4. **Theme toggle (optional):** light/dark switch. Verified cheap: components contain
   zero color literals or Tailwind color utilities; every color already flows through
   the variable palette in `styles.css`, so this is a variable override block plus a
   toggle. Timeboxed to half a day — skipped if it exceeds that.

**Exit condition:** everything renders from persisted/committed records only, frontend
tests cover each addition (including a language-toggle test), and no evaluator behavior
changed. Internal cut order if time runs short: theme toggle → propagation overlay →
comparison view. The `/regressions` route and i18n are keepers.

### P5 — Wrap-up and submission (the former single next action)

1. Operator's end-to-end hand review of the workbench, now including the new views and
   both languages; findings become the last fix slice.
2. Update [REPORT.md](REPORT.md), [README](../README.md), and
   [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md) so headline numbers include v3 and
   the guardrail result.
3. Record the ≤2-minute demo per [DEMO.md](DEMO.md) (state-isolation protocol; the new
   views join the scene script only if they strengthen it within the time budget).
4. Clean-clone re-verification, annotated delivery tag, push, GitHub render check,
   submission through the Rhino-Bird channel.

## Explicitly skipped (recorded decisions)

- **Second blinded labeler / inter-rater agreement** — requires a second human;
  remains in the report's limitations.
- **Counterfactual replay** — effort out of proportion to the remaining time.
- **Codex-trajectory import comparison** — dilutes Hy3 centrality and needs Codex
  access; stays parked per research 03.
- **DSH adapter, security/prompt-injection dimension** — parked upstream / out of
  scope, unchanged.
- **Wider slice v2 beyond Django** — only if time remains after P1–P4; P2 already
  contributes new recorded runs.

## Maintenance notes

- Committed evidence under `results/` and `data/` is frozen validation output;
  regenerate it only alongside a new recorded evaluation round, never casually.
- The evaluator version, rubric version, and prompt version must be bumped together
  with any behavior change, with a new regression card against the frozen labels.
