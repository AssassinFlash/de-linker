"""One bounded local checkpoint for a deployment, retained only until archive."""

from __future__ import annotations

import fcntl
import hashlib
import json
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
        temporary.write_text(json.dumps(asdict(checkpoint), sort_keys=True))
        temporary.chmod(0o600)
        temporary.replace(path(staging))
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
        if checkpoint.snapshot:
            saved = Path(str(checkpoint.snapshot["path"]))
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
    path(staging).unlink()
