"""Every shaped answer carries its next step (#394).

The eight baseline rows are graded here with the deterministic checker.
Judge rows (b23, b41, b42) still need a judge for a full live pass; an empty
list means the floors and the row's expect, including the next step, hold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from baseline.grade import Turn, answer_text, check, untraceable_numbers

from linker_genie.abilities import Abilities
from linker_genie.agent import _user_prompt, instructions
from linker_genie.app import _answer
from linker_genie.contact import decide
from linker_genie.cycle import TurnResult, run
from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.ground import shipped
from linker_genie.jev import Reading
from linker_genie.lexicon import Match
from linker_genie.route import CONFIDENT, Route, Subject, plan, with_page
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    CardsBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    ESA_BATTERY,
    LOGIN_REQUIRED,
    PARTNER,
    PARTNER_CODES,
    PROMISE,
    REPLY_PROMISE,
    ROOF,
    SCRIPTED,
    TALK,
    finish,
    german_is_clean,
    roof_answer,
)
from linker_genie.understand import Prepared

SET = Path(__file__).parents[1] / "eval" / "baseline" / "baseline100.jsonl"
ROWS = {
    row["id"]: row
    for row in (json.loads(line) for line in SET.read_text().splitlines() if line)
}
NONE = Subject((), {}, {})
H2 = Subject((4107,), {4107: "inverters"}, {4107: "H2-10K-T3"})
EIGHT = (
    "b23-en",
    "b23-de",
    "b28-en",
    "b28-de",
    "b41-en",
    "b41-de",
    "b42-en",
    "b42-de",
)
# Text the model might ship with the next step missing. Grounding accepts it.
STUB = {
    "b23-en": "Sure.",
    "b23-de": "Gern.",
    "b28-en": "The team will look at it.",
    "b28-de": "Das Team sieht sich das an.",
    "b41-en": "Hello!",
    "b41-de": "Hallo!",
    "b42-en": "A helper.",
    "b42-de": "Ein Helfer.",
}
MAILBOX = {
    "sentence_en": "Please write to our team at sales@de-linker.com.",
    "sentence_de": "Bitte schreiben Sie an sales@de-linker.com.",
}


def _reading(intent: str, confidence: float = 0.95) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _request(row: dict[str, object]) -> TurnRequest:
    lang = str(row["lang"])
    return TurnRequest(
        conversation_id="c-394",
        locale=lang,  # type: ignore[arg-type]
        messages=[TurnMessage(role="user", content=str(row["question"]))],
    )


def _grade(row: dict[str, object], result: object) -> list[str]:
    output = result.output  # type: ignore[attr-defined]
    turn = Turn(
        meta={
            "grounded": result.grounded,  # type: ignore[attr-defined]
            "fallback": result.fallback,  # type: ignore[attr-defined]
            "language": output.language,
            "failures": list(result.failures),  # type: ignore[attr-defined]
        },
        blocks=[block.model_dump() for block in output.blocks],
        done=True,
    )
    return check(row, turn)


def _ship(row_id: str) -> tuple[Route, TurnResult]:
    row = ROWS[row_id]
    route = plan(str(row["question"]), [], _reading("other"), NONE, str(row["lang"]))

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language=row["lang"],
                blocks=[TextBlock(text=STUB[row_id])],
            ),
            TurnFacts(),
        )

    return route, run(_request(row), generate, route)


def test_the_eight_rows_pass_the_deterministic_grade() -> None:
    shapes = {"b23": "partner", "b28": "promise", "b41": "talk", "b42": "talk"}
    seen: dict[str, list[str]] = {}
    for row_id in EIGHT:
        row = ROWS[row_id]
        route, result = _ship(row_id)
        slot = row_id.split("-")[0]
        assert route.name == "model"
        assert route.calls == ()
        assert route.shape == shapes[slot]
        assert route.no_handoff and route.no_cards
        assert result.grounded and not result.fallback
        assert _grade(row, result) == []
        seen[row_id] = [block.type for block in result.output.blocks]
        if row["lang"] == "de":
            prose = " ".join(
                block.text if isinstance(block, TextBlock) else " ".join(block.options)
                for block in result.output.blocks
                if isinstance(block, TextBlock | AskBlock)
            )
            assert german_is_clean(prose)
        again = finish(result.output, TurnFacts(), route)
        assert again == result.output
    for slot, kinds in (("b23", ["text", "ask"]), ("b28", ["text", "action"])):
        assert seen[f"{slot}-en"] == seen[f"{slot}-de"] == kinds
    for slot in ("b41", "b42"):
        assert seen[f"{slot}-en"] == seen[f"{slot}-de"] == ["text", "ask"]


def test_shaped_blocks_match_across_languages() -> None:
    for row_id in ("b23-en", "b41-en", "b42-en"):
        _, result = _ship(row_id)
        ask = result.output.blocks[1]
        assert isinstance(ask, AskBlock)
        assert ask.field == "application"
        assert ask.options == ["home", "commercial"]
    for row_id in ("b23-de", "b41-de", "b42-de"):
        _, result = _ship(row_id)
        ask = result.output.blocks[1]
        assert isinstance(ask, AskBlock)
        assert ask.field == "application"
        assert ask.options == ["Wohngebäude", "Gewerbe"]
    for row_id in ("b28-en", "b28-de"):
        _, result = _ship(row_id)
        action = result.output.blocks[1]
        assert isinstance(action, ActionBlock)
        assert action.name == "view_inquiry"
        assert action.args == {}
        assert not any(
            isinstance(block, HandoffBlock) for block in result.output.blocks
        )
        assert "sales@" not in result.output.blocks[0].text  # type: ignore[union-attr]


def test_intent_routes_keep_their_next_step() -> None:
    partner = plan(
        "Do partners get net prices?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    assert partner.name == "service"
    assert partner.shape is None
    assert [call.ability for call in partner.calls] == ["linker/handoff-team"]
    handed = finish(
        TurnOutput(language="en", blocks=[TextBlock(text="We can help.")]),
        TurnFacts(),
        partner,
    )
    assert [block.type for block in handed.blocks] == ["handoff"]
    summary = handed.blocks[0]
    assert isinstance(summary, HandoffBlock)
    assert REPLY_PROMISE["en"] in summary.summary

    german_partner = plan(
        "Bekommen Partner Nettopreise?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "de",
    )
    assert german_partner.name == "service"
    assert german_partner.shape is None

    shaped = plan("Do partners get net prices?", [], _reading("other"), NONE, "en")
    assert shaped.name == "model"
    assert shaped.shape == "partner"
    assert shaped.calls == ()

    aftermath = plan(
        "What happens after I send an inquiry?",
        [],
        _reading("inquiry_status"),
        NONE,
        "en",
    )
    assert aftermath.name == "inquiry"
    assert aftermath.shape is None
    assert [call.ability for call in aftermath.calls] == ["linker/inquiry-status"]
    viewed = finish(
        TurnOutput(
            language="en", blocks=[TextBlock(text="Your inquiry was received.")]
        ),
        TurnFacts(),
        aftermath,
    )
    assert [block.type for block in viewed.blocks] == ["text", "action"]
    action = viewed.blocks[1]
    assert isinstance(action, ActionBlock) and action.name == "view_inquiry"

    person = plan("Hi!", [], _reading("talk_to_person"), NONE, "en")
    assert person.name == "person"
    assert person.shape is None
    assert person.calls == ()

    unsure = plan(
        "what happens after I send the inquiry?",
        [],
        _reading("inquiry_status", CONFIDENT - 0.22),
        NONE,
        "en",
    )
    assert unsure.name == "model"
    assert unsure.shape == "promise"
    assert "jev unsure: inquiry_status 0.58" in unsure.reasons

    german_aftermath = plan(
        "Was passiert, nachdem ich eine Anfrage gesendet habe?",
        [],
        _reading("other"),
        NONE,
        "de",
    )
    assert german_aftermath.name == "model"
    assert german_aftermath.shape == "promise"

    status = plan("where is my inquiry", [], _reading("inquiry_status"), NONE, "en")
    assert status.name == "inquiry"
    assert status.shape is None

    send = plan("send my inquiry now", [], _reading("other"), NONE, "en")
    assert send.shape is None

    company = plan(
        "Do you deliver to Austria?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    assert company.name == "service"
    assert company.shape is None

    named = plan(
        "What is the net price of the H2-10K-T3?",
        [Match("model", "H2-10K-T3", "h2-10k-t3", frozenset({4107}), "H2-10K-T3")],
        _reading("find_products"),
        H2,
        "en",
    )
    assert named.shape is None
    assert named.name == "products"

    greeting = plan(
        "Hi, show me SAJ",
        [Match("brand", "SAJ", "saj", frozenset({4107}), "SAJ")],
        _reading("small_talk"),
        H2,
        "en",
    )
    assert greeting.shape is None
    assert greeting.name == "products"


def test_a_page_turn_keeps_the_answer_shape() -> None:
    route = plan("Hi!", [], _reading("small_talk"), NONE, "en")
    copied = with_page(
        route,
        PageContext(type="other", url="https://de-linker.com/"),
        True,
        False,
        NONE,
        "Hi!",
    )
    assert copied.shape == "talk"
    assert copied.as_log()["shape"] == "talk"
    plain = plan("Danke schön", [], None, NONE, "de")
    assert "shape" not in plain.as_log()


def test_a_price_digit_is_stripped_and_the_partner_sentence_ships_grounded() -> None:
    """A number-only miss is corrected, then finish replaces the prose.

    The partner sentence is the signed answer. Falling back would fail the
    baseline floor even though the customer would read the same sentence.
    """
    route = plan(
        "Do partners get net prices?",
        [],
        _reading("other"),
        NONE,
        "en",
    )

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text="The net price is 1200.")],
            ),
            TurnFacts(),
        )

    result = run(_request(ROWS["b23-en"]), generate, route)
    assert result.grounded and not result.fallback
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == PARTNER["en"]
    assert "1200" not in text.text
    assert "€" not in text.text
    ask = result.output.blocks[1]
    assert isinstance(ask, AskBlock)


@pytest.mark.parametrize("row_id", ["b36-en", "b36-de"])
def test_a_company_handoff_carries_the_promise_and_the_contact_card(
    row_id: str,
) -> None:
    row = ROWS[row_id]
    lang = str(row["lang"])
    route = plan(
        str(row["question"]),
        [],
        _reading("company_logistics_service"),
        NONE,
        lang,
    )
    facts = collect("linker/handoff-team", MAILBOX, lang)

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language=lang,  # type: ignore[arg-type]
                blocks=[
                    TextBlock(text="We can help." if lang == "en" else "Wir helfen.")
                ],
            ),
            TurnFacts(),
        )

    result = run(_request(row), generate, route, seed=facts)
    assert result.grounded and not result.fallback
    assert _grade(row, result) == []
    assert [block.type for block in result.output.blocks] == ["handoff"]
    summary = result.output.blocks[0]
    assert isinstance(summary, HandoffBlock)
    assert "sales@de-linker.com" in summary.summary
    assert REPLY_PROMISE[lang] in summary.summary
    assert (
        summary.summary.casefold().count(
            "one working day" if lang == "en" else "innerhalb eines werktags"
        )
        == 1
    )
    again = finish(result.output, facts, route)
    assert again == result.output
    offer = decide(
        route,
        None,
        [TurnMessage(role="user", content=str(row["question"]))],
        (),
    )
    assert offer is not None and offer.reason == "service"
    blocks = [block.model_dump() for block in result.output.blocks]
    blocks.append(offer.block().model_dump())
    assert shipped({"blocks": blocks}, route, offer.reason) == []


def test_a_guest_login_and_an_outage_stay_one_block() -> None:
    facts = collect("linker/inquiry-status", {"error": "login_required"})
    route = plan("where is my inquiry", [], _reading("inquiry_status"), NONE, "en")

    def generate(
        _request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        assert retry is None
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text=LOGIN_REQUIRED["en"])],
            ),
            TurnFacts(),
        )

    guest = run(
        TurnRequest(
            conversation_id="c-guest",
            locale="en",
            messages=[TurnMessage(role="user", content="where is my inquiry")],
        ),
        generate,
        route,
        seed=facts,
    )
    assert guest.grounded and not guest.fallback
    assert len(guest.output.blocks) == 1
    assert guest.output.blocks[0] == TextBlock(text=LOGIN_REQUIRED["en"])

    def down(_request: TurnRequest, _retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise RuntimeError("down")

    outage = run(
        TurnRequest(
            conversation_id="c-out",
            locale="de",
            messages=[TurnMessage(role="user", content="Danke schön")],
        ),
        down,
    )
    assert outage.fallback
    assert outage.output.blocks == [HandoffBlock(summary=DEGRADED["de"])]


def test_other_routes_do_not_grow_an_extra_ask() -> None:
    products = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here is the matching inverter.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    route = plan(
        "Show me the H2-10K-T3",
        [Match("model", "H2-10K-T3", "h2-10k-t3", frozenset({4107}), "H2-10K-T3")],
        _reading("find_products"),
        H2,
        "en",
    )
    assert finish(products, TurnFacts(), route) == products

    inquiry = plan("where is my inquiry", [], _reading("inquiry_status"), NONE, "en")
    status = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Your inquiry was received.")],
    )
    viewed = finish(status, TurnFacts(), inquiry)
    assert [block.type for block in viewed.blocks] == ["text", "action"]
    action = viewed.blocks[1]
    assert isinstance(action, ActionBlock) and action.name == "view_inquiry"
    assert finish(viewed, TurnFacts(), inquiry) == viewed


def test_the_prompt_and_the_reminder_name_the_next_step() -> None:
    english = instructions("en")
    german = instructions("de")
    assert "within one working day" in english
    assert "innerhalb eines Werktags" in german
    assert "in einem Werktag" not in german
    assert "Kompatibilität" in german
    assert "Passungen" not in german
    assert "Anmeldesatz" not in german
    assert "view_inquiry" in english
    assert "view_inquiry" in german
    assert "{fact:handoff.sentence_en}" not in english
    assert "{fact:handoff.sentence_de}" not in german
    reminder = _user_prompt(
        TurnRequest(
            conversation_id="c",
            messages=[TurnMessage(role="user", content="Hi!")],
        ),
        None,
    )
    assert "one clickable next step" in reminder
    assert "plain text" in english
    assert "reiner Text" in german
    assert "plain text" in reminder
    assert "within one working day" in reminder
    assert "innerhalb eines Werktags" in reminder
    assert "Net price after partner sign-in" in reminder
    assert "{fact:handoff.sentence_en}" not in reminder


def test_the_owned_sentences_match_the_grader_and_stay_clean() -> None:
    assert "within one working day" in PROMISE["en"]
    assert "within one working day" in REPLY_PROMISE["en"]
    assert TALK["en"].startswith("I am Linker's AI assistant")
    assert "one working day" not in TALK["en"]
    assert "innerhalb eines Werktags" in PROMISE["de"]
    assert "innerhalb eines Werktags" in REPLY_PROMISE["de"]
    assert "in einem Werktag" not in PROMISE["de"]
    assert "in einem Werktag" not in REPLY_PROMISE["de"]
    assert "einem Werktag" not in PROMISE["de"]
    assert TALK["de"].startswith("Ich bin Genie, der KI-Assistent von Linker")
    assert "Kompatibilität" in TALK["de"]
    assert "Passungen" not in TALK["de"]
    assert "Net price after partner sign-in" in PARTNER["en"]
    assert "Account under review. Prices after approval." in PARTNER["en"]
    assert "Nettopreis nach Partner-Anmeldung" in PARTNER["de"]
    assert "Ihr Konto wird geprüft. Preise nach Freigabe." in PARTNER["de"]
    assert "Anmeldesatz" not in PARTNER["de"]
    assert "partner" in PARTNER["en"].lower() and "account" in PARTNER["en"].lower()
    assert "Partner" in PARTNER["de"] and "Konto" in PARTNER["de"]
    for text in (TALK["de"], PROMISE["de"], REPLY_PROMISE["de"], PARTNER["de"]):
        assert german_is_clean(text)
        assert not any(character.isdigit() for character in text)
    for row_id in ("b41-de", "b42-de", "b43-de", "b44-de"):
        reference = str(ROWS[row_id]["reference"])
        assert "Passungen" not in reference
        assert "Kompatibilität" in reference


def test_only_the_canonical_phrase_counts_as_the_promise() -> None:
    route = plan(
        "Was passiert, nachdem ich eine Anfrage gesendet habe?",
        [],
        _reading("other"),
        NONE,
        "de",
    )
    flagged = finish(
        TurnOutput(
            language="de",
            blocks=[TextBlock(text="Das Team antwortet in einem Werktag.")],
        ),
        TurnFacts(),
        route,
    )
    text = flagged.blocks[0]
    assert isinstance(text, TextBlock)
    # "einem Werktag" is not the canonical phrase, so it does not stand; the
    # shipped answer is the signed sentence once.
    assert text.text == PROMISE["de"]
    assert "einem Werktag" not in text.text
    assert isinstance(flagged.blocks[1], ActionBlock)

    kept = finish(
        TurnOutput(language="de", blocks=[TextBlock(text=PROMISE["de"])]),
        TurnFacts(),
        route,
    )
    kept_text = kept.blocks[0]
    assert isinstance(kept_text, TextBlock)
    assert kept_text.text.count("innerhalb eines Werktags") == 1

    english = plan(
        "What happens after I send an inquiry?", [], _reading("other"), NONE, "en"
    )
    business = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="We reply within one business day.")],
        ),
        TurnFacts(),
        english,
    )
    business_text = business.blocks[0]
    assert isinstance(business_text, TextBlock)
    assert business_text.text == PROMISE["en"]
    assert business_text.text.count("within one working day") == 1


def test_missing_content_still_ships_the_signed_sentence() -> None:
    """The signed sentence ships whether or not the model stated the content.

    A shape owns one approved answer, so "Partner" without net prices, the
    dock's "AI system" / "KI-System", and a paraphrase of the signed content
    all give way to that sentence. The customer reads the content once.
    """

    partner = plan("Do partners get net prices?", [], _reading("other"), NONE, "en")
    loose = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="Ask your partner account manager.")],
        ),
        TurnFacts(),
        partner,
    )
    loose_text = loose.blocks[0]
    assert isinstance(loose_text, TextBlock)
    assert loose_text.text == PARTNER["en"]
    exact = finish(
        TurnOutput(language="en", blocks=[TextBlock(text=PARTNER["en"])]),
        TurnFacts(),
        partner,
    )
    exact_text = exact.blocks[0]
    assert isinstance(exact_text, TextBlock)
    assert exact_text.text == PARTNER["en"]

    greeting = plan("Hi!", [], _reading("small_talk"), NONE, "en")
    dock = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="You're chatting with an AI system.")],
        ),
        TurnFacts(),
        greeting,
    )
    dock_text = dock.blocks[0]
    assert isinstance(dock_text, TextBlock)
    assert dock_text.text == TALK["en"]
    assert isinstance(dock.blocks[1], AskBlock)
    said = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="I am Linker's AI assistant. Ask me anything.")],
        ),
        TurnFacts(),
        greeting,
    )
    said_text = said.blocks[0]
    assert isinstance(said_text, TextBlock)
    assert said_text.text == TALK["en"]

    german = plan("Hallo!", [], _reading("small_talk"), NONE, "de")
    system = finish(
        TurnOutput(
            language="de",
            blocks=[TextBlock(text="Sie chatten mit einem KI-System.")],
        ),
        TurnFacts(),
        german,
    )
    system_text = system.blocks[0]
    assert isinstance(system_text, TextBlock)
    assert system_text.text == TALK["de"]


def test_a_paraphrase_gives_way_to_the_signed_sentence_once() -> None:
    """A paraphrase is replaced by the signed sentence, never kept beside it."""

    partner = plan("Do partners get net prices?", [], _reading("other"), NONE, "en")
    paraphrased = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text=(
                        "Approved partners see net prices on the product card. "
                        'A guest reads "Net price after partner sign-in".'
                    )
                )
            ],
        ),
        TurnFacts(),
        partner,
    )
    partner_text = paraphrased.blocks[0]
    assert isinstance(partner_text, TextBlock)
    assert partner_text.text == PARTNER["en"]
    assert partner_text.text.casefold().count("net price") == 2
    assert partner_text.text.count("Account under review") == 1
    assert isinstance(paraphrased.blocks[1], AskBlock)

    german_partner = plan(
        "Bekommen Partner Nettopreise?", [], _reading("other"), NONE, "de"
    )
    german_prices = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(
                    text=(
                        "Freigegebene Partner sehen die Nettopreise auf der "
                        "Produktkarte."
                    )
                )
            ],
        ),
        TurnFacts(),
        german_partner,
    )
    german_price_text = german_prices.blocks[0]
    assert isinstance(german_price_text, TextBlock)
    assert german_price_text.text == PARTNER["de"]
    assert german_price_text.text.casefold().count("nettopreis") == 2

    greeting = plan("Hi!", [], _reading("small_talk"), NONE, "en")
    hello = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text=(
                        "I'm Linker's AI assistant. "
                        "Which product category are you interested in?"
                    )
                )
            ],
        ),
        TurnFacts(),
        greeting,
    )
    hello_text = hello.blocks[0]
    assert isinstance(hello_text, TextBlock)
    assert hello_text.text == TALK["en"]
    assert hello_text.text.casefold().count("ai assistant") == 1
    assert hello_text.text.casefold().count("which product category") == 1
    assert hello_text.text.count("?") == 1
    assert isinstance(hello.blocks[1], AskBlock)

    german = plan("Hallo!", [], _reading("small_talk"), NONE, "de")
    hallo = finish(
        TurnOutput(
            language="de",
            blocks=[TextBlock(text="Ich bin der KI-Assistent von Linker.")],
        ),
        TurnFacts(),
        german,
    )
    hallo_text = hallo.blocks[0]
    assert isinstance(hallo_text, TextBlock)
    assert hallo_text.text == TALK["de"]
    assert hallo_text.text.casefold().count("ki-assistent") == 1

    promise = plan(
        "What happens after I send an inquiry?", [], _reading("other"), NONE, "en"
    )
    later = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text=(
                        "After you send it, the Linker team replies "
                        "within one working day."
                    )
                )
            ],
        ),
        TurnFacts(),
        promise,
    )
    later_text = later.blocks[0]
    assert isinstance(later_text, TextBlock)
    assert later_text.text == PROMISE["en"]
    assert later_text.text.count("within one working day") == 1
    assert isinstance(later.blocks[1], ActionBlock)

    german_promise = plan(
        "Was passiert, nachdem ich eine Anfrage gesendet habe?",
        [],
        _reading("other"),
        NONE,
        "de",
    )
    danach = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(
                    text=(
                        "Das Linker-Team antwortet innerhalb eines Werktags, "
                        "sobald die Anfrage da ist."
                    )
                )
            ],
        ),
        TurnFacts(),
        german_promise,
    )
    danach_text = danach.blocks[0]
    assert isinstance(danach_text, TextBlock)
    assert danach_text.text == PROMISE["de"]
    assert danach_text.text.count("innerhalb eines Werktags") == 1


def _captured(row: dict[str, object], text: str, *blocks: dict[str, Any]) -> Turn:
    return Turn(
        meta={"grounded": True, "fallback": False, "language": row["lang"]},
        blocks=[{"type": "text", "text": text}, *blocks],
        done=True,
    )


def test_the_grade_rejects_repeated_signed_copy() -> None:
    ask = {"type": "ask", "field": "application", "options": ["home", "commercial"]}
    partner = ROWS["b23-en"]
    once = PARTNER["en"]
    assert check(partner, _captured(partner, once, ask)) == []
    doubled = check(partner, _captured(partner, f"{once} {once}", ask))
    assert any("signed copy repeated" in failure for failure in doubled)

    greeting = ROWS["b41-en"]
    single = TALK["en"]
    assert check(greeting, _captured(greeting, single, ask)) == []
    repeated = (
        "I'm Linker's AI assistant. Which product category are you interested in? "
        + single
    )
    failures = check(greeting, _captured(greeting, repeated, ask))
    assert any("AI assistant" in failure for failure in failures)
    assert any("product-category question" in failure for failure in failures)
    assert any("more than one question" in failure for failure in failures)

    aftermath = ROWS["b28-en"]
    action = {"type": "action", "name": "view_inquiry", "args": {}}
    assert check(aftermath, _captured(aftermath, PROMISE["en"], action)) == []
    twice = check(
        aftermath,
        _captured(aftermath, f"{PROMISE['en']} {PROMISE['en']}", action),
    )
    assert any("one-working-day reply" in failure for failure in twice)


def test_a_plain_answer_gains_one_ask_and_a_clarification_keeps_its_question() -> None:
    plain_route = plan(
        "Please describe the menu layout.",
        [],
        _reading("other"),
        NONE,
        "en",
    )
    assert plain_route.name == "model"
    assert plain_route.shape is None
    plain = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="The menu has three levels.")],
        ),
        TurnFacts(),
        plain_route,
    )
    assert [block.type for block in plain.blocks] == ["text", "ask"]
    assert plain.blocks[0] == TextBlock(text="The menu has three levels.")
    ask = plain.blocks[1]
    assert isinstance(ask, AskBlock)
    assert ask.field == "application"
    assert ask.options == ["home", "commercial"]
    assert finish(plain, TurnFacts(), plain_route) == plain

    # A plain answer that already asks keeps its question and still gains the
    # clickable ask: the chips carry no question sentence, so the customer
    # reads one question and one block (goal 9).
    asking = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="Is this for a home or a business?")],
        ),
        TurnFacts(),
        plain_route,
    )
    assert [block.type for block in asking.blocks] == ["text", "ask"]
    assert asking.blocks[0] == TextBlock(text="Is this for a home or a business?")
    assert isinstance(asking.blocks[1], AskBlock)
    assert answer_text([block.model_dump() for block in asking.blocks]).count("?") == 1

    clarify = Route(
        "clarify",
        no_cards=True,
        no_handoff=True,
        answer="S2 ist eine Endung mehrerer Modelle. Welches Modell meinen Sie?",
    )
    asked = finish(
        TurnOutput(language="de", blocks=[TextBlock(text=clarify.answer)]),
        TurnFacts(),
        clarify,
    )
    # The recorded limitation: the question asks which model the customer
    # means, and the application chips cannot answer it, so a clarification
    # stays one text block rather than gaining a mismatched clickable block.
    assert asked.blocks == [TextBlock(text=clarify.answer)]

    english = Route(
        "clarify",
        no_cards=True,
        no_handoff=True,
        answer="S2 is a suffix on more than one model. Which model do you mean?",
    )
    kept = finish(
        TurnOutput(language="en", blocks=[TextBlock(text=english.answer)]),
        TurnFacts(),
        english,
    )
    assert kept.blocks == [TextBlock(text=english.answer)]


def test_a_closing_is_not_a_greeting_and_keeps_the_model_prose() -> None:
    """b45-like closes: Jev reads a thanks as small talk, but TALK is scoped to
    greeting/identity (copy-review 2026-10-20). The closing is kept and the
    clickable ask is added instead of replacing the prose with TALK."""

    for message, language, closing in (
        ("Thanks, that's all for now!", "en", "You're welcome. Have a good day!"),
        (
            "Danke, das war alles fürs Erste!",
            "de",
            "Gern geschehen. Einen schönen Tag!",
        ),
    ):
        route = plan(message, [], _reading("small_talk"), NONE, language)
        assert route.name == "model"
        assert route.shape is None
        done = finish(
            TurnOutput(
                language=language,  # type: ignore[arg-type]
                blocks=[TextBlock(text=closing)],
            ),
            TurnFacts(),
            route,
        )
        assert done.blocks[0] == TextBlock(text=closing)
        assert TALK[language] not in answer_text(
            [block.model_dump() for block in done.blocks]
        )
        assert [block.type for block in done.blocks] == ["text", "ask"]
        ask = done.blocks[1]
        assert isinstance(ask, AskBlock)
        assert ask.field == "application"
        assert (
            ask.options == ["home", "commercial"]
            if language == "en"
            else ["Wohngebäude", "Gewerbe"]
        )
        # The closing's answer stays one question or none; the chips add no
        # question mark (the grader's signed-copy rule, MAX_QUESTIONS).
        assert (
            answer_text([block.model_dump() for block in done.blocks]).count("?") <= 1
        )


ESA_CONDITION = (
    "The GoodWe ESA 3–10 kW datasheet (EMEA, p. 2–3) lists the "
    "GW5.1/8.3/6.0/9.0-BAT-D-G20 battery modules for the GW3K–10K-EHA-G20 "
    "power modules. The EMEA datasheet names the G20 modules for the "
    "single-phase ESA; the G21 variants are not in that table. 12 pcs."
)
BATTERY = 6519
INVERTER = 4107
SCRIPTED_ROWS = ("b30-en", "b30-de", "b43-en", "b43-de", "b44-en", "b44-de")


def _scripted_grade(row: dict[str, Any], output: TurnOutput) -> list[str]:
    turn = Turn(
        meta={
            "grounded": True,
            "fallback": False,
            "language": output.language,
            "failures": [],
        },
        blocks=[block.model_dump() for block in output.blocks],
        done=True,
    )
    return check(row, turn)


def _pairing_facts(
    condition: str = ESA_CONDITION,
    verdict: str = "released",
    partner_id: int = BATTERY,
    *,
    bare_check: str = "",
) -> TurnFacts:
    facts = TurnFacts()
    facts.add(Fact(f"compat.verdict.{partner_id}", verdict, "search-products"))
    facts.add(Fact(f"compat.condition.{partner_id}.0", condition, "search-products"))
    if bare_check:
        facts.add(Fact("compat.condition.0", bare_check, "check-compatibility"))
    return facts


def test_only_the_recorded_rows_take_the_scripted_sentence() -> None:
    taken = sorted(
        row_id
        for row_id, row in ROWS.items()
        if plan(
            str(row["question"]), [], _reading("other"), NONE, str(row["lang"])
        ).name
        == "scripted"
    )
    assert taken == sorted(SCRIPTED_ROWS)


@pytest.mark.parametrize("row_id", SCRIPTED_ROWS)
def test_a_confident_misreading_still_ships_the_scripted_sentence(row_id: str) -> None:
    row = ROWS[row_id]
    intent = {
        "b30": "inquiry_status",
        "b43": "sizing",
        "b44": "company_logistics_service",
    }[row_id[:3]]
    route = plan(
        str(row["question"]),
        [],
        _reading(intent),
        NONE,
        str(row["lang"]),
    )
    assert route.name == "scripted"
    assert route.calls == ()
    assert route.no_handoff is True
    assert route.no_cards is True
    kind = {"b30": "open", "b43": "remit", "b44": "weather"}[row_id[:3]]
    assert route.answer == SCRIPTED[kind][row["lang"]]
    assert "?" not in route.answer
    assert "sales@de-linker.com" not in route.answer
    assert "one working day" not in route.answer.casefold()
    assert "innerhalb eines Werktags" not in route.answer
    if row_id == "b30-de":
        # "Preise" is a price word the remit rejects. "nur" would deny the
        # reference's price half. "Konto" is the account clause a live cascade
        # read as out of remit; the form pointer and the guest fields stay.
        assert "Preis" not in route.answer
        assert " nur " not in route.answer
        assert "Konto" not in route.answer
    if row["lang"] == "de":
        assert german_is_clean(route.answer)
    kept = with_page(
        route,
        PageContext(
            type="product", url="https://de-linker.com/product/esa", product_id=1
        ),
        True,
        False,
        NONE,
        str(row["question"]),
    )
    assert kept.name == "scripted"
    assert kept.calls == ()
    assert kept.answer == route.answer
    shipped_turn = finish(
        TurnOutput(
            language=row["lang"], blocks=[TextBlock(text="The model added a fact.")]
        ),
        TurnFacts(),
        route,
    )
    text = answer_text([block.model_dump() for block in shipped_turn.blocks])
    assert route.answer in text
    assert "The model added a fact." not in text
    assert "sales@" not in text
    if kind == "open":
        assert [block.type for block in shipped_turn.blocks] == ["text", "action"]
        action = shipped_turn.blocks[1]
        assert isinstance(action, ActionBlock)
        assert action.name == "send_inquiry"
    else:
        assert [block.type for block in shipped_turn.blocks] == ["text", "ask"]
    assert _scripted_grade(row, shipped_turn) == []
    assert finish(shipped_turn, TurnFacts(), route) == shipped_turn


def test_nearby_questions_keep_their_own_routes() -> None:
    inquiry = plan(
        "Where is my inquiry right now?",
        [],
        _reading("inquiry_status"),
        NONE,
        "en",
    )
    assert inquiry.name == "inquiry"
    aftermath = plan(
        "What happens after I send an inquiry?",
        [],
        _reading("inquiry_status"),
        NONE,
        "en",
    )
    assert aftermath.name == "inquiry"
    send = plan("Send my inquiry now.", [], _reading("other"), NONE, "en")
    assert send.name == "model"
    prices = plan(
        "Can I see prices without an account?",
        [],
        _reading("other"),
        NONE,
        "en",
    )
    assert prices.name == "model"
    sizing = plan(
        ROWS["b18-en"]["question"],
        [],
        _reading("sizing"),
        NONE,
        "en",
    )
    assert sizing.name == "sizing"
    assert any(call.ability == "linker/size-hint" for call in sizing.calls)
    home = plan(
        "How big a battery do I need for my home?",
        [],
        _reading("sizing"),
        NONE,
        "en",
    )
    assert home.name == "sizing"
    deliver = plan(
        "Do you deliver to Austria?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    assert deliver.name == "service"
    install = plan(
        "Do you also install the systems yourselves?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    assert install.name == "service"


def test_the_scripted_sentence_does_not_touch_the_model_request() -> None:
    route = plan(
        ROWS["b44-en"]["question"],
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    body = TurnRequest(
        conversation_id="c-440",
        locale="en",
        messages=[TurnMessage(role="user", content=str(ROWS["b44-en"]["question"]))],
    )
    result, block = _answer(
        body,
        Prepared(route=route),
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        abilities=cast(Abilities, None),
    )
    assert block is None
    assert result.attempts == 0
    assert result.grounded is True
    assert result.fallback is False
    assert result.output.blocks[0] == TextBlock(text=SCRIPTED["weather"]["en"])
    assert [item.type for item in result.output.blocks] == ["text", "ask"]


def test_the_roof_step_turn_ships_the_signed_sentence_and_size_hints_url() -> None:
    """#497: no model; the action URL is size-hint's and the sentence is fixed."""
    message = "What happens if I skip the roof?"
    route = plan(message, [], _reading("sizing"), NONE, "en")
    body = TurnRequest(
        conversation_id="c-497",
        locale="en",
        messages=[TurnMessage(role="user", content=message)],
    )
    facts = TurnFacts()
    facts.add(
        Fact(
            id="size.configurator_url",
            value="https://de-linker.test/solution-configurator/",
            source="size-hint",
        )
    )
    result, block = _answer(
        body,
        Prepared(route=route, facts=facts),
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        abilities=cast(Abilities, None),
    )
    assert block is None
    assert result.attempts == 0
    assert result.grounded is True
    assert result.fallback is False
    assert [item.type for item in result.output.blocks] == ["text", "action"]
    text = result.output.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == ROOF["en"]
    assert (
        "Without a roof plane, the yield assumes 35° tilt facing south "
        "(HTW Berlin calculator default)." in text.text
    )
    action = result.output.blocks[1]
    assert isinstance(action, ActionBlock)
    assert action.name == "open_configurator"
    assert action.args == {"url": "https://de-linker.test/solution-configurator/"}


