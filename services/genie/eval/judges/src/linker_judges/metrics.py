"""Agreement with the human labels, repeatability, cost, latency and the cascade.

Definitions (docs/research/2026-10-09/judge-bakeoff.md):
- agreement: share of (item, question) where the judge's label equals the human label,
  averaged over runs; an invalid answer counts as a disagreement;
- stability: share of (item, question) whose label is the same in every run;
- one judgment = one call evaluating one item (all its questions together);
- cascade: a decision model's answer stands when its confidence reaches the question's
  threshold, otherwise the fallback judge's answer is used. Thresholds come from the
  calibration split only, by the rule fixed before any result (THRESHOLD_GRID,
  MAX_CALIBRATION_LOSS), and are then applied unchanged to the test split.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .rubric import QA_QUESTIONS

Records = list[dict[str, Any]]

# The JEV-as-a-Judge frozen-policy grid and rule (arXiv:2609.26550 §7): the threshold
# with the most coverage whose calibration accuracy stays within two points of the
# fallback's; if none does, everything is escalated.
THRESHOLD_GRID = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0)
MAX_CALIBRATION_LOSS = 0.02
NEVER = float("inf")
QA_NAMES = tuple(question.name for question in QA_QUESTIONS)


def latest(records: Records) -> Records:
    """One record per (item, run): a call that was repeated after a failure keeps its
    last attempt (the runner appends, so file order is call order)."""
    kept: dict[tuple[str, int], dict[str, Any]] = {}
    for record in records:
        kept[(record["item"], int(record["run"]))] = record
    return list(kept.values())


def by_run(records: Records) -> dict[int, dict[str, dict[str, Any]]]:
    """run -> item -> record (the last record wins if a call was repeated)."""
    table: dict[int, dict[str, dict[str, Any]]] = {}
    for record in records:
        table.setdefault(int(record["run"]), {})[record["item"]] = record
    return table


def label_of(record: dict[str, Any] | None, question: str) -> str | None:
    if record is None:
        return None
    answer = record["answers"].get(question) or {}
    label = answer.get("label")
    return str(label) if label is not None else None


def confidence_of(record: dict[str, Any] | None, question: str) -> float:
    if record is None:
        return -1.0
    answer = record["answers"].get(question) or {}
    value = answer.get("confidence")
    return (
        float(value) if value is not None and answer.get("label") is not None else -1.0
    )


def agreement(
    records: Records,
    labels: dict[str, dict[str, str]],
    item_ids: Iterable[str],
    questions: Iterable[str],
) -> float | None:
    """Mean over runs of the share of (item, question) labelled as the human did."""
    ids = [i for i in item_ids if i in labels]
    names = list(questions)
    runs = by_run(records)
    if not ids or not runs:
        return None
    shares = []
    for table in runs.values():
        hits = sum(
            label_of(table.get(i), q) == labels[i][q] for i in ids for q in names
        )
        shares.append(hits / (len(ids) * len(names)))
    return statistics.fmean(shares)


def stability(
    records: Records, item_ids: Iterable[str], questions: Iterable[str]
) -> float | None:
    """Share of (item, question) with one and the same valid label in every run."""
    runs = by_run(records)
    if len(runs) < 2:
        return None
    names = list(questions)
    ids = [i for i in item_ids if all(i in table for table in runs.values())]
    if not ids:
        return None
    stable = 0
    for i in ids:
        for q in names:
            seen = {label_of(table[i], q) for table in runs.values()}
            stable += len(seen) == 1 and None not in seen
    return stable / (len(ids) * len(names))


def score_variance(
    records: Records, item_ids: Iterable[str], question: str = "grounded"
) -> float | None:
    """Mean over items of the population variance of the score level across runs."""
    runs = by_run(records)
    if len(runs) < 2:
        return None
    variances = []
    for i in item_ids:
        levels = [label_of(table.get(i), question) for table in runs.values()]
        numbers = [int(level) for level in levels if level is not None]
        if len(numbers) == len(runs):
            variances.append(statistics.pvariance(numbers))
    return statistics.fmean(variances) if variances else None


def invalid_share(records: Records, questions: Iterable[str]) -> float:
    names = list(questions)
    total = sum(len(names) for _ in records)
    invalid = sum(label_of(r, q) is None for r in records for q in names)
    return invalid / total if total else 0.0


def cost_per_thousand(records: Records) -> float | None:
    """USD per 1,000 judgments (calls), from the billed tokens of each call."""
    calls = [r for r in records if not r.get("error")]
    return 1000 * statistics.fmean(r["cost_usd"] for r in calls) if calls else None


def latency(records: Records) -> tuple[float, float] | None:
    """(p50, p95) seconds per call, measured at the client."""
    seconds = sorted(r["seconds"] for r in records if not r.get("error"))
    if not seconds:
        return None
    return statistics.median(seconds), _percentile(seconds, 0.95)


def _percentile(sorted_values: list[float], share: float) -> float:
    """Nearest-rank percentile."""
    rank = max(1, math.ceil(share * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


@dataclass(frozen=True)
class Cascade:
    thresholds: dict[str, float]
    calibration: dict[str, dict[str, float]]
    agreement: float | None
    first_agreement: float | None
    fallback_agreement: float | None
    coverage: dict[str, float]
    escalated_items: float
    cost_per_thousand: float | None
    fallback_cost_per_thousand: float | None


def _cascade_label(
    first: dict[str, Any] | None, fallback: dict[str, Any] | None, q: str, tau: float
) -> str | None:
    if confidence_of(first, q) >= tau:
        return label_of(first, q)
    return label_of(fallback, q)


def choose_threshold(
    first: Records,
    fallback: Records,
    labels: dict[str, dict[str, str]],
    calibration_ids: list[str],
    q: str,
) -> tuple[float, dict[str, float]]:
    """The calibration-split rule: most coverage within MAX_CALIBRATION_LOSS of the fallback."""
    f_runs, b_runs = by_run(first), by_run(fallback)
    ids = [i for i in calibration_ids if i in labels]
    runs = sorted(set(f_runs) & set(b_runs))
    if not ids or not runs:
        return NEVER, {}

    def accuracy(tau: float) -> float:
        """Calibration agreement when answers below `tau` go to the fallback."""
        hits = sum(
            _cascade_label(f_runs[r].get(i), b_runs[r].get(i), q, tau) == labels[i][q]
            for r in runs
            for i in ids
        )
        return hits / (len(runs) * len(ids))

    base = accuracy(NEVER)
    trace = {"fallback": base}
    for tau in THRESHOLD_GRID:
        cascaded = accuracy(tau)
        trace[str(tau)] = cascaded
        if cascaded >= base - MAX_CALIBRATION_LOSS:
            return tau, trace
    return NEVER, trace


def cascade(
    first: Records,
    fallback: Records,
    labels: dict[str, dict[str, str]],
    calibration_ids: list[str],
    test_ids: list[str],
    questions: tuple[str, ...] = QA_NAMES,
) -> Cascade:
    """Thresholds from calibration, applied unchanged to test; cost counts the first
    judge on every item and the fallback on every item with at least one escalation."""
    thresholds, traces = {}, {}
    for q in questions:
        thresholds[q], traces[q] = choose_threshold(
            first, fallback, labels, calibration_ids, q
        )
    f_runs, b_runs = by_run(first), by_run(fallback)
    runs = sorted(set(f_runs) & set(b_runs))
    ids = [i for i in test_ids if i in labels]
    if not ids or not runs:
        return Cascade(thresholds, traces, None, None, None, {}, 0.0, None, None)
    hits = accepted = 0
    accepted_by_q = {q: 0 for q in questions}
    costs, fallback_costs, escalated = [], [], 0
    for r in runs:
        for i in ids:
            f, b = f_runs[r].get(i), b_runs[r].get(i)
            any_escalated = False
            for q in questions:
                take_first = confidence_of(f, q) >= thresholds[q]
                accepted_by_q[q] += take_first
                accepted += take_first
                any_escalated |= not take_first
                hits += (label_of(f, q) if take_first else label_of(b, q)) == labels[i][
                    q
                ]
            escalated += any_escalated
            cost = (f or {}).get("cost_usd", 0.0) + (
                (b or {}).get("cost_usd", 0.0) if any_escalated else 0.0
            )
            costs.append(cost)
            fallback_costs.append((b or {}).get("cost_usd", 0.0))
    total = len(runs) * len(ids)
    return Cascade(
        thresholds,
        traces,
        hits / (total * len(questions)),
        agreement(first, labels, ids, questions),
        agreement(fallback, labels, ids, questions),
        {q: accepted_by_q[q] / total for q in questions},
        escalated / total,
        1000 * statistics.fmean(costs),
        1000 * statistics.fmean(fallback_costs),
    )
