"""'Let Linker contact me' (#243, docs/specs/13-genie.md goal 6).

Genie offers the team's contact in four cases, and keeps answering after it (the
offer never mutes the assistant, unlike Knocket's 30-minute silence: TRIAL.md §3):

- `asked`: the customer asks for a person. A phrase of the table below matches before
  Jev or the model run (`asks_for_person`, the route is `person` and the whole turn is
  this module's, `answer()`), or Jev reads the intent `talk_to_person` (route.py).
  Offered every time the customer asks.
- `service`: a company, delivery or service question; the answer is the team mailbox
  sentence every time, and the card stands beside it (goal 1: "同时可一键").
- `dissatisfied`: Jev reads "asks for a person or is frustrated" (`wants_person`) on
  another intent; the answer goes on as routed and the offer is added.
- `repeat`: the customer asks the same question for the third round in a row; the offer
  is added once for that question.

The last three never come on two turns in a row (goal 6; review round 1 of #243). Which
earlier turns carried the offer is the service's own turn log (`log.TurnLog.offers`,
which stores the reason this module decided), not the browser. The offer itself is the
`contact` block the shell renders as the contact card; the model never writes it
(schema.ContactBlock), and `ground.shipped` holds the answer as it ships.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from linker_genie.jev import Reading
from linker_genie.route import LIKELY, Route
from linker_genie.schema import ContactBlock, ContactReason, TextBlock, TurnMessage

# Rounds of the same question before the offer: the owner's rule (goal 6, "同一问题
# 重复三轮时提议一次"; INTL.md §8 A5).
REPEATS = 3
# The share of words (Jaccard) two messages must still have in common to be one
# question, once the later adds no word and no model code (same_question). Measured on
# eval/contact/repeats.json: 39 pairs EN/DE incl. 8 real follow-up negatives (a feature
# or quantity added, a sibling model), written 2026-10-18 and extended in review round
# 1 of #243. All 39 are right for any cut from 0 to 0.75 (above 0.75 the shortened
# "Garantie GoodWe ET?" stops counting as a repeat); 0.5 sits in the middle.
SAME = 0.5
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
# Nouns that name a person only: "team", "expert" and "engineer" also name software,
# modes and guides ("the team portal", "expert mode", "the engineer's guide"), so a
# team counts only as somebody's ("your team", "the Linker team"), and an agent only
# with an article that makes it a person (review round 1 of #243).
_PERSON = (
    r"(?:person|human|human being|someone|somebody|representative|staff member|"
    r"employee|colleague|salesperson|sales rep|sales representative)"
)
_TEAM = r"(?:your|the\s+linker|linker|the\s+sales|your\s+sales|someone\s+from\s+your(?:\s+sales)?)\s+team"
_DE_PERSON = (
    r"(?:mitarbeiter(?:in)?|menschen|mensch|person|berater(?:in)?|ansprechpartner(?:in)?|"
    r"kollegen|kollegin|vertrieb|verkäufer(?:in)?|jemandem|jemand)"
)
_DE_VERB = r"(?:sprechen|reden|chatten|telefonieren)"
PHRASES: dict[str, tuple[re.Pattern[str], ...]] = {
    "en": tuple(
        re.compile(pattern)
        for pattern in (
            rf"\b(?:talk|speak|chat)\s+(?:to|with)\s+(?:a\s+|an\s+|the\s+|your\s+)?(?:real\s+|actual\s+|live\s+)?{_PERSON}\b",
            rf"\b(?:talk|speak|chat)\s+(?:to|with)\s+{_TEAM}\b",
            r"\b(?:talk|speak|chat)\s+(?:to|with)\s+(?:a|an|your)\s+(?:real\s+|live\s+|human\s+)?agent\b",
            rf"\b(?:connect|transfer|put)\s+me\s+(?:through\s+)?(?:to|with)\s+(?:a\s+|an\s+|the\s+|your\s+)?(?:real\s+|live\s+)?(?:{_PERSON}|agent)\b",
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
            rf"\b(?:mit|zu)\s+(?:einem\s+|einer\s+|ihrem\s+|ihrer\s+|dem\s+|der\s+)?(?:echten\s+|richtigen\s+|realen\s+)?{_DE_PERSON}\s+(?:\w+\s+)?{_DE_VERB}\b",
            rf"\bmit\s+(?:ihrem|dem\s+linker)\s+(?:vertriebs)?team\s+(?:\w+\s+)?{_DE_VERB}\b",
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

# Where a clause ends: a negation is read inside its own clause only.
_CLAUSE = re.compile(r"[.!?;:,]+")
# Words that turn a following phrase into its opposite, EN and DE, on the normalized
# text ("don't" is "don t" there).
_NEGATION = re.compile(
    r"\b(?:don t|do not|dont|doesn t|does not|never|no need to|not|nicht|kein|keine|"
    r"keinen|niemals)\b"
)

# The sentence of a turn that only answers a request for a person: the contact card
# (the shell's ContactCard) follows it with the one-business-day promise. Copy review:
# docs/acceptance/2026-10-18/243/copy-review.md.
ANSWER = {
    "en": "Someone from the Linker team can get in touch with you by email.",
    "de": "Jemand aus dem Linker-Team kann sich per E-Mail bei Ihnen melden.",
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
    """The words of the phrase that asks for a person, None when none matches.

    A phrase after a negation in its own clause ("I don't want to talk to a person",
    "ich möchte nicht mit einem Mitarbeiter sprechen") is not a request; such a
    message goes on to Jev like any other (copy review of #243). A negation in an
    earlier clause does not reach it ("That did not help. Can I talk to a person?").
    """
    for clause in _CLAUSE.split(message):
        text = normalize(clause)
        for patterns in PHRASES.values():
            for pattern in patterns:
                found = pattern.search(text)
                if found and not _NEGATION.search(text[: found.start()]):
                    return found.group(0)
    return None


def _words(message: str) -> frozenset[str]:
    return frozenset(w for w in normalize(message).split() if w not in _STOPWORDS)


def same_question(earlier: str, later: str) -> bool:
    """Whether a later customer message asks the earlier one's question again.

    A repeat says nothing new: the later message adds no content word to the earlier
    one (a feature such as "backup" or a quantity such as "15 kWh" makes it a new,
    refined question), names the same model codes (H2-10K-T3 and H2-8K-T3 are two
    questions), and still shares SAME of the words (a cut-down "SAJ battery?" is
    another question). Messages of fewer than MIN_WORDS content words are no
    question to repeat.
    """
    left, right = _words(earlier), _words(later)
    if len(left) < MIN_WORDS or len(right) < MIN_WORDS:
        return False
    if right - left or _codes(left) != _codes(right):
        return False
    return len(left & right) / len(left | right) >= SAME


def _codes(words: frozenset[str]) -> frozenset[str]:
    """The words with a digit: model codes and quantities."""
    return frozenset(w for w in words if any(c.isdigit() for c in w))


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
    if offers and offers[0]:
        # Never two turns in a row (goal 6), the company card included: its
        # mailbox sentence stays every time (review round 1 of #243).
        return None
    if route.name == "service":
        return Offer("service")
    if reading is not None and reading.wants_person >= LIKELY:
        return Offer("dissatisfied")
    run = repeats(messages)
    if run >= REPEATS and not any(offers[: run - 1]):
        return Offer("repeat")
    return None


def answer(locale: str) -> TextBlock:
    """The sentence of a turn that answers a request for a person (no model runs)."""
    return TextBlock(text=ANSWER["de" if locale == "de" else "en"])
