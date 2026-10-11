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


def test_the_openrouter_jev_posts_to_systemone_as_jev_itself(
    monkeypatch: Any,
) -> None:
    seen: dict[str, Any] = {}

    def fake_post(url: str, body: dict[str, Any], key: str | None) -> Response:
        seen["url"], seen["key"], seen["auth_model"] = url, key, body["model"]
        seen["state"], seen["questions"] = body.get("state"), body.get("questions")
        return Response(
            {
                "model": "typesafe/jev-1.13-20260917",
                "answers": {"grounded": {"type": "score", "probabilities": {"0": 0.0, "1": 0.0, "2": 1.0}, "confidence": 0.95}},
                "usage": {"input_tokens": 314, "output_tokens": 23, "cost": 0.01},
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

    # The hosted base keeps its /v1 suffix once: the join strips it first.
    assert seen["url"] == "https://openrouter.example/api/v1/systemone"
    assert seen["key"] == "k"
    assert seen["auth_model"] == "typesafe/jev-1.13"
    assert seen["questions"]["grounded"]["type"] == "score"
    assert verdict.model_reported == "typesafe/jev-1.13-20260917"
    # The endpoint's own cost wins over the fallback price formula (0.30/1.20).
    assert abs(verdict.cost_usd - 0.01) < 1e-12
    # A score's label is its most probable level; Jev reports its confidence.
    assert verdict.answers["grounded"].label == "2"
    confidence = verdict.answers["grounded"].confidence
    assert confidence is not None and abs(confidence - 0.95) < 1e-9
