"""The understanding layer runs the route's calls and records every failure."""

import json
import logging
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from conftest import STORE_FIXTURE as FIXTURE

from linker_genie.abilities import AbilityClient
from linker_genie.jev import JevError, Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.schema import TurnRequest
from linker_genie.storeapi import VocabularyError
from linker_genie.understand import Understander

SEARCH = {
    "qualified": [
        {
            "product_id": 4109,
            "title": "SAJ HS2-5K-T2-X",
            "url": "/p/4109",
            "why": [],
            "facts": {"phase": 3},
            "commerce": {},
        }
    ],
    "excluded": {"by_reason": {}},
    "unknown_fields": [],
}


class FakeJev:
    def __init__(
        self, reading: Reading | None = None, error: str | None = None
    ) -> None:
        self.reading = reading
        self.error = error
        self.seen: list[tuple[str, dict[str, Any]]] = []

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        self.seen.append((message, page))
        if self.error:
            raise JevError(self.error)
        assert self.reading is not None
        return self.reading


def _abilities(seen: list[httpx.Request], status: int = 200) -> AbilityClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json={"result": SEARCH})

    return AbilityClient(
        "http://site.test", transport=httpx.MockTransport(handle), sleep=lambda s: None
    )


def _request(message: str, locale: str = "en", **page: Any) -> TurnRequest:
    return TurnRequest.model_validate(
        {
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": message}],
            "locale": locale,
            "page_context": page or {"type": "other"},
        }
    )


def _reading(intent: str, confidence: float = 0.99) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.00003)  # type: ignore[arg-type]


def test_saved_report_weather_uses_only_matching_native_planning_context(
    vocabulary: Vocabulary,
) -> None:
    from linker_genie import planning

    project, run = "a" * 32, "b" * 32
    raw = {
        "schema_version": 1,
        "status": "available",
        "project": {"id": project, "title": "Owned fixture", "revision": 3},
        "rows": [],
        "runs": [
            {
                "id": run,
                "revision": 3,
                "kind": "planning_report_v1",
                "state": "succeeded",
                "rows": [{"label": "recorded_source", "value": "retained weather"}],
                "details_available": True,
            }
        ],
        "truncated": False,
    }
    # The retained production failure's exact question and Jev decision: the
    # fixed weather sentence ran before the selected report could be read.
    question = (
        "For the selected saved report, please explain the exact UTC start and end of "
        "the PV generation and energy calculation periods, the weather databases, "
        "the time zone and the TMY selection years. Are the equipment and country "
        "checks approved? Keep the two calculation periods separate and identify "
        "the saved results behind your answer."
    )
    reading = Reading("documents_specs", 0.46, 0.76, 0.05, 0.84, 0.167, 0.000041622)
    for message, locale, context, expected in (
        (question, "en", raw, "model"),
        (
            "Welche Wetterdaten und Zeiträume verwendet der ausgewählte gespeicherte Bericht?",
            "de",
            raw,
            "model",
        ),
        ("Which weather data were used for this report?", "en", raw, "model"),
        (
            "Welche Wetterdaten wurden für diesen Bericht verwendet?",
            "de",
            raw,
            "model",
        ),
        ("What is the weather tomorrow?", "en", raw, "scripted"),
        ("Explain tomorrow's weather report", "en", raw, "scripted"),
        ("Wie wird das Wetter morgen?", "de", raw, "scripted"),
        (question, "en", None, "scripted"),
        (
            question,
            "en",
            {**raw, "project": {"id": "c" * 32, "revision": 3}},
            "scripted",
        ),
        (question, "en", {**raw, "status": "unsaved_changes"}, "scripted"),
        (
            question,
            "en",
            {**raw, "project": {"id": project, "revision": 2}},
            "scripted",
        ),
        (question, "en", {**raw, "runs": []}, "scripted"),
    ):
        request = _request(
            message,
            locale,
            planning_project_id=project,
            planning_revision=3,
            planning_run_ids=[run],
        ).model_copy(update={"planning_context": context})
        seen: list[httpx.Request] = []
        prepared = Understander(lambda: vocabulary, FakeJev(reading)).prepare(
            request, _abilities(seen)
        )
        assert prepared.route.name == expected
        assert seen == []
        if expected == "model":
            assert not prepared.route.answer
            assert [call.ability for call in prepared.route.calls] == [planning.NAME]
            assert prepared.results[0]["result"]["status"] == "available"
            assert "retained weather" in prepared.results[0]["result"]["text"]
        else:
            assert prepared.route.calls == ()
            assert prepared.facts.facts == {}


