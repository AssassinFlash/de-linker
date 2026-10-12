"""One reproducible probe of the eval set on OpenRouter's /v1/systemone.

Registry C12: the 11-round agreement figures in
`services/genie/eval/judges/runs/pilot-20261011-t16i2/` were measured on the
old chat route. After the switch to OpenRouter's native `/v1/systemone` with
`typesafe/jev-1.13`, the only live record was one item
(`docs/acceptance/2026-10-11/16i/systemone-probe-20261011.json`). This probe
runs the same call path — `linker_judges.registry.JUDGES["jev"]` through
`linker_judges.judges.call` — once over the archived behaviour-panel set
(the 11 `panel-*.json` rows under the deepseek-flash archive).

It is one pass of jev only. It is not the switched-path agreement rate.
The pilot's 9/11 (`runs/pilot-20261011-t16i2/summary.json`) is also one
pass per item, not a mean over repeated runs: `pilot.py` calls jev once,
then deepseek when a confidence is under `TURN_THRESHOLDS`, and counts
items whose cascade labels match the panel. This probe never calls that
cascade. It records `would_escalate_at_0_6` and stops. The JSON says so
in `not_an_agreement_rate`.

The reference is the turn log's own `tool_calls` (what that turn's abilities
returned and the model saw), not a live replay against a WordPress instance.
A replay would need the instance that served those turns; the log is the
record that still exists, and it is what makes the probe reproducible without
that instance.

Run from `services/genie/eval/judges`:

    uv run --locked python ../../../../docs/acceptance/2026-10-13/genie-facts-protocol/probe-systemone-set.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
JUDGES_DIR = REPO / "services" / "genie" / "eval" / "judges"
if str(JUDGES_DIR) not in sys.path:
    sys.path.insert(0, str(JUDGES_DIR))

import pilot  # noqa: E402
from linker_judges.judges import call  # noqa: E402
from linker_judges.registry import JUDGES  # noqa: E402
from linker_judges.turns import (  # noqa: E402
    TURN_THRESHOLDS,
    answer_with_offers,
    turns_questions,
    turns_state,
)


def build_item(panel: Path, db_path: Path, name: str) -> dict[str, Any]:
    """One panel row, reference taken from the turn log rather than a live replay."""
    payload = json.loads((panel / f"{name}.json").read_text())
    parsed = pilot.parse_stream(payload["stream"])
    meta, blocks = parsed["meta"], parsed["blocks"]
    answer_text, cards = pilot.rendered_answer(blocks)
    db = sqlite3.connect(db_path)
    try:
        row = db.execute(
            "SELECT tool_calls FROM turns WHERE id = ?", (meta.get("turn_id"),)
        ).fetchone()
    finally:
        db.close()
    calls = json.loads(row[0]) if row else []
    reference = {
        "source": "turn-log tool_calls, not a live WordPress replay",
        "calls": calls,
    }
    swap = pilot.SWAPS.get(name)
    page = pilot.PAGE_PRODUCT.get(name)
    return {
        "id": name,
        "turn_id": meta.get("turn_id"),
        "question": pilot.QUESTIONS[name],
        "answer": answer_with_offers(answer_text, page, cards),
        "reference": reference,
        "cards": cards,
        "answer_a": answer_with_offers(answer_text, page, cards),
        "answer_b": answer_with_offers(
            answer_text, page, cards, (swap[1], swap[2]) if swap else None
        ),
        "has_candidates": swap is not None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One systemone pass over the eval set.")
    parser.add_argument(
        "--panel",
        type=Path,
        default=REPO / "docs" / "acceptance" / "2026-10-11" / "13" / "deepseek-flash",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".cache" / "linker-genie" / "turns.sqlite",
    )
    parser.add_argument("--out", type=Path, default=HERE / "systemone-probe.json")
    args = parser.parse_args(argv)

    names = sorted(path.stem for path in args.panel.glob("panel-*.json"))
    judge = JUDGES["jev"]
    items: list[dict[str, Any]] = []
    missing_key = False
    started = time.time()
    for name in names:
        item = build_item(args.panel, args.db, name)
        questions = turns_questions(item["has_candidates"])
        verdict = call(judge, turns_state(item), questions)
        if verdict.error and "key" in verdict.error.lower():
            missing_key = True
        escalated = {
            question.name: (verdict.answers[question.name].confidence or -1.0)
            < TURN_THRESHOLDS[question.name]
            for question in questions
        }
        items.append(
            {
                "id": name,
                "turn_id": item["turn_id"],
                "question": item["question"],
                "model_reported": verdict.model_reported,
                "seconds": verdict.seconds,
                "attempts": verdict.attempts,
                "input_tokens": verdict.input_tokens,
                "output_tokens": verdict.output_tokens,
                "cost_usd": verdict.cost_usd,
                "error": verdict.error,
                "answers": {
                    question_name: {
                        "label": answer.label,
                        "confidence": answer.confidence,
                    }
                    for question_name, answer in verdict.answers.items()
                },
                "would_escalate_at_0_6": escalated,
            }
        )
        print(
            f"{name}: model={verdict.model_reported or '-'} "
            f"error={verdict.error or '-'} {verdict.seconds:.1f}s",
            flush=True,
        )

    record = {
        "probe": "one pass of the archived behaviour-panel set on /v1/systemone",
        "not_an_agreement_rate": (
            "One jev pass over the 11 archived panel items, not the "
            "switched-path agreement. The pilot's 9/11 "
            "(runs/pilot-20261011-t16i2/summary.json) is also one call per "
            "item, not a mean of repeated runs: pilot.py calls jev once and "
            "deepseek only when a confidence is under TURN_THRESHOLDS, then "
            "counts cascade labels against the panel. This probe never calls "
            "that cascade. would_escalate_at_0_6 is computed here and not acted "
            "on; 7 of 11 items would escalate on grounded."
        ),
        "date": "2026-10-13",
        "run_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "seconds": round(time.time() - started, 1),
        "judge": {
            "name": judge.name,
            "kind": judge.kind,
            "model_requested": judge.model,
            "endpoint": judge.endpoint,
            "url": "https://openrouter.ai/api/v1/systemone",
        },
        "set": {
            "panel": str(args.panel.relative_to(REPO)),
            "items": len(names),
            "reference": "turn-log tool_calls, not a live WordPress replay",
        },
        "items": items,
        "missing_key": missing_key,
    }
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {args.out} ({len(items)} items, {record['seconds']}s)")
    return 1 if missing_key or any(item["error"] for item in items) else 0


if __name__ == "__main__":
    sys.exit(main())
