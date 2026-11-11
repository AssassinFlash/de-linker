"""The real engine executable refuses an unsafe launch before lifecycle work.

PHP=/opt/homebrew/opt/php@8.3/bin/php LINKER_PLANNER_TEST_INSTANCE=<owned instance> \
uv run --locked --project tools/local pytest \
tools/local/tests/integration/test_engine_launch_protection.py -q

`tests/test_engine_release.py` and `tests/test_planner_launch.py` replace the
release probe, the retained-input floor and the store with fakes, so nothing
there observes what the shipped executable reports or where the refusal lands
in the lifecycle. This file runs the actual engine source and its retained
environment through `PlannerWorker` and the real service manager.

Spec: docs/specs/548-native-solar-install.md "Launch protection and private
provider contract". Every case uses a contained workspace below the owned
instance; the instance's own project store is never opened for writing.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest

from linker_local import server, services
from linker_local.checkout import Checkout
from linker_local.cli import require_php
from linker_local.instance import HOST, Instance, home
from linker_local.planner_worker import PlannerWorker
from linker_local.processes import Background, ProcessError
from linker_local.registry import Registry
from linker_local.wpcli import WpCli, WpCliError

RESOURCE_VERSION = "LINKER_ENGINE_RESOURCE_VERSION"
# The module `PlannerWorker.command()` runs; recorded argv names it in full.
WORKER_HOST = "linker_engine.planning.worker_host"


@pytest.fixture(scope="module")
def local() -> Iterator[tuple[Instance, WpCli, Checkout]]:
    name = os.environ.get("LINKER_PLANNER_TEST_INSTANCE", "")
    if not name:
        pytest.skip("name the owned local instance explicitly")
    instance = Registry(home()).get(name)
    assert instance is not None and instance.is_provisioned()
    checkout = Checkout.here()
    assert (instance.wp_content / "plugins/linker-tools").resolve() == (
        checkout.root / "plugins/linker-tools"
    ).resolve()
    engine = checkout.service("engine")
    if not (engine / ".venv/bin/python").is_file():
        pytest.skip(
            "the real engine environment is required: "
            "uv sync --locked --project services/engine"
        )
    assert server.process(instance).pid() is not None, "`just up` the instance first"
    wp = WpCli(require_php(), instance)
    # These cases own both service halves; a live pair would be replaced by the
    # manager before its refusal could be observed.
    services.stop(instance)
    assert services.running(instance) == []
    try:
        yield instance, wp, checkout
    finally:
        assert services.serve(instance, checkout, wp, only="engine")


def uv() -> Path:
    found = shutil.which("uv")
    assert found is not None
    return Path(found)


def resource_version(wp: WpCli) -> str:
    try:
        return wp.run("config", "get", RESOURCE_VERSION, "--type=constant")
    except WpCliError:
        return ""


@contextmanager
def contained_workspace(instance: Instance) -> Iterator[Path]:
    """One empty workspace below the owned instance; the policy is restored."""
    policy_file = instance.dir / "planner/runtime.json"
    assert policy_file.is_file(), "`just serve` the instance once, then stop it"
    original = policy_file.read_bytes()
    policy = json.loads(original)
    assert Path(policy["directory"]).resolve().is_relative_to(instance.dir.resolve())
    workspace = instance.dir / "planner" / ("launch-protection-" + uuid.uuid4().hex)
    workspace.mkdir(mode=0o700)
    try:
        policy["directory"] = str(workspace)
        policy_file.write_text(json.dumps(policy))
        yield workspace
    finally:
        policy_file.write_bytes(original)
        assert policy_file.read_bytes() == original
        shutil.rmtree(workspace, ignore_errors=True)
        assert not workspace.exists()


def build_store(workspace: Path, version: int) -> dict[str, tuple[int, str]]:
    """A populated store at `version`; returns an mtime+bytes fingerprint."""
    database = workspace / "workspace.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE projects(id TEXT, owner TEXT)")
        connection.execute(
            "INSERT INTO projects VALUES (?,?)", ("a" * 32, "guest:wp:1:guest:retained")
        )
        connection.execute(f"PRAGMA user_version={version}")
    return fingerprint(workspace)


def fingerprint(workspace: Path) -> dict[str, tuple[int, str]]:
    return {
        entry.name: (entry.stat().st_mtime_ns, entry.read_bytes().hex())
        for entry in sorted(workspace.iterdir())
        if entry.is_file()
    }


@contextmanager
def recording_uv(tmp_path: Path) -> Iterator[Path]:
    """A real uv that records its argv before executing, so sync is observable."""
    directory = tmp_path / "uv"
    directory.mkdir()
    log = directory / "commands"
    wrapper = directory / "uv"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"{{ printf '%s\\0' \"$@\"; printf '\\n'; }} >> {str(log)!r}\n"
        f'exec {str(uv())!r} "$@"\n'
    )
    wrapper.chmod(0o755)
    previous = os.environ.get("PATH", "")
    os.environ["PATH"] = str(directory) + os.pathsep + previous
    try:
        yield log
    finally:
        os.environ["PATH"] = previous


def recorded(log: Path) -> list[list[str]]:
    """Each recorded argv; the wrapper's field separator leaves one empty tail."""
    if not log.is_file():
        return []
    commands = []
    for line in log.read_text().splitlines():
        fields = line.split("\x00")
        assert fields[-1] == "", "the wrapper records a terminated argv"
        commands.append(fields[:-1])
    return commands


