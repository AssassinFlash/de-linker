"""Jev on OpenRouter's /api/v1/systemone: the request, the answer, every failure explicit."""

import json
from typing import Any

import httpx
import pytest

from linker_genie.jev import ATTEMPTS, MODEL, QUESTIONS, Jev, JevError, page_state

# The shape OpenRouter returned for "saj" on 2026-10-17
# (docs/research/2026-10-17-jev-intent/raw/run2.json), with needs_followup added.
ANSWER: dict[str, Any] = {
    "model": "typesafe/jev-1.13-20260917",
    "answers": {
        "intent": {
            "type": "choice",
            "choice": "find_products",
            "probabilities": {"find_products": 0.99, "small_talk": 0.01},
            "confidence": 0.99,
        },
        "about_this_page": {"type": "noul", "noul": 0.1},
        "wants_person": {"type": "noul", "noul": 0.07},
        "needs_followup": {"type": "noul", "noul": 0.3},
    },
    "usage": {"input_tokens": 763, "output_tokens": 143, "cost": 3.2046e-05},
    "provider": "TypeSafe",
}


def _jev(handler: Any) -> tuple[Jev, list[float]]:
    waits: list[float] = []
    jev = Jev(
        "test-key",
        "https://openrouter.example/api/v1",
        transport=httpx.MockTransport(handler),
        sleep=waits.append,
    )
    return jev, waits


def test_one_request_asks_the_four_questions_of_jev_itself() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ANSWER)

    jev, _ = _jev(handler)
    reading = jev.read("saj", page_state("other", None), [("user", "hi")])
    (request,) = seen
    assert str(request.url) == "https://openrouter.example/api/v1/systemone"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == MODEL
    assert (
        set(body["questions"])
        == set(QUESTIONS)
        == {
            "intent",
            "about_this_page",
            "wants_person",
            "needs_followup",
        }
    )
    assert body["state"]["customer_message"] == "saj"
    assert body["state"]["conversation"] == [{"role": "user", "content": "hi"}]
    assert (reading.intent, reading.confidence) == ("find_products", 0.99)
    assert reading.wants_person == 0.07
    assert reading.as_log()["cost"] == 3.2046e-05


def test_a_transient_failure_is_retried() -> None:
    answers = iter([httpx.Response(503), httpx.Response(200, json=ANSWER)])
    jev, waits = _jev(lambda request: next(answers))
    assert jev.read("saj", {"type": "other"}).intent == "find_products"
    assert waits == [0.25]


def test_a_failure_that_outlasts_the_retries_is_raised() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("down", request=request)

    jev, waits = _jev(handler)
    with pytest.raises(JevError, match=f"after {ATTEMPTS} attempts: transport"):
        jev.read("saj", {"type": "other"})
    assert len(calls) == ATTEMPTS
    assert waits == [0.25, 0.5]


def test_a_refused_request_is_not_retried_and_never_names_the_key() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    jev, _ = _jev(handler)
    with pytest.raises(JevError) as raised:
        jev.read("saj", {"type": "other"})
    assert calls == [1]
    assert "test-key" not in str(raised.value)


def test_an_answer_from_another_model_is_refused() -> None:
    other = {**ANSWER, "model": "deepseek/deepseek-v4.1-flash"}
    jev, _ = _jev(lambda request: httpx.Response(200, json=other))
    with pytest.raises(JevError, match="not typesafe/jev-1.13"):
        jev.read("saj", {"type": "other"})


def test_an_incomplete_answer_is_refused() -> None:
    partial = {**ANSWER, "answers": {"intent": ANSWER["answers"]["intent"]}}
    jev, _ = _jev(lambda request: httpx.Response(200, json=partial))
    with pytest.raises(JevError, match="incomplete"):
        jev.read("saj", {"type": "other"})


def test_the_page_is_described_as_the_measurement_did() -> None:
    assert page_state("draft", None) == {"type": "solution_draft"}
    assert page_state("product", "SAJ H2-10K-T3") == {
        "type": "product",
        "product": "SAJ H2-10K-T3",
    }
