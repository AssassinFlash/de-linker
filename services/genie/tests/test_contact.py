"""'Let Linker contact me' (#243): when Genie offers it, and the turn that offers it."""

import json
import re
from pathlib import Path

import pytest

import linker_genie.contact as contact_mod
from linker_genie.contact import (
    asks_for_person,
    decide,
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
        "Can I talk to your team?",
        "Could I speak to someone from your sales team?",
        "I'd like to talk to a real person please",
        "Kann ich mit Ihrem Team sprechen?",
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
        # Words that name a person only in a request (review round 1 of #243).
        "Can the inverter talk to the team portal?",
        "Does the app have an expert mode?",
        "Can I talk to the engineer's guide in the app?",
        "Where is the engineer's guide for the H2?",
        "Kann der Wechselrichter mit dem Team-Portal sprechen?",
        "Hat die App einen Expertenmodus?",
        "Wo finde ich die Techniker-Anleitung für den H2?",
    ],
)
def test_ordinary_questions_do_not_match(message: str) -> None:
    assert not asks_for_person(message)


@pytest.mark.parametrize("case", CASES["pairs"], ids=lambda c: c["a"][:30])
def test_same_question_matches_the_measured_cases(case: dict[str, object]) -> None:
    assert same_question(str(case["a"]), str(case["b"])) is case["same"]


def _sweep_mismatches() -> list[str]:
    """Pairs the 0-to-0.75 sweep gets wrong, as short labels."""
    missed: list[str] = []
    for cut_hundredths in range(76):
        cut = cut_hundredths / 100
        for case in CASES["pairs"]:
            if same_question(str(case["a"]), str(case["b"]), cut) is not case["same"]:
                missed.append(f"{cut}: {case['b']}")
                return missed
    return missed


def test_339_filler_corpus_holds_for_every_cut_from_0_to_0_75() -> None:
    """#339: repeats.json, including the #375 filler pairs, matches every cut.

    The spec's claim is any Jaccard cut from 0 through 0.75. Above 0.75 the
    shortened "Garantie GoodWe ET?" stops counting, because its overlap is 3/4.
    The corpus size is the 81 pairs in ``eval/contact/repeats.json``. The #339
    case map records that length. It still holds when the campaign module
    reexports this test.
    """
    assert len(CASES["pairs"]) == 81
    assert _sweep_mismatches() == []


def test_language_markers_are_the_unambiguous_stopwords() -> None:
    """Markers are derived from the stop lists, minus homographs."""
    assert contact_mod._EN_MARKERS <= contact_mod._EN_STOP
    assert contact_mod._DE_MARKERS <= contact_mod._DE_STOP
    assert contact_mod._EN_MARKERS.isdisjoint(contact_mod._DE_MARKERS)
    assert contact_mod._EN_MARKERS.isdisjoint(contact_mod._AMBIGUOUS_WORDS)
    assert contact_mod._DE_MARKERS.isdisjoint(contact_mod._AMBIGUOUS_WORDS)
    covered = (
        contact_mod._EN_MARKERS | contact_mod._DE_MARKERS | contact_mod._AMBIGUOUS_WORDS
    )
    assert contact_mod._STOPWORDS <= covered
    for homograph in ("will", "die", "was", "wo", "hat", "am", "er"):
        assert homograph not in contact_mod._EN_MARKERS
        assert homograph not in contact_mod._DE_MARKERS


