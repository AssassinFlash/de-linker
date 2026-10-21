"""The saved-solution reader (#496).

Ask Genie on the design report saves the solution first and opens the dock with
its id; `solution.py` reads it through the shell's read-only ability, re-runs the
engine from the stored design and writes the figures as `[nK=…]` tags, the way
the page reader writes a page's (#234). The model cites `{fact:solution.nK}` and
hydration fills the value.

The fixture values are the recorded answer of the Munich design of
`tests/fixtures/configurator/residential-en.json` (the engine's fixture feed),
reduced to what the ability returns.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie import facts, hydrate, solution
from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.schema import PageContext, TextBlock, TurnOutput, TurnRequest
from linker_genie.understand import Understander

MANIFEST = Path(__file__).resolve().parent / "fixtures" / "339" / "manifest.json"


class Recorder:
    """An ability client that records the call and answers with a payload."""

    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, dict[str, Any], str | None]] = []

    def run(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        user_context: str | None = None,
    ) -> Any:
        self.calls.append((name, dict(arguments or {}), user_context))
        if self.error is not None:
            raise self.error
        return self.payload


def _raw(status: str = "solution") -> dict[str, Any]:
    return {
        "id": 45,
        "title": "GoodWe GW10K-ETA-G20, 80538",
        "created": "2026-10-21",
        "status": status,
        "yield": {
            "kwh_year_low": 10034.0,
            "kwh_year_high": 12164.0,
            "kwh_year_mean": 11190.0,
        },
        "storage": {"usable_kwh": 5.8, "recommended": True},
        "metrics": {
            "autarky_low": 0.6142,
            "autarky_high": 0.7142,
            "self_consumption_low": 0.3279,
            "self_consumption_high": 0.3767,
        },
        "selected": {
            "inverter": "GoodWe GW10K-ETA-G20",
            "battery": "GoodWe GW6.0-BAT-D-G20",
            "battery_quantity": 1,
        },
        "basis": [
            "3-phase, as selected",
            "1.00, at most 2.00 per the manufacturer",
            "1.5 kWh × 10 kWp = 15 kWh",
        ],
        "warnings": [],
        "items": [
            {"product_id": 3556, "quantity": 1, "model": "GoodWe GW10K-ETA-G20"},
            {"product_id": 3611, "quantity": 1, "model": "GoodWe GW6.0-BAT-D-G20"},
        ],
    }


def test_the_figures_are_tagged_and_hydrate_the_report_s_values() -> None:
    payload = solution.view(_raw(), "en")
    assert payload["title"] == "GoodWe GW10K-ETA-G20, 80538"
    figures = payload["figures"]
    values = list(figures.values())
    # The German fixture's range read back in the English report's style:
    # 10,034 – 12,164 kWh, mean 11,190, 5.8 kWh, 61 % – 71 % autarky,
    # 33 % – 38 % self-consumption.
    assert any(value.startswith("10,034") for value in values)
    assert any(value.startswith("12,164") for value in values)
    assert any(value.startswith("11,190") for value in values)
    assert any(value.startswith("5.8") for value in values)
    assert "61 %" in values and "71 %" in values
    assert "33 %" in values and "38 %" in values
    # A model code is a name, not a figure.
    assert "GW10K-ETA-G20" in payload["text"]
    assert not any("GW10K" in value for value in values)
    # The text carries the tags the model cites; model_view drops the table.
    first = next(iter(figures))
    assert f"[n{first.split('.n')[1]}=" in payload["text"]
    assert "figures" not in solution.model_view(payload)


def test_the_model_can_hydrate_a_figure_it_cited() -> None:
    payload = solution.view(_raw(), "en")
    gathered = solution.collect(payload)
    key = next(
        key for key, value in payload["figures"].items() if value == "11,190 kWh"
    )
    text = hydrate.fill(f"He says {{fact:{key}}}.", gathered, "en")
    assert text == "He says 11,190 kWh."


def test_a_german_turn_reads_the_figures_in_the_page_s_style() -> None:
    payload = solution.view(_raw(), "de")
    values = payload["figures"].values()
    assert any(value.startswith("10.034") for value in values)
    assert any(value.startswith("12.164") for value in values)
    assert any(value.startswith("5,8") for value in values)
    assert "61 %" in values
    assert "Jahresertrag" in payload["text"]
    assert "Autarkiegrad mit Speicher" in payload["text"]


def test_the_facts_name_the_solution_its_figures_and_its_products() -> None:
    payload = solution.view(_raw(), "en")
    gathered = solution.collect(payload)
    assert gathered.facts["solution"].value == "GoodWe GW10K-ETA-G20, 80538"
    assert "solution.text" in gathered.facts
    assert gathered.facts[next(iter(payload["figures"]))].source == "read-solution"
    assert {product["product_id"] for product in payload["products"]} == {3556, 3611}
    assert gathered.product_ids == {3556, 3611}


def test_a_refused_login_is_not_a_solution_and_carries_no_fact() -> None:
    payload = solution.view({"error": "login_required"}, "en")
    gathered = solution.collect(payload)
    assert payload == {"error": "login_required"}
    assert gathered.facts == {} and gathered.product_ids == set()


def test_the_read_goes_to_the_ability_as_this_customer_and_the_turn_language() -> None:
    recorder = Recorder(_raw())
    payload, gathered = solution.record(recorder, 45, "44|1792300000|signature", "de")
    assert recorder.calls == [
        (
            "linker/read-solution",
            {"solution_id": 45, "lang": "de"},
            "44|1792300000|signature",
        )
    ]
    assert payload["title"]
    assert gathered.facts["solution"].value
    assert gathered.tool_calls[0]["name"] == "linker/read-solution"
    assert gathered.tool_calls[0]["arguments"] == {"solution_id": 45}
    # The log keeps what the model read, so the quality check rebuilds the facts.
    assert gathered.tool_calls[0]["result"] == payload


def test_another_customer_s_solution_is_an_error_never_a_solution() -> None:
    recorder = Recorder(error=AbilityError("linker/read-solution returned 403"))
    with pytest.raises(AbilityError):
        solution.record(recorder, 46, "44|1792300000|signature", "en")


def test_no_amount_of_money_reaches_the_reader() -> None:
    raw = _raw()
    # The engine's result carries no price; a payload that names one still must
    # not surface it, because the reader only reads the keys it knows.
    raw["price"] = "€ 1,680.00"
    raw["items"][0]["price"] = "€ 1,680.00"
    payload = solution.view(raw, "en")
    assert "€" not in payload["text"]
    assert "EUR" not in payload["text"]
    assert "1,680" not in payload["text"]
    assert not any("€" in value for value in payload["figures"].values())


def test_the_stored_input_without_a_solution_says_so() -> None:
    payload = solution.view(_raw(status="no_candidate"), "en")
    assert "no complete solution" in payload["text"]
    assert payload["status"] == "no_candidate"


def test_an_answer_can_use_the_solution_text_from_the_turn_log() -> None:
    """The log stores the model's payload, so a judge rebuilds the same facts."""
    recorder = Recorder(_raw())
    payload, gathered = solution.record(recorder, 45, None, "en")
    logged = gathered.tool_calls[0]["result"]
    assert logged == payload
    assert facts.collect("linker/read-solution", logged).facts.keys() == (
        gathered.facts.keys()
    )


