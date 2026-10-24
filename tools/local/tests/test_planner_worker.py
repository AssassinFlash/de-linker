"""The local manager's process and instance boundary; energy has separate real tests."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from linker_local.instance import Instance
from linker_local.planner_worker import PlannerWorker
from linker_local.private_config import lifecycle_lock, publish_once
from linker_local.processes import ProcessError

IDENTITY = {
    "runtime_sha256": "a" * 64,
    "execution_key": "b" * 64,
    "storage_binding": "c" * 64,
}

# Only readiness/process ownership is simulated here, never energy or jobs.
READY_CHILD = """
import json, os, signal, sys
from pathlib import Path
from threading import Event
arguments = dict(zip(sys.argv[2::2], sys.argv[3::2], strict=True))
policy = json.loads(Path(os.environ['LINKER_PLANNER_WORKER_CONFIG']).read_bytes())
ready = Path(policy['ready_file'])
ready.parent.mkdir(parents=True, exist_ok=True)
stop = Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
value = dict(schema_version=1, pid=os.getpid(),
             generation=arguments['--generation'],
             runtime_sha256=arguments['--expected-runtime'],
             execution_key=arguments['--expected-execution'],
             storage_binding=arguments['--expected-storage'])
ready.write_text(json.dumps(value))
stop.wait()
ready.unlink(missing_ok=True)
"""


@pytest.fixture
def worker(tmp_path: Path) -> PlannerWorker:
    instance = Instance("owned", 1, 2, 3, tmp_path)
    subject = PlannerWorker(instance, tmp_path / "engine", Path(sys.executable))
    publish_once(
        subject.runtime_file, {"directory": str(instance.dir / "planner/workspace")}
    )
    subject.ensure_policy()
    return subject


def child(subject: PlannerWorker, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject, "command", lambda *args: [sys.executable, "-c", READY_CHILD, *args]
    )
    subject.start(IDENTITY, 3)


def test_private_policy_preserves_operator_choices(worker: PlannerWorker) -> None:
    assert worker.policy_file.stat().st_mode & 0o777 == 0o600
    policy = json.loads(worker.policy_file.read_bytes())
    policy["drain_timeout_seconds"] = 7
    worker.policy_file.write_text(json.dumps(policy))
    worker.ensure_policy()
    assert json.loads(worker.policy_file.read_bytes())["drain_timeout_seconds"] == 7


@pytest.mark.parametrize("weather_enabled", [False, True])
def test_numerical_environment_does_not_inherit_credentials(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch, weather_enabled: bool
) -> None:
    if weather_enabled:
        policy = json.loads(worker.runtime_file.read_bytes())
        policy["weather_acquisition"] = {}
        worker.runtime_file.write_text(json.dumps(policy))
    for key in (
        "GENIE_SERVICE_TOKEN",
        "APIFY_TOKEN",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.setenv(key, "synthetic-not-a-secret")
    assert not any(
        key in worker.environment()
        for key in (
            "GENIE_SERVICE_TOKEN",
            "APIFY_TOKEN",
            "OPENROUTER_API_KEY",
            "DEEPSEEK_API_KEY",
        )
    )
    assert worker.environment()["LINKER_PLANNER_CONFIG"] == str(worker.runtime_file)


def test_another_instances_store_and_readiness_are_refused(
    worker: PlannerWorker, tmp_path: Path
) -> None:
    worker.runtime_file.write_text(json.dumps({"directory": str(tmp_path / "foreign")}))
    with pytest.raises(ProcessError, match="owned instance"):
        worker.environment()
    policy = json.loads(worker.policy_file.read_bytes())
    policy["ready_file"] = str(tmp_path / "foreign/ready.json")
    worker.policy_file.write_text(json.dumps(policy))
    with pytest.raises(ProcessError, match="owned instance"):
        worker.ensure_policy()


def test_actual_process_group_generation_and_identity_are_required(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    child(worker, monkeypatch)
    try:
        pid = worker.process.pid()
        ready = worker.readiness(IDENTITY)
        assert pid is not None and ready is not None
        assert os.getpgid(ready["pid"]) == pid
        assert worker.readiness(IDENTITY, "0" * 32) is None
        worker.start(IDENTITY, 3)
        assert worker.process.pid() == pid
        with pytest.raises(ProcessError, match="different/unready"):
            worker.start({**IDENTITY, "execution_key": "d" * 64}, 3)
        assert worker.process.pid() == pid
        policy = json.loads(worker.policy_file.read_bytes())
        Path(policy["ready_file"]).write_text(json.dumps({**ready, "pid": os.getpid()}))
        assert worker.readiness(IDENTITY) is None
    finally:
        worker.stop()


def test_stale_readiness_without_the_owned_process_is_not_ready(
    worker: PlannerWorker,
) -> None:
    policy = json.loads(worker.policy_file.read_bytes())
    Path(policy["ready_file"]).parent.mkdir(parents=True, exist_ok=True)
    Path(policy["ready_file"]).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": os.getpid(),
                "generation": "0" * 32,
                **IDENTITY,
            }
        )
    )
    assert worker.readiness(IDENTITY) is None


def test_expired_drain_preserves_a_live_process_and_pending_tasks(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    child(worker, monkeypatch)
    try:
        policy = json.loads(worker.policy_file.read_bytes())
        # An artificial 20 ms manager deadline, not a production job budget.
        policy["drain_timeout_seconds"] = 0.02
        worker.policy_file.write_text(json.dumps(policy))
        operations = []

        def control(operation: str) -> dict[str, object]:
            operations.append(operation)
            return {"pending": 1, "draining": True, **IDENTITY}

        monkeypatch.setattr(worker, "control", control)
        pid = worker.process.pid()
        with pytest.raises(ProcessError, match="tasks and processes preserved"):
            worker.drain()
        assert worker.process.pid() == pid
        assert operations[0] == "drain" and "resume" not in operations
    finally:
        worker.stop()


def test_pending_tasks_without_a_live_executor_refuse_restart(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker, "control", lambda operation: {"pending": 1})
    with pytest.raises(ProcessError, match="no live matching worker"):
        worker.drain()


def test_lifecycle_lock_refuses_a_second_manager_and_then_releases(
    tmp_path: Path,
) -> None:
    lock = tmp_path / "run/services.lock"
    with lifecycle_lock(lock):
        with pytest.raises(ProcessError, match="already"):
            with lifecycle_lock(lock):
                pytest.fail("second lifecycle manager acquired the lock")
    with lifecycle_lock(lock):
        pass


def test_local_queue_empty_does_not_pass_unresolved_remote_work(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        worker,
        "control",
        lambda _: {"pending": 0, "draining": True, "quiescent": False, **IDENTITY},
    )
    with pytest.raises(ProcessError, match="no live matching worker"):
        worker.drain()


@pytest.mark.parametrize("issued", [False, True])
def test_legacy_drain_requires_read_only_no_remote_start_proof(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch, issued: bool
) -> None:
    directory = Path(json.loads(worker.runtime_file.read_bytes())["directory"])
    directory.mkdir(parents=True)
    database = directory / "workspace.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE weather_acquisitions (post_claimed INTEGER)")
        connection.execute(
            "INSERT INTO weather_acquisitions VALUES (?)", (int(issued),)
        )
        connection.execute("PRAGMA user_version=2")
    original = database.read_bytes()
    monkeypatch.setattr(
        worker, "control", lambda _: {"pending": 0, "draining": True, **IDENTITY}
    )
    if issued:
        with pytest.raises(ProcessError, match="issued remote weather"):
            worker.drain()
    else:
        worker.drain()
    assert database.read_bytes() == original


def test_inconsistent_remote_quiescence_from_child_is_rejected(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = {
        "schema_version": 1,
        "pending": 0,
        "draining": True,
        "quiescent": True,
        "remote_weather": {"unknown": 1, "active": 0, "terminal": 0, "unresolved": 1},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, json.dumps(state), ""
        ),
    )
    with pytest.raises(ProcessError, match="invalid remote quiescence"):
        worker.control("status")


@pytest.mark.parametrize("stored", [0, 2, 3, 5])
def test_preflight_refuses_different_populated_schema_without_writing(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch, stored: int
) -> None:
    directory = Path(json.loads(worker.runtime_file.read_bytes())["directory"])
    directory.mkdir(parents=True)
    database = directory / "workspace.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE projects(id TEXT)")
        connection.execute("INSERT INTO projects VALUES ('retained')")
        connection.execute(f"PRAGMA user_version={stored}")
    original = database.read_bytes()
    monkeypatch.setattr(
        worker,
        "release",
        lambda: {
            "schema_version": 1,
            "runtime_sha256": "a" * 64,
            "storage_schema_version": 4,
        },
    )
    with pytest.raises(ProcessError, match="verified paired upgrade"):
        worker.compatible_release()
    assert database.read_bytes() == original
    assert sorted(path.name for path in directory.iterdir()) == ["workspace.sqlite"]


def test_matching_schema_and_truly_empty_store_can_start(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = {
        "schema_version": 1,
        "runtime_sha256": "a" * 64,
        "storage_schema_version": 4,
    }
    monkeypatch.setattr(worker, "release", lambda: release)
    assert worker.compatible_release() == release
    directory = Path(json.loads(worker.runtime_file.read_bytes())["directory"])
    directory.mkdir(parents=True)
    database = directory / "workspace.sqlite"
    with sqlite3.connect(database):
        pass
    assert worker.compatible_release() == release
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE projects(id TEXT)")
        connection.execute("PRAGMA user_version=4")
    assert worker.compatible_release() == release


def test_running_worker_with_another_runtime_is_preserved(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch
) -> None:
    child(worker, monkeypatch)
    try:
        monkeypatch.setattr(
            worker,
            "release",
            lambda: {
                "schema_version": 1,
                "runtime_sha256": "d" * 64,
                "storage_schema_version": 4,
            },
        )
        pid = worker.process.pid()
        with pytest.raises(ProcessError, match="running planning worker differs"):
            worker.compatible_release()
        assert worker.process.pid() == pid
        assert worker.readiness(IDENTITY) is not None
    finally:
        worker.stop()


@pytest.mark.parametrize(
    "reply",
    [
        "not-json",
        "{}",
        json.dumps(
            {
                "schema_version": 1,
                "runtime_sha256": "a" * 64,
                "storage_schema_version": True,
            }
        ),
        json.dumps(
            {"schema_version": 1, "runtime_sha256": "bad", "storage_schema_version": 4}
        ),
    ],
)
def test_invalid_release_reply_is_not_authority(
    worker: PlannerWorker, monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, reply, ""),
    )
    with pytest.raises(ProcessError, match="release probe returned"):
        worker.release()
