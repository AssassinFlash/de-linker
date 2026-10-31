"""The service's turn log: the quality worker's queue.

The worker reads it without changing any turn. The API owns retention, so
cleanup still runs when the optional judge cannot start (retention.py).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from linker_genie.log import ADDED_COLUMNS
from linker_genie.tools import READ_ATTACHMENT

# Seconds a read waits for the service's write lock. The service commits each
# turn in one short INSERT, so a reader waits milliseconds; five seconds only
# bounds a stuck writer, which the next cycle then meets again.
BUSY_TIMEOUT = 5.0

# The columns the worker reads, in `LoggedTurn` order.
COLUMNS = (
    "id",
    "conversation_id",
    "created_at",
    "locale",
    "fallback",
    "tool_calls",
    "output",
    "question",
    "page",
    "approved",
)
# The columns the service added after its first release: a log it has not
# upgraded yet lacks them, and the worker reads them as NULL there (a turn with
# no question is skipped as such; one with no account flag is not approved).
LATER_COLUMNS = frozenset(name for name, _ in ADDED_COLUMNS)


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
    """Reads the log the service writes.

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
            self._with_readings(_turn(row))
            for row in self._query(
                "SELECT {columns} FROM turns WHERE id > ? ORDER BY id LIMIT ?",
                (turn_id, limit),
            )
        ]

    def by_ids(self, ids: list[int]) -> list[LoggedTurn]:
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        return [
            self._with_readings(_turn(row))
            for row in self._query(
                "SELECT {columns} FROM turns WHERE id IN (" + marks + ") ORDER BY id",
                tuple(ids),
            )
        ]

    def _with_readings(self, turn: LoggedTurn) -> LoggedTurn:
        """The turn with each earlier file reading it names filled in.

        The service logs a reading once, with the turn that read it, and later turns
        name it by id (`attachments.recorded`, #236). The judges read what the answer
        could cite, so the reading is taken from the newest earlier turn of the same
        conversation that logged it in full; a reading purged with its conversation
        (`log.TurnLog.forget`) stays as it is.
        """
        wanted = {
            str(call["result"]["id"])
            for call in turn.tool_calls
            if call.get("name") == READ_ATTACHMENT
            and isinstance(call.get("result"), dict)
            and call["result"].get("earlier")
        }
        if not wanted:
            return turn
        found: dict[str, dict[str, Any]] = {}
        for row in self._query(
            "SELECT id, tool_calls FROM turns WHERE conversation_id = ? AND id < ? "
            "ORDER BY id DESC",
            (turn.conversation_id, turn.id),
        ):
            calls = json.loads(row["tool_calls"]) if row["tool_calls"] else []
            for call in calls if isinstance(calls, list) else []:
                result = call.get("result") if isinstance(call, dict) else None
                if (
                    call.get("name") == READ_ATTACHMENT
                    and isinstance(result, dict)
                    and str(result.get("id")) in wanted
                    and not result.get("earlier")
                ):
                    found.setdefault(str(result["id"]), result)
        calls = [
            {**call, "result": found[str(call["result"]["id"])]}
            if call.get("name") == READ_ATTACHMENT
            and isinstance(call.get("result"), dict)
            and call["result"].get("earlier")
            and str(call["result"]["id"]) in found
            else call
            for call in turn.tool_calls
        ]
        return replace(turn, tool_calls=calls)

    def _query(self, sql: str, args: tuple[Any, ...]) -> list[sqlite3.Row]:
        """Run `sql`, its `{columns}` filled with `select_list` for this log."""
        if not self.path.exists():
            return []
        database = sqlite3.connect(
            f"file:{self.path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT
        )
        database.row_factory = sqlite3.Row
        try:
            columns = select_list(_columns(database))
            return list(database.execute(sql.format(columns=columns), args).fetchall())
        except sqlite3.OperationalError as error:
            if "no such table" in str(error):
                return []
            raise
        finally:
            database.close()


def select_list(present: set[str]) -> str:
    """The SELECT list of `COLUMNS` for a log that has the columns `present`."""
    return ", ".join(
        column
        if column in present or column not in LATER_COLUMNS
        else f"NULL AS {column}"
        for column in COLUMNS
    )


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
