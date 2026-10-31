"""Real SQLite retention without a running judge or any external calls."""

from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import tempfile
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie import retention
from linker_genie.log import TurnLog
from linker_genie.quality import worker as quality_worker
from linker_genie.quality.store import Status, Store
from linker_genie.quality.turns import TurnSource
from linker_genie.quality.wordpress import WordPress

NOW = datetime(2026, 10, 31, tzinfo=UTC).timestamp()
CUTOFF = NOW - retention.RETENTION_DAYS * 86400
BEFORE = datetime.fromtimestamp(CUTOFF, UTC).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def root() -> Iterator[Path]:
    # This fixture owns the SQLite files only for the test; unlike pytest's
    # retained tmp_path sessions, TemporaryDirectory removes them in finally.
    with tempfile.TemporaryDirectory(prefix="genie-retention-test-") as directory:
        yield Path(directory)


def _record(
    log: TurnLog, conversation: str = "success", *, failed: bool = False
) -> int:
    return log.record(
        conversation,
        "en",
        not failed,
        ("provider unavailable",) if failed else (),
        failed,
        "deepseek",
        "deepseek-flash",
        [],
        {"blocks": []},
    )


def test_retention_covers_success_failure_cancel_and_crash_but_keeps_recent_evidence(
    root: Path,
) -> None:
    path = root / "turns.sqlite"
    log = TurnLog(path)
    store = Store(root / "judgments.sqlite")
    try:
        for _ in range(retention.DELETE_BATCH + 1):
            _record(log)
        _record(log, "failure", failed=True)
        log._db.execute("UPDATE turns SET created_at = '2000-01-01 00:00:00'")
        for state in ("cancel", "crash"):
            log.start(state, "en")
        log._db.execute("UPDATE turn_starts SET created_at = '2000-01-01 00:00:00'")
        log._db.commit()
        good = _record(log, "recent success")
        bad = _record(log, "recent failure", failed=True)
        active = log.start("active", "en")
        cancelled = log.start("recent cancel", "en")
        boundary = _record(log, "exactly 90 days")
        log._db.execute(
            "UPDATE turns SET created_at = ? WHERE id = ?", (BEFORE, boundary)
        )
        log._db.commit()
        statuses: tuple[Status, ...] = ("judged", "failed", "skipped")
        for turn_id, status in enumerate(statuses, start=1):
            store.save(turn_id, "old", status, 1, {"error": "old evidence"}, CUTOFF - 1)
        store.save(bad, "recent failure", "failed", 1, {"error": "keep failure"}, NOW)
        store.save(boundary, "boundary", "judged", 1, {}, CUTOFF)

        assert retention.sweep(path, root / "judgments.sqlite", NOW)

        assert [
            row[0] for row in log._db.execute("SELECT id FROM turns ORDER BY id")
        ] == [good, bad, boundary]
        assert [
            row[0]
            for row in log._db.execute("SELECT token FROM turn_starts ORDER BY token")
        ] == [active, cancelled]
        assert [
            row[0]
            for row in store._db.execute(
                "SELECT turn_id FROM judgments ORDER BY turn_id"
            )
        ] == [bad, boundary]
        assert store.last_failure() == ("keep failure", NOW)
        # An indexed age predicate, rather than a full scan on every request.
        for table, column in (("turns", "created_at"), ("turn_starts", "created_at")):
            plan = log._db.execute(
                f"EXPLAIN QUERY PLAN SELECT rowid FROM {table} WHERE {column} < ? LIMIT ?",
                (BEFORE, retention.DELETE_BATCH),
            ).fetchone()
            assert "USING COVERING INDEX" in plan[3]
    finally:
        store.close()
        log.close()


def test_legacy_log_can_be_fully_pruned_without_reusing_ids_below_judge_cursor(
    root: Path,
) -> None:
    path = root / "turns.sqlite"
    log = TurnLog(path)
    store = Store(root / "judgments.sqlite")
    try:
        last = _record(log)
        store.set_cursor(last)
        log._db.execute("UPDATE turns SET created_at = '2000-01-01 00:00:00'")
        # The deployed schema has no high-water table yet.
        log._db.execute("DROP TABLE turn_sequence")
        log._db.commit()
        assert retention.sweep(path, root / "judgments.sqlite", NOW)
        assert log._db.execute("SELECT COUNT(*) FROM turns").fetchone() == (0,)
        new = _record(log, "after complete cleanup")
        assert new > last
        assert [
            turn.id for turn in TurnSource(path).after(store.cursor() or 0, 20)
        ] == [new]
        assert store.cursor() == last
    finally:
        store.close()
        log.close()


