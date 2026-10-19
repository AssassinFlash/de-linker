"""The understanding layer's checks: documents as links, domain words, the route."""

import pytest

from linker_genie.cycle import run
from linker_genie.facts import Document, Fact, TurnFacts, collect
from linker_genie.ground import check
from linker_genie.hydrate import hydrate
from linker_genie.route import Call, Route
from linker_genie.schema import (
    ActionBlock,
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import DOCUMENTS, SIZING, fallback

PDF = "https://de-linker.com/wp-content/uploads/2026/03/SAJ-H2-user-manual.pdf"
PRODUCTS = Route(
    "products",
    (Call("linker/search-products", {"brand": "saj"}),),
    show_products=True,
    no_handoff=True,
)
SIZE = Route(
    "sizing",
    (Call("linker/size-hint", {}),),
    action="open_configurator",
    no_cards=True,
    no_handoff=True,
)
DOCS = Route("documents", no_handoff=True)


def _facts() -> TurnFacts:
    facts = TurnFacts()
    facts.product_ids = {4107, 4109}
    facts.qualified_ids = {4107, 4109}
    facts.chunk_ids = {"c1"}
    facts.add(Fact(id="c1", value="Manual · p.42", source="search-knowledge"))
    facts.documents["c1"] = Document(url=PDF, title="SAJ H2 user manual", page=42)
    facts.add(
        Fact(id="compat.document.0", value=f"{PDF} · p.7", source="check-compatibility")
    )
    facts.documents["compat.document.0"] = Document(
        url=PDF, title="SAJ H2 user manual", page=7
    )
    return facts


def _turn(*blocks: object) -> TurnOutput:
    return TurnOutput(language="en", blocks=list(blocks))  # type: ignore[arg-type]


def test_a_document_block_hydrates_into_a_link_with_its_page() -> None:
    output = _turn(
        TextBlock(text="The manual has the steps.", refs=["c1"]),
        DocumentBlock(ref="c1"),
    )
    assert check(output, _facts()).ok
    document = hydrate(output, _facts()).blocks[1]
    assert isinstance(document, DocumentBlock)
    assert document.label == "SAJ H2 user manual · p.\u00a042"
    assert document.url == PDF + "#page=42"


def test_a_german_document_link_says_seite() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Die Schritte stehen im Handbuch.", refs=["c1"]),
            DocumentBlock(ref="c1"),
        ],
    )
    document = hydrate(output, _facts()).blocks[1]
    assert isinstance(document, DocumentBlock)
    assert document.label == "SAJ H2 user manual · S.\u00a042"


def test_a_document_block_must_name_a_document_of_this_turn() -> None:
    result = check(
        _turn(TextBlock(text="See the manual."), DocumentBlock(ref="c9")), _facts()
    )
    assert "document 'c9' is not in this turn's tools" in result.failures


def test_the_model_may_not_write_the_link_itself() -> None:
    block = DocumentBlock(ref="c1", url="https://elsewhere.example/x.pdf")
    result = check(_turn(TextBlock(text="See the manual."), block), _facts())
    assert "a document block carries only its ref" in result.failures


@pytest.mark.parametrize(
    "text",
    [
        f"The manual is at {PDF}.",
        "See www.saj-electric.com for it.",
        "The conditions stand in {fact:compat.document.0}.",
    ],
)
def test_no_url_stands_in_the_text(text: str) -> None:
    result = check(_turn(TextBlock(text=text)), _facts())
    assert any("URL" in failure for failure in result.failures), result.failures


@pytest.mark.parametrize(
    "text",
    [
        "which is an article of its own",
        "Browse our catalogue.",
        "Add it to your cart.",
        "Der Artikel ist lieferbar.",
        "Im Katalog finden Sie mehr.",
        "Legen Sie es in den Warenkorb.",
    ],
)
def test_the_domain_words_are_kept(text: str) -> None:
    result = check(_turn(TextBlock(text=text)), _facts())
    assert any(failure.startswith("banned words") for failure in result.failures)


