"""Join the battery's turns with the service's own understanding log.

The turn log (services/genie log.py) records what code did before the model:
lexicon matches, Jev's answers, the route and its calls. That is the evidence
the defect list attributes layers from (deterministic match / Jev routing /
tools / retrieval / prompt / hydration / i18n / infrastructure).

Usage: python3 attribution.py [turns.sqlite] < cases.jsonl > attribution.json
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def rows(database: Path) -> dict[int, dict]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    found: dict[int, dict] = {}
    for row in connection.execute(
        "SELECT id, question, understanding, tool_calls, output, failures, "
        "fallback, provider, model FROM turns"
    ):
        found[row["id"]] = dict(row)
    connection.close()
    return found


def main() -> int:
    database = Path(
        sys.argv[1] if len(sys.argv) > 1
        else "~/de-linker-local/c330/genie/turns.sqlite"
    ).expanduser()
    by_id = rows(database)
    for line in sys.stdin:
        case = json.loads(line)
        meta = case.get("meta") or {}
        turn_id = meta.get("turn_id")
        logged = by_id.get(turn_id)
        if logged is None:
            print(json.dumps({"case": case["case"], "turn_id": turn_id,
                              "logged": None}))
            continue
        understanding = json.loads(logged["understanding"] or "{}")
        print(json.dumps({
            "case": case["case"],
            "turn_id": turn_id,
            "question": logged["question"],
            "matches": understanding.get("matches"),
            "jev": {k: v for k, v in understanding.items()
                    if k.startswith("jev")},
            "route": understanding.get("route"),
            "reasons": understanding.get("reasons"),
            "calls": [c.get("name") for c in understanding.get("calls", [])],
            "tool_calls": json.loads(logged["tool_calls"] or "[]"),
            "fallback": bool(logged["fallback"]),
            "failures": json.loads(logged["failures"] or "[]"),
            "provider": logged["provider"],
            "model": logged["model"],
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
