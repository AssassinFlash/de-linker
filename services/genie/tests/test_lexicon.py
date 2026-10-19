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
from linker_genie.lexicon import (
    MIN_CODE,
    SHORT_BODY_WIDTH,
    Category,
    Product,
    Vocabulary,
    build,
    normalize,
)
from linker_genie.route import Subject, plan, with_page
from linker_genie.schema import PageContext
from linker_genie.storeapi import StoreVocabulary, VocabularyError
from linker_genie.template import german_is_clean

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
        unresolved_bodies=vocabulary.unresolved_bodies,
        shared_suffixes=vocabulary.shared_suffixes,
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


# Snapshot regression: these tokens are not models on the 2026-10-15 catalog.
# The clause oracles are the synthetic products below. This list alone stays
# green if the rule is widened, because the snapshot simply has no such key.
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


def _product(
    product_id: int,
    name: str,
    *,
    sku: str = "",
    models: tuple[str, ...] = (),
    brands: tuple[tuple[str, str], ...] = (),
    series: tuple[str, ...] = (),
) -> Product:
    return Product(
        product_id,
        name,
        sku,
        brands,
        series,
        models,
        (),
    )


def _catalog(
    products: list[Product],
    translated: list[tuple[Product, list[Category]]] | None = None,
) -> Vocabulary:
    return build(products, [], translated or [])


def _model_values(vocabulary: Vocabulary, key: str) -> list[str]:
    return [entry.value for entry in vocabulary.lookup(key) if entry.kind == "model"]


def _alone(model: str, sku: str) -> Vocabulary:
    """One product. A neighbour's name can contain a rejected key and hide the clause."""
    return _catalog([_product(1, "Hybrid", models=(model,), sku=sku)])


def test_each_short_body_clause_is_enforced_on_synthetic_products() -> None:
    """Each clause has a product that makes that clause the reason for the result.

    Width is `SHORT_BODY_WIDTH` and is not `MIN_CODE`. A four-character mixed
    join, a two-character join, a letters-only join, and a join that needs the
    trailing segment are not keys. Each of those products is alone: another
    product's name can contain the same characters, and the uniqueness guard
    would then reject the key even after the clause was deleted. A three-segment
    code with no brand token is a key, and so is a SKU of that shape. The search
    text is the source that held the body.
    """
    assert SHORT_BODY_WIDTH == 3
    assert MIN_CODE == 4
    vocabulary = _catalog(
        [
            _product(1, "Hybrid", models=("EF AB-8-S2",), sku="SKU-AB8"),
            _product(6, "Pack", models=("BD-8-S2",), sku="SKU-NOBRAND"),
            _product(7, "Pack", sku="ZX-9-S2"),
            _product(
                8,
                "Two models",
                models=("EF HD-P1-6K-S2", "EF QR-7-S2"),
                sku="SKU-MULTI",
            ),
        ]
    )
    assert _model_values(vocabulary, "ab8") == ["EF AB-8-S2"]
    assert _model_values(vocabulary, "bd8") == ["BD-8-S2"]
    assert "bd8" not in vocabulary.unresolved_bodies
    assert _model_values(vocabulary, "zx9") == ["ZX-9-S2"]
    assert _model_values(vocabulary, "qr7") == ["EF QR-7-S2"]
    # A1+B2 is four characters and mixes a letter and a digit. Only the width
    # rejects it. Allowing a longer join yields a1b2.
    wide = _alone("EF A1-B2-S2", "SKU-WIDE")
    assert _model_values(wide, "a1b2") == []
    assert wide.unresolved_bodies == frozenset()
    # B+8 is two characters. A check that accepts every join below MIN_CODE yields b8.
    short = _alone("EF B-8-S2", "SKU-SHORT")
    assert _model_values(short, "b8") == []
    assert short.unresolved_bodies == frozenset()
    # AB+C is letters only. Dropping the letter-and-digit check yields abc.
    letters = _alone("EF AB-C-S2", "SKU-LETTERS")
    assert _model_values(letters, "abc") == []
    assert letters.unresolved_bodies == frozenset()
    # The only width-3 mixed join of this code includes the trailing segment.
    # The correct rule yields no key. Allowing the trailing segment yields bd8.
    trailing = _alone("WW X-B-D8", "SKU-TRAIL")
    assert _model_values(trailing, "bd8") == []
    assert trailing.unresolved_bodies == frozenset()


def test_a_shared_body_asks_instead_of_searching_the_family() -> None:
    """One structural owner, and a second product that only contains the body.

    Deleting `holders == ids` would keep the key (the structural set has one id)
    and the Ocean sentence would search that battery. The body must stay
    unresolved, and the route must ask instead of searching the family.
    """
    owner = _product(
        1,
        "EcoFlow OCEAN 2 Battery Base (EF BD-8-S2)",
        sku="DLK-ECOFLOW-EFBD8S2",
        models=("EF BD-8-S2",),
        brands=(("EcoFlow", "ecoflow"),),
        series=("ecoflow-ocean-2-battery",),
    )
    other = _product(2, "Controller board BD8 spare", sku="CTRL-BOARD-1")
    vocabulary = _catalog([owner, other])
    assert _model_values(vocabulary, "bd8") == []
    assert "bd8" in vocabulary.unresolved_bodies
    message = "Looking for Ecoflow Ocean two batteries, the BD-8 one."
    matches = vocabulary.match(message)
    assert any(match.kind == "series" for match in matches)
    assert [match for match in matches if match.kind == "model"] == []
    for reading in (_reading("find_products"), None):
        route = _route(vocabulary, {"lang": "en", "message": message}, reading)
        assert route.name == "clarify"
        assert route.calls == ()
        assert route.answer == (
            "BD-8 matches more than one product. Which model do you mean?"
        )
    german = "Ich suche zwei EcoFlow OCEAN Batterien, die BD-8."
    german_route = _route(
        vocabulary, {"lang": "de", "message": german}, _reading("find_products")
    )
    assert german_route.name == "clarify"
    assert german_route.calls == ()
    assert german_route.answer == (
        "BD-8 passt zu mehr als einem Produkt. Welches Modell meinen Sie?"
    )
    assert german_is_clean(german_route.answer)


