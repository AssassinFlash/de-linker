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


# Ticket #369. The body of EF BD-8-S2 is written "BD-8" / "BD8"; case, hyphen
# and space are the same key. BD-5 is the only other join the snapshot produces.
SHORT_BODIES = [
    ("BD-8", "EF BD-8-S2", 3582),
    ("BD8", "EF BD-8-S2", 3582),
    ("bd-8", "EF BD-8-S2", 3582),
    ("Bd 8", "EF BD-8-S2", 3582),
    ("the BD-8 one", "EF BD-8-S2", 3582),
    ("BD-8-S2", "EF BD-8-S2", 3582),
    ("Ich suche den BD-8", "EF BD-8-S2", 3582),
    ("BD-5", "EF BD-5-S2", 3581),
    ("BD5", "EF BD-5-S2", 3581),
]


@pytest.mark.parametrize(
    ("message", "label", "product_id"),
    SHORT_BODIES,
    ids=[case[0] for case in SHORT_BODIES],
)
def test_a_hyphenated_model_body_matches_its_product(
    vocabulary: Vocabulary, message: str, label: str, product_id: int
) -> None:
    models = [m for m in vocabulary.match(message) if m.kind == "model"]
    assert [(m.value, m.product_ids) for m in models] == [
        (label, frozenset({product_id}))
    ]


# The repro (#369): EcoFlow and OCEAN are in the sentence, and without the body
# the series hit is the Battery Base family. EN and DE use the same match.
BD8_QUESTIONS = [
    ("en", "Looking for Ecoflow Ocean two batteries, the BD-8 one."),
    ("de", "Ich suche zwei EcoFlow OCEAN Batterien, die BD-8."),
]


@pytest.mark.parametrize(
    ("lang", "message"), BD8_QUESTIONS, ids=[case[0] for case in BD8_QUESTIONS]
)
@pytest.mark.parametrize(
    "reading", [_reading("find_products"), None], ids=["jev", "down"]
)
def test_the_bd8_question_searches_that_battery(
    vocabulary: Vocabulary, lang: str, message: str, reading: Reading | None
) -> None:
    route = _route(vocabulary, {"lang": lang, "message": message}, reading)
    assert route.calls
    assert {call.arguments.get("text") for call in route.calls} == {"EF BD-8-S2"}
    assert all(call.arguments.get("brand") == "ecoflow" for call in route.calls)
    assert all("series" not in call.arguments for call in route.calls)


def test_the_full_model_still_beats_its_short_body(vocabulary: Vocabulary) -> None:
    (match,) = [m for m in vocabulary.match("EF BD-8-S2") if m.kind == "model"]
    assert match.value == "EF BD-8-S2"
    assert match.product_ids == frozenset({3582})
    assert normalize(match.words) == "efbd8s2"


# Suffixes and other short tokens that must not become a model. "S2" sits on 24
# products, "G20" on 21; "AC", "DC" and "2" are ordinary words; "20K" is inside
# both H2-20K-T3 and GW20K; "G2F" is a unique trailing suffix.
NOT_A_MODEL = [
    "S2",
    "s2",
    "G20",
    "G10",
    "P3",
    "AC",
    "DC",
    "2",
    "the S2 one",
    "EcoFlow S2",
    "8-S2",
    "8S2",
    "G2F",
    "20K",
    "10K",
    "HV1",
    "BD",
    "8",
    "what is the AC output?",
    "48 V DC",
    "OCEAN 2",
]


@pytest.mark.parametrize("message", NOT_A_MODEL)
def test_a_suffix_or_bare_short_token_is_not_a_model(
    vocabulary: Vocabulary, message: str
) -> None:
    assert [m for m in vocabulary.match(message) if m.kind == "model"] == []


def test_an_embedded_power_token_does_not_replace_the_full_code(
    vocabulary: Vocabulary,
) -> None:
    """A bare 20K names no product; the full codes that contain it still do."""
    assert vocabulary.match("20K") == []
    (h2,) = [m for m in vocabulary.match("H2-20K-T3") if m.kind == "model"]
    assert h2.value == "H2-20K-T3"
    (gw,) = [m for m in vocabulary.match("GW20K-ETA-G20") if m.kind == "model"]
    assert gw.value == "GW20K-ETA-G20"


# Campaign #330 class E: case, the hyphen and the space. Eleven messages.
E_CLASS = [
    ("is the gw10k eta g20 single-phase?", "model", "GW10K-ETA-G20"),
    ("Do you have Gw10k-Eta-G20 in stock?", "model", "GW10K-ETA-G20"),
    ("H210KT3 - what is the AC output?", "model", "H2-10K-T3"),
    ("h2 10k t3 availability please", "model", "H2-10K-T3"),
    ("Tell me about gw 5.1 bat d g20", "model", "GW5.1-BAT-D-G20"),
    ("GOODWE inverters - which GOODWE models do you carry?", "brand", "goodwe"),
    ("ist der gw10k eta g20 dreiphasig?", "model", "GW10K-ETA-G20"),
    ("H210KT3 - welche Nennleistung?", "model", "H2-10K-T3"),
    ("Haben Sie GW5,1-BAT-D-G20 auf Lager?", "model", "GW5.1-BAT-D-G20"),
    ("saj hs2 5k t2 x verfügbar?", "model", "HS2-5K-T2-X"),
    ("Zeigen Sie mir GOODWE GW25K-ETA-G20", "model", "GW25K-ETA-G20"),
]


@pytest.mark.parametrize(
    ("message", "kind", "value"),
    E_CLASS,
    ids=[
        "E1-EN",
        "E2-EN",
        "E3-EN",
        "E4-EN",
        "E5-EN",
        "E6-EN",
        "E1-DE",
        "E2-DE",
        "E3-DE",
        "E4-DE",
        "E5-DE",
    ],
)
def test_e_class_case_hyphen_and_space_variants_still_match(
    vocabulary: Vocabulary, message: str, kind: str, value: str
) -> None:
    matches = vocabulary.match(message)
    assert (kind, value) in {(m.kind, m.value) for m in matches}
    models = {m.value for m in matches if m.kind == "model"}
    assert models == ({value} if kind == "model" else set())


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
