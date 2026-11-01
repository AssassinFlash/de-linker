"""One bounded local checkpoint for a deployment, retained only until archive."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

from linker_cutover import atomic, backup, plan, snapshot
from linker_cutover.target import CutoverError, Target


@dataclass
class Checkpoint:
    """Candidate identity and completed phases; never authorization for another source."""

    deploy_id: str
    source: str
    target: list[str | None]
    live: dict[str, str]
    snapshot_pending: dict[str, str] = field(default_factory=dict)
    snapshot: dict[str, str | int] = field(default_factory=dict)
    prepared: dict[str, str] = field(default_factory=dict)
    uploaded: dict[str, str] = field(default_factory=dict)
    completed: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


def path(staging: Path) -> Path:
    """The only active checkpoint in a staging workspace."""
    return staging / ".deploy.json"


@contextmanager
def workspace(staging: Path) -> Iterator[None]:
    """CLI single-writer ownership for the one checkpoint; contention never waits."""
    staging.mkdir(parents=True, exist_ok=True)
    lock = staging / ".deploy.lock"
    with lock.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CutoverError(f"deployment workspace is in use: {staging}") from error
        # Keep one empty inode for this workspace. Unlinking it would let a
        # contender that already opened it lock the old inode while a new
        # contender opens and locks its replacement.
        yield


def target_identity(target: Target) -> list[str | None]:
    """Include transport identity, site root and origin; labels alone are not identity."""
    return [target.label, target.root, target.base_url, target.rsync_remote]


def source_identity(repository: Path, artifacts: list[atomic.Artifact]) -> str:
    """Hash shipped inputs and deploy control logic, independent of unrelated HEAD edits."""
    ignored = tuple(pattern.rstrip("/") for pattern in plan.DEPLOY_EXCLUDES)
    inputs = [
        (
            item.relative,
            atomic.source_digest(item.source, ignored if item.source.is_dir() else ()),
        )
        for item in artifacts
    ]
    for relative in (
        "content",
        "tools/migrate/201-consent.php",
        "tools/migrate/201-consent.json",
    ):
        source = repository / relative
        if source.exists():
            inputs.append((relative, atomic.source_digest(source)))
    inputs.append(("cutover-control", atomic.source_digest(Path(__file__).parent)))
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def save(staging: Path, checkpoint: Checkpoint) -> None:
    """Atomic replacement; one record and one transient write, no history copies."""
    staging.mkdir(parents=True, exist_ok=True)
    temporary = path(staging).with_suffix(".json.next")
    try:
        with temporary.open("w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(asdict(checkpoint), stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path(staging))
        directory = os.open(staging, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def load(staging: Path, target: Target, source: str) -> Checkpoint:
    """Fail closed without removing metadata or its recovery point."""
    try:
        checkpoint = Checkpoint(**json.loads(path(staging).read_text()))
        atomic._check_id(checkpoint.deploy_id)
        if checkpoint.target != target_identity(target):
            raise CutoverError("deployment target mismatch; checkpoint retained")
        if checkpoint.source != source:
            raise CutoverError("deployment source mismatch; checkpoint retained")
        if checkpoint.snapshot_pending:
            pending = checkpoint.snapshot_pending
            if (
                set(pending) != {"name", "home"}
                or not isinstance(pending["name"], str)
                or snapshot.NAME.fullmatch(pending["name"]) is None
                or not isinstance(pending["home"], str)
                or not Path(pending["home"]).is_absolute()
            ):
                raise CutoverError("invalid pending snapshot; checkpoint retained")
        if checkpoint.snapshot:
            saved = Path(str(checkpoint.snapshot["path"]))
            if checkpoint.snapshot_pending and (
                checkpoint.snapshot.get("name") != checkpoint.snapshot_pending["name"]
                or saved
                != snapshot.directory(Path(checkpoint.snapshot_pending["home"]))
                / checkpoint.snapshot_pending["name"]
            ):
                raise CutoverError("deployment snapshot reservation differs")
            if (
                not saved.is_file()
                or saved.stat().st_size != checkpoint.snapshot["size"]
                or backup.sha256(saved) != checkpoint.snapshot["sha256"]
                or not backup.readable_gzip(saved)
            ):
                raise CutoverError("deployment snapshot invalid; checkpoint retained")
        return checkpoint
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise CutoverError(f"invalid deployment checkpoint: {path(staging)}") from error


def record_snapshot(
    staging: Path, checkpoint: Checkpoint, taken: snapshot.Snapshot
) -> None:
    """Keep the exact verified recovery point, rather than taking another on retry."""
    pending = checkpoint.snapshot_pending
    if pending and (
        taken.name != pending["name"]
        or taken.path != snapshot.directory(Path(pending["home"])) / pending["name"]
    ):
        raise CutoverError("deployment snapshot does not match its reservation")
    checkpoint.snapshot = {**asdict(taken), "path": str(taken.path)}
    save(staging, checkpoint)


def cleanup(staging: Path) -> None:
    """After successful archive, reclaim only the stage directories this record owns."""
    checkpoint = Checkpoint(**json.loads(path(staging).read_text()))
    for relative in checkpoint.prepared:
        name = Path(relative).name
        source = staging / name
        if source.is_dir() and not source.is_symlink():
            shutil.rmtree(source)
        (staging / ".stage" / f"{name}.sha256").unlink(missing_ok=True)
    stamp = staging / ".stage"
    if stamp.is_dir() and not any(stamp.iterdir()):
        stamp.rmdir()
    if checkpoint.snapshot_pending:
        snapshot.finish_checkpoint(
            Path(checkpoint.snapshot_pending["home"]),
            path(staging),
            checkpoint.deploy_id,
        )
    else:
        path(staging).unlink()