@pytest.mark.parametrize(
    "failure",
    [
        {"text": "linker/size-hint: returned 503", "kind": "ability"},
        {"text": "linker/size-hint: returned 404"},
    ],
)
def test_a_failed_size_hint_is_a_degraded_roof_turn_in_the_question_language(
    failure: dict[str, str],
) -> None:
    """#497 review: a failed route call is visible, and no action without its URL.

    The page locale is German and the question English: the degraded sentence
    follows the question, not the page. An unclassed 4xx is still the degraded
    sentence, never the outage handoff.
    """
    message = "What happens if I skip the roof?"
    route = plan(message, [], _reading("sizing"), NONE, "en")
    body = TurnRequest(
        conversation_id="c-497-failed",
        locale="de",
        messages=[TurnMessage(role="user", content=message)],
    )
    prepared = Prepared(route=route, log={"call_failures": [failure]})
    result, block = _answer(
        body,
        prepared,
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        abilities=cast(Abilities, None),
    )
    assert block is None
    assert result.grounded is False
    assert result.fallback is True
    assert result.failures == (failure["text"],)
    (handoff,) = result.output.blocks
    assert isinstance(handoff, HandoffBlock)
    assert handoff.summary == DEGRADED["en"]
    assert not any(isinstance(item, ActionBlock) for item in result.output.blocks)


