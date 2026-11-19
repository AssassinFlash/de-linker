"""Published Woo figures through the same turn cycle used by the HTTP service."""

import pytest

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.hydrate import hydrate
from linker_genie.route import Route
from linker_genie.schema import (
    DocumentBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)

MANUAL = "https://site.test/h2-manual.pdf"
DATASHEET = "https://site.test/h2-datasheet.pdf"


def product(product_id: int) -> TurnFacts:
    return collect(
        "linker/get-product",
        {
            "product_id": product_id,
            "title": "SAJ H2 hybrid inverter",
            "documents": [
                {"url": MANUAL, "document_id": "doc-manual", "title": "Manual"},
                {
                    "url": DATASHEET,
                    "document_id": "doc-datasheet",
                    "title": "Datasheet",
                },
            ],
            "figures": {
                "max_battery_charge_a": {
                    "value": "50",
                    "unit": "A",
                    "citation": {"url": MANUAL, "page": 38, "title": "Manual"},
                    "evidence_refs": [
                        "doc-manual:p38",
                        "doc-manual:p43",
                        "doc-datasheet:p2",
                    ],
                    "qualifier": {
                        "quantity_kind": "maximum",
                        "scope": "per_battery_port",
                        "direction": "charge",
                        "ports": ["BAT1", "BAT2"],
                        "source_expression": "2*50 A",
                    },
                },
                "n_battery_ports": {
                    "value": "2",
                    "citation": {"url": DATASHEET, "page": 2, "title": "Datasheet"},
                },
            },
        },
    )


def answer(
    text: str, *products: TurnFacts, locale: Locale = "en"
) -> tuple[str, list[DocumentBlock]]:
    question = (
        "Wie hoch ist der maximale Ladestrom je Batterieeingang?"
        if locale == "de"
        else "What is the maximum charge current per battery input?"
    )
    request = TurnRequest(
        conversation_id="figure-citations",
        locale=locale,
        messages=[TurnMessage(role="user", content=question)],
    )
    draft = TurnOutput(language=locale, blocks=[TextBlock(text=text)])
    result = run(
        request,
        lambda *_: (draft, TurnFacts()),
        Route("documents"),
        merge(list(products)),
    )
    prose = " ".join(
        block.text for block in result.output.blocks if isinstance(block, TextBlock)
    )
    return prose, [
        block for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]


@pytest.mark.parametrize(
    ("locale", "expected", "label"),
    [
        (
            "en",
            "The maximum charge current is 50 A per battery input.",
            "Manual · pp. 38, 43",
        ),
        (
            "de",
            "Der maximale Ladestrom beträgt 50 A je Batterieeingang.",
            "Manual · S. 38, 43",
        ),
    ],
)
def test_qualified_current_links_its_bound_manual_and_keeps_per_port_scope(
    locale: Locale,
    expected: str,
    label: str,
) -> None:
    prose, links = answer(
        "{fact:p1179.max_battery_charge_a}", product(1179), locale=locale
    )
    assert prose == expected
    assert [(link.url, link.label) for link in links] == [(f"{MANUAL}#page=38", label)]


def test_explicit_port_count_supplies_its_separately_bound_datasheet() -> None:
    _, links = answer(
        "{fact:p1179.max_battery_charge_a}\n\nThere are {fact:1179.n_battery_ports} battery inputs.",
        product(1179),
    )
    assert {link.url for link in links} == {f"{MANUAL}#page=38", f"{DATASHEET}#page=2"}


def test_shared_manual_keeps_each_products_evidence() -> None:
    _, links = answer(
        "The first inverter\n\n{fact:p1179.max_battery_charge_a}\n\nThe other inverter\n\n{fact:p1181.max_battery_charge_a}",
        product(1179),
        product(1181),
    )
    assert [(link.ref, link.url) for link in links] == [
        ("p1179.max_battery_charge_a.source", f"{MANUAL}#page=38"),
        ("p1181.max_battery_charge_a.source", f"{MANUAL}#page=38"),
    ]


@pytest.mark.parametrize("chunk_owner", [1179, 1181])
def test_an_indexed_page_and_a_figure_merge_only_for_the_same_evidence_owner(
    chunk_owner: int,
) -> None:
    chunk = "manual-p38-excerpt"
    retrieved = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": chunk,
                    "doc_url": MANUAL,
                    "page": 38,
                    "document_id": "doc-manual",
                    "document_revision": "revision-1",
                    "evidence_product_id": chunk_owner,
                    "product_ids": [chunk_owner],
                }
            ]
        },
    )
    result = hydrate(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="{fact:p1179.max_battery_charge_a}", refs=[chunk]),
                DocumentBlock(ref=chunk),
            ],
        ),
        merge([product(1179), retrieved]),
    )
    refs = {block.ref for block in result.blocks if isinstance(block, DocumentBlock)}
    expected = {"p1179.max_battery_charge_a.source"}
    if chunk_owner != 1179:
        expected.add(chunk)
    assert refs == expected


@pytest.mark.parametrize(
    "clarification",
    [
        "The current limit is not shared between the two inputs.",
        "This is not a shared current limit for both inputs.",
    ],
)
def test_negated_shared_limit_keeps_the_qualified_answer(clarification: str) -> None:
    prose, _ = answer(
        "{fact:p1179.max_battery_charge_a}\n" + clarification, product(1179)
    )
    assert "50 A per battery input." in prose
    assert clarification in prose


def test_german_negation_of_the_shared_scope_keeps_its_answer() -> None:
    clarification = "Dieser Grenzwert gilt nicht für beide Eingänge zusammen."
    prose, _ = answer(
        "{fact:p1179.max_battery_charge_a}\n" + clarification,
        product(1179),
        locale="de",
    )
    assert "50 A je Batterieeingang." in prose
    assert clarification in prose


def test_other_product_port_count_does_not_support_a_shared_current() -> None:
    prose, _ = answer(
        "{fact:p1179.max_battery_charge_a}\nThat current is shared between both inputs unlike the other inverter with {fact:p1181.n_battery_ports} ports.",
        product(1179),
        product(1181),
    )
    assert "shared between both inputs" not in prose


def test_fallback_shows_document_library_without_unconsumed_figure_pages() -> None:
    _, links = answer("{fact:missing}", product(1179))
    assert {link.url for link in links} == {MANUAL, DATASHEET}


@pytest.mark.parametrize(
    ("locale", "text"),
    [
        (
            "en",
            "The total battery charging current is {fact:p1179.max_battery_charge_a}.",
        ),
        ("en", "{fact:p1179.max_battery_charge_a} in total for both inputs."),
        ("en", "{fact:p1179.max_battery_charge_a}\nBoth inputs share it."),
        (
            "de",
            "{fact:p1179.max_battery_charge_a}\nEr gilt für beide Eingänge zusammen.",
        ),
        ("de", "Der maximale Entladestrom beträgt {fact:p1179.max_battery_charge_a}."),
        ("de", "{fact:p1179.max_battery_charge_a} für beide Eingänge zusammen."),
        (
            "en",
            "{fact:p1179.max_battery_charge_a}\nThat limit is shared between both inputs, not available at each input.",
        ),
        (
            "de",
            "Dieser Grenzwert gilt für beide Eingänge zusammen.\n{fact:p1179.max_battery_charge_a}",
        ),
    ],
)
def test_contradictory_placement_cannot_ship_a_qualified_current(
    locale: Locale, text: str
) -> None:
    prose, links = answer(text, product(1179), locale=locale)
    assert "50 A" not in prose
    assert {link.url for link in links} == {MANUAL, DATASHEET}
