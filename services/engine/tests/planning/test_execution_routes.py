"""Real durable routing/admission; fixture executables are not energy claims."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from linker_engine.planning.canonical import digest
from linker_engine.planning.errors import ServiceDraining
from linker_engine.planning.execution_control import ExecutionControl
from linker_engine.planning.execution_identity import EvaluationRouting, execution_key
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace


def enqueue(workspace: Workspace, owner: Actor, context: Context, name: str):
    project = workspace.create(owner, name, {"fixture_only": True}, key=name)
    return workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=2)


@pytest.mark.parametrize("change", ["code", "model", "settings"])
def test_matching_claim_skips_other_execution_without_spending_attempts(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    change: str,
) -> None:
    other = replace(
        context,
        code_sha256=digest(b"other-executable")
        if change == "code"
        else context.code_sha256,
        models={"persistence-fixture": "2"} if change == "model" else context.models,
        parameters={"fixture_only": "different"}
        if change == "settings"
        else context.parameters,
    )
    foreign = enqueue(workspace, owner, other, "first-other")
    own = enqueue(workspace, owner, context, "later-matching")
    routing = EvaluationRouting(execution_key(context.document()), 8)
    lease = Jobs(workspace).claim(
        "matching", kinds=("evaluate",), lease_seconds=30, routing=routing
    )
    assert lease is not None and lease.run_id == own.id
    assert workspace.run(owner, foreign.id).state == "queued"
    with workspace.database.read() as connection:
        assert (
            connection.execute(
                "SELECT attempt FROM jobs WHERE run_id=?", (foreign.id,)
            ).fetchone()[0]
            == 0
        )
    second = Jobs(workspace).claim(
        "other",
        kinds=("evaluate",),
        lease_seconds=30,
        routing=EvaluationRouting(execution_key(other.document()), 8),
    )
    assert second is not None and second.run_id == foreign.id


def test_unindexed_v2_jobs_are_routed_in_batches_without_changing_frozen_bytes(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    clock,
) -> None:
    foreign = replace(context, code_sha256=digest(b"retained-old-release"))
    old = enqueue(workspace, owner, foreign, "old-first")
    clock.advance(1)
    own = enqueue(workspace, owner, context, "own-last")
    with workspace.database.transaction() as connection:
        connection.execute("DELETE FROM evaluation_routes")
    key = execution_key(context.document())
    jobs = Jobs(workspace)
    assert (
        jobs.claim(
            "current",
            kinds=("evaluate",),
            lease_seconds=30,
            routing=EvaluationRouting(key, 1),
        )
        is None
    )
    lease = jobs.claim(
        "current",
        kinds=("evaluate",),
        lease_seconds=30,
        routing=EvaluationRouting(key, 1),
    )
    assert lease is not None and lease.run_id == own.id
    assert workspace.run(owner, old.id).manifest_sha256 == old.manifest_sha256
    assert workspace.run(owner, own.id).manifest_sha256 == own.manifest_sha256


def test_unknown_cached_key_is_repaired_after_bounded_rotation_past_foreign_rows(
    workspace: Workspace, owner: Actor, context: Context, clock
) -> None:
    other = replace(context, code_sha256=digest(b"other-retained-release"))
    foreign = []
    for index in range(5):
        foreign.append(enqueue(workspace, owner, other, f"foreign-{index}"))
        clock.advance(1)
    own = enqueue(workspace, owner, context, "stranded-cache")
    with workspace.database.transaction() as connection:
        connection.execute(
            "UPDATE evaluation_routes SET execution_sha256=? WHERE job_id IN "
            "(SELECT id FROM jobs WHERE run_id=?)",
            (digest(b"nonexistent-worker"), own.id),
        )
    jobs = Jobs(workspace)
    routing = EvaluationRouting(execution_key(context.document()), 1)
    for _ in range(5):
        assert (
            jobs.claim(
                "current", kinds=("evaluate",), lease_seconds=30, routing=routing
            )
            is None
        )
    lease = jobs.claim(
        "current", kinds=("evaluate",), lease_seconds=30, routing=routing
    )
    assert lease is not None and lease.run_id == own.id
    for run in foreign:
        assert workspace.run(owner, run.id).state == "queued"
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM jobs WHERE attempt=0").fetchone()[
                0
            ]
            == 5
        )
    assert workspace.run(owner, own.id).manifest_sha256 == own.manifest_sha256


def test_wrong_cached_route_is_repaired_before_a_foreign_worker_can_lease_it(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    other = replace(context, parameters={"fixture_only": "other"})
    run = enqueue(workspace, owner, other, "cache-target")
    key = execution_key(context.document())
    with workspace.database.transaction() as connection:
        connection.execute("UPDATE evaluation_routes SET execution_sha256=?", (key,))
    assert (
        Jobs(workspace).claim(
            "wrong",
            kinds=("evaluate",),
            lease_seconds=30,
            routing=EvaluationRouting(key, 8),
        )
        is None
    )
    with workspace.database.read() as connection:
        row = connection.execute(
            "SELECT state, attempt FROM jobs WHERE run_id=?", (run.id,)
        ).fetchone()
        assert tuple(row) == ("queued", 0)
    lease = Jobs(workspace).claim(
        "right",
        kinds=("evaluate",),
        lease_seconds=30,
        routing=EvaluationRouting(execution_key(other.document()), 8),
    )
    assert lease is not None and lease.run_id == run.id


def test_missing_old_request_fails_by_name_without_claiming_another_owner(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    run = enqueue(workspace, owner, context, "missing-source")
    with workspace.database.transaction() as connection:
        connection.execute("DELETE FROM evaluation_routes")
        connection.execute("UPDATE jobs SET request_sha256=?", (digest(b"absent"),))
    assert (
        Jobs(workspace).claim(
            "current",
            kinds=("evaluate",),
            lease_seconds=30,
            routing=EvaluationRouting(execution_key(context.document()), 8),
        )
        is None
    )
    failed = workspace.run(owner, run.id)
    assert failed.state == "failed"
    assert failed.error == {"code": "version_unavailable", "retryable": False}


def test_drain_rejects_only_new_intents_and_preserves_exact_receipts_and_cancellation(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    run = enqueue(workspace, owner, context, "before-drain")
    control = ExecutionControl(workspace)
    control.set_draining(True)
    assert (
        workspace.evaluate(
            owner, run.project_id, 1, context, key="run", max_attempts=2
        ).id
        == run.id
    )
    with pytest.raises(ServiceDraining):
        workspace.evaluate(owner, run.project_id, 1, context, key="new", max_attempts=2)
    assert control.status()["pending"] == 1
    workspace.cancel(owner, run.id)
    assert control.status()["pending"] == 0
    control.set_draining(False)
    assert (
        workspace.evaluate(
            owner, run.project_id, 1, context, key="new", max_attempts=2
        ).state
        == "queued"
    )


def test_concurrent_admission_and_drain_have_one_transactional_order(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    project = workspace.create(owner, "Drain race fixture", {}, key="race")
    barrier = Barrier(2)

    def submit():
        barrier.wait()
        try:
            return workspace.evaluate(
                owner, project.id, 1, context, key="race", max_attempts=2
            )
        except ServiceDraining:
            return None

    def drain():
        barrier.wait()
        ExecutionControl(workspace).set_draining(True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        submitted = pool.submit(submit)
        draining = pool.submit(drain)
        run = submitted.result()
        draining.result()
    assert ExecutionControl(workspace).status()["pending"] == int(run is not None)
    with pytest.raises(ServiceDraining):
        workspace.evaluate(owner, project.id, 1, context, key="after", max_attempts=2)


def test_concurrent_matching_workers_do_not_share_a_lease(
    workspace: Workspace,
    owner: Actor,
    context: Context,
) -> None:
    run = enqueue(workspace, owner, context, "one-lease")
    routing = EvaluationRouting(execution_key(context.document()), 8)
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(
            pool.map(
                lambda name: Jobs(workspace).claim(
                    name, kinds=("evaluate",), lease_seconds=30, routing=routing
                ),
                ("one", "two"),
            )
        )
    assert sum(lease is not None for lease in leases) == 1
    assert next(lease for lease in leases if lease is not None).run_id == run.id
