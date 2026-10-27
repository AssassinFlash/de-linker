"""Actual independent Python processes execute the analytic energy fixture."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object
from linker_engine.planning.execution_identity import storage_binding
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.records import Actor, Project, Run
from linker_engine.planning.runtime_config import RuntimeConfig
from linker_engine.planning.worker_policy import WorkerPolicy
from linker_engine.planning.workspace import Workspace

from .conftest import json_object
from .test_energy_kernel import PROVENANCE, create_scenario, mapping


def wait_for[T](
    value: Callable[[], T], predicate: Callable[[T], bool], *, timeout: float = 15
) -> T:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = value()
        if predicate(current):
            return current
        time.sleep(0.01)
    raise AssertionError("actual process/state did not reach the expected condition")


def configuration(
    root: Path, *, rows: int = 100, absolute: float = 1e-7
) -> RuntimeConfig:
    return RuntimeConfig(
        schema_version=1,
        directory=str(root / "workspace"),
        max_body_bytes=2 * 1024 * 1024,
        max_csv_bytes=1024 * 1024,
        max_page_size=20,
        max_json_depth=32,
        max_intervals=rows,
        max_attempts=2,
        absolute_kwh=absolute,
        absolute_kw=1e-7,
        relative=1e-9,
    )


def launch(
    root: Path,
    settings: RuntimeConfig,
    *,
    label: str = "a",
    ready: Path | None = None,
    mismatch: str | None = None,
) -> tuple[subprocess.Popen[bytes], Path, str]:
    root.mkdir(parents=True, exist_ok=True)
    runtime_file = root / (label + "-runtime.json")
    runtime_file.write_text(settings.model_dump_json())
    ready = ready or root / (label + "-ready.json")
    # Short leases are test-only lifecycle policy; actual energy still runs.
    policy = WorkerPolicy(
        schema_version=1,
        name="process-test-" + label,
        lease_seconds=1,
        heartbeat_seconds=0.1,
        retry_seconds=0.1,
        poll_seconds=0.01,
        routing_batch_size=8,
        drain_timeout_seconds=5,
        ready_file=str(ready),
    )
    policy_file = root / (label + "-worker.json")
    policy_file.write_text(policy.model_dump_json())
    workspace, energy = settings.open()
    pv = settings.pv_service(workspace)
    weather = settings.weather_service(workspace)
    registry = service_registry(
        energy,
        pv,
        weather,
        settings.equipment_service(workspace),
        settings.equipment_search_service(workspace),
        settings.report_service(workspace),
    )
    identity = {
        "runtime": energy.kernel.runtime.sha256,
        "execution": registry.execution_key(),
        "storage": storage_binding(workspace.database.path),
    }
    if mismatch is not None:
        identity[mismatch] = "f" * 64
    generation = uuid4().hex
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LINKER_PLANNER_CONFIG": str(runtime_file),
        "LINKER_PLANNER_WORKER_CONFIG": str(policy_file),
    }
    with (root / (label + "-process.log")).open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "linker_engine.planning.worker_host",
                "serve",
                "--expected-runtime",
                identity["runtime"],
                "--expected-execution",
                identity["execution"],
                "--expected-storage",
                identity["storage"],
                "--generation",
                generation,
            ],
            env=environment,
            stdout=log,
            stderr=log,
        )
    return process, ready, generation


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def ready_generation(path: Path) -> str | None:
    try:
        generation = json.loads(path.read_bytes())["generation"]
        assert isinstance(generation, str)
        return generation
    except (FileNotFoundError, ValueError):
        return None


def completed(workspace: Workspace, owner: Actor, run: Run) -> Run:
    return wait_for(
        lambda: workspace.run(owner, run.id),
        lambda value: value.state in ("succeeded", "failed", "cancelled"),
    )


def long_scenario(
    workspace: Workspace, owner: Actor, project: Project, rows: int = 5000
) -> Project:
    # Explicit synthetic 1-minute means: PV meets load directly. This gives
    # enough real CPU work to observe SIGKILL/cancellation, not fake sleeps.
    start = datetime(2024, 1, 1, tzinfo=UTC)
    selected = {}
    for role, power in (("gross_load", 1), ("pv_available_ac", 1), ("aux_ac", 0)):
        raw = (
            "time,power\n"
            + "".join(
                f"{(start + timedelta(minutes=index)).isoformat()},{power}\n"
                for index in range(rows)
            )
        ).encode()
        selected[role] = (
            ProfileImport(Assets(workspace))
            .csv(
                owner,
                project.id,
                raw,
                replace(mapping(cast(Measurement, role)), interval_seconds=60),
                PROVENANCE,
                key="long-" + role,
            )
            .id
        )
    replay = dict(cast(Object, json_object(project.inputs)["energy_replay"]))
    replay.update(
        {
            "gross_load_asset_id": selected["gross_load"],
            "pv_available_asset_id": selected["pv_available_ac"],
            "aux_ac_asset_id": selected["aux_ac"],
            "schedule": [
                {
                    "start_utc": start.isoformat(),
                    "end_utc": (start + timedelta(minutes=rows)).isoformat(),
                    "mode": "connected",
                    "reserve_kwh": 0,
                    "import_cap_kw": None,
                    "export_cap_kw": 0,
                    "pv_enabled": True,
                    "allow_grid_charge": False,
                }
            ],
        }
    )
    return workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, "energy_replay": replay},
        key="long-scenario",
    )


def test_two_actual_workers_execute_only_their_own_numerical_settings(
    tmp_path: Path,
) -> None:
    first = configuration(tmp_path)
    second = configuration(tmp_path, absolute=2e-7)
    workspace, service_a = first.open()
    _, service_b = second.open()
    owner = Actor("user", "synthetic-process-owner")
    project = create_scenario(workspace, owner)
    other = service_b.evaluate(owner, project.id, project.revision, key="other-first")
    own = service_a.evaluate(owner, project.id, project.revision, key="matching-second")
    a, ready_a, generation_a = launch(tmp_path / "processes", first)
    b = None
    try:
        wait_for(lambda: ready_generation(ready_a), lambda value: value == generation_a)
        finished_a = completed(workspace, owner, own)
        assert finished_a.state == "succeeded"
        assert workspace.run(owner, other.id).state == "queued"
        with workspace.database.read() as connection:
            assert (
                connection.execute(
                    "SELECT attempt FROM jobs WHERE run_id=?", (other.id,)
                ).fetchone()[0]
                == 0
            )
        b, ready_b, generation_b = launch(tmp_path / "processes", second, label="b")
        wait_for(lambda: ready_generation(ready_b), lambda value: value == generation_b)
        finished_b = completed(workspace, owner, other)
        assert finished_b.state == "succeeded"
        for run in (finished_a, finished_b):
            assert run.result is not None
            metric = cast(Object, json_object(run.result)["metrics"])
            assert metric["gross_load_kwh"] == 4
            assert metric["solar_load_kwh"] == pytest.approx(3.62)
            assert metric["grid_import_kwh"] == pytest.approx(0.38)
            assert (
                cast(Object, json_object(run.result)["equipment_release"])["status"]
                == "not_assessed"
            )
        assert a.poll() is None and b.poll() is None
    finally:
        stop(a)
        if b is not None:
            stop(b)
    assert not ready_a.exists()


@pytest.mark.parametrize("mismatch", ["runtime", "execution", "storage"])
def test_startup_refuses_a_different_http_identity_without_claiming_work(
    tmp_path: Path,
    mismatch: str,
) -> None:
    settings = configuration(tmp_path)
    workspace, energy = settings.open()
    owner = Actor("user", "synthetic-start-owner")
    project = create_scenario(workspace, owner)
    run = energy.evaluate(owner, project.id, project.revision, key="queued")
    process, ready, _ = launch(tmp_path / "processes", settings, mismatch=mismatch)
    try:
        assert process.wait(timeout=10) == 1
        assert not ready.exists()
        assert workspace.run(owner, run.id).state == "queued"
        with workspace.database.read() as connection:
            assert connection.execute("SELECT attempt FROM jobs").fetchone()[0] == 0
    finally:
        stop(process)


def test_duplicate_ready_path_cannot_replace_a_live_worker(tmp_path: Path) -> None:
    settings = configuration(tmp_path)
    a, ready, generation = launch(tmp_path / "processes", settings)
    b = None
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        original = ready.read_bytes()
        b, _, _ = launch(
            tmp_path / "processes", settings, label="duplicate", ready=ready
        )
        assert b.wait(timeout=10) == 1
        assert a.poll() is None and ready.read_bytes() == original
    finally:
        stop(a)
        if b is not None:
            stop(b)


def test_sigkill_recovers_the_real_energy_lease_in_a_fresh_process(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path, rows=6000)
    workspace, energy = settings.open()
    owner = Actor("user", "synthetic-recovery-owner")
    project = long_scenario(workspace, owner, create_scenario(workspace, owner))
    run = energy.evaluate(owner, project.id, project.revision, key="recover-after-kill")
    process, ready, generation = launch(tmp_path / "processes", settings)
    replacement = None
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        wait_for(
            lambda: workspace.run(owner, run.id), lambda value: value.state == "running"
        )
        process.send_signal(signal.SIGKILL)
        process.wait(timeout=5)
        lost = workspace.run(owner, run.id)
        assert lost.state == "running" and lost.result is None
        assert ready.exists()  # stale file is deliberately left by a real SIGKILL
        replacement, _, next_generation = launch(
            tmp_path / "processes", settings, ready=ready, label="replacement"
        )
        wait_for(
            lambda: ready_generation(ready), lambda value: value == next_generation
        )
        finished = completed(workspace, owner, run)
        assert finished.state == "succeeded" and finished.result is not None
        assert cast(Object, json_object(finished.result)["metrics"])[
            "gross_load_kwh"
        ] == pytest.approx(5000 / 60)
        with workspace.database.read() as connection:
            assert (
                connection.execute(
                    "SELECT attempt FROM jobs WHERE run_id=?", (run.id,)
                ).fetchone()[0]
                == 2
            )
    finally:
        stop(process)
        if replacement is not None:
            stop(replacement)


def test_actual_running_cancellation_cannot_publish_and_worker_serves_the_next_run(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path, rows=6000)
    workspace, energy = settings.open()
    owner = Actor("user", "synthetic-cancel-owner")
    original = create_scenario(workspace, owner)
    project = long_scenario(workspace, owner, original)
    run = energy.evaluate(owner, project.id, project.revision, key="cancel-running")
    process, ready, generation = launch(tmp_path / "processes", settings)
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        wait_for(
            lambda: workspace.run(owner, run.id), lambda value: value.state == "running"
        )
        workspace.cancel(owner, run.id)
        revised = workspace.revise(
            owner,
            project.id,
            project.revision,
            original.inputs,
            key="restore-two-hours",
        )
        next_run = energy.evaluate(
            owner, project.id, revised.revision, key="after-cancel"
        )
        finished = completed(workspace, owner, next_run)
        assert finished.state == "succeeded"
        cancelled = workspace.run(owner, run.id)
        assert cancelled.state == "cancelled" and cancelled.result is None
        assert process.poll() is None
    finally:
        stop(process)


def test_sigterm_finishes_inflight_energy_and_leaves_the_next_job_queued(
    tmp_path: Path,
) -> None:
    settings = configuration(tmp_path, rows=6000)
    workspace, energy = settings.open()
    owner = Actor("user", "synthetic-drain-owner")
    original = create_scenario(workspace, owner)
    project = long_scenario(workspace, owner, original)
    run = energy.evaluate(owner, project.id, project.revision, key="inflight")
    process, ready, generation = launch(tmp_path / "processes", settings)
    try:
        wait_for(lambda: ready_generation(ready), lambda value: value == generation)
        wait_for(
            lambda: workspace.run(owner, run.id), lambda value: value.state == "running"
        )
        revised = workspace.revise(
            owner, project.id, project.revision, original.inputs, key="next-inputs"
        )
        next_run = energy.evaluate(owner, project.id, revised.revision, key="next-job")
        process.terminate()
        assert process.wait(timeout=15) == 0
        assert workspace.run(owner, run.id).state == "succeeded"
        assert workspace.run(owner, next_run.id).state == "queued"
        assert not ready.exists()
    finally:
        stop(process)
