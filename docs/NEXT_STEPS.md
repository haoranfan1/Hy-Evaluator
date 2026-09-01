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

### P1 — Evaluator v3: close the two measured gaps — **COMPLETE (Day 11, 2026-09-01)**

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

**Recorded exit evidence (2026-09-01):**

- **P1a (commit `3485e06`):** the deterministic lane resolves protected-path
  references written relative to a `cd`-established working directory (proper
  path-suffix joined to the tracked directory, accepted only on a component-aligned
  match; an unknown working directory is never guessed). django-15278 anchors its
  first error at step 27, matching the frozen human label; every other recorded
  bundle is byte-identical to v2 behavior. The evasion is reproduced as the tracked
  fixture `data/fixtures/invalid-relative-path/` with a step-4 oracle.
- **P1b:** bounded semantic-input condensation per the recorded design in
  [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) (`semantic-prompt-v2`,
  `semantic-condense-v1`): stage A aggregates all-passing per-test check families
  and drops indentation, stage B excerpts oversized observations around explicit
  elision markers, and the honest `context_limit` abstention remains the floor.
  Condensed reviews are marked in the new `EvaluationResult.semantic_condensation`
  field. On the real slice, stage A alone fits all four oversized inputs
  (197K–215K → 97K–154K chars); in-limit runs render byte-identically.
- **`results/regression/day11-regression-card-v3.json`** — all eight frozen slice
  runs re-evaluated in memory with the live judge under v3 against the frozen day8
  human labels: **false positives 0/4** (v1 3/4), **detection 4/4** preserved,
  **exact and within-one localization 4/4** (v1 0/4; v2 3/4), process verdicts
  agreeing with the human label on **all eight runs**, every run `completed` with
  zero exclusions — **semantic coverage 8/8** (previously 4/8 abstained). The day8
  15278 semantic contradiction is gone: the judge, now able to read the condensed
  trajectory, independently concurs with the deterministic `invalid`.
- **`results/judge-stability/day11-condensed-14017.json`** — five live repeats on
  the condensed 14017 input: verdict unanimous `valid` (the human label), first
  error unanimous `none`, advisory finding count the only variance (1–5), two
  attempts used the single schema-repair retry.

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

**Progress (2026-09-01):** the slice, guardrail config, and driver are committed
(`7078aaf`); the pruned day8 images were rebuilt through the recorded official
path and all three tasks re-passed the gold-patch oracle gate
(`data/environment-checks/arm64-oracle-guardrail-slice.json`); and all three
agent runs completed on the first trial, were imported with the new run-level
`slice_id` tag, and were evaluated with verdicts suppressed
(16801 → `django__django-16801__qEfUSGs__agent`, 16429 →
`django__django-16429__tUw7PUV__agent`, 16899 →
`django__django-16899__JbTxrSc__agent`; official verifier: all three passed).
Supporting infrastructure landed with tests: runs record their slice, scope
membership is per-run (an intervention slice matches only tagged runs; a legacy
slice excludes foreign-tagged runs — the frozen day8 scoped summary regenerates
byte-identically apart from the exporting-version stamps), and a task manifest is
shared across slices only when its substantive contract is identical.
**Waiting on the operator:** blinded initial labels for the three runs, entered
in the UI as `operator-blinded-guardrail` before any reveal; verdicts stay out of
this conversation until those labels are saved.

### P3 — Non-UI amplifiers — **COMPLETE (Day 11, 2026-09-01)**

1. Chinese summary (摘要) at the top of the README and report for Rhino-Bird reviewers,
   reusing the report's existing bilingual term mapping (定位准确率 / 误报率 / 结果对、过程有问题).
2. Optional: package the evaluator as a standalone process-gate CLI (nonzero exit on
   invalid process) with a short README section. Cut first if the schedule tightens.

**Exit condition:** the summary is faithful to the frozen numbers (no new claims), and
the CLI — if built — is covered by the offline test suite.

