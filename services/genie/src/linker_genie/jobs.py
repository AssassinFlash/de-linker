"""Private cross-worker turn results, sharing the actual worker slot database."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .work import Slots, WorkError, configured_slots

RETENTION_SECONDS = 180


class Jobs:
    def __init__(self, slots: Slots) -> None:
        self.slots = slots

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.slots.transaction() as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            db.execute("""CREATE TABLE IF NOT EXISTS turn_jobs (
                job_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                subject TEXT NOT NULL, pid INTEGER NOT NULL, slot_id TEXT NOT NULL,
                status TEXT NOT NULL, stage TEXT NOT NULL, result_stream TEXT,
                error_status INTEGER, error_code TEXT, error_detail TEXT,
                created_at REAL NOT NULL, updated_at REAL NOT NULL, expires_at REAL
            )""")
            yield db

    def begin(self, slot: str, conversation: str, subject: str, stage: str) -> float:
        # The slot's UUID4 identifies exactly one admitted turn through completion.
        now = time.time()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO turn_jobs
                (job_id,conversation_id,subject,pid,slot_id,status,stage,created_at,updated_at)
                VALUES(?,?,?,?,?,'running',?,?,?)""",
                (slot, conversation, subject, os.getpid(), slot, stage, now, now),
            )
        return now

    def stage(self, job: str, value: str) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE turn_jobs SET stage=?,updated_at=? WHERE job_id=? AND status='running' AND stage<>?",
                (value, time.time(), job, value),
            )

    def finish(self, job: str, stream: str) -> bool:
        now = time.time()
        with self.transaction() as db:
            recorded = db.execute(
                "UPDATE turn_jobs SET status='completed',result_stream=?,updated_at=?,expires_at=? WHERE job_id=?",
                (stream, now, now + RETENTION_SECONDS, job),
            )
            db.execute("DELETE FROM slots WHERE id=?", (job,))
            return recorded.rowcount == 1

    def fail(self, job: str, status: int, code: str, detail: str) -> None:
        with self.transaction() as db:
            self._fail(db, job, status, code, detail)

    @staticmethod
    def _fail(
        db: sqlite3.Connection, job: str, status: int, code: str, detail: str
    ) -> None:
        now = time.time()
        db.execute(
            """UPDATE turn_jobs SET status='failed',error_status=?,error_code=?,error_detail=?,
            updated_at=?,expires_at=? WHERE job_id=? AND status='running'""",
            (status, code, detail, now, now + RETENTION_SECONDS, job),
        )
        db.execute("DELETE FROM slots WHERE id=?", (job,))

    def _reap_dead(self, db: sqlite3.Connection, row: sqlite3.Row) -> bool:
        try:
            os.kill(row["pid"], 0)
        except ProcessLookupError:
            self._fail(
                db, row["job_id"], 503, "genie_worker_stopped", "genie_worker_stopped"
            )
            return True
        return False

    def read(self, job: str, subject: str) -> dict[str, Any] | None:
        with self.transaction() as db:
            db.execute("DELETE FROM turn_jobs WHERE expires_at<=?", (time.time(),))
            select = "SELECT * FROM turn_jobs WHERE job_id=? AND subject=?"
            row = db.execute(select, (job, subject)).fetchone()
            if row is None:
                return None
            if row["status"] == "running" and self._reap_dead(db, row):
                row = db.execute(select, (job, subject)).fetchone()
            if row["status"] == "running":
                return dict(
                    job_id=job,
                    status="running",
                    stage=row["stage"],
                    updated_at=row["updated_at"],
                )
            if row["status"] == "completed":
                return dict(job_id=job, status="completed", stream=row["result_stream"])
            return dict(
                job_id=job,
                status="failed",
                http_status=row["error_status"],
                code=row["error_code"],
                detail=row["error_detail"],
            )

    def prune(self) -> None:
        if self.slots.path.exists():
            with self.transaction() as db:
                db.execute("DELETE FROM turn_jobs WHERE expires_at<=?", (time.time(),))
                for row in db.execute(
                    "SELECT job_id,pid FROM turn_jobs WHERE status='running'"
                ).fetchall():
                    self._reap_dead(db, row)

    def forget(self, conversation: str) -> None:
        if self.slots.path.exists():
            with self.transaction() as db:
                db.execute(
                    "DELETE FROM turn_jobs WHERE conversation_id=?", (conversation,)
                )


async def expire_results(stop: asyncio.Event) -> None:
    """Expire stored readings even after the visitor closes their last tab."""
    if not os.environ.get("LINKER_GENIE_WORK_PATH"):
        return
    jobs = Jobs(configured_slots())
    while not stop.is_set():
        try:
            await asyncio.to_thread(jobs.prune)
        except (WorkError, OSError, sqlite3.Error):
            logging.getLogger(__name__).exception("could not expire Genie turn results")
        try:
            await asyncio.wait_for(stop.wait(), timeout=RETENTION_SECONDS)
        except TimeoutError:
            continue
