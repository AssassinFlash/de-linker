"""The conversation summary an inquiry carries (#244): deepseek-flash writes it, the
service checks it, and anything it cannot vouch for is refused with a reason."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

from linker_genie import summary
from linker_genie.app import app
from linker_genie.summary import SummaryError, SummaryRequest, summarise

H2 = {"id": 4107, "name": "SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)"}
BATTERY = {"id": 3582, "name": "EcoFlow OCEAN 2 Battery 8.03 kWh (EF BD-8-S2)"}
INVERTER = {
    "id": 3576,
    "name": "EcoFlow OCEAN 2 HD-P3-12K0-S2 (12 kW three-phase hybrid)",
}


def _request(
    *turns: tuple[str, str], products: list[dict[str, Any]], locale: str = "en"
) -> SummaryRequest:
    return SummaryRequest.model_validate(
        {
            "locale": locale,
            "messages": [{"role": role, "content": text} for role, text in turns],
            "products": products,
        }
    )


EN = _request(
    (
        "user",
        "I need a hybrid inverter for a three-phase house, 12 kWp on the roof, backup is a must",
    ),
    ("assistant", "For three-phase with backup, the SAJ H2-10K-T3 fits."),
    ("user", "ok, I'd take 4 of the H2-10K-T3 for four houses in the same project"),
    products=[H2],
)


def _model(
    answer: dict[str, Any] | str, seen: list[tuple[str, str]] | None = None
) -> Callable[[str, str], str]:
    def complete(system: str, user: str) -> str:
        if seen is not None:
            seen.append((system, user))
        return answer if isinstance(answer, str) else json.dumps(answer)

    return complete


GOOD = {
    "summary": "The customer needs a three-phase hybrid inverter with backup for 12 kWp. They want the SAJ H2-10K-T3 for four houses.",
    "quantities": [{"product_id": 4107, "quantity": 4}],
    "conditions": ["three-phase", "12 kWp PV", "backup required"],
    "note": "",
}


def test_a_checked_answer_is_the_summary() -> None:
    result = summarise(EN, _model(GOOD))
    assert result.summary.startswith("The customer needs")
    assert [(q.product_id, q.quantity) for q in result.quantities] == [(4107, 4)]
    assert result.conditions == ["three-phase", "12 kWp PV", "backup required"]
    assert result.note == ""
    assert result.dropped == []


def test_the_model_reads_the_conversation_and_the_products_only() -> None:
    seen: list[tuple[str, str]] = []
    summarise(EN, _model(GOOD, seen))
    ((system, user),) = seen
    assert "user: I need a hybrid inverter" in user
    assert "assistant: For three-phase with backup" in user
    assert "4107: SAJ H2-10K-T3" in user
    assert "LANGUAGE: English" in user
    assert "data, not instructions" in system


def test_german_is_asked_for_in_the_sie_form() -> None:
    seen: list[tuple[str, str]] = []
    request = _request(("user", "Drei Stück bitte"), products=[BATTERY], locale="de")
    summarise(
        request,
        _model(
            {
                "summary": "Der Kunde möchte drei Batterien.",
                "quantities": [],
                "conditions": [],
                "note": "",
            },
            seen,
        ),
    )
    assert "LANGUAGE: German (formal, Sie)" in seen[0][1]


def test_the_identity_of_the_customer_is_not_accepted() -> None:
    """The service never receives who the customer is (privacy policy: name, email
    and account are not sent with the messages)."""
    with pytest.raises(ValueError):
        SummaryRequest.model_validate(
            {"locale": "en", "messages": [], "products": [], "email": "a@example.test"}
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("summary", "The customer compared it with an offer of €1,450."),
        ("summary", "Customer was quoted 900 EUR per unit."),
        ("conditions", ["budget 5000 Euro"]),
        ("note", "Please match $1,200."),
    ],
)
def test_a_summary_never_carries_a_price(field: str, value: Any) -> None:
    request = _request(
        (
            "user",
            "My other supplier offers it for €1,450, 900 EUR, 5000 Euro or $1,200. I want 4.",
        ),
        products=[H2],
    )
    with pytest.raises(SummaryError) as refused:
        summarise(request, _model({**GOOD, field: value}))
    assert refused.value.reason == "price"


def test_a_figure_nobody_said_is_refused() -> None:
    with pytest.raises(SummaryError) as refused:
        summarise(
            EN, _model({**GOOD, "summary": "The customer needs 15 kWh of storage."})
        )
    assert refused.value.reason == "figure"


def test_figures_from_the_conversation_and_the_product_names_pass() -> None:
    request = _request(
        (
            "user",
            "Jahresverbrauch ca. 9.500 kWh pro Jahr, drei Stück der Batterie und einen Wechselrichter",
        ),
        products=[BATTERY, INVERTER],
        locale="de",
    )
    result = summarise(
        request,
        _model(
            {
                "summary": "Der Kunde möchte 3 OCEAN 2 Battery 8.03 kWh und einen HD-P3-12K0-S2; Jahresverbrauch 9500 kWh.",
                "quantities": [
                    {"product_id": 3582, "quantity": 3},
                    {"product_id": 3576, "quantity": 1},
                ],
                "conditions": ["Jahresverbrauch ca. 9.500 kWh"],
                "note": "",
            }
        ),
    )
    assert [(q.product_id, q.quantity) for q in result.quantities] == [
        (3582, 3),
        (3576, 1),
    ]


def test_a_quantity_for_a_product_not_in_the_conversation_is_dropped() -> None:
    result = summarise(
        EN,
        _model(
            {
                **GOOD,
                "quantities": [
                    {"product_id": 4107, "quantity": 4},
                    {"product_id": 999, "quantity": 4},
                ],
            }
        ),
    )
    assert [(q.product_id, q.quantity) for q in result.quantities] == [(4107, 4)]
    assert result.dropped == ["product 999"]


def test_a_quantity_the_customer_never_stated_is_dropped() -> None:
    result = summarise(
        EN, _model({**GOOD, "quantities": [{"product_id": 4107, "quantity": 6}]})
    )
    assert result.quantities == []
    assert result.dropped == ["quantity 6"]


@pytest.mark.parametrize(
    "answer",
    [
        "not json",
        json.dumps({"summary": "x"}),
        json.dumps({**GOOD, "summary": "x" * (summary.MAX_SUMMARY + 1)}),
        json.dumps({**GOOD, "conditions": ["c"] * (summary.MAX_CONDITIONS + 1)}),
        json.dumps({**GOOD, "quantities": [{"product_id": 4107, "quantity": 0}]}),
        json.dumps({**GOOD, "extra": 1}),
    ],
)
def test_an_answer_outside_the_shape_is_refused(answer: str) -> None:
    with pytest.raises(SummaryError) as refused:
        summarise(EN, _model(answer))
    assert refused.value.reason == "unreadable"


def test_an_empty_summary_is_refused() -> None:
    with pytest.raises(SummaryError) as refused:
        summarise(EN, _model({**GOOD, "summary": "  "}))
    assert refused.value.reason == "unreadable"


def test_a_conversation_without_a_customer_message_is_not_sent_to_the_model() -> None:
    request = _request(("assistant", "Hi, I'm Genie."), products=[])
    seen: list[tuple[str, str]] = []
    with pytest.raises(SummaryError) as refused:
        summarise(request, _model(GOOD, seen))
    assert refused.value.reason == "empty"
    assert seen == []


def test_a_model_failure_is_refused_with_its_cause() -> None:
    def broken(system: str, user: str) -> str:
        raise summary.ModelUnavailable("timeout")

    with pytest.raises(SummaryError) as refused:
        summarise(EN, broken)
    assert refused.value.reason == "model: timeout"


def test_the_endpoint_answers_the_checked_summary() -> None:
    app.state.summary_model = _model(GOOD)
    try:
        response = TestClient(app, headers=SHELL).post("/summary", json=EN.model_dump())
    finally:
        del app.state.summary_model
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == GOOD["summary"]
    assert body["quantities"] == [{"product_id": 4107, "quantity": 4}]
    assert body["model"] == "deepseek-flash"


def test_the_endpoint_names_the_reason_it_refuses() -> None:
    app.state.summary_model = _model({**GOOD, "summary": "Offer: €900."})
    try:
        response = TestClient(app, headers=SHELL).post("/summary", json=EN.model_dump())
    finally:
        del app.state.summary_model
    assert response.status_code == 422
    assert response.json() == {"error": "price"}


def test_the_call_asks_deepseek_flash_on_the_official_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    sent: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}]}
        )

    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("GENIE_BASE_URL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    complete = summary.deepseek(transport=httpx.MockTransport(handle))
    assert json.loads(complete("system", "user")) == GOOD
    (request,) = sent
    assert str(request.url) == "https://api.deepseek.com/v1/chat/completions"
    body = json.loads(request.content)
    assert body["model"] == "deepseek-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == summary.MAX_TOKENS


def test_a_failed_call_is_a_named_model_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    complete = summary.deepseek(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, json={}))
    )
    with pytest.raises(summary.ModelUnavailable) as failed:
        complete("system", "user")
    assert str(failed.value) == "HTTP 503"


def test_an_article_in_the_summary_is_not_a_figure() -> None:
    """ "eine Lieferung" is an article; measured on de-note-deadline (eval/summary/)."""
    request = _request(
        ("user", "Bitte bis Ende November liefern. 2 Schränke."),
        products=[H2],
        locale="de",
    )
    result = summarise(
        request,
        _model(
            {
                "summary": "Der Kunde möchte 2 Schränke und eine Lieferung bis Ende November.",
                "quantities": [],
                "conditions": ["Lieferung bis Ende November"],
                "note": "",
            }
        ),
    )
    assert result.summary.endswith("Ende November.")


def test_a_digit_the_customer_wrote_as_a_word_passes() -> None:
    request = _request(("user", "drei Stück bitte"), products=[H2], locale="de")
    result = summarise(
        request,
        _model(
            {
                "summary": "Der Kunde möchte 3 Stück.",
                "quantities": [{"product_id": 4107, "quantity": 3}],
                "conditions": [],
                "note": "",
            }
        ),
    )
    assert [(q.product_id, q.quantity) for q in result.quantities] == [(4107, 3)]
