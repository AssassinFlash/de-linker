"""Native SQLite expiry must remain visible without blocking Woo preparation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from test_sync_feed import Restarter, feed_document, load_sync
from test_sync_feed import feed_url as feed_url

from linker_engine.selections import Selections


def receipts(cache: Path) -> Path:
    path = Selections(cache / "private").path
    with sqlite3.connect(path) as database:
        database.executemany(
            "INSERT INTO selections VALUES (?, ?, ?, ?, ?)",
            [
                ("expired", "input-a", "residential", "{}", 9999),
                ("boundary", "input-b", "residential", "{}", 10000),
                ("current", "input-c", "commercial", "{}", 20000),
            ],
        )
    return path


def test_minute_pass_without_pending_job_still_removes_only_expired_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync = load_sync()
    state = tmp_path / "state"
    cache = state / "cache"
    path = receipts(cache)
    original = cache / "retained-project-original.pdf"
    original.write_bytes(b"unchanged private original")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(cache))
    monkeypatch.setattr(sync.time, "time", lambda: 10000)
    lines: list[str] = []
    monkeypatch.setattr(sync, "log", lines.append)
    real_cleanup, real_sync = sync.cleanup_receipts, sync.sync
    monkeypatch.setattr(
        sync, "cleanup_receipts", lambda: real_cleanup(state_root=state)
    )
    monkeypatch.setattr(sync, "job_request", lambda action, payload: {"job": None})
    restarts = Restarter()

    def prepare(**kwargs: Any) -> int:
        return int(
            real_sync(
                feed_target=state / "feed.json",
                compatibility_target=state / "compatibility.json",
                restart=restarts,
                log=lines.append,
                **kwargs,
            )
        )

    monkeypatch.setattr(sync, "sync", prepare)
    assert sync.main([]) == 0
    with sqlite3.connect(path) as database:
        assert database.execute(
            "SELECT fingerprint FROM selections ORDER BY fingerprint"
        ).fetchall() == [("boundary",), ("current",)]
    assert original.read_bytes() == b"unchanged private original"
    assert restarts.calls == 0
    assert any("deleted 1 expired" in line for line in lines)
    assert "no pending engineering preparation" in lines


def test_readonly_gc_fails_visibly_but_still_publishes_and_acknowledges_current_job(
    tmp_path: Path, feed_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync = load_sync()
    state = tmp_path / "state"
    cache = state / "cache"
    path = receipts(cache)
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(cache))
    monkeypatch.setattr(sync.time, "time", lambda: 10000)
    connect = sqlite3.connect

    def readonly(
        database: str | Path, *, uri: bool = False, timeout: float = 5.0
    ) -> sqlite3.Connection:
        if database == f"{path.as_uri()}?mode=rw":
            return connect(f"{path.as_uri()}?mode=ro", uri=True)
        return connect(database, uri=uri, timeout=timeout)

    monkeypatch.setattr(sync.sqlite3, "connect", readonly)
    document = feed_document()
    (tmp_path / "feed.json").write_text(json.dumps(document))
    lines: list[str] = []
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(sync, "log", lines.append)
    assert not sync.cache_preflight(state_root=state)
    real_cleanup, real_sync = sync.cleanup_receipts, sync.sync
    monkeypatch.setattr(
        sync, "cleanup_receipts", lambda: real_cleanup(state_root=state)
    )

    def job(action: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((action, payload))
        return (
            {
                "job": {
                    "job_id": "current",
                    "lease_token": "synthetic",
                    "source_revision": document["source_revision"],
                }
            }
            if action == "claim"
            else {}
        )

    monkeypatch.setattr(sync, "job_request", job)
    restarts = Restarter()

    def loaded() -> dict[str, Any]:
        actual = json.loads((state / "feed.json").read_text())
        return {
            "source_revision": actual["source_revision"],
            "compatibility_revision": actual["compatibility_revision"],
        }

    def prepare(**kwargs: Any) -> int:
        return int(
            real_sync(
                feed_url=feed_url,
                feed_target=state / "feed.json",
                compatibility_target=state / "compatibility.json",
                probe_python=sync.sys.executable,
                restart=restarts,
                loaded=loaded,
                log=lines.append,
                **kwargs,
            )
        )

    monkeypatch.setattr(sync, "sync", prepare)
    assert sync.main([]) == 1, (
        "the unit must report failed retention despite preparation"
    )
    assert restarts.calls == 1
    assert (state / "feed.json").is_symlink()
    assert calls[-1][0] == "ack" and calls[-1][1]["status"] == "ready"
    assert any("receipt retention failed" in line for line in lines)
    assert any("OperationalError" in line for line in lines)
    with connect(path) as database:
        assert database.execute("SELECT COUNT(*) FROM selections").fetchone() == (3,)


@pytest.mark.parametrize(
    "configured", [None, "", "/root/.cache/linker-engine", "relative/cache"]
)
def test_invisible_or_implicit_cache_is_not_claimed_as_retention_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured: str | None
) -> None:
    sync = load_sync()
    if configured is None:
        monkeypatch.delenv("LINKER_ENGINE_CACHE", raising=False)
    else:
        monkeypatch.setenv("LINKER_ENGINE_CACHE", configured)
    lines: list[str] = []
    monkeypatch.setattr(sync, "log", lines.append)
    assert not sync.cleanup_receipts(state_root=tmp_path)
    assert any("receipt retention failed" in line for line in lines)
    assert not list(tmp_path.iterdir())


def test_preflight_rejects_cache_symlink_outside_writable_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync = load_sync()
    state, outside = tmp_path / "state", tmp_path / "outside"
    state.mkdir()
    outside.mkdir()
    (state / "cache").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(state / "cache"))
    monkeypatch.setattr(sync, "log", lambda message: None)
    assert not sync.cache_preflight(state_root=state)
    assert not list(outside.iterdir())


def test_preflight_checks_future_database_writes_and_removes_its_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync = load_sync()
    cache = tmp_path / "cache"
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(cache))
    lines: list[str] = []
    monkeypatch.setattr(sync, "log", lines.append)
    assert sync.cache_preflight(state_root=tmp_path)
    assert (cache / "private").is_dir()
    assert not list((cache / "private").iterdir())
    assert sync.cleanup_receipts(state_root=tmp_path)
    assert any("database not yet created" in line for line in lines)


def test_preflight_checks_existing_database_write_permission_without_expiring_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync = load_sync()
    cache = tmp_path / "cache"
    path = receipts(cache)
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(cache))
    lines: list[str] = []
    monkeypatch.setattr(sync, "log", lines.append)
    assert sync.cache_preflight(state_root=tmp_path)
    with sqlite3.connect(path) as database:
        assert database.execute("SELECT COUNT(*) FROM selections").fetchone() == (3,)
    assert list((cache / "private").iterdir()) == [path]
