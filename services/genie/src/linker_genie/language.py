"""Which language an answer uses (#374).

The customer's last message wins when it is clearly English or clearly German.
A language-neutral message (a bare model code, an emoji, a number) and a
question that mixes both languages follow the page locale. Mixed language has
no public precedent (dossier 2026-10-19-genie-campaign-gaps §1.13); the floor
that does is "a German question is answered in German", applied here to both
languages. Brands and model codes are not evidence: they are the same words
on either page. A single clear content word (price, Preis, datasheet) is
evidence. An answer that mixes both languages fails the check. A hyphenated
menu name is one label: `of` inside `Time-of-use` does not vote. A content
word in the same shape still does (`price-list`), and a German closed-class
word still does (`Export-Für`). One short phrase copied from a cited chunk
is the document's wording, not the answer's. Bold text is still the answer's
prose.

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
# `im` and `ins` are not in the German list: they are also English
# ("Im looking", "ins and outs").
_PLACEHOLDER = re.compile(r"\{fact:[^}]*\}")
# The ampere unit is an "A" after a number ("63 A", "63A"). A model code writes
# the same letter after a hyphen ("ATS1-T63-A"). "Typ A" / "type A" is the RCD
# characteristic. lower() would turn that token into the English article (#396).
# The article in "a battery" has no digit and no "Typ"/"type" in front and still
# counts. Bold marks stay, so the hyphen form has to be named here (#443).
_UNIT_A = re.compile(
    r"(?<=\d)\s*[Aa]\b|(?<=\d)-[Aa]\b|\b(?:typ|type)\s+[Aa]\b",
    re.IGNORECASE,
)
# A street name is an address, not a language vote (#404).
_ADDRESS = re.compile(r"\b[\w]*?(?:straße|strasse)\b", re.IGNORECASE)
# Quoted page text is data. A German sentence inside quotes does not vote.
# A quote is one line: both arms run to the closing mark, with no character
# cap. There is no published cap. The old ASCII arm `{0,500}` left a longer
# quotation in the vote, so its words still counted (#396, #404).
_QUOTED = re.compile(r"„[^“”]*[“”]|\"[^\"\n]*\"")
_HYPHEN = "-–—"
# Function words a hyphenated menu name may contain. `of` in `Time-of-use`
# does not vote. Content words are not here: `price` in `price-list` and
# `battery` in `the-battery` still do. German closed-class words are counted
# before this skip, so `Für` in `Export-Für` still votes (#443).
_HYPHEN_SKIP = frozenset(
    """
    a the and or with for of to from on at by which what how does did do
    is are be been can could would should your you this that these those our
    my where when why who not have has about between than into any some
    there here only just but if we they them their it its
    """.split()
)
# A copied menu label, not a paragraph. Longer than this stays prose.
_CITED_LABEL_WORDS = 8
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
    """Drop units, addresses and quotations before the lists vote.

    "63 A" and "Typ A" are units (#396). "Hauptstraße" is an address (#404).
    Text in quotes is the page's, not the answer's language. Bold and underscore
    marks stay: they are emphasis, not a second way to hide a sentence (#443).
    """
    return _QUOTED.sub(" ", _ADDRESS.sub(" ", _UNIT_A.sub(" ", text)))


def _hyphen_fragment(text: str, start: int, end: int) -> bool:
    """True when a hyphen joins this token to another letter token.

    `Time-of-use` is one menu name. `of the battery` has no hyphen and still votes.
    The caller skips only a closed-class fragment (`of`), not a content word.
    """
    if (
        start
        and text[start - 1] in _HYPHEN
        and start >= 2
        and text[start - 2].isalpha()
    ):
        return True
    return bool(
        end < len(text)
        and text[end] in _HYPHEN
        and end + 1 < len(text)
        and text[end + 1].isalpha()
    )


def _votes_prepared(prepared: str) -> tuple[bool, bool]:
    """Whether prepared text hits the English list and the German one."""
    english = False
    german = False
    # Capitalised umlaut tokens held back until the other votes are known.
    names = False
    for match in _WORD.finditer(prepared):
        original = match.group(0)
        word = original.lower()
        # A capitalised closed-class word still votes. `Für` is German; holding
        # every capitalised umlaut back would let it pass an English sentence.
        # This runs before the menu-name skip, so `Export-Für` still votes.
        if word in _GERMAN:
            german = True
            continue
        # `of` inside `Time-of-use` is a closed-class fragment and does not vote.
        # `price` inside `price-list` is a content word and does.
        if word in _HYPHEN_SKIP and _hyphen_fragment(
            prepared, match.start(), match.end()
        ):
            continue
        # lower() keeps ß; casefold() would turn it into "ss" and hide it.
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


def _votes(text: str) -> tuple[bool, bool]:
    """Whether `text` hits the English list and whether it hits the German one.

    An umlaut counts as German before the lists are consulted. A word in
    neither list, including a shared word, counts for neither side. A
    capitalised umlaut word that is not a closed-class word is a proper noun
    inside English prose (#404) and does not vote there. On its own
    ("Verfügbarkeit?") it is the German content word. `im` and `ins` are not
    German evidence. A closed-class fragment inside a hyphenated menu name
    (`of` in `Time-of-use`) is not evidence either. A content word in that
    shape is. A German closed-class word is, even when a hyphen joins it.
    """
    return _votes_prepared(_prepare(text))


def _blank_cited_labels(text: str, cited: str, expected: Locale) -> str:
    """Blank one short menu phrase copied verbatim from a cited chunk.

    The phrase is at most eight words. It must contain the other language's
    closed class, at least two words that are in neither list, and none of the
    expected language. A lone `the` or `the Einstellung` is not a label. Only
    the longest matching window is blanked, so a copied paragraph still votes.
    A fully English answer is still English: this only removes that one span
    so the surrounding prose can be judged.
    """
    if not cited:
        return text
    haystack = " ".join(cited.casefold().split())
    tokens = list(_WORD.finditer(text))
    other = _ENGLISH if expected == "de" else _GERMAN
    own = _GERMAN if expected == "de" else _ENGLISH
    closed = _ENGLISH | _GERMAN
    spans: list[tuple[int, int, int]] = []
    for start in range(len(tokens)):
        for width in range(2, _CITED_LABEL_WORDS + 1):
            end = start + width
            if end > len(tokens):
                break
            window = tokens[start:end]
            words = [match.group(0).casefold() for match in window]
            if any(word in own for word in words):
                continue
            if not any(word in other for word in words):
                continue
            if sum(word not in closed for word in words) < 2:
                continue
            phrase = " ".join(words)
            # The chunk may end the label with a period. A word boundary keeps
            # that label; a whitespace boundary would miss `type.`
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", haystack) is None:
                continue
            spans.append((window[0].start(), window[-1].end(), width))
    if not spans:
        return text
    start, end, _width = max(
        spans, key=lambda span: (span[2], span[1] - span[0], -span[0])
    )
    chars = list(text)
    for index in range(start, end):
        if not chars[index].isspace():
            chars[index] = " "
    return "".join(chars)


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


def language_failure(
    output: TurnOutput, expected: Locale, cited: str = ""
) -> str | None:
    """Why `output` breaks the rule, or None when it follows `expected`.

    The `language` field and the prose must both be `expected`. A neutral
    prose (a model code alone) is accepted when the field is right. Mixed
    prose fails, and so does prose that is clearly the other language. A menu
    phrase copied from `cited` (a cited chunk's text) does not vote, unless
    the rest of the answer is already clearly the other language. The reason
    starts with `LANGUAGE_RETRY_PREFIX` so the next prompt is a language re-ask.
    """
    prose_text = visible_text(output)
    prepared = _prepare(prose_text)
    english, german = _votes_prepared(prepared)
    if _language_holds(output.language, expected, english, german):
        return None
    if cited and not _clearly_other(english, german, expected):
        blanked = _blank_cited_labels(prepared, cited, expected)
        if blanked != prepared:
            held_english, held_german = _votes_prepared(blanked)
            if _language_holds(output.language, expected, held_english, held_german):
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


def _language_holds(field: str, expected: Locale, english: bool, german: bool) -> bool:
    """True when the field is `expected` and the votes are not the other language."""
    if field != expected or (english and german):
        return False
    if english and not german:
        return expected == "en"
    if german and not english:
        return expected == "de"
    return True


def _clearly_other(english: bool, german: bool, expected: Locale) -> bool:
    """True when the unblanked prose is already the other language, not mixed."""
    if expected == "de":
        return english and not german
    return german and not english
