"""Retry once, then the deterministic template."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from pydantic import TypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.agent import make_generate
from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts, collect, merge
from linker_genie.route import Route
from linker_genie.schema import (
    AskBlock,
    Block,
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    LOGIN_REQUIRED,
    NO_MATCH_DE,
    NO_MATCH_EN,
    fallback,
    german_is_clean,
)
from linker_genie.timing import Timing


def _request() -> TurnRequest:
    return TurnRequest(
        conversation_id="c1",
        messages=[TurnMessage(role="user", content="10 kWp three-phase home")],
        locale="en",
    )


def _facts() -> TurnFacts:
    gathered = TurnFacts()
    gathered.product_ids = {4107}
    gathered.qualified_ids = {4107}
    gathered.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    gathered.unknown_fields = ["backup"]
    return gathered


def _qualified_table(value: str, condition: str) -> TurnFacts:
    """Synthetic projection for exercising the post-hydration seal."""
    hit = {
        "chunk_id": "sample-p2",
        "doc_url": "https://example.test/sample.pdf",
        "title": "Sample",
        "page": 2,
        "product_ids": [1],
        "text": f"| Reading | [n1={value}] |\n{condition} (p. 3)",
        "figures": {"sample-p2.n1": value},
        "qualification_required": True,
        "qualifications": [
            {"quote": condition, "page": 3, "chunk_id": "sample-p3", "lang": "en"}
        ],
    }
    return collect("linker/search-knowledge", {"hits": [hit]})


@pytest.mark.parametrize("language", ["en", "de"])
def test_seal_preserves_a_qualified_figure_and_numbers_in_its_original_condition(
    language: Locale,
) -> None:
    condition = "*6: This synthetic condition applies above 30.5 A."
    facts = _qualified_table("125.7 A", condition)
    request = TurnRequest(
        conversation_id="sample",
        messages=[
            TurnMessage(
                role="user",
                content="What is the rated current?"
                if language == "en"
                else "Wie hoch ist der Nennstrom?",
            )
        ],
        locale=language,
    )
    output = TurnOutput(
        language=language,
        blocks=[
            TextBlock(
                text="The current is {fact:sample-p2.n1}."
                if language == "en"
                else "Der Strom beträgt {fact:sample-p2.n1}."
            )
        ],
    )

    result = run(request, lambda _request, _retry: (output, facts), Route("products"))

    assert result.grounded and not result.fallback
    answer = result.output.blocks[0]
    assert isinstance(answer, TextBlock)
    assert "125.7 A" in answer.text
    assert condition.split(": ", 1)[1] in answer.text
    if language == "de":
        assert "Herstellerbedingung (englisches Original):" in answer.text
    assert "\ue000" not in answer.text and "\ue001" not in answer.text
    links = [
        block.url for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert links == [
        "https://example.test/sample.pdf#page=2",
        "https://example.test/sample.pdf#page=3",
    ]


def test_seal_protects_the_qualified_occurrence_not_an_equal_other_fact() -> None:
    qualified = _qualified_table("5", "*6: This synthetic condition applies.")
    other = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "other-p2",
                    "doc_url": "https://example.test/other.pdf",
                    "title": "Other model",
                    "page": 2,
                    "product_ids": [2],
                    "text": "| Power | [n1=5 kW] |",
                    "figures": {"other-p2.n1": "5 kW"},
                }
            ]
        },
    )
    request = TurnRequest(
        conversation_id="sample",
        messages=[TurnMessage(role="user", content="What is the reading?")],
        locale="en",
    )
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="The reading is {fact:sample-p2.n1}. The power is {fact:other-p2.n1}."
            )
        ],
    )

    result = run(
        request,
        lambda _request, _retry: (output, merge([qualified, other])),
        Route("products"),
    )

    assert result.grounded and not result.fallback
    answer = result.output.blocks[0]
    assert isinstance(answer, TextBlock)
    assert "reading is 5" in answer.text
    assert "5 kW" not in answer.text
    assert "This synthetic condition applies." in answer.text


def test_qualified_digit_does_not_protect_an_unrelated_regulation_tail() -> None:
    qualified = _qualified_table("5", "*6: This synthetic condition applies.")
    other = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "other-p2",
                    "doc_url": "https://example.test/other.pdf",
                    "title": "Other model",
                    "page": 2,
                    "product_ids": [2],
                    "text": "VDE-AR-N [n1=4105]",
                    "figures": {"other-p2.n1": "4105"},
                }
            ]
        },
    )
    request = TurnRequest(
        conversation_id="sample",
        messages=[TurnMessage(role="user", content="What does the datasheet say?")],
        locale="en",
    )
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="The reading is {fact:sample-p2.n1}. The number is {fact:other-p2.n1}."
            )
        ],
    )

    result = run(
        request,
        lambda _request, _retry: (output, merge([qualified, other])),
        Route("documents"),
    )

    assert result.grounded and not result.fallback
    answer = result.output.blocks[0]
    assert isinstance(answer, TextBlock)
    assert "reading is 5" in answer.text
    assert "4105" not in answer.text
    assert "This synthetic condition applies." in answer.text


@pytest.mark.parametrize(
    "question", ["What is the usable capacity?", "What is the clearance?"]
)
def test_seal_cannot_append_an_uncited_or_conditioned_number_from_the_blob(
    question: str,
) -> None:
    facts = _qualified_table("260 kWh", "*6: This synthetic condition applies.")
    other = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "other-p2",
                    "doc_url": "https://example.test/other.pdf",
                    "title": "Other model",
                    "page": 2,
                    "text": "| Nominal Capacity (kWh) | [n1=260 kWh] |\n| Clearance (mm) | [n2=500 mm] |",
                    "figures": {"other-p2.n1": "260 kWh", "other-p2.n2": "500 mm"},
                }
            ]
        },
    )
    request = TurnRequest(
        conversation_id="sample",
        messages=[TurnMessage(role="user", content=question)],
        locale="en",
    )
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Please see the document.", refs=["sample-p2"])],
    )

    result = run(
        request,
        lambda _request, _retry: (output, merge([facts, other])),
        Route("documents"),
    )

    assert result.grounded and not result.fallback
    answer = result.output.blocks[0]
    assert isinstance(answer, TextBlock)
    assert "260" not in answer.text
    assert "500" not in answer.text
    assert "do not state a usable capacity" not in answer.text


def test_a_grounded_turn_is_hydrated_without_fallback() -> None:
    facts = _facts()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="This inverter is {fact:p4107.ac_power_kw} kW.",
                        refs=["4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    result = run(_request(), generate)
    assert result.fallback is False
    assert result.grounded is True
    assert result.attempts == 1
    assert "10 kW" in result.output.blocks[0].text  # type: ignore[union-attr]


def test_a_number_only_miss_is_stripped_and_stays_grounded() -> None:
    """A miss that is only a bare number is corrected, not retried or templated.

    A model retry rewrites the answer and can drop the cards. The baseline floor
    treats fallback as no answer. The question's 10 does not license the digit:
    correction runs before hydration, and a turn with no route is not sealed back.
    """
    facts = _facts()
    attempts: list[str | None] = []

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        attempts.append(retry)
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="This inverter is 10 kW.", refs=["4107"]),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    result = run(_request(), generate)
    assert len(attempts) == 1
    assert attempts[0] is None
    assert result.fallback is False
    assert result.grounded is True
    assert result.attempts == 1
    assert result.retried
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == "This inverter is"
    assert [block.type for block in result.output.blocks] == ["text", "cards"]


def test_a_regulation_number_survives_the_number_strip() -> None:
    """`EnWG 14a Abs. 1` and `VDE-AR-N 4105` are the rule, not a measurement.

    `10 kW` is still stripped. The turn stays grounded (#443).
    """
    facts = _facts()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text=(
                            "The code is EnWG 14a Abs. 1 and VDE-AR-N 4105. "
                            "This inverter is 10 kW."
                        ),
                        refs=["4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    result = run(_request(), generate)
    assert result.fallback is False
    assert result.grounded is True
    assert result.attempts == 1
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert "EnWG 14a Abs. 1" in text.text
    assert "VDE-AR-N 4105" in text.text
    assert "10 kW" not in text.text


def test_a_number_strip_that_leaves_the_wrong_language_retries_in_that_language() -> (
    None
):
    """A language miss after the strip is a language re-ask, not a number miss."""
    facts = _facts()
    attempts: list[str | None] = []
    request = TurnRequest(
        conversation_id="c1",
        messages=[TurnMessage(role="user", content="Welche Batterien passen?")],
        locale="de",
    )

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        attempts.append(retry)
        if retry is None:
            return (
                TurnOutput(
                    language="en",
                    blocks=[
                        TextBlock(text="This inverter is 10 kW.", refs=["4107"]),
                        CardsBlock(product_ids=[4107]),
                    ],
                ),
                facts,
            )
        return (
            TurnOutput(
                language="de",
                blocks=[
                    TextBlock(
                        text="Dieser Wechselrichter ist geeignet.", refs=["4107"]
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    result = run(request, generate)
    assert attempts[0] is None
    assert attempts[1] is not None
    assert attempts[1].startswith("answer in German")
    assert "numbers" not in attempts[1]
    assert result.fallback is False
    assert result.grounded is True
    assert result.attempts == 2
    shipped = result.output.blocks[0]
    assert isinstance(shipped, TextBlock)
    assert shipped.text == "Dieser Wechselrichter ist geeignet."


def test_a_copied_menu_label_does_not_send_the_german_answer_to_the_template() -> None:
    """The chunk's own menu phrase does not make a German answer English (#443)."""
    facts = TurnFacts()
    facts.add(
        Fact(
            id="770ccafa080c-p26-ea46e782.text",
            value="Please select the type",
            source="search-knowledge",
        )
    )
    attempts: list[str | None] = []
    request = TurnRequest(
        conversation_id="c1",
        messages=[
            TurnMessage(role="user", content="Wie stellt man das Exportlimit ein?")
        ],
        locale="de",
    )

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        attempts.append(retry)
        return (
            TurnOutput(
                language="de",
                blocks=[
                    TextBlock(
                        text=(
                            "Öffnen Sie Please select the type und speichern Sie "
                            "die Einstellung."
                        )
                    )
                ],
            ),
            facts,
        )

    result = run(request, generate)
    assert attempts == [None]
    assert result.fallback is False
    assert result.grounded is True
    shipped = result.output.blocks[0]
    assert isinstance(shipped, TextBlock)
    assert "Please select the type" in shipped.text


def test_invalid_structure_counts_as_a_failed_attempt() -> None:
    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise ValueError("not a TurnOutput")

    result = run(_request(), generate)
    assert result.fallback is True
    assert result.output.blocks[0].type in {"handoff", "text", "cards"}


def test_an_ability_that_stays_dead_falls_back_to_the_degradation() -> None:
    """The storm, as the cycle sees it: every ability call of both attempts
    fails (AbilityError after the client's retries), so the turn ships the
    plain degraded handoff - never an exception out of the service."""

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise AbilityError(
            "linker/search-products could not be reached: boom", fatal=True
        )

    result = run(_request(), generate)

    assert result.fallback is True
    assert result.grounded is False
    assert result.attempts == 2
    handoff = result.output.blocks[0]
    assert isinstance(handoff, HandoffBlock)
    assert handoff.summary.startswith("I could not answer this time.")


def test_template_lists_qualified_cards_and_one_ask() -> None:
    output = fallback(_facts(), "en")
    types = [block.type for block in output.blocks]
    assert types.count("ask") == 1
    cards = next(block for block in output.blocks if isinstance(block, CardsBlock))
    assert cards.product_ids == [4107]


def test_template_handoff_uses_the_tool_sentence_when_present() -> None:
    facts = TurnFacts()
    facts.add(
        Fact(
            id="handoff.sentence_de",
            value="Bitte schreiben Sie an unser Team: vertrieb@de-linker.com.",
            source="handoff-team",
        )
    )

    output = fallback(facts, "de")

    handoff = output.blocks[0]
    assert isinstance(handoff, HandoffBlock)
    assert (
        handoff.summary == "Bitte schreiben Sie an unser Team: vertrieb@de-linker.com."
    )


def test_template_handoff_without_the_tool_declares_the_degradation() -> None:
    """Nothing citable, and handoff-team did not run: the degraded sentence.
    The same empty facts with the login fact outrank that sentence."""
    english = fallback(TurnFacts(), "en")
    german = fallback(TurnFacts(), "de")

    english_handoff = english.blocks[0]
    german_handoff = german.blocks[0]
    assert isinstance(english_handoff, HandoffBlock)
    assert isinstance(german_handoff, HandoffBlock)
    assert english_handoff.summary == (
        "I could not answer this time. Please try again in a moment, "
        "or write to our team."
    )
    assert german_handoff.summary == (
        "Ich konnte Ihre Frage diesmal nicht beantworten. Bitte versuchen Sie "
        "es gleich noch einmal, oder wenden Sie sich an unser Team."
    )
    assert german_is_clean(german_handoff.summary)
    assert " the " not in f" {german_handoff.summary.lower()} "

    # Login fact on otherwise empty facts: the login sentence, not DEGRADED,
    # even though handoff-team did not run either.
    guest = _guest_inquiry()
    login = fallback(guest, "de")
    assert isinstance(login.blocks[0], TextBlock)
    assert login.blocks[0].text == LOGIN_REQUIRED["de"]
    assert login.blocks[0].text != DEGRADED["de"]


def _guest_inquiry() -> TurnFacts:
    """What inquiry-status returns for an anonymous caller (facts.py:252)."""
    return collect("linker/inquiry-status", {"error": "login_required"})


def _guest_request(locale: str) -> TurnRequest:
    return TurnRequest(
        conversation_id="c-guest",
        locale=locale,  # type: ignore[arg-type]
        messages=[
            TurnMessage(role="user", content="Wo steht meine Proforma?")
            if locale == "de"
            else TurnMessage(role="user", content="Where does my Proforma stand?")
        ],
        page_context={"type": "account"},  # type: ignore[arg-type]
    )


def test_anonymous_german_proforma_falls_back_to_the_login_request() -> None:
    """C2-anon-de: grounding refused the mailbox sentence; the template must
    ask the guest to log in, in German, and must not ship the team mailbox."""
    facts = _guest_inquiry()
    facts.add(
        Fact(
            id="handoff.sentence_de",
            value="Unser Team beantwortet das unter sales@de-linker.com.",
            source="handoff-team",
        )
    )

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="de",
                blocks=[
                    HandoffBlock(summary="{fact:handoff.sentence_de}"),
                ],
            ),
            facts,
        )

    result = run(_guest_request("de"), generate)

    assert result.fallback is True
    assert result.grounded is False
    assert len(result.output.blocks) == 1
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert block.text == LOGIN_REQUIRED["de"]
    assert "melden Sie sich in Ihrem Konto an" in block.text
    assert "sales@" not in block.text
    assert "@" not in block.text
    assert german_is_clean(block.text)
    assert result.output.language == "de"


