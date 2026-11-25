"""Private cross-worker turn results, sharing the actual worker slot database."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event
from typing import Any, Literal

from .work import SITE_SLOTS, Slots, WorkError, configured_slots

RETENTION_SECONDS = 180


def _expiry(token: str) -> int:
    # WP verifies the signature at the ability. Only WP's signed expiry orders renewals.
    fields = token.split("|", 2)
    return (
        int(fields[1])
        if len(fields) == 3 and fields[1].isascii() and fields[1].isdigit()
        else 0
    )


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
                created_at REAL NOT NULL, updated_at REAL NOT NULL, expires_at REAL, execution_at REAL,
                owner_context TEXT
            )""")
            columns = {
                row["name"] for row in db.execute("PRAGMA table_info(turn_jobs)")
            }
            if "execution_at" not in columns:
                db.execute("ALTER TABLE turn_jobs ADD COLUMN execution_at REAL")
            if "owner_context" not in columns:
                db.execute("ALTER TABLE turn_jobs ADD COLUMN owner_context TEXT")
            yield db

    def begin(self, slot: str, conversation: str, subject: str, stage: str) -> float:
        # The accepted job keeps its ID when a worker becomes available.
        now = time.time()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO turn_jobs
                (job_id,conversation_id,subject,pid,slot_id,status,stage,created_at,updated_at)
                VALUES(?,?,?,?,?,'running',?,?,?)""",
                (slot, conversation, subject, os.getpid(), slot, stage, now, now),
            )
        return now

    def claim(
        self, job: str, subject: str, stage: str
    ) -> Literal["gone", "waiting", "claimed"]:
        with self.transaction() as db:
            row = db.execute(
                "SELECT 1 FROM turn_jobs WHERE job_id=? AND subject=? AND status='running' AND stage='waiting'",
                (job, subject),
            ).fetchone()
            if row is None:
                return "gone"
            if not self.slots.reserve(db, subject, job):
                return "waiting"
            now = time.time()
            db.execute(
                "UPDATE turn_jobs SET execution_at=?,updated_at=?,stage=? WHERE job_id=?",
                (now, now, stage, job),
            )
            return "claimed"

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
                "UPDATE turn_jobs SET status='completed',owner_context=NULL,result_stream=?,updated_at=?,expires_at=? WHERE job_id=?",
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
            """UPDATE turn_jobs SET status='failed',owner_context=NULL,error_status=?,error_code=?,error_detail=?,
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

    def user_context(self, job: str, subject: str, original: str) -> str:
        """Private account reads use the newest credential issued by this turn's owner."""
        with self.transaction() as db:
            row = db.execute(
                "SELECT owner_context FROM turn_jobs WHERE job_id=? AND subject=? AND status='running'",
                (job, subject),
            ).fetchone()
        token = (row["owner_context"] or original) if row else ""
        if token.partition("|")[0] != original.partition("|")[0] or _expiry(
            token
        ) < int(time.time()):
            raise WorkError("user_context_expired", 401)
        return str(token)

    def read(
        self, job: str, subject: str, owner_context: str | None = None
    ) -> dict[str, Any] | None:
        with self.transaction() as db:
            db.execute("DELETE FROM turn_jobs WHERE expires_at<=?", (time.time(),))
            select = "SELECT * FROM turn_jobs WHERE job_id=? AND subject=?"
            row = db.execute(select, (job, subject)).fetchone()
            if row is None:
                return None
            if row["status"] == "running" and self._reap_dead(db, row):
                row = db.execute(select, (job, subject)).fetchone()
            if (
                owner_context
                and row["status"] == "running"
                and _expiry(owner_context) > _expiry(row["owner_context"] or "")
            ):
                db.execute(
                    "UPDATE turn_jobs SET owner_context=? WHERE job_id=?",
                    (owner_context, job),
                )
            timing = {}
            if row["execution_at"] is not None:
                timing["queued_seconds"] = max(
                    0.0, row["execution_at"] - row["created_at"]
                )
            elif row["stage"] == "waiting":
                timing["queued_seconds"] = max(0.0, time.time() - row["created_at"])
            if row["status"] == "running":
                return dict(
                    **timing,
                    job_id=job,
                    status="running",
                    stage=row["stage"],
                    updated_at=row["updated_at"],
                )
            if row["status"] == "completed":
                return dict(
                    **timing,
                    job_id=job,
                    status="completed",
                    stream=row["result_stream"],
                )
            return dict(
                **timing,
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


class TurnWorkers:
    """A bounded set of threads services accepted requests from this API process."""

    def __init__(self) -> None:
        self.stopped = Event()
        self.pool = ThreadPoolExecutor(
            max_workers=SITE_SLOTS, thread_name_prefix="genie-turn"
        )

    def submit(
        self,
        jobs: Jobs,
        job: str,
        subject: str,
        first_stage: str,
        execute: Callable[[], None],
    ) -> None:
        def run() -> None:
            try:
                while not self.stopped.is_set():
                    claim = jobs.claim(job, subject, first_stage)
                    if claim == "gone":
                        return
                    if claim == "claimed":
                        execute()
                        return
                    # Another API process or the synchronous route owns the slot.
                    self.stopped.wait(0.6)
                jobs.fail(job, 503, "genie_worker_stopped", "genie_worker_stopped")
            except (OSError, sqlite3.Error):
                logging.getLogger(__name__).exception(
                    "could not claim queued Genie turn"
                )
                jobs.fail(job, 503, "genie_resource_storage", "genie_resource_storage")

        def cancel_unstarted(future: Future[None]) -> None:
            if future.cancelled():
                jobs.fail(job, 503, "genie_worker_stopped", "genie_worker_stopped")

        self.pool.submit(run).add_done_callback(cancel_unstarted)

    def close(self) -> None:
        self.stopped.set()
        self.pool.shutdown(wait=False, cancel_futures=True)


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
