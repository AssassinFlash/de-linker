"""SQLite log of each Genie turn: tools, grounding, model metadata, votes."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    locale TEXT NOT NULL,
    grounded INTEGER NOT NULL,
    failures TEXT NOT NULL,
    fallback INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tool_calls TEXT NOT NULL,
    output TEXT NOT NULL,
    vote INTEGER
);
"""


class TurnLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # The service's sync endpoints run in uvicorn's threadpool, so one
        # request can log from a different thread than the one that opened
        # the connection; SQLite must allow that (writes stay serialized by
        # the connection's own lock).
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def record(
        self,
        conversation_id: str,
        locale: str,
        grounded: bool,
        failures: tuple[str, ...],
        fallback: bool,
        provider: str,
        model: str,
        tool_calls: list[dict[str, Any]],
        output: dict[str, Any],
    ) -> int:
        cursor = self._db.execute(
            """
            INSERT INTO turns (
                conversation_id, locale, grounded, failures, fallback,
                provider, model, tool_calls, output
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                locale,
                int(grounded),
                json.dumps(list(failures)),
                int(fallback),
                provider,
                model,
                json.dumps(tool_calls),
                json.dumps(output),
            ),
        )
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def vote(self, turn_id: int, value: int) -> bool:
        """Record a vote; False when the turn id is unknown."""
        cursor = self._db.execute(
            "UPDATE turns SET vote = ? WHERE id = ?", (value, turn_id)
        )
        self._db.commit()
        return cursor.rowcount > 0
