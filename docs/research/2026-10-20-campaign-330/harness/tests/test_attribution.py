"""Join on conversation id, and refuse a turn_id collision like K1/K3."""

from __future__ import annotations

import io
import json
import sqlite3
from typing import Any

import attribution


def _row(
    turn_id: int,
    conversation_id: str,
    question: str,
    answer: str,
) -> dict[str, Any]:
    return {
        "id": turn_id,
        "conversation_id": conversation_id,
        "question": question,
        "understanding": json.dumps({"route": "parts", "matches": [], "calls": []}),
        "tool_calls": "[]",
        "output": json.dumps({"blocks": [{"type": "text", "text": answer}]}),
        "failures": "[]",
        "fallback": 0,
        "provider": "test",
        "model": "test",
    }


def _case(
    case_id: str,
    request: str,
    answer: str,
    turn_id: int,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "case": case_id,
        "request": request,
        "blocks": [{"type": "text", "text": answer}],
        "meta": {"turn_id": turn_id},
    }
    if conversation_id is not None:
        item["conversation_id"] = conversation_id
    return item


def test_conversation_id_wins_over_a_wrong_sse_turn() -> None:
    rows = [
        _row(10, "c330-A", "question a", "answer a"),
        _row(11, "c330-B", "question b", "answer b"),
    ]
    by_id, by_conversation = attribution.index_turns(rows)
    resolved = attribution.attribute(
        [_case("A", "question a", "answer a", 11, "c330-A")],
        by_id,
        by_conversation,
    )
    assert resolved[0]["turn_id"] == 10
    assert resolved[0]["joined_by"] == "conversation_id"
    assert resolved[0]["mismatch"] is False


def test_k3_answer_text_rejoins_when_sse_turn_id_collides() -> None:
    """K1 and K3 asked the same question. Both streams said turn 117."""
    question = "Here is my parts list."
    rows = [
        _row(116, "c330-K3-EN-1", question, "three duplicate rows"),
        _row(117, "c330-K1-EN-1", question, "a normal list"),
    ]
    by_id, by_conversation = attribution.index_turns(rows)
    resolved = attribution.attribute(
        [
            _case("K3-EN", question, "three duplicate rows", 117),
            _case("K1-EN", question, "a normal list", 117),
        ],
        by_id,
        by_conversation,
    )
    by_case = {item["case"]: item for item in resolved}
    assert by_case["K3-EN"]["turn_id"] == 116
    assert by_case["K3-EN"]["joined_by"] == "question+answer"
    assert by_case["K3-EN"]["mismatch"] is True
    assert "turn 116" in " ".join(by_case["K3-EN"]["mismatch_reasons"])
    assert by_case["K1-EN"]["turn_id"] == 117
    assert by_case["K1-EN"]["mismatch"] is False


def test_two_cases_on_one_turn_are_both_mismatches() -> None:
    rows = [_row(5, "c", "q", "same")]
    by_id, by_conversation = attribution.index_turns(rows)
    resolved = attribution.attribute(
        [
            _case("A", "q", "same", 5),
            _case("B", "q", "same", 5),
        ],
        by_id,
        by_conversation,
    )
    assert all(item["mismatch"] for item in resolved)
    assert all("also joined" in " ".join(item["mismatch_reasons"]) for item in resolved)


def test_question_mismatch() -> None:
    rows = [_row(5, "c330-A", "logged question", "answer")]
    by_id, by_conversation = attribution.index_turns(rows)
    resolved = attribution.attribute(
        [_case("A", "case request", "answer", 9, "c330-A")],
        by_id,
        by_conversation,
    )
    assert resolved[0]["mismatch"] is True
    assert (
        "logged question does not match the request" in resolved[0]["mismatch_reasons"]
    )


def test_main_exits_nonzero_on_mismatch(tmp_path: Any, monkeypatch: Any) -> None:
    database = tmp_path / "turns.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE turns (id INTEGER, conversation_id TEXT, question TEXT, "
        "understanding TEXT, tool_calls TEXT, output TEXT, failures TEXT, "
        "fallback INTEGER, provider TEXT, model TEXT)"
    )
    row = _row(5, "c", "logged question", "answer")
    connection.execute(
        "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            row["id"],
            row["conversation_id"],
            row["question"],
            row["understanding"],
            row["tool_calls"],
            row["output"],
            row["failures"],
            row["fallback"],
            row["provider"],
            row["model"],
        ),
    )
    connection.commit()
    connection.close()
    payload = json.dumps(_case("A", "case request", "answer", 5, "c")) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert attribution.main([str(database)]) == 1