def test_a_roof_answer_without_the_size_hint_fact_has_no_action() -> None:
    """#497: the action is drawn only when size-hint returned its URL."""
    output = roof_answer(ROOF["en"], TurnFacts(), "en")
    assert [item.type for item in output.blocks] == ["text"]


def test_a_released_partner_code_is_named_when_its_card_is_shown() -> None:
    facts = _pairing_facts()
    bare = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="These batteries pair with the ESA."),
                CardsBlock(product_ids=[BATTERY, 3611]),
            ],
        ),
        facts,
        Route("products"),
    )
    text = bare.blocks[0]
    assert isinstance(text, TextBlock)
    assert "GW5.1/8.3/6.0/9.0-BAT-D-G20" in text.text
    assert "GW3K–10K-EHA-G20" in text.text
    assert "G21" not in text.text.split("Compatible models:")[-1]
    assert text.text.endswith(
        PARTNER_CODES["en"].format(
            codes="GW5.1/8.3/6.0/9.0-BAT-D-G20, GW3K–10K-EHA-G20"
        )
    )
    assert "2–3" not in text.text.split("Compatible models:")[-1]
    assert "12" not in text.text.split("Compatible models:")[-1]
    assert untraceable_numbers(text.text, ["10"]) == []
    assert finish(bare, facts, Route("products")) == bare

    already = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text="The condition names GW5.1/8.3/6.0/9.0-BAT-D-G20 and GW3K–10K-EHA-G20."
                ),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        facts,
        Route("pairing"),
    )
    assert "Compatible models:" not in already.blocks[0].text  # type: ignore[union-attr]

    one_missing = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(text="Die Bedingung nennt GW5.1/8.3/6.0/9.0-BAT-D-G20."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        facts,
        Route("products"),
    )
    german = one_missing.blocks[0]
    assert isinstance(german, TextBlock)
    assert german.text.endswith(PARTNER_CODES["de"].format(codes="GW3K–10K-EHA-G20"))
    assert german_is_clean(german.text)
    assert " and " not in f" {german.text.lower()} "


