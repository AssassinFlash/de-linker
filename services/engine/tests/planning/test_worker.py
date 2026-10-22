"""The execution boundary uses pinned bytes and durable outcomes."""

from __future__ import annotations

from typing import Literal

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context, Lease
from linker_engine.planning.worker import Control, RetryableExecution, Worker
from linker_engine.planning.workspace import Workspace


@pytest.mark.parametrize("outcome", ["success", "transient", "bug", "cancel"])
def test_worker_publishes_only_owned_frozen_work(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    outcome: Literal["success", "transient", "bug", "cancel"],
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
    else:
        assert current.state == "cancelled" and current.result is None
    assert not worker.run_once()
