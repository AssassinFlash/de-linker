"""Publication retries must not acknowledge an unconfirmed directory entry."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from linker_engine.planning.canonical import digest
from linker_engine.planning.storage import Blobs


def test_retry_reconfirms_both_directories_after_publication_fsync_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blobs = Blobs(tmp_path / "blobs")
    content = b"an interrupted but already linked dependency"
    sha256 = digest(content)
    destination = blobs.directory / sha256[:2] / sha256
    fsync = os.fsync

    def interrupted(descriptor: int) -> None:
        if destination.exists() and stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError("fixture: directory sync failed after link")
        fsync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", interrupted)
        with pytest.raises(OSError):
            blobs.put(content)
    assert destination.read_bytes() == content
    synced: set[int] = set()

    def record(descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            synced.add(os.fstat(descriptor).st_ino)
        fsync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", record)
        assert blobs.put(content) == sha256
    assert {blobs.directory.stat().st_ino, destination.parent.stat().st_ino} <= synced


def test_repeated_sync_failure_cannot_acknowledge_existing_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blobs = Blobs(tmp_path / "blobs")
    blobs.put(b"fixture")

    def disk_failure(_: int) -> None:
        raise OSError("fixture: storage still cannot confirm durability")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", disk_failure)
        with pytest.raises(OSError):
            blobs.put(b"fixture")
