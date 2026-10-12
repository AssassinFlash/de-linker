"""Retry once, then the deterministic template."""

from linker_genie.abilities import AbilityError
from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    LOGIN_REQUIRED,
    fallback,
    german_is_clean,
)


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


def test_a_failing_turn_is_retried_then_falls_back_to_the_template() -> None:
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
    assert len(attempts) == 2
    assert attempts[0] is None
    assert attempts[1] is not None
    assert result.fallback is True
    assert result.grounded is False
    types = [block.type for block in result.output.blocks]
    assert "cards" in types
    assert types.count("ask") <= 1


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
        raise AbilityError("linker/search-products could not be reached: boom")

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
    """Nothing citable this turn: the handoff says so and offers the retry
    and the team, in the turn's language, instead of reading as a normal
    out-of-scope handoff."""
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
    assert "melden Sie sich an" in block.text
    assert "sales@" not in block.text
    assert "@" not in block.text
    assert german_is_clean(block.text)
    assert result.output.language == "de"


def test_fallback_after_grounding_stays_inside_the_protocol_set() -> None:
    """C2-fallback: a refused product turn ships qualified cards inside the
    allowed set, cited by the text; a German line carries no English fragment.
    A turn with nothing citable ships the degraded sentence of that language,
    not the mailbox sentence."""
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
