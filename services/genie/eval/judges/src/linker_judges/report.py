"""Markdown tables for docs/research/2026-10-09/judge-bakeoff.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import metrics
from .dataset import read_jsonl
from .registry import JUDGES
from .rubric import COPY_QUESTIONS, QA_QUESTIONS

QA = tuple(q.name for q in QA_QUESTIONS)
COPY = tuple(q.name for q in COPY_QUESTIONS)
CLASSES = (
    "correct",
    "paraphrase_correct",
    "numeric_tamper",
    "wrong_model",
    "out_of_scope_answered",
)
CLOSED_LLMS = ("deepseek", "haiku", "gemini")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def _usd(value: float | None) -> str:
    return "—" if value is None else f"${value:.4f}"


def load_runs(run_dir: Path) -> dict[str, metrics.Records]:
    return {
        path.stem: metrics.latest(read_jsonl(path))
        for path in sorted(run_dir.glob("*.jsonl"))
        if path.stem in JUDGES
    }


def render(
    run_dir: Path,
    items: dict[str, dict[str, Any]],
    construction: dict[str, dict[str, Any]],
    labels: dict[str, dict[str, str]],
    split: str,
) -> str:
    runs = load_runs(run_dir)

    def ids(item_set: str, **where: str) -> list[str]:
        chosen = []
        for item_id, item in items.items():
            if item["set"] != item_set or item_id not in labels:
                continue
            if split != "all" and item["split"] != split:
                continue
            if all(
                item.get(k) == v or construction[item_id].get(k) == v
                for k, v in where.items()
            ):
                chosen.append(item_id)
        return chosen

    qa, copy = ids("qa"), ids("copy")
    out = [
        f"Items with human labels in split `{split}`: {len(qa)} answer pairs, {len(copy)} copy items. "
        "Agreement is the mean over runs; one judgment = one call on one item.",
        "",
        "| judge | weights | runs | factual (3 questions) | EN | DE | grounded | appropriate | better_pick | stable across runs | grounded variance | invalid | USD per 1,000 judgments | p50 / p95 s per judgment |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, records in runs.items():
        judge = JUDGES[name]
        qa_records = [r for r in records if r["item"] in set(qa)]
        if not qa_records:
            continue
        timing = metrics.latency(qa_records)
        out.append(
            "| "
            + " | ".join(
                [
                    name,
                    judge.weights,
                    str(len(metrics.by_run(qa_records))),
                    _pct(metrics.agreement(qa_records, labels, qa, QA)),
                    _pct(
                        metrics.agreement(qa_records, labels, ids("qa", lang="en"), QA)
                    ),
                    _pct(
                        metrics.agreement(qa_records, labels, ids("qa", lang="de"), QA)
                    ),
                    *(
                        _pct(metrics.agreement(qa_records, labels, qa, (q,)))
                        for q in QA
                    ),
                    _pct(metrics.stability(qa_records, qa, QA)),
                    "—"
                    if (v := metrics.score_variance(qa_records, qa)) is None
                    else f"{v:.3f}",
                    _pct(metrics.invalid_share(qa_records, QA)),
                    _usd(metrics.cost_per_thousand(qa_records)),
                    "—" if timing is None else f"{timing[0]:.2f} / {timing[1]:.2f}",
                ]
            )
            + " |"
        )
    out += [
        "",
        "Factual agreement by answer class:",
        "",
        "| judge | " + " | ".join(CLASSES) + " |",
        "|---" * (len(CLASSES) + 1) + "|",
    ]
    for name, records in runs.items():
        if not any(r["item"] in set(qa) for r in records):
            continue
        cells = [
            _pct(metrics.agreement(records, labels, ids("qa", answer_class=c), QA))
            for c in CLASSES
        ]
        out.append(f"| {name} | " + " | ".join(cells) + " |")

    if copy:
        out += [
            "",
            "Copy quality without a reference (AI phrasing, marketing tone):",
            "",
            "| judge | both questions | EN | DE | ai_phrasing | marketing |",
            "|---|---|---|---|---|---|",
        ]
        for name, records in runs.items():
            copy_records = [r for r in records if r["item"] in set(copy)]
            if not copy_records:
                continue
            out.append(
                f"| {name} | "
                + " | ".join(
                    [
                        _pct(metrics.agreement(copy_records, labels, copy, COPY)),
                        _pct(
                            metrics.agreement(
                                copy_records, labels, ids("copy", lang="en"), COPY
                            )
                        ),
                        _pct(
                            metrics.agreement(
                                copy_records, labels, ids("copy", lang="de"), COPY
                            )
                        ),
                        *(
                            _pct(metrics.agreement(copy_records, labels, copy, (q,)))
                            for q in COPY
                        ),
                    ]
                )
                + " |"
            )

    calibration = [
        i
        for i, item in items.items()
        if item["set"] == "qa" and item["split"] == "calibration" and i in labels
    ]
    llms = [name for name in CLOSED_LLMS if name in runs]
    if "jev" in runs and llms and calibration:
        fallback = max(
            llms,
            key=lambda name: (
                metrics.agreement(runs[name], labels, calibration, QA) or 0.0,
                -(metrics.cost_per_thousand(runs[name]) or 0.0),
            ),
        )
        test = [
            i
            for i, item in items.items()
            if item["set"] == "qa" and item["split"] == "test" and i in labels
        ]
        result = metrics.cascade(runs["jev"], runs[fallback], labels, calibration, test)
        thresholds = ", ".join(
            f"{q} ≥ {t}" if t != metrics.NEVER else f"{q}: escalate all"
            for q, t in result.thresholds.items()
        )
        jev_test_qa = [r for r in runs["jev"] if r["item"] in set(qa)]
        out += [
            "",
            f"Jev confidence cascade (fallback = {fallback}, the best LLM on the calibration split; "
            f"thresholds from calibration only: {thresholds}):",
            "",
            "| on the test split | factual agreement | items escalated | USD per 1,000 judgments |",
            "|---|---|---|---|",
            f"| Jev alone | {_pct(result.first_agreement)} | 0% | {_usd(metrics.cost_per_thousand(jev_test_qa))} |",
            f"| {fallback} alone | {_pct(result.fallback_agreement)} | 100% | {_usd(result.fallback_cost_per_thousand)} |",
            f"| cascade | {_pct(result.agreement)} | {_pct(result.escalated_items)} | {_usd(result.cost_per_thousand)} |",
            "",
            "Accepted from Jev per question: "
            + ", ".join(f"{q} {_pct(v)}" for q, v in result.coverage.items()),
        ]
    return "\n".join(out)
