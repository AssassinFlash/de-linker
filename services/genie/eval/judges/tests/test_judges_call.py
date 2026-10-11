"""The call layer: where a remote judge's request goes and what it costs."""

from dataclasses import replace
from typing import Any

from linker_judges import judges as judges_mod
from linker_judges.http import Response
from linker_judges.judges import call, chat_url
from linker_judges.rubric import QA_QUESTIONS

CHAT_COMPLETIONS = "/chat/completions"


def test_an_openrouter_base_already_carries_v1() -> None:
    assert chat_url("https://openrouter.ai/api/v1") == (
        "https://openrouter.ai/api/v1" + CHAT_COMPLETIONS
    )


def test_a_bare_host_gets_the_v1_prefix() -> None:
    assert (
        chat_url("https://aihubmix.com/") == "https://aihubmix.com/v1/chat/completions"
    )


def test_the_openrouter_judge_posts_to_the_router_and_bills_its_own_cost(
    monkeypatch: Any,
) -> None:
    seen: dict[str, Any] = {}

    def fake_post(url: str, body: dict[str, Any], key: str | None) -> Response:
        seen["url"], seen["key"], seen["auth_model"] = url, key, body["model"]
        return Response(
            {
                "model": "openai/gpt-6-luna",
                "choices": [
                    {
                        "message": {
                            "content": '{"grounded": {"probabilities": {"0": 0.0, "1": 0.0, "2": 1.0}}, "reason": "r"}'
                        }
                    }
                ],
                "usage": {"prompt_tokens": 195, "completion_tokens": 162, "cost": 0.01},
            },
            1.0,
            1,
            0.0,
        )

    monkeypatch.setattr(judges_mod, "post_json", fake_post)
    monkeypatch.setattr(
        judges_mod,
        "openrouter_credentials",
        lambda: ("https://openrouter.example/api/v1", "k"),
    )
    jev = replace(
        __import__("linker_judges.registry", fromlist=["JUDGES"]).JUDGES["jev"]
    )

    verdict = call(jev, {"answer": "a"}, QA_QUESTIONS)

    assert seen["url"] == "https://openrouter.example/api/v1" + CHAT_COMPLETIONS
    assert seen["key"] == "k"
    assert seen["auth_model"] == "typesafe/jev-router"
    assert verdict.model_reported == "openai/gpt-6-luna"
    # The endpoint's own cost wins over the fallback price formula (0.30/1.20).
    assert abs(verdict.cost_usd - 0.01) < 1e-12
    assert verdict.answers["grounded"].label == "2"