def test_a_product_word_turn_must_show_its_cards() -> None:
    greeting = _turn(TextBlock(text="Hello saj, welcome! How can I help?"))
    assert (
        "the customer named products: show the search result as cards"
        in check(greeting, _facts(), PRODUCTS).failures
    )
    shown = _turn(
        TextBlock(text="Here are SAJ products.", refs=["4109"]),
        CardsBlock(product_ids=[4109]),
    )
    assert check(shown, _facts(), PRODUCTS).ok


def test_a_sizing_turn_opens_the_configurator_without_cards() -> None:
    facts = _facts()
    facts.add(
        Fact(
            id="size.configurator_url",
            value="https://de-linker.com/configurator/?pv_kwp=8",
            source="size-hint",
        )
    )
    cards = _turn(
        TextBlock(text="These fit.", refs=["4107"]), CardsBlock(product_ids=[4107])
    )
    failures = check(cards, facts, SIZE).failures
    assert "a sizing turn shows no product cards" in failures
    assert "a sizing turn carries the open_configurator action" in failures
    good = _turn(
        TextBlock(text="The configurator sizes it."),
        ActionBlock(
            name="open_configurator",
            args={"url": "https://de-linker.com/configurator/?pv_kwp=8"},
        ),
    )
    assert check(good, facts, SIZE).ok


def test_a_document_question_is_not_handed_to_the_team() -> None:
    facts = _facts()
    facts.add(
        Fact(
            id="handoff.sentence_en",
            value="Write to sales@de-linker.com.",
            source="handoff-team",
        )
    )
    output = _turn(HandoffBlock(summary="{fact:handoff.sentence_en}"))
    assert (
        "a documents turn is not a question for the team"
        in check(output, facts, DOCS).failures
    )


def test_the_sizing_fallback_is_the_configurator() -> None:
    facts = TurnFacts()
    facts.add(
        Fact(
            id="size.configurator_url",
            value="https://de-linker.com/configurator/",
            source="size-hint",
        )
    )
    for language in ("en", "de"):
        output = fallback(facts, language, SIZE)
        assert [b.type for b in output.blocks] == ["text", "action"]
        assert output.blocks[0].text == SIZING[language]  # type: ignore[union-attr]


def test_the_document_fallback_links_the_documents() -> None:
    output = fallback(_facts(), "de", DOCS)
    assert output.blocks[0].text == DOCUMENTS["de"]  # type: ignore[union-attr]
    links = [b for b in output.blocks if isinstance(b, DocumentBlock)]
    assert links and all(b.url and b.label for b in links)


def test_search_knowledge_hits_become_documents() -> None:
    gathered = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "k7",
                    "doc_url": PDF,
                    "title": "SAJ H2 user manual",
                    "page": 12,
                    "section": "6.6",
                    "text": "Export limit",
                    "score": 0.8,
                }
            ]
        },
    )
    assert gathered.documents["k7"] == Document(PDF, "SAJ H2 user manual", 12)


def test_the_route_facts_survive_a_model_that_fails_twice() -> None:
    seed = _facts()

    def broken(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise ValueError("model output did not validate")

    request = TurnRequest.model_validate(
        {"conversation_id": "c", "messages": [{"role": "user", "content": "saj"}]}
    )
    result = run(request, broken, PRODUCTS, seed)
    assert result.fallback
    cards = [b for b in result.output.blocks if isinstance(b, CardsBlock)]
    assert cards and set(cards[0].product_ids) == {4107, 4109}


def test_get_product_documents_become_linkable() -> None:
    gathered = collect(
        "linker/get-product",
        {
            "product_id": 4106,
            "facts": {},
            "documents": [
                {"url": PDF, "title": "SAJ CHS2 Datasheet", "type": "datasheet"}
            ],
        },
    )
    assert gathered.documents["p4106.document.0"] == Document(
        PDF, "SAJ CHS2 Datasheet", None
    )


def test_a_handoff_turn_is_the_handoff_block_alone() -> None:
    facts = TurnFacts()
    facts.add(
        Fact(id="handoff.sentence_de", value="Unser Team …", source="handoff-team")
    )
    service = Route("service", (Call("linker/handoff-team", {}),))
    doubled = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="{fact:handoff.sentence_de}"),
            HandoffBlock(summary="{fact:handoff.sentence_de}"),
        ],
    )
    assert (
        "a handoff turn is the handoff block alone"
        in check(doubled, facts, service).failures
    )
    alone = TurnOutput(
        language="de", blocks=[HandoffBlock(summary="{fact:handoff.sentence_de}")]
    )
    assert check(alone, facts, service).ok