def test_fallback_after_grounding_stays_inside_the_protocol_set() -> None:
    """C2-fallback: a refused product turn ships qualified cards inside the
    allowed set, cited by the text; a German line carries no English fragment.
    Nothing citable and handoff-team did not run: the degraded sentence of
    that language. The mailbox sentence ships only when that tool's sentence
    is a fact of the turn (test_template_handoff_uses_the_tool_sentence_when_present)."""
    allowed = {4107, 3556}
    facts = TurnFacts()
    facts.product_ids = set(allowed)
    facts.qualified_ids = set(allowed)
    facts.unknown_fields = ["phase"]

    german_cards = fallback(facts, "de")
    offered = {
        product_id
        for block in german_cards.blocks
        if isinstance(block, CardsBlock)
        for product_id in block.product_ids
    }
    assert offered
    assert offered <= allowed
    text = next(block for block in german_cards.blocks if isinstance(block, TextBlock))
    # The template cites a card as p<id> (template.py); the shell and the
    # grounding check both read that form.
    assert set(text.refs) >= {f"p{product_id}" for product_id in offered}
    assert german_cards.language == "de"
    for block in german_cards.blocks:
        rendered = getattr(block, "text", None) or ""
        options = getattr(block, "options", None) or []
        for line in [rendered, *options]:
            if line:
                assert german_is_clean(line), line
    assert not any(block.type == "handoff" for block in german_cards.blocks)

    german_empty = fallback(TurnFacts(), "de")
    empty = german_empty.blocks[0]
    assert isinstance(empty, HandoffBlock)
    assert empty.summary == DEGRADED["de"]
    assert german_is_clean(empty.summary)
    assert "sales@" not in empty.summary
    assert " the " not in f" {empty.summary.lower()} "