def copy_executable(source: Path, destination: Path) -> Path:
    """The same engine sources plus one extra module: a different runtime."""
    destination.mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(source / name, destination / name)
    for name in ("src", "schemas"):
        shutil.copytree(
            source / name,
            destination / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    (destination / "src/linker_engine/planning/launch_marker.py").write_text(
        '"""A different executable tree with one additional module."""\n'
    )
    # The retained interpreter environment is reused, never copied.
    (destination / ".venv").symlink_to((source / ".venv").resolve())
    return destination


def identity_of(worker: PlannerWorker) -> dict[str, object]:
    result = subprocess.run(
        worker.command("identity"),
        env=worker.environment(),
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    value = json.loads(result.stdout)
    assert isinstance(value, dict)
    return value


def start_engine_http(
    instance: Instance, checkout: Checkout, project: Path, token: str
) -> Background:
    """The real engine HTTP distribution, from `project`, on the instance port."""
    environment = services._engine_environment(instance, checkout)
    environment.update(
        {
            "GENIE_SERVICE_TOKEN": token,
            "LINKER_ENGINE_GATE_MODE": "enforce",
            "PYTHONPATH": str(project / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    process = services.SERVICES[0].process(instance)
    process.restart(
        [
            str(uv()),
            "run",
            "--locked",
            "--no-sync",
            "--offline",
            "--project",
            str(project),
            "uvicorn",
            services.SERVICES[0].app,
            "--host",
            HOST,
            "--port",
            str(instance.engine_port),
        ],
        environment,
        instance.engine_port,
        services.START_TIMEOUT,
    )
    return process


@pytest.mark.parametrize(("label", "version"), [("versioned", 3), ("unversioned", 0)])
def test_serve_refuses_a_store_the_executable_cannot_adopt(
    local: tuple[Instance, WpCli, Checkout],
    tmp_path: Path,
    label: str,
    version: int,
) -> None:
    """Spec (a) and (c): a different-or-absent version is never a new empty database."""
    instance, wp, checkout = local
    with contained_workspace(instance) as workspace:
        before = build_store(workspace, version)
        config_before = resource_version(wp)
        with recording_uv(tmp_path) as log:
            with pytest.raises(ProcessError, match="paired upgrade"):
                services.serve(instance, checkout, wp, only="engine")
        # Read-only: the store kept its bytes, its mtime and its file set, and
        # no WAL/journal side file was created by a write transaction.
        assert fingerprint(workspace) == before
        assert not (workspace / "workspace.sqlite-wal").exists()
        assert resource_version(wp) == config_before
        # The only process this launch ran is the identity probe: no dependency
        # synchronization, no service restart, no lifecycle command.
        commands = recorded(log)
        assert len(commands) == 1, commands
        assert commands[0][:5] == [
            "run",
            "--locked",
            "--no-sync",
            "--offline",
            "--project",
        ]
        assert commands[0][-2:] == [WORKER_HOST, "release"]
        assert "sync" not in commands[0]
        assert services.running(instance) == []


def test_refusal_order_puts_the_store_before_the_executor_pair(
    local: tuple[Instance, WpCli, Checkout], tmp_path: Path
) -> None:
    """Both guards would trip; the store's refusal is the one that is reported."""
    instance, wp, checkout = local
    with contained_workspace(instance) as workspace:
        other = copy_executable(checkout.service("engine"), tmp_path / "other")
        paired = instance.dir / "planner" / ("launch-paired-" + uuid.uuid4().hex)
        paired.mkdir(mode=0o700)
        policy_file = instance.dir / "planner/runtime.json"
        policy = json.loads(policy_file.read_bytes())
        worker = PlannerWorker(instance, other, uv(), checkout=checkout)
        try:
            policy["directory"] = str(paired)
            policy_file.write_text(json.dumps(policy))
            worker.ensure_policy()
            actual = identity_of(worker)
            worker.start(actual, 180)
            assert worker.readiness(actual) is not None
            # The live pair is real. Now the store is also the wrong version, so
            # a check that ran the executor guard first would say "worker differs".
            policy["directory"] = str(workspace)
            policy_file.write_text(json.dumps(policy))
            build_store(workspace, 9)
            with pytest.raises(ProcessError) as refused:
                worker.compatible_release()
            assert "storage/executable versions differ" in str(refused.value), str(
                refused.value
            )
            assert "worker differs" not in str(refused.value)
            # The prepared pair is preserved for the paired upgrade.
            assert worker.process.pid() is not None
            assert worker.readiness(actual) is not None
        finally:
            worker.stop()
            shutil.rmtree(paired, ignore_errors=True)
            assert not paired.exists()


def test_serve_refuses_a_running_worker_from_another_executable(
    local: tuple[Instance, WpCli, Checkout], tmp_path: Path
) -> None:
    """Spec (b), worker half: a different live runtime is refused, not stopped."""
    instance, wp, checkout = local
    with contained_workspace(instance):
        other = copy_executable(checkout.service("engine"), tmp_path / "other")
        worker = PlannerWorker(instance, other, uv(), checkout=checkout)
        try:
            worker.ensure_policy()
            actual = identity_of(worker)
            ours = identity_of(
                PlannerWorker(
                    instance, checkout.service("engine"), uv(), checkout=checkout
                )
            )
            assert actual["runtime_sha256"] != ours["runtime_sha256"]
            worker.start(actual, 180)
            ready = instance.run_dir / "planner-worker.ready.json"
            ready_before = ready.read_bytes()
            pid = worker.process.pid()
            assert pid is not None and worker.readiness(actual) is not None
            config_before = resource_version(wp)
            with recording_uv(tmp_path) as log:
                with pytest.raises(
                    ProcessError, match="running planning worker differs"
                ):
                    services.serve(instance, checkout, wp, only="engine")
            # Preserved: same process, same readiness, no WordPress write.
            assert worker.process.pid() == pid
            assert worker.readiness(actual) is not None
            assert ready.read_bytes() == ready_before
            assert resource_version(wp) == config_before
            # Refused before drain: the only child a serve ran is the identity
            # probe, so no `control` lifecycle command and no uvicorn restart.
            commands = recorded(log)
            assert len(commands) == 1, commands
            assert commands[0][-2:] == [WORKER_HOST, "release"]
            assert all("control" not in command for command in commands)
            assert all("uvicorn" not in command for command in commands)
        finally:
            assert worker.stop()


def test_serve_refuses_a_running_http_from_another_executable(
    local: tuple[Instance, WpCli, Checkout], tmp_path: Path
) -> None:
    """Spec (b), HTTP half: the same rule for the served half of the pair."""
    instance, wp, checkout = local
    with contained_workspace(instance):
        other = copy_executable(checkout.service("engine"), tmp_path / "other")
        token = services.service_token(wp)
        process = start_engine_http(instance, checkout, other, token)
        try:
            pid = process.pid()
            assert pid is not None
            served = services._planner_probe(
                f"http://{HOST}:{instance.engine_port}", token
            )
            ours = PlannerWorker(
                instance, checkout.service("engine"), uv(), checkout=checkout
            ).release()
            assert served["runtime_sha256"] != ours["runtime_sha256"]
            config_before = resource_version(wp)
            with recording_uv(tmp_path) as log:
                with pytest.raises(ProcessError, match="running planning HTTP differs"):
                    services.serve(instance, checkout, wp, only="engine")
            assert process.pid() == pid
            assert resource_version(wp) == config_before
            commands = recorded(log)
            assert len(commands) == 1, commands
            assert commands[0][-2:] == [WORKER_HOST, "release"]
            assert all("uvicorn" not in command for command in commands)
        finally:
            process.stop()
            assert process.pid() is None


def test_release_probe_needs_no_policy_store_or_migration(
    local: tuple[Instance, WpCli, Checkout], tmp_path: Path
) -> None:
    """The probe reports the code's storage version without opening a store."""
    _, _, checkout = local
    engine = checkout.service("engine")
    declared = re.search(
        r"^SCHEMA_VERSION = (\d+)$",
        (engine / "src/linker_engine/planning/schema.py").read_text(),
        re.MULTILINE,
    )
    assert declared, "schema.py must declare its storage version"
    workspace = tmp_path / "unreadable"
    workspace.mkdir()
    database = workspace / "workspace.sqlite"
    database.write_bytes(b"not a database")
    database.chmod(0o000)
    policy = tmp_path / "absent-policy.json"
    result = subprocess.run(
        [
            str(uv()),
            "run",
            "--locked",
            "--no-sync",
            "--offline",
            "--project",
            str(engine),
            "python",
            "-m",
            "linker_engine.planning.worker_host",
            "release",
        ],
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LINKER_PLANNER_CONFIG": str(policy),
            "PYTHONPATH": str(engine / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    release = json.loads(result.stdout)
    assert release["schema_version"] == 1
    assert re.fullmatch(r"[a-f0-9]{64}", release["runtime_sha256"])
    assert release["storage_schema_version"] == int(declared[1])
    assert isinstance(release["project_input_contracts"], list)
    # No policy was read into existence and the store was never opened for a
    # migration: it is not even readable by the probe's own credentials.
    assert not policy.exists()
    database.chmod(0o600)
    assert database.read_bytes() == b"not a database"
    assert [entry.name for entry in workspace.iterdir()] == ["workspace.sqlite"]


def test_routine_serve_accepts_the_store_its_own_executable_created(
    local: tuple[Instance, WpCli, Checkout],
) -> None:
    """A negative case is only meaningful if the matching launch is accepted."""
    instance, _, checkout = local
    with contained_workspace(instance) as workspace:
        worker = PlannerWorker(
            instance, checkout.service("engine"), uv(), checkout=checkout
        )
        worker.ensure_policy()
        # The real engine creates and migrates the store when it first runs.
        state = worker.control("status")
        assert state["pending"] == 0
        assert (workspace / "workspace.sqlite").is_file()
        release = worker.compatible_release()
        version = release["storage_schema_version"]
        assert isinstance(version, int) and version >= 1
        # A preflight that only inspects the store starts no worker.
        assert worker.readiness() is None
