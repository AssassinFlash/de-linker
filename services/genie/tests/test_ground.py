"""Five anchoring checks: injected failures are all refused."""

from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import check
from linker_genie.route import NamedModel, Route
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


def test_a_document_figure_not_in_its_chunk_is_refused() -> None:
    facts = _facts()
    facts.add(Fact(id="c1.n9", value="99", source="search-knowledge"))
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Secret rating {fact:c1.n9} kW.", refs=["c1"])],
    )
    result = check(output, facts)
    assert not result.ok
    assert any("cited chunk" in item for item in result.failures)


def test_a_document_figure_from_its_chunk_passes() -> None:
    facts = _facts()
    facts.add(Fact(id="c1.n1", value="10 kW", source="search-knowledge"))
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Rated at {fact:c1.n1}.", refs=["c1"])],
    )
    assert check(output, facts).ok


def test_product_facts_are_not_held_to_the_chunk_texts() -> None:
    facts = _facts()
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="Rated {fact:p4107.ac_power_kw}, see the manual.",
                refs=["4107", "c1"],
            ),
            CardsBlock(product_ids=[4107]),
        ],
    )
    assert check(output, facts).ok


def test_a_model_code_with_a_decimal_segment_is_not_a_bare_number() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="The CB2-100.3-HV5 stands upright.", refs=["c1"])],
    )
    assert check(output, _facts()).ok


def _extreme_facts() -> TurnFacts:
    facts = _facts()
    facts.product_ids.add(6518)
    facts.qualified_ids.add(6518)
    facts.add(
        Fact(id="search.extreme_product_id", value="6518", source="search-products")
    )
    facts.add(
        Fact(id="search.extreme_model", value="GW30K-ETA-G20", source="search-products")
    )
    return facts


def _named(text: str, product_ids: list[int]) -> TurnOutput:
    return TurnOutput(
        language="en",
        blocks=[
            TextBlock(text=text, refs=[str(product_id) for product_id in product_ids]),
            CardsBlock(product_ids=product_ids),
        ],
    )


def test_an_applied_extreme_names_that_model_on_one_card() -> None:
    output = _named("The GW30K-ETA-G20 meets the limit you named.", [6518])
    assert check(output, _extreme_facts()).ok


def test_an_extreme_with_another_card_is_refused() -> None:
    facts = _extreme_facts()
    facts.product_ids.add(6506)
    facts.qualified_ids.add(6506)
    output = _named("The GW30K-ETA-G20 meets the limit you named.", [6506])
    result = check(output, facts)
    assert any("only that card" in failure for failure in result.failures)


def test_an_extreme_card_without_the_model_code_is_refused() -> None:
    output = _named("This product meets the limit you named.", [6518])
    result = check(output, _extreme_facts())
    assert any("GW30K-ETA-G20" in failure for failure in result.failures)


def test_a_hidden_price_names_no_cheapest_model() -> None:
    facts = _facts()
    facts.add(
        Fact(id="search.extreme_price_hidden", value="1", source="search-products")
    )
    named = TurnOutput(
        language="en",
        blocks=[TextBlock(text="The cheapest one is the GW75K-ET-G10.")],
    )
    german = TurnOutput(
        language="de",
        blocks=[TextBlock(text="Das günstigste Modell ist das GW75K-ET-G10.")],
    )
    plain = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "I cannot name a cheapest product. "
                    "Approved partner accounts see net prices."
                )
            )
        ],
    )
    assert any("cheapest" in failure for failure in check(named, facts).failures)
    assert any("cheapest" in failure for failure in check(german, facts).failures)
    assert check(plain, facts).ok


def test_an_applied_extreme_is_the_only_card_beside_other_named_models() -> None:
    # The winner card satisfies the extreme. The other searched model is not
    # also required as a card. An absence claim for it is still refused, and
    # a code the route did not search must still be called not searched.
    route = Route(
        "products",
        show_products=True,
        no_handoff=True,
        named_models=(
            NamedModel(code="HS3-5K-T2", product_ids=(2198,), searched=True),
            NamedModel(code="GW30K-ETA-G20", product_ids=(6518,), searched=True),
            NamedModel(code="HS3-12K-T2", product_ids=(1185,), searched=False),
        ),
    )
    facts = _extreme_facts()
    facts.product_ids.add(2198)
    facts.qualified_ids.add(2198)
    winner = _named("The GW30K-ETA-G20 meets the limit you named.", [6518])
    absent = _named(
        "The GW30K-ETA-G20 meets the limit you named. HS3-5K-T2 has no entry.",
        [6518],
    )
    missed = _named(
        "The GW30K-ETA-G20 meets the limit you named. HS3-12K-T2 was not searched.",
        [6518],
    )
    assert check(missed, facts, route).ok
    assert any(
        "no entry" in failure for failure in check(absent, facts, route).failures
    )
    assert any(
        "not searched" in failure for failure in check(winner, facts, route).failures
    )