def test_the_clock_times_a_grounded_turn_without_changing_it() -> None:
    """#336: the model attempt, grounding and hydration are timed as phases; the
    turn's result is the one the same generate produces without a clock."""
    facts = _facts()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="This inverter is {fact:p4107.ac_power_kw} kW.",
                        refs=["4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    clock = Timing()
    result = run(_request(), generate, clock=clock)
    assert result.fallback is False
    assert "10 kW" in result.output.blocks[0].text  # type: ignore[union-attr]
    record = clock.as_log()
    # A grounded first attempt: exactly these phases, nothing skipped.
    assert set(record) == {
        "model",
        "model.attempt_1",
        "ground",
        "hydrate",
        "total",
    }
    assert all(value >= 0 for value in record.values())


def test_the_clock_times_both_attempts_and_the_fallback_render() -> None:
    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise ValueError("not a TurnOutput")

    clock = Timing()
    result = run(_request(), generate, clock=clock)
    assert result.fallback is True
    assert set(clock.as_log()) == {
        "model",
        "model.attempt_1",
        "model.attempt_2",
        "template",
        "hydrate",
        "total",
    }


def test_an_outside_document_is_retried_not_rewritten() -> None:
    """b09-en cited p3612.document.2. The check reports it; the model answers again.

    The service does not strip or rewrite the first draft (spec 13: no text
    rewrite). The retry carries the reason, and the second answer ships.
    """
    facts = _facts()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        if retry is None:
            return (
                TurnOutput(
                    language="en",
                    blocks=[
                        TextBlock(text="See the manual.", refs=["4107"]),
                        DocumentBlock(ref="p3612.document.2"),
                        CardsBlock(product_ids=[4107]),
                    ],
                ),
                facts,
            )
        assert "p3612.document.2" in retry
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="See the manual.", refs=["4107"]),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    result = run(_request(), generate)

    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 2
    assert [block.type for block in result.output.blocks] == ["text", "cards"]
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == "See the manual."
    cards = result.output.blocks[1]
    assert isinstance(cards, CardsBlock)
    assert cards.product_ids == [4107]


