"""The judges in the bake-off, with their prices and where they run.

Prices are USD per million tokens. aihubmix judges: aihubmix's billing
configuration (`GET https://aihubmix.com/api/v1/models`, `pricing_lines`, default
tier, read 2026-10-09); aihubmix itself bills twice that between 01:00-04:00 and
06:00-10:00 UTC, and the report states the time of every call. The direct DeepSeek
judge: the official pricing page (api-docs.deepseek.com/quick_start/pricing, read
2026-10-11) at peak rates — off-peak halves them. OpenRouter reports each call's
true cost in `usage.cost` (its jev-router's backend varies per call), which
overrides the fallback prices. Open models cost 0 per call
(owner 2026-10-09: openjev and its kind are counted at 0).
"""

from __future__ import annotations

import os

from .judges import AIHUBMIX, DEEPSEEK, OPENROUTER, Judge


def _local(name: str, port: int) -> str:
    """A local llama.cpp server; `JUDGE_<NAME>_URL` points the judge elsewhere (the VPS)."""
    return os.environ.get(
        f"JUDGE_{name.upper().replace('-', '_').replace('.', '_')}_URL",
        f"http://127.0.0.1:{port}",
    )


JUDGES: dict[str, Judge] = {
    judge.name: judge
    for judge in (
        # TypeSafe Jev through OpenRouter's chat completions (owner ruling
        # 2026-10-11: aihubmix's balance is depleted and drops to fallback). The
        # router replies with calibrated probabilities and reports each call's
        # true cost in usage.cost — which wins over these prices, because its
        # backend varies per call (deepseek-v4.1-flash and openai/gpt-6-luna were
        # both seen on 2026-10-11); 0.30/1.20 are the observed deepseek-flash
        # backend's rates, kept as the fallback formula's input.
        Judge(
            "jev",
            "chat",
            "typesafe/jev-router",
            OPENROUTER,
            0.30,
            1.20,
            None,
            True,
        ),
        # The cascade's escalation judge, direct on the official DeepSeek API
        # (owner ruling 2026-10-11: aihubmix serves only the Jev first pass and
        # the gemini-embedding-2 index, and gemini-3.8-flash — a candidate the
        # banned session had written into the #33 spec — is withdrawn entirely).
        # deepseek-flash thinks by default and rejects sampling parameters, so no
        # temperature is sent; json_object is measured to work on the direct
        # endpoint (docs/acceptance/2026-10-11/13/).
        Judge("deepseek", "chat", "deepseek-flash", DEEPSEEK, 0.30, 1.20, None, True),
        # Chat judges; temperature 0 where the model accepts it (claude-haiku-5-5 rejects
        # the parameter, and aihubmix degrades its JSON mode, so it gets neither).
        Judge("haiku", "chat", "claude-haiku-5-5", AIHUBMIX, 0.1, 0.5, None, False),
        # Open decision models (Apache-2.0, ggml-org GGUF conversions; judge-models.md).
        Judge(
            "julia1",
            "system_one",
            "Julia-1-Q8_0",
            _local("julia1", 18081),
            weights="Julia-1 (144M) Q8_0",
        ),
        Judge(
            "laya",
            "system_one",
            "Laya-Q8_0",
            _local("laya", 18082),
            weights="Laya (0.4B) Q8_0",
        ),
        Judge(
            "lev",
            "system_one",
            "lev-Q4_K_M",
            _local("lev", 18083),
            weights="lev (4B) Q4_K_M",
        ),
        # A general open LLM as the chat-judge baseline, thinking off for a short reply.
        Judge(
            "qwen3-1.7b",
            "chat",
            "Qwen3-1.7B-Q4_K_M",
            _local("qwen3-1.7b", 18084),
            temperature=0.0,
            json_mode=True,
            extra={"chat_template_kwargs": {"enable_thinking": False}},
            weights="Qwen3-1.7B Q4_K_M",
        ),
    )
}
