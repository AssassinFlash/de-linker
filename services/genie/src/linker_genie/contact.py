"""'Let Linker contact me' (#243, docs/specs/13-genie.md goal 6).

Genie offers the team's contact in four cases, and keeps answering after it (the
offer never mutes the assistant, unlike Knocket's 30-minute silence: TRIAL.md §3):

- `asked`: the customer asks for a person. A phrase of the table below matches before
  Jev or the model run (`asks_for_person`, the route is `person` and the whole turn is
  this module's, `answer()`), or Jev reads the intent `talk_to_person` (route.py).
- `service`: a company, delivery or service question; the answer is the team mailbox
  sentence, and the offer stands beside it (goal 1: "同时可一键").
- `dissatisfied`: Jev reads "asks for a person or is frustrated" (`wants_person`) on
  another intent; the answer goes on as routed and the offer is added.
- `repeat`: the customer asks the same question for the third round in a row; the offer
  is added once for that question.

The last two are proactive: never on two turns in a row (goal 6). Which earlier turns
carried the offer is read from the service's own turn log (`log.TurnLog.offers`), not
from the browser. The offer itself is the `contact` block the shell renders as the
contact card; the model never writes it (schema.ContactBlock).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from linker_genie.jev import Reading
from linker_genie.route import LIKELY, Route
from linker_genie.schema import ContactBlock, ContactReason, TextBlock, TurnMessage

# Rounds of the same question before the offer: the owner's rule (goal 6, "同一问题
# 重复三轮时提议一次"; INTL.md §8 A5).
REPEATS = 3
# Two messages ask the same question when their content words overlap by this share
# (Jaccard): eval/contact/repeats.json, 31 pairs EN/DE written 2026-10-18, all right
# for a cut above 0.67 (which joins "datasheet" and "manual" of one model) up to 0.75
# (the shortened "Garantie GoodWe ET?" scores 0.75); 0.7 sits inside that range.
SAME = 0.7
# Fewer content words than this is no question to repeat ("ok", "danke"): the same
# pairs ("warranty GoodWe ET?" has three).
MIN_WORDS = 2

# Words that do not make the question: articles, pronouns, auxiliaries and politeness,
# EN and DE. Measured with the pairs above ("What is the warranty of the GoodWe ET?"
# against "warranty GoodWe ET?").
_STOPWORDS = frozenset(
    """
    a an the of for to on in at with and or is are be do does did can could would
    should will i me my we you your it its this that there please pls hi hello thanks
    thank ok okay how what which who whom why when where
    der die das den dem des ein eine einen einem einer eines zu zum zur für mit von
    vom bei beim im in an am auf und oder ist sind sein hat haben gibt es ich mir mich
    wir sie ihr ihre ihnen bitte danke hallo wie was welche welcher welches wer warum
    wann wo
    """.split()
)

# The phrases that ask for a person, matched in code before Jev and the model run
# (Knocket's outer layer: docs/research/2026-10-17-knocket/raw/apify/pages/
# knocket-handoff-phrases.md — normalize, match on word boundaries, explicit requests
# only; bare nouns such as "agent" or "customer service" stay with Jev). Both
# languages are always checked: customers mix them, and Knocket keeps English on
# every session for the same reason.
_PERSON = r"(?:person|human|human being|someone|somebody|agent|representative|rep|staff|employee|colleague|salesperson|sales|sales team|team|engineer|expert)"
_DE_PERSON = r"(?:mitarbeiter(?:in)?|menschen|mensch|person|berater(?:in)?|ansprechpartner(?:in)?|kollegen|kollegin|vertrieb|verkäufer(?:in)?|team|techniker(?:in)?|jemandem|jemand)"
PHRASES: dict[str, tuple[re.Pattern[str], ...]] = {
    "en": tuple(
        re.compile(pattern)
        for pattern in (
            rf"\b(?:talk|speak|chat)\s+(?:to|with)\s+(?:a\s+|an\s+|the\s+|your\s+)?(?:real\s+|actual\s+|live\s+)?{_PERSON}\b",
            rf"\b(?:connect|transfer|put)\s+me\s+(?:through\s+)?(?:to|with)\s+(?:a\s+|an\s+|the\s+|your\s+)?(?:real\s+|live\s+)?{_PERSON}\b",
            r"\b(?:transfer|escalate)\s+(?:me\s+)?to\s+(?:a\s+)?(?:human|person|agent)\b",
            r"\b(?:a|an)\s+(?:real|live|actual)\s+(?:person|human)\b",
            r"\b(?:anyone|anybody|someone|somebody)\s+(?:i|we)\s+can\s+(?:talk|speak)\s+(?:to|with)\b",
            r"\b(?:call|ring|phone)\s+me(?:\s+back)?\b",
            r"\bcall\s*back\b",
            r"\bcontact\s+me\b",
            r"\bget\s+in\s+touch\s+with\s+me\b",
        )
    ),
    "de": tuple(
        re.compile(pattern)
        for pattern in (
            rf"\b(?:mit|zu)\s+(?:einem\s+|einer\s+|ihrem\s+|ihrer\s+|dem\s+|der\s+)?(?:echten\s+|richtigen\s+|realen\s+)?{_DE_PERSON}\s+(?:\w+\s+)?(?:sprechen|reden|chatten|telefonieren)\b",
            r"\bverbinden\s+sie\s+mich\b",
            r"\b(?:rufen|ruft)\s+sie\s+mich\s+(?:bitte\s+)?(?:zurück|an)\b",
            r"\bmich\s+(?:\w+\s+)?(?:anrufen|zurückrufen)\b",
            r"\brückruf\b",
            r"\b(?:kontaktieren|kontaktiert)\s+sie\s+mich\b",
            r"\bmelden\s+sie\s+sich\s+(?:bitte\s+)?bei\s+mir\b",
            r"\b(?:echten|richtigen)\s+(?:menschen|mitarbeiter)\b",
        )
    ),
}

# The sentence of a turn that only answers a request for a person: the contact card
# (the shell's ContactCard) follows it with the one-working-day promise. Copy review:
# docs/acceptance/2026-10-18/243/copy-review.md.
ANSWER = {
    "en": "Yes, someone from the Linker team can get in touch with you.",
    "de": "Gern meldet sich jemand aus dem Linker-Team bei Ihnen.",
}


@dataclass(frozen=True)
class Offer:
    """Genie offers the team's contact on this turn, for this reason."""

    reason: ContactReason

    def block(self) -> ContactBlock:
        return ContactBlock(reason=self.reason)


