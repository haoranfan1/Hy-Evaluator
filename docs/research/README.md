# Research Record

## Status

**Research is complete.** The project now has one scenario, benchmark strategy, harness, evaluator design, web stack, differentiation order, and implementation roadmap.

Do not create Research 05 or 06. New uncertainty should be resolved through a bounded implementation spike and recorded in the relevant architecture or evaluator document.

## Completed sequence

| Order | Topic | Decision | Note | Status |
| --- | --- | --- | --- | --- |
| 01 | Domain and user scenario | Coding-agent process evaluation for agent developers | [01-domain-and-user.md](01-domain-and-user.md) | Complete |
| 02 | Benchmarks and industry practice | Reuse established tasks/traces; frame the product as a trace-to-evaluation workflow rather than a new benchmark | [Benchmark landscape](02-benchmark-landscape.md) · [Industry practice](02-industry-practice.md) | Complete |
| 03 | Exact Hy3 task and harness | Hy3 repairs SWE-bench Verified issues through mini-SWE-agent and Harbor; ATIF is the trace boundary | [03-hy3-feasibility.md](03-hy3-feasibility.md) | Complete |
| 04 | Evaluator, stack, differentiation, and scope synthesis | Thin hybrid evaluator, React/FastAPI workbench, human validation, required analysis, and optional regression card | [04-evaluator-and-implementation.md](04-evaluator-and-implementation.md) | Complete |

Research 04 absorbed the former evaluator-methods, differentiation, and scope-synthesis topics so the project would not remain in a repeated research loop.

## Final decisions

- **User:** coding-agent developer investigating Hy3 trajectories.
- **Task:** SWE-bench Verified issue repair.
- **Model:** Hy3.
- **Agent:** mini-SWE-agent v2.
- **Environment/verifier:** Harbor.
- **Trace:** Harbor-compatible ATIF v1.7.
- **Evaluator:** deterministic evidence plus rubric-bound Hy3 semantic review plus human adjudication.
- **Application:** local React/FastAPI web workbench.
- **MVP strength:** evidence-linked interactive process debugger with transparent evaluator lanes.
- **First optional differentiator:** human-approved regression card.
- **Non-goals:** new benchmark, multiple harnesses, autonomous self-evolution, universal ingestion, authentication, and cloud-scale deployment.

## Promoted specifications

Stable research conclusions now live in:

- [Architecture](../ARCHITECTURE.md)
- [Evaluator specification](../EVALUATOR_SPEC.md)
- [10-day build roadmap](../ROADMAP.md)
- [Next implementation action](../NEXT_STEPS.md)

The research notes remain as evidence and history. When a later implementation result contradicts a conclusion, update the promoted specification and record the observed evidence; do not rewrite the historical note as if the original uncertainty never existed.