def test_339_names_the_saved_solution_case() -> None:
    """The #339 manifest keeps the regression."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    case = next(
        item for item in manifest["cases"] if item["id"] == "496-saved-solution"
    )
    assert case["issue"] == 496
    assert case["locales"] == ["en", "de"]
    assert case["accounts"] == ["approved", "pending", "restricted", "guest"]
    assert "403" in case["pass"] and "401" in case["pass"]


# The understanding layer: when the turn reads the solution, and what it carries.


REPORT = {
    "type": "other",
    "url": "/solution-configurator/",
    "title": "Solution Configurator",
    "solution_id": 45,
}


class Jev:
    def __init__(self, intent: str, about_page: float, confidence: float = 0.95):
        self.reading = Reading(intent, confidence, about_page, 0.02, 0.1, 2.6, 0.0)  # type: ignore[arg-type]
        self.pages: list[dict[str, Any]] = []

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        self.pages.append(page)
        return self.reading


def _abilities(
    payload: dict[str, Any] | None = None,
    status: int = 200,
    seen: list[httpx.Request] | None = None,
) -> AbilityClient:
    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if request.url.path.endswith("read-solution/run"):
            return httpx.Response(status, json=payload or {})
        return httpx.Response(200, json={"inquiries": []})

    return AbilityClient(
        "http://site.test", transport=httpx.MockTransport(handle), sleep=lambda s: None
    )


def _request(
    message: str, page: dict[str, Any], logged_in: bool = True, locale: str = "en"
) -> TurnRequest:
    return TurnRequest.model_validate(
        {
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": message}],
            "locale": locale,
            "page_context": page,
            "user": {"logged_in": logged_in, "context": "44|1792300000|sig"},
        }
    )


def test_a_question_about_the_solution_reads_it_before_the_model(
    vocabulary: Vocabulary,
) -> None:
    seen: list[httpx.Request] = []
    understander = Understander(
        lambda: vocabulary, Jev("other", about_page=0.97), pages=None
    )
    message = "What does my saved solution say?"
    prepared = understander.prepare(
        _request(message, REPORT), _abilities(_raw(), seen=seen)
    )
    assert [(call.ability, call.arguments) for call in prepared.route.calls] == [
        ("linker/read-solution", {"solution_id": 45})
    ]
    assert prepared.results[0]["name"] == "linker/read-solution"
    assert prepared.facts.facts["solution"].value
    assert "solution.n1" in prepared.facts.facts
    assert "about this page: other" in prepared.route.reasons
    prompt = _user_prompt(_request(message, REPORT), None, prepared)
    assert "solution_id=45" in prompt
    assert '"figures"' not in prompt  # the model reads the tagged text only
    # The call carried the customer's identity token and the turn language.
    read = next(r for r in seen if r.url.path.endswith("read-solution/run"))
    assert read.headers.get("X-Linker-User-Context") == "44|1792300000|sig"
    assert read.url.params["input[lang]"] == "en"


def test_a_solution_word_reads_it_even_when_jev_is_not_sure_it_is_this_page(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("other", about_page=0.1), pages=None
    )
    for message in (
        "What about my solution?",
        "Was sagt meine gespeicherte Lösung?",
        "How high is the yield?",
        "Wie hoch ist der Ertrag?",
    ):
        prepared = understander.prepare(_request(message, REPORT), _abilities(_raw()))
        assert [call.ability for call in prepared.route.calls] == [
            "linker/read-solution"
        ], message


def test_a_message_that_names_no_solution_does_not_read_it(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("small_talk", about_page=0.1), pages=None
    )
    prepared = understander.prepare(_request("Thanks!", REPORT), _abilities(_raw()))
    assert prepared.route.calls == ()
    # The prompt still names the reference, for the model to read it when it must.
    assert "solution_id=45" in _user_prompt(_request("Thanks!", REPORT), None, prepared)


def test_a_solution_read_cut_by_the_call_budget_says_it_was_not_read(
    vocabulary: Vocabulary,
) -> None:
    from linker_genie.route import Call, Route, Subject, with_page

    route = Route(
        "model",
        tuple(
            Call("linker/get-product", {"product_id": product_id})
            for product_id in (3556, 3611, 4107, 1832)
        ),
    )
    result = with_page(
        route,
        PageContext.model_validate(REPORT),
        True,
        True,
        Subject(ids=(), device_class={}),
        "What about my solution?",
    )
    assert any(call.ability == solution.NAME for call in result.dropped)
    assert "saved solution was not read" in result.hint
    assert "figures and its selection basis are here" in result.hint


def test_asking_for_a_person_on_the_report_reads_nothing(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("talk_to_person", about_page=0.99), pages=None
    )
    prepared = understander.prepare(
        _request("Can someone call me about my solution?", REPORT),
        _abilities(_raw()),
    )
    assert prepared.route.name == "person"
    assert prepared.route.calls == ()


def test_a_solution_the_customer_does_not_own_is_logged_and_the_turn_goes_on(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("other", about_page=0.97), pages=None
    )
    prepared = understander.prepare(
        _request("What about my solution?", REPORT), _abilities(status=403)
    )
    assert prepared.results == []
    assert prepared.log["call_failures"] == [
        {
            "text": "linker/read-solution: linker/read-solution returned 403 for "
            "{'input[solution_id]': 45, 'input[lang]': 'en'}"
        }
    ]
    assert "could not be read" in prepared.route.hint


def test_a_login_required_answer_reads_as_a_sign_in_request(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("other", about_page=0.97), pages=None
    )
    prepared = understander.prepare(
        _request("What about my solution?", REPORT, logged_in=False),
        _abilities(status=401),
    )
    # The ability client maps 401 to the login fact; the reader carries it and
    # states no figures.
    assert prepared.results[0]["result"] == {"error": "login_required"}
    assert prepared.facts.facts == {}


def test_an_answer_from_the_solution_is_grounded_and_hydrated(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(
        lambda: vocabulary, Jev("other", about_page=0.97), pages=None
    )
    request = _request("What does my saved solution say?", REPORT)
    prepared = understander.prepare(request, _abilities(_raw()))
    key = next(
        key
        for key, value in prepared.facts.facts.items()
        if value.value == "11,190 kWh"
    )

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text=f"Your saved solution yields {{fact:{key}}} a year.",
                        refs=["solution"],
                    )
                ],
            ),
            TurnFacts(),
        )

    result = run(request, generate, prepared.route, prepared.facts)
    assert result.grounded, result.failures
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert block.text == "Your saved solution yields 11,190 kWh a year."


def _user_prompt(request: TurnRequest, retry: str | None, prepared: Any) -> str:
    from linker_genie.agent import _user_prompt as prompt

    return prompt(request, retry, prepared)