def test_datasheet_figures_become_facts_in_the_turns_language() -> None:
    payload = {
        "product_id": 4107,
        "facts": {"phase": 3},
        "figures": {
            "n_mppt": {"value": "3", "unit": ""},
            "max_pv_input_v": {"value": "1000", "unit": "V"},
            "topology": {"value": "Non-isolated", "value_de": "Trafolos", "unit": None},
            "phase": {"value": "Three-phase", "unit": ""},
        },
    }
    english = collect("linker/get-product", payload, "en")
    german = collect("linker/get-product", payload, "de")
    assert english.facts["p4107.n_mppt"].value == "3"
    assert english.facts["p4107.max_pv_input_v"].value == "1000 V"
    assert german.facts["p4107.topology"].value == "Trafolos"
    # The selection fact of the same key stays.
    assert english.facts["p4107.phase"].value == "3"
    text = "{fact:p4107.max_pv_input_v} and {fact:p4107.n_mppt} MPPT"
    from linker_genie.hydrate import fill

    assert fill(text, english) == "1000 V and 3 MPPT"


def test_the_fallback_shows_at_most_the_routes_six_cards() -> None:
    facts = TurnFacts()
    facts.product_ids = set(range(100, 112))
    facts.qualified_ids = set(range(100, 112))
    cards = [b for b in fallback(facts, "en").blocks if isinstance(b, CardsBlock)]
    assert len(cards[0].product_ids) == 6


def test_one_file_is_one_link_with_its_cited_pages() -> None:
    facts = _facts()
    other = "https://de-linker.com/wp-content/uploads/2026/03/H2-configuration.pdf"
    facts.documents["compat.document.1832.0"] = Document(
        other, "H2 Configuration Instructions", None
    )
    facts.documents["compat.document.2067.0"] = Document(
        other, "H2 Configuration Instructions", None
    )
    output = _turn(
        TextBlock(text="See the documents.", refs=["c1"]),
        DocumentBlock(ref="c1"),
        DocumentBlock(ref="compat.document.1832.0"),
        DocumentBlock(ref="compat.document.0"),
        DocumentBlock(ref="compat.document.2067.0"),
    )
    links = [b for b in hydrate(output, facts).blocks if isinstance(b, DocumentBlock)]
    assert [(b.label, b.url) for b in links] == [
        ("SAJ H2 user manual · pp.\u00a07, 42", PDF + "#page=7"),
        ("H2 Configuration Instructions", other),
    ]


def test_a_german_link_of_several_pages_keeps_s() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Siehe Handbuch.", refs=["c1"]),
            DocumentBlock(ref="c1"),
            DocumentBlock(ref="compat.document.0"),
        ],
    )
    (link,) = [
        b for b in hydrate(output, _facts()).blocks if isinstance(b, DocumentBlock)
    ]
    assert link.label == "SAJ H2 user manual · S.\u00a07, 42"


def test_the_service_writes_the_configurator_link() -> None:
    facts = _facts()
    url = "https://de-linker.com/solution-configurator/?pv_kwp=8&annual_kwh=6000"
    facts.add(Fact(id="size.configurator_url", value=url, source="size-hint"))
    for args in ({}, {"url": "https://de-linker.com/solution-configurator/?pv=8"}):
        output = _turn(
            TextBlock(text="The configurator sizes it."),
            ActionBlock(name="open_configurator", args=args),
        )
        assert check(output, facts, SIZE).ok
        action = hydrate(output, facts).blocks[1]
        assert isinstance(action, ActionBlock)
        assert action.args["url"] == url


