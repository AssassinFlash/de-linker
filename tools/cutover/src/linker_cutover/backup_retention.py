"""Full-backup retention, after success only (docs/agents/local-storage.md).

Two permanent empty lock inodes coordinate native writers/readers. The one
small state file caches verified dumps and explicitly adopts legacy manifests;
unknown directories are never inferred from their name or target label.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from linker_local.instance import home as local_home
from linker_local.registry import Registry

from linker_cutover import backup
from linker_cutover.target import HTACCESS, PLUGINS, UPLOADS, CutoverError, Target

NAME = re.compile(r"cutover-\d{8}-\d{4}")
STATE = ".backup-retention.json"
# Owner retention table: latest three, last successful backup per UTC day
# within seven days, one explicit baseline, plus actual active references.
KEEP = 3
DAYS = 7


def select_retained(
    entries: list[tuple[datetime, str]],
    *,
    now: datetime,
    protect: frozenset[str] = frozenset(),
) -> set[str]:
    """Keep the newest three, each recent UTC day end, and explicit protections."""
    ordered = sorted(entries, key=lambda item: (item[0], item[1]), reverse=True)
    kept = {name for _, name in ordered[:KEEP]} | set(protect)
    days: set[object] = set()
    today = now.astimezone(UTC).date()
    for at, name in ordered:
        day = at.astimezone(UTC).date()
        if today - timedelta(days=DAYS - 1) <= day <= today and day not in days:
            kept.add(name)
            days.add(day)
    return kept


def identity(target: Target) -> list[str | None]:
    """Match the deployment checkpoint's transport/root/origin identity."""
    return [target.label, target.root, target.base_url, target.rsync_remote]


@contextmanager
def locked(home: Path, *, writer: bool = False, reader: bool = False) -> Iterator[None]:
    """Never wait for another operator; shared readers make pruning skip."""
    home.mkdir(parents=True, exist_ok=True)
    name = ".backup-create.lock" if writer else ".backup-read.lock"
    with (home / name).open("a") as handle:
        try:
            fcntl.flock(
                handle, (fcntl.LOCK_SH if reader else fcntl.LOCK_EX) | fcntl.LOCK_NB
            )
        except BlockingIOError as error:
            raise CutoverError(f"backup resource is in use: {home}") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _state(home: Path) -> dict[str, Any]:
    path = home / STATE
    if not path.exists():
        return {"version": 1, "backups": {}, "baselines": {}, "proofs": {}}
    data = json.loads(path.read_text())
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("backups"), dict)
        or not isinstance(data.get("baselines"), dict)
        or not all(isinstance(v, dict) for v in data["backups"].values())
        or not all(isinstance(v, str) for v in data["baselines"].values())
        or not isinstance(data.get("proofs", {}), dict)
        or not all(isinstance(v, dict) for v in data.get("proofs", {}).values())
    ):
        raise CutoverError(f"unknown backup retention state: {path}")
    data.setdefault("proofs", {})
    return data


def _save(home: Path, state: dict[str, Any]) -> None:
    pending = home / (STATE + ".next")
    try:
        pending.write_text(json.dumps(state, sort_keys=True) + "\n")
        pending.chmod(0o600)
        pending.replace(home / STATE)
    finally:
        pending.unlink(missing_ok=True)


def _stamp(path: Path) -> list[int]:
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def file_stamp(path: Path) -> list[int]:
    """Include ctime so even same-size writes with restored mtime invalidate proof.

    The new backup's manifest proves shared inodes once for every retained
    version, including ctime changes caused by creating additional hard links.
    """
    return _stamp(path)


def _manifest(directory: Path) -> tuple[dict[str, Any], str]:
    if directory.is_symlink() or not directory.is_dir():
        raise CutoverError(f"not a backup directory: {directory}")
    manifest = directory / backup.MANIFEST
    if manifest.is_symlink():
        raise CutoverError(f"linked backup manifest: {manifest}")
    raw = manifest.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise CutoverError(f"invalid backup manifest: {directory}")
    if not {backup.DUMP, backup.OPTIONS, HTACCESS} <= data["files"].keys():
        raise CutoverError(f"incomplete backup manifest: {directory}")
    return data, hashlib.sha256(raw).hexdigest()