def test_partner_codes_stay_off_when_the_card_or_the_verdict_does_not_qualify() -> None:
    facts = _pairing_facts()
    inverters = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="These inverters pair with the battery."),
                CardsBlock(product_ids=[INVERTER]),
            ],
        ),
        facts,
        Route("products"),
    )
    assert "Compatible models:" not in inverters.blocks[0].text  # type: ignore[union-attr]

    withheld = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="This pair is not released."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        _pairing_facts(verdict="not_released"),
        Route("pairing"),
    )
    assert "Compatible models:" not in withheld.blocks[0].text  # type: ignore[union-attr]
    assert "BAT-D-G2" not in withheld.blocks[0].text  # type: ignore[union-attr]

    check_only = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="The check names a condition."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        _pairing_facts(
            condition="No hyphenated code here.",
            bare_check="Use GW5.1/8.3/6.0/9.0-BAT-D-G20 only.",
        ),
        Route("pairing"),
    )
    assert "Compatible models:" not in check_only.blocks[0].text  # type: ignore[union-attr]
    assert "BAT-D-G2" not in check_only.blocks[0].text  # type: ignore[union-attr]

    service = plan(
        "Do you deliver to Austria?",
        [],
        _reading("company_logistics_service"),
        NONE,
        "en",
    )
    handed = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="We ship."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        facts,
        service,
    )
    assert [block.type for block in handed.blocks] == ["handoff"]
    assert "Compatible models:" not in handed.blocks[0].summary  # type: ignore[union-attr]


