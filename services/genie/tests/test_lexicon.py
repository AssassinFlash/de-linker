"""Product words against the real Store API vocabulary (snapshot 2026-10-15).

The fixture is the trimmed Store API of a local instance loaded with the live
snapshot (eval/understanding/capture.py). The cases are the bare-word evaluation set
of #233 (eval/understanding/bare_words.json): each must route to a product search for
its brand, series, model or category, whatever Jev says or whether Jev answers at all.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from conftest import STORE_FIXTURE as FIXTURE
from conftest import store_transport as _transport

from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary, normalize
from linker_genie.route import Subject, plan
from linker_genie.storeapi import StoreVocabulary, VocabularyError

CASES = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "eval"
        / "understanding"
        / "bare_words.json"
    ).read_text()
)["cases"]


def _reading(intent: str, confidence: float = 0.99) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.00003)  # type: ignore[arg-type]


def _route(
    vocabulary: Vocabulary, case: dict[str, Any], reading: Reading | None
) -> Any:
    matches = vocabulary.match(case["message"])
    subject = Subject(
        (),
        vocabulary.device_class,
        vocabulary.labels,
        vocabulary.phase,
        vocabulary.series_members,
    )
    bare = vocabulary.bare(case["message"])
    return plan(case["message"], matches, reading, subject, case["lang"], bare)


def _satisfies(arguments: dict[str, Any], expect: dict[str, str]) -> bool:
    ((kind, value),) = expect.items()
    if kind == "brand":
        return arguments.get("brand") == value
    if kind == "model":
        return normalize(arguments.get("text", "")) == normalize(value)
    if kind == "series":
        return arguments.get("series") == value
    if kind == "title":
        return normalize(arguments.get("text", "")) == normalize(value)
    return arguments.get("device_class") == value


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{c['lang']}:{c['message']}" for c in CASES]
)
def test_a_bare_product_word_searches_its_products(
    vocabulary: Vocabulary, case: dict[str, Any]
) -> None:
    route = _route(vocabulary, case, _reading("find_products"))
    assert route.name == "products"
    assert route.show_products and route.no_handoff
    assert route.calls
    for call in route.calls:
        assert call.ability == "linker/search-products"
        assert call.arguments["lang"] == case["lang"]
        assert _satisfies(call.arguments, case["expect"]), call.arguments


# A bare product word may never become small talk, whatever Jev says — a category
# word alone included ("EMS", "Zubehör").
NAMED = [c for c in CASES if c.get("bare", True)]


@pytest.mark.parametrize(
    "case", NAMED, ids=[f"{c['lang']}:{c['message']}" for c in NAMED]
)
@pytest.mark.parametrize(
    "reading",
    [None, _reading("small_talk"), _reading("find_products", 0.4)],
    ids=["jev-down", "jev-small-talk", "jev-unsure"],
)
def test_a_bare_product_word_is_never_small_talk(
    vocabulary: Vocabulary, case: dict[str, Any], reading: Reading | None
) -> None:
    route = _route(vocabulary, case, reading)
    assert route.name == "products"
    assert all(_satisfies(c.arguments, case["expect"]) for c in route.calls)


@pytest.mark.parametrize(
    "message",
    [
        "hi",
        "Hallo!",
        "thanks, that helps",
        "Danke schön",
        "data please",
        "what is the weather in Berlin?",
        "Erzähl mir einen Witz",
        "meters",
        "Notstrom",
        "et",
        "ci",
    ],
)
def test_ordinary_words_are_no_product_words(
    vocabulary: Vocabulary, message: str
) -> None:
    assert [m for m in vocabulary.match(message) if m.kind != "category"] == []


def test_a_german_category_joins_its_english_device_class(
    vocabulary: Vocabulary,
) -> None:
    (match,) = vocabulary.match("Wechselrichter")
    assert (match.kind, match.value) == ("category", "inverters")


def test_a_model_match_names_the_english_product(vocabulary: Vocabulary) -> None:
    (match,) = vocabulary.match("Welcher Speicher passt zum H2-10K-T3?")[:1]
    assert match.kind == "model"
    english_ids = {p["id"] for p in FIXTURE["en"]["products"]}
    assert match.product_ids and match.product_ids <= english_ids


def test_the_longest_product_word_wins(vocabulary: Vocabulary) -> None:
    kinds = [(m.kind, m.value) for m in vocabulary.match("DLK-SAJ-H210KT3")]
    assert kinds == [("model", "H2-10K-T3")]


def test_the_vocabulary_is_cached_until_its_ttl() -> None:
    calls: list[str] = []
    now = [0.0]
    store = StoreVocabulary(
        "http://site.test",
        transport=_transport(FIXTURE, calls),
        clock=lambda: now[0],
        ttl=600,
    )
    store.get()
    first = len(calls)
    now[0] = 599
    store.get()
    assert len(calls) == first
    now[0] = 600
    store.get()
    assert len(calls) == 2 * first


def test_an_unreadable_store_api_is_an_explicit_error() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    store = StoreVocabulary("http://site.test", transport=httpx.MockTransport(down))
    with pytest.raises(VocabularyError, match="503"):
        store.get()


def test_a_category_word_inside_a_sentence_is_not_bare(vocabulary: Vocabulary) -> None:
    assert vocabulary.bare("Zubehör")
    assert not vocabulary.bare("Ich plane eine Anlage mit Wechselrichter und Notstrom")


def test_a_family_with_both_phases_is_searched_per_phase(
    vocabulary: Vocabulary,
) -> None:
    case = {"lang": "en", "message": "EcoFlow OCEAN 2"}
    route = _route(vocabulary, case, _reading("find_products"))
    assert [c.arguments.get("phase") for c in route.calls] == [1, 3]
    assert all(c.arguments["limit"] == 3 for c in route.calls)


def test_a_family_of_one_phase_is_one_search(vocabulary: Vocabulary) -> None:
    route = _route(vocabulary, {"lang": "en", "message": "SAJ H2"}, None)
    (call,) = route.calls
    assert call.arguments == {"series": "saj-h2", "lang": "en", "limit": 6}


def test_a_brand_and_a_series_name_their_products(vocabulary: Vocabulary) -> None:
    """The parts list needs the products behind a brand or series word (#251).

    A row that names only a brand or a family is not one product; the candidates
    come from these maps (the fixture is the live snapshot of 2026-10-15).
    """
    assert 3556 in vocabulary.brand_members["goodwe"]
    assert vocabulary.series_members["goodwe-hca"] == {3587, 3586, 3557}
    assert vocabulary.brand_members["saj"] >= {4107, 4108}
    assert "goodwe" in vocabulary.brand_of[3556]
    assert vocabulary.series_of[3556] == {"goodwe-esa-5-30kw-eta-g20"}
