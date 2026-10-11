"""Judge the turns a regression run just took, one item per question.

`pilot.py` scores the archived #13 behaviour panel; this driver scores any
turns, so #16's end-to-end suite (`tests/e2e`) can put the same Jev -> DeepSeek
cascade behind every question it asks the live service:

    uv run --project . python score.py --items items.jsonl --out run/ \
        --db ~/.cache/linker-genie/turns.sqlite --wp http://127.0.0.1:8945

Each input line is one judged item:

    {"id": "R1-en", "question": "…", "answer": "…", "cards": [4107],
     "turn_id": 202, "swap": {"from": 4107, "to": 6507}}

`turn_id` names the service's logged turn; the reference is rebuilt from that
turn's own ability calls, replayed read-only against `--wp` (the same replay
the pilot uses), so the judge sees what the turn actually read. `swap` is
optional: when present the item also carries the wrong-pick variant
`answer_b`, so `better_pick` has a real choice and the real answer must win.

Output in `--out`: `items.jsonl` (the resolved items), `jev.jsonl` and
`deepseek.jsonl` (one record per call), `cascade.jsonl` (the final labels and
where each came from) and `summary.json` (per item, plus the tallies).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from linker_judges.cascade import run_cascade
from linker_judges.registry import JUDGES
from linker_judges.turns import turns_questions
from pilot import (
    record,
    write_jsonl,
)  # same directory: the pilot's own record and writers


def read_items(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def tool_calls(db_path: Path, turn_id: int) -> list[dict[str, Any]]:
    """The ability calls of one logged turn, empty when the turn is not logged.

    A turn the service refused or crashed on leaves no row; the item then has
    an empty reference, which the judge reads as "the answer must state no
    product facts" rather than as a pass by default.
    """
    database = sqlite3.connect(db_path)
    try:
        row = database.execute(
            "SELECT tool_calls FROM turns WHERE id = ?", (turn_id,)
        ).fetchone()
    finally:
        database.close()
    return json.loads(row[0]) if row else []


def replay(
    base_url: str, calls: list[dict[str, Any]], timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Re-run a turn's ability calls read-only and return what they answered.

    The pilot's `replay()` raises on a refusal; this one keeps the refusal as
    the result, because a turn's own tool calls include the ones that were
    *meant* to be refused — `linker/inquiry-status` answers 401 to a guest, and
    the service turns that into the `login_required` fact the model read. A
    judge asked to compare the answer with its reference must see what the
    model saw, not an evaluator crash.
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
        try:
            with urllib.request.urlopen(url, timeout=timeout) as reply:
                body = json.loads(reply.read())
            result = body.get("result", body) if isinstance(body, dict) else body
        except urllib.error.HTTPError as error:
            if error.code == 401:
                result = {"error": "login_required"}
            else:
                result = {"error": f"http_{error.code}"}
        replayed.append(
            {"name": one["name"], "arguments": one.get("arguments"), "result": result}
        )
    return replayed


def build_item(row: dict[str, Any], calls: list[dict[str, Any]]) -> dict[str, Any]:
    """The judge's item for one input row (see `turns.turns_state`)."""
    answer = str(row["answer"])
    cards = [int(pid) for pid in row.get("cards") or []]
    if not calls:
        # No reference and no calls: the judge must be told the answer is not
        # backed by anything, not handed an empty state it would call fine.
        reference: Any = {"calls": []}
    else:
        reference = {"calls": calls}
    item: dict[str, Any] = {
        "question": str(row["question"]),
        "answer": answer,
        "reference": reference,
        "cards": cards,
    }
    swap = row.get("swap")
    if swap and cards:
        variant = [
            int(swap["to"]) if int(pid) == int(swap["from"]) else int(pid)
            for pid in cards
        ]
        offered = ", ".join(str(pid) for pid in cards)
        picked = ", ".join(str(pid) for pid in variant)
        item["answer_a"] = f"{answer}\n\nProducts offered: {offered}"
        item["answer_b"] = f"{answer}\n\nProducts offered: {picked}"
    return item


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cascade-judge regression turns")
    parser.add_argument("--items", type=Path, required=True, help="items jsonl")
    parser.add_argument("--out", type=Path, required=True, help="run directory")
    parser.add_argument("--db", type=Path, required=True, help="the turn log sqlite")
    parser.add_argument("--wp", required=True, help="the instance base URL for replay")
    args = parser.parse_args(argv)

    first, fallback = JUDGES["jev"], JUDGES["deepseek"]
    args.out.mkdir(parents=True, exist_ok=True)

    resolved: list[dict[str, Any]] = []
    jev_rows: list[dict[str, Any]] = []
    fallback_rows: list[dict[str, Any]] = []
    cascade_rows: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for row in read_items(args.items):
        identifier = str(row["id"])
        calls = replay(args.wp, tool_calls(args.db, int(row["turn_id"])))
        item = build_item(row, calls)
        questions = turns_questions("answer_b" in item)
        resolved.append({"id": identifier, **item})

        cascade = run_cascade(item, first, fallback, questions)
        jev_rows.append(record(first.name, identifier, 1, cascade.first))
        if cascade.fallback is not None:
            fallback_rows.append(record(fallback.name, identifier, 1, cascade.fallback))
        cascade_rows.append(
            {
                "item": identifier,
                "labels": cascade.labels,
                "sources": cascade.sources,
                "escalated": cascade.escalated,
            }
        )
        summary.append(
            {
                "item": identifier,
                "turn_id": row["turn_id"],
                "question": row["question"],
                "labels": cascade.labels,
                "sources": cascade.sources,
                "jev": {
                    name: {
                        "label": cascade.first.answers[name].label,
                        "confidence": cascade.first.answers[name].confidence,
                    }
                    for name in cascade.first.answers
                },
                "reference_calls": [one.get("name") for one in calls],
                "judged_at": time.time(),
            }
        )
        print(f"{identifier}: {cascade.labels} ({cascade.sources})", flush=True)

    write_jsonl(args.out / "items.jsonl", resolved)
    write_jsonl(args.out / "jev.jsonl", jev_rows)
    write_jsonl(args.out / "deepseek.jsonl", fallback_rows)
    write_jsonl(args.out / "cascade.jsonl", cascade_rows)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1)
    )
    print(f"{len(summary)} items judged -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