def same_source(directory: Path, target: Target) -> bool:
    """Only a recorded source may provide incremental hard links."""
    try:
        data, digest = _manifest(directory)
        if data.get("source") == identity(target):
            return True
        record = _state(directory.parent)["backups"].get(directory.name, {})
        return bool(
            record.get("source") == identity(target)
            and record.get("manifest") == digest
        )
    except (OSError, ValueError, TypeError, KeyError, CutoverError):
        return False


def _check_files(
    directory: Path,
    data: dict[str, Any],
    proofs: dict[str, str],
    *,
    exact: bool = False,
) -> set[str]:
    """Verify changed/unproven inodes once; reuse exact stat proofs otherwise."""
    files = data["files"]
    checked_directories: set[Path] = set()
    used: set[str] = set()
    for name, entry in files.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
            raise CutoverError(f"unsafe backup entry: {name}")
        path = directory / relative
        for parent in path.parents:
            if not parent.is_relative_to(directory) or parent in checked_directories:
                break
            if parent.is_symlink():
                raise CutoverError(f"linked backup directory: {parent}")
            checked_directories.add(parent)
        if (
            path.is_symlink()
            or not path.is_file()
            or not isinstance(entry, dict)
            or path.stat().st_size != entry.get("bytes")
            or not re.fullmatch(r"[a-f0-9]{64}", str(entry.get("sha256", "")))
        ):
            raise CutoverError(f"backup file is missing or changed: {path}")
        stamp = file_stamp(path)
        key = json.dumps(stamp)
        expected = entry["sha256"]
        if entry.get("verified_stat") != stamp and proofs.get(key) != expected:
            if backup.sha256(path) != expected or file_stamp(path) != stamp:
                raise CutoverError(f"backup file content changed: {path}")
        proofs[key] = expected
        used.add(key)
    for tree in (PLUGINS, UPLOADS):
        if not (directory / tree).is_dir():
            raise CutoverError(f"backup tree is missing: {directory / tree}")
    if exact:
        actual = {
            str(p.relative_to(directory))
            for p in directory.rglob("*")
            if p.is_file() or p.is_symlink()
        }
        if actual != set(files) | {backup.MANIFEST}:
            raise CutoverError(f"backup has unknown files: {directory}")
    return used


def _verify_dump(
    directory: Path,
    data: dict[str, Any],
    digest: str,
    record: dict[str, Any],
    proofs: dict[str, str],
) -> None:
    dump = directory / backup.DUMP
    stamp = _stamp(dump)
    proof = {"manifest": digest, "dump": stamp}
    if record.get("verified") == proof:
        return
    if (
        proofs.get(json.dumps(stamp)) != data["files"][backup.DUMP]["sha256"]
        or not backup.readable_gzip(dump)
        or _stamp(dump) != stamp
    ):
        raise CutoverError(f"backup database is not verified: {dump}")
    record["verified"] = proof


def register(directory: Path, target: Target, *, baseline: bool = False) -> None:
    """Explicit native adoption of a previously verified legacy source.

    The operator supplies the source legacy labels cannot prove. Validate the
    existing manifest/files and database, retaining that proof for later runs.
    No old backup is deleted by registration.
    """
    directory = directory.absolute()
    if not NAME.fullmatch(directory.name):
        raise CutoverError(f"not a native backup name: {directory}")
    home = directory.parent
    with locked(home, writer=True), locked(home, reader=True):
        state = _state(home)
        data, digest = _manifest(directory)
        if data.get("target") != target.label or data.get(
            "source", identity(target)
        ) != identity(target):
            raise CutoverError("backup registration source mismatch")
        proofs = state["proofs"].setdefault(json.dumps(identity(target)), {})
        _check_files(directory, data, proofs)
        record = state["backups"].setdefault(directory.name, {})
        if record.get("source", identity(target)) != identity(target):
            raise CutoverError("backup registration source mismatch")
        _verify_dump(directory, data, digest, record, proofs)
        record.update(source=identity(target), manifest=digest)
        if baseline:
            state["baselines"][json.dumps(identity(target))] = directory.name
        _save(home, state)


