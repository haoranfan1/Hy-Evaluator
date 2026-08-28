# Data

This directory will contain the tracked task manifest and development fixtures. The required metadata and review contracts are defined in [Evaluator Specification](../docs/EVALUATOR_SPEC.md).

Planned tracked content:

- `manifests/swebench_verified.jsonl`: selected task IDs, source/provenance, official difficulty, behavioral test contract, checker version, and selection reason.
- `fixtures/`: small synthetic or recorded ATIF examples used to test valid, invalid, recovered, inconclusive, and correct-result/invalid-process behavior.

Live Harbor jobs, raw API output, and mutable review state belong under the ignored `.local/` directory. Final sanitized evaluation evidence belongs under `results/` and is committed only after validation.

The official gold patch is provenance, not the only valid answer. It must never be exposed to Hy3 during task execution or initial semantic review.

Do not add private, licensed-without-permission, or credential-bearing data.