def test_an_outside_document_does_not_drop_the_ask_or_the_valid_document() -> None:
    """Turn 417's retry shipped one document and no ask. The retry is the
    model's own answer; the service keeps the valid blocks it returns."""
    from linker_genie.facts import Document

    facts = _released_pair()
    facts.documents["p3612.document.1"] = Document(
        url="https://de-linker.com/manual.pdf",
        title="ESA manual",
        page=1,
    )
    calls = 0

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        nonlocal calls
        calls += 1
        blocks: list[Block] = [
            TextBlock(
                text="These inverters are released.",
                refs=["6528", "3612"],
            ),
            CardsBlock(product_ids=[6528, 3612]),
            DocumentBlock(ref="p3612.document.1"),
            AskBlock(field="phase", options=["single-phase", "three-phase"]),
        ]
        if calls == 1:
            blocks.insert(3, DocumentBlock(ref="p3612.document.2"))
        else:
            assert retry is not None and "p3612.document.2" in retry
        return TurnOutput(language="en", blocks=blocks), facts

    result = run(_request(), generate, Route("pairing"))
    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 2
    assert [block.type for block in result.output.blocks] == [
        "text",
        "cards",
        "document",
        "ask",
    ]
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == "These inverters are released."
    documents = [
        block for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert [block.ref for block in documents] == ["p3612.document.1"]


def test_an_outside_document_on_a_german_turn_is_retried_in_german() -> None:
    facts = _facts()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        blocks: list[Block] = [
            TextBlock(text="Siehe das Handbuch.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ]
        if retry is None:
            blocks.insert(1, DocumentBlock(ref="p3612.document.2"))
        else:
            assert "p3612.document.2" in retry
        return TurnOutput(language="de", blocks=blocks), facts

    request = TurnRequest(
        conversation_id="c396",
        messages=[TurnMessage(role="user", content="Welche Batterien passen?")],
        locale="de",
    )
    result = run(request, generate)

    assert result.grounded is True and result.fallback is False
    assert result.attempts == 2
    assert [block.type for block in result.output.blocks] == ["text", "cards"]
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == "Siehe das Handbuch."
    assert german_is_clean(text.text)


def test_an_invented_citation_does_not_outrank_the_login_sentence() -> None:
    guest = _guest_inquiry()
    guest.product_ids = {3612}
    output = fallback(guest, "de", invented_citation=True)
    assert isinstance(output.blocks[0], TextBlock)
    assert output.blocks[0].text == LOGIN_REQUIRED["de"]
    assert not any(block.type == "cards" for block in output.blocks)


def _released_pair() -> TurnFacts:
    """One released check-compatibility set: inverter 6528, battery 3612."""
    payload: dict[str, Any] = {"verdict": "released", "conditions": [], "documents": []}
    facts = collect("linker/check-compatibility", payload, "en")
    facts.tool_calls.append(
        {
            "name": "linker/check-compatibility",
            "arguments": {"inverter_id": 6528, "battery_id": 3612},
            "ok": True,
            "result": payload,
        }
    )
    facts.product_ids.update({6528, 3612})
    facts.qualified_ids.update({6528, 3612})
    return facts


def test_a_degraded_pairing_answer_does_not_gain_cards() -> None:
    """#366/#410: the degraded sentence stays without product cards.

    route model/pairing and one released set used to append CardsBlock
    [6528, 3612] after `_degraded`.
    """
    facts = _released_pair()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del retry
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="See the manual, item 2."),
                    DocumentBlock(ref="p3612.document.2"),
                ],
            ),
            facts,
        )

    for name in ("pairing", "model"):
        result = run(_request(), generate, Route(name))
        assert result.fallback is True
        assert [block.type for block in result.output.blocks] == ["handoff"]
        handoff = result.output.blocks[0]
        assert isinstance(handoff, HandoffBlock)
        assert handoff.summary == DEGRADED["en"]
        assert not any(block.type == "cards" for block in result.output.blocks)


