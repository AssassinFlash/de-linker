"""Five anchoring checks: injected failures are all refused."""

from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import bare_numbers, catalogue_name_phrases, check
from linker_genie.route import NamedModel, Route
from linker_genie.ground import check
from linker_genie.jev import Reading
from linker_genie.lexicon import Match
from linker_genie.route import NamedModel, Route, Subject, plan
from linker_genie.schema import (
    ActionBlock,
    CardsBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)
from linker_genie.template import fallback, german_is_clean


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


_OCEAN_TITLE = "EcoFlow OCEAN 2 HD-P1-3K-S2 (3 kW single-phase power module)"


def _ocean_facts() -> TurnFacts:
    facts = _facts()
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {},
            "ok": True,
            "result": {
                "qualified": [
                    {
                        "product_id": 4107,
                        "title": _OCEAN_TITLE,
                        "facts": {"ac_power_kw": 10},
                    }
                ]
            },
        }
    )
    return facts


def _ocean(text: str) -> TurnOutput:
    return TurnOutput(
        language="en",
        blocks=[
            TextBlock(text=text, refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )


def test_a_series_designator_in_a_returned_title_is_not_a_number() -> None:
    facts = _ocean_facts()
    assert check(_ocean("The EcoFlow OCEAN 2 is the single-phase hybrid."), facts).ok
    assert check(_ocean("The EcoFlow ocean 2 is the single-phase hybrid."), facts).ok


def test_a_power_beside_a_series_name_is_still_a_number() -> None:
    result = check(_ocean("The EcoFlow OCEAN 2 is rated 10 kW."), _ocean_facts())
    assert result.failures == ("model text contains numbers ['10']",)


def test_two_years_is_still_a_number_when_the_title_names_ocean_2() -> None:
    result = check(_ocean("The EcoFlow OCEAN 2 ships in 2 years."), _ocean_facts())
    assert not result.ok
    assert "['2']" in result.reason


def test_a_decimal_beside_the_series_name_is_still_a_number() -> None:
    result = check(_ocean("The warranty on the OCEAN 2 is 2.0 years."), _ocean_facts())
    assert not result.ok
    assert "2.0" in result.reason


def test_ocean_2_without_the_title_in_the_tools_is_a_number() -> None:
    result = check(_ocean("The EcoFlow OCEAN 2 is the single-phase hybrid."), _facts())
    assert not result.ok
    assert "['2']" in result.reason


def test_ocean_20_is_not_swallowed_by_the_ocean_2_title() -> None:
    result = check(_ocean("The OCEAN 20 is a different machine."), _ocean_facts())
    assert not result.ok
    assert "20" in result.reason


def test_catalogue_name_phrases_read_the_head_before_the_parenthesis() -> None:
    calls = [
        {
            "result": {
                "qualified": [{"product_id": 4107, "title": _OCEAN_TITLE}],
                "hits": [
                    {
                        "chunk_id": "c1",
                        "title": "GoodWe ESA Serie 5–30 kW Benutzerhandbuch",
                    }
                ],
                "documents": [
                    {"url": "https://example.test/a.pdf", "title": "OCEAN 2 datasheet"}
                ],
                "faq": [{"title": "Step 2", "question": "Step 2"}],
            }
        }
    ]
    assert catalogue_name_phrases(calls) == ("OCEAN 2", "Serie 5")
    assert bare_numbers("rated 10 kW", catalogue_name_phrases(calls)) == ["10"]
    assert bare_numbers("the OCEAN 2", catalogue_name_phrases(calls)) == []


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


def test_cheapest_over_written_models_names_the_codes_and_no_price() -> None:
    # #339 registration (#384). The aggregate carries extreme=cheapest, so a
    # hidden price is recorded. The answer names both codes and no price.
    messages = (
        ("en", "Which is the cheapest inverter, HS3-5K-T2 or HS3-12K-T2?"),
        (
            "de",
            "Welcher ist der günstigste Wechselrichter, HS3-5K-T2 oder HS3-12K-T2?",
        ),
    )
    matches = [
        Match("model", "HS3-5K-T2", "HS3-5K-T2", frozenset({2198}), "HS3-5K-T2"),
        Match("model", "HS3-12K-T2", "HS3-12K-T2", frozenset({1185}), "HS3-12K-T2"),
        Match("category", "inverters", "inverters", frozenset(), "inverter"),
    ]
    reading = Reading("find_products", 0.95, 0.1, 0.05, 0.2, 2.6, 0.0)
    shapes: list[list[str]] = []
    for lang, message in messages:
        route = plan(message, matches, reading, Subject((), {}, {}), lang)
        assert route.calls[0].arguments["extreme"] == "cheapest"
        facts = _facts()
        facts.product_ids = {2198, 1185}
        facts.qualified_ids = {2198, 1185}
        facts.add(
            Fact(id="search.extreme_price_hidden", value="1", source="search-products")
        )
        for code, product_id in (("HS3-5K-T2", 2198), ("HS3-12K-T2", 1185)):
            facts.tool_calls.append(
                {
                    "name": "linker/search-products",
                    "arguments": {"text": code, "lang": lang, "limit": 6},
                    "ok": True,
                    "result": {"qualified": [{"product_id": product_id}]},
                }
            )
        output = fallback(facts, lang, route)
        texts = [block.text for block in output.blocks if isinstance(block, TextBlock)]
        joined = " ".join(texts)
        assert "HS3-5K-T2" in joined and "HS3-12K-T2" in joined
        assert "€" not in joined and "$" not in joined and "{fact:" not in joined
        for text in texts:
            folded = text.casefold()
            if "HS3-" in text:
                assert "cheapest" not in folded
                assert "günstig" not in folded
                assert "guenstig" not in folded
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert len(cards) == 1 and cards[0].product_ids == [2198, 1185]
        assert check(output, facts, route).ok
        if lang == "de":
            assert german_is_clean(joined)
            price = "Freigegebene Partnerkonten sehen die Nettopreise."
            named = "Sie haben HS3-5K-T2, HS3-12K-T2 genannt."
        else:
            price = "Approved partner accounts see net prices."
            named = "You named HS3-5K-T2, HS3-12K-T2."
        assert price in texts
        assert named in texts
        # The price sentence alone, with the cards, still omits the codes.
        # This fails if the hidden arm of the naming condition is removed:
        # known codes beside a hidden price would no longer have to be named.
        omitted = TurnOutput(
            language=lang,  # type: ignore[arg-type]
            blocks=[
                TextBlock(text=price, refs=["2198", "1185"]),
                CardsBlock(product_ids=[2198, 1185]),
            ],
        )
        refused_names = check(omitted, facts, route)
        assert any(
            "name HS3-5K-T2 as well as the extreme result" in failure
            for failure in refused_names.failures
        )
        assert any(
            "name HS3-12K-T2 as well as the extreme result" in failure
            for failure in refused_names.failures
        )
        shapes.append([type(block).__name__ for block in output.blocks])
        claim = (
            "The cheapest one is the HS3-5K-T2."
            if lang == "en"
            else "Das günstigste Modell ist das HS3-5K-T2."
        )
        refused = check(
            TurnOutput(language=lang, blocks=[TextBlock(text=claim)]),  # type: ignore[arg-type]
            facts,
            route,
        )
        assert any("cheapest" in failure for failure in refused.failures)
    assert shapes[0] == shapes[1]


def test_a_visible_price_extreme_names_the_codes_on_the_winner_card() -> None:
    # The aggregate is applied, so grounding allows exactly the winner card.
    # The codes written beside that question are still named. EN and DE use
    # the service sentences, not a paraphrase.
    messages = (
        (
            "en",
            "Which is the cheapest inverter, HS3-5K-T2 or HS3-12K-T2?",
            "The GW30K-ETA-G20 meets the limit you named.",
            "You named HS3-5K-T2, HS3-12K-T2.",
        ),
        (
            "de",
            "Welcher ist der günstigste Wechselrichter, HS3-5K-T2 oder HS3-12K-T2?",
            "Das Modell GW30K-ETA-G20 erfüllt die genannte Grenze.",
            "Sie haben HS3-5K-T2, HS3-12K-T2 genannt.",
        ),
    )
    matches = [
        Match("model", "HS3-5K-T2", "HS3-5K-T2", frozenset({2198}), "HS3-5K-T2"),
        Match("model", "HS3-12K-T2", "HS3-12K-T2", frozenset({1185}), "HS3-12K-T2"),
        Match("category", "inverters", "inverters", frozenset(), "inverter"),
    ]
    reading = Reading("find_products", 0.95, 0.1, 0.05, 0.2, 2.6, 0.0)
    shapes: list[list[str]] = []
    for lang, message, winner_sentence, named_sentence in messages:
        route = plan(message, matches, reading, Subject((), {}, {}), lang)
        assert "show each found product" not in route.hint
        assert "show only the winner card" in route.hint
        facts = _extreme_facts()
        facts.product_ids.update({2198, 1185})
        facts.qualified_ids.update({2198, 1185})
        for code, product_id in (("HS3-5K-T2", 2198), ("HS3-12K-T2", 1185)):
            facts.tool_calls.append(
                {
                    "name": "linker/search-products",
                    "arguments": {"text": code, "lang": lang, "limit": 6},
                    "ok": True,
                    "result": {"qualified": [{"product_id": product_id}]},
                }
            )
        output = fallback(facts, lang, route)
        texts = [block.text for block in output.blocks if isinstance(block, TextBlock)]
        joined = " ".join(texts)
        assert winner_sentence in joined
        assert named_sentence in joined
        assert "€" not in joined and "$" not in joined and "{fact:" not in joined
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert len(cards) == 1 and cards[0].product_ids == [6518]
        assert check(output, facts, route).ok
        if lang == "de":
            assert german_is_clean(joined)
        extra = _named(
            f"{winner_sentence} {named_sentence}",
            [6518, 2198, 1185],
        )
        refused = check(extra, facts, route)
        assert any("only that card" in failure for failure in refused.failures)
        shapes.append([type(block).__name__ for block in output.blocks])
    assert shapes[0] == shapes[1]


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
