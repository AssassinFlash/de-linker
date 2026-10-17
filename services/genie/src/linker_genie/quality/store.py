"""The worker's own SQLite: where the queue stands and what each turn got.

The turn log is the queue; this file holds the worker's position in it, every
verdict, and whether WordPress has it yet. A verdict WordPress has not
acknowledged stays unpushed and goes again on the next cycle, so a site that
was unreachable for an hour loses nothing.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

Status = Literal["judged", "failed", "skipped"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS judgments (
    turn_id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    record TEXT NOT NULL,
    updated_at REAL NOT NULL,
    pushed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cursor (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_turn INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def cursor(self) -> int | None:
        """The last turn id taken from the log; None before the first start."""
        row = self._db.execute("SELECT last_turn FROM cursor WHERE id = 1").fetchone()
        return int(row[0]) if row else None

    def set_cursor(self, turn_id: int) -> None:
        self._db.execute(
            "INSERT INTO cursor (id, last_turn) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_turn = excluded.last_turn",
            (turn_id,),
        )
        self._db.commit()

    def attempts(self, turn_id: int) -> int:
        row = self._db.execute(
            "SELECT attempts FROM judgments WHERE turn_id = ?", (turn_id,)
        ).fetchone()
        return int(row[0]) if row else 0

    def save(
        self,
        turn_id: int,
        conversation_id: str,
        status: Status,
        attempts: int,
        record: dict[str, Any],
        now: float,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO judgments
                (turn_id, conversation_id, status, attempts, record, updated_at, pushed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(turn_id) DO UPDATE SET
                status = excluded.status, attempts = excluded.attempts,
                record = excluded.record, updated_at = excluded.updated_at,
                pushed = 0
            """,
            (
                turn_id,
                conversation_id,
                status,
                attempts,
                json.dumps(record, ensure_ascii=False),
                now,
            ),
        )
        self._db.commit()

    def retryable(self, max_attempts: int, before: float) -> list[int]:
        """Failed turns with attempts left whose last try is older than `before`."""
        return [
            int(row[0])
            for row in self._db.execute(
                "SELECT turn_id FROM judgments WHERE status = 'failed' "
                "AND attempts < ? AND updated_at <= ? ORDER BY turn_id",
                (max_attempts, before),
            )
        ]

    def unpushed(self, limit: int) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self._db.execute(
                "SELECT record FROM judgments WHERE pushed = 0 ORDER BY turn_id LIMIT ?",
                (limit,),
            )
        ]

    def mark_pushed(self, turn_ids: list[int]) -> None:
        self._db.executemany(
            "UPDATE judgments SET pushed = 1 WHERE turn_id = ?",
            [(turn_id,) for turn_id in turn_ids],
        )
        self._db.commit()

    def last_failure(self) -> tuple[str, float] | None:
        """The newest error among turns that are still `failed`, and when it
        happened; None once every failed turn has been judged after all.

        Read from the store, not kept in memory, so a restarted worker still
        reports a failure that is not resolved."""
        row = self._db.execute(
            "SELECT record, updated_at FROM judgments WHERE status = 'failed' "
            "ORDER BY updated_at DESC, turn_id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return str(json.loads(row[0]).get("error") or ""), float(row[1])

    def counts(self, max_attempts: int) -> dict[str, int]:
        """Failed turns still being retried, and those whose retries ran out."""
        retrying, exhausted = self._db.execute(
            "SELECT "
            "COALESCE(SUM(status = 'failed' AND attempts < ?), 0), "
            "COALESCE(SUM(status = 'failed' AND attempts >= ?), 0) "
            "FROM judgments",
            (max_attempts, max_attempts),
        ).fetchone()
        return {"retrying": int(retrying), "gave_up": int(exhausted)}
