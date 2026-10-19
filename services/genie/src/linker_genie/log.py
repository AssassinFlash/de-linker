"""SQLite log of each Genie turn: tools, grounding, model metadata, votes.

The log is also the quality check's queue (docs/specs/33-judge-bakeoff.md,
"部署目标"): the judge worker reads it after the fact and never writes it. The
worker judges what the customer asked (`question`), on which page (`page`),
against what the turn's abilities returned (`tool_calls[*].result`), so those
are logged with the turn. The understanding layer's record (product words,
Jev's reading, the route, its failures) is logged with it too (#233), and
whether the customer's account is an approved one (`approved`, #258): the
judges' remit lets an approved account see prices and nobody else. The turn's
passive phase timings are one JSON object per row (`timing`, #336, timing.py) —
the numbers the latency work reads (ops/turn_latency.py). A turn that never
answered has no row here (a row is written only after the answer exists);
`turn_starts` notes every begun turn and is closed when the row lands, so those
unfinished turns stay countable.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from linker_genie.tools import READ_ATTACHMENT

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
    contact TEXT,
    timing TEXT
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
    # The turn's passive phase timings (#336, timing.py): a JSON object of
    # phase→seconds, written when the row is recorded and completed with the
    # final totals when the turn's stream ends (set_timing).
    ("timing", "TEXT"),
)

# One row per turn that has begun, removed when its turn row lands
# (app.assistant_turn). A row left behind is a turn that never answered — a model
# hang, a restart, a killed process — which the `turns` table cannot show: it
# gets a row only after the answer exists, so the worst of the latency tail would
# silently vanish. ops/turn_latency.py counts the stale ones (#336).
STARTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS turn_starts (
    token INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    locale TEXT NOT NULL
);
"""


