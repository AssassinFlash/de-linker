"""The confirmation card of an in-conversation inquiry (#250, docs/specs/13-genie.md goal 5).

Genie drafts the inquiry; the shell's confirmation card shows every line that will
be sent (the solution draft's products and quantities, the message, whether the
conversation summary is attached, and the one-business-day promise), and only the
customer's Send button sends it. The model cannot send: it has no ability that
writes an inquiry, and the card's route (`Linker\\Tools\\Genie\\InquiryRequest`)
is the only door. A model sentence claiming an inquiry was sent is refused by
grounding (`ground._no_sent_claim`), so a forged claim never ships either.

The offer itself is the `send_inquiry` action. The model may write it (it is on
schema.ActionName); an explicit request in the customer's own message adds it when
the model did not, the way `contact.asks_for_person` settles a request for a
person without the model. That keeps the card one click away for the sentences the
owner named ("客户也可以直接说'发询盘'"), whatever Jev read the intent as.

The table is deliberately narrow: it names the act of sending an inquiry, a quote
or a proforma. A question about the customer's own inquiry ("where is my
inquiry?", "Wo steht meine Anfrage?") has no send verb and stays with the
inquiry-status route, which answers it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

# The German inquiry nouns: Anfrage is the customer's word for it (AGENTS.md §3);
# Angebot is what a customer often says for the same request.
_DE_NOUN = r"(?:anfrage|anfragen|angebot|angebote|proformarechnung|proforma)"
# The verbs that ask for it in German: infinitive, first person and the Sie
# imperative ("senden", "sende", "senden Sie"), including the separable "abschicken"
# and "einholen".
_DE_VERB = (
    r"(?:senden|sende|sendet|absenden|absende|abzusenden|abschicken|abschicke|"
    r"abzuschicken|schicken|schicke|schickt|stellen|stelle|stellt|erstellen|"
    r"erstelle|erstellt|anfordern|fordere|fordert|anfragen|einholen|hole|holt)"
)

# A request to send the inquiry, EN and DE, matched on contact.normalize's text
# (lower case, punctuation to spaces).
PHRASES: dict[str, tuple[re.Pattern[str], ...]] = {
    "en": tuple(
        re.compile(pattern)
        for pattern in (
            # "send an inquiry", "send me a quote"; "place the order" is not one.
            r"\b(?:send|submit|place|file|make|create|start|prepare)"
            r"(?: me| us)? (?:an |a |the |my |our |this )?(?:inquiry|enquiry|quote|"
            r"proforma request|proforma)\b",
            r"\b(?:request|get|ask for) (?:a |an |the |my |our )?"
            r"(?:quote|offer|proforma|rfq)\b",
            r"\b(?:i (?:want|would like|need|d like) (?:to )?"
            r"(?:send|submit|place|make)) (?:an |a |the |my )?"
            r"(?:inquiry|enquiry)\b",
            r"\b(?:can|could|would|will) you (?:please )?"
            r"(?:send|submit|place|prepare) (?:an |a |the |my |our )?"
            r"(?:inquiry|enquiry|quote)\b",
            r"\b(?:go ahead|proceed) with (?:the |my |our )?"
            r"(?:inquiry|enquiry|request|quote|proforma)\b",
            r"\b(?:send|sending|submit|submitting) (?:it|this|these|them)"
            r" (?:as|in) (?:an |a )?(?:inquiry|request)\b",
            r"\brfq\b",
            r"\brequest for quotation\b",
        )
    ),
    "de": tuple(
        re.compile(pattern)
        for pattern in (
            # "Anfrage senden", "Anfrage abschicken", "Angebot einholen".
            rf"\b{_DE_NOUN} (?:\w+ )?{_DE_VERB}\b",
            rf"\b{_DE_VERB} sie (?:mir |uns )?(?:bitte )?"
            rf"(?:eine |die |meine |unsere )?{_DE_NOUN}\b",
            rf"\bich (?:möchte|moechte|will|würde|wuerde|hätte|haette)"
            rf" (?:gern |gerne )?(?:eine |die |meine |unsere )?"
            rf"{_DE_NOUN} (?:\w+ )?{_DE_VERB}\b",
            rf"\b(?:bitte )?(?:eine |die |meine |unsere )?{_DE_NOUN}"
            rf" (?:bitte )?{_DE_VERB}\b",
            # "Ich hätte gern ein Angebot für …" (no verb: a request).
            r"\bich (?:hätte|haette|möchte|moechte|würde|wuerde)"
            r" (?:gern |gerne )?(?:ein|eine) (?:angebot|anfrage)"
            r" (?:für|fuer|zu|über|ueber)\b",
            r"\b(?:abschicken|senden|schicken|stellen|erstellen) sie"
            r"(?: das| es| die anfrage)?\b",
            r"\b(?:auftrag|bestellung) (?:auslösen|ausloesen|starten)\b",
            r"\bangebot einholen\b",
        )
    ),
}

# Where a clause ends: a negation is read inside its own clause only.
_CLAUSE = re.compile(r"[.!?;:,]+")
# Words that turn a following phrase into its opposite, EN and DE, on the
# normalized text ("don't" is "don t" there).
_NEGATION = re.compile(
    r"\b(?:don t|do not|dont|doesn t|does not|never|no need to|not|nicht|kein|keine|"
    r"keinen|niemals)\b"
)
# The action that shows the card (schema.ActionName).
ACTION = "send_inquiry"
# A question about the act, not a request: "Should I send an inquiry?" and "What
# happens after I send an inquiry?" are answered, not confirmed.
_HYPOTHETICAL = re.compile(
    r"\b(?:should i|shall i|soll ich|sollte ich|do i (?:need|have) to|"
    r"muss ich|must i|after i (?:send|submit|place)|after sending|"
    r"before i (?:send|submit|place)|bevor ich)\b"
)


def normalize(message: str) -> str:
    """NFKC, lower case, punctuation to spaces, one space (contact.normalize's)."""
    text = unicodedata.normalize("NFKC", message).lower()
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def requests_inquiry(message: str) -> bool:
    """Whether the customer asks to send an inquiry, a quote or a proforma.

    A phrase after a negation in its own clause ("I don't want to send an
    inquiry", "ich möchte keine Anfrage senden") is not a request; the message then
    stays with the model's own judgement.
    """
    for clause in _CLAUSE.split(message):
        text = normalize(clause)
        if _HYPOTHETICAL.search(text):
            continue
        for patterns in PHRASES.values():
            for pattern in patterns:
                found = pattern.search(text)
                if found and not _NEGATION.search(text[: found.start()]):
                    return True
    return False


def decide(message: str, blocks: Sequence[dict[str, Any]]) -> bool:
    """Whether the service adds the card's action after this answer.

    The model may already have written `send_inquiry`; a handoff answer is the
    team's sentence and nothing else (contact/ground rules), so neither gets a
    second action.
    """
    if not requests_inquiry(message):
        return False
    for block in blocks:
        kind = block.get("type")
        if kind == "handoff":
            return False
        if kind == "action" and block.get("name") == ACTION:
            return False
    return True
