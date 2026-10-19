"""Answer language follows the customer's last message, in both directions (#374).

The page locale is the fallback for a language-neutral message and for a
message that mixes English and German. A model that answers in the other
language is asked once; a second miss is not shipped.
"""

import json
from pathlib import Path

import pytest

from linker_genie.agent import _user_prompt, instructions
from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.language import (
    _ENGLISH,
    _GERMAN,
    _WORD,
    answer_language,
    clear_language,
    language_failure,
    visible_text,
)
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
    HANDOFF_PLACEHOLDER,
    LOGIN_PLACEHOLDER,
    LOGIN_REQUIRED,
    german_is_clean,
)

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


@pytest.mark.parametrize(
    ("message", "language"),
    [
        ("Price?", "en"),
        ("Datasheet?", "en"),
        ("Availability?", "en"),
        ("Preis?", "de"),
        ("Empfehlung?", "de"),
        ("Kosten?", "de"),
        ("Lieferzeit?", "de"),
        ("Verfügbarkeit?", "de"),
    ],
)
def test_one_content_word_is_that_language(message: str, language: str) -> None:
    """A bare code, emoji or number stays neutral. One clear word does not."""
    assert clear_language(message) == language
    assert answer_language(message, "en" if language == "de" else "de") == language


def test_mixed_prose_fails_even_when_the_language_field_matches() -> None:
    mixed = "Diese Batterien work with the H2-10K-T3."
    assert clear_language(mixed) is None
    assert language_failure(_output("en", mixed), "en") is not None
    assert language_failure(_output("de", mixed), "de") is not None
    # A model code beside one language is not mixed.
    assert language_failure(_output("en", ENGLISH_ANSWER), "en") is None
    assert language_failure(_output("de", GERMAN_ANSWER), "de") is None


def _closed(text: str, words: frozenset[str], *, umlauts: bool) -> list[str]:
    found: list[str] = []
    for word in _WORD.findall(text.lower()):
        if word in words or (umlauts and any(letter in word for letter in "äöüß")):
            found.append(word)
    return found


def _pairing(language: str, condition: str, price: str) -> tuple[TurnOutput, TurnFacts]:
    prose = (
        "These batteries work with the H2-10K-T3. {fact:compat.condition.0}"
        if language == "en"
        else "Diese Batterien passen zu Ihrem H2-10K-T3. {fact:compat.condition.0}"
    )
    facts = TurnFacts()
    facts.product_ids.add(4107)
    facts.qualified_ids.add(4107)
    facts.add(
        Fact(id="compat.condition.0", value=condition, source="check-compatibility")
    )
    facts.commerce[4107] = {"price_line": price, "price_reason": "pending"}
    output = TurnOutput(
        language=language,  # type: ignore[arg-type]
        blocks=[
            TextBlock(text=prose, refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    return output, facts


def test_the_hydrated_answer_follows_the_question_on_either_page() -> None:
    """English on a DE page, and German on an EN page.

    The first attempt's model text is already the right language, but the
    hydrated condition and the price line are the page's language. The check
    reads that final text, asks once, and ships the second attempt. The
    assertion is the hydrated answer, not the model's placeholder.
    """
    cases = (
        (
            ENGLISH_QUESTION,
            "de",
            "en",
            "Die Module stehen in einer Säule",
            "Preise nach Freigabe",
            "The modules stand in one column.",
            "Prices after approval",
            _GERMAN,
            True,
        ),
        (
            GERMAN_QUESTION,
            "en",
            "de",
            "The modules stand in one column.",
            "Prices after approval",
            "Die Module stehen in einer Säule",
            "Preise nach Freigabe",
            _ENGLISH,
            False,
        ),
    )
    for (
        question,
        locale,
        language,
        wrong_condition,
        wrong_price,
        right_condition,
        right_price,
        foreign,
        umlauts,
    ) in cases:
        reasons: list[str | None] = []

        def generate(
            _request: TurnRequest,
            retry: str | None,
            language: str = language,
            wrong_condition: str = wrong_condition,
            wrong_price: str = wrong_price,
            right_condition: str = right_condition,
            right_price: str = right_price,
            reasons: list[str | None] = reasons,
        ) -> tuple[TurnOutput, TurnFacts]:
            reasons.append(retry)
            condition, price = (
                (wrong_condition, wrong_price)
                if retry is None
                else (right_condition, right_price)
            )
            return _pairing(language, condition, price)

        result = run(_request(question, locale), generate)
        shipped = visible_text(result.output)

        assert reasons[0] is None
        assert reasons[1] is not None and reasons[1].startswith("answer in ")
        assert result.fallback is False
        assert result.attempts == 2
        assert result.output.language == language
        assert right_condition in shipped
        assert right_price in shipped
        assert wrong_condition not in shipped
        assert wrong_price not in shipped
        assert _closed(shipped, foreign, umlauts=umlauts) == []
        if language == "de":
            assert "Ihr" in shipped
            assert german_is_clean(shipped)


def test_a_page_language_handoff_placeholder_hydrates_in_the_question_language() -> (
    None
):
    english = "Please write to our team."
    german = "Bitte schreiben Sie an unser Team."
    facts = TurnFacts()
    for fact_id, value in (
        ("handoff.sentence_en", english),
        ("handoff.sentence_de", german),
        ("handoff.sentence", german),
    ):
        facts.add(Fact(id=fact_id, value=value, source="handoff-team"))

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[HandoffBlock(summary="{fact:handoff.sentence_de}")],
            ),
            facts,
        )

    result = run(_request(ENGLISH_QUESTION, "de"), generate)
    summary = result.output.blocks[0]
    assert isinstance(summary, HandoffBlock)
    assert summary.summary == english
    assert _closed(summary.summary, _GERMAN, umlauts=True) == []
    assert result.fallback is False

    def german_turn(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="de",
                blocks=[HandoffBlock(summary="{fact:handoff.sentence_en}")],
            ),
            facts,
        )

    mirrored = run(_request(GERMAN_QUESTION, "en"), german_turn)
    mirrored_summary = mirrored.output.blocks[0]
    assert isinstance(mirrored_summary, HandoffBlock)
    assert mirrored_summary.summary == german
    assert _closed(mirrored_summary.summary, _ENGLISH, umlauts=False) == []
    assert "Sie" in mirrored_summary.summary


