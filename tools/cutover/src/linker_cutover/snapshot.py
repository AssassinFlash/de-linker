"""The database snapshot every deploy takes first (docs/specs/17-cutover.md, 部署前快照).

A code deploy cannot touch `wp-content/uploads`, and the atomic switch keeps
the code it replaces (`atomic.py`; `rollback-deploy` puts it back). What a
deploy can still change is the database: plugin activation, options,
language packs. So the backup a deploy needs is the database alone, and it
needs it before anything is uploaded (owner question 2026-10-18, #305).

The dump streams to this Mac, like the full backup's, and nothing is written
on the host: the owner keeps the account's disk for the site (2026-10-18). It
is the full backup's own dump script, so the password stays on the host in
mysqldump's environment.

One table is left out: `<prefix>genie_chunks`, 817.9 MB of the database
(measured on live 2026-10-18; the rest of the database is about 110 MB). It
is the retired in-database knowledge index. The Genie service reads its own
SQLite index on the VPS (#257), no site code reads or writes this table, and a
code deploy cannot change it. The full backup (`backup.py`) still carries it.
Restoring a snapshot leaves the table as it is, because the dump neither drops
nor recreates it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import backup
from linker_cutover.target import CutoverError, Target

DIRECTORY = "snapshots"

# Tables a code deploy never writes and the snapshot leaves out (see the module
# docstring for the measurement); the WordPress table prefix is read on the host.
SKIPPED_TABLES = ("genie_chunks",)

# The newest 20 stay; older ones are deleted after a new one is verified. The
# first live snapshot was 6,200,721 bytes (2026-10-18), so 20 hold about
# 125 MB of this Mac: every deploy of the last weeks stays one command away.
KEEP = 20

NAME = re.compile(r"db-\d{8}T\d{6}Z\.sql\.gz")


@dataclass(frozen=True)
class Snapshot:
    """A snapshot written and verified on this Mac."""

    name: str
    path: Path
    size: int
    sha256: str


def directory(home: Path) -> Path:
    """`~/de-linker-data/snapshots/`, beside the full backups."""
    return home / DIRECTORY


def name_at(now: datetime | None = None) -> str:
    """The snapshot's file name for a moment, in UTC."""
    return (now or datetime.now(UTC)).strftime("db-%Y%m%dT%H%M%SZ.sql.gz")


def existing(home: Path, name: str) -> Path:
    """The path of a snapshot by name, refusing anything that is not one."""
    if not NAME.fullmatch(name):
        raise CutoverError(
            f"{name!r} is not a snapshot name (db-YYYYMMDDTHHMMSSZ.sql.gz)"
        )
    path = directory(home) / name
    if not path.is_file():
        raise CutoverError(f"{path} does not exist")
    return path


def take(
    target: Target,
    home: Path,
    *,
    now: datetime | None = None,
    protect: frozenset[str] = frozenset(),
) -> Snapshot:
    """Stream the database here, verify it, keep the newest KEEP.

    The dump is written to a hidden partial file and renamed only after it
    reads to the end as gzip, so the directory never holds a snapshot that
    would not restore. A failed dump leaves nothing behind. Pruning never
    removes the snapshot just taken (even when a clock skew put a newer name
    on an older file) nor any name in `protect` (the one a restore is about
    to read).
    """
    folder = directory(home)
    folder.mkdir(parents=True, exist_ok=True)
    name = name_at(now)
    final = folder / name
    if final.exists():
        raise CutoverError(f"{final} already exists; take the snapshot again")
    partial = folder / f".{name}.partial"
    try:
        backup.dump_to(target, partial, skip=SKIPPED_TABLES)
        partial.rename(final)
    finally:
        partial.unlink(missing_ok=True)
    others = [old for old in available(home) if old != name and old not in protect]
    for old in others[KEEP - 1 - len(protect) :]:
        (folder / old).unlink(missing_ok=True)
    return Snapshot(
        name=name, path=final, size=final.stat().st_size, sha256=backup.sha256(final)
    )


def restore(
    target: Target, home: Path, name: str, *, now: datetime | None = None
) -> list[str]:
    """Put a snapshot back, after snapshotting the database it replaces.

    The import is a data write like any other (AGENTS.md §5): the state being
    overwritten is kept first, so a restore of the wrong snapshot is itself
    one command away from undone. Only the tables in the snapshot are
    replaced; a table created after it (a new plugin's) keeps its rows, and
    the code is put back separately with `rollback-deploy`.
    """
    path = existing(home, name)
    if not backup.readable_gzip(path):
        raise CutoverError(f"{path} is not a readable gzip")
    before = take(target, home, now=now, protect=frozenset({path.name}))
    backup.restore_database(target, path)
    target.wp("cache", "flush")
    return [
        f"kept the replaced database as {before.name}",
        f"restored {path}",
        "wp cache flush",
    ]


def available(home: Path) -> list[str]:
    """The snapshot names on this Mac, newest first."""
    folder = directory(home)
    if not folder.is_dir():
        return []
    return sorted(
        (path.name for path in folder.iterdir() if NAME.fullmatch(path.name)),
        reverse=True,
    )
