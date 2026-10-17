"""Placeholders are filled from this turn's tools; leftover IDs stay visible."""

from typing import Any

import pytest
from pydantic import ValidationError

from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.hydrate import fill, hydrate, leftover_placeholders
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)


def test_fill_replaces_known_placeholders() -> None:
    facts = TurnFacts()
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    assert fill("Rated {fact:p4107.ac_power_kw} kW.", facts) == "Rated 10 kW."


def test_unknown_placeholder_is_left_in_place() -> None:
    facts = TurnFacts()
    text = "Rated {fact:p1.missing} kW."
    assert fill(text, facts) == text
    assert leftover_placeholders(text) == ["p1.missing"]


def test_hydrate_touches_text_blocks_and_handoff_summaries() -> None:
    facts = TurnFacts()
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    facts.add(
        Fact(
            id="handoff.sentence_en",
            value="Please write to our team at sales@de-linker.com.",
            source="handoff-team",
        )
    )
    facts.product_ids.add(4107)
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="{fact:p4107.ac_power_kw} kW", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
            HandoffBlock(summary="{fact:handoff.sentence_en}"),
        ],
    )
    filled = hydrate(output, facts)
    text = filled.blocks[0]
    cards = filled.blocks[1]
    handoff = filled.blocks[2]
    assert isinstance(text, TextBlock)
    assert isinstance(cards, CardsBlock)
    assert isinstance(handoff, HandoffBlock)
    assert text.text == "10 kW"
    assert cards.product_ids == [4107]
    assert handoff.summary == "Please write to our team at sales@de-linker.com."


def test_collect_search_products_records_qualified_facts() -> None:
    payload = {
        "qualified": [
            {
                "product_id": 4107,
                "facts": {"ac_power_kw": 10.0, "pv_input_kw": 20.0},
                "commerce": {"price_visible": False},
            }
        ],
        "unknown_fields": ["backup"],
    }
    gathered = collect("linker/search-products", payload)
    assert 4107 in gathered.qualified_ids
    assert gathered.facts["p4107.ac_power_kw"].value == "10.0"
    assert gathered.unknown_fields == ["backup"]


def test_collect_search_products_records_released_pairings() -> None:
    payload = {
        "qualified": [
            {
                "product_id": 4107,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": [
                    {
                        "product_id": 6519,
                        "verdict": "released_with_accessory",
                        "conditions": [{"en": "Bridge required", "de": "Bridge nötig"}],
                    },
                    {"product_id": 6521, "verdict": "unknown", "conditions": []},
                ],
            }
        ],
    }
    gathered = collect("linker/search-products", payload)

    assert gathered.product_ids == {4107, 6519, 6521}
    # Only the released pair qualifies for cards; the unknown one stays out.
    assert gathered.qualified_ids == {4107, 6519}
    assert gathered.facts["compat.verdict.6519"].value == "released_with_accessory"
    assert gathered.facts["compat.condition.6519.0"].value == "Bridge required"


def test_a_german_turn_reads_the_german_side_of_a_condition() -> None:
    """R6-de (measured 2026-10-11): a German answer that cites a pairing
    condition must not hydrate the English side - the English sentence in
    German text is the row's failure. The data is English-first: a German
    turn falls back to the English side of a half-written pair, and an
    English turn never reads the German side."""
    payload = {
        "qualified": [
            {
                "product_id": 4107,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": [
                    {
                        "product_id": 3611,
                        "verdict": "released",
                        "conditions": [
                            {
                                "en": "A column holds six modules",
                                "de": "Sechs Module je Säule",
                            },
                            {"en": "Meter required"},
                            {"de": "Zähler erforderlich"},
                        ],
                    }
                ],
            }
        ],
    }

    german = collect("linker/search-products", payload, "de")

    assert german.facts["compat.condition.3611.0"].value == "Sechs Module je Säule"
    # The half-written pair reads its English side rather than going empty.
    assert german.facts["compat.condition.3611.1"].value == "Meter required"
    assert german.facts["compat.condition.3611.2"].value == "Zähler erforderlich"
    english = collect("linker/search-products", payload, "en")
    assert (
        english.facts["compat.condition.3611.0"].value == "A column holds six modules"
    )
    # The reverse leak is refused: no German sentence in an English answer.
    assert "compat.condition.3611.2" not in english.facts


def test_collect_check_compatibility_records_documents() -> None:
    payload = {
        "verdict": "released",
        "conditions": [{"en": "Meter required", "de": "Zähler erforderlich"}],
        "documents": [
            {
                "url": "https://de-linker.test/wp-content/uploads/datasheet.pdf",
                "page": 2,
            },
            {"url": "https://de-linker.test/wp-content/uploads/manual.pdf"},
        ],
    }
    gathered = collect("linker/check-compatibility", payload)

    assert gathered.facts["compat.condition.0"].value == "Meter required"
    assert (
        gathered.facts["compat.document.0"].value
        == "https://de-linker.test/wp-content/uploads/datasheet.pdf · p.2"
    )
    assert (
        gathered.facts["compat.document.1"].value
        == "https://de-linker.test/wp-content/uploads/manual.pdf"
    )
    # The same turn in German: the second call site reads the German side too.
    german = collect("linker/check-compatibility", payload, "de")
    assert german.facts["compat.condition.0"].value == "Zähler erforderlich"


def test_illegal_structure_is_refused_by_the_schema() -> None:
    with pytest.raises(ValidationError):
        TurnOutput.model_validate(
            {"language": "en", "blocks": [{"type": "text", "text": "hi", "extra": 1}]}
        )
    with pytest.raises(ValidationError):
        TurnOutput.model_validate(
            {
                "language": "en",
                "blocks": [{"type": "action", "name": "delete_everything", "args": {}}],
            }
        )


