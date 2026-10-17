"""Judging the behaviour panel's turns after the fact (#13's Jev pilot; #16 reuses this).

The service's deterministic grounding checks guarantee structure before an answer
ships; the Jev cascade then judges the shipped turn. One item per turn: the
customer's question, the answer as rendered, the reference (what the turn's own
ability calls returned, replayed read-only against the same instance), and —
where the row offers several product candidates — a mechanically constructed
wrong-pick variant as `answer_b`, so `better_pick` has a real choice and the
real answer must win.

The questions are the bake-off's own wording (`rubric.py`: one wording, every
judge). The thresholds started as the #33 formal run's calibration on its
calibration split (docs/research/2026-10-09/judge-bakeoff.md §采用结论) and were
recalibrated on the real-turn pilot (see `TURN_THRESHOLDS`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .rubric import QA_QUESTIONS, Question

TURN_THRESHOLDS: dict[str, float] = {
    # Grounded 0.6 recalibrates the #33 formal calibration's frozen 0.85 on
    # the real-turn pilot (ticket #16, 2026-10-11, runs/pilot-20261011-v4):
    # on the archived panel turns jev's grounded confidence runs 0.0-0.95,
    # every label at 0.6 or above was correct (11/11 in the offline cascade
    # replay of the run's records), and the one wrong label sat at 0.0 — so
    # 0.6 keeps that label out of the first pass and cuts the escalations
    # from 9/11 to 3/11 at unchanged agreement.
    "grounded": 0.6,
    "appropriate": 0.5,
    "better_pick": 0.6,
}


def turns_questions(has_candidates: bool) -> tuple[Question, ...]:
    """All three rubric questions when the turn offers product candidates to pick
    between; without them `better_pick` has nothing to choose between and the
    turn is judged on grounded and appropriate only."""
    return QA_QUESTIONS if has_candidates else QA_QUESTIONS[:2]


def answer_with_offers(
    answer: str,
    page: int | None,
    cards: Sequence[int],
    swap: tuple[int, int] | None = None,
) -> str:
    """`answer` as the judge receives it: the customer's words plus the offers,
    the page's own product named apart from the recommendations.

    The R5 divergence of the 2026-10-11 pilot came from flattening the two roles
    into one "Products offered" list, which read "documented pairing" as a claim
    about the page's own product too. Every driver builds the judged answer's
    offers here, so a pilot row and a regression-suite row read the same way:
    `page` is the product page the turn ran on (`None` when it ran on none) and
    `cards` are the ids the answer offered, the page's own product among them
    when the page offers itself. A row with no products keeps the plain answer.

    `swap` is the wrong-pick variant's `(from, to)`: the variant claims the
    swapped-out card's role for another product — a recommendation offered in
    its place, or, when the source is the page's own product, the page product
    itself, which the variant then misattributes.
    """
    recommended = [pid for pid in cards if pid != page]
    if swap is not None:
        source, target = swap
        if page is not None and source == page:
            page = target
        else:
            recommended = [target if pid == source else pid for pid in recommended]
    lines: list[str] = []
    if page is not None:
        lines.append(f"This page's product: {page}.")
    if recommended:
        lines.append(
            f"Recommended products: {', '.join(str(pid) for pid in recommended)}."
        )
    return answer if not lines else answer + "\n\n" + "\n".join(lines)


def turns_state(row: dict[str, Any]) -> dict[str, Any]:
    """The judge's state for one archived panel row.

    Expected fields: `question` (the customer's words), `answer` (the rendered
    text the customer reads), `reference` (the JSON the turn's ability calls
    returned), `cards` (the offered product ids, informational), and for rows
    with candidates `answer_a` (the real reply) and `answer_b` (the constructed
    wrong-pick variant). `account` (`{"approved": bool}`) is passed on when the
    row has it: the remit judges a price against it, and reads a state without
    it as not approved (rubric.REMIT).
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
    if row.get("account") is not None:
        state["account"] = row["account"]
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