def test_the_login_sentence_follows_the_question_not_the_page() -> None:
    facts = collect("linker/inquiry-status", {"error": "login_required"}, "de")

    def exact(_request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        return _output("de", LOGIN_REQUIRED["de"]), facts

    def placeholder(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return _output("de", LOGIN_PLACEHOLDER), facts

    for generate in (exact, placeholder):
        result = run(_request(ENGLISH_QUESTION, "de"), generate)
        block = result.output.blocks[0]
        assert isinstance(block, TextBlock)
        assert block.text == LOGIN_REQUIRED["en"]
        assert result.output.language == "en"
        assert result.fallback is False
        assert result.attempts == 1
        assert _closed(block.text, _GERMAN, umlauts=True) == []

    english_facts = collect("linker/inquiry-status", {"error": "login_required"}, "en")

    def german_login(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return _output("en", LOGIN_REQUIRED["en"]), english_facts

    mirrored = run(_request(GERMAN_QUESTION, "en"), german_login)
    mirrored_block = mirrored.output.blocks[0]
    assert isinstance(mirrored_block, TextBlock)
    assert mirrored_block.text == LOGIN_REQUIRED["de"]
    assert "Sie" in mirrored_block.text
    assert mirrored.fallback is False
    assert _closed(mirrored_block.text, _ENGLISH, umlauts=False) == []


def test_mixed_prose_is_reasked_once_and_a_second_miss_uses_the_template() -> None:
    mixed = "Diese Batterien work with the H2-10K-T3."
    reasons: list[str | None] = []

    def once(_request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        reasons.append(retry)
        text = mixed if retry is None else ENGLISH_ANSWER
        return _output("en", text), TurnFacts()

    repaired = run(_request(ENGLISH_QUESTION, "de"), once)
    assert reasons[1] is not None and reasons[1].startswith("answer in ")
    assert repaired.fallback is False
    assert repaired.output.blocks[0].text == ENGLISH_ANSWER  # type: ignore[union-attr]

    def twice(_request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        return _output("de", mixed), TurnFacts()

    fallen = run(_request(GERMAN_QUESTION, "en"), twice)
    assert fallen.fallback is True
    assert fallen.output.language == "de"
    shipped = fallen.output.blocks[0]
    assert isinstance(shipped, HandoffBlock)
    assert shipped.summary == DEGRADED["de"]
    assert mixed not in shipped.summary
    assert german_is_clean(shipped.summary)
    assert "Sie" in shipped.summary
    assert "Ihre" in shipped.summary


def test_339_language_cases_hold() -> None:
    """The #374 cases registered for the #339 regression corpus."""
    path = Path(__file__).resolve().parents[1] / "eval" / "language" / "cases.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["issue"] == 374
    assert manifest["corpus"] == 339
    for case in manifest["cases"]:
        if "message" in case:
            assert answer_language(case["message"], case["locale"]) == case["expected"]
        if "answer" in case:
            failure = language_failure(
                _output(case["language"], case["answer"]), case["expected"]
            )
            assert (failure is not None) is case["fails"]
    assert HANDOFF_PLACEHOLDER == "{fact:handoff.sentence}"
    assert LOGIN_PLACEHOLDER == "{fact:inquiry.login}"
