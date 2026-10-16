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
