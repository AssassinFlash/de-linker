"""The worker's own SQLite: where the queue stands and what each turn got.

The turn log is the queue; this file holds the worker's position in it, every
verdict, and whether WordPress has it yet. A verdict WordPress has not
acknowledged stays unpushed. Delivery retries have their own durable schedule;
an explicit permanent site rejection retains the verdict without claiming it
was pushed. Delivery metadata never extends the verdict's retention timestamp.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

Status = Literal["judged", "failed", "skipped"]

# Double the worker's existing 30-second poll; cap at its ten-minute heartbeat.
# This changes delivery pacing, never the existing model-attempt policy.
DELIVERY_DELAYS = (60.0, 120.0, 240.0, 480.0, 600.0)

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
CREATE TABLE IF NOT EXISTS delivery_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    failures INTEGER NOT NULL DEFAULT 0,
    next_attempt REAL NOT NULL DEFAULT 0,
    last_success REAL NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    error_at REAL NOT NULL DEFAULT 0
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.executescript(SCHEMA)
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(judgments)")}
        for name, definition in {
            "push_attempts": "INTEGER NOT NULL DEFAULT 0",
            "push_after": "REAL NOT NULL DEFAULT 0",
            "push_reason": "TEXT NOT NULL DEFAULT ''",
            "push_terminal": "INTEGER NOT NULL DEFAULT 0",
            "push_at": "REAL NOT NULL DEFAULT 0",
        }.items():
            if name not in columns:
                self._db.execute(
                    f"ALTER TABLE judgments ADD COLUMN {name} {definition}"
                )
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
                pushed = 0, push_attempts = 0, push_after = 0,
                push_reason = '', push_terminal = 0, push_at = 0
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

    def unpushed(self, limit: int, now: float = float("inf")) -> list[dict[str, Any]]:
        """Eligible delivery rows; fresh records precede older refused retries."""
        return [
            json.loads(row[0])
            for row in self._db.execute(
                "SELECT record FROM judgments WHERE pushed = 0 "
                "AND push_terminal = 0 AND push_after <= ? "
                "ORDER BY push_attempts, turn_id LIMIT ?",
                (now, limit),
            )
        ]

    def mark_pushed(self, turn_ids: list[int]) -> None:
        self._db.executemany(
            "UPDATE judgments SET pushed = 1, push_after = 0, push_reason = '', push_terminal = 0 WHERE turn_id = ?",
            [(turn_id,) for turn_id in turn_ids],
        )
        self._db.commit()

    def defer_delivery(
        self, reasons: dict[int, str], now: float, *, terminal: bool = False
    ) -> None:
        for turn_id, reason in reasons.items():
            row = self._db.execute(
                "SELECT push_attempts FROM judgments WHERE turn_id=? AND pushed=0",
                (turn_id,),
            ).fetchone()
            if row is None:
                continue
            attempt = int(row[0]) + 1
            due = (
                0.0
                if terminal
                else now + DELIVERY_DELAYS[min(attempt - 1, len(DELIVERY_DELAYS) - 1)]
            )
            self._db.execute(
                "UPDATE judgments SET push_attempts=?,push_after=?,push_reason=?,push_terminal=?,push_at=? WHERE turn_id=? AND pushed=0",
                (attempt, due, reason, int(terminal), now, turn_id),
            )
        self._db.commit()

    def transport(self) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT failures,next_attempt,last_success,error,error_at FROM delivery_state WHERE id=1"
        ).fetchone()
        return dict(
            zip(
                ("failures", "next_attempt", "last_success", "error", "error_at"),
                row or (0, 0.0, 0.0, "", 0.0),
                strict=True,
            )
        )

    def transport_failed(self, now: float, reason: str) -> None:
        previous = self.transport()
        failures = int(previous["failures"]) + 1
        due = now + DELIVERY_DELAYS[min(failures - 1, len(DELIVERY_DELAYS) - 1)]
        self._db.execute(
            "INSERT INTO delivery_state(id,failures,next_attempt,last_success,error,error_at) VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET failures=excluded.failures,next_attempt=excluded.next_attempt,error=excluded.error,error_at=excluded.error_at",
            (failures, due, previous["last_success"], reason, now),
        )
        self._db.commit()

    def transport_succeeded(self, now: float) -> None:
        self._db.execute(
            "INSERT INTO delivery_state(id,last_success) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET failures=0,next_attempt=0,last_success=excluded.last_success,error='',error_at=0",
            (now,),
        )
        self._db.commit()

    def delivery_status(self, now: float) -> dict[str, Any]:
        pending, deferred, rejected, due = self._db.execute(
            "SELECT COALESCE(SUM(pushed=0 AND push_terminal=0),0),COALESCE(SUM(pushed=0 AND push_terminal=0 AND push_after>?),0),COALESCE(SUM(pushed=0 AND push_terminal=1),0),MIN(CASE WHEN pushed=0 AND push_terminal=0 THEN push_after END) FROM judgments",
            (now,),
        ).fetchone()
        transport = self.transport()
        latest = self._db.execute(
            "SELECT push_reason,push_at FROM judgments WHERE pushed=0 AND push_reason!='' ORDER BY push_at DESC LIMIT 1"
        ).fetchone()
        error, error_at = latest or ("", 0.0)
        if transport["error"] and transport["error_at"] >= error_at:
            error, error_at = transport["error"], transport["error_at"]
        return {
            "delivery_pending": int(pending),
            "delivery_deferred": int(
                pending if transport["next_attempt"] > now else deferred
            ),
            "delivery_rejected": int(rejected),
            "delivery_retry_at": max(float(due or 0), float(transport["next_attempt"])),
            "delivery_error": error,
            "delivery_error_at": float(error_at),
        }

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
