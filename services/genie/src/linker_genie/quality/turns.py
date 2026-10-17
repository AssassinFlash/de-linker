"""The service's turn log: the quality worker's queue.

The worker reads it, and deletes from it only what is past retention
(`prune`); it never changes a turn.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Seconds a read waits for the service's write lock. The service commits each
# turn in one short INSERT, so a reader waits milliseconds; five seconds only
# bounds a stuck writer, which the next cycle then meets again.
BUSY_TIMEOUT = 5.0

COLUMNS = (
    "id, conversation_id, created_at, locale, fallback, tool_calls, output, "
    "question, page, approved"
)
# The columns the service added after its first release (log.ADDED_COLUMNS) that
# the worker reads: a log the service has not upgraded yet reads them as NULL.
LATER_COLUMNS = ("question", "page", "approved")


@dataclass(frozen=True)
class LoggedTurn:
    """One answered turn as the service logged it."""

    id: int
    conversation_id: str
    created_at: str
    """SQLite's `datetime('now')`: UTC, `YYYY-MM-DD HH:MM:SS`."""
    locale: str
    fallback: bool
    tool_calls: list[dict[str, Any]]
    output: dict[str, Any]
    question: str | None
    """None for a turn logged before the log carried questions."""
    page: dict[str, Any]
    approved: bool = False
    """Whether the customer's account was an approved one (`UserContext.partner`):
    the only account the remit lets see prices. False for a guest, a pending or
    a restricted account, and for a turn logged before the log carried it."""


class TurnSource:
    """Reads the log the service writes; deletes only expired turns.

    Each read opens its own read-only connection, so the worker holds no lock
    between cycles and a log the service has not created yet reads as empty.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def latest_id(self) -> int:
        rows = self._query("SELECT COALESCE(MAX(id), 0) AS id FROM turns", ())
        return int(rows[0]["id"]) if rows else 0

    def after(self, turn_id: int, limit: int) -> list[LoggedTurn]:
        """The turns logged after `turn_id`, oldest first."""
        return [
            _turn(row)
            for row in self._query(
                f"SELECT {COLUMNS} FROM turns WHERE id > ? ORDER BY id LIMIT ?",
                (turn_id, limit),
            )
        ]

    def by_ids(self, ids: list[int]) -> list[LoggedTurn]:
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        return [
            _turn(row)
            for row in self._query(
                f"SELECT {COLUMNS} FROM turns WHERE id IN ({marks}) ORDER BY id",
                tuple(ids),
            )
        ]

    def prune(self, before: str) -> int:
        """Delete the turns logged before `before` (`YYYY-MM-DD HH:MM:SS`,
        UTC, the log's own `created_at` form); return how many went."""
        if not self.path.exists():
            return 0
        database = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT)
        try:
            cursor = database.execute(
                "DELETE FROM turns WHERE created_at < ?", (before,)
            )
            database.commit()
            return cursor.rowcount
        except sqlite3.OperationalError as error:
            if "no such table" in str(error):
                return 0
            raise
        finally:
            database.close()

    def _query(self, sql: str, args: tuple[Any, ...]) -> list[sqlite3.Row]:
        if not self.path.exists():
            return []
        database = sqlite3.connect(
            f"file:{self.path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT
        )
        database.row_factory = sqlite3.Row
        try:
            present = _columns(database)
            for column in LATER_COLUMNS:
                if column not in present:
                    # A log the service has not upgraded yet (log.ADDED_COLUMNS):
                    # a turn with no question is skipped as such; one with no
                    # account flag reads as not approved.
                    sql = sql.replace(f", {column}", f", NULL AS {column}", 1)
            return list(database.execute(sql, args).fetchall())
        except sqlite3.OperationalError as error:
            if "no such table" in str(error):
                return []
            raise
        finally:
            database.close()


def _columns(database: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in database.execute("PRAGMA table_info(turns)")}


def _turn(row: sqlite3.Row) -> LoggedTurn:
    page = json.loads(row["page"]) if row["page"] else {}
    output = json.loads(row["output"]) if row["output"] else {}
    calls = json.loads(row["tool_calls"]) if row["tool_calls"] else []
    return LoggedTurn(
        id=int(row["id"]),
        conversation_id=str(row["conversation_id"]),
        created_at=str(row["created_at"]),
        locale=str(row["locale"]),
        fallback=bool(row["fallback"]),
        tool_calls=calls if isinstance(calls, list) else [],
        output=output if isinstance(output, dict) else {},
        question=row["question"],
        page=page if isinstance(page, dict) else {},
        approved=bool(row["approved"]),
    )
