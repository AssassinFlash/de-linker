"""Which language an answer uses (#374).

The customer's last message wins when it is clearly English or clearly German.
A language-neutral message (a bare model code, an emoji, a number) and a
message that mixes both languages follow the page locale. Mixed language has
no public precedent (dossier 2026-10-19-genie-campaign-gaps §1.13); the floor
that does is "a German question is answered in German", applied here to both
languages. Brands and model codes are not evidence: they are the same words
on either page.

The cycle asks the model once when an answer breaks the rule, then ships the
template in the required language. A violating answer is not returned.
"""

from __future__ import annotations

import re

from linker_genie.schema import (
    AskBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnOutput,
    TurnRequest,
)

# Closed-class words that are one language and not the other. Shared words
# (in, was, am, will, so) are in neither list: one of them must not flip the
# answer. A word the lists do not know — a brand, a model, "home" — is not
# evidence either, so a bare code stays language-neutral.
_ENGLISH = frozenset(
    """
    a an the and or with for of to from on at by which what how does did do
    is are be been can could would should your you this that these those our
    my please show tell where when why who not have has about between than
    into work works any some there here also only just but if we they them
    their it its batteries battery
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
    passen passt batterien batterie speicher
    """.split()
)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_PLACEHOLDER = re.compile(r"\{fact:[^}]*\}")
_NAMES = {"en": "English", "de": "German"}
# The retry reason starts with this. agent._user_prompt treats that prefix as
# a language re-ask, not a grounding failure.
LANGUAGE_RETRY_PREFIX = "answer in "


def page_language(locale: str) -> Locale:
    """`de` for a German page locale, otherwise `en` (template.language_of)."""
    return "de" if locale.startswith("de") else "en"


def customer_message(request: TurnRequest) -> str:
    """The last thing the customer wrote, or empty when they have not."""
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return ""


def clear_language(text: str) -> Locale | None:
    """`en` or `de` when `text` is clearly that language; None when it is not.

    None covers a language-neutral text and a text that uses both languages.
    Both follow the page locale (`answer_language`).
    """
    english = False
    german = False
    for word in _WORD.findall(text.lower()):
        # lower() keeps ß; casefold() would turn it into "ss" and hide it.
        if any(letter in word for letter in "äöüß"):
            german = True
            continue
        if word in _GERMAN:
            german = True
        elif word in _ENGLISH:
            english = True
    if english and not german:
        return "en"
    if german and not english:
        return "de"
    return None


def answer_language(message: str, locale: str) -> Locale:
    """The last message's language when it is clearly one; else the page locale."""
    voted = clear_language(message)
    if voted is not None:
        return voted
    return page_language(locale)


def visible_text(output: TurnOutput) -> str:
    """The prose the customer reads, without fact placeholders."""
    parts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, HandoffBlock):
            parts.append(block.summary)
        elif isinstance(block, AskBlock):
            parts.extend(block.options)
    return _PLACEHOLDER.sub(" ", " ".join(parts))


def language_failure(output: TurnOutput, expected: Locale) -> str | None:
    """Why `output` breaks the rule, or None when it follows `expected`.

    The `language` field and the prose must both be `expected`. A neutral
    prose (a model code alone) is accepted when the field is right. A second
    language in the prose is not.
    """
    prose = clear_language(visible_text(output))
    if output.language == expected and prose in (None, expected):
        return None
    name = _NAMES[expected]
    return (
        f"{LANGUAGE_RETRY_PREFIX}{name} (language={expected}): follow the "
        "customer's last message when it is clearly one language, otherwise "
        "the page locale"
    )