**Recorded exit evidence (2026-09-01):** 摘要（中文）sections added to the README and
REPORT, sourced only from the frozen committed evidence (day8 labels, day9/day11
regression cards, fifteen judge-stability sessions) with the report's bilingual terms.
In the same pass the English headline sections were brought up to v3 (the guardrail
line is deliberately absent until P2 closes), the report gained an "Evaluator v3
(Day 11)" continuation of §6, and the two v2-era limitations closed by v3 are marked
closed rather than deleted. The optional process gate landed as
`scripts/process_gate.py` over `hy3_workbench/gate.py`: read-only exit-code mapping
(0 valid · 2 invalid · 3 inconclusive · 4 not evaluated · 5 unknown), `--json` output,
covered by three offline tests (167 backend tests total).

### P4 — UI phase (deliberately last) — **COMPLETE except the guardrail comparison (Day 11, 2026-09-01)**

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

**Progress (2026-09-01) — review-experience subset pulled forward.** Operator feedback
during the guardrail labeling handoff ("nobody wants to read stack output and logs in
the frontend") pulled the readability half of this item ahead of the P2 labeling
session, since the labeling session is exactly where it pays off:

- Structured observations (`{"returncode": N, "output": …}`) render as an exit-code
  chip plus clean text instead of escaped JSON; long command and observation bodies
  collapse to a verbatim head/tail preview with an explicit hidden-line count and
  one-click expansion; nothing is summarized or lost.
- **Defect found and fixed:** Harbor's chat-completions conversion leaves
  `source_call_id` null on every real run's observation results, and the timeline's
  strict filter silently dropped all of them — the entire day8 labeling was done
  without a single command output visible in the timeline. Unmatched results now
  attach to their step.
- All-passing per-test verifier tables above ten rows collapse to a counted summary
  (failing rows always stay visible), mirroring the evaluator's own condensation
  stage; long prose summaries (v1-era protected-path walls) and the task-instruction
  step clamp with show-all toggles.
- 26 frontend tests (12 new), typecheck and build clean; verified visually against
  the real day8 django-16899 run via headless screenshots.

**Recorded exit evidence (2026-09-01, commits `5c8c460`, `112a3be`, `18907f4`,
`63a386a`, plus the theme commit):**

1. **Evidence views** — `/regressions` serves and renders the committed regression
   cards and judge-stability records read-only via `GET /api/regressions`
   (unparseable files are listed, never dropped; a committed-evidence test pins the
   real day9/day11 files). Each card is the v1-vs-v2/v3 before/after comparison:
   score families with change direction and per-run human/stored/re-evaluated lanes
   with agreement chips — an honest `inconclusive` is labeled *abstained*, not
   painted as a wrong verdict. The error-propagation overlay marks the selected
   finding's recorded `downstream_step_ids` on the timeline ("downstream of step N",
   clickable from the finding) — persisted evidence only, no inferred causality.
   The **baseline-vs-guardrail run comparison** is the one deferred piece: it joins
   the P2 comparison work once the blinded labels land, so no guardrail verdict has
   to be rendered before then.
2. **Efficiency analytics** — `/analytics` gains the official-provenance agent-effort
   table (median/min/max steps, median tool calls per difficulty × outcome) counted
   from the stored ATIF trajectories at summary time; unreadable trajectories are
   reported as missing, never interpolated. On the frozen day8 slice: medians
   45 → 44 → 57 steps across the three bands.
3. **Internationalization (required)** — dependency-free typed dictionary, EN
   default + 中文 with a persisted header toggle. Chrome only: statuses, categories,
   run ids, file paths, and frozen-record content stay untranslated; terms reuse the
   report's bilingual mapping (误报 / 定位 / 结果对、过程有问题). Covered by dedicated
   tests including a dictionary invariant (both languages, balanced placeholders).
4. **Theme toggle (optional, landed within its timebox)** — every remaining color
   literal moved into the `:root` variable palette (1:1, so light mode is
   pixel-identical), one `[data-theme="dark"]` override block, persisted 🌙/☀️
   toggle defaulting to the system preference.
- Gates at completion: 164 backend tests, 43 frontend tests, ruff clean,
  typecheck/build clean; light and dark, English and Chinese verified against the
  real day8 data via headless screenshots.

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
