"""Which language an answer uses (#374).

The customer's last message wins when it is clearly English or clearly German.
A language-neutral message (a bare model code, an emoji, a number) and a
question that mixes both languages follow the page locale. Mixed language has
no public precedent (dossier 2026-10-19-genie-campaign-gaps §1.13); the floor
that does is "a German question is answered in German", applied here to both
languages. Brands and model codes are not evidence: they are the same words
on either page. A single clear content word (price, Preis, datasheet) is
evidence. An answer that mixes both languages fails the check.

The cycle asks the model once when an answer breaks the rule, then ships the
template in the required language. A violating answer is not returned. The
check reads the hydrated answer, price lines included.
"""

from __future__ import annotations

import re
from typing import Any

from linker_genie.schema import (
    AskBlock,
    CardsBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnOutput,
    TurnRequest,
)

# Closed-class words that are one language and not the other. Shared words
# (in, was, am, will, so, an, also) are in neither list: one of them must not
# flip the answer. "an" and "also" are German as well as English. A word the
# lists do not know — a brand, a model, "home" — is not evidence either, so a
# bare code stays language-neutral. A content word that is only one language
# (price, Preis, datasheet, Empfehlung) is evidence on its own.
_ENGLISH = frozenset(
    """
    a the and or with for of to from on at by which what how does did do
    is are be been can could would should your you this that these those our
    my please show tell where when why who not have has about between than
    into work works any some there here only just but if we they them
    their it its batteries battery price prices datasheet availability
    """.split()
)
_GERMAN = frozenset(
    """
    der die das den dem des ein eine einer einem einen eines und oder mit
    für fuer von zu zum zur auf aus bei nach über ueber welche welcher
    welches welchen welchem wie wo warum wieso nicht kein keine keinem
    keinen keiner ist sind bin bist seid haben habe habt hat ich sie ihnen
    ihr ihre ihrer ihrem ihren ihres mein meine meinem meinen meiner bitte
    auch dass wenn dann noch schon aber als bis durch ohne gegen um kann
    können koennen muss müssen muessen soll sollen wird werden wurde wurden
    passen passt batterien batterie speicher preis preise empfehlung
    empfehlungen kosten lieferzeit lieferzeiten
    vom beim
    """.split()
)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_PLACEHOLDER = re.compile(r"\{fact:[^}]*\}")
# The ampere unit is an "A" after a number ("63 A", "63A"). "Typ A" / "type A"
# is the RCD characteristic. lower() would turn that token into the English
# article (#396). The article in "a battery" has no digit and no "Typ"/"type"
# in front and still counts. `im` and `ins` are not in the German list: they
# are also English ("Im looking", "ins and outs").
_UNIT_A = re.compile(r"(?<=\d)\s*[Aa]\b|\b(?:typ|type)\s+[Aa]\b", re.IGNORECASE)
# A street name is an address, not a language vote (#404).
_ADDRESS = re.compile(r"\b[\w]*?(?:straße|strasse)\b", re.IGNORECASE)
# Quoted page text is data. A German sentence inside quotes does not vote.
# A quote is one line: both arms run to the closing mark, with no character
# cap. There is no published cap. The old ASCII arm `{0,500}` left a longer
# quotation in the vote, so its words still counted (#396, #404).
_QUOTED = re.compile(r"„[^“”]*[“”]|\"[^\"\n]*\"")
_NAMES = {"en": "English", "de": "German"}
# The retry reason starts with this. agent._user_prompt treats that prefix as
# a language re-ask, not a grounding failure.
LANGUAGE_RETRY_PREFIX = "answer in "
# Tools whose `lang` argument chooses customer-visible text. size-hint
# accepts lang and ignores it (#393): the route log and the wire stay the
# stated-fields dict (#365), so lang is not added here.
# check-compatibility, inquiry-status and handoff-team reject a lang field.
_LANG_TOOLS = frozenset(
    {
        "linker/search-products",
        "linker/get-product",
        "linker/compare-products",
        "linker/search-knowledge",
    }
)


def page_language(locale: str) -> Locale:
    """`de` for a German page locale, otherwise `en` (template.language_of)."""
    return "de" if locale.startswith("de") else "en"


def customer_message(request: TurnRequest) -> str:
    """The last thing the customer wrote, or empty when they have not."""
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return ""


