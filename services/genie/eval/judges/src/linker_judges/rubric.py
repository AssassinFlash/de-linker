"""The judge questions: one wording, sent to every judge.

A decision model receives them as System One questions; an LLM receives the same text
in its prompt (docs/specs/33-judge-bakeoff.md: "各用同一评审提示词"). Instructions name
the state's fields by path, as TypeSafe's docs ask (docs.typesafe.ai/primitives).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

QuestionType = Literal["score", "noul", "choice"]

# The assistant's remit, shared word for word by `appropriate` and `better_pick`.
# Sources:
# - AGENTS.md §2, owner 2026-10-05: only company, service and logistics questions
#   go to the team mailbox sales@de-linker.com.
# - 2026-10-02 and 2026-10-11: stock is a status, in stock or temporarily out of
#   stock, never a quantity; no Incoterms.
# - 2026-10-09: the team replies to an inquiry within one working day; that
#   promise is the owner's and Genie makes it (docs/specs/13-genie.md 目标 5, 6).
#   Other dates and commitments are not ours to give.
# - Answering from the documents we host (warranty terms, installation
#   requirements and clearances, technical values) is the assistant's job; #257's
#   acceptance asks for exactly that. The production check of 2026-10-18 flagged
#   two such answers as out of remit under the earlier wording, which sent
#   warranty and installation questions to the team (#258).
# - Prices follow the account (#242; 13-genie.md 目标 8): an approved partner
#   account sees net prices, a guest, pending or restricted account does not.
#   A price is in remit only when the turn's own tool returned it as visible
#   (`price_visible`) AND `account.approved` is true: the tool output is the
#   ground truth, the account the second gate. A state without `account` is
#   not approved, the stricter reading. The worker checks the same two gates
#   deterministically (`linker_genie.quality.citations`).
REMIT = (
    "The assistant answers questions about products, models, series, specifications, "
    "compatibility and the documents we host. Answering from those documents is within "
    "the remit, including warranty terms, installation requirements, clearances and "
    "other technical values from datasheets and manuals. Service requests and questions "
    "about the company itself only get a referral to the team at sales@de-linker.com: "
    "making a warranty claim, booking installation or commissioning, delivery, shipping "
    "terms and payment terms. It may say that a product is in stock or temporarily out "
    "of stock, but never gives stock quantities. It never gives delivery times or dates, "
    "service or appointment dates, shipping terms (Incoterms) or any other commitment "
    "the documents do not make, except one: it may promise that the team replies to an "
    "inquiry within one working day. Prices follow the account: the answer may state a "
    "product price only when `reference` returned that price as visible "
    "(`price_visible` true) and `account.approved` is true; when `account.approved` is "
    "false or `account` is missing (a guest, a pending or a restricted account), the "
    "answer states no price; saying that approved partner accounts see prices, or "
    "pointing to an inquiry or a Proforma request, stays within the remit."
)


@dataclass(frozen=True)
class Question:
    """One typed question. `levels` is ordered low to high; `options` maps key to meaning."""

    name: str
    type: QuestionType
    instructions: str
    levels: tuple[str, ...] = ()
    options: tuple[tuple[str, str], ...] = ()

    def labels(self) -> tuple[str, ...]:
        """The answers a judge can give, as the strings human labels use."""
        if self.type == "score":
            return tuple(str(level) for level in range(len(self.levels)))
        if self.type == "noul":
            return ("yes", "no")
        return tuple(key for key, _ in self.options)

    def system_one(self) -> dict[str, Any]:
        """The question in the System One request format (TypeSafe, llama.cpp)."""
        if self.type == "score":
            return {
                "type": "score",
                "instructions": self.instructions,
                "criteria": list(self.levels),
            }
        if self.type == "noul":
            criteria = dict(self.options)
            return {
                "type": "noul",
                "instructions": self.instructions,
                "criteria": {"true": criteria["yes"], "false": criteria["no"]},
            }
        return {
            "type": "choice",
            "instructions": self.instructions,
            "criteria": dict(self.options),
        }

    def prompt_lines(self, number: int) -> list[str]:
        """The question as it appears in an LLM judge's prompt."""
        if self.type == "score":
            kind = "score"
            answers = "; ".join(
                f"{level} = {text}" for level, text in enumerate(self.levels)
            )
            reply = "the level number"
        elif self.type == "noul":
            kind = "yes/no"
            answers = "; ".join(f'"{key}" = {text}' for key, text in self.options)
            reply = '"yes" or "no"'
        else:
            kind = "choice"
            answers = "; ".join(f'"{key}" = {text}' for key, text in self.options)
            reply = "the option key"
        return [
            f"{number}. {self.name} ({kind}): {self.instructions}",
            f"   Answers: {answers}. Reply with {reply}.",
        ]


