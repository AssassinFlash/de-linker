"""Placeholders are filled from this turn's tools; leftover IDs stay visible."""

import pytest
from pydantic import ValidationError

from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.hydrate import fill, hydrate, leftover_placeholders
from linker_genie.schema import CardsBlock, HandoffBlock, TextBlock, TurnOutput


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


def test_collect_check_compatibility_records_documents() -> None:
    payload = {
        "verdict": "released",
        "conditions": [],
        "documents": [
            {
                "url": "https://de-linker.test/wp-content/uploads/datasheet.pdf",
                "page": 2,
            },
            {"url": "https://de-linker.test/wp-content/uploads/manual.pdf"},
        ],
    }
    gathered = collect("linker/check-compatibility", payload)

    assert (
        gathered.facts["compat.document.0"].value
        == "https://de-linker.test/wp-content/uploads/datasheet.pdf · p.2"
    )
    assert (
        gathered.facts["compat.document.1"].value
        == "https://de-linker.test/wp-content/uploads/manual.pdf"
    )


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