def test_saj_is_searched_by_code_before_the_model(vocabulary: Vocabulary) -> None:
    seen: list[httpx.Request] = []
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(_request("saj"), _abilities(seen))
    assert prepared.route.name == "products"
    (request,) = seen
    assert request.url.path.endswith("/linker/search-products/run")
    assert request.url.params["input[brand]"] == "saj"
    assert prepared.facts.qualified_ids == {4109}
    assert prepared.results[0]["result"] == SEARCH
    assert prepared.calls_made == 1
    assert prepared.log["jev"]["intent"] == "find_products"
    assert prepared.log["matches"] == [
        {"kind": "brand", "value": "saj", "words": "saj"}
    ]


def test_an_english_question_on_a_german_page_is_searched_in_english(
    vocabulary: Vocabulary,
) -> None:
    """#374: the route's lang and the HTTP input[lang] follow the question."""
    seen: list[httpx.Request] = []
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(
        _request("which batteries work with saj", "de"), _abilities(seen)
    )
    assert seen
    assert {request.url.params.get("input[lang]") for request in seen} == {"en"}
    assert {call.arguments.get("lang") for call in prepared.route.calls} == {"en"}


def test_a_roof_step_question_asks_size_hint_and_keeps_its_url(
    vocabulary: Vocabulary,
) -> None:
    """#497: the route's one call is size-hint; its URL is the action's."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "result": {
                    "summary": "Open the Solution Configurator.",
                    "configurator_url": "https://site.test/solution-configurator/",
                }
            },
        )

    client = AbilityClient(
        "http://site.test",
        transport=httpx.MockTransport(handle),
        sleep=lambda s: None,
    )
    understander = Understander(lambda: vocabulary, FakeJev(_reading("sizing")))
    prepared = understander.prepare(
        _request("What happens if I skip the roof?"), client
    )
    assert prepared.route.name == "roof"
    assert prepared.calls_made == 1
    (request,) = seen
    assert request.url.path.endswith("/linker/size-hint/run")
    assert not request.url.params
    fact = prepared.facts.facts["size.configurator_url"]
    assert fact.value == "https://site.test/solution-configurator/"
    assert fact.source == "size-hint"


def test_jev_failure_is_logged_and_the_product_word_still_searches(
    vocabulary: Vocabulary, caplog: pytest.LogCaptureFixture
) -> None:
    seen: list[httpx.Request] = []
    understander = Understander(
        lambda: vocabulary, FakeJev(error="jev failed after 3 attempts: http 503")
    )
    with caplog.at_level(logging.WARNING, logger="linker_genie"):
        prepared = understander.prepare(_request("SAJ", "de"), _abilities(seen))
    assert prepared.log["jev_error"] == "jev failed after 3 attempts: http 503"
    assert "deepseek-flash decides this turn" in caplog.text
    assert prepared.route.name == "products"
    assert "jev unavailable" in prepared.route.reasons
    assert seen[0].url.params["input[lang]"] == "de"


def test_jev_failure_without_product_words_leaves_the_turn_to_the_model(
    vocabulary: Vocabulary,
) -> None:
    seen: list[httpx.Request] = []
    understander = Understander(lambda: vocabulary, FakeJev(error="down"))
    prepared = understander.prepare(_request("Danke schön", "de"), _abilities(seen))
    assert (prepared.route.name, seen) == ("model", [])
    assert prepared.log["jev_error"] == "down"


def test_missing_openrouter_key_is_recorded(vocabulary: Vocabulary) -> None:
    prepared = Understander(lambda: vocabulary, None).prepare(
        _request("hi"), _abilities([])
    )
    assert prepared.log["jev_error"] == "OPENROUTER_API_KEY is not configured"


def test_an_unreadable_vocabulary_is_recorded_and_jev_still_routes() -> None:
    def broken() -> Vocabulary:
        raise VocabularyError("store api /products returned 503")

    seen: list[httpx.Request] = []
    understander = Understander(broken, FakeJev(_reading("inquiry_status")))
    prepared = understander.prepare(_request("where is my proforma?"), _abilities(seen))
    assert prepared.log["vocabulary_error"] == "store api /products returned 503"
    assert prepared.route.name == "inquiry"
    assert seen[0].url.path.endswith("/linker/inquiry-status/run")


def test_a_failed_route_call_is_recorded_and_the_turn_goes_on(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(_request("goodwe"), _abilities([], status=500))
    assert prepared.results == []
    failure = prepared.log["call_failures"][0]
    assert failure["text"].startswith("linker/search-products")
    assert failure["kind"] == "ability"


def test_jev_sees_the_page_product_by_name(vocabulary: Vocabulary) -> None:
    jev = FakeJev(_reading("documents_specs"))
    understander = Understander(lambda: vocabulary, jev)
    h2 = next(p["id"] for p in FIXTURE["en"]["products"] if "H2-10K-T3" in p["name"])
    prepared = understander.prepare(
        _request("datasheet please", type="product", product_id=h2), _abilities([])
    )
    assert jev.seen[0][1]["type"] == "product"
    assert "H2-10K-T3" in jev.seen[0][1]["product"]
    knowledge = prepared.route.calls[0]
    assert knowledge.ability == "linker/search-knowledge"
    assert knowledge.arguments["product_ids"] == [h2]


def test_the_log_is_json(vocabulary: Vocabulary) -> None:
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(_request("H2-10K-T3"), _abilities([]))
    json.dumps(prepared.log)
    assert prepared.log["route"] == "products"


@pytest.mark.parametrize(
    ("message", "locale"),
    [
        ("Can I talk to a person?", "en"),
        ("Ich möchte mit einem Mitarbeiter sprechen", "de"),
    ],
)
def test_a_person_phrase_routes_to_a_person_without_jev(
    vocabulary: Vocabulary, message: str, locale: str
) -> None:
    jev = FakeJev(_reading("find_products"))
    seen: list[httpx.Request] = []
    prepared = Understander(lambda: vocabulary, jev).prepare(
        _request(message, locale), _abilities(seen)
    )
    assert prepared.route.name == "person"
    assert prepared.route.calls == ()
    # Not one model call: neither Jev nor an ability (#243, Knocket's outer layer).
    assert (jev.seen, seen) == ([], [])
    assert prepared.log["person_phrase"]
    assert prepared.reading is None


def test_the_reading_is_kept_for_the_contact_offer(vocabulary: Vocabulary) -> None:
    reading = Reading("other", 0.9, 0.1, 0.92, 0.2, 2.6, 0.0)
    prepared = Understander(lambda: vocabulary, FakeJev(reading)).prepare(
        _request("This is useless."), _abilities([])
    )
    assert prepared.reading == reading


def test_a_pasted_parts_list_is_the_services_own_turn(vocabulary: Vocabulary) -> None:
    """#251: the rows are matched in code, Jev is not asked, no ability runs."""
    jev = FakeJev(_reading("find_products"))
    seen: list[httpx.Request] = []
    understander = Understander(lambda: vocabulary, jev)
    prepared = understander.prepare(
        _request(
            "2x SAJ H2-10K-T3\n"
            "1 x GoodWe GW10K-ETA-G20\n"
            "3 Stk. SAJ H2\n"
            "1 x SMA Sunny Boy 5.0"
        ),
        _abilities(seen),
    )
    assert prepared.route.name == "parts"
    assert jev.seen == []
    assert seen == []
    assert prepared.parts_list is not None
    assert [
        (row.status, row.product_id, row.quantity) for row in prepared.parts_list.rows
    ] == [
        ("matched", 4107, 2),
        ("matched", 3556, 1),
        ("uncertain", None, 3),
        ("missing", None, 1),
    ]
    assert prepared.log["parts"]["rows"] == 4
    assert prepared.log["parts"]["uncertain"] == 1