def test_a_product_id_outside_the_turn_keeps_the_partner_cards() -> None:
    """Product ids keep the card rules. They do not ship the degraded sentence."""
    facts = _released_pair()

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del retry
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="These inverters are released.", refs=["9999"]),
                    CardsBlock(product_ids=[9999]),
                ],
            ),
            facts,
        )

    result = run(_request(), generate, Route("pairing"))
    assert result.fallback is True
    assert not any(
        isinstance(block, HandoffBlock) and block.summary == DEGRADED["en"]
        for block in result.output.blocks
    )
    cards = [block for block in result.output.blocks if isinstance(block, CardsBlock)]
    assert cards
    assert 6528 in cards[0].product_ids
    assert 3612 in cards[0].product_ids


def test_cites_outside_turn_reads_the_kind_from_the_check() -> None:
    """The kind is data on the check, not a parse of the failure prose."""
    from linker_genie.ground import Citation, check, cites_outside_turn

    empty = TurnFacts()

    document = check(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="See the manual."),
                DocumentBlock(ref="p3612.document.2"),
            ],
        ),
        empty,
    )
    assert document.citations == (Citation("document", "p3612.document.2"),)
    assert cites_outside_turn(document.citations)

    chunk = check(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text="The manual says so.",
                    refs=["770ccafa080c-p37-63a0f610"],
                )
            ],
        ),
        empty,
    )
    assert chunk.citations == (Citation("chunk", "770ccafa080c-p37-63a0f610"),)
    assert cites_outside_turn(chunk.citations)

    known = TurnFacts()
    known.product_ids = {6528}
    product = check(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="These inverters are released.", refs=["9999"]),
                CardsBlock(product_ids=[9999]),
            ],
        ),
        known,
    )
    assert Citation("product", "9999") in product.citations
    assert not cites_outside_turn(product.citations)

    numeric = check(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="See this product.", refs=["6528"])],
        ),
        empty,
    )
    assert numeric.citations == (Citation("product", "6528"),)
    assert not cites_outside_turn(numeric.citations)

    prefixed = check(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="See this product.", refs=["p6528"])],
        ),
        empty,
    )
    assert prefixed.citations == (Citation("product", "p6528"),)
    assert not cites_outside_turn(prefixed.citations)

    placeholder = check(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="Power is {fact:p6528.ac_power_kw}.")],
        ),
        empty,
    )
    assert placeholder.citations == (Citation("placeholder", "p6528.ac_power_kw"),)
    assert not cites_outside_turn(placeholder.citations)


