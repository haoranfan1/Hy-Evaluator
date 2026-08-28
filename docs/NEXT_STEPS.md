# Next Steps

## Status

**Research is complete. Implementation is ready to begin.**

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

Before writing the complete UI, perform the bounded Hy3 handshake needed by this slice:

- Confirm `HY3_BASE_URL`, `HY3_MODEL`, and authentication.
- Confirm Chat Completions and nested `chat_template_kwargs.reasoning_effort=high`.
- Test one structured evaluator response and record unsupported fields honestly.

## Exit condition

The slice is complete when one invalid fixture and one valid fixture can be inspected in the browser, every evaluator finding cites real evidence, invalid or missing evidence produces an inconclusive result, and no Harbor/SWE-bench execution is required for the test path.

Do not start the regression card, comparison view, evaluation-set run, or UI polish before this exit condition passes.

Implementation details are fixed in [ARCHITECTURE.md](ARCHITECTURE.md) and [EVALUATOR_SPEC.md](EVALUATOR_SPEC.md).
