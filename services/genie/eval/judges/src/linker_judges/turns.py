"""Judging the behaviour panel's turns after the fact (#13's Jev pilot; #16 reuses this).

The service's deterministic grounding checks guarantee structure before an answer
ships; the Jev cascade then judges the shipped turn. One item per turn: the
customer's question, the answer as rendered, the reference (what the turn's own
ability calls returned, replayed read-only against the same instance), and —
where the row offers several product candidates — a mechanically constructed
wrong-pick variant as `answer_b`, so `better_pick` has a real choice and the
real answer must win.

The questions are the bake-off's own wording (`rubric.py`: one wording, every
judge). The thresholds are the ones the #33 formal run calibrated on its
calibration split and froze (docs/research/2026-10-09/judge-bakeoff.md
§采用结论), applied unchanged here.
"""

from __future__ import annotations

from typing import Any

from .rubric import QA_QUESTIONS, Question

TURN_THRESHOLDS: dict[str, float] = {
    "grounded": 0.85,
    "appropriate": 0.5,
    "better_pick": 0.6,
}


def turns_questions(has_candidates: bool) -> tuple[Question, ...]:
    """All three rubric questions when the turn offers product candidates to pick
    between; without them `better_pick` has nothing to choose between and the
    turn is judged on grounded and appropriate only."""
    return QA_QUESTIONS if has_candidates else QA_QUESTIONS[:2]


def turns_state(row: dict[str, Any]) -> dict[str, Any]:
    """The judge's state for one archived panel row.

    Expected fields: `question` (the customer's words), `answer` (the rendered
    text the customer reads), `reference` (the JSON the turn's ability calls
    returned), `cards` (the offered product ids, informational), and for rows
    with candidates `answer_a` (the real reply) and `answer_b` (the constructed
    wrong-pick variant).
    """
    state: dict[str, Any] = {
        "question": row["question"],
        "reference": row["reference"],
        "answer": row["answer"],
        "cards": row.get("cards", []),
    }
    if row.get("answer_b") is not None:
        state["answer_a"] = row["answer_a"]
        state["answer_b"] = row["answer_b"]
    return state


def cascade_answers(
    first: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
    questions: tuple[Question, ...],
    thresholds: dict[str, float] | None = None,
) -> tuple[dict[str, str | None], dict[str, str]]:
    """The cascade's final labels for one item, per question.

    The first judge's label stands when its confidence reaches the question's
    frozen threshold; otherwise the fallback judge's label is taken. Returns
    `(labels, sources)` — `sources[q]` names the judge each label came from, or
    `"unresolved"` when the confidence fell short and no fallback verdict exists
    (an outage must not silently become a first-judge answer).
    """
    limits = thresholds or TURN_THRESHOLDS
    labels: dict[str, str | None] = {}
    sources: dict[str, str] = {}
    for question in questions:
        name = question.name
        first_answer = ((first or {}).get("answers") or {}).get(name) or {}
        label = first_answer.get("label")
        confidence = first_answer.get("confidence")
        if (
            label is not None
            and confidence is not None
            and float(confidence) >= limits[name]
        ):
            labels[name] = str(label)
            sources[name] = str((first or {}).get("judge", "first"))
            continue
        fallback_answer = ((fallback or {}).get("answers") or {}).get(name) or {}
        fallback_label = fallback_answer.get("label")
        if fallback_label is not None:
            labels[name] = str(fallback_label)
            sources[name] = str((fallback or {}).get("judge", "fallback"))
        else:
            labels[name] = None
            sources[name] = "unresolved"
    return labels, sources
