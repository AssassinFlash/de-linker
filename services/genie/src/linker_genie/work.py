"""Actual Genie work slots, held by the synchronous worker after HTTP disconnect."""

from __future__ import annotations

import os
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path


class Slots:
    """Hold one subject slot and one of two site slots until work finishes.

    WP admission has the same dimensions (#508). These private slots protect
    actual Genie work after the PHP caller stops waiting. Dead worker PIDs are reclaimed;
    elapsed time alone never releases a still-running turn.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass
        if (
            self.path.parent.is_symlink()
            or self.path.is_symlink()
            or self.path.stat().st_mode & 0o077
        ):
            raise OSError("Genie slot store is not private")
        with closing(sqlite3.connect(self.path, timeout=5, isolation_level=None)) as db:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()

    def acquire(self, subject: str) -> str | None:
        with self.transaction() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS slots (id TEXT PRIMARY KEY, subject TEXT UNIQUE NOT NULL, pid INTEGER NOT NULL)"
            )
            for ident, pid in db.execute("SELECT id,pid FROM slots").fetchall():
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    db.execute("DELETE FROM slots WHERE id=?", (ident,))
            busy = db.execute(
                "SELECT COUNT(*) FROM slots WHERE subject=?", (subject,)
            ).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
            if busy or total >= 2:
                return None
            ident = str(uuid.uuid4())
            db.execute(
                "INSERT INTO slots VALUES (?,?,?)", (ident, subject, os.getpid())
            )
            return ident

    def release(self, ident: str) -> None:
        with self.transaction() as db:
            db.execute("DELETE FROM slots WHERE id=? AND pid=?", (ident, os.getpid()))


class WorkError(Exception):
    def __init__(self, reason: str, status: int = 503) -> None:
        self.reason = reason
        self.status = status
        super().__init__(f"genie_resource_{reason}")


def configured_slots() -> Slots:
    path = Path(os.environ.get("LINKER_GENIE_WORK_PATH", ""))
    if not path.is_absolute():
        raise WorkError("configuration")
    return Slots(path)


def require_subject(subject: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", subject):
        raise WorkError("subject", 400)


def acquire(slots: Slots, subject: str) -> str:
    require_subject(subject)
    try:
        ident = slots.acquire(subject)
    except (OSError, sqlite3.Error) as error:
        raise WorkError("storage") from error
    if ident is None:
        raise WorkError("busy", 429)
    return ident


@contextmanager
def hold(subject: str) -> Iterator[None]:
    """Synchronous handler scope, not an ASGI cancellation/finalizer scope.

    A dropped socket/PHP timeout cannot release a thread that still calls models.
    All expensive turn work completes before the SSE response is constructed.
    """
    mode = os.environ.get("LINKER_GENIE_WORK_MODE", "off")
    if mode == "off":
        yield
        return
    if mode != "enforce":
        raise WorkError("configuration")
    slots = configured_slots()
    ident = acquire(slots, subject)
    try:
        yield
    finally:
        slots.release(ident)
