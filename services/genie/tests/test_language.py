"""Answer language follows the customer's last message, in both directions (#374).

The page locale is the fallback for a language-neutral message and for a
message that mixes English and German. A model that answers in the other
language is asked once; a second miss is not shipped.
"""

import pytest

from linker_genie.agent import _user_prompt, instructions
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts
from linker_genie.language import (
    _ENGLISH,
    _GERMAN,
    answer_language,
    clear_language,
)
from linker_genie.schema import (
    HandoffBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import DEGRADED, german_is_clean

ENGLISH_QUESTION = "Which batteries work with the SAJ H2-10K-T3?"
GERMAN_QUESTION = "Welche Batterien passen zum SAJ H2-10K-T3?"
ENGLISH_ANSWER = "These batteries work with the H2-10K-T3."
GERMAN_ANSWER = "Diese Batterien passen zum H2-10K-T3."
# Dossier §1.13: one sentence in both languages has no public precedent.
MIXED_QUESTION = "Welche battery für den H2-10K-T3?"


def _request(content: str, locale: str) -> TurnRequest:
    return TurnRequest(
        conversation_id="c374",
        messages=[TurnMessage(role="user", content=content)],
        locale=locale,  # type: ignore[arg-type]
    )


def _output(language: str, text: str) -> TurnOutput:
    return TurnOutput(
        language=language,  # type: ignore[arg-type]
        blocks=[TextBlock(text=text)],
    )


def _paragraphs(locale: str) -> list[str]:
    return [part.strip() for part in instructions(locale).split("\n\n") if part.strip()]


def test_the_word_lists_do_not_share_a_word() -> None:
    assert not (_ENGLISH & _GERMAN)


def test_an_english_question_on_a_german_page_is_answered_in_english() -> None:
    assert answer_language(ENGLISH_QUESTION, "de") == "en"
    assert clear_language(ENGLISH_QUESTION) == "en"


def test_a_german_question_on_an_english_page_is_answered_in_german() -> None:
    assert answer_language(GERMAN_QUESTION, "en") == "de"
    assert clear_language(GERMAN_QUESTION) == "de"


def test_the_two_directions_follow_the_question_not_the_page() -> None:
    """EN/DE same structure: each clear question keeps its language on either page."""
    assert answer_language(ENGLISH_QUESTION, "en") == answer_language(
        ENGLISH_QUESTION, "de"
    )
    assert answer_language(GERMAN_QUESTION, "en") == answer_language(
        GERMAN_QUESTION, "de"
    )
    assert answer_language(ENGLISH_QUESTION, "de") == "en"
    assert answer_language(GERMAN_QUESTION, "en") == "de"


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize(
    "message",
    ["H2-10K-T3", "SAJ", "42", "😀", "10 kWp three-phase home"],
)
def test_a_neutral_message_follows_the_page_locale(message: str, locale: str) -> None:
    assert clear_language(message) is None
    assert answer_language(message, locale) == locale


@pytest.mark.parametrize("locale", ["en", "de"])
def test_a_mixed_message_falls_back_to_the_page_locale(locale: str) -> None:
    assert clear_language(MIXED_QUESTION) is None
    assert answer_language(MIXED_QUESTION, locale) == locale


def test_both_prompts_state_the_same_rule_and_keep_the_same_structure() -> None:
    english, german = _paragraphs("en"), _paragraphs("de")
    assert len(english) == len(german)
    english_at = [i for i, part in enumerate(english) if part.startswith("Language:")]
    german_at = [i for i, part in enumerate(german) if part.startswith("Sprache:")]
    assert english_at == german_at
    assert len(english_at) == 1
    rule_en, rule_de = english[english_at[0]], german[german_at[0]]

    assert "last message" in rule_en
    assert "clearly one language" in rule_en
    assert "language-neutral" in rule_en
    assert "bare model code" in rule_en
    assert "emoji" in rule_en
    assert "number" in rule_en
    assert "mixes English and German" in rule_en
    assert "`locale=`" in rule_en
    assert "Sie form" in rule_en
    assert 'No "not X but Y"' in rule_en
    assert 'No trademark "Linker Genie"' in rule_en
    assert not rule_en.startswith("Language: English")

    assert "letzten Nachricht" in rule_de
    assert "eindeutig eine Sprache" in rule_de
    assert "sprachneutral" in rule_de
    assert "bloßer Modellcode" in rule_de
    assert "Emoji" in rule_de
    assert "Zahl" in rule_de
    assert "Englisch und Deutsch mischt" in rule_de
    assert "`locale=`" in rule_de
    assert "Sie-Form" in rule_de
    assert "Kein „nicht … sondern …“" in rule_de
    assert "Nicht „Linker Genie“ zusammenschreiben." in rule_de
    assert "Sprache: Deutsch, Sie-Form." not in rule_de

    # The other answer rules stay, including product vocabulary.
    assert "solution draft" in instructions("en")
    assert "Never write article, catalogue" in instructions("en")
    assert "Lösungsentwurf" in instructions("de")
    assert "Schreiben Sie nie Artikel, Katalog oder Warenkorb." in instructions("de")


def test_a_language_reask_is_worded_as_a_language_reask() -> None:
    request = _request(ENGLISH_QUESTION, "de")
    prompt = _user_prompt(
        request,
        "answer in English (language=en): follow the customer's last message",
    )
    assert "The previous answer used the wrong language." in prompt
    assert "failed grounding" not in prompt
    assert "answer in English" in prompt

    grounding = _user_prompt(request, "bare number in text")
    assert "The previous answer failed grounding: bare number in text" in grounding
    assert "wrong language" not in grounding


@pytest.mark.parametrize(
    ("question", "locale", "wrong", "right"),
    [
        (ENGLISH_QUESTION, "de", ("de", GERMAN_ANSWER), ("en", ENGLISH_ANSWER)),
        (GERMAN_QUESTION, "en", ("en", ENGLISH_ANSWER), ("de", GERMAN_ANSWER)),
    ],
)
def test_the_model_is_reasked_once_when_the_answer_language_is_wrong(
    question: str,
    locale: str,
    wrong: tuple[str, str],
    right: tuple[str, str],
) -> None:
    reasons: list[str | None] = []

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        reasons.append(retry)
        language, text = wrong if retry is None else right
        return _output(language, text), TurnFacts()

    result = run(_request(question, locale), generate)

    assert reasons[0] is None
    assert reasons[1] is not None
    assert reasons[1].startswith("answer in ")
    assert len(reasons) == 2
    assert result.fallback is False
    assert result.grounded is True
    assert result.attempts == 2
    assert result.output.language == right[0]
    assert result.output.blocks[0].text == right[1]  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("question", "locale", "wrong_language", "wrong_text", "expected"),
    [
        (ENGLISH_QUESTION, "de", "de", GERMAN_ANSWER, "en"),
        (GERMAN_QUESTION, "en", "en", ENGLISH_ANSWER, "de"),
    ],
)
def test_a_second_language_violation_is_not_shipped(
    question: str,
    locale: str,
    wrong_language: str,
    wrong_text: str,
    expected: str,
) -> None:
    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return _output(wrong_language, wrong_text), TurnFacts()

    result = run(_request(question, locale), generate)

    assert result.fallback is True
    assert result.grounded is False
    assert result.attempts == 2
    assert result.output.language == expected
    shipped = result.output.blocks[0]
    assert isinstance(shipped, HandoffBlock)
    assert shipped.summary == DEGRADED[expected]
    assert wrong_text not in shipped.summary
    assert any(failure.startswith("answer in ") for failure in result.failures)
    if expected == "de":
        assert german_is_clean(shipped.summary)


@pytest.mark.parametrize("locale", ["en", "de"])
def test_a_neutral_message_is_accepted_in_the_page_language(locale: str) -> None:
    text = ENGLISH_ANSWER if locale == "en" else GERMAN_ANSWER
    reasons: list[str | None] = []

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        reasons.append(retry)
        return _output(locale, text), TurnFacts()

    result = run(_request("H2-10K-T3", locale), generate)

    assert reasons == [None]
    assert result.fallback is False
    assert result.output.language == locale
    assert result.output.blocks[0].text == text  # type: ignore[union-attr]