def test_tool_retries_match_the_ability_attempt_count() -> None:
    """pydantic-ai AgentRetries.tools is retries after the first call.

    TOOL_RETRIES = 2 is three attempts, the same count as ABILITY_ATTEMPTS
    (#103). Dossier 2026-10-19 §1.15 publishes no competitor count.
    """
    from linker_genie.abilities import ABILITY_ATTEMPTS
    from linker_genie.agent import TOOL_RETRIES

    assert TOOL_RETRIES == ABILITY_ATTEMPTS - 1 == 2


# G5-EN asked for a model the series search did not qualify. The unrelated
# card the route still held (product 3608) must not ship as a normal match.
_UNRELATED = 3608
_QUESTIONS: dict[Locale, str] = {
    "en": "Do you carry the EcoFlow OCEAN 3 HD-P3-20K0-S2?",
    "de": "Führen Sie dieses Produkt?",
}
_RECOVERED: dict[Locale, str] = {
    "en": "The search did not return that product.",
    "de": "Die Suche hat dieses Produkt nicht geliefert.",
}


def _ocean_request(language: Locale) -> TurnRequest:
    return TurnRequest(
        conversation_id="g5",
        locale=language,
        messages=[TurnMessage(role="user", content=_QUESTIONS[language])],
    )


def _series_seed() -> TurnFacts:
    """A products search that qualified a different model in the series."""
    facts = TurnFacts()
    facts.product_ids = {_UNRELATED}
    facts.qualified_ids = {_UNRELATED}
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"series": "ecoflow-ocean-2-battery", "brand": "ecoflow"},
            "ok": True,
            "result": {"qualified": [{"product_id": _UNRELATED}]},
        }
    )
    return facts


