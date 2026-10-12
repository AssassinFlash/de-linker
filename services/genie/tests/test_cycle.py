"""Retry once, then the deterministic template."""

from linker_genie.abilities import AbilityError
from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import fallback


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