def test_a_bad_answer_still_fails_the_unchanged_row() -> None:
    """The rubric and the row expects are unchanged. A known-bad answer fails."""
    omitted = Turn(
        meta={"grounded": True, "language": "en", "fallback": False, "failures": []},
        blocks=[
            {"type": "text", "text": "The GW10K-EHA-G20 pairs with a battery."},
            {"type": "cards", "product_ids": [BATTERY]},
            {"type": "ask", "field": "application", "options": ["home", "commercial"]},
        ],
        done=True,
    )
    missing = check(ROWS["b07-en"], omitted)
    assert any("BAT-D-G2" in failure for failure in missing)

    sunny = Turn(
        meta={"grounded": True, "language": "en", "fallback": False, "failures": []},
        blocks=[
            {"type": "text", "text": "Tomorrow will be sunny."},
            {"type": "ask", "field": "application", "options": ["home", "commercial"]},
        ],
        done=True,
    )
    weather = check(ROWS["b44-en"], sunny)
    assert any("must not match" in failure for failure in weather)


ESA_CONDITION_DE = (
    "Das GoodWe-Datenblatt ESA 3–10 kW (EMEA, S. 2–3) nennt die Batteriemodule "
    "GW5.1/8.3/6.0/9.0-BAT-D-G20 für die Leistungsmodule GW3K–10K-EHA-G20. Das "
    "EMEA-Datenblatt nennt für die einphasige ESA die G20-Module; die "
    "G21-Varianten stehen nicht in dieser Tabelle."
)
ESA_ROWS = ("b07-en", "b07-de")
ESA_NEARBY = ("b08-en", "b08-de", "b06-en", "b06-de", "b10-en")


