# Hy3 Process Evaluation Project

> An individual project for the Rhino-Bird open-source practical task. This repository is not an official Tencent release.

This repository will implement Project 2 as a web-based workbench for evaluating Hy3 coding-agent trajectories. Hy3 repairs SWE-bench Verified issues through mini-SWE-agent and Harbor; the application then combines executable evidence, semantic trace review, and human validation to diagnose the process and analyze capability boundaries.

## Current status

- Project requirements have been extracted from the instruction PDF.
- The four-part research phase is complete.
- The SWE-bench/mini-SWE-agent/Harbor/ATIF direction is fixed.
- The hybrid evaluator, metadata contracts, React/FastAPI architecture, web workflow, and ten-day implementation roadmap are specified.
- The first implementation action is an offline ATIF-to-evidence-debugger vertical slice.
- No application code has been implemented yet.

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

Setup and run commands will be added with the first vertical slice. Do not add real credentials to this repository; Hy3 credentials must be supplied through environment variables or an ignored local configuration file.