def test_without_size_hint_an_invented_configurator_link_is_refused() -> None:
    output = _turn(
        TextBlock(text="Open it."),
        ActionBlock(
            name="open_configurator", args={"url": "https://elsewhere.example/"}
        ),
    )
    assert (
        "action open_configurator url is not from this turn's tools"
        in check(output, _facts()).failures
    )


@pytest.mark.parametrize(
    "text",
    [
        "The CB2-100.3-HV5 stands on the floor.",
        "Der HS3-5K-T2-W/G-PX ist dreiphasig.",
        "The GW8.3-BAT-D-G21 module fits.",
    ],
)
def test_a_model_code_written_whole_is_no_number(text: str) -> None:
    assert check(_turn(TextBlock(text=text)), _facts()).ok


@pytest.mark.parametrize(
    "text",
    ["It is a 3-phase unit.", "Choose 10-20 modules.", "It holds 100.3 of energy."],
)
def test_numbers_beside_codes_are_still_refused(text: str) -> None:
    result = check(_turn(TextBlock(text=text)), _facts())
    assert any(f.startswith("model text contains numbers") for f in result.failures)


def test_a_document_of_this_turn_may_be_cited_in_refs() -> None:
    output = _turn(TextBlock(text="See the datasheet.", refs=["compat.document.0"]))
    assert check(output, _facts()).ok


def test_the_shipped_company_turn_is_the_mailbox_sentence_and_the_card() -> None:
    from linker_genie.ground import shipped

    handoff = {"type": "handoff", "summary": "Our team will answer that at x."}
    card = {"type": "contact", "reason": "service"}
    assert shipped({"blocks": [handoff, card]}, Route("service"), "service") == []
    assert shipped({"blocks": [handoff]}, Route("service"), None) == []
    assert shipped(
        {"blocks": [handoff, {"type": "cards", "product_ids": [1]}, card]},
        Route("service"),
        "service",
    )


def test_the_extreme_fallback_names_one_product_in_both_languages() -> None:
    facts = TurnFacts()
    facts.product_ids = {6518}
    facts.qualified_ids = {6518}
    facts.add(
        Fact(id="search.extreme_product_id", value="6518", source="search-products")
    )
    facts.add(
        Fact(id="search.extreme_model", value="GW30K-ETA-G20", source="search-products")
    )
    expected = {
        "en": "The GW30K-ETA-G20 meets the limit you named.",
        "de": "Das Modell GW30K-ETA-G20 erfüllt die genannte Grenze.",
    }
    for locale, sentence in expected.items():
        output = fallback(facts, locale)
        text, cards = output.blocks
        assert isinstance(text, TextBlock)
        assert isinstance(cards, CardsBlock)
        assert text.text == sentence
        assert text.refs == ["6518"]
        assert cards.product_ids == [6518]
        assert check(output, facts).ok


def test_a_hidden_price_keeps_the_ordinary_fallback() -> None:
    facts = TurnFacts()
    facts.product_ids = {2068, 2069}
    facts.qualified_ids = {2068, 2069}
    facts.add(
        Fact(id="search.extreme_price_hidden", value="1", source="search-products")
    )
    output = fallback(facts, "en")
    text, cards = output.blocks[0], output.blocks[1]
    assert isinstance(text, TextBlock)
    assert isinstance(cards, CardsBlock)
    assert text.text == "Here are matching products from our range."
    assert cards.product_ids == [2068, 2069]


def test_the_contact_card_is_the_offer_the_service_decided() -> None:
    from linker_genie.ground import shipped

    text = {"type": "text", "text": "An answer.", "refs": []}
    card = {"type": "contact", "reason": "repeat"}
    assert shipped({"blocks": [text, card]}, Route("model"), "repeat") == []
    # No offer, no card; one card, last, of the decided reason.
    assert shipped({"blocks": [text, card]}, Route("model"), None)
    assert shipped({"blocks": [card, text]}, Route("model"), "repeat")
    assert shipped({"blocks": [text, card, card]}, Route("model"), "repeat")
    assert shipped({"blocks": [text, card]}, Route("model"), "dissatisfied")
    assert shipped({"blocks": [text]}, Route("model"), "repeat")