def _references(home: Path) -> set[str]:
    """Read existing instance and cutover metadata, without traversing sites."""
    root = local_home()
    paths = set(root.glob("*/snapshot.json"))
    paths |= {
        instance.snapshot_file
        for instance in Registry(root).all()
        if instance.snapshot_file.exists()
    }
    workspace = home / "cutover-workspace"
    paths |= set(workspace.glob("*.json")) | set(workspace.glob("staging/.*.json"))
    paths |= set(workspace.glob("*/drill.json"))
    references: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            references.update(NAME.findall(value))
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for path in paths:
        visit(json.loads(path.read_text()))
    return references


def _unused(directory: Path, commands: str) -> bool:
    """Check non-cooperating readers too; a failed observer cannot authorize deletion."""
    if str(directory) in commands:
        return False
    try:
        result = subprocess.run(
            ["lsof", "-nP", "-Fpn", "+D", str(directory)],
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


def prune(
    home: Path,
    target: Target,
    current: Path,
    *,
    now: datetime,
    protect: frozenset[str] = frozenset(),
    verified_dump: str | None = None,
) -> list[str]:
    """Called only after a complete backup; failure never invalidates that backup."""
    removed: list[str] = []
    try:
        with locked(home):
            state = _state(home)
            source = identity(target)
            source_key = json.dumps(source)
            proofs = state["proofs"].setdefault(source_key, {})
            candidates: list[tuple[datetime, Path, dict[str, Any], str]] = []
            for path in home.iterdir():
                if not NAME.fullmatch(path.name):
                    continue
                try:
                    data, digest = _manifest(path)
                    record = state["backups"].get(path.name, {})
                    owned = data.get("source") == source or (
                        record.get("source") == source
                        and record.get("manifest") == digest
                    )
                    at = datetime.fromisoformat(data["taken_at"])
                    if owned and at.tzinfo is not None:
                        candidates.append((at.astimezone(UTC), path, data, digest))
                except (OSError, ValueError, KeyError, TypeError, CutoverError):
                    continue
            candidates.sort(key=lambda item: (item[0], item[1].name), reverse=True)
            if not any(path == current for _, path, _, _ in candidates):
                raise CutoverError("current backup has no verified source identity")
            baseline = state["baselines"].get(source_key, "")
            if baseline and not any(
                path.name == baseline for _, path, _, _ in candidates
            ):
                raise CutoverError("registered backup baseline is missing or changed")
            kept = select_retained(
                [(at, path.name) for at, path, _, _ in candidates],
                now=now,
                protect=frozenset(
                    {current.name, baseline} | set(protect) | _references(home)
                ),
            )
            # Verify ALL selected recovery points before the first deletion.
            proof_keys: set[str] = set()
            for _, path, data, digest in candidates:
                if path.name not in kept:
                    continue
                proof_keys |= _check_files(path, data, proofs)
                record = state["backups"].setdefault(path.name, {})
                if (
                    path == current
                    and verified_dump == data["files"][backup.DUMP]["sha256"]
                ):
                    record["verified"] = {
                        "manifest": digest,
                        "dump": _stamp(path / backup.DUMP),
                    }
                _verify_dump(path, data, digest, record, proofs)
            state["proofs"][source_key] = {key: proofs[key] for key in proof_keys}
            _save(home, state)
            commands = subprocess.run(
                ["ps", "-axo", "command="],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout
            pending: list[tuple[Path, str]] = []
            # Preflight every deletion before unlinking anything: removing one
            # hard link changes the shared inode's ctime. Validating all copies
            # first lets every old tree reuse one exact inode proof.
            for _, path, data, digest in candidates:
                if path.name in kept:
                    continue
                # Re-read references immediately before each removal. Unknown
                # supplemental evidence inside a backup protects that directory.
                if path.name in _references(home) or not _unused(path, commands):
                    continue
                try:
                    _check_files(path, data, proofs, exact=True)
                except CutoverError as error:
                    print(f"backup retention: preserved {path} ({error})")
                    continue
                pending.append((path, digest))
            for path, digest in pending:
                if path.name in _references(home) or not _unused(path, commands):
                    continue
                if _manifest(path)[1] != digest:
                    raise CutoverError(f"backup changed during retention: {path}")
                shutil.rmtree(path)
                removed.append(path.name)
                state["backups"].pop(path.name, None)
            _save(home, state)
    except (
        CutoverError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ) as error:
        print(f"backup retention: skipped remaining cleanup ({error})")
    for name in removed:
        print(f"backup retention: removed {home / name}")
    return removed
