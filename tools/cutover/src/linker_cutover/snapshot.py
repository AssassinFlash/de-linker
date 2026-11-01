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

import fcntl
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linker_cutover import backup, backup_retention
from linker_cutover.target import CutoverError, Target

DIRECTORY = "snapshots"

# Tables a code deploy never writes and the snapshot leaves out (see the module
# docstring for the measurement); the WordPress table prefix is read on the host.
SKIPPED_TABLES = ("genie_chunks",)

# The stricter owner retention limit in docs/agents/local-storage.md applies
# across deployments. A restore's explicitly protected source always stays.
KEEP = backup_retention.KEEP
STATE = ".snapshot-retention.json"
LOCK = ".snapshot-retention.lock"
ORIGIN = "linker-cutover-snapshot-retention-v1"
TRANSACTION = STATE + ".txn-"
TRANSACTION_MARKER = ('{"origin":"' + ORIGIN + '",').encode()

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


@contextmanager
def _locked(folder: Path) -> Iterator[None]:
    """Serialize snapshot, restore and baseline operations without replacing the lock."""
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink() or not folder.is_dir():
        raise CutoverError(f"snapshot directory is not a real directory: {folder}")
    fd = os.open(folder / LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CutoverError(f"snapshot resource is in use: {folder}") from error
        try:
            _reap_transactions(folder)
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _state(folder: Path) -> dict[str, Any]:
    path = folder / STATE
    if path.is_symlink():
        raise CutoverError(f"linked snapshot retention state: {path}")
    if not path.exists():
        return {"version": 1, "snapshots": {}, "baselines": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise CutoverError(f"invalid snapshot retention state: {path}") from error
    if (
        not isinstance(data, dict)
        or data.get("origin") != ORIGIN
        or data.get("version") != 1
        or not isinstance(data.get("snapshots"), dict)
        or not isinstance(data.get("baselines"), dict)
        or not all(isinstance(v, dict) for v in data["snapshots"].values())
        or not all(isinstance(v, dict) for v in data["baselines"].values())
    ):
        raise CutoverError(f"invalid snapshot retention state: {path}")
    return data


def _save(folder: Path, state: dict[str, Any]) -> None:
    path = folder / STATE
    fd, name = tempfile.mkstemp(prefix=TRANSACTION, dir=folder)
    pending = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"origin": ORIGIN, **state}, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        pending.replace(path)
    except BaseException:
        pending.unlink(missing_ok=True)
        raise


def _reap_transactions(folder: Path) -> None:
    """Remove only abandoned temp states bearing this operator's marker."""
    for path in folder.glob(TRANSACTION + "*"):
        try:
            info = path.lstat()
            if (
                path.is_symlink()
                or not path.is_file()
                or info.st_uid != os.getuid()
                or info.st_mode & 0o777 != 0o600
                or info.st_size < len(TRANSACTION_MARKER)
            ):
                continue
            with path.open("rb") as stream:
                marker = stream.read(len(TRANSACTION_MARKER))
            if marker == TRANSACTION_MARKER and _unused(path):
                path.unlink()
        except OSError:
            continue


def _verified(path: Path, record: dict[str, Any]) -> bool:
    """Reuse a full hash/gzip proof only while its exact file stamp is unchanged."""
    try:
        if path.is_symlink() or not path.is_file():
            return False
        stamp = backup_retention.file_stamp(path)
        return bool(
            stamp == record.get("stamp")
            and path.stat().st_size == record.get("size")
            and isinstance(record.get("sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", record["sha256"]) is not None
            and backup_retention.file_stamp(path) == stamp
        )
    except OSError:
        return False


def _references(home: Path) -> set[str]:
    """Protect snapshots referenced by the existing cutover workspace records."""
    workspace = home / "cutover-workspace"
    paths = set(workspace.glob("*.json")) | set(workspace.glob("staging/.*.json"))
    paths |= set(workspace.glob("*/drill.json"))
    result: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            result.update(NAME.findall(value))
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for path in paths:
        if path.is_symlink():
            raise CutoverError(f"linked cutover reference: {path}")
        try:
            visit(json.loads(path.read_text()))
        except (OSError, ValueError) as error:
            raise CutoverError(f"unreadable cutover reference: {path}") from error
    return result


def _unused(path: Path) -> bool:
    """An uncertain reader check protects the snapshot."""
    try:
        result = subprocess.run(
            ["lsof", "-nP", "-Fpn", str(path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (
        result.returncode == 1
        and not result.stdout.strip()
        and not result.stderr.strip()
    )


def _prune(
    target: Target,
    home: Path,
    state: dict[str, Any],
    *,
    now: datetime,
    current: str,
    protect: frozenset[str],
) -> None:
    """Retire only unchanged, readable snapshots with proven matching origin."""
    folder = directory(home)
    source = backup_retention.identity(target)
    candidates: list[tuple[datetime, str]] = []
    recovered = False
    for name, record in list(state["snapshots"].items()):
        if record.get("source") != source:
            continue
        if not isinstance(name, str) or NAME.fullmatch(name) is None:
            raise CutoverError("invalid recorded snapshot name")
        path = folder / name
        if (
            record.get("retiring") is True
            and not path.exists()
            and not path.is_symlink()
        ):
            del state["snapshots"][name]
            recovered = True
            continue
        if not _verified(path, record):
            raise CutoverError(f"recorded snapshot is missing or changed: {path}")
        try:
            at = datetime.strptime(name, "db-%Y%m%dT%H%M%SZ.sql.gz").replace(tzinfo=UTC)
        except ValueError as error:
            raise CutoverError(f"invalid recorded snapshot date: {path}") from error
        candidates.append((at, name))
    if recovered:
        _save(folder, state)
    baseline_record = state["baselines"].get(json.dumps(source))
    baseline = ""
    if baseline_record is not None:
        baseline = baseline_record.get("name", "")
        if (
            not isinstance(baseline, str)
            or NAME.fullmatch(baseline) is None
            or not _verified(folder / baseline, baseline_record)
        ):
            raise CutoverError("snapshot baseline is missing or changed")
    references = _references(home)
    for name in set(protect) | references:
        if NAME.fullmatch(name) is not None:
            path = folder / name
            record = state["snapshots"].get(name)
            valid = (
                _verified(path, record)
                if isinstance(record, dict)
                else not path.is_symlink()
                and path.is_file()
                and backup.readable_gzip(path)
            )
            if not valid:
                raise CutoverError(f"protected snapshot is not readable: {path}")
    kept = backup_retention.select_retained(
        candidates,
        now=now,
        protect=frozenset({current, baseline} | set(protect) | references),
    )
    for _, name in candidates:
        record = state["snapshots"][name]
        if name in kept or name in _references(home):
            if record.pop("retiring", None) is not None:
                _save(folder, state)
            continue
        path = folder / name
        if not _unused(path) or not _verified(path, record):
            continue
        record["retiring"] = True
        _save(folder, state)
        if (
            name in _references(home)
            or not _unused(path)
            or not _verified(path, record)
        ):
            record.pop("retiring", None)
            _save(folder, state)
            continue
        path.unlink()
        del state["snapshots"][name]
        _save(folder, state)


def set_baseline(target: Target, home: Path, name: str) -> None:
    """Explicitly retain one verified recovery baseline for this source."""
    folder = directory(home)
    with _locked(folder):
        path = existing(home, name)
        if path.is_symlink() or not backup.readable_gzip(path):
            raise CutoverError(f"snapshot baseline is not a readable gzip: {path}")
        state = _state(folder)
        record = state["snapshots"].get(name)
        if record is not None and (
            record.get("source") != backup_retention.identity(target)
            or not _verified(path, record)
        ):
            raise CutoverError("snapshot baseline source or identity differs")
        stamp = backup_retention.file_stamp(path)
        digest = backup.sha256(path)
        if backup_retention.file_stamp(path) != stamp:
            raise CutoverError("snapshot baseline changed during verification")
        state["baselines"][json.dumps(backup_retention.identity(target))] = {
            "name": name,
            "sha256": digest,
            "size": path.stat().st_size,
            "stamp": stamp,
        }
        _save(folder, state)


def reconcile(target: Target, home: Path, current: str) -> None:
    """Retry interrupted retirement without taking another database dump."""
    folder = directory(home)
    if NAME.fullmatch(current) is None or not (folder / STATE).exists():
        return  # A pre-registry deployment remains usable, with no pruning.
    try:
        with _locked(folder):
            state = _state(folder)
            record = state["snapshots"].get(current)
            if not isinstance(record, dict) or record.get(
                "source"
            ) != backup_retention.identity(target):
                return
            if not _verified(folder / current, record):
                raise CutoverError("deployment snapshot proof differs from registry")
            _prune(
                target,
                home,
                state,
                now=datetime.now(UTC),
                current=current,
                protect=frozenset({current}),
            )
    except (CutoverError, OSError, ValueError) as error:
        print(f"snapshot retention: preserved older snapshots ({error})")


def take(
    target: Target,
    home: Path,
    *,
    now: datetime | None = None,
    protect: frozenset[str] = frozenset(),
    on_verified: Callable[[Snapshot], None] | None = None,
) -> Snapshot:
    """Stream and verify a snapshot, then apply same-source retention.

    The dump is written to a hidden partial file and renamed only after it
    reads to the end as gzip. Unknown legacy and other-source snapshots are
    never candidates for deletion; current, explicit protections and active
    workspace references stay even when they fall outside the normal union.
    """
    folder = directory(home)
    with _locked(folder):
        return _take_locked(
            target, home, now=now, protect=protect, on_verified=on_verified
        )


def _take_locked(
    target: Target,
    home: Path,
    *,
    now: datetime | None,
    protect: frozenset[str],
    on_verified: Callable[[Snapshot], None] | None,
) -> Snapshot:
    folder = directory(home)
    state = _state(folder)
    at = now or datetime.now(UTC)
    name = name_at(at)
    final = folder / name
    if final.exists() or final.is_symlink() or name in state["snapshots"]:
        raise CutoverError(f"{final} already exists; take the snapshot again")
    partial = folder / f".{name}.partial"
    pending = folder / (STATE + ".next")
    if (
        partial.exists()
        or partial.is_symlink()
        or pending.exists()
        or pending.is_symlink()
    ):
        raise CutoverError("unfinished snapshot or retention state must be inspected")
    try:
        backup.dump_to(target, partial, skip=SKIPPED_TABLES)
        partial.rename(final)
    finally:
        partial.unlink(missing_ok=True)
    stamp = backup_retention.file_stamp(final)
    taken = Snapshot(
        name=name, path=final, size=final.stat().st_size, sha256=backup.sha256(final)
    )
    record = {
        "source": backup_retention.identity(target),
        "sha256": taken.sha256,
        "size": taken.size,
        "stamp": stamp,
    }
    if not backup.readable_gzip(final) or not _verified(final, record):
        raise CutoverError(f"new snapshot changed during verification: {final}")
    state["snapshots"][name] = record
    _save(folder, state)
    if on_verified is not None:
        on_verified(taken)
    try:
        _prune(target, home, state, now=at, current=name, protect=protect)
    except (CutoverError, OSError, ValueError) as error:
        # The new, verified snapshot remains usable even if retirement cannot
        # safely establish the identity or references of the older ones.
        if not _verified(final, record):
            raise CutoverError(
                f"new snapshot changed during retention: {final}"
            ) from error
        print(f"snapshot retention: preserved older snapshots ({error})")
    if not _verified(final, record):
        raise CutoverError(f"new snapshot changed during retention: {final}")
    return taken


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
    with _locked(directory(home)):
        path = existing(home, name)
        if not backup.readable_gzip(path):
            raise CutoverError(f"{path} is not a readable gzip")
        before = _take_locked(
            target, home, now=now, protect=frozenset({path.name}), on_verified=None
        )
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