def test_a_german_title_head_code_is_a_short_body_on_the_english_id() -> None:
    """`_add_codes` reads the German head. The short-body pass reads those codes too."""
    english = _product(10, "Ocean battery", sku="DLK-ECOFLOW-PLAIN")
    german = _product(99, "EcoFlow Batterie BD-8-S2", sku="DLK-ECOFLOW-PLAIN")
    vocabulary = _catalog([english], [(german, [])])
    assert _model_values(vocabulary, "bd8") == ["BD-8-S2"]
    (entry,) = [item for item in vocabulary.lookup("bd8") if item.kind == "model"]
    assert entry.product_ids == frozenset({10})


def test_a_parenthetical_code_is_not_a_title_code_in_either_language() -> None:
    """`_codes` stops at the bracket. A German-only parenthetical does not become a key."""
    english = _product(10, "Ocean battery", sku="DLK-ECOFLOW-PLAIN")
    german = _product(99, "EcoFlow Batterie (EF BD-8-S2)", sku="DLK-ECOFLOW-PLAIN")
    vocabulary = _catalog([english], [(german, [])])
    assert _model_values(vocabulary, "bd8") == []


def test_the_real_catalog_records_shared_suffixes_and_no_unresolved_body(
    vocabulary: Vocabulary,
) -> None:
    assert "s2" in vocabulary.shared_suffixes
    assert "g20" in vocabulary.shared_suffixes
    assert "bd8" not in vocabulary.shared_suffixes
    assert vocabulary.unresolved_bodies == frozenset()


SUFFIX_QUESTIONS = [
    (
        "en",
        "the S2 one",
        "S2 is a suffix on more than one model. Which model do you mean?",
    ),
    (
        "en",
        "the G20 one",
        "G20 is a suffix on more than one model. Which model do you mean?",
    ),
    (
        "de",
        "die S2",
        "S2 ist eine Endung mehrerer Modelle. Welches Modell meinen Sie?",
    ),
    (
        "de",
        "das G20",
        "G20 ist eine Endung mehrerer Modelle. Welches Modell meinen Sie?",
    ),
]


@pytest.mark.parametrize(
    ("lang", "message", "sentence"),
    SUFFIX_QUESTIONS,
    ids=[case[1] for case in SUFFIX_QUESTIONS],
)
@pytest.mark.parametrize(
    "reading",
    [_reading("find_products"), None, _reading("documents_specs")],
    ids=["jev", "down", "documents"],
)
def test_a_suffix_only_request_asks_which_model(
    vocabulary: Vocabulary,
    lang: str,
    message: str,
    sentence: str,
    reading: Reading | None,
) -> None:
    route = _route(vocabulary, {"lang": lang, "message": message}, reading)
    assert route.name == "clarify"
    assert route.calls == ()
    assert route.answer == sentence
    if lang == "de":
        assert german_is_clean(sentence)
    page = PageContext(
        type="product", url="https://example.test/p", product_id=3582, title="Battery"
    )
    on_page = with_page(route, page, True, False, _route_subject(vocabulary), message)
    assert on_page.name == "clarify"
    assert on_page.calls == ()
    assert on_page.answer == sentence


def _route_subject(vocabulary: Vocabulary) -> Subject:
    return Subject(
        (),
        vocabulary.device_class,
        vocabulary.labels,
        vocabulary.phase,
        vocabulary.series_members,
        unresolved_bodies=vocabulary.unresolved_bodies,
        shared_suffixes=vocabulary.shared_suffixes,
    )


def test_a_question_around_an_ordinary_short_token_is_not_a_suffix_question(
    vocabulary: Vocabulary,
) -> None:
    route = _route(
        vocabulary,
        {"lang": "en", "message": "what is the AC output?"},
        _reading("find_products"),
    )
    assert route.name == "model"
    assert route.calls == ()
    assert route.answer == ""


def test_a_named_model_is_not_turned_into_a_suffix_question(
    vocabulary: Vocabulary,
) -> None:
    route = _route(
        vocabulary,
        {"lang": "en", "message": "H210KT3 - what is the AC output?"},
        _reading("documents_specs"),
    )
    assert route.name == "documents"
    assert {call.arguments.get("text") for call in route.calls} >= {"H2-10K-T3"}


def test_a_brand_beside_a_suffix_still_searches_the_brand(
    vocabulary: Vocabulary,
) -> None:
    route = _route(
        vocabulary,
        {"lang": "en", "message": "EcoFlow S2"},
        _reading("find_products"),
    )
    assert route.name == "products"
    assert route.calls
    assert all(call.arguments.get("brand") == "ecoflow" for call in route.calls)
    assert all("text" not in call.arguments for call in route.calls)
