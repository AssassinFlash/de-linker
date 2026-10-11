"""One live probe of the jev judge on OpenRouter's /v1/systemone (2026-10-11, ticket #16 / 16i).

Jev's judge entry moved to OpenRouter's native `/v1/systemone` with the direct
model id `typesafe/jev-1.13` (branch commit b6fefe9, owner ruling 2026-10-11):
the chat route (`typesafe/jev-router`) is a meta-router that delegates per call
to other backends and returns no calibrated probabilities. The 11-turn pilot
archived in `services/genie/eval/judges/runs/pilot-20261011-t16i2/` was measured
on the old chat route; this probe is the one live record on the new path.

It runs through the pilot's own call path — `linker_judges.registry.JUDGES["jev"]`
through `linker_judges.judges.call` — on one rebuilt panel item: the archived SSE
stream parsed to the rendered answer, the turn log's ability calls replayed
read-only against the instance (`pilot.py`'s own helpers, imported not copied).
The record written beside it keeps the wire response (the model the endpoint
reports, the raw answers with their probabilities, `usage` including `cost`) and
the parsed verdict, so the acceptance note can quote numbers, not paraphrase.

Run from `services/genie/eval/judges` (its uv project owns the imports):

    uv run --locked python ../../../../docs/acceptance/2026-10-11/16i/probe-systemone-jev.py

Defaults rebuild `panel-r10` from the deepseek-flash panel (turn 183) against the
t16i instance on 127.0.0.1:8948 and write `systemone-probe-20261011.json` here.
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

import linker_judges.judges as judges_mod  # noqa: E402
import pilot  # noqa: E402  (the item builder the pilot runs, imported not copied)
from linker_judges.judges import call  # noqa: E402
from linker_judges.registry import JUDGES  # noqa: E402
from linker_judges.turns import turns_questions, turns_state  # noqa: E402


def build_item(panel: Path, db_path: Path, wp: str, name: str) -> dict[str, Any]:
    """One panel row as the pilot builds it: rendered answer + replayed reference."""
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
    reference = {"calls": pilot.replay(wp, calls)}
    swap = pilot.SWAPS.get(name)
    page = pilot.PAGE_PRODUCT.get(name)
    recommended = [pid for pid in cards if pid != page]
    roles = f"This page's product: {page}.\n" if page is not None else ""

    def offer_line(ids: list[int]) -> str:
        return roles + f"Recommended products: {', '.join(str(pid) for pid in ids)}."

    return {
        "question": pilot.QUESTIONS[name],
        "answer": answer_text + "\n\n" + offer_line(recommended),
        "reference": reference,
        "cards": cards,
        "answer_a": answer_text + "\n\n" + offer_line(recommended),
        "answer_b": answer_text
        + "\n\n"
        + (
            offer_line([swap[2] if pid == swap[1] else pid for pid in recommended])
            if swap
            else offer_line(recommended)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One live jev/systemone probe.")
    parser.add_argument(
        "--panel",
        type=Path,
        default=REPO / "docs" / "acceptance" / "2026-10-11" / "13" / "deepseek-flash",
        help="archive directory with panel-<row>.json streams",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".cache" / "linker-genie" / "turns.sqlite",
        help="the turn log (tool_calls per turn_id)",
    )
    parser.add_argument(
        "--wp", default="http://127.0.0.1:8948", help="instance to replay against"
    )
    parser.add_argument("--item", default="panel-r10", help="panel row to probe")
    parser.add_argument(
        "--out", type=Path, default=HERE / "systemone-probe-20261011.json"
    )
    args = parser.parse_args(argv)

    item = build_item(args.panel, args.db, args.wp, args.item)
    judge = JUDGES["jev"]
    # The pilot asks better_pick only where the row has a constructed variant.
    questions = turns_questions(pilot.SWAPS.get(args.item) is not None)

    # The call path is `call` itself; this tap only keeps the wire response for
    # the record (the verdict has the parsed view, not the raw body).
    raw: dict[str, Any] = {}
    real_post = judges_mod.post_json

    def tapping_post(*post_args: Any, **post_kwargs: Any) -> Any:
        response = real_post(*post_args, **post_kwargs)
        raw.update(
            url=post_args[0],
            seconds=response.seconds,
            attempts=response.attempts,
            started_at=response.started_at,
            body=response.body,
        )
        return response

    judges_mod.post_json = tapping_post
    try:
        verdict = call(judge, turns_state(item), questions)
    finally:
        judges_mod.post_json = real_post

    record: dict[str, Any] = {
        "probe": "one live item through the eval/judges call path (registry Jev)",
        "date": "2026-10-11",
        "run_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "item": args.item,
        "judge": {
            "name": judge.name,
            "kind": judge.kind,
            "model_requested": judge.model,
            "endpoint": judge.endpoint,
            "url": raw.get("url"),
        },
        "response": {
            "model": raw.get("body", {}).get("model"),
            "answers": raw.get("body", {}).get("answers"),
            "usage": raw.get("body", {}).get("usage"),
        },
        "verdict": {
            "answers": {
                name: {
                    "label": answer.label,
                    "confidence": answer.confidence,
                    "probabilities": answer.probabilities,
                }
                for name, answer in verdict.answers.items()
            },
            "model_reported": verdict.model_reported,
            "input_tokens": verdict.input_tokens,
            "output_tokens": verdict.output_tokens,
            "cost_usd": verdict.cost_usd,
            "seconds": verdict.seconds,
            "attempts": verdict.attempts,
            "started_at": verdict.started_at,
            "reason": verdict.reason,
            "error": verdict.error,
        },
    }
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    print(f"{args.out}: {verdict.model_reported} cost ${verdict.cost_usd}")
    for name, answer in verdict.answers.items():
        print(f"  {name}: {answer.label} conf={answer.confidence}")
    return 0 if verdict.error is None else 1


if __name__ == "__main__":
    sys.exit(main())
