"""The Jev -> DeepSeek cascade, over one item, as one function.

`turns.py` owns the rule (the thresholds and which label stands); this module
owns the two calls around it, so every caller runs the cascade the same way:
the first judge answers every question, and only when one of its confidences
falls short does the escalation judge get the item. The #13 pilot (`pilot.py`)
drives it for the archived panel rows; #16's regression suite (`score.py`)
drives it for the turns the suite just took, one item per question; the VPS
quality worker (`linker_genie.quality`) drives it for every live turn.

A first judge that *failed* (its call raised after the retries, so `error` is
set) is not a first judge that was unsure: the item is not escalated, and the
cascade comes back with `error` set and every label unresolved. Escalating an
outage would put the DeepSeek judge in Jev's place without anyone seeing it —
the silent model swap the model routing law forbids (AGENTS.md §5: an
OpenRouter failure is retried and then reported, never quietly degraded).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .judges import Judge, Verdict, call
from .rubric import Question
from .turns import TURN_THRESHOLDS, cascade_answers, turns_state


@dataclass(frozen=True)
class Cascade:
    """One item's verdicts and the labels the cascade settled on."""

    first: Verdict
    fallback: Verdict | None
    labels: dict[str, str | None]
    sources: dict[str, str]
    short: tuple[str, ...] = ()
    """The questions whose first-judge confidence fell short (the escalation's
    reason); empty when nothing escalated."""

    @property
    def escalated(self) -> bool:
        return self.fallback is not None

    @property
    def error(self) -> str | None:
        """Why the item has no verdict: the first judge's failure, else the
        escalation judge's; None when every call answered."""
        if self.first.error:
            return f"first judge: {self.first.error}"
        if self.fallback is not None and self.fallback.error:
            return f"escalation judge: {self.fallback.error}"
        return None


def run_cascade(
    item: dict[str, Any],
    first: Judge,
    fallback: Judge,
    questions: tuple[Question, ...],
    thresholds: dict[str, float] | None = None,
) -> Cascade:
    """Judge one item: `first` for everything, `fallback` only where confidence
    fell short of the question's threshold.

    `item` is `turns_state()`'s shape: question, answer, reference, cards, and
    for items with candidates `answer_a`/`answer_b`.
    """
    limits = thresholds or TURN_THRESHOLDS
    state = turns_state(item)
    first_verdict = call(first, state, questions)
    if first_verdict.error:
        return Cascade(
            first_verdict,
            None,
            {question.name: None for question in questions},
            {question.name: "unresolved" for question in questions},
        )
    first_answer = {
        question.name: first_verdict.answers[question.name] for question in questions
    }
    short = [
        question.name
        for question in questions
        if first_answer[question.name].label is None
        or (first_answer[question.name].confidence or -1.0) < limits[question.name]
    ]

    fallback_verdict = None
    fallback_answer: dict[str, Any] = {}
    if short:
        fallback_verdict = call(fallback, state, questions)
        fallback_answer = {
            question.name: fallback_verdict.answers[question.name]
            for question in questions
        }

    labels, sources = cascade_answers(
        {
            "judge": first.name,
            "answers": {
                name: {"label": answer.label, "confidence": answer.confidence}
                for name, answer in first_answer.items()
            },
        },
        (
            {
                "judge": fallback.name,
                "answers": {
                    name: {"label": answer.label, "confidence": answer.confidence}
                    for name, answer in fallback_answer.items()
                },
            }
            if fallback_verdict
            else None
        ),
        questions,
        limits,
    )
    return Cascade(first_verdict, fallback_verdict, labels, sources, tuple(short))
