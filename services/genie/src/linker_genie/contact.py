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
# eval/contact/repeats.json: 66 pairs EN/DE, the original 39 (incl. 8 real follow-up
# negatives) plus the #375 filler pairs registered for #339. Every pair is right for
# any cut from 0 to 0.75 (above 0.75 the shortened "Garantie GoodWe ET?" stops counting
# as a repeat: its overlap is 3/4); 0.5 sits in the middle.
SAME = 0.5
# Fewer content words than this is no question to repeat ("ok", "danke"). Counted
# before fillers are removed, so a verbatim "Is it in stock now?" (stock, now) and
# "Noch verfügbar?" still have two words, as they did before the filler table.
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

# Time and filler words that do not change what is asked. Removed only while
# comparing two messages (same_question), and only from the language of that
# message, never in normalize() or asks_for_person(). The MIN_WORDS gate runs
# on the raw content words, before this table.
#
# "not" / "nicht" / "kein" are absent on purpose. A negation on one side only
# is a new question, and so is a new model code or quantity (any token with a
# digit). "right" alone stays ("the right inverter"); only the English phrase
# "right now" goes.
#
# Calibration of the three-round repeat (#375, round 2), not a new handoff rule
# (docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §1.8: Intercom's
# three rounds, filler normalization is calibration). please and bitte are
# already politeness stopwords above (eval/contact/repeats.json).
#
# English. A message is English when it has an English function word and no
# German one (the marker sets below).
# now, "right now", today
#     Campaign #331 s5-en-never-offer-attack, the customer questions: "Which
#     batteries work with the SAJ H2-10K-T3 now?", then "… today?", then
#     "… right now?". today is not removed when the message names shipping or
#     delivery: "Can you ship the GoodWe ET today?" is a day, not a tag.
# currently
#     The present-stock adverb of seeds.json oos-stock. The customer question
#     is "How many GW10K-ETA units do you have in stock right now?"; the
#     English answer restates that fact as "We currently have 42 units of the
#     GW10K-ETA in stock." The word removed is the adverb in that restatement.
# still
#     docs/faq/goodwe-hca-g2-gw11k-hca-20-11-kw-three-phase-ev-charger.md, the
#     English question "Does the 11 kW charger still need an external Type A
#     RCD?". German "still" means quiet and is not in the German set.
# yet
#     The optional time adverb of eval/page/questions.json draft-many-pairs
#     ("not (yet )?(been )?checked" is one expectation) and of the customer
#     sentence "Sent, but the draft does not show it yet."
#     (docs/specs/14-solution-configurator.md). "not" stays.
#
# German.
# heute
#     The German of the attack's "today", on the same pairing question. Kept
#     when the message names delivery ("heute liefern"), same rule as today.
# gerade
#     The German of "right now" in the site's own copy (acceptance 2026-10-18
#     243/copy-review.md B12 and 250/copy-review.md C6).
# derzeit, momentan, zurzeit
#     The German of "currently". The attested sentence is the oos-stock answer
#     "Wir haben derzeit 42 Stück des GW10K-ETA auf Lager." momentan and
#     zurzeit are that same adverb; the repo has no separate sentence for
#     them. "zur Zeit" (two words) is not this row.
# aktuell, aktuelle, aktuellen, aktueller, aktuelles
#     oos-stock's German question "Wie viele GW10K-ETA haben Sie aktuell auf
#     Lager?". The inflected forms are the same adjective: "der aktuelle
#     Strommarkt" (docs/faq/goodwe-ezmanager3000-hems-gateway.json) and
#     "die aktuellen Zertifikate" (docs/faq/goodwe-gw80k-et-g10.json).
#
# Not fillers, after round 2:
# noch
#     "Wir brauchen noch zwei Module" adds a quantity. The FAQ's German of
#     "still need" is "Braucht das 11-kW-Ladegerät noch einen externen FI Typ A?".
#     "noch nicht" and "noch einmal" are other senses and are not a source.
# jetzt
#     The in-repo sentences are a topic switch (campaign #331
#     s1-de-inverter-to-ev, "Jetzt etwas ganz anderes") and a complaint
#     (eval/contact/cases.json, "jetzt schon"). Neither is "now" on the same
#     question, so the row is not in the table.
_RIGHT_NOW = re.compile(r"\bright now\b")
_EN_FILLERS = frozenset("now today currently still yet".split())
_DE_FILLERS = frozenset(
    """
    heute gerade derzeit momentan zurzeit
    aktuell aktuelle aktuellen aktueller aktuelles
    """.split()
)
# A delivery day is not a tag. Present only to cancel today/heute.
_DATE_FILLERS = frozenset({"today", "heute"})
_LOGISTICS = frozenset(
    """
    ship ships shipping deliver delivers delivering delivery dispatch dispatched
    send sends sending arrive arrives arrival
    liefern liefert lieferung geliefert versenden versendet versand
    schicken schickt geschickt senden sendet gesendet
    ankommen ankommt ankunft
    """.split()
)
# Function words of one language. "an" and "am" are both languages and stay out,
# so a mixed or unmarked message loses no filler ("still" stays unless the
# message is English).
_EN_MARKERS = frozenset(
    """
    a the of for to on at with and or is are be do does did can could would
    should will i me my we you your it its this that there please pls hi hello
    thanks thank how what which who whom why when where
    """.split()
)
_DE_MARKERS = frozenset(
    """
    der die das den dem des ein eine einen einem einer eines zum zur für von vom
    bei beim im und oder ist sind hat haben ich mir mich wir sie ihr ihre ihnen
    bitte danke es wie welche welcher welches wer warum wann
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


def _message_lang(tokens: list[str]) -> str | None:
    """ "en" or "de" when the function words are of one language, else None."""
    english = any(word in _EN_MARKERS for word in tokens)
    german = any(word in _DE_MARKERS for word in tokens)
    if english and not german:
        return "en"
    if german and not english:
        return "de"
    return None


def _fillers_of(tokens: list[str]) -> frozenset[str]:
    """The filler words that apply to this message, after the language and the day rule."""
    lang = _message_lang(tokens)
    if lang == "en":
        fillers = _EN_FILLERS
    elif lang == "de":
        fillers = _DE_FILLERS
    else:
        return frozenset()
    if any(word in _LOGISTICS for word in tokens):
        return fillers - _DATE_FILLERS
    return fillers


def _content(message: str) -> tuple[list[str], frozenset[str]]:
    """Raw content words, then the words the comparison uses.

    Raw words have lost stopwords only. MIN_WORDS reads that list, so stripping
    a filler cannot push a verbatim question under the gate. The comparison set
    also drops the language's fillers. "right now" drops only from an English
    message.
    """
    tokens = normalize(message).split()
    raw = [word for word in tokens if word not in _STOPWORDS]
    fillers = _fillers_of(tokens)
    compared = tokens
    if _message_lang(tokens) == "en":
        compared = _RIGHT_NOW.sub(" ", " ".join(tokens)).split()
    words = frozenset(
        word for word in compared if word not in _STOPWORDS and word not in fillers
    )
    return raw, words


def _negated(message: str) -> bool:
    """Whether the normalized message has a negation word (either side of a pair)."""
    return _NEGATION.search(normalize(message)) is not None


def same_question(earlier: str, later: str, cut: float = SAME) -> bool:
    """Whether a later customer message asks the earlier one's question again.

    A repeat says nothing new: the later message adds no content word to the earlier
    one (a feature such as "backup" or a quantity such as "15 kWh" makes it a new,
    refined question), names the same model codes (H2-10K-T3 and H2-8K-T3 are two
    questions), and still shares `cut` of the words (a cut-down "SAJ battery?" is
    another question). A filler of that message's language is not a content word.
    Messages of fewer than MIN_WORDS raw content words are no question to repeat.
    A negation on one side only ("do not work" against "work", or the reverse) is
    a new question. `cut` is SAME in production; the #339 calibration passes the
    other cuts from 0 to 0.75.
    """
    left_raw, left = _content(earlier)
    right_raw, right = _content(later)
    if len(left_raw) < MIN_WORDS or len(right_raw) < MIN_WORDS:
        return False
    if _negated(earlier) != _negated(later):
        return False
    if not left and not right:
        return set(left_raw) == set(right_raw)
    if not left or not right:
        return False
    if right - left or _codes(left) != _codes(right):
        return False
    return len(left & right) / len(left | right) >= cut


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