def test_a_csv_attachment_becomes_a_parts_turn(vocabulary: Vocabulary) -> None:
    """#251: the CSV rides #236's channel, is read in-process, and its rows match."""
    import base64

    from linker_genie.schema import Upload

    upload = Upload(
        name="list.csv",
        type="text/csv",
        data=base64.b64encode(b"Produkt;Menge\nSAJ H2-10K-T3;2\n").decode(),
    )
    request = _request("Attached: list.csv")
    request.attachments.append(upload)
    prepared = Understander(lambda: vocabulary, None).prepare(request, _abilities([]))
    assert prepared.route.name == "parts"
    assert prepared.parts_list is not None
    assert [(row.status, row.product_id) for row in prepared.parts_list.rows] == [
        ("matched", 4107)
    ]
    assert [reading.kind for reading in prepared.readings] == ["list"]
    assert prepared.cards[0]["kind"] == "list"


def test_the_layer_times_its_own_phases(vocabulary: Vocabulary) -> None:
    """#336: the layer's clock travels with the Prepared; the app adopts it."""
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(_request("saj"), _abilities([]))
    assert prepared.timing is not None
    record = prepared.timing.as_log()
    assert {
        "understand.vocabulary",
        "understand.jev",
        "understand.calls",
        "understand.call.linker/search-products",
        "total",
    } <= set(record)
    assert all(value >= 0 for value in record.values())


