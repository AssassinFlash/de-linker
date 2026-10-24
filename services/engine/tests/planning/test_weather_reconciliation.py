"""Real queued recovery/leases/CAS; provider replies are simulated, no Actor starts."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.apify_transport import ApifyTransport
from linker_engine.planning.canonical import encode
from linker_engine.planning.errors import (
    Conflict,
    InvalidInput,
    LeaseLost,
    ServiceDraining,
    VersionUnavailable,
)
from linker_engine.planning.execution_control import ExecutionControl
from linker_engine.planning.execution_identity import storage_binding
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_host import main as weather_main
from linker_engine.planning.weather_journal import WeatherJournal
from linker_engine.planning.weather_kernel import WeatherKernel
from linker_engine.planning.weather_operator import WeatherOperator
from linker_engine.planning.weather_reconciliation import WeatherReconciliation
from linker_engine.planning.weather_submission import submission
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_apify_weather_client import (
    Reply,
    SequenceAdapter,
    effective,
    provider,
    record,
)
from .test_pvgis_tmy import raw
from .test_weather_journal import plan, remote, source
from .test_weather_kernel import (
    asset_count,
    services,
    source_inputs,
)
from .test_weather_kernel import (
    worker as compute_worker,
)
from .test_worker_host import configuration, launch, ready_generation, stop, wait_for

OPERATOR = Actor("team", "recovery-fixture")


def failed_start(
    workspace: Workspace,
    owner: Actor,
    adapter: SequenceAdapter,
    *,
    retry_after: float | None = None,
):
    project = workspace.create(
        owner, "Recovery fixture", source_inputs(), key="project"
    )
    weather, energy = services(workspace, adapter)
    run = weather.evaluate(owner, project.id, project.revision, key="weather")
    jobs = Jobs(workspace)
    lease = jobs.claim("producer", kinds=("evaluate",), lease_seconds=300)
    assert lease
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    jobs.fail(
        lease,
        {"code": "weather_start_unknown", "retryable": retry_after is not None},
        retry_after=retry_after,
    )
    return project, run, weather, energy, journal, intent


def maintenance(workspace: Workspace, weather):
    return Worker(
        Jobs(workspace),
        "reconciliation",
        {
            "reconcile_weather": WeatherReconciliation(
                workspace, connection=weather.kernel.transport
            )
        },
        lease_seconds=300,
        heartbeat_seconds=1,
        retry_seconds=1,
    )


def job(workspace: Workspace, job_id: str):
    with workspace.database.read() as connection:
        return dict(
            connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        )


def test_late_verified_capture_then_explicit_remaining_attempt_publishes_without_another_start(
    workspace: Workspace, owner: Actor, clock: Clock, tmp_path: Path
) -> None:
    adapter = SequenceAdapter()
    project, run, weather, energy, journal, intent = failed_start(
        workspace, owner, adapter
    )
    clock.advance(61)
    control = ExecutionControl(workspace)
    control.set_draining(True)
    assert control.status()["pending"] == 0 and control.status()["quiescent"] is False
    assert control.status()["remote_weather"]["unknown"] == 1
    operator = WeatherOperator(workspace)
    receipt = operator.admit(
        OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="ack"
    )
    assert (
        operator.admit(
            OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="ack"
        )
        == receipt
    )
    assert adapter.calls == [] and control.status()["pending"] == 1
    adapter.replies.extend(
        [Reply(200, provider()), Reply(200, encode(effective(intent.nonce)))]
    )
    assert maintenance(workspace, weather).run_once()
    assert job(workspace, receipt["job_id"])["state"] == "succeeded"
    assert (
        workspace.run(owner, run.id).state == "failed"
        and workspace.run(owner, run.id).result is None
    )
    assert control.status()["quiescent"] is True
    capture = operator.admit(OPERATOR, run.id, "capture", key="capture")
    adapter.replies.extend(
        [
            Reply(200, encode(effective(intent.nonce))),
            Reply(200, encode([record()])),
            Reply(200, raw()),
        ]
    )
    assert maintenance(workspace, weather).run_once()
    assert job(workspace, capture["job_id"])["state"] == "succeeded"
    assert journal.captured_source(intent).content == raw()
    assert (
        journal.current(intent).deadline_at == intent.deadline_at
        and asset_count(workspace) == 0
    )
    with pytest.raises(ServiceDraining):
        operator.resume(OPERATOR, run.id, weather.kernel, key="resume")
    control.set_draining(False)
    resumed = operator.resume(OPERATOR, run.id, weather.kernel, key="resume")
    assert resumed["previous_attempt"] == 1 and resumed["max_attempts"] == 2
    assert operator.resume(OPERATOR, run.id, None, key="resume") == resumed
    assert compute_worker(workspace, service_registry(energy, None, weather)).run_once()
    assert (
        workspace.run(owner, run.id).state == "succeeded"
        and asset_count(workspace) == 1
    )
    assert workspace.get(owner, project.id).inputs == project.inputs
    assert len(adapter.calls) == 5 and all(
        call.method == "GET" for call in adapter.calls
    )
    archive.backup(workspace, tmp_path / "backup")
    restored = archive.restore(tmp_path / "backup", tmp_path / "restored")
    assert (
        WeatherOperator(restored).inspect(run.id)["capture_sha256"]
        == journal.current(intent).capture_sha256
    )
    assert (
        WeatherOperator(restored).resume(OPERATOR, run.id, None, key="resume")
        == resumed
    )
    # This failure is now reachable only through the immutable resume receipt.
    previous_failure = resumed["dependencies"]["previous_failure"]
    (workspace.blobs.directory / previous_failure[:2] / previous_failure).unlink()
    with pytest.raises(VersionUnavailable):
        archive.backup(workspace, tmp_path / "missing-receipt-child")


@pytest.mark.parametrize("status", ["FAILED", "ABORTED"])
def test_acknowledgement_retains_exact_verified_inputs_without_a_capture(
    workspace: Workspace, owner: Actor, tmp_path: Path, status
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    receipt = WeatherOperator(workspace).admit(
        OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="ack"
    )
    effective_original = (
        b"\n" + json.dumps(effective(intent.nonce), indent=2).encode() + b"\n"
    )
    adapter.replies.extend(
        [Reply(200, provider(status)), Reply(200, effective_original)]
    )
    assert maintenance(workspace, weather).run_once()
    row = job(workspace, receipt["job_id"])
    assert row["state"] == "succeeded"
    output = workspace.blobs.object(row["output_sha256"])
    dependencies = output["dependencies"]
    assert (
        workspace.blobs.read(dependencies["effective_input_original"])
        == effective_original
    )
    assert workspace.blobs.object(
        dependencies["submitted_input_original"]
    ) == submission(plan(), intent.nonce)
    assert (
        journal.current(intent).capture_sha256 is None and asset_count(workspace) == 0
    )
    assert workspace.run(owner, run.id).state == "failed"
    assert len(adapter.calls) == 2 and all(c.method == "GET" for c in adapter.calls)
    archive.backup(workspace, tmp_path / "backup")
    restored = archive.restore(tmp_path / "backup", tmp_path / "restored")
    restored_row = job(restored, receipt["job_id"])
    assert restored.blobs.object(restored_row["output_sha256"]) == output
    assert (
        restored.blobs.read(dependencies["effective_input_original"])
        == effective_original
    )
    sha = dependencies["effective_input_original"]
    (workspace.blobs.directory / sha[:2] / sha).unlink()
    with pytest.raises(VersionUnavailable):
        archive.backup(workspace, tmp_path / "missing-verified-input")


def test_mismatched_recovery_nonce_cannot_acknowledge_or_start_anything(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    receipt = WeatherOperator(workspace).admit(
        OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="wrong"
    )
    adapter.replies.extend(
        [Reply(200, provider()), Reply(200, encode(effective("a" * 32)))]
    )
    assert maintenance(workspace, weather).run_once()
    assert job(workspace, receipt["job_id"])["state"] == "failed"
    assert journal.current(intent).remote_run_id is None
    assert (
        workspace.run(owner, run.id).state == "failed" and asset_count(workspace) == 0
    )
    assert len(adapter.calls) == 2 and all(c.method == "GET" for c in adapter.calls)


def test_pending_reconciliation_is_unique_and_receipt_conflicts_are_atomic(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, run, _, _, _, _ = failed_start(workspace, owner, adapter)
    operator = WeatherOperator(workspace)
    first = operator.admit(
        OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="first"
    )
    with pytest.raises(Conflict):
        operator.admit(
            OPERATOR, run.id, "acknowledge", provider_run_id=remote().id, key="another"
        )
    with pytest.raises(Conflict):
        operator.admit(
            OPERATOR, run.id, "acknowledge", provider_run_id="wrongRun", key="first"
        )
    with pytest.raises(InvalidInput):
        operator.admit(
            owner, run.id, "acknowledge", provider_run_id=remote().id, key="user"
        )
    with workspace.database.read() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE kind='reconcile_weather'"
            ).fetchone()[0]
            == 1
        )
    assert job(workspace, first["job_id"])["state"] == "queued" and adapter.calls == []


def test_stop_observes_abort_terminal_without_changing_cancelled_original(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(
        workspace, owner, adapter, retry_after=0
    )
    journal.acknowledge(intent, remote("RUNNING"))
    workspace.cancel(owner, run.id)
    receipt = WeatherOperator(workspace).admit(OPERATOR, run.id, "stop", key="stop")
    # A repeated customer cancellation cannot erase the operator job.
    workspace.cancel(owner, run.id)
    adapter.replies.extend(
        [
            Reply(200, provider("RUNNING")),
            Reply(200, provider("ABORTING")),
            Reply(200, provider("ABORTED")),
        ]
    )
    assert maintenance(workspace, weather).run_once()
    assert job(workspace, receipt["job_id"])["state"] == "succeeded"
    assert journal.observation(intent).status == "ABORTED"
    assert (
        workspace.run(owner, run.id).state == "cancelled"
        and workspace.run(owner, run.id).result is None
    )
    assert asset_count(workspace) == 0 and len(adapter.calls) == 3
    assert all("/acts/" not in c.url for c in adapter.calls)
    with pytest.raises(Conflict):
        WeatherOperator(workspace).resume(
            OPERATOR, run.id, weather.kernel, key="forbidden"
        )


def test_replaced_recovery_lease_cannot_enter_abort_after_journal_observation(
    workspace: Workspace,
    owner: Actor,
    clock: Clock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("RUNNING"))
    receipt = WeatherOperator(workspace).admit(OPERATOR, run.id, "stop", key="stop")
    jobs = Jobs(workspace)
    lease = jobs.claim("old-recovery", kinds=("reconcile_weather",), lease_seconds=1)
    assert lease and lease.id == receipt["job_id"]
    observe = WeatherJournal.observe

    def observe_then_replace(self, current, observed):
        retained = observe(self, current, observed)
        clock.advance(2)
        replacement = jobs.claim(
            "replacement", kinds=("reconcile_weather",), lease_seconds=60
        )
        assert replacement and replacement.id == lease.id and replacement.attempt == 2
        return retained

    monkeypatch.setattr(WeatherJournal, "observe", observe_then_replace)
    adapter.replies.append(Reply(200, provider("RUNNING")))
    with pytest.raises(LeaseLost):
        WeatherReconciliation(workspace, connection=weather.kernel.transport)(
            lease, Control()
        )
    assert len(adapter.calls) == 1 and adapter.calls[0].method == "GET"
    assert journal.current(intent).abort_sha256 is None
    row = job(workspace, receipt["job_id"])
    assert row["worker"] == "replacement" and row["state"] == "running"
    assert (
        workspace.run(owner, run.id).state == "failed" and asset_count(workspace) == 0
    )


def test_recovery_deadline_survives_retry_and_does_not_issue_provider_requests(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("RUNNING"))
    receipt = WeatherOperator(workspace).admit(
        OPERATOR, run.id, "observe", key="observe"
    )
    jobs = Jobs(workspace)
    first = jobs.claim("lost-recovery", kinds=("reconcile_weather",), lease_seconds=1)
    assert first
    clock.advance(61)
    assert maintenance(workspace, weather).run_once()
    row = job(workspace, receipt["job_id"])
    assert row["attempt"] == 2 and row["state"] == "failed" and adapter.calls == []
    assert (
        workspace.blobs.object(row["error_sha256"])["code"]
        == "weather_deadline_exceeded"
    )


def test_resume_cannot_reset_attempts_deadline_or_runtime(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    operator = WeatherOperator(workspace)
    with pytest.raises(Conflict, match="verified provider"):
        operator.resume(OPERATOR, run.id, weather.kernel, key="unknown")
    journal.acknowledge(intent, remote("RUNNING"))
    with pytest.raises(VersionUnavailable):
        operator.resume(OPERATOR, run.id, None, key="disabled")
    clock.advance(61)
    with pytest.raises(Conflict, match="deadline"):
        operator.resume(OPERATOR, run.id, weather.kernel, key="expired")
    assert workspace.run(owner, run.id).state == "failed" and adapter.calls == []


def test_aborting_is_unresolved_and_missing_terminal_evidence_fails_closed(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, _, _, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("RUNNING"))
    journal.abort_reply(intent, remote("ABORTING"))
    control = ExecutionControl(workspace)
    control.set_draining(True)
    state = control.status()
    assert (
        state["pending"] == 0
        and state["remote_weather"]["active"] == 1
        and state["quiescent"] is False
    )
    final = journal.observe(intent, remote("ABORTED"))
    assert control.status()["quiescent"] is True
    (
        workspace.blobs.directory
        / final.observation_sha256[:2]
        / final.observation_sha256
    ).unlink()
    with pytest.raises(VersionUnavailable):
        control.status()


def test_explicit_resume_keeps_exhausted_budget_and_rejects_changed_executor(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, run, weather, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("RUNNING"))
    operator = WeatherOperator(workspace)
    changed = WeatherKernel(
        workspace,
        plan().limits.model_copy(update={"max_polls": 11}),
        credential=lambda: "fixture-only",
        adapter_factory=lambda: adapter,
    )
    with pytest.raises(VersionUnavailable):
        operator.resume(OPERATOR, run.id, changed, key="changed")
    receipt = operator.resume(OPERATOR, run.id, weather.kernel, key="last-attempt")
    lease = Jobs(workspace).claim(
        "last-attempt", kinds=("evaluate",), lease_seconds=300
    )
    assert lease and lease.attempt == 2
    Jobs(workspace).fail(
        lease, {"code": "weather_read_failed", "retryable": False}, retry_after=None
    )
    with pytest.raises(Conflict, match="exhausted"):
        operator.resume(OPERATOR, run.id, weather.kernel, key="exhausted")
    assert operator.resume(OPERATOR, run.id, None, key="last-attempt") == receipt
    assert workspace.run(owner, run.id).state == "failed" and adapter.calls == []


@pytest.mark.parametrize("action", ["stop", "capture"])
def test_destructive_recovery_requires_an_inactive_producer(
    workspace: Workspace, owner: Actor, action
) -> None:
    adapter = SequenceAdapter()
    _, run, _, _, journal, intent = failed_start(
        workspace, owner, adapter, retry_after=0
    )
    journal.acknowledge(intent, remote("RUNNING"))
    with pytest.raises(Conflict, match="inactive terminal"):
        WeatherOperator(workspace).admit(OPERATOR, run.id, action, key="active")
    assert workspace.run(owner, run.id).state == "retry_wait" and adapter.calls == []


def test_private_cli_queues_exact_receipt_without_provider_work(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    adapter = SequenceAdapter()
    _, run, _, _, _, _ = failed_start(workspace, owner, adapter)
    settings = configuration(tmp_path).model_copy(
        update={"directory": str(workspace.database.path.parent)}
    )
    config_file = tmp_path / "operator-runtime.json"
    config_file.write_text(settings.model_dump_json())
    monkeypatch.setenv("LINKER_PLANNER_CONFIG", str(config_file))
    args = [
        "acknowledge",
        "--run-id",
        run.id,
        "--provider-run-id",
        remote().id,
        "--key",
        "cli-ack",
        "--expected-storage",
        storage_binding(workspace.database.path),
    ]
    assert weather_main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert weather_main(args) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert job(workspace, first["job_id"])["state"] == "queued" and adapter.calls == []
    with workspace.database.read() as connection:
        assert connection.execute(
            "SELECT actor FROM idempotency WHERE scope=?",
            ("weather-reconcile:" + run.id,),
        ).fetchone()[0] == "team:local-operator:" + str(os.getuid())


def test_wrong_cli_storage_binding_cannot_migrate_its_target(
    workspace: Workspace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = configuration(tmp_path).model_copy(
        update={"directory": str(workspace.database.path.parent)}
    )
    config_file = tmp_path / "operator-runtime.json"
    config_file.write_text(settings.model_dump_json())
    monkeypatch.setenv("LINKER_PLANNER_CONFIG", str(config_file))
    with sqlite3.connect(workspace.database.path) as connection:
        connection.execute("PRAGMA user_version=3")
    original = workspace.database.path.read_bytes()
    assert (
        weather_main(
            [
                "observe",
                "--run-id",
                "unknown",
                "--key",
                "wrong-target",
                "--expected-storage",
                "0" * 64,
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "conflict"
    assert workspace.database.path.read_bytes() == original
    with sqlite3.connect(workspace.database.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3


def test_independent_process_reconciles_cached_capture_with_new_acquisition_disabled(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path)
    workspace, _ = settings.open()
    owner = Actor("user", "independent-recovery-owner")
    adapter = SequenceAdapter()
    _, run, _, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("SUCCEEDED"))
    journal.retain_capture(
        intent,
        source(),
        {"dependencies": {"fixture_source": workspace.blobs.put(raw())}},
    )
    receipt = WeatherOperator(workspace).admit(
        OPERATOR, run.id, "capture", key="cached-capture"
    )
    ExecutionControl(workspace).set_draining(True)
    process, ready, generation = launch(tmp_path / "independent-worker", settings)
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        finished = wait_for(
            lambda: job(workspace, receipt["job_id"]),
            lambda value: value["state"] in ("succeeded", "failed"),
        )
        assert finished["state"] == "succeeded"
        assert (
            workspace.blobs.object(finished["output_sha256"])["capture_sha256"]
            == journal.current(intent).capture_sha256
        )
        assert ExecutionControl(workspace).status()["quiescent"] is True
        assert (
            workspace.run(owner, run.id).state == "failed"
            and workspace.run(owner, run.id).result is None
        )
        assert asset_count(workspace) == 0 and adapter.calls == []
    finally:
        stop(process)


def test_reconciliation_cannot_use_a_transport_with_different_frozen_limits(
    workspace: Workspace, owner: Actor
) -> None:
    adapter = SequenceAdapter()
    _, run, _, _, journal, intent = failed_start(workspace, owner, adapter)
    journal.acknowledge(intent, remote("RUNNING"))
    receipt = WeatherOperator(workspace).admit(
        OPERATOR, run.id, "observe", key="policy"
    )
    executor = WeatherReconciliation(
        workspace,
        connection=lambda limits: ApifyTransport(
            lambda: "fixture-only",
            limits.model_copy(update={"max_polls": 11}),
            adapter=adapter,
        ),
    )
    runner = Worker(
        Jobs(workspace),
        "bad-policy",
        {"reconcile_weather": executor},
        lease_seconds=300,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert runner.run_once()
    row = job(workspace, receipt["job_id"])
    assert (
        row["state"] == "failed"
        and workspace.blobs.object(row["error_sha256"])["code"] == "version_unavailable"
    )
    assert adapter.calls == []