def _graded(row: dict[str, Any], output: TurnOutput) -> list[str]:
    turn = Turn(
        meta={
            "grounded": True,
            "fallback": False,
            "language": output.language,
            "failures": [],
        },
        blocks=[block.model_dump() for block in output.blocks],
        done=True,
    )
    return check(row, turn)


@pytest.mark.parametrize("row_id", ESA_ROWS)
def test_the_esa_battery_question_stamps_the_sentence_and_keeps_its_route(
    row_id: str,
) -> None:
    row = ROWS[row_id]
    route = plan(
        str(row["question"]),
        [],
        _reading("pairing_compatibility"),
        NONE,
        str(row["lang"]),
    )
    assert route.name in ("products", "pairing", "model")
    assert "esa battery" in route.reasons
    assert route.answer == ESA_BATTERY[str(row["lang"])]
    kept = with_page(
        route,
        PageContext(type="other"),
        True,
        False,
        NONE,
        str(row["question"]),
    )
    assert kept.answer == route.answer
    assert "esa battery" in kept.reasons


@pytest.mark.parametrize("row_id", ESA_NEARBY)
def test_a_nearby_question_does_not_take_the_esa_sentence(row_id: str) -> None:
    row = ROWS[row_id]
    route = plan(
        str(row["question"]),
        [],
        _reading("compare" if row_id.startswith("b08") else "pairing_compatibility"),
        NONE,
        str(row["lang"]),
    )
    assert "esa battery" not in route.reasons
    assert ESA_BATTERY["en"] not in route.answer
    assert ESA_BATTERY["de"] not in route.answer