def test_removing_any_filler_row_fails_the_calibration_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each filler row is the only reason some corpus pair survives 0 to 0.75."""
    rows = [("_EN_FILLERS", word) for word in sorted(contact_mod._EN_FILLERS)]
    rows += [("_DE_FILLERS", word) for word in sorted(contact_mod._DE_FILLERS)]
    for name, word in rows:
        current = getattr(contact_mod, name)
        monkeypatch.setattr(contact_mod, name, current - {word})
        assert _sweep_mismatches(), word
        monkeypatch.setattr(contact_mod, name, current)
    monkeypatch.setattr(contact_mod, "_RIGHT_NOW", re.compile(r"(?!)"))
    assert _sweep_mismatches()


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


def test_the_service_card_is_not_offered_twice_in_a_row() -> None:
    # The mailbox sentence stays every time; the card only when the previous
    # turn did not show one (review round 1 of #243).
    offer = decide(
        Route("service"),
        _reading("company_logistics_service"),
        _thread("Lieferzeit?", "Und nach Österreich?"),
        (True,),
    )
    assert offer is None


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


# #375. The #331 attack adds one time word per round to one pairing question
# (s5-en-never-offer-attack: now, today, right now). German uses heute, gerade
# and aktuell. please and bitte are already stopwords.
# Round 3: homographs are not language markers; unmarked text still drops
# fillers other than German "still"; today/heute stay on a delivery participle.
@pytest.mark.parametrize(
    ("earlier", "later"),
    [
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 now?",
        ),
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 today?",
        ),
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 right now?",
        ),
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 still?",
        ),
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 please?",
        ),
        # Round 3. "will" / "die" are homographs, and "stock now?" has no
        # function word. None of these may block the filler.
        (
            "Ich will die SAJ H2-10K-T3 Batterie kaufen.",
            "Ich will die SAJ H2-10K-T3 Batterie kaufen aktuell.",
        ),
        (
            "GW10K-ETA stock?",
            "GW10K-ETA stock now?",
        ),
        (
            "Which batteries die fastest?",
            "Which batteries die fastest now?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 heute?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 gerade?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 bitte?",
        ),
        (
            "Wie viele GW10K-ETA haben Sie auf Lager?",
            "Wie viele GW10K-ETA haben Sie aktuell auf Lager?",
        ),
        (
            "Wie ist der Lagerbestand des GW10K-ETA?",
            "Wie ist der aktuelle Lagerbestand des GW10K-ETA?",
        ),
        (
            "Haben Sie den Lagerbestand des GW10K-ETA?",
            "Haben Sie den aktuellen Lagerbestand des GW10K-ETA?",
        ),
        (
            "Ist ein Lagerbestand des GW10K-ETA bekannt?",
            "Ist ein aktueller Lagerbestand des GW10K-ETA bekannt?",
        ),
        (
            "Ist ein Lager des GW10K-ETA bekannt?",
            "Ist ein aktuelles Lager des GW10K-ETA bekannt?",
        ),
        # Both sides already negated: a filler does not open a new question.
        (
            "Which batteries do not work with the SAJ H2-10K-T3?",
            "Which batteries do not work with the SAJ H2-10K-T3 now?",
        ),
        (
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3?",
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3 gerade?",
        ),
    ],
)
def test_a_filler_does_not_make_the_question_new(earlier: str, later: str) -> None:
    assert same_question(earlier, later)


@pytest.mark.parametrize("question", ["Is it in stock now?", "Noch verfügbar?"])
def test_a_verbatim_short_question_still_counts(question: str) -> None:
    # Fillers used to be removed before MIN_WORDS, so both fell under the gate.
    assert same_question(question, question)
    assert repeats(_thread(question, question, question)) == 3


@pytest.mark.parametrize(
    ("earlier", "later"),
    [
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries do not work with the SAJ H2-10K-T3?",
        ),
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries do not work with the SAJ H2-10K-T3 now?",
        ),
        (
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3?",
        ),
        (
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3 heute?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen noch nicht zum SAJ H2-10K-T3?",
        ),
        # Later drops the negation. The added-not direction is above.
        (
            "Which batteries do not work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3?",
        ),
        (
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3?",
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
        ),
        # today/heute name a delivery day, including the participles.
        # noch adds. German still is quiet, including when "will" is the only
        # English-looking word. jetzt, yet, currently, derzeit, momentan and
        # zurzeit are not fillers. Dropping keiner/keinem/keines is a new question.
        (
            "Can you ship the GoodWe ET?",
            "Can you ship the GoodWe ET today?",
        ),
        (
            "Can the GoodWe ET be delivered?",
            "Can the GoodWe ET be delivered today?",
        ),
        (
            "Can the GoodWe ET be shipped?",
            "Can the GoodWe ET be shipped today?",
        ),
        (
            "Can the GoodWe ET be sent?",
            "Can the GoodWe ET be sent today?",
        ),
        (
            "Können Sie den GoodWe ET liefern?",
            "Können Sie den GoodWe ET heute liefern?",
        ),
        (
            "Können Sie den GoodWe ET versenden?",
            "Können Sie den GoodWe ET heute versenden?",
        ),
        (
            "Ist der GoodWe ET lieferbar?",
            "Ist der GoodWe ET heute lieferbar?",
        ),
        (
            "Kann der GoodWe ET ausgeliefert werden?",
            "Kann der GoodWe ET heute ausgeliefert werden?",
        ),
        (
            "Wann wird der GoodWe ET versandt?",
            "Wann wird der GoodWe ET heute versandt?",
        ),
        (
            "Will er laden?",
            "Will er still laden?",
        ),
        (
            "Is the GW10K-ETA in stock?",
            "Is the GW10K-ETA in stock yet?",
        ),
        (
            "How many GW10K-ETA units do you have in stock?",
            "How many GW10K-ETA units do you have in stock currently?",
        ),
        (
            "Wie viele GW10K-ETA haben Sie auf Lager?",
            "Wie viele GW10K-ETA haben Sie derzeit auf Lager?",
        ),
        (
            "Wie viele GW10K-ETA haben Sie auf Lager?",
            "Wie viele GW10K-ETA haben Sie momentan auf Lager?",
        ),
        (
            "Wie viele GW10K-ETA haben Sie auf Lager?",
            "Wie viele GW10K-ETA haben Sie zurzeit auf Lager?",
        ),
        (
            "Passt der Speicher zu einem SAJ H2-10K-T3?",
            "Passt der Speicher zu keinem SAJ H2-10K-T3?",
        ),
        (
            "Passt der Speicher zu keinem SAJ H2-10K-T3?",
            "Passt der Speicher zu einem SAJ H2-10K-T3?",
        ),
        (
            "Passt das zu einer SAJ Batterie?",
            "Passt das zu keiner SAJ Batterie?",
        ),
        (
            "Passt das zu keiner SAJ Batterie?",
            "Passt das zu einer SAJ Batterie?",
        ),
        (
            "Ist eines SAJ Modells kompatibel?",
            "Ist keines SAJ Modells kompatibel?",
        ),
        (
            "Ist keines SAJ Modells kompatibel?",
            "Ist eines SAJ Modells kompatibel?",
        ),
        (
            "Wir brauchen zwei Module.",
            "Wir brauchen noch zwei Module.",
        ),
        (
            "Läuft der Wechselrichter?",
            "Läuft der Wechselrichter still?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 noch?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 jetzt?",
        ),
        (
            "Which battery fits the SAJ H2-10K-T3?",
            "Which battery fits the SAJ H2-10K-T3 with backup now?",
        ),
        (
            "Which battery fits the SAJ H2-10K-T3?",
            "Which battery fits the SAJ H2-8K-T3 today?",
        ),
        (
            "Which battery fits the SAJ H2-10K-T3?",
            "Which battery fits the SAJ H2-10K-T3 for 15 kWh right now?",
        ),
        (
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
            "Welcher Speicher passt zum SAJ H2-10K-T3 für 15 kWh jetzt?",
        ),
        # "right" alone is not the phrase "right now".
        (
            "Is the GoodWe ET three-phase?",
            "Is the right GoodWe ET three-phase?",
        ),
        # A topic switch that opens with the filler (campaign #331 s1).
        (
            "The SAJ H2-10K-T3 looks right. Which batteries pair with it?",
            "Now something completely different: which EV chargers do you carry?",
        ),
        (
            "Der SAJ H2-10K-T3 sieht passend aus. Welche Batterien passen dazu?",
            "Jetzt etwas ganz anderes: welche Wallboxen führen Sie?",
        ),
    ],
)
def test_negation_codes_and_new_words_stay_a_different_question(
    earlier: str, later: str
) -> None:
    assert not same_question(earlier, later)


@pytest.mark.parametrize(
    "rounds",
    [
        (
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 now?",
            "Which batteries work with the SAJ H2-10K-T3 today?",
            "Which batteries work with the SAJ H2-10K-T3 right now?",
        ),
        (
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "Welche Batterien passen zum SAJ H2-10K-T3 aktuell?",
            "Welche Batterien passen zum SAJ H2-10K-T3 heute?",
            "Welche Batterien passen zum SAJ H2-10K-T3 gerade?",
        ),
    ],
    ids=["en", "de"],
)
def test_the_third_filler_round_offers_once_and_not_again(
    rounds: tuple[str, ...],
) -> None:
    # Two rounds are not yet the offer, filler or not. The verbatim triple is
    # test_the_third_round_of_one_question_offers_contact_once.
    assert decide(Route("model"), _reading(), _thread(*rounds[:2]), (False,)) is None
    third = decide(Route("model"), _reading(), _thread(*rounds[:3]), (False, False))
    assert third is not None and third.reason == "repeat"
    # The fourth follows the offer: never two in a row.
    fourth = decide(Route("model"), _reading(), _thread(*rounds), (True, False, False))
    assert fourth is None
    # Offered once for this run already, even when the previous turn had no card.
    fifth = decide(
        Route("model"),
        _reading(),
        _thread(*rounds, rounds[-1]),
        (False, True, False, False),
    )
    assert fifth is None


def test_a_negated_third_round_is_not_a_repeat() -> None:
    # "not" / "nicht" stay content words, including when a filler rides along.
    # Dropping one is test_dropping_a_negation_is_not_a_repeat_either.
    # The person-phrase negation is test_ordinary_questions_do_not_match.
    en = decide(
        Route("model"),
        _reading(),
        _thread(
            "Which batteries work with the SAJ H2-10K-T3?",
            "Which batteries work with the SAJ H2-10K-T3 now?",
            "Which batteries do not work with the SAJ H2-10K-T3 today?",
        ),
        (False, False),
    )
    de = decide(
        Route("model"),
        _reading(),
        _thread(
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
            "Welcher Speicher passt zum SAJ H2-10K-T3 jetzt?",
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3 heute?",
        ),
        (False, False),
    )
    assert en is None
    assert de is None


def test_dropping_a_negation_is_not_a_repeat_either() -> None:
    # The earlier rounds say "not" / "nicht"; the third takes the word out.
    en = decide(
        Route("model"),
        _reading(),
        _thread(
            "Which batteries do not work with the SAJ H2-10K-T3?",
            "Which batteries do not work with the SAJ H2-10K-T3 now?",
            "Which batteries work with the SAJ H2-10K-T3?",
        ),
        (False, False),
    )
    de = decide(
        Route("model"),
        _reading(),
        _thread(
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3?",
            "Welcher Speicher passt nicht zum SAJ H2-10K-T3 gerade?",
            "Welcher Speicher passt zum SAJ H2-10K-T3?",
        ),
        (False, False),
    )
    assert en is None
    assert de is None


def test_without_jev_the_repeat_rule_still_offers() -> None:
    question = "Welcher Speicher passt zum SAJ H2-10K-T3?"
    offer = decide(Route("model"), None, _thread(question, question, question), ())
    assert offer is not None and offer.reason == "repeat"
