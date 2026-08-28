# Next Steps

## Status

**Research is complete. The isolated application foundation is implemented.**

Completed foundation work:

- Repository-local Python 3.12 through `scripts/uv-local`.
- Locked Python dependencies, including Harbor 0.22.0 and mini-SWE-agent 2.4.6.
- MIT license, `.env.example`, runtime pins, and development documentation.
- FastAPI health endpoint that never calls Hy3 implicitly.
- Explicit single-request Hy3 handshake command with nested reasoning configuration.
- React/Vite application shell and initial backend/frontend tests.

Current setup gates:

- Configure the ignored `.env` with the real Hy3 endpoint, model, and key, then run
  `./scripts/check-hy3`.
- Generate `frontend/package-lock.json` after npm registry connectivity is available; no frontend
  packages or partial lockfile were retained from the failed network attempts.

## Single next action

Build the first offline vertical slice:

```text
recorded ATIF v1.7 fixture
    -> typed validation and immutable artifact registration
    -> deterministic evidence extraction
    -> Hy3 semantic review with validated evidence references
    -> merged evaluator result
    -> FastAPI read endpoint
    -> React run-detail page linking findings to trajectory steps
```

Before writing the complete UI, complete the bounded Hy3 handshake needed by this slice:

- Confirm `HY3_BASE_URL`, `HY3_MODEL`, and authentication.
- Confirm Chat Completions and nested `chat_template_kwargs.reasoning_effort=high`.
- Test one structured evaluator response and record unsupported fields honestly.

## Exit condition

The slice is complete when one invalid fixture and one valid fixture can be inspected in the browser, every evaluator finding cites real evidence, invalid or missing evidence produces an inconclusive result, and no Harbor/SWE-bench execution is required for the test path.

Do not start the regression card, comparison view, evaluation-set run, or UI polish before this exit condition passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