def _products_route() -> Route:
    return Route("products", show_products=True, no_handoff=True)


def _invalid_search(_arguments: dict[str, Any] | None) -> dict[str, Any]:
    """The tool body raises pydantic.ValidationError on every call."""
    parsed: int = TypeAdapter(int).validate_python("nope")
    return {"parsed": parsed}


def _keep_calling_knowledge(
    _messages: list[ModelMessage], _info: AgentInfo
) -> ModelResponse:
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="linker_search_knowledge",
                args={"arguments": {"query": "OCEAN 3", "lang": "en"}},
            )
        ]
    )


def _block_types(output: TurnOutput) -> list[str]:
    return [block.type for block in output.blocks]


@contextmanager
def _event_loop() -> Iterator[None]:
    """A set event loop for `Agent.run_sync`.

    pydantic-ai calls `asyncio.get_event_loop()`. On Python 3.12 that warns
    when no loop is set, and this suite treats warnings as errors. The loop
    set here is the one `run_sync` drives.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def test_a_tool_that_always_fails_validation_is_a_visible_degradation() -> None:
    """#366: retry exhaustion is DEGRADED, never the series card.

    The knowledge tool raises ValidationError until pydantic-ai stops the
    run (`exceeded max retries count of N`). The route already qualified
    product 3608. That card is not the asked model, and the answer does
    not present it as one. EN and DE are the same one-block shape.
    """
    shapes: list[list[str]] = []
    languages: tuple[Locale, ...] = ("en", "de")
    for language in languages:
        generate = make_generate(
            AbilityClient("http://127.0.0.1:9"),
            model=FunctionModel(_keep_calling_knowledge),
            search=_invalid_search,
        )
        with _event_loop():
            result = run(
                _ocean_request(language),
                generate,
                route=_products_route(),
                seed=_series_seed(),
            )
        assert result.fallback is True
        assert result.grounded is False
        assert result.attempts == 2
        assert any(
            "exceeded max retries count of 2" in item for item in result.failures
        )
        assert len(result.output.blocks) == 1
        handoff = result.output.blocks[0]
        assert isinstance(handoff, HandoffBlock)
        assert handoff.summary == DEGRADED[language]
        assert result.output.language == language
        assert not any(isinstance(block, CardsBlock) for block in result.output.blocks)
        assert "matching products" not in handoff.summary
        if language == "de":
            assert german_is_clean(handoff.summary)
        shapes.append(_block_types(result.output))
    assert shapes[0] == shapes[1] == ["handoff"]

    # A guest inquiry still asks for a login. Exhaustion does not replace it.
    guest = collect("linker/inquiry-status", {"error": "login_required"})
    guest.product_ids = {_UNRELATED}
    guest.qualified_ids = {_UNRELATED}
    login = fallback(guest, "en", _products_route(), exhausted=True)
    assert isinstance(login.blocks[0], TextBlock)
    assert login.blocks[0].text == LOGIN_REQUIRED["en"]


def test_a_products_route_with_nothing_qualified_shows_no_unrelated_cards() -> None:
    """#366: product_ids that the search did not qualify are not cards.

    A search that ran asks once. A search that did not is the outage
    sentence. A model route still shows the product the get-product call
    recorded. EN and DE keep the same block types.
    """
    asked: list[list[str]] = []
    outages: list[list[str]] = []
    languages: tuple[Locale, ...] = ("en", "de")
    for language in languages:
        facts = TurnFacts()
        facts.product_ids = {_UNRELATED}
        facts.tool_calls.append(
            {
                "name": "linker/search-products",
                "arguments": {"text": "HD-P3-20K0-S2"},
                "ok": True,
                "result": {"qualified": []},
            }
        )
        found = fallback(facts, language, _products_route())
        assert not any(isinstance(block, CardsBlock) for block in found.blocks)
        assert _block_types(found) == ["text", "ask"]
        text = next(block for block in found.blocks if isinstance(block, TextBlock))
        ask = next(block for block in found.blocks if isinstance(block, AskBlock))
        assert text.text == (NO_MATCH_DE if language == "de" else NO_MATCH_EN)
        assert ask.field == "brand" and ask.options == []
        if language == "de":
            assert german_is_clean(text.text)
        asked.append(_block_types(found))

        missed = TurnFacts()
        missed.product_ids = {_UNRELATED}
        outage = fallback(missed, language, _products_route())
        assert len(outage.blocks) == 1
        handoff = outage.blocks[0]
        assert isinstance(handoff, HandoffBlock)
        assert handoff.summary == DEGRADED[language]
        assert not any(isinstance(block, CardsBlock) for block in outage.blocks)
        outages.append(_block_types(outage))
    assert asked[0] == asked[1]
    assert outages[0] == outages[1]

    # Scope: a model route's get-product id is still the card. This ticket
    # only stops a products search from borrowing ids it did not qualify.
    recorded = TurnFacts()
    recorded.product_ids = {_UNRELATED}
    model = fallback(recorded, "en", Route("model", show_products=True))
    cards = [block for block in model.blocks if isinstance(block, CardsBlock)]
    assert cards and cards[0].product_ids == [_UNRELATED]


def _recover(language: Locale) -> FunctionModel:
    def respond(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        last = messages[-1]
        parts = getattr(last, "parts", [])
        if any(isinstance(part, ToolReturnPart) for part in parts):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="final_result",
                        args={
                            "language": language,
                            "blocks": [{"type": "text", "text": _RECOVERED[language]}],
                        },
                    )
                ]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="linker_search_knowledge",
                    args={"arguments": {"query": "OCEAN", "lang": language}},
                )
            ]
        )

    return FunctionModel(respond)


def test_a_validation_error_that_recovers_is_a_normal_answer() -> None:
    """One ValidationError, then a real tool result, is not a degradation.

    pydantic-ai hands the error back and the next call succeeds. The cycle
    ships that answer. EN and DE are one text block, with no card.
    """
    shapes: list[list[str]] = []
    languages: tuple[Locale, ...] = ("en", "de")
    for language in languages:
        attempts = {"n": 0}

        def search(
            _arguments: dict[str, Any] | None, *, _attempts: dict[str, int] = attempts
        ) -> dict[str, Any]:
            _attempts["n"] += 1
            if _attempts["n"] == 1:
                parsed: int = TypeAdapter(int).validate_python("nope")
                return {"parsed": parsed}
            return {
                "hits": [],
                "ranking": "vector",
                "encoder": None,
                "index_version": "t",
            }

        generate = make_generate(
            AbilityClient("http://127.0.0.1:9"),
            model=_recover(language),
            search=search,
        )
        with _event_loop():
            result = run(
                _ocean_request(language),
                generate,
                route=_products_route(),
                seed=TurnFacts(),
            )
        assert attempts["n"] == 2
        assert result.fallback is False
        assert result.grounded is True
        assert result.attempts == 1
        assert result.failures == ()
        assert len(result.output.blocks) == 1
        block = result.output.blocks[0]
        assert isinstance(block, TextBlock)
        assert block.text == _RECOVERED[language]
        assert result.output.language == language
        assert not any(isinstance(item, CardsBlock) for item in result.output.blocks)
        if language == "de":
            assert german_is_clean(block.text)
        shapes.append(_block_types(result.output))
    assert shapes[0] == shapes[1] == ["text"]
