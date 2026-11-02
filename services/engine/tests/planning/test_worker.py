"""The execution boundary uses pinned bytes and durable outcomes."""

from __future__ import annotations

import time
from dataclasses import replace
from threading import Event, Thread
from typing import Any, Literal

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import EvidenceMissing
from linker_engine.planning.execution_identity import EvaluationRouting, execution_key
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context, Lease
from linker_engine.planning.worker import Control, Published, RetryableExecution, Worker
from linker_engine.planning.workspace import Workspace


def test_resource_class_routing_keeps_ordinary_work_moving(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    project = workspace.create(owner, "Synthetic routing", {"load": 5}, key="new")
    expanded = replace(
        context,
        parameters={**context.parameters, "execution_class": "clear_flat_roof_v1"},
    )
    first = workspace.evaluate(
        owner, project.id, 1, expanded, key="expanded-1", max_attempts=1
    )
    second = workspace.evaluate(
        owner, project.id, 1, expanded, key="expanded-2", max_attempts=1
    )
    normal = workspace.evaluate(
        owner, project.id, 1, context, key="ordinary", max_attempts=1
    )
    ordinary_key = execution_key(context.document())
    expanded_key = execution_key(expanded.document())
    active, started, release = Event(), Event(), Event()

    def long_job(_lease: Lease, control: Control) -> Object:
        started.set()
        assert release.wait(5)
        control.checkpoint()
        return {"expanded": True}

    def ordinary_job(_lease: Lease, _control: Control) -> Object:
        assert active.is_set()
        return {"ordinary": True}

    large_worker = Worker(
        Jobs(workspace),
        "large",
        {"evaluate": long_job},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
        routing=EvaluationRouting(expanded_key, 10, (expanded_key,)),
    )
    normal_worker = Worker(
        Jobs(workspace),
        "normal",
        {"evaluate": ordinary_job},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
        routing=EvaluationRouting(ordinary_key, 10, (ordinary_key,)),
        active=active,
    )
    thread = Thread(target=large_worker.run_once)
    thread.start()
    try:
        assert started.wait(5)
        assert normal_worker.run_once()
        assert workspace.run(owner, normal.id).state == "succeeded"
        assert {
            workspace.run(owner, first.id).state,
            workspace.run(owner, second.id).state,
        } == {"queued", "running"}
        assert not active.is_set()
    finally:
        release.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert {
        workspace.run(owner, first.id).state,
        workspace.run(owner, second.id).state,
    } == {"queued", "succeeded"}


def test_child_committed_result_survives_heartbeat_and_is_not_republished(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(owner, "Synthetic child result", {"load": 5}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    complete = jobs.complete
    calls = 0

    def counted(*args: Any, **kwargs: Any) -> str:
        nonlocal calls
        calls += 1
        return complete(*args, **kwargs)

    monkeypatch.setattr(jobs, "complete", counted)

    def child(lease: Lease, _control: Control) -> Published:
        sha = jobs.complete(lease, {"committed_in_child": True})
        time.sleep(0.05)  # allow a heartbeat to observe the committed attempt
        return Published(sha)

    worker = Worker(
        jobs,
        "worker",
        {"evaluate": child},
        lease_seconds=1,
        heartbeat_seconds=0.01,
        retry_seconds=1,
    )
    assert worker.run_once()
    assert workspace.run(owner, run.id).state == "succeeded"
    assert calls == 1


@pytest.mark.parametrize(
    "outcome", ["success", "transient", "bug", "cancel", "evidence"]
)
def test_worker_publishes_only_owned_frozen_work(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    outcome: Literal["success", "transient", "bug", "cancel", "evidence"],
) -> None:
    project = workspace.create(owner, "Project", {"load": 5}, key="new")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=3)
    workspace.revise(owner, project.id, 1, {"load": 10}, key="edit")

    def execute(lease: Lease, control: Control) -> Object:
        control.checkpoint()
        manifest_hash = lease.request["manifest_sha256"]
        assert isinstance(manifest_hash, str)
        manifest = workspace.blobs.object(manifest_hash)
        frozen = workspace.pinned_inputs(manifest)
        assert frozen == {"load": 5}
        if outcome == "transient":
            raise RetryableExecution("fixture transport error")
        if outcome == "bug":
            raise RuntimeError("fixture unexpected error")
        if outcome == "evidence":
            raise EvidenceMissing(
                "private raw fixture detail must not escape",
                constraint_id="plant_dc_pv_nameplate_mismatch",
            )
        if outcome == "cancel":
            workspace.cancel(owner, run.id)
        return {"fixture_only": True, "frozen_inputs": frozen}

    worker = Worker(
        Jobs(workspace),
        "fixture-worker",
        {"evaluate": execute},
        lease_seconds=30,
        heartbeat_seconds=10,
        retry_seconds=5,
    )
    assert worker.run_once()
    current = workspace.run(owner, run.id)
    if outcome == "success":
        assert current.state == "succeeded"
        assert current.result == {"fixture_only": True, "frozen_inputs": {"load": 5}}
    elif outcome == "transient":
        assert current.state == "retry_wait" and current.result is None
        assert current.error == {"code": "source_unavailable", "retryable": True}
    elif outcome == "bug":
        assert current.state == "failed" and current.result is None
        assert current.error == {"code": "execution_failed", "retryable": False}
    elif outcome == "evidence":
        assert current.state == "failed" and current.result is None
        assert current.error == {
            "code": "evidence_missing",
            "retryable": False,
            "details": {"constraint_id": "plant_dc_pv_nameplate_mismatch"},
        }
    else:
        assert current.state == "cancelled" and current.result is None
    assert not worker.run_once()