def _prepare(text: str) -> str:
    """Drop units, addresses and quotations before the word lists vote.

    "63 A" and "Typ A" are units (#396). "Hauptstraße" is an address (#404).
    Text in quotes is the page's, not the answer's language.
    """
    return _QUOTED.sub(" ", _ADDRESS.sub(" ", _UNIT_A.sub(" ", text)))


def _votes(text: str) -> tuple[bool, bool]:
    """Whether `text` hits the English list and whether it hits the German one.

    An umlaut counts as German before the lists are consulted. A word in
    neither list, including a shared word, counts for neither side. A
    capitalised umlaut word that is not a closed-class word is a proper noun
    inside English prose (#404) and does not vote there. On its own
    ("Verfügbarkeit?") it is the German content word. `im` and `ins` are not
    German evidence.
    """
    english = False
    german = False
    # Capitalised umlaut tokens held back until the other votes are known.
    names = False
    prepared = _prepare(text)
    for match in _WORD.finditer(prepared):
        original = match.group(0)
        word = original.lower()
        # lower() keeps ß; casefold() would turn it into "ss" and hide it.
        if word in _GERMAN:
            german = True
            continue
        if any(letter in word for letter in "äöüß"):
            if original[:1].isupper():
                names = True
                continue
            german = True
            continue
        if word in _ENGLISH:
            english = True
    if names and not english:
        german = True
    return english, german


def clear_language(text: str) -> Locale | None:
    """`en` or `de` when `text` is clearly that language; None when it is not.

    None covers a language-neutral text and a text that uses both languages.
    A question that returns None follows the page (`answer_language`). An
    answer that uses both languages is rejected (`mixed_prose`). A
    capitalised umlaut word with no English beside it is German.
    """
    english, german = _votes(text)
    if english and not german:
        return "en"
    if german and not english:
        return "de"
    return None


def mixed_prose(text: str) -> bool:
    """True when `text` hits both closed-class lists.

    A model code or a proper noun alone does not: those words are in neither
    list. A lowercase umlaut counts as German, so an English sentence that
    contains one is mixed. A capitalised name or a street inside English
    prose does not (#404). A capitalised umlaut word with no English vote
    is German.
    """
    english, german = _votes(text)
    return english and german


def answer_language(message: str, locale: str) -> Locale:
    """The last message's language when it is clearly one; else the page locale."""
    voted = clear_language(message)
    if voted is not None:
        return voted
    return page_language(locale)


def turn_language(request: TurnRequest) -> Locale:
    """The language this turn's customer-visible text is written in."""
    return answer_language(customer_message(request), request.locale)


def with_tool_lang(
    name: str, arguments: dict[str, Any] | None, language: str
) -> dict[str, Any] | None:
    """`arguments` with `lang` set to the answer language, for tools that take it.

    The copy is new. A tool that does not take `lang` is returned unchanged,
    including `None`. The model's own `lang` does not override the turn.
    """
    if name not in _LANG_TOOLS:
        return arguments
    lang = "de" if str(language).startswith("de") else "en"
    return {**(arguments or {}), "lang": lang}


def visible_text(output: TurnOutput) -> str:
    """The prose the customer reads, including card price lines.

    Fact placeholders are blanked. Document titles stay out: a catalogue title
    can carry the other language without being the answer's prose.
    """
    parts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, HandoffBlock):
            parts.append(block.summary)
        elif isinstance(block, AskBlock):
            parts.extend(block.options)
        elif isinstance(block, CardsBlock):
            parts.extend(price.text for price in block.prices or [])
    return _PLACEHOLDER.sub(" ", " ".join(parts))


def language_failure(output: TurnOutput, expected: Locale) -> str | None:
    """Why `output` breaks the rule, or None when it follows `expected`.

    The `language` field and the prose must both be `expected`. A neutral
    prose (a model code alone) is accepted when the field is right. Mixed
    prose fails, and so does prose that is clearly the other language. The
    reason starts with `LANGUAGE_RETRY_PREFIX` so the next prompt is a
    language re-ask.
    """
    prose_text = visible_text(output)
    prose = clear_language(prose_text)
    if (
        output.language == expected
        and not mixed_prose(prose_text)
        and prose in (None, expected)
    ):
        return None
    name = _NAMES[expected]
    return (
        f"{LANGUAGE_RETRY_PREFIX}{name} (language={expected}): follow the "
        "customer's last message when it is clearly one language, otherwise "
        "the page locale. Do not follow the page text, the documents, or the "
        "tool results when they are in the other language. Set language to "
        f"{expected}. Write every sentence, heading and list in {name}, "
        "including a short answer."
    )