def test_missing_judge_store_is_not_created_and_no_credentials_are_required(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in (
        "GENIE_JUDGE_TOKEN",
        "GENIE_WP_URL",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    log = TurnLog(root / "turns.sqlite")
    try:
        log.start("crashed", "en")
        log._db.execute("UPDATE turn_starts SET created_at = '2000-01-01 00:00:00'")
        log._db.commit()
        assert retention.sweep(log.path, root / "absent.sqlite", NOW)
        assert log._db.execute("SELECT COUNT(*) FROM turn_starts").fetchone() == (0,)
        assert not (root / "absent.sqlite").exists()
        assert retention.sweep(root / "missing.sqlite", root / "absent.sqlite", NOW)
        assert not (root / "missing.sqlite").exists()
    finally:
        log.close()


def test_active_writer_can_log_between_cleanup_batches_and_shutdown_stops_backlog(
    root: Path,
) -> None:
    log = TurnLog(root / "turns.sqlite")
    paused = threading.Event()
    resume = threading.Event()
    calls = 0

    def stopped() -> bool:
        nonlocal calls
        calls += 1
        # The store check and first deletion have passed; the first batch has
        # committed before the timer checks whether another batch should run.
        if calls == 3:
            paused.set()
            assert resume.wait(2)
            return True
        return False

    try:
        for _ in range(retention.DELETE_BATCH + 1):
            _record(log)
        log._db.execute("UPDATE turns SET created_at = '2000-01-01 00:00:00'")
        log._db.commit()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                retention.sweep, log.path, root / "absent.sqlite", NOW, stopped
            )
            try:
                assert paused.wait(2)
                active = log.start("active while cleanup runs", "en")
                fresh = _record(log, "concurrent success")
            finally:
                resume.set()
            future.result(timeout=2)
        assert log._db.execute(
            "SELECT COUNT(*) FROM turns WHERE created_at < ?", (BEFORE,)
        ).fetchone() == (1,)
        assert log._db.execute(
            "SELECT id FROM turns WHERE id = ?", (fresh,)
        ).fetchone() == (fresh,)
        assert log._db.execute("SELECT token FROM turn_starts").fetchone() == (active,)
        # The next sweep resumes the unprocessed expired row, preserving the
        # concurrent answer rather than holding a writer lock for the backlog.
        assert retention.sweep(log.path, root / "absent.sqlite", NOW)
        assert log._db.execute("SELECT id FROM turns").fetchall() == [(fresh,)]
    finally:
        resume.set()
        log.close()


def test_locked_turn_log_reports_error_but_other_store_still_cleans(
    root: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    log = TurnLog(root / "turns.sqlite")
    store = Store(root / "judgments.sqlite")
    monkeypatch.setattr(retention, "BUSY_TIMEOUT", 0.01)
    try:
        _record(log)
        log._db.execute("UPDATE turns SET created_at = '2000-01-01 00:00:00'")
        log._db.commit()
        store.save(1, "old", "failed", 1, {"error": "old"}, 0)
        log._db.execute("BEGIN IMMEDIATE")
        with caplog.at_level(logging.ERROR, logger="linker_genie.retention"):
            assert not retention.sweep(log.path, root / "judgments.sqlite", NOW)
        assert "database is locked" in caplog.text
        assert store._db.execute("SELECT COUNT(*) FROM judgments").fetchone() == (0,)
        log._db.rollback()
        assert retention.sweep(log.path, root / "judgments.sqlite", NOW)
        assert log._db.execute("SELECT COUNT(*) FROM turns").fetchone() == (0,)
    finally:
        store.close()
        log.close()


@pytest.mark.parametrize(
    "success,interval",
    [(True, retention.PRUNE_EVERY_SECONDS), (False, retention.RETRY_AFTER_SECONDS)],
)
def test_idle_timer_uses_daily_success_and_bounded_error_retry(
    monkeypatch: pytest.MonkeyPatch, success: bool, interval: float
) -> None:
    calls: list[float] = []
    waits: list[float] = []

    async def scenario() -> None:
        stop = asyncio.Event()

        def sweep(*args: Any) -> bool:
            calls.append(args[2])
            return success

        async def wait_for(waiter: Any, *, timeout: float) -> bool:
            waits.append(timeout)
            if len(waits) == 1:
                waiter.close()
                raise TimeoutError
            stop.set()
            return bool(await waiter)

        monkeypatch.setattr(retention, "sweep", sweep)
        monkeypatch.setattr(asyncio, "wait_for", wait_for)
        await retention.run(Path("unused"), Path("unused"), stop, clock=lambda: NOW)

    asyncio.run(scenario())
    assert calls == [NOW, NOW]
    assert waits == [interval, interval]


def test_api_lifespan_cleans_without_requests_and_joins_task_on_exit(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import linker_genie.app as service

    path = root / "turns.sqlite"
    monkeypatch.setenv("GENIE_LOG", str(path))
    monkeypatch.setenv("GENIE_JUDGMENTS", str(root / "custom.sqlite"))
    monkeypatch.delenv("GENIE_JUDGE_TOKEN", raising=False)
    log = TurnLog(path)
    try:
        log.start("cancelled before restart", "de")
        log._db.execute("UPDATE turn_starts SET created_at = '2000-01-01 00:00:00'")
        log._db.commit()
        completed = threading.Event()
        original = retention.sweep

        def sweep(*args: Any) -> bool:
            assert args[1] == root / "custom.sqlite"
            result = original(*args)
            completed.set()
            return result

        monkeypatch.setattr(retention, "sweep", sweep)

        async def scenario() -> None:
            async with service.app.router.lifespan_context(service.app):
                assert await asyncio.to_thread(completed.wait, 2)
                assert log._db.execute(
                    "SELECT COUNT(*) FROM turn_starts"
                ).fetchone() == (0,)
            assert not [
                task
                for task in asyncio.all_tasks()
                if task.get_name() == "genie-log-retention"
            ]

        asyncio.run(scenario())
        assert not (root / "custom.sqlite").exists()
    finally:
        log.close()


def test_the_vps_matches_the_sites_existing_privacy_term() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "plugins/linker-tools/includes/Genie/Retention.php"
    ).read_text()
    match = re.search(r"const RETENTION_DAYS = (\d+);", source)
    assert match is not None
    assert int(match.group(1)) == retention.RETENTION_DAYS


@pytest.mark.parametrize("custom", [True, False])
def test_judge_cli_cleans_legacy_custom_db_without_duplicating_api_cleanup(
    root: Path, monkeypatch: pytest.MonkeyPatch, custom: bool
) -> None:
    path = root / ("custom.sqlite" if custom else "judgments.sqlite")
    store = Store(path)
    try:
        store.save(1, "old", "failed", 3, {"error": "expired"}, 0)
        store.save(2, "recent", "failed", 3, {"error": "recent"}, NOW)
        store.mark_pushed([1, 2])
    finally:
        store.close()
    monkeypatch.delenv("GENIE_JUDGMENTS", raising=False)
    monkeypatch.setenv("GENIE_JUDGE_TOKEN", "fixture-token")
    monkeypatch.setattr(quality_worker, "openrouter_credentials", lambda: None)
    monkeypatch.setattr(quality_worker, "deepseek_credentials", lambda: None)
    monkeypatch.setattr(time, "time", lambda: NOW)
    site = WordPress(
        "https://site.test",
        "fixture-token",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"stored": []})
        ),
    )
    monkeypatch.setattr(quality_worker, "WordPress", lambda *_: site)
    opened: list[Store] = []

    def open_store(path: Path) -> Store:
        result = Store(path)
        opened.append(result)
        return result

    monkeypatch.setattr(quality_worker, "Store", open_store)
    try:
        assert (
            quality_worker.main(
                [
                    "--log",
                    str(root / "turns.sqlite"),
                    "--db",
                    str(path),
                    "--wp",
                    "https://site.test",
                    "--once",
                ]
            )
            == 0
        )
        assert [
            row[0]
            for row in opened[0]._db.execute(
                "SELECT turn_id FROM judgments ORDER BY turn_id"
            )
        ] == ([2] if custom else [1, 2])
        assert not (root / "turns.sqlite").exists()
    finally:
        for database in opened:
            database.close()


