"""Every shaped answer carries its next step (#394).

The eight baseline rows are graded here with the deterministic checker.
Judge rows (b23, b41, b42) still need a judge for a full live pass; an empty
list means the floors and the row's expect, including the next step, hold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from baseline.grade import Turn, answer_text, check

from linker_genie.agent import _user_prompt, instructions
from linker_genie.contact import decide
from linker_genie.cycle import TurnResult, run
from linker_genie.facts import TurnFacts, collect
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
    LOGIN_REQUIRED,
    PARTNER,
    PROMISE,
    REPLY_PROMISE,
    TALK,
    finish,
    german_is_clean,
)

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


def test_a_price_digit_falls_back_to_the_partner_sentence() -> None:
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
    assert result.fallback and not result.grounded
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
    weather = plan(
        "What's the weather going to be like tomorrow?",
        [],
        _reading("other"),
        NONE,
        "en",
    )
    assert weather.name == "model"
    assert weather.shape is None
    plain = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="I have no weather data.")],
        ),
        TurnFacts(),
        weather,
    )
    assert [block.type for block in plain.blocks] == ["text", "ask"]
    assert plain.blocks[0] == TextBlock(text="I have no weather data.")
    ask = plain.blocks[1]
    assert isinstance(ask, AskBlock)
    assert ask.field == "application"
    assert ask.options == ["home", "commercial"]
    assert finish(plain, TurnFacts(), weather) == plain

    # A plain answer that already asks keeps its question and still gains the
    # clickable ask: the chips carry no question sentence, so the customer
    # reads one question and one block (goal 9).
    asking = finish(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="Is this for a home or a business?")],
        ),
        TurnFacts(),
        weather,
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