def _calls(raw: str | None) -> list[dict[str, Any]]:
    """The turn's logged calls; a malformed entry is left out, never raised."""
    calls = json.loads(raw) if raw else []
    if not isinstance(calls, list):
        return []
    return [call for call in calls if isinstance(call, dict)]


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
        self._db.execute(STARTS_SCHEMA)
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
        timing: dict[str, float] | None = None,
    ) -> int:
        cursor = self._db.execute(
            """
            INSERT INTO turns (
                conversation_id, locale, grounded, failures, fallback,
                provider, model, tool_calls, output, question, page,
                understanding, approved, contact, timing
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(timing) if timing else None,
            ),
        )
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def set_timing(self, turn_id: int, timing: dict[str, float]) -> None:
        """Complete a turn's timing record when its stream ends (#336): the phases
        were written with the row, the final `total` and `first_event` exist only
        after the customer's stream is done. A passive second write of the row."""
        self._db.execute(
            "UPDATE turns SET timing = ? WHERE id = ?",
            (json.dumps(timing), turn_id),
        )
        self._db.commit()

    def start(self, conversation_id: str, locale: str) -> int:
        """Note that a turn has begun, before any wait; `finish` closes the note
        when the turn's row lands. A note left behind is an unfinished turn
        (turn_starts, #336)."""
        cursor = self._db.execute(
            "INSERT INTO turn_starts (conversation_id, locale) VALUES (?, ?)",
            (conversation_id, locale),
        )
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def finish(self, token: int) -> None:
        """The turn's row landed: close its start note. A note the service died
        before closing stays for ops/turn_latency.py to count (#336)."""
        self._db.execute("DELETE FROM turn_starts WHERE token = ?", (token,))
        self._db.commit()

    def offers(self, conversation_id: str, limit: int) -> list[bool]:
        """Whether each of the conversation's last `limit` turns carried the contact
        offer, newest first (contact.decide: never twice in a row, once a question)."""
        rows = self._db.execute(
            "SELECT contact FROM turns WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, max(0, limit)),
        ).fetchall()
        return [row[0] is not None for row in rows]

    def forget(self, conversation_id: str) -> int:
        """Take the reading text of a deleted conversation's files out of its turns.

        A reading is the customer's file as read (a nameplate's serial-free text, a
        datasheet's pages): it goes when the conversation goes (docs/specs/13-genie.md
        "附件与铭牌", 保存与清理). Each `read-attachment` call keeps only its id, kind,
        page counts and failure, marked `purged`; a call whose words the reading made
        (`from_reading`: the nameplate's product search) keeps its name and loses its
        arguments and result the same way. The rest of the turn stays for the quality
        check. Returns how many turns changed.
        """
        rows = self._db.execute(
            "SELECT id, tool_calls, understanding, output FROM turns "
            "WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchall()
        # The readings this conversation logged in full: the ids whose text goes.
        purged: set[str] = set()
        for _turn_id, raw, _understanding, _output in rows:
            for call in _calls(raw):
                result = call.get("result")
                if (
                    call.get("name") == READ_ATTACHMENT
                    and isinstance(result, dict)
                    and isinstance(result.get("id"), str)
                    and not result.get("purged")
                    and not result.get("earlier")
                ):
                    purged.add(result["id"])
        changed = 0
        for turn_id, raw, raw_understanding, raw_output in rows:
            calls = _calls(raw)
            touched = False
            derived: set[str] = set()
            for call in calls:
                if call.get("name") == READ_ATTACHMENT:
                    result = call.get("result")
                    # A later turn's entry names the reading only (`earlier`): no text.
                    if (
                        isinstance(result, dict)
                        and not result.get("purged")
                        and not result.get("earlier")
                    ):
                        call["result"] = {
                            key: result[key]
                            for key in ("id", "kind", "pages", "pages_read", "failed")
                            if key in result
                        } | {"purged": True}
                        touched = True
                elif call.get("from_reading") in purged:
                    # The words of this call are the reading's: they go with it.
                    call["arguments"] = {}
                    call["result"] = {"purged": True}
                    if isinstance(call.get("name"), str):
                        derived.add(call["name"])
                    touched = True
            understanding = json.loads(raw_understanding) if raw_understanding else {}
            if not isinstance(understanding, dict):
                understanding = {}
            # The route log names the same words (the nameplate's search input).
            for key in ("calls", "dropped_calls"):
                for call in understanding.get(key) or []:
                    if isinstance(call, dict) and call.get("from_reading") in purged:
                        call["arguments"] = {}
                        call["from_reading"] = None
                        call["purged"] = True
                        touched = True
            # A failed call's error carries its arguments (the search words): an
            # entry naming a purged call goes too.
            failures = understanding.get("call_failures")
            if isinstance(failures, list):
                kept = [
                    entry
                    for entry in failures
                    if not (
                        isinstance(entry, str)
                        and any(entry.startswith(f"{name}: ") for name in derived)
                    )
                ]
                if len(kept) != len(failures):
                    understanding["call_failures"] = kept
                    touched = True
            # A parts list read from a file keeps the rows it matched (#251): the
            # row texts are the file's words and go with its reading; the statuses,
            # quantities and our product labels stay for the quality check.
            output = json.loads(raw_output) if raw_output else {}
            if not isinstance(output, dict):
                output = {}
            parts = understanding.get("parts")
            if isinstance(parts, dict) and parts.get("reading") in purged:
                for block in output.get("blocks") or []:
                    if not (isinstance(block, dict) and block.get("type") == "parts"):
                        continue
                    for row in block.get("rows") or []:
                        if isinstance(row, dict) and row.get("text"):
                            row["text"] = ""
                            row["purged"] = True
                            touched = True
            if touched:
                self._db.execute(
                    "UPDATE turns SET tool_calls = ?, understanding = ?, output = ? "
                    "WHERE id = ?",
                    (
                        json.dumps(calls),
                        json.dumps(understanding, ensure_ascii=False),
                        json.dumps(output, ensure_ascii=False),
                        turn_id,
                    ),
                )
                changed += 1
        self._db.commit()
        return changed

    def vote(self, turn_id: int, value: int) -> bool:
        """Record a vote; False when the turn id is unknown."""
        cursor = self._db.execute(
            "UPDATE turns SET vote = ? WHERE id = ?", (value, turn_id)
        )
        self._db.commit()
        return cursor.rowcount > 0
