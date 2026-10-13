"""Five anchoring checks: injected failures are all refused."""

from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import check
from linker_genie.schema import (
    ActionBlock,
    CardsBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)


def _facts() -> TurnFacts:
    gathered = TurnFacts()
    gathered.product_ids = {4107, 3556}
    gathered.qualified_ids = {4107, 3556}
    gathered.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    gathered.add(Fact(id="p4107.pv_input_kw", value="20", source="selection-facts"))
    gathered.chunk_ids = {"c1"}
    gathered.add(Fact(id="c1", value="Manual · p.2", source="search-knowledge"))
    gathered.add(
        Fact(
            id="c1.text",
            value="Rated AC power 10 kW, PV 20 kW",
            source="search-knowledge",
        )
    )
    return gathered


def _ok() -> TurnOutput:
    return TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="This inverter is {fact:p4107.ac_power_kw} kW.",
                refs=["4107", "p4107.ac_power_kw"],
            ),
            CardsBlock(product_ids=[4107]),
        ],
    )


def test_a_grounded_turn_passes() -> None:
    assert check(_ok(), _facts()).ok


def test_forged_placeholder_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Power is {fact:p9999.ac_power_kw}.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("placeholder" in item for item in result.failures)


def test_forged_ref_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="See this model.", refs=["9999"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("ref" in item for item in result.failures)


def test_card_outside_qualified_is_refused() -> None:
    facts = _facts()
    facts.product_ids.add(6507)
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="A commercial inverter.", refs=["6507"]),
            CardsBlock(product_ids=[6507]),
        ],
    )
    result = check(output, facts)
    assert not result.ok
    assert any("qualified" in item for item in result.failures)


def test_card_not_in_text_refs_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="One match.", refs=["4107"]),
            CardsBlock(product_ids=[4107, 3556]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("not cited" in item for item in result.failures)


def test_action_with_foreign_product_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Add it.", refs=["4107"]),
            ActionBlock(name="add_to_draft", args={"product_id": 9999}),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("action" in item for item in result.failures)


def test_a_guest_inquiry_answered_with_the_mailbox_is_refused() -> None:
    """C2-anon-de: login_required must not hydrate into the team mailbox sentence."""
    from linker_genie.facts import collect
    from linker_genie.template import LOGIN_REQUIRED

    facts = collect("linker/inquiry-status", {"error": "login_required"})
    facts.add(
        Fact(
            id="handoff.sentence_de",
            value="Unser Team beantwortet das unter sales@de-linker.com.",
            source="handoff-team",
        )
    )
    mailbox = TurnOutput(
        language="de",
        blocks=[HandoffBlock(summary="{fact:handoff.sentence_de}")],
    )
    refused = check(mailbox, facts)
    assert not refused.ok
    assert any("login request" in item for item in refused.failures)

    login = TurnOutput(
        language="de",
        blocks=[TextBlock(text=LOGIN_REQUIRED["de"])],
    )
    assert check(login, facts).ok


def test_handoff_mixed_with_cards_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            HandoffBlock(summary="Ask sales@de-linker.com"),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("handoff" in item for item in result.failures)


def test_handoff_with_the_tool_sentence_passes_and_unknown_fails() -> None:
    facts = _facts()
    facts.add(
        Fact(
            id="handoff.sentence_en",
            value="Please write to our team at sales@de-linker.com.",
            source="handoff-team",
        )
    )
    output = TurnOutput(
        language="en",
        blocks=[HandoffBlock(summary="{fact:handoff.sentence_en}")],
    )
    assert check(output, facts).ok

    forged = TurnOutput(
        language="en",
        blocks=[HandoffBlock(summary="{fact:handoff.sentence_xx}")],
    )
    result = check(forged, facts)
    assert not result.ok
    assert any("placeholder" in item for item in result.failures)


def test_bare_digits_in_a_handoff_summary_are_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[HandoffBlock(summary="Delivery takes 5 days.")],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("numbers" in item for item in result.failures)


def test_bare_number_in_model_text_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="This inverter is 10 kW.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("numbers" in item for item in result.failures)


def test_model_names_are_not_counted_as_numbers() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "The GoodWe GW10K-ETA-G20 pairs with the H2-10K-T3 "
                    "and the ESA G2x modules."
                ),
                refs=["4107"],
            ),
            CardsBlock(product_ids=[4107]),
        ],
    )
    assert check(output, _facts()).ok


def test_cards_must_be_cited_even_when_the_text_names_no_product() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here are matching products.", refs=[]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("not cited" in item for item in result.failures)


def test_action_url_returned_by_a_tool_passes() -> None:
    facts = _facts()
    facts.add(
        Fact(
            id="size.configurator_url",
            value="https://de-linker.test/solution-configurator/?pv_kwp=10",
            source="size-hint",
        )
    )
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Open the configurator.", refs=["4107"]),
            ActionBlock(
                name="open_configurator",
                args={"url": "https://de-linker.test/solution-configurator/?pv_kwp=10"},
            ),
        ],
    )
    assert check(output, facts).ok


def test_action_url_not_from_the_tools_is_refused() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Open the configurator.", refs=["4107"]),
            ActionBlock(
                name="open_configurator",
                args={"url": "https://example.net/configurator"},
            ),
        ],
    )
    result = check(output, _facts())
    assert not result.ok
    assert any("url is not from this turn" in item for item in result.failures)


def test_number_not_in_cited_chunk_is_refused() -> None:
    facts = _facts()
    facts.add(Fact(id="p4107.made_up", value="99", source="selection-facts"))
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Secret rating {fact:p4107.made_up}.", refs=["4107", "c1"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = check(output, facts)
    assert not result.ok
    assert any("cited chunk" in item for item in result.failures)
