# Documentation

This directory is the source of truth for project scope, design, planning, and progress.

## Documents

| Document | Purpose | Update when |
| --- | --- | --- |
| [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md) | Extracted Project 2 requirements and acceptance checklist | The source instructions are clarified or the interpretation changes |
| [ROADMAP.md](ROADMAP.md) | Ten-day implementation sequence and cut order | A build phase starts, finishes, or changes scope |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Approved components, stack, APIs, data flow, and failure handling | Implementation evidence changes a technical decision |
| [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md) | Evaluator semantics, taxonomy, schemas, merge policy, and metrics | Validation evidence changes evaluator behavior |
| [NEXT_STEPS.md](NEXT_STEPS.md) | The single next approved action | The current action is completed or changed |
| [research/](research/README.md) | Completed source-backed research record | A later implementation result contradicts a research conclusion |

## Documentation practice

- Keep requirements separate from proposed implementation choices.
- Update the roadmap at milestone boundaries.
- Keep `NEXT_STEPS.md` short and actionable.
- Keep completed research separate from execution-dependent implementation spikes.
- Link code and evaluation results from the relevant design document once they exist.
