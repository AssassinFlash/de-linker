"""Offline CAS mark/sweep; HTTP and worker must be stopped before apply.

The release operator owns that maintenance window. Planning is read-only and
advisory: apply always recomputes reachability under the exclusive CAS lock.
Official archive backups are independent. Database-only copies outside that
contract are unsupported and must not rely on this workspace's source CAS.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import archive
from .canonical import Object
from .dependencies import cas_lock, reachable_blobs
from .errors import VersionUnavailable
from .storage import Blobs, _sync_directory

HASH = re.compile(r"[a-f0-9]{64}")
INCOMING = re.compile(r"\.incoming-[a-f0-9]{32}")


def independent_snapshot(path: Path, source: Path) -> Object:
    """Reject DB-only, shared-CAS and unknown snapshot layouts explicitly."""
    path = path.absolute()
    if path.resolve() != path or (path / "blobs").resolve() != path / "blobs":
        raise VersionUnavailable("snapshot is not independent of source storage")
    if path == source or path.is_relative_to(source):
        raise VersionUnavailable("snapshot must be outside the source workspace")
    for name in ("workspace.sqlite", "backup.json"):
        item = path / name
        if not item.is_file() or item.resolve() != item or item.stat().st_nlink != 1:
            raise VersionUnavailable(
                "snapshot database and manifest must own independent files"
            )
    manifest = archive.verify(path)
    # Verify alone follows paths; independent recovery must own the actual
    # retained byte paths rather than sharing a symlink to the source CAS.
    hashes = manifest["blobs"]
    assert isinstance(hashes, list)
    for sha256 in hashes:
        assert isinstance(sha256, str)
        item = path / "blobs" / sha256[:2] / sha256
        if item.resolve() != item:
            raise VersionUnavailable("snapshot CAS is not independent")
    return manifest


def _inventory(directory: Path) -> tuple[dict[str, Path], list[Path]]:
    blobs: dict[str, Path] = {}
    temporary: list[Path] = []
    for prefix in sorted(directory.iterdir()):
        if re.fullmatch(r"[a-f0-9]{2}", prefix.name) is None:
            continue
        if not prefix.is_dir() or prefix.resolve() != prefix:
            raise VersionUnavailable("invalid CAS prefix")
        for path in sorted(prefix.iterdir()):
            if HASH.fullmatch(path.name):
                if (
                    not path.is_file()
                    or path.resolve() != path
                    or path.name[:2] != prefix.name
                ):
                    raise VersionUnavailable("invalid CAS byte path")
                blobs[path.name] = path
            elif INCOMING.fullmatch(path.name):
                if not path.is_file() or path.is_symlink():
                    raise VersionUnavailable("invalid CAS temporary path")
                temporary.append(path)
    return blobs, temporary


def _collect(
    directory: Path,
    *,
    apply: bool,
    recovery: Path | None,
    snapshots: tuple[Path, ...],
    owned_runtime_sha256: str | None,
) -> Object:
    if (
        directory.resolve() != directory
        or (directory / "blobs").resolve() != directory / "blobs"
    ):
        raise VersionUnavailable("workspace paths must not follow symbolic links")
    if (
        not (directory / "blobs").is_dir()
        or not (directory / "workspace.sqlite").is_file()
    ):
        raise VersionUnavailable("workspace storage is absent")
    blobs = Blobs(directory / "blobs")
    retained = archive._check_database(directory / "workspace.sqlite", blobs)
    if (
        owned_runtime_sha256 is not None
        and owned_runtime_sha256 not in retained
        and (blobs.directory / owned_runtime_sha256[:2] / owned_runtime_sha256).exists()
    ):
        # Kernel startup owns this bundle before any job persists its hash.
        # Retain its complete verified graph without publishing missing bytes.
        retained.update(reachable_blobs(blobs, {owned_runtime_sha256}, blobs.directory))
    inventory, temporary = _inventory(blobs.directory)
    for snapshot in snapshots:
        independent_snapshot(snapshot, directory)
    candidates = sorted(inventory.keys() - retained)
    # Validate all candidate bytes before the first unlink, as well as all roots.
    for sha256 in candidates:
        blobs.read(sha256)
    sizes = {sha256: inventory[sha256].stat().st_size for sha256 in candidates}
    if apply:
        if recovery is None:
            raise VersionUnavailable(
                "a verified independent recovery archive is required"
            )
        manifest = independent_snapshot(recovery, directory)
        hashes = manifest["blobs"]
        assert isinstance(hashes, list)
        if not set(candidates).issubset(hashes):
            raise VersionUnavailable(
                "recovery archive does not cover deletion candidates"
            )
        for sha256 in candidates:
            inventory[sha256].unlink()
        for path in temporary:
            path.unlink()
        for parent in {inventory[sha].parent for sha in candidates} | {
            p.parent for p in temporary
        }:
            _sync_directory(parent)
    return {
        "schema_version": 1,
        "mode": "apply" if apply else "plan",
        "advisory": not apply,
        "retained_count": len(retained),
        "candidate_sha256": list(candidates),
        "candidate_count": len(candidates),
        "candidate_bytes": sum(sizes.values()),
        "temporary_count": len(temporary),
        "deleted_count": len(candidates) if apply else 0,
        "deleted_bytes": sum(sizes.values()) if apply else 0,
        "temporary_deleted_count": len(temporary) if apply else 0,
    }


def collect(
    directory: Path,
    *,
    apply: bool = False,
    offline: bool = False,
    recovery: Path | None = None,
    snapshots: tuple[Path, ...] = (),
    owned_runtime_sha256: str | None = None,
) -> Object:
    """The operator owns downtime; its executable supplies the owned runtime.

    The optional digest comes from that caller's actual RuntimeSnapshot, never
    workspace metadata. A plan may retain existing bytes but never publish them.
    """
    directory = directory.absolute()
    if owned_runtime_sha256 is not None and not HASH.fullmatch(owned_runtime_sha256):
        raise VersionUnavailable("owned runtime identity is invalid")
    if not apply:
        return _collect(
            directory,
            apply=False,
            recovery=recovery,
            snapshots=snapshots,
            owned_runtime_sha256=owned_runtime_sha256,
        )
    if not offline:
        raise VersionUnavailable("CAS deletion requires a stopped maintenance window")
    with cas_lock(directory / "blobs", exclusive=True):
        return _collect(
            directory,
            apply=True,
            recovery=recovery,
            snapshots=snapshots,
            owned_runtime_sha256=owned_runtime_sha256,
        )
