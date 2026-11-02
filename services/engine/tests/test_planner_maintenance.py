"""The scheduled caller uses real SQLite/CAS recovery and the native collector."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import signal
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from linker_engine.planning import archive
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.records import Actor
from linker_engine.planning.retention import collect
from linker_engine.planning.workspace import Workspace

OPS = Path(__file__).resolve().parents[1] / "ops"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, OPS / (name + ".py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


maintenance = load("planner_maintenance")
installer = load("install_planner_maintenance")


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "live")


@pytest.fixture
def owner() -> Actor:
    return Actor("user", "wordpress:17")


def setup_store(tmp_path: Path, workspace: Workspace) -> tuple[Any, Path]:
    root = tmp_path / "archives"
    root.mkdir(mode=0o700)
    point = root / "archive-20261030T020000Z"
    manifest = archive.backup(workspace, point)
    registry = {
        "source": {"host": "example", "root": "/opt/linker-planner"},
        "entries": [
            {
                "kind": "verified_workspace_archive",
                "path": str(point),
                "database": {"sha256": manifest["database_sha256"]},
                "manifest": {
                    "sha256": hashlib.sha256(
                        (point / "backup.json").read_bytes()
                    ).hexdigest()
                },
            }
        ],
        "latest_verified_recovery": str(point),
    }
    (root / "RECOVERY-POINTS.json").write_text(json.dumps(registry))
    policy = maintenance.Policy("example", Path("/opt/linker-planner"), root, "a" * 32)
    return policy, point


class RemoteFixture:
    def __init__(self, workspace: Workspace, *, busy: bool = False) -> None:
        self.workspace = workspace
        self.busy = busy
        self.selected: str | None = None
        self.recovery_seconds = 0.0
        self.last_action = "local_recovery"
        self.events: list[str] = []
        self.recovery: Path | None = None
        self.fail: str | None = None
        self.fail_snapshot_ack = False

    def call(self, action: str, **values: Any) -> dict[str, Any]:
        self.last_action = action
        self.events.append(action)
        if action == self.fail:
            raise ConnectionError("private transport detail must not be logged")
        source = self.workspace.database.path.parent
        if action == "plan":
            return {
                "selected": "selected",
                "status": "busy" if self.busy else "idle",
                "recovery": None,
                "recovery_seconds": 400,
                "plan": collect(source),
            }
        if action == "stage":
            import tarfile

            self.recovery = source.parent / "remote-recovery"
            self.recovery.mkdir()
            with tarfile.open(fileobj=io.BytesIO(values["payload"])) as tar:
                for member in tar:
                    assert member.name in {"workspace.sqlite", "backup.json"}
                    stream = tar.extractfile(member)
                    assert stream is not None
                    (self.recovery / member.name).write_bytes(stream.read())
            manifest = json.loads((self.recovery / "backup.json").read_text())
            for sha in manifest["blobs"]:
                target = self.recovery / "blobs" / sha[:2] / sha
                target.parent.mkdir(parents=True, exist_ok=True)
                target.hardlink_to(source / "blobs" / sha[:2] / sha)
            return {"staged": True}
        if action == "apply":
            assert self.recovery is not None
            return {
                **collect(source, apply=True, offline=True, recovery=self.recovery),
                "restored": True,
            }
        if action == "cleanup":
            import shutil

            if self.recovery is not None:
                shutil.rmtree(self.recovery)
            return {"freed_bytes": 17}
        raise AssertionError(action)

    @contextmanager
    def snapshot(self, known: list[str]) -> Iterator[tuple[dict[str, Any], Any]]:
        self.events.append("snapshot")
        with sqlite3.connect(":memory:") as target:
            connection = self.workspace.database.connect()
            try:
                connection.backup(target)
                database = target.serialize()
            finally:
                connection.close()
        paths = {p.name: p for p in self.workspace.blobs.directory.glob("*/*")}
        sizes = {sha: path.stat().st_size for sha, path in paths.items()}
        missing = sorted(set(paths) - set(known))
        document: Object = {
            "schema": 1,
            "database_sha256": hashlib.sha256(database).hexdigest(),
            "blobs": [sha for sha in sorted(paths)],
        }
        manifest = encode(document)
        stream = io.BytesIO(
            database + manifest + b"".join(paths[s].read_bytes() for s in missing)
        )
        yield (
            {
                "database_bytes": len(database),
                "manifest_bytes": len(manifest),
                "sizes": sizes,
                "missing": missing,
            },
            stream.read,
        )
        if self.fail_snapshot_ack:
            raise ConnectionError("snapshot acknowledgement transport lost")


@pytest.mark.parametrize("mode", ["outside", "busy", "zero", "network"])
def test_no_work_never_creates_a_backup_or_stops_services(
    workspace: Workspace, tmp_path: Path, mode: str
) -> None:
    policy, original = setup_store(tmp_path, workspace)
    remote = RemoteFixture(workspace, busy=mode == "busy")
    now = dt.datetime(2026, 10, 31, 1 if mode == "outside" else 2, tzinfo=dt.UTC)
    if mode == "network":
        remote.fail = "plan"
        with pytest.raises(ConnectionError):
            maintenance.run(policy, remote, now)
        # The same day's next scheduler wake does not retry the network.
        assert (
            maintenance.run(policy, remote, now)["reason"] == "already_attempted_today"
        )
        assert remote.events == ["plan"]
    else:
        result = maintenance.run(policy, remote, now)
        assert result["status"] in {"skipped", "noop"}
        assert remote.events == ([] if mode == "outside" else ["plan"])
    assert sorted(p for p in policy.archives.glob("archive-*")) == [original]


def test_real_incremental_recovery_apply_and_zero_followup(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    project = workspace.create(owner, "retained", {"load": 1}, key="saved")
    policy, original = setup_store(tmp_path, workspace)
    orphan = workspace.blobs.put(b"unreferenced failed publication")
    remote = RemoteFixture(workspace)
    result = maintenance.run(
        policy, remote, dt.datetime(2026, 10, 31, 2, tzinfo=dt.UTC)
    )
    assert result["deleted_count"] == 1 and result["freed_bytes"] == 17
    assert remote.events == ["plan", "snapshot", "stage", "apply", "cleanup"]
    assert workspace.get(owner, project.id).inputs == {"load": 1}
    current = Path(result["archive"])
    recovered = archive.verify(current)["blobs"]
    assert isinstance(recovered, list) and orphan in recovered
    retained = project.input_sha256
    assert (current / "blobs" / retained[:2] / retained).stat().st_ino == (
        original / "blobs" / retained[:2] / retained
    ).stat().st_ino
    assert not list(policy.archives.glob(".incoming-*"))
    assert not (workspace.database.path.parent.parent / "remote-recovery").exists()
    remote.events.clear()
    assert (
        maintenance.run(policy, remote, dt.datetime(2026, 11, 1, 2, tzinfo=dt.UTC))[
            "status"
        ]
        == "noop"
    )
    assert remote.events == ["plan"]
    with pytest.raises(ValueError, match="maintenance_owner_changed"):
        maintenance.Archives(replace(policy, owner="b" * 32))


def test_apply_failure_cleans_owned_recovery_and_keeps_verified_point(
    workspace: Workspace, tmp_path: Path
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    workspace.blobs.put(b"orphan")
    remote = RemoteFixture(workspace)
    remote.fail = "apply"
    with pytest.raises(ConnectionError) as failure:
        maintenance.run(policy, remote, dt.datetime(2026, 10, 31, 2, tzinfo=dt.UTC))
    registry = json.loads((policy.archives / "RECOVERY-POINTS.json").read_text())
    assert archive.verify(Path(registry["latest_verified_recovery"]))
    assert remote.events[-1] == "cleanup"
    assert (
        maintenance.failure_result(failure.value, remote.last_action)["phase"]
        == "apply"
    )


def test_lost_snapshot_reply_reuses_published_recovery_instead_of_another_copy(
    workspace: Workspace, tmp_path: Path
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    workspace.blobs.put(b"orphan")
    remote = RemoteFixture(workspace)
    remote.fail_snapshot_ack = True
    with pytest.raises(ConnectionError):
        maintenance.run(policy, remote, dt.datetime(2026, 10, 31, 2, tzinfo=dt.UTC))
    assert len(list(policy.archives.glob("archive-*"))) == 2
    assert not list(policy.archives.glob(".incoming-*"))
    remote.fail_snapshot_ack = False
    result = maintenance.run(policy, remote, dt.datetime(2026, 11, 1, 2, tzinfo=dt.UTC))
    assert result["deleted_count"] == 1
    assert len(list(policy.archives.glob("archive-*"))) == 2


def test_another_source_registry_is_rejected_before_any_remote_call(
    workspace: Workspace, tmp_path: Path
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    path = policy.archives / "RECOVERY-POINTS.json"
    registry = json.loads(path.read_text())
    registry["source"]["host"] = "somewhere-else"
    path.write_text(json.dumps(registry))
    remote = RemoteFixture(workspace)
    with pytest.raises(ValueError, match="registry_source_mismatch"):
        maintenance.run(policy, remote, dt.datetime(2026, 10, 31, 2, tzinfo=dt.UTC))
    assert remote.events == []


def test_schedule_has_no_retry_daemon_and_keeps_utc_window_args(
    workspace: Workspace, tmp_path: Path
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    value = plistlib.loads(
        installer.rendered(policy, Path(sys.executable), OPS / "planner_maintenance.py")
    )
    assert value["StartInterval"] == 3600 and "KeepAlive" not in value
    assert value["ProgramArguments"][1] == "-B"
    assert value["ProgramArguments"][-6:] == [
        "--hour-utc",
        "2",
        "--window-minutes",
        "60",
        "--budget-seconds",
        "600",
    ]
    assert maintenance.failure_result(ConnectionError("secret"), "snapshot") == {
        "status": "error",
        "reason": "ConnectionError",
        "phase": "snapshot",
    }


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("Connection timed out during banner exchange", "ssh_banner_timeout"),
        ("user@private-host: Permission denied (publickey).", "ssh_auth_denied"),
        (
            "ssh: connect to host private-host port 22: Connection refused",
            "ssh_refused",
        ),
        ("unrecognized private diagnostic", "exit_255"),
    ],
)
def test_remote_plan_failure_records_only_the_diagnostic_category(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, message: str, reason: str
) -> None:
    policy = maintenance.Policy(
        "example", Path("/opt/linker-planner"), tmp_path, "a" * 32
    )
    remote = maintenance.Remote(policy)
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys;sys.stderr.write(sys.argv[1]);sys.exit(255)",
            message,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    monkeypatch.setattr(remote, "start", lambda *_args: child)
    with pytest.raises(RuntimeError) as failure:
        remote.call("plan")
    assert maintenance.failure_result(failure.value, "plan") == {
        "phase": "plan",
        "status": "error",
        "reason": f"remote_plan_{reason}",
    }
    assert child.returncode == 255


@pytest.mark.parametrize(
    ("command", "reason"),
    [
        (
            "runuser retention --apply --offline private-path",
            "offline_retention_timeout",
        ),
        ("systemctl stop private-unit", "subprocess_timeout"),
    ],
)
def test_remote_apply_timeout_records_only_the_operation_category(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, reason: str
) -> None:
    policy = maintenance.Policy(
        "example", Path("/opt/linker-planner"), tmp_path, "a" * 32
    )
    remote = maintenance.Remote(policy)
    message = (
        f"subprocess.TimeoutExpired: Command {command!r} timed out after 30 seconds\n"
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys;sys.stderr.write(sys.argv[1]);sys.exit(1)",
            message,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    monkeypatch.setattr(remote, "start", lambda *_args: child)
    with pytest.raises(RuntimeError) as failure:
        remote.call("apply")
    assert str(failure.value) == f"remote_apply_{reason}"
    assert "private" not in str(failure.value)


def test_native_automatic_guards_never_stop_on_busy_zero_or_missing_recovery(
    tmp_path: Path,
) -> None:
    operator = load("planner_release")
    (tmp_path / "selection.json").write_text(
        json.dumps({"current": str(tmp_path / "spec.json")})
    )
    events: list[str] = []
    plan = {"candidate_count": 0, "temporary_count": 0, "candidate_sha256": []}
    control = {"draining": False, "pending": 0}

    def call(*args: str) -> dict[str, Any]:
        events.append(args[0])
        return control if args[0] == "control" else plan

    target = SimpleNamespace(
        root=tmp_path, spec_file=tmp_path / "spec.json", operator=call
    )
    assert operator.maintain(target, apply=True, when_idle=True)["mode"] == "noop"
    control["pending"] = 1
    assert operator.maintain(target, apply=True, when_idle=True)["reason"] == "busy"
    control["pending"] = 0
    plan["candidate_count"] = 1
    with pytest.raises(ValueError, match="verified recovery"):
        operator.maintain(target, apply=True, when_idle=True)
    target.recovery_covers = lambda *_: (_ for _ in ()).throw(
        ValueError("coverage_missing")
    )
    with pytest.raises(ValueError, match="coverage_missing"):
        operator.maintain(
            target, apply=True, when_idle=True, recovery=tmp_path / "recovery"
        )
    target.recovery_covers = lambda *_: control.update(pending=1)
    target.preflight = lambda: {}
    target.probe = lambda: {}
    target.ready = lambda _: {"pid": 123}
    assert (
        operator.maintain(
            target, apply=True, when_idle=True, recovery=tmp_path / "recovery"
        )["reason"]
        == "busy"
    )
    assert not any(x in events for x in ["stop", "start", "drain"])


def test_N3_preserves_explicit_baseline_and_unknown_evidence(
    workspace: Workspace, owner: Actor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    workspace.create(owner, "protected", {"load": 1}, key="saved")
    policy, current = setup_store(tmp_path, workspace)
    store = maintenance.Archives(policy)
    baseline = policy.archives / "accepted-baseline.sqlite"
    shutil.copyfile(current / "workspace.sqlite", baseline)
    store.registry["entries"].append(
        {
            "kind": "db_only_snapshot",
            "path": str(baseline),
            "sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            "independent_local_CAS_binding": {"archive": str(current)},
        }
    )
    for day in [25, 26, 27]:
        point = policy.archives / f"archive-202610{day}T020000Z"
        manifest = archive.backup(workspace, point)
        store.registry["entries"].append(
            {
                "kind": "verified_workspace_archive",
                "path": str(point),
                "database": {"sha256": manifest["database_sha256"]},
                "manifest": {
                    "sha256": hashlib.sha256(
                        (point / "backup.json").read_bytes()
                    ).hexdigest()
                },
            }
        )
    unknown = policy.archives / "peer-unique-evidence.tar"
    unknown.write_bytes(b"unique")
    monkeypatch.setattr(
        maintenance.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(returncode=1, stdout=b""),
    )
    retired = policy.archives / "archive-20261025T020000Z"

    def partial(path: Path) -> None:
        assert path == retired
        (path / "workspace.sqlite").unlink()
        raise OSError("interrupted archive retirement")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance.shutil, "rmtree", partial)
        with pytest.raises(OSError, match="interrupted archive retirement"):
            store.rotate(current)
    assert retired.exists() and not (retired / "workspace.sqlite").exists()
    # Resume from durable intent, without trying to verify already removed data.
    store = maintenance.Archives(policy)
    store.rotate(current)
    assert len(store.entries()) == 3
    assert baseline.exists() and unknown.read_bytes() == b"unique"
    assert not (policy.archives / "archive-20261025T020000Z").exists()
    assert store.registry["entries"][1]["independent_local_CAS_binding"][
        "archive"
    ] == str(current)


@pytest.mark.parametrize("mode", ["complete", "keyboard", "TERM"])
def test_framed_pipe_ack_and_cancellation_reap_actual_child(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    remote = maintenance.Remote(policy)
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys,struct; h=b'{}'; sys.stdout.buffer.write(struct.pack('>I',len(h))+h+b'x'*9001);sys.stdout.buffer.flush(); assert sys.stdin.buffer.readline()==b'verified\\n';sys.stdout.buffer.write(b'ACKED\\n');sys.stdout.buffer.flush()",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        bufsize=0,
    )
    monkeypatch.setattr(remote, "start", lambda *_a: child)
    try:
        if mode == "keyboard":
            with pytest.raises(KeyboardInterrupt), remote.snapshot([]) as (_, read):
                assert read(9001) == b"x" * 9001
                raise KeyboardInterrupt
        elif mode == "TERM":
            previous = signal.getsignal(signal.SIGTERM)

            def interrupted_run() -> int:
                import os

                with remote.snapshot([]) as (_, read):
                    assert read(9001) == b"x" * 9001
                    os.kill(os.getpid(), signal.SIGTERM)
                raise AssertionError("TERM did not interrupt")

            monkeypatch.setattr(maintenance, "_main", interrupted_run)
            with pytest.raises(KeyboardInterrupt):
                maintenance.main()
            assert signal.getsignal(signal.SIGTERM) == previous
        else:
            with remote.snapshot([]) as (_, read):
                assert read(9001) == b"x" * 9001
            assert child.returncode == 0
    finally:
        maintenance._finish(child)
    assert child.poll() is not None


def test_recovery_reserve_is_used_while_sending_cleanup_request(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    remote = maintenance.Remote(policy)
    remote.deadline = time.monotonic() - 1
    remote.recovery_seconds = 30
    popen = subprocess.Popen

    def local_request(*_args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        return popen(
            [
                sys.executable,
                "-B",
                "-c",
                "import sys,json;print(json.dumps(json.loads(sys.stdin.buffer.readline())))",
            ],
            **kwargs,
        )

    monkeypatch.setattr(maintenance.subprocess, "Popen", local_request)
    child = remote.start("cleanup", {})
    try:
        stdout, _ = child.communicate(timeout=5)
        request = json.loads(stdout)
        assert request["action"] == "cleanup" and request["budget"] > 0
        assert child.returncode == 0
    finally:
        maintenance._finish(child)


def test_owner_survives_interrupted_directory_cleanup_and_foreign_is_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    root = tmp_path / "recovery"
    root.mkdir()
    (root / "workspace.sqlite").write_bytes(b"owned temporary snapshot")
    (root / "backup.json").write_bytes(b"owned temporary manifest")
    note = {"owner": "a" * 32, "database_sha256": "b" * 64, "manifest_sha256": "c" * 64}
    marker = maintenance.recovery_owner_file(root, note["owner"])
    marker.write_text(json.dumps(note))
    original = shutil.rmtree

    def partial(path: Path) -> None:
        (path / "workspace.sqlite").unlink()
        raise OSError("interrupted directory removal")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance.shutil, "rmtree", partial)
        with pytest.raises(OSError):
            maintenance.remove_recovery(root, note["owner"], note, os.getuid())
    assert marker.exists() and root.exists()
    assert maintenance.recovery_marker(root, note["owner"], os.getuid()) == note
    assert maintenance.remove_recovery(root, note["owner"], note, os.getuid())[
        "removed"
    ]
    assert not root.exists() and not marker.exists()
    root.mkdir()
    (root / "foreign").write_bytes(b"unique")
    foreign = {**note, "owner": "d" * 32}
    marker.write_text(json.dumps(foreign))
    with pytest.raises(RuntimeError, match="foreign_recovery_owner"):
        maintenance.remove_recovery(root, note["owner"], note, os.getuid())
    assert (root / "foreign").read_bytes() == b"unique" and marker.exists()
    # Test teardown owns the entire synthetic root; product code refused it.
    original(root)


def test_partial_owner_without_a_data_directory_only_cleans_its_metadata(
    tmp_path: Path,
) -> None:
    root = tmp_path / "recovery"
    owner = "a" * 32
    marker = maintenance.recovery_owner_file(root, owner)
    marker.write_bytes(b'{"owner":')
    note = maintenance.recovery_marker(root, owner, os.getuid())
    assert note["incomplete_marker"] is True
    maintenance.remove_recovery(root, owner, note, os.getuid())
    assert not marker.exists() and not root.exists()


def test_real_safe_status_and_system_sink_receive_error_once(
    workspace: Workspace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    events: list[str] = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "planner_maintenance",
            "--host",
            policy.host,
            "--archives",
            str(policy.archives),
            "--owner",
            policy.owner,
        ],
    )
    monkeypatch.setattr(
        maintenance.syslog, "syslog", lambda _level, message: events.append(message)
    )
    monkeypatch.setattr(
        maintenance,
        "run",
        lambda *_a: (_ for _ in ()).throw(ConnectionError("secret credential")),
    )
    assert maintenance.main() == 1
    assert len(events) == 1 and "secret" not in events[0]
    assert events[0] in capsys.readouterr().out
    value = json.loads(
        (policy.archives / ("maintenance-" + policy.owner + ".json")).read_text()
    )
    assert value["last_result"]["reason"] == "ConnectionError"
    assert len(json.dumps(value)) < 2048
    monkeypatch.setattr(maintenance, "run", lambda *_a: {"status": "noop"})
    assert maintenance.main() == 0
    monkeypatch.setattr(
        maintenance,
        "run",
        lambda *_a: {"status": "skipped", "reason": "outside_UTC_window"},
    )
    assert maintenance.main() == 0
    count = len(events)
    assert maintenance.main() == 0 and len(events) == count
    value = json.loads(
        (policy.archives / ("maintenance-" + policy.owner + ".json")).read_text()
    )
    assert value["last_result"]["reason"] == "ConnectionError"
    assert value["last_failure"]["reason"] == "ConnectionError"


@pytest.mark.parametrize("owned", [True, False])
def test_installer_resolves_bootstrap_timeout_before_restoring_disk_definition(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owned: bool
) -> None:
    policy, _ = setup_store(tmp_path, workspace)
    home = tmp_path / "home"
    target = home / "Library/LaunchAgents" / (installer.LABEL + ".plist")
    target.parent.mkdir(parents=True)
    prior = plistlib.dumps({"ProgramArguments": ["previous"]})
    target.write_bytes(prior)
    monkeypatch.setattr(installer.Path, "home", lambda: home)
    monkeypatch.setattr(installer.sys, "platform", "darwin")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install_planner_maintenance",
            "--host",
            policy.host,
            "--archives",
            str(policy.archives),
            "--owner",
            policy.owner,
            "--install",
        ],
    )
    loaded = False
    calls: list[str] = []

    def launchctl(
        arguments: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        nonlocal loaded
        action = arguments[1]
        calls.append(action)
        if action == "bootstrap":
            loaded = True
            raise subprocess.TimeoutExpired(arguments, 15)
        if action == "bootout":
            assert owned
            loaded = False
            return subprocess.CompletedProcess(arguments, 0, "", "")
        assert action == "print"
        if not loaded:
            return subprocess.CompletedProcess(
                arguments, 113, "", f'Could not find service "{installer.LABEL}"'
            )
        args = (
            plistlib.loads(target.read_bytes())["ProgramArguments"]
            if owned
            else ["foreign"]
        )
        text = "arguments = {\n" + "\n".join(args) + "\n}\n"
        return subprocess.CompletedProcess(arguments, 0, text, "")

    monkeypatch.setattr(installer.subprocess, "run", launchctl)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        installer.main()
    if owned:
        assert not loaded and "bootout" in calls and target.read_bytes() == prior
    else:
        assert loaded and "bootout" not in calls and target.read_bytes() != prior
        assert "cleanup unconfirmed" in caught.value.__notes__[0]
