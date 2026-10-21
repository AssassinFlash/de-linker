"""Private, cross-process provider dispatch ledger (#508/#521).

This is a request-count guard, not a token or euro estimate. Nothing from a
customer's input, an API key or a browser is stored here. A successful take is
final: a request might have reached the provider even if its reply never arrives.
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Literal

Provider = Literal["deepseek", "jev", "embedding"]
# Owner-approved operating limits: #508, decision comment 6324114050. Every
# actual HTTP attempt (including a tool loop, page or retry) uses one unit.
# Runtime embedding: #521 operating recommendation accepted by owner; the
# offline index builder does not use this budget.
CAPACITIES: dict[Provider, int] = {"deepseek": 2000, "jev": 200, "embedding": 2000}


class BudgetError(Exception):
    """Safe failure code; deliberately not RuntimeError (cycle retries those)."""

    def __init__(self, reason: str, status: int = 503) -> None:
        self.reason = reason
        self.status = status
        super().__init__(f"provider_budget_{reason}")


class Ledger:
    """Atomic pre-dispatch debit in a private, persistent SQLite file.

    All service and quality-worker processes must use the same absolute path.
    BEGIN IMMEDIATE serializes the check and debit; commit happens before send.
    A repeated attempt ID cannot authorize another send, even after a restart.
    """

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        if not path.is_absolute() or path.is_symlink():
            raise BudgetError("configuration")
        self.path = path
        self.clock = clock

    def take(self, provider: Provider, attempt: str) -> int:
        if provider not in CAPACITIES:
            raise BudgetError("provider", 400)
        try:
            if (
                str(uuid.UUID(attempt, version=4)) != attempt
                or uuid.UUID(attempt).version != 4
            ):
                raise ValueError
        except ValueError as error:
            raise BudgetError("attempt", 400) from error
        # UTC days are Unix days; this is independent of host timezone/DST.
        day = int(self.clock()) // 86400
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            # O_EXCL prevents opening an existing untrusted/symlinked file at
            # creation. Deployment owns the private parent directory.
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
            if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
                raise BudgetError("permissions")
            with closing(
                sqlite3.connect(self.path, timeout=5, isolation_level=None)
            ) as db:
                db.execute("PRAGMA busy_timeout=5000")
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS dispatch (id TEXT PRIMARY KEY, provider TEXT NOT NULL, day INTEGER NOT NULL)"
                )
                # Keep the current and previous UTC day for bounded storage and
                # ambiguous retries over midnight. UUID reuse never means permit.
                db.execute("DELETE FROM dispatch WHERE day < ?", (day - 1,))
                if db.execute(
                    "SELECT 1 FROM dispatch WHERE id = ?", (attempt,)
                ).fetchone():
                    raise BudgetError("replayed", 409)
                used = int(
                    db.execute(
                        "SELECT COUNT(*) FROM dispatch WHERE provider = ? AND day = ?",
                        (provider, day),
                    ).fetchone()[0]
                )
                if used >= CAPACITIES[provider]:
                    raise BudgetError("quota", 429)
                db.execute(
                    "INSERT INTO dispatch VALUES (?, ?, ?)", (attempt, provider, day)
                )
                db.commit()
                return CAPACITIES[provider] - used - 1
        except (OSError, sqlite3.Error) as error:
            # Never reset a damaged ledger or create an in-memory substitute.
            raise BudgetError("unavailable") from error


def take(provider: Provider, attempt: str | None = None) -> int | None:
    """Shared Python API, also used by the private PHP translation gateway.

    Explicit off is the rollout switch. Enforce with no valid path fails closed;
    public protection's off/observe mode has no influence on this hard guard.
    """
    mode = os.environ.get("LINKER_PROVIDER_BUDGET_MODE", "off")
    if mode == "off":
        return None
    if mode != "enforce":
        raise BudgetError("configuration")
    path = os.environ.get("LINKER_PROVIDER_BUDGET_PATH", "")
    if not path:
        raise BudgetError("configuration")
    return Ledger(Path(path)).take(provider, attempt or str(uuid.uuid4()))
