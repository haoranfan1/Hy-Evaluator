# Hy3 Process Evaluation Project

> An individual project for the Rhino-Bird open-source practical task. This repository is not an official Tencent release.

This repository will implement Project 2 as a web-based workbench for evaluating Hy3 coding-agent trajectories. Hy3 repairs SWE-bench Verified issues through mini-SWE-agent and Harbor; the application then combines executable evidence, semantic trace review, and human validation to diagnose the process and analyze capability boundaries.

## Current status

- Project requirements have been extracted from the instruction PDF.
- The four-part research phase is complete.
- The SWE-bench/mini-SWE-agent/Harbor/ATIF direction is fixed.
- The hybrid evaluator, metadata contracts, React/FastAPI architecture, web workflow, and ten-day implementation roadmap are specified.
- The repository-local Python 3.12 environment, dependency lock, FastAPI health endpoint, explicit
  Hy3 handshake client, React/Vite shell, configuration examples, and initial tests are scaffolded.
- The Day 1 contracts, verified fixture bundles, and offline evidence gate are complete.
- The Day 2 deterministic lane is complete: typed, evidence-linked checks for identity, ATIF
  structure, per-test verifier results, outcome policy, patch scope, protected paths, command
  failures, and final-claim comparison, produced without any model call.
- The Day 3 semantic evaluator and merge policy are complete: a versioned rubric, the fixed Hy3
  judge with evidence-reference validation and one schema-repair retry, honest semantic failure,
  and merged contract-valid evaluation results. Two bounded live Hy3 reviews reproduced the
  fixture oracles exactly.
- The Day 4 persistence and API workflow are complete: SQLite storage with atomic imports and
  append-only review versions, plus restart-safe FastAPI endpoints for import,
  digest-idempotent evaluation, reads, blinded reviews, adjudications, and byte-stable exports.
- The Day 5 evidence-debugger UI is complete: a filterable run list and a run detail page with
  the step timeline, marked first error, evidence lanes with two-way cross-highlighting, patch
  and verifier views, and honest inconclusive rendering — verified live against the API with a
  real Hy3 judge.
- The Day 6 human-review workflow and analytics are complete: blinded initial labels before any
  verdict reveal, append-only adjudication versions, and provenance-aware aggregate metrics
  with explicit numerators, denominators, exclusions, and a seeded bootstrap decline test,
  rendered on the analytics page and exported deterministically.
- The Day 7 real Hy3/Harbor/SWE-bench integration is complete: a recorded oracle/environment
  check passed on a source-built ARM64 image, one real SWE-bench Verified task ran end to end
  through Harbor + mini-SWE-agent + Hy3, and the imported ATIF v1.7 run produced the first
  real correct-result/invalid-process diagnosis (a rewritten protected test file, localized
  to its step and confirmed by the live Hy3 judge) in the debugger.
- The Day 8 frozen difficulty-covering evaluation slice with blinded validation labels is the
  active milestone; it is not complete yet.

See [Next Steps](docs/NEXT_STEPS.md) for the first implementation slice.

## Repository layout

```text
.
├── data/                         # Versioned benchmark data and data documentation
├── docs/                         # Requirements, roadmap, design, decisions, and next steps
├── scripts/                      # Reproducible experiment and maintenance entry points
├── src/                          # Application and evaluator source code
├── tests/                        # Automated tests
├── .gitignore
├── README.md
└── 犀牛鸟开源-实战任务-混元大语言模型项目.pdf  # Original instruction file
```

## Documentation

- [Documentation index](docs/README.md)
- [Project requirements](docs/PROJECT_REQUIREMENTS.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Evaluator specification](docs/EVALUATOR_SPEC.md)
- [Next steps](docs/NEXT_STEPS.md)
- [Research workspace](docs/research/README.md)

## Development

The application foundation uses a repository-local Python 3.12 environment managed by `uv` and a
React/Vite frontend. See [Development setup](docs/DEVELOPMENT_SETUP.md) for the isolation policy,
configuration, local commands, Docker gate, and Google Cloud fallback.

Do not add real credentials to this repository. Copy `.env.example` to the ignored `.env` file and
set Hy3 credentials locally.
