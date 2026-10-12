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

REMIT = (
    "The assistant answers questions about products, models, series, specifications, "
    "compatibility and documents. Questions about delivery, shipping terms, stock "
    "quantities, installation, commissioning, warranty handling, prices, payment or the "
    "company itself only get a referral to the team at sales@de-linker.com. It may say "
    "that a product is in stock, but never gives stock quantities, delivery times or "
    "dates, shipping terms (Incoterms) or service commitments."
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
        "better when it is correct according to `reference` and stays within the remit "
        "(questions about delivery, stock quantities, services, payment or the company only "
        "get a referral to sales@de-linker.com). Wording, length, style and units do not "
        "make a reply better."
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
