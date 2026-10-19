"""Join a battery turn with the service's own understanding log.

The turn log (services/genie log.py) records what code did before the model:
lexicon matches, Jev's answers, the route and its calls. Defect attribution
reads that row.

Join on (conversation_id, turn_index). run_battery writes turn_index on every
case (0 for the one turn that case posts). A stored row with no turn_index
joins index 0 only when that conversation has exactly one turn. More than one
turn and a missing index is a mismatch: it does not silently join turn 0.
The SSE `turn_id` is only a fallback: with `--workers 3`, K3's stream carried
K1's turn_id (117) while K3's own log row is 116. A logged question or answer
that is not the case's is a mismatch, and the process exits 1 when any case
has one, so a bad join cannot pass silently.

Usage: python3 attribution.py [turns.sqlite] < cases.jsonl > attribution.json
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from run_battery import answer_text

COLUMNS = (
    "id, conversation_id, question, understanding, tool_calls, output, "
    "failures, fallback, provider, model"
)


def load_turns(database: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    found = [dict(row) for row in connection.execute(f"SELECT {COLUMNS} FROM turns")]
    connection.close()
    return found


def index_turns(
    rows: list[dict[str, Any]],
) -> tuple[dict[int, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_id: dict[int, dict[str, Any]] = {}
    by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_id[int(row["id"])] = row
        by_conversation[str(row["conversation_id"])].append(row)
    for group in by_conversation.values():
        group.sort(key=lambda item: int(item["id"]))
    return by_id, by_conversation


def logged_answer(row: dict[str, Any]) -> str:
    raw = row.get("output") or ""
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        return ""
    return answer_text(blocks).strip()


def _json_field(raw: Any, fallback: Any) -> Any:
    """Parse a log column. A bad string is the fallback, not a crash."""
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _record(case: dict[str, Any], logged: dict[str, Any] | None) -> dict[str, Any]:
    if logged is None:
        meta = case.get("meta") or {}
        return {
            "case": case["case"],
            "turn_id": meta.get("turn_id"),
            "logged": None,
        }
    understanding = _json_field(logged.get("understanding"), {})
    if not isinstance(understanding, dict):
        understanding = {}
    calls = understanding.get("calls") or []
    if not isinstance(calls, list):
        calls = []
    tool_calls = _json_field(logged.get("tool_calls"), [])
    if not isinstance(tool_calls, list):
        tool_calls = []
    failures = _json_field(logged.get("failures"), [])
    if not isinstance(failures, list):
        failures = []
    return {
        "case": case["case"],
        "turn_id": int(logged["id"]),
        "conversation_id": logged["conversation_id"],
        "question": logged["question"],
        "matches": understanding.get("matches"),
        "jev": {
            key: value for key, value in understanding.items() if key.startswith("jev")
        },
        "route": understanding.get("route"),
        "reasons": understanding.get("reasons"),
        "calls": [call.get("name") for call in calls if isinstance(call, dict)],
        "tool_calls": tool_calls,
        "fallback": bool(logged["fallback"]),
        "failures": failures,
        "provider": logged["provider"],
        "model": logged["model"],
    }


def resolve(
    case: dict[str, Any],
    by_id: dict[int, dict[str, Any]],
    by_conversation: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """The log row for one case, plus mismatch reasons when the join is wrong."""
    request = (case.get("request") or "").strip()
    meta = case.get("meta") or {}
    sse_turn = meta.get("turn_id")
    case_answer = answer_text(case.get("blocks") or []).strip()
    reasons: list[str] = []
    logged: dict[str, Any] | None = None
    joined_by = ""

    conversation_id = case.get("conversation_id")
    if isinstance(conversation_id, str) and conversation_id in by_conversation:
        turns = by_conversation[conversation_id]
        raw_index = case.get("turn_index")
        if raw_index is None:
            if len(turns) == 1:
                logged = turns[0]
                joined_by = "conversation_id"
            else:
                reasons.append(
                    f"turn_index missing for {conversation_id} ({len(turns)} turns)"
                )
        else:
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                index = -1
            if 0 <= index < len(turns):
                logged = turns[index]
                joined_by = "conversation_id"
            else:
                reasons.append(f"no turn index {index} in {conversation_id}")

    if logged is None and isinstance(sse_turn, int):
        logged = by_id.get(sse_turn)
        joined_by = "turn_id"
        if logged is None:
            reasons.append(f"sse turn_id {sse_turn} is not in the log")

    if logged is not None and case_answer:
        got = logged_answer(logged)
        if got and got != case_answer:
            same = [
                row
                for row in by_id.values()
                if (row.get("question") or "").strip() == request
                and logged_answer(row) == case_answer
            ]
            if len(same) == 1:
                reasons.append(
                    f"sse turn_id {sse_turn} is {logged['conversation_id']} "
                    f"turn {logged['id']}; the answer is turn {same[0]['id']}"
                )
                logged = same[0]
                joined_by = "question+answer"
            else:
                reasons.append("logged answer does not match the case answer")

    if logged is not None and request:
        logged_question = (logged.get("question") or "").strip()
        if logged_question and logged_question != request:
            reasons.append("logged question does not match the request")

    record = _record(case, logged)
    record["joined_by"] = joined_by or None
    record["sse_turn_id"] = sse_turn
    record["mismatch"] = bool(reasons)
    record["mismatch_reasons"] = reasons
    return record


def attribute(
    cases: list[dict[str, Any]],
    by_id: dict[int, dict[str, Any]],
    by_conversation: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Join every case. Two cases that land on one log row are both mismatches."""
    resolved = [resolve(case, by_id, by_conversation) for case in cases]
    owners: dict[int, list[str]] = defaultdict(list)
    for record in resolved:
        turn_id = record.get("turn_id")
        # A found row sets joined_by. A miss leaves it empty, so two cases
        # that never found a log row are not treated as one shared turn.
        if isinstance(turn_id, int) and record.get("joined_by"):
            owners[turn_id].append(str(record["case"]))
    for record in resolved:
        turn_id = record.get("turn_id")
        if isinstance(turn_id, int) and len(owners[turn_id]) > 1:
            others = ", ".join(owners[turn_id])
            record["mismatch"] = True
            record["mismatch_reasons"].append(f"turn {turn_id} also joined to {others}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    database = Path(
        args[0] if args else "~/de-linker-local/c330/genie/turns.sqlite"
    ).expanduser()
    by_id, by_conversation = index_turns(load_turns(database))
    cases: list[dict[str, Any]] = []
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            print("attribution: a case line is not JSON", file=sys.stderr)
            return 1
        if isinstance(parsed, dict):
            cases.append(parsed)
    # The battery writes "case"; a hand file may use the same key.
    for case in cases:
        case.setdefault("case", case.get("id"))
    resolved = attribute(cases, by_id, by_conversation)
    mismatches = 0
    for record in resolved:
        if record["mismatch"]:
            mismatches += 1
        print(json.dumps(record, ensure_ascii=False))
    if mismatches:
        print(f"{mismatches} attribution mismatch(es)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
