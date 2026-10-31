"""Daily local log retention, owned by the API rather than optional judges.

No provider or WordPress credentials are needed. Existing files only are opened;
the service does not create a judge store just to clean it. SQLite frees deleted
pages for reuse; an automatic VACUUM would rewrite the file and block requests.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from linker_genie.log import TURN_SEQUENCE_SCHEMA

log = logging.getLogger(__name__)
# Match the site's conversation retention and daily WP-Cron sweep
# (plugins/linker-tools/includes/Genie/Retention.php).
RETENTION_DAYS = 90
PRUNE_EVERY_SECONDS = 86400.0
# Reuse the quality worker's ten-minute outage retry interval. A locked store
# must not wait another whole day, or retry on every customer request.
RETRY_AFTER_SECONDS = 600.0
# Match the quality worker's 20-turn batch; commit each deletion separately so
# an accumulated backlog does not hold the service's writer lock for the sweep.
DELETE_BATCH = 20
BUSY_TIMEOUT = 5.0


def judgments_path(turns_path: Path) -> Path:
    """Shared with the optional judge CLI; --db still overrides it there."""
    return Path(
        os.environ.get("GENIE_JUDGMENTS", str(turns_path.with_name("judgments.sqlite")))
    )


def _delete(
    database: sqlite3.Connection,
    table: str,
    column: str,
    cutoff: str | float,
    stopped: Callable[[], bool],
) -> int:
    database.execute(
        f"CREATE INDEX IF NOT EXISTS {table}_retention ON {table} ({column})"
    )
    database.commit()
    total = 0
    while not stopped():
        with database:
            cursor = database.execute(
                f"DELETE FROM {table} WHERE rowid IN "
                f"(SELECT rowid FROM {table} WHERE {column} < ? LIMIT ?)",
                (cutoff, DELETE_BATCH),
            )
        total += cursor.rowcount
        if cursor.rowcount < DELETE_BATCH:
            return total
    return total


def _prune(
    path: Path, cutoff: str | float, *, turns: bool, stopped: Callable[[], bool]
) -> dict[str, int]:
    if not path.exists():
        return {}
    # mode=rw also prevents accidental creation if the file disappears after
    # exists(). Each sweep owns and closes its connection in the worker thread.
    database = sqlite3.connect(
        f"{path.as_uri()}?mode=rw", uri=True, timeout=BUSY_TIMEOUT
    )
    try:
        present = {
            row[0]
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        deleted: dict[str, int] = {}
        if turns:
            if "turns" in present:
                database.executescript(TURN_SEQUENCE_SCHEMA)
                with database:
                    # Capture the high-water mark before removing any rows. It
                    # keeps future turn IDs above the judge's durable cursor.
                    database.execute(
                        "UPDATE turn_sequence SET last_id = MAX(last_id, "
                        "COALESCE((SELECT MAX(id) FROM turns), 0)) WHERE id = 1"
                    )
                deleted["turns"] = _delete(
                    database, "turns", "created_at", cutoff, stopped
                )
            if "turn_starts" in present:
                deleted["turn_starts"] = _delete(
                    database, "turn_starts", "created_at", cutoff, stopped
                )
        elif "judgments" in present:
            deleted["judgments"] = _delete(
                database, "judgments", "updated_at", cutoff, stopped
            )
        return deleted
    finally:
        database.close()


def sweep(
    turns_path: Path,
    judgments_path: Path,
    now: float,
    stopped: Callable[[], bool] = lambda: False,
) -> bool:
    """Clean each independent store even if the other is locked; report failure.

    Recent unfinished requests and failed verdicts remain available for diagnosis.
    Only records older than the existing privacy boundary are removed.
    """
    cutoff = now - RETENTION_DAYS * 86400
    before = datetime.fromtimestamp(cutoff, UTC).strftime("%Y-%m-%d %H:%M:%S")
    success = True
    deleted: dict[str, int] = {}
    for path, boundary, turns in (
        (turns_path, before, True),
        (judgments_path, cutoff, False),
    ):
        if stopped():
            return False
        try:
            deleted.update(
                _prune(path.resolve(), boundary, turns=turns, stopped=stopped)
            )
        except sqlite3.Error as error:
            log.error("retention sweep failed for %s: %s", path, error)
            success = False
    log.info("retention: deleted %s older than %d days", deleted, RETENTION_DAYS)
    return success


async def run(
    turns_path: Path,
    judgments_path: Path,
    stop: asyncio.Event,
    *,
    clock: Callable[[], float] = time.time,
) -> None:
    """Sweep at API startup and daily while idle, never on the request thread.

    Shutdown wakes the timer and waits for an in-progress SQLite sweep to close
    its connections. No detached task or extra service survives the API.
    """
    while not stop.is_set():
        success = await asyncio.to_thread(
            sweep, turns_path, judgments_path, clock(), stop.is_set
        )
        delay = PRUNE_EVERY_SECONDS if success else RETRY_AFTER_SECONDS
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            pass
