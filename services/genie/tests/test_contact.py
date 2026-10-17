"""'Let Linker contact me' (#243): when Genie offers it, and the turn that offers it."""

import json
from pathlib import Path

import pytest

from linker_genie.contact import (
    asks_for_person,
    decide,
    offered,
    repeats,
    same_question,
)
from linker_genie.jev import Reading
from linker_genie.route import Route
from linker_genie.schema import TurnMessage

CASES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "eval" / "contact" / "repeats.json"
    ).read_text(encoding="utf-8")
)


def _reading(intent: str = "other", person: float = 0.05) -> Reading:
    return Reading(intent, 0.95, 0.1, person, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _thread(*customer: str) -> list[TurnMessage]:
    """Customer messages with an answer between them, as the browser sends them."""
    messages: list[TurnMessage] = []
    for text in customer:
        if messages:
            messages.append(TurnMessage(role="assistant", content="An answer."))
        messages.append(TurnMessage(role="user", content=text))
    return messages


@pytest.mark.parametrize(
    "message",
    [
        # The ticket's own sentences (completion criteria of #243).
        "Can I talk to a person?",
        "Ich möchte mit einem Mitarbeiter sprechen",
        # The trial's question 17 (docs/research/2026-10-17-knocket/TRIAL.md).
        "Can I talk to someone?",
        "I want to speak with a real human",
        "Please connect me to an agent.",
        "transfer to human",
        "Is there anyone I can talk to?",
        "Can someone call me back?",
        "Please contact me about this offer",
        "Kann ich mit jemandem sprechen?",
        "Ich will mit einem Menschen reden!",
        "Verbinden Sie mich bitte mit einem Berater",
        "Bitte rufen Sie mich zurück",
        "Kann mich jemand anrufen?",
        "Ich hätte gern einen Rückruf",
        "Kontaktieren Sie mich bitte",
        "MIT EINEM MITARBEITER SPRECHEN",
        # A negation of an earlier sentence does not reach the request.
        "That did not help at all. Can I talk to a person?",
        "Das hat nicht geholfen. Kann ich mit jemandem sprechen?",
    ],
)
def test_an_explicit_request_for_a_person_is_matched_without_a_model(
    message: str,
) -> None:
    assert asks_for_person(message)


@pytest.mark.parametrize(
    "message",
    [
        # Bare nouns and product talk stay with Jev (the library is strict, as
        # Knocket's: docs/research/2026-10-17-knocket/raw/apify/pages/
        # knocket-handoff-phrases.md, "Loose or ambiguous wording … kept out").
        "Do you have customer service?",
        "Can the inverter talk to the battery?",
        "Kann der Wechselrichter mit dem Speicher sprechen?",
        "Is the SAJ H2 suitable for a one-person household?",
        "Email me the datasheet of the GoodWe ET",
        "Which agent software runs on the EMS?",
        "Welcher Speicher passt zum SAJ H2-10K-T3?",
        "saj",
        # A negated phrase is no request (copy review of #243).
        "I don't want to talk to a person, just tell me the price.",
        "Ich möchte nicht mit einem Mitarbeiter sprechen.",
    ],
)
def test_ordinary_questions_do_not_match(message: str) -> None:
    assert not asks_for_person(message)


@pytest.mark.parametrize("case", CASES["pairs"], ids=lambda c: c["a"][:30])
def test_same_question_matches_the_measured_cases(case: dict[str, object]) -> None:
    assert same_question(str(case["a"]), str(case["b"])) is case["same"]


def test_three_rounds_of_the_same_question_count_three() -> None:
    messages = _thread(
        "Which battery fits the SAJ H2-10K-T3?",
        "which battery fits SAJ H2-10K-T3",
        "Which battery fits the SAJ H2 10K T3??",
    )
    assert repeats(messages) == 3


def test_a_different_question_breaks_the_run() -> None:
    messages = _thread(
        "Which battery fits the SAJ H2-10K-T3?",
        "Datasheet of the GoodWe ET please",
        "Which battery fits the SAJ H2-10K-T3?",
    )
    assert repeats(messages) == 1


def test_an_explicit_request_is_always_answered_with_the_offer() -> None:
    offer = decide(Route("person"), None, _thread("Can I talk to a person?"), (True,))
    assert offer is not None and offer.reason == "asked"


def test_a_company_question_carries_the_offer_beside_the_mailbox_sentence() -> None:
    offer = decide(
        Route("service"),
        _reading("company_logistics_service"),
        _thread("Lieferzeit?"),
        (),
    )
    assert offer is not None and offer.reason == "service"


def test_dissatisfaction_offers_contact_beside_the_answer() -> None:
    offer = decide(
        Route("model"), _reading("other", person=0.9), _thread("This is useless."), ()
    )
    assert offer is not None and offer.reason == "dissatisfied"


def test_dissatisfaction_is_not_offered_twice_in_a_row() -> None:
    offer = decide(
        Route("model"),
        _reading("other", person=0.9),
        _thread("Still useless."),
        (True,),
    )
    assert offer is None


def test_the_third_round_of_one_question_offers_contact_once() -> None:
    question = "Which battery fits the SAJ H2-10K-T3?"
    third = decide(
        Route("model"),
        _reading(),
        _thread(question, question, question),
        (False, False),
    )
    assert third is not None and third.reason == "repeat"
    # The fourth round follows the offer: never two in a row.
    fourth = decide(
        Route("model"),
        _reading(),
        _thread(question, question, question, question),
        (True, False, False),
    )
    assert fourth is None
    # The fifth: the offer was made for this question already (once).
    fifth = decide(
        Route("model"),
        _reading(),
        _thread(question, question, question, question, question),
        (False, True, False, False),
    )
    assert fifth is None


def test_two_rounds_are_not_yet_a_repeat() -> None:
    question = "Which battery fits the SAJ H2-10K-T3?"
    assert (
        decide(Route("model"), _reading(), _thread(question, question), (False,))
        is None
    )


def test_without_jev_the_repeat_rule_still_offers() -> None:
    question = "Welcher Speicher passt zum SAJ H2-10K-T3?"
    offer = decide(Route("model"), None, _thread(question, question, question), ())
    assert offer is not None and offer.reason == "repeat"


def test_a_logged_answer_carries_the_offer_when_it_has_the_contact_block() -> None:
    assert offered(
        {"blocks": [{"type": "text"}, {"type": "contact", "reason": "asked"}]}
    )
    assert not offered({"blocks": [{"type": "handoff", "summary": "x"}]})
    assert not offered({})
