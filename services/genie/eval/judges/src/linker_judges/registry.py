"""The judges in the bake-off, with their prices and where they run.

Prices are USD per million tokens from aihubmix's billing configuration
(`GET https://aihubmix.com/api/v1/models`, `pricing_lines`, default tier, read
2026-10-09). DeepSeek bills twice that between 01:00-04:00 and 06:00-10:00 UTC; the
runs here fall outside those hours and the report states the time of every call.
Open models cost 0 per call (owner 2026-10-09: openjev and its kind are counted at 0).
"""

from __future__ import annotations

import os

from .judges import AIHUBMIX, Judge


def _local(name: str, port: int) -> str:
    """A local llama.cpp server; `JUDGE_<NAME>_URL` points the judge elsewhere (the VPS)."""
    return os.environ.get(
        f"JUDGE_{name.upper().replace('-', '_').replace('.', '_')}_URL",
        f"http://127.0.0.1:{port}",
    )


JUDGES: dict[str, Judge] = {
    judge.name: judge
    for judge in (
        # TypeSafe Jev through aihubmix's /v1/systemone; output tokens are free.
        Judge(
            "jev", "system_one", "jev-1.13", AIHUBMIX, price_in=0.0462, price_out=0.0
        ),
        # Chat judges; temperature 0 where the model accepts it (claude-haiku-5-5 rejects
        # the parameter, and aihubmix degrades its JSON mode, so it gets neither).
        Judge(
            "deepseek", "chat", "deepseek-v4.1-flash", AIHUBMIX, 0.155, 0.62, 0.0, True
        ),
        Judge("haiku", "chat", "claude-haiku-5-5", AIHUBMIX, 0.1, 0.5, None, False),
        Judge("gemini", "chat", "gemini-3.8-flash", AIHUBMIX, 0.75, 3.75, 0.0, True),
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