def test_a_power_or_energy_value_carries_its_unit() -> None:

    gathered = TurnFacts()
    gathered.add(Fact(id="p6483.ac_power_kw", value="3", source="selection-facts"))
    gathered.add(Fact(id="p6483.pv_input_kw", value="9", source="selection-facts"))
    gathered.add(Fact(id="p3582.usable_kwh", value="8.03", source="selection-facts"))
    gathered.add(Fact(id="p2090.kwh_range", value="5–25", source="selection-facts"))
    gathered.add(Fact(id="p6483.phase", value="1", source="selection-facts"))
    text = (
        "From {fact:p6483.ac_power_kw} with {fact:p6483.pv_input_kw} of PV, "
        "{fact:p3582.usable_kwh} usable, {fact:p2090.kwh_range} per stack, "
        "phase {fact:p6483.phase}."
    )
    assert fill(text, gathered) == (
        "From 3 kW with 9 kW of PV, 8.03 kWh usable, 5–25 kWh per stack, phase 1."
    )
    assert fill("{fact:p6483.ac_power_kw} kW", gathered) == "3 kW"
    assert fill("{fact:p3582.usable_kwh}kWh", gathered) == "8.03kWh"


def _knowledge(locale: str = "en") -> TurnFacts:
    return collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "770c-p37-63a0",
                    "title": "SAJ H2 manual",
                    "page": 37,
                    "doc_url": "https://de-linker.com/h2.pdf",
                    "text": "| No. of MPPT | [n1=3] | Selling Power Limit [n2=5000 W] |",
                    "figures": {"770c-p37-63a0.n1": "3", "770c-p37-63a0.n2": "5000 W"},
                },
                {
                    "chunk_id": "a786-p1-b113",
                    "title": "GoodWe warranty",
                    "page": 1,
                    "doc_url": "https://de-linker.com/gw.pdf",
                    "text": "[n1=10 years] from [n2=1 st January 2026]",
                    "figures": {
                        "a786-p1-b113.n1": "10 years",
                        "a786-p1-b113.n2": "1 st January 2026",
                    },
                },
                {
                    "chunk_id": "770c-p38-f6f6",
                    "title": "SAJ H2 manual",
                    "page": 38,
                    "doc_url": "https://de-linker.com/h2.pdf",
                    "text": "More rows.",
                    "figures": {},
                },
            ]
        },
        locale,
    )


def _links(blocks: list[Any]) -> list[tuple[str, str | None, str | None]]:
    return [(b.ref, b.label, b.url) for b in blocks if isinstance(b, DocumentBlock)]


def test_a_document_figure_is_filled_and_its_chunk_linked() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="It has {fact:770c-p37-63a0.n1} MPPTs.", refs=[])],
    )

    blocks = hydrate(output, _knowledge()).blocks

    assert blocks[0].text == "It has 3 MPPTs."  # type: ignore[union-attr]
    assert _links(blocks) == [
        (
            "770c-p37-63a0",
            "SAJ H2 manual · p.\u00a037",
            "https://de-linker.com/h2.pdf#page=37",
        )
    ]


def test_cited_chunks_become_one_link_per_file_after_the_answer() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="First part.", refs=["770c-p37-63a0"]),
            CardsBlock(product_ids=[3556]),
            TextBlock(text="Second part.", refs=["770c-p38-f6f6", "a786-p1-b113"]),
        ],
    )

    blocks = hydrate(output, _knowledge()).blocks

    assert [block.type for block in blocks] == [
        "text", "cards", "text", "document", "document",
    ]  # fmt: skip
    assert [(ref, label) for ref, label, _ in _links(blocks)] == [
        ("770c-p37-63a0", "SAJ H2 manual · pp.\u00a037, 38"),
        ("a786-p1-b113", "GoodWe warranty · p.\u00a01"),
    ]


def test_a_german_answer_localizes_the_figures_and_links_in_german() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text="Ab dem {fact:a786-p1-b113.n2} gelten {fact:a786-p1-b113.n1}.",
                refs=["a786-p1-b113"],
            )
        ],
    )

    blocks = hydrate(output, _knowledge("de")).blocks

    assert blocks[0].text == "Ab dem 1. Januar 2026 gelten 10 Jahre."  # type: ignore[union-attr]
    assert [label for _, label, _ in _links(blocks)] == ["GoodWe warranty · S.\u00a01"]


def test_a_chunk_the_model_linked_itself_is_not_linked_twice() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="See the manual.", refs=["770c-p37-63a0"]),
            DocumentBlock(ref="770c-p37-63a0"),
        ],
    )

    blocks = hydrate(output, _knowledge()).blocks

    assert [ref for ref, _, _ in _links(blocks)] == ["770c-p37-63a0"]


def test_a_unit_written_twice_is_written_once() -> None:
    assert (
        fill("limit {fact:770c-p37-63a0.n2} W here", _knowledge())
        == "limit 5000 W here"
    )
    assert fill("{fact:770c-p37-63a0.n1} MPPTs", _knowledge()) == "3 MPPTs"


def test_two_adjacent_placeholders_both_fill() -> None:
    """Issue #257 trial run: the unit check swallowed the second placeholder."""
    text = "{fact:770c-p37-63a0.n1}–{fact:770c-p37-63a0.n2}."

    assert fill(text, _knowledge()) == "3–5000 W."
