"""Read the judged production turns from the VPS, read-only.

Runs on the VPS through ssh's stdin (it needs only the standard library):

    ssh linker-services python3 - < docs/research/2026-10-18-judge-remit/fetch_turns.py > <scratch>/turns.json

Both stores are opened `mode=ro`. The output holds the turns' questions and
answers, so it goes to a scratch directory and is never committed; the
committed summaries carry turn ids, labels and confidences only.
"""

import json
import sqlite3

# The worker's default stores on the VPS (docs/specs/33-judge-bakeoff.md, 部署).
BASE = "/root/.cache/linker-genie"


def main() -> None:
    judgments = sqlite3.connect(f"file:{BASE}/judgments.sqlite?mode=ro", uri=True)
    turns = sqlite3.connect(f"file:{BASE}/turns.sqlite?mode=ro", uri=True)
    turns.row_factory = sqlite3.Row
    records = {
        turn_id: json.loads(record)
        for turn_id, record in judgments.execute(
            "SELECT turn_id, record FROM judgments ORDER BY turn_id"
        )
    }
    marks = ",".join("?" for _ in records)
    rows = []
    for row in turns.execute(
        "SELECT id, conversation_id, created_at, locale, fallback, tool_calls,"
        f" output, question, page FROM turns WHERE id IN ({marks}) ORDER BY id",
        tuple(records),
    ):
        turn = dict(row)
        turn["judgment"] = records[turn["id"]]
        rows.append(turn)
    print(json.dumps(rows, ensure_ascii=False))


main()
