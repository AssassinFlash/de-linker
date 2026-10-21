# Signed numeric facts

A real German SAJ eSolar AIO3 answer rendered an operating range as 40℃ to 60℃. The hosted PDF says -40℃ to +60℃. Markdown preserves literal signs; the loss happened before generation: tag() left signs outside the numeric fact slot, so a model citing the slot received a positive value.

Unary signs now belong to the fact. Complete preceding measurements still distinguish binary range separators; model names remain intact. Comparison, quote, comma, ellipsis and Unicode-minus boundaries are covered, together with table and attachment unit inheritance and EN/DE hydration. Raw retrieved chunks are tagged per request, so no knowledge-index rebuild is needed.

The initial eleven regressions produced ten failures on the old implementation. Review uncovered further signed boundaries; eighteen boundary cases produced fifteen failures on the first narrow fix. The corrected related suite passes 156 tests. Independent Spec review passes the full diff and 156 tests. Independent Standards review passes the full diff and 200 tests including attachments. Ruff, formatting, module mypy and diff checks pass. Models, channels, prompts and the renderer are unchanged.

The source diagnosis and hosted-PDF fingerprint are in diagnosis.json. Production release and real-response readback are separate acceptance gates; this source review does not claim deployment.