GROUNDED = Question(
    name="grounded",
    type="score",
    instructions=(
        "Compare `answer` with `reference` only, not with outside knowledge, and judge the "
        "factual statements about products in `answer`. Unit conversions, number formats "
        "(15000 Wp = 15 kWp = 15.000 Wp; 8,7 = 8.7) and rewording count as agreement."
    ),
    levels=(
        "Contradicted: at least one statement in `answer` conflicts with `reference`, for "
        "example a different value, the value of another model or a wrong unit.",
        "Not verifiable: nothing in `answer` conflicts with `reference`, but `answer` states "
        "facts that `reference` does not contain, such as stock levels, delivery times, "
        "services or company details.",
        "Supported: every factual statement about products in `answer` is stated in "
        "`reference`, or `answer` states no product facts.",
    ),
)

APPROPRIATE = Question(
    name="appropriate",
    type="noul",
    instructions=(
        f"Does `answer` stay within the assistant's remit? {REMIT} Judge only the remit, "
        "not whether the facts are correct."
    ),
    options=(
        ("yes", "`answer` stays within the remit."),
        ("no", "`answer` answers or promises something outside the remit."),
    ),
)

BETTER_PICK = Question(
    name="better_pick",
    type="choice",
    instructions=(
        "Which of `answer_a` and `answer_b` is the better reply to `question`? A reply is "
        "better when it is correct according to `reference` and stays within the remit. "
        f"{REMIT} Wording, length, style and units do not make a reply better."
    ),
    options=(
        ("A", "`answer_a` is better."),
        ("B", "`answer_b` is better."),
        ("equal", "Both are equally good, or equally flawed."),
    ),
)

AI_PHRASING = Question(
    name="ai_phrasing",
    type="noul",
    instructions=(
        "Does `answer` use phrasing typical of AI-written marketing text: a 'not X but Y' or "
        "'not only X but also Y' contrast (German 'nicht …, sondern …', 'nicht nur …, "
        "sondern auch …'); three parallel words or phrases strung together for rhythm; a "
        "stock opener such as 'In today's …', 'Whether you're …' (German 'In der heutigen "
        "…', 'Ob … oder …'); or filler such as seamless, robust, cutting-edge, unlock, "
        "elevate, empower (German nahtlos, zukunftssicher, Gamechanger)? Plain sentences "
        "that state facts do not count."
    ),
    options=(
        ("yes", "`answer` contains such phrasing."),
        ("no", "`answer` contains none of it."),
    ),
)

MARKETING = Question(
    name="marketing",
    type="noul",
    instructions=(
        "Does `answer` use promotional language instead of plain information: superlatives, "
        "hype or claims the text cannot back up, such as 'best-in-class', 'unbeatable', "
        "'revolutionary', 'the perfect choice' (German 'erstklassig', 'unschlagbar', "
        "'revolutionär', 'die perfekte Wahl')? Stating a specification plainly does not count."
    ),
    options=(
        ("yes", "`answer` is promotional."),
        ("no", "`answer` is plain information."),
    ),
)

QA_QUESTIONS = (GROUNDED, APPROPRIATE, BETTER_PICK)
COPY_QUESTIONS = (AI_PHRASING, MARKETING)

SYSTEM_PROMPT = (
    "You are an evaluation judge. You receive a JSON state and numbered questions about it. "
    "Answer every question on its own, using only the state. Reply with one JSON object that "
    "has a key for every question name, calibrated probabilities for that answer's options "
    '(either under a "probabilities" key or as the object\'s entries), and a key "reason" '
    "with one or two sentences."
)


def questions_for(item_set: str) -> tuple[Question, ...]:
    return QA_QUESTIONS if item_set == "qa" else COPY_QUESTIONS


def chat_messages(
    state: dict[str, Any], questions: tuple[Question, ...]
) -> list[dict[str, str]]:
    """The LLM judge's messages: the same state and question text a decision model gets.

    The closing line overrides the per-question "reply with" phrasing with the
    calibrated-probabilities form the cascade needs: without per-question
    probabilities a chat reply carries no confidence, and the first pass could
    then never stand (owner ruling 2026-10-11: the wired jev-router first pass
    answers with calibrated probabilities)."""
    lines = [
        "STATE:",
        json.dumps(state, ensure_ascii=False, indent=1),
        "",
        "QUESTIONS:",
    ]
    for number, question in enumerate(questions, 1):
        lines.extend(question.prompt_lines(number))
    keys = ", ".join(question.name for question in questions)
    lines += [
        "",
        "Answer every question with its calibrated probabilities: one JSON object"
        " with a key for every question (" + keys + "), each question's value an"
        " object that maps that question's answer options to probabilities"
        ' ({"grounded": {"0": 0.05, "1": 0.15, "2": 0.8}},'
        ' {"appropriate": {"yes": 0.9, "no": 0.1}},'
        ' {"better_pick": {"A": 0.7, "B": 0.05, "equal": 0.25}}), plus one "reason"'
        " key with one or two sentences. Answer nothing else.",
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]
