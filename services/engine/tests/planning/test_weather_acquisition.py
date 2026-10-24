"""Actual SQLite/CAS/HTTP seam; no live provider call or owned publication."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import requests

from linker_engine.planning.canonical import encode
from linker_engine.planning.errors import InvalidInput, LeaseLost
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_acquisition import WeatherAcquisition
from linker_engine.planning.weather_fetch_errors import (
    WeatherPollingLimit,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
)
from linker_engine.planning.weather_journal import (
    WeatherDeadlineExceeded,
    WeatherJournal,
    WeatherStartUnknown,
)
from linker_engine.planning.worker import Control
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_apify_weather_client import Reply, client, effective, provider, record
from .test_pvgis_tmy import raw
from .test_weather_journal import operation, plan, remote


class AdvancingControl(Control):
    def __init__(self, clock: Clock) -> None:
        super().__init__()
        self.clock = clock

    def wait(self, seconds: float) -> None:
        self.checkpoint()
        self.clock.advance(seconds)


def download(nonce: str) -> list[Reply]:
    return [
        Reply(200, encode(effective(nonce))),
        Reply(200, encode([record()])),
        Reply(200, raw()),
    ]


def test_real_capture_is_immutable_and_reused_without_new_network_after_deadline(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, adapter = client(
        Reply(201, provider("READY")), Reply(200, provider()), *download(intent.nonce)
    )
    try:
        acquisition = WeatherAcquisition(journal, source)
        acquired = acquisition.acquire(lease, plan(), Control())
        assert acquired.content == raw()
        assert journal.view(owner, run.id)["acquisition_state"] == "captured"
        original_capture = journal.current(intent).capture_sha256
        clock.advance(61)
        assert acquisition.acquire(lease, plan(), Control()) == acquired
        assert (
            len(adapter.calls) == 5
            and journal.current(intent).capture_sha256 == original_capture
        )
        assert workspace.run(owner, run.id).state == "running"
        assert workspace.run(owner, run.id).result is None
        with workspace.database.read() as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0]
                == 0
            )
    finally:
        source.transport.close()


def test_transient_read_reuses_acknowledged_run_without_second_start(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, first = client(
        Reply(201, provider("READY")),
        Reply(0, b"", error=requests.ConnectionError("private sentinel")),
    )
    try:
        with pytest.raises(WeatherProviderUnavailable):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        assert [call.method for call in first.calls] == ["POST", "GET"]
    finally:
        source.transport.close()
    source, second = client(Reply(200, provider()), *download(intent.nonce))
    try:
        assert (
            WeatherAcquisition(journal, source)
            .acquire(lease, plan(), Control())
            .content
            == raw()
        )
        assert [call.method for call in second.calls] == ["GET"] * 4
        assert journal.current(intent).remote_run_id == remote().id
    finally:
        source.transport.close()


def test_lost_ack_blocks_repeat_and_unique_nonce_recovers_same_provider_run(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, first = client(Reply(0, b"", error=requests.ConnectionError("lost reply")))
    try:
        acquisition = WeatherAcquisition(journal, source)
        with pytest.raises(WeatherStartUnknown):
            acquisition.acquire(lease, plan(), Control())
        with pytest.raises(WeatherStartUnknown):
            acquisition.acquire(lease, plan(), Control())
        assert len(first.calls) == 1 and not journal.current(intent).may_start
    finally:
        source.transport.close()
    source, second = client(
        Reply(200, provider("READY")),
        Reply(200, encode(effective(intent.nonce))),
        Reply(200, provider()),
        *download(intent.nonce),
    )
    try:
        acquisition = WeatherAcquisition(journal, source)
        recovered = acquisition.recover_acknowledgement(intent, remote().id)
        assert recovered.remote_run_id == remote().id
        assert acquisition.acquire(lease, plan(), Control()).content == raw()
        assert all(call.method == "GET" for call in second.calls)
    finally:
        source.transport.close()


def test_identical_weather_url_without_unique_nonce_cannot_be_adopted(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    source, adapter = client(
        Reply(200, provider()), Reply(200, encode(effective("a" * 32)))
    )
    try:
        with pytest.raises(WeatherResponseInvalid):
            WeatherAcquisition(journal, source).recover_acknowledgement(
                intent, remote().id
            )
        assert journal.current(intent).remote_run_id is None and len(adapter.calls) == 2
    finally:
        source.transport.close()


def test_late_ack_after_cancel_is_retained_then_abort_observation_remains_truthful(
    workspace: Workspace, owner: Actor
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, adapter = client(
        Reply(201, provider("READY"), after=lambda: workspace.cancel(owner, run.id)),
        Reply(200, provider("ABORTING")),
    )
    try:
        with pytest.raises(LeaseLost):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        current = journal.current(intent)
        assert current.remote_run_id == remote().id and current.abort_sha256 is not None
        assert journal.view(owner, run.id)["acquisition_state"] == "ABORTING"
        assert (
            workspace.run(owner, run.id).state == "cancelled"
            and current.capture_sha256 is None
        )
        assert [call.method for call in adapter.calls] == ["POST", "POST"]
        assert (adapter.calls[-1].url or "").endswith("/abort?gracefully=false")
    finally:
        source.transport.close()


def test_old_lease_does_not_abort_a_run_now_owned_by_replacement(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())

    def replace_lease() -> None:
        clock.advance(1)
        assert (
            Jobs(workspace).claim("replacement", kinds=("evaluate",), lease_seconds=300)
            is not None
        )

    with workspace.database.transaction() as connection:
        connection.execute(
            "UPDATE jobs SET lease_until=? WHERE id=?", (clock.value + 0.5, lease.id)
        )
    source, adapter = client(Reply(201, provider("READY"), after=replace_lease))
    try:
        with pytest.raises(LeaseLost):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        assert len(adapter.calls) == 1
        assert journal.current(intent).remote_run_id == remote().id
        assert journal.current(intent).abort_sha256 is None
    finally:
        source.transport.close()


def test_persisted_deadline_attempts_known_abort_without_erasing_original_failure(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, adapter = client(
        Reply(201, provider("READY")),
        Reply(200, provider("RUNNING"), after=lambda: clock.advance(61)),
        Reply(200, provider("ABORTING")),
    )
    try:
        with pytest.raises(WeatherDeadlineExceeded):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        assert journal.current(intent).deadline_at == intent.deadline_at
        assert journal.view(owner, run.id)["acquisition_state"] == "ABORTING"
        assert (
            len(adapter.calls) == 3 and journal.current(intent).capture_sha256 is None
        )
    finally:
        source.transport.close()


def test_polling_cap_has_one_start_and_one_abort_with_interruptible_waits(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    source, adapter = client(
        Reply(201, provider("READY")),
        *[Reply(200, provider("RUNNING")) for _ in range(10)],
        Reply(200, provider("ABORTED")),
    )
    try:
        with pytest.raises(WeatherPollingLimit):
            WeatherAcquisition(journal, source).acquire(
                lease, plan(), AdvancingControl(clock)
            )
        assert len(adapter.calls) == 12
        assert sum(call.method == "POST" for call in adapter.calls) == 2
    finally:
        source.transport.close()


def test_abort_failure_keeps_known_remote_and_does_not_replace_cancellation(
    workspace: Workspace, owner: Actor, caplog: pytest.LogCaptureFixture
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, _ = client(
        Reply(201, provider("READY"), after=lambda: workspace.cancel(owner, run.id)),
        Reply(500, b"private sentinel"),
    )
    try:
        with pytest.raises(LeaseLost):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        current = journal.current(intent)
        assert current.remote_run_id == remote().id and current.abort_sha256 is None
        assert "unconfirmed" in caplog.text and "private sentinel" not in caplog.text
    finally:
        source.transport.close()


def test_control_wait_observes_revocation_without_sleeping() -> None:
    control = Control()
    control.revoke()
    with pytest.raises(LeaseLost):
        control.wait(60)


def test_unexpected_abort_failure_cannot_mask_original_cancellation(
    workspace: Workspace, owner: Actor, caplog: pytest.LogCaptureFixture
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    source, _ = client(
        Reply(201, provider("READY"), after=lambda: workspace.cancel(owner, run.id)),
        Reply(0, b"", error=RuntimeError("private unexpected failure sentinel")),
    )
    try:
        with pytest.raises(LeaseLost):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        assert journal.current(intent).remote_run_id == remote().id
        assert journal.current(intent).abort_sha256 is None
        assert "unexpected_cleanup_failure" in caplog.text
        assert "private unexpected failure sentinel" not in caplog.text
    finally:
        source.transport.close()


def test_database_read_failure_cannot_replace_lease_loss_or_authorize_abort(
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    control = Control()

    @contextmanager
    def unavailable() -> Iterator[sqlite3.Connection]:
        raise sqlite3.OperationalError("private outage sentinel")
        yield  # pragma: no cover - retain the context-manager shape

    def cancelled_with_read_outage() -> None:
        workspace.cancel(owner, run.id)
        control.revoke()
        monkeypatch.setattr(workspace.database, "read", unavailable)

    source, adapter = client(
        Reply(201, provider("READY"), after=cancelled_with_read_outage)
    )
    try:
        with pytest.raises(LeaseLost):
            WeatherAcquisition(journal, source).acquire(lease, plan(), control)
        monkeypatch.undo()
        assert (
            len(adapter.calls) == 1
            and journal.current(intent).remote_run_id == remote().id
        )
        assert journal.current(intent).abort_sha256 is None
        assert (
            "unexpected_cleanup_failure" in caplog.text
            and "private outage sentinel" not in caplog.text
        )
    finally:
        monkeypatch.undo()
        source.transport.close()


def test_full_download_with_invalid_source_units_is_not_retained_or_published(
    workspace: Workspace,
    owner: Actor,
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    invalid = json.loads(raw())
    invalid["meta"]["outputs"]["tmy_hourly"]["variables"]["SP"]["units"] = "kPa"
    source, adapter = client(
        Reply(201, provider("SUCCEEDED")),
        Reply(200, encode(effective(intent.nonce))),
        Reply(200, encode([record()])),
        Reply(200, encode(invalid)),
    )
    try:
        with pytest.raises(InvalidInput):
            WeatherAcquisition(journal, source).acquire(lease, plan(), Control())
        assert len(adapter.calls) == 4
        assert journal.current(intent).capture_sha256 is None
        assert workspace.run(owner, run.id).result is None
        with workspace.database.read() as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0]
                == 0
            )
    finally:
        source.transport.close()
