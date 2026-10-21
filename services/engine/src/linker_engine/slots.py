"""Actual engine work slots across workers, including a disconnected PHP caller."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path


class Slots:
    """Hold one subject slot and one of four site slots until work finishes.

    WP admission has the same dimensions (#508). These private slots protect
    the actual process after a PHP timeout. Dead worker PIDs are reclaimed;
    elapsed time alone never releases a still-running calculation.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def acquire(self, subject: str) -> str | None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass
        if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
            raise OSError("engine slot store is not private")
        with closing(sqlite3.connect(self.path, timeout=5, isolation_level=None)) as db:
            db.execute("BEGIN IMMEDIATE")
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
            if busy or total >= 4:
                db.rollback()
                return None
            ident = str(uuid.uuid4())
            db.execute(
                "INSERT INTO slots VALUES (?,?,?)", (ident, subject, os.getpid())
            )
            db.commit()
            return ident

    def release(self, ident: str) -> None:
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute("DELETE FROM slots WHERE id=? AND pid=?", (ident, os.getpid()))
            db.commit()
