"""The #13 Jev pilot: post-hoc cascade judging of one archived behaviour-panel run.

`uv run --project . python pilot.py --panel <dir> --db <turns.sqlite> --wp <url> --out <run-dir>`

For every archived panel row the driver rebuilds the judge item — the customer's
question, the rendered answer (text plus the offered product ids) and the
reference (the row's own ability calls replayed read-only against the same
instance, in the wire format of linker_genie.abilities) — then runs the cascade:
Jev (jev-1.13 via aihubmix) first; any question whose confidence falls below its
frozen threshold (`turns.TURN_THRESHOLDS`, the #33 formal calibration) takes the
direct DeepSeek escalation judge's answer (`registry.JUDGES["deepseek"]`).

Every call lands as one JSON line in the run directory in the runner's record
format, plus `cascade.jsonl` with the final labels and where each came from, and
`summary.json` with the agreement of the cascade against the panel's
deterministic outcomes (every shipped row is grounded; the constructed
wrong-pick variant must lose).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from linker_judges.judges import call
from linker_judges.registry import JUDGES
from linker_judges.rubric import questions_for  # noqa: F401  (qa/copy sets)
from linker_judges.turns import (
    TURN_THRESHOLDS,
    cascade_answers,
    turns_questions,
    turns_state,
)

# The panel rows and the mechanical wrong-pick swap for `answer_b`: one offered
# product id replaced so the variant offers a product the reference does not
# back (an ETR commercial unit, a battery outside the documented pairings, the
# declined model). Rows without at least two candidates are not asked
# better_pick at all.
SWAPS: dict[str, tuple[str, int, int]] = {
    "panel-r1": ("6514", 6514, 6507),
    "panel-r2en": ("6514", 6514, 6507),
    "panel-r2de": ("3556", 3556, 6507),
    "panel-r5": ("2092", 2092, 3581),
    "panel-r10": ("3611", 3611, 3581),
    "panel-r3spell": ("2198", 2198, 2199),
    "panel-r4spell": ("6483", 6483, 6507),
    "panel-r11spell": ("3581", 3581, 4107),
}

# The rows and their exact customer questions — the panel wording of
# docs/acceptance/genie-panel.md (and the rerun records). The archive and the
# turn log do not carry the question text, so the pilot states it here.
QUESTIONS: dict[str, str] = {
    "panel-r1": "I need a three-phase hybrid inverter for a home with 10 kWp PV and a future battery.",
    "panel-r2en": "I need a three-phase hybrid inverter for a home with 10 kWp PV and a future battery. Any brand is fine.",
    "panel-r2de": "Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohngebäude mit 10 kWp PV und späterer Batterie. Marke ist egal.",
    "panel-r5": "Which batteries have documented pairing with this model?",
    "panel-r8en": "Do you do installations?",
    "panel-r14de": "Lieferzeit?",
    "panel-r10": "I already have a GoodWe GW10K-ET and want to add a battery.",
    "panel-r3spell": "We have twelve kilowatt peak on a three-phase home — is the HS3-5K enough for that?",
    "panel-r4spell": "I need a hybrid inverter for my home.",
    "panel-r11spell": "I need a forty-eight volt battery for a single-phase home.",
    "panel-r13spell": "Tell me about this model.",
}


def parse_stream(stream: str) -> dict[str, Any]:
    """The archived SSE text -> {meta, blocks}."""
    meta: dict[str, Any] = {}
    blocks: list[dict[str, Any]] = []
    for event in stream.split("\n\n"):
        lines = [line for line in event.splitlines() if line.startswith("data: ")]
        if not lines:
            continue
        data = json.loads(lines[0][6:])
        if "turn_id" in data:
            meta = data
        else:
            blocks.append(data)
    return {"meta": meta, "blocks": blocks}


def rendered_answer(blocks: list[dict[str, Any]]) -> tuple[str, list[int]]:
    """The words and product ids the customer is shown."""
    parts: list[str] = []
    cards: list[int] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "text":
            parts.append(str(block.get("text", "")))
        elif kind == "handoff":
            parts.append(str(block.get("summary", "")))
        elif kind == "cards":
            cards.extend(block.get("product_ids", []))
        elif kind == "ask":
            parts.append(f"[The assistant asks about: {block.get('field', '')}]")
        elif kind == "action":
            parts.append(f"[The assistant offers the action: {block.get('name', '')}]")
    return "\n".join(parts), cards


def replay(
    base_url: str, calls: list[dict[str, Any]], timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Re-run a turn's ability calls read-only and return what they answered.

    Same wire format as `linker_genie.abilities.AbilityClient`: anonymous GET,
    the input as nested query params (`input[k]=v`, lists `input[k][i]`).
    """
    replayed = []
    for one in calls:
        params: dict[str, str] = {}
        for key, value in (one.get("arguments") or {}).items():
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    params[f"input[{key}][{index}]"] = str(item)
            else:
                params[f"input[{key}]"] = str(value)
        url = (
            base_url.rstrip("/")
            + "/wp-json/wp-abilities/v1/abilities/"
            + urllib.parse.quote(one["name"], safe="")
            + "/run?"
            + urllib.parse.urlencode(params)
        )
        with urllib.request.urlopen(url, timeout=timeout) as reply:
            body = json.loads(reply.read())
        result = body.get("result", body) if isinstance(body, dict) else body
        replayed.append(
            {"name": one["name"], "arguments": one.get("arguments"), "result": result}
        )
    return replayed


