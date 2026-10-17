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
    assert prepared.log["call_failures"][0].startswith("linker/search-products")


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