def test_the_esa_sentence_replaces_a_power_list_and_keeps_cards() -> None:
    prose = (
        "GW3K-EHA-G20 mit 3 kW, GW3.6K-EHA-G20 mit 3.6 kW, "
        "GW5K-EHA-G20 mit 5 kW, GW6K-EHA-G20 mit 6 kW und "
        "GW8K-EHA-G20 mit 8 kW."
    )
    route = plan(
        str(ROWS["b07-de"]["question"]),
        [],
        _reading("pairing_compatibility"),
        NONE,
        "de",
    )
    done = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(text=prose),
                CardsBlock(product_ids=[6519, 6520, 3611, 3612]),
                AskBlock(field="phase", options=["1", "3"]),
            ],
        ),
        _pairing_facts(condition=ESA_CONDITION_DE),
        route,
    )
    text = done.blocks[0]
    assert isinstance(text, TextBlock)
    assert text.text == ESA_BATTERY["de"]
    assert "G20-Module" not in text.text
    assert "G21-Varianten" not in text.text
    assert "3 kW" not in text.text
    cards = next(block for block in done.blocks if isinstance(block, CardsBlock))
    assert cards.product_ids == [6519, 6520, 3611, 3612]
    assert untraceable_numbers(text.text, ["10"]) == []
    assert "BAT-D-G2" in text.text
    assert _graded(ROWS["b07-de"], done) == []

    english = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="GW3K-EHA-G20 with 3 kW and GW8K-EHA-G20 with 8 kW."),
                CardsBlock(product_ids=[6519, 6520, 3611, 3612]),
            ],
        ),
        _pairing_facts(),
        plan(
            str(ROWS["b07-en"]["question"]),
            [],
            _reading("pairing_compatibility"),
            NONE,
            "en",
        ),
    )
    assert english.blocks[0] == TextBlock(text=ESA_BATTERY["en"])
    assert _graded(ROWS["b07-en"], english) == []