def test_a_route_call_failure_is_timed_like_any_call(vocabulary: Vocabulary) -> None:
    """The failed call's duration is the one latency work needs (the retries the
    ability client makes happen inside it); it is observed in the finally."""
    understander = Understander(lambda: vocabulary, FakeJev(_reading("find_products")))
    prepared = understander.prepare(_request("goodwe"), _abilities([], status=500))
    assert prepared.log["call_failures"]
    assert prepared.timing is not None
    assert "understand.call.linker/search-products" in prepared.timing.as_log()


def test_a_page_read_is_timed_under_its_ability_name(vocabulary: Vocabulary) -> None:
    """A route's page read is `understand.call.linker/read-page` — the dossier's
    first suspect in the serial stack (§1.14), so the key names it directly."""
    from linker_genie.jev import Reading as JevReading

    def pages(page: Any, question: str, logged_in: bool) -> dict[str, Any]:
        return {
            "type": page.type,
            "title": page.title or "",
            "url": "/blog/",
            "outline": ["What is AC coupling?"],
            "text": "## What is AC coupling?\nAC coupling adds a battery inverter.",
            "figures": {},
            "complete": True,
        }

    jev = FakeJev(JevReading("other", 0.9, 0.97, 0.05, 0.1, 2.6, 0.0))
    understander = Understander(lambda: vocabulary, jev, pages=pages)
    prepared = understander.prepare(
        _request(
            "What does this page mean by AC coupling?",
            type="blog",
            title="Blog",
            url="/blog/",
        ),
        _abilities([]),
    )
    assert [call.ability for call in prepared.route.calls] == ["linker/read-page"]
    assert prepared.timing is not None
    assert "understand.call.linker/read-page" in prepared.timing.as_log()