@pytest.mark.parametrize("initially_locked", [False, True])
def test_custom_worker_respects_daily_sweep_and_lock_retry_intervals(
    root: Path, monkeypatch: pytest.MonkeyPatch, initially_locked: bool
) -> None:
    path = root / "custom.sqlite"
    store = Store(path)
    blocker = sqlite3.connect(path)
    site = WordPress(
        "https://site.test",
        "fixture-token",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"stored": []})
        ),
    )
    monkeypatch.setattr(retention, "BUSY_TIMEOUT", 0.01)
    try:
        store.set_cursor(0)
        store.save(1, "old", "failed", 3, {"error": "expired"}, 0)
        store.mark_pushed([1])
        if initially_locked:
            blocker.execute("BEGIN IMMEDIATE")
        worker = quality_worker.Worker(
            TurnSource(root / "absent.sqlite"),
            store,
            site,
            custom_judgments=path,
        )
        worker.cycle(NOW)
        blocker.rollback()
        if not initially_locked:
            assert store._db.execute("SELECT COUNT(*) FROM judgments").fetchone() == (
                0,
            )
            # New expired data after a successful sweep must wait for the next
            # daily pass, rather than rescanning this custom store every poll.
            store.save(2, "also old", "failed", 3, {"error": "expired"}, 0)
            store.mark_pushed([2])
        worker.cycle(NOW + quality_worker.POLL_SECONDS)
        assert store._db.execute("SELECT COUNT(*) FROM judgments").fetchone() == (1,)
        interval = (
            retention.RETRY_AFTER_SECONDS
            if initially_locked
            else retention.PRUNE_EVERY_SECONDS
        )
        worker.cycle(NOW + interval)
        assert store._db.execute("SELECT COUNT(*) FROM judgments").fetchone() == (0,)
    finally:
        blocker.close()
        store.close()