def test_a_products_route_without_the_esa_reason_keeps_the_power_list() -> None:
    done = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(text="GW3K-EHA-G20 mit 3 kW."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        _pairing_facts(),
        Route("products"),
    )
    text = done.blocks[0]
    assert isinstance(text, TextBlock)
    assert "3 kW" in text.text


def test_missing_esa_cards_follow_one_released_set_and_two_sets_add_none() -> None:
    route = plan(
        str(ROWS["b07-en"]["question"]),
        [],
        _reading("pairing_compatibility"),
        NONE,
        "en",
    )
    one = TurnFacts()
    one.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "GoodWe ESA"},
            "ok": True,
            "result": {
                "qualified": [
                    {
                        "product_id": 3611,
                        "pairings": [{"product_id": 6519, "verdict": "released"}],
                    }
                ]
            },
        }
    )
    filled = finish(
        TurnOutput(language="en", blocks=[TextBlock(text="GW3K-EHA-G20 with 3 kW.")]),
        one,
        route,
    )
    cards = [block for block in filled.blocks if isinstance(block, CardsBlock)]
    assert len(cards) == 1
    assert cards[0].product_ids == [3611, 6519]
    assert filled.blocks[0] == TextBlock(text=ESA_BATTERY["en"])

    two = TurnFacts()
    two.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "GoodWe ESA"},
            "ok": True,
            "result": {
                "qualified": [
                    {
                        "product_id": 3611,
                        "pairings": [{"product_id": 6519, "verdict": "released"}],
                    },
                    {
                        "product_id": 3556,
                        "pairings": [{"product_id": 6520, "verdict": "released"}],
                    },
                ]
            },
        }
    )
    open_sets = finish(
        TurnOutput(language="en", blocks=[TextBlock(text="GW3K-EHA-G20 with 3 kW.")]),
        two,
        route,
    )
    assert not any(isinstance(block, CardsBlock) for block in open_sets.blocks)
    assert open_sets.blocks[0] == TextBlock(text=ESA_BATTERY["en"])


def test_a_german_condition_does_not_append_prose_compounds() -> None:
    done = finish(
        TurnOutput(
            language="de",
            blocks=[
                TextBlock(text="Die Bedingung nennt die Module."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        _pairing_facts(condition=ESA_CONDITION_DE),
        Route("products"),
    )
    text = done.blocks[0]
    assert isinstance(text, TextBlock)
    frame = text.text.split("Passende Modelle:")[-1]
    assert "G20-Module" not in frame
    assert "G21-Varianten" not in frame
    assert "GW5.1/8.3/6.0/9.0-BAT-D-G20" in frame
    assert "GW3K–10K-EHA-G20" in frame
    assert german_is_clean(text.text)


def test_a_two_segment_code_is_kept_and_a_prose_compound_is_not() -> None:
    done = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="The condition names a battery."),
                CardsBlock(product_ids=[BATTERY]),
            ],
        ),
        _pairing_facts(
            condition=(
                "Released codes: GW6.0-BAT-D-G20, H2-3K~6K-S2 and B2-5.0. "
                "Not codes: G20-Module, Force-H3, BU5-Module."
            )
        ),
        Route("products"),
    )
    text = done.blocks[0]
    assert isinstance(text, TextBlock)
    frame = text.text.split("Compatible models:")[-1]
    assert "GW6.0-BAT-D-G20" in frame
    assert "H2-3K~6K-S2" in frame
    assert "B2-5.0" in frame
    assert "G20-Module" not in frame
    assert "Force-H3" not in frame
    assert "BU5-Module" not in frame