def record(judge: str, item: str, run: int, verdict: Any) -> dict[str, Any]:
    return {
        "judge": judge,
        "item": item,
        "run": run,
        "answers": {
            name: {
                "label": answer.label,
                "confidence": answer.confidence,
                "probabilities": answer.probabilities,
            }
            for name, answer in verdict.answers.items()
        },
        "seconds": verdict.seconds,
        "attempts": verdict.attempts,
        "started_at": verdict.started_at,
        "input_tokens": verdict.input_tokens,
        "output_tokens": verdict.output_tokens,
        "cost_usd": verdict.cost_usd,
        "model_reported": verdict.model_reported,
        "reason": verdict.reason,
        "error": verdict.error,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="#13 Jev pilot over panel turns")
    parser.add_argument("--panel", type=Path, required=True, help="archived panel dir")
    parser.add_argument("--db", type=Path, required=True, help="the turn log sqlite")
    parser.add_argument("--wp", required=True, help="the instance base URL for replay")
    parser.add_argument("--out", type=Path, required=True, help="run directory")
    args = parser.parse_args(argv)

    first, fallback = JUDGES["jev"], JUDGES["deepseek"]
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row

    jev_rows: list[dict[str, Any]] = []
    fallback_rows: list[dict[str, Any]] = []
    cascade_rows: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    archives = sorted(args.panel.glob("panel-*.json"))
    for archive in archives:
        name = archive.stem
        payload = json.loads(archive.read_text())
        parsed = parse_stream(payload["stream"])
        meta, blocks = parsed["meta"], parsed["blocks"]
        answer_text, cards = rendered_answer(blocks)
        row = db.execute(
            "SELECT tool_calls FROM turns WHERE id = ?", (meta.get("turn_id"),)
        ).fetchone()
        calls = json.loads(row["tool_calls"]) if row else []
        reference = {"calls": replay(args.wp, calls)}
        swap = SWAPS.get(name)
        has_candidates = swap is not None
        products = ", ".join(str(pid) for pid in cards)
        variant = products
        if swap:
            variant = ", ".join(
                str(swap[2]) if pid == swap[1] else str(pid) for pid in cards
            )
        item = {
            "question": QUESTIONS[name],
            "answer": answer_text + f"\n\nProducts offered: {products}",
            "reference": reference,
            "cards": cards,
            "answer_a": answer_text + f"\n\nProducts offered: {products}",
            "answer_b": answer_text + f"\n\nProducts offered: {variant}",
        }
        questions = turns_questions(has_candidates)

        started = time.time()
        first_verdict = call(first, turns_state(item), questions)
        jev_rows.append(record(first.name, name, 1, first_verdict))
        thresholds_met = {
            q.name: (
                (first_verdict.answers[q.name].confidence or -1.0)
                >= TURN_THRESHOLDS[q.name]
                and first_verdict.answers[q.name].label is not None
            )
            for q in questions
        }
        fallback_verdict = None
        if not all(thresholds_met.values()):
            fallback_verdict = call(fallback, turns_state(item), questions)
            fallback_rows.append(record(fallback.name, name, 1, fallback_verdict))
        labels, sources = cascade_answers(
            {
                "judge": first.name,
                "answers": {
                    q.name: {
                        "label": first_verdict.answers[q.name].label,
                        "confidence": first_verdict.answers[q.name].confidence,
                    }
                    for q in questions
                },
            },
            (
                {
                    "judge": fallback.name,
                    "answers": {
                        q.name: {
                            "label": fallback_verdict.answers[q.name].label,
                            "confidence": fallback_verdict.answers[q.name].confidence,
                        }
                        for q in questions
                    },
                }
            )
            if fallback_verdict
            else None,
            questions,
        )
        cascade_rows.append(
            {
                "item": name,
                "turn_id": meta.get("turn_id"),
                "grounded": meta.get("grounded"),
                "labels": labels,
                "sources": sources,
                "thresholds_met": thresholds_met,
                "escalated": fallback_verdict is not None,
                "swap": {"from": swap[1], "to": swap[2]} if swap else None,
            }
        )
        truth = {"grounded": "2", "appropriate": "yes"}
        if has_candidates:
            truth["better_pick"] = "A"
        row_summary = {
            "item": name,
            "agrees": all(labels[q] == truth[q] for q in truth),
            **{f"{q}_label": labels[q] for q in labels},
            **{f"{q}_source": sources[q] for q in sources},
        }
        summary.append(row_summary)
        flags = "OK " if row_summary["agrees"] else "DIFF"
        print(
            f"{flags} {name}: "
            + " ".join(f"{q}={labels[q]}({sources[q]})" for q in labels)
            + f"  [{time.time() - started:.1f}s]",
            flush=True,
        )

    write_jsonl(
        args.out / "items.jsonl",
        [
            {
                "id": row["item"],
                "turn_id": row["turn_id"],
                "question": QUESTIONS[row["item"]],
                "escalated": row["escalated"],
                "labels": row["labels"],
                "sources": row["sources"],
            }
            for row in cascade_rows
        ],
    )
    write_jsonl(args.out / "jev.jsonl", jev_rows)
    write_jsonl(args.out / "deepseek.jsonl", fallback_rows)
    write_jsonl(args.out / "cascade.jsonl", cascade_rows)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1)
    )
    agrees = sum(1 for row in summary if row["agrees"])
    print(f"\nagreement {agrees}/{len(summary)}; escalated {len(fallback_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