def normalize(message: str) -> str:
    """Knocket's normalizer: NFKC, lower case, punctuation to spaces, one space."""
    text = unicodedata.normalize("NFKC", message).lower()
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def asks_for_person(message: str) -> str | None:
    """The words of the phrase that asks for a person, None when none matches."""
    text = normalize(message)
    for patterns in PHRASES.values():
        for pattern in patterns:
            found = pattern.search(text)
            if found:
                return found.group(0)
    return None


def _words(message: str) -> frozenset[str]:
    return frozenset(w for w in normalize(message).split() if w not in _STOPWORDS)


def same_question(a: str, b: str) -> bool:
    """Whether two customer messages ask the same question (SAME, MIN_WORDS)."""
    left, right = _words(a), _words(b)
    if len(left) < MIN_WORDS or len(right) < MIN_WORDS:
        return False
    return len(left & right) / len(left | right) >= SAME


def repeats(messages: Sequence[TurnMessage]) -> int:
    """How many customer messages in a row, ending with the last, ask its question."""
    asked = [m.content for m in messages if m.role == "user"]
    if not asked:
        return 0
    last = asked[-1]
    count = 1
    for earlier in reversed(asked[:-1]):
        if not same_question(earlier, last):
            break
        count += 1
    return count


def decide(
    route: Route,
    reading: Reading | None,
    messages: Sequence[TurnMessage],
    offers: Sequence[bool],
) -> Offer | None:
    """Whether this turn offers the contact, and why (module docstring).

    `offers` tells, newest first, which of this conversation's earlier turns carried the
    offer (log.TurnLog.offers).
    """
    if route.name == "person":
        return Offer("asked")
    if route.name == "service":
        return Offer("service")
    if offers and offers[0]:
        return None
    if reading is not None and reading.wants_person >= LIKELY:
        return Offer("dissatisfied")
    run = repeats(messages)
    if run >= REPEATS and not any(offers[: run - 1]):
        return Offer("repeat")
    return None


def answer(locale: str) -> TextBlock:
    """The sentence of a turn that answers a request for a person (no model runs)."""
    return TextBlock(text=ANSWER["de" if locale == "de" else "en"])


def offered(output: dict[str, Any]) -> bool:
    """Whether a logged answer carried the offer (its blocks hold a contact block)."""
    blocks = output.get("blocks") if isinstance(output, dict) else None
    return any(
        isinstance(block, dict) and block.get("type") == "contact"
        for block in blocks or []
    )
