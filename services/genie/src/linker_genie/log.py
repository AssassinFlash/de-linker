"""SQLite log of each Genie turn: tools, grounding, model metadata, votes.

The log is also the quality check's queue (docs/specs/33-judge-bakeoff.md,
"部署目标"): the judge worker reads it after the fact and never writes it. The
worker judges what the customer asked (`question`), on which page (`page`),
against what the turn's abilities returned (`tool_calls[*].result`), so those
are logged with the turn. The understanding layer's record (product words,
Jev's reading, the route, its failures) is logged with it too (#233), and
whether the customer's account is an approved one (`approved`, #258): the
judges' remit lets an approved account see prices and nobody else.
"""

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
    vote INTEGER,
    question TEXT,
    page TEXT,
    understanding TEXT,
    approved INTEGER,
    contact TEXT
);
"""

# Columns added after the first release: a log the service already wrote keeps
# its rows and gains the columns (NULL for the turns logged before them).
ADDED_COLUMNS = (
    ("question", "TEXT"),
    ("page", "TEXT"),
    ("understanding", "TEXT"),
    ("approved", "INTEGER"),
    # Why the turn offered the team's contact (contact.py, #243), NULL when it did not.
    ("contact", "TEXT"),
)


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
        present = {row[1] for row in self._db.execute("PRAGMA table_info(turns)")}
        for name, kind in ADDED_COLUMNS:
            if name not in present:
                self._db.execute(f"ALTER TABLE turns ADD COLUMN {name} {kind}")
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
        question: str = "",
        page: dict[str, Any] | None = None,
        understanding: dict[str, Any] | None = None,
        approved: bool = False,
        contact: str | None = None,
    ) -> int:
        cursor = self._db.execute(
            """
            INSERT INTO turns (
                conversation_id, locale, grounded, failures, fallback,
                provider, model, tool_calls, output, question, page,
                understanding, approved, contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                question,
                json.dumps(page or {}),
                json.dumps(understanding or {}, ensure_ascii=False),
                int(approved),
                contact,
            ),
        )
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def offers(self, conversation_id: str, limit: int) -> list[bool]:
        """Whether each of the conversation's last `limit` turns carried the contact
        offer, newest first (contact.decide: never twice in a row, once a question)."""
        rows = self._db.execute(
            "SELECT contact FROM turns WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, max(0, limit)),
        ).fetchall()
        return [row[0] is not None for row in rows]

    def vote(self, turn_id: int, value: int) -> bool:
        """Record a vote; False when the turn id is unknown."""
        cursor = self._db.execute(
            "UPDATE turns SET vote = ? WHERE id = ?", (value, turn_id)
        )
        self._db.commit()
        return cursor.rowcount > 0
