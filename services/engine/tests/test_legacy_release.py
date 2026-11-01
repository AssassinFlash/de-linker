"""Reader transaction against real source files and authenticated loopback HTTP.

uv/systemd are bounded stand-ins; no service, existing cache or production host
is touched. The separate native probe test executes the real locked interpreter.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from linker_engine.version import digest, source_bytes

SPEC = importlib.util.spec_from_file_location(
    "legacy_release", Path(__file__).parents[1] / "ops/legacy_release.py"
)
assert SPEC is not None and SPEC.loader is not None
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)
OLD = "20261101T010000000000Z-11111111"
NEW = "20261101T020000000000Z-22222222"


def oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


class Machine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[list[str]] = []
        self.failure = ""
        self.running = OLD
        self.active = True
        self.timer = "active"
        self.trigger = "10"
        self.worker_start = "10"
        self.worker_exit = "10"
        self.worker_result = "success"
        self.feed = b'{"source_revision":"source","compatibility_revision":"contract"}'
        self.original = {
            "src/linker_engine/reader.py": b"old source\n",
            "data/plz_de.csv.gz": b"owned geo source",
            "pyproject.toml": b"project",
            "uv.lock": b"locked",
        }
        self.new = {**self.original, "src/linker_engine/reader.py": b"new source\n"}
        (root / OLD).mkdir(parents=True)
        for name, data in self.original.items():
            path = root / OLD / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o444)
        (root / "current").symlink_to(OLD)
        (root / "state").mkdir()
        (root / "ops").mkdir()
        (root / "ops/sync-feed.py").write_text(
            "PROBE_PYTHON = " + repr(str(root / "current/.venv/bin/python")) + "\n"
        )
        machine = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.headers.get("X-Linker-Service-Token") != "fixture-token":
                    self.send_error(401)
                    return
                receipt = machine.receipt(root / machine.running)
                if self.path.startswith("/resource/version"):
                    data = {
                        key: receipt[key]
                        for key in (
                            "version",
                            "source_revision",
                            "compatibility_revision",
                            "prepared_products",
                        )
                    }
                    if machine.failure == "loaded" and machine.running == NEW:
                        data["version"] = "wrong-loaded-generation"
                else:
                    data = receipt["geo"]
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = int(self.server.server_address[1])
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )
        self.thread.start()

    def receipt(self, path: Path) -> dict[str, Any]:
        return {
            "version": digest(
                source_bytes(path / "src/linker_engine"), self.feed, b"{}"
            ),
            "source_revision": json.loads(self.feed)["source_revision"],
            "compatibility_revision": "contract",
            "prepared_products": [{"product_id": 7, "product_revision": "p"}],
            "feed_sha256": hashlib.sha256(self.feed).hexdigest(),
            "compatibility_sha256": hashlib.sha256(b"{}").hexdigest(),
            "geo": {
                "plz": "10115",
                "latitude": 52.5,
                "longitude": 13.4,
                "state": "DE-BE",
                "place": "Berlin",
            },
        }

    def archive(self) -> bytes:
        manifest = {
            "revision": "2" * 40,
            "blobs": {n: oid(v) for n, v in self.new.items()},
            "baseline": {
                "revision": "1" * 40,
                "blobs": {n: oid(v) for n, v in self.original.items()},
            },
        }
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w") as tar:
            for name, data in {
                **self.new,
                ops.MANIFEST: json.dumps(manifest).encode(),
            }.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return output.getvalue()

    def command(self, args: list[str], **kwargs: Any) -> bytes:
        self.calls.append(args)
        if args[0].endswith("/uv"):
            assert ops.selected(self.root) == OLD
            candidate = Path(args[-1])
            assert candidate.parent == self.root
            if self.failure == "uv":
                raise ops.OperatorError(
                    args, b"locked build failed", 17, "prepare.locked_environment"
                )
            path = candidate / ".venv/bin/python"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("locked interpreter fixture")
        elif args[:2] == ["systemctl", "stop"]:
            if args[-1] == ops.TIMER:
                self.timer = "inactive"
            if args[-1] == ops.SERVICE:
                self.active = False
        elif args[:2] == ["systemctl", "start"]:
            if args[-1] == ops.TIMER:
                self.timer = "active"
            if args[-1] == ops.SERVICE:
                name = ops.selected(self.root)
                if name == OLD and self.failure == "old-start-once":
                    self.failure = ""
                    raise ops.OperatorError(
                        args, b"prior unit startup failed", 19, "rollback.start"
                    )
                if name == NEW and self.failure == "start":
                    raise ops.OperatorError(
                        args, b"unit startup failed", 19, "activate.start"
                    )
                self.running = name
                self.active = True
        else:
            raise AssertionError("unexpected host command")
        return b""

    def unit(self, name: str) -> dict[str, str]:
        if name == ops.SERVICE:
            return {
                "ActiveState": "active" if self.active else "inactive",
                "SubState": "running",
                "MainPID": "55",
                "ExecStart": str(self.root / "current/.venv/bin/python"),
            }
        if name == ops.TIMER:
            return {
                "ActiveState": self.timer,
                "UnitFileState": "enabled",
                "Unit": ops.WORKER,
                "LastTriggerUSecMonotonic": "2w 23h 57min 28.995211s",
            }
        return {
            "ActiveState": "inactive",
            "ExecStart": str(self.root / "ops/sync-feed.py"),
            "ExecMainStatus": "0",
            "Result": self.worker_result,
            "ExecMainStartTimestampMonotonic": self.worker_start,
            "ExecMainExitTimestampMonotonic": self.worker_exit,
        }


@pytest.fixture
def machine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Machine]:
    value = Machine(tmp_path / "engine")
    monkeypatch.setattr(ops, "command", value.command)
    monkeypatch.setattr(ops, "unit", value.unit)
    monkeypatch.setattr(ops, "timer_tick", lambda: int(value.trigger))
    monkeypatch.setattr(ops, "probe", lambda path, env: value.receipt(path))
    monkeypatch.setattr(ops, "referenced", lambda path: False)
    monkeypatch.setattr(
        ops,
        "check_process",
        lambda root, name: (
            {"pid": "55", "cwd": str(root / name)}
            if value.active and value.running == name
            else (_ for _ in ()).throw(RuntimeError("wrong process"))
        ),
    )
    # Exercise all real HTTP/identity checks once; omit only the startup retry delay.
    monkeypatch.setattr(ops, "ready", ops.readback)
    try:
        yield value
    finally:
        value.server.shutdown()
        value.server.server_close()
        value.thread.join(timeout=2)
        assert not value.thread.is_alive()


def prepare(machine: Machine) -> None:
    ops.prepare(
        machine.root,
        NEW,
        OLD,
        machine.archive(),
        {"GENIE_SERVICE_TOKEN": "fixture-token"},
    )


def activate(machine: Machine) -> dict[str, Any]:
    result: dict[str, Any] = ops.activate(
        machine.root, NEW, OLD, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port
    )
    return result


def test_final_path_build_precedes_selection_and_adopts_real_manifestless_baseline(
    machine: Machine,
) -> None:
    before = {n: (machine.root / OLD / n).stat().st_mode for n in machine.original}
    prepare(machine)
    assert ops.selected(machine.root) == OLD
    assert not (machine.root / OLD / ops.MANIFEST).exists()
    assert before == {
        n: (machine.root / OLD / n).stat().st_mode for n in machine.original
    }
    assert all(args[0] != "systemctl" for args in machine.calls)
    result = activate(machine)
    assert result["loaded"]["version"] == machine.receipt(machine.root / NEW)["version"]
    assert ops.selected(machine.root) == NEW and machine.timer == "active"
    assert not any("genie" in " ".join(args) for args in machine.calls)


@pytest.mark.parametrize("failure", ["unpack", "uv", "probe"])
def test_prepare_failures_leave_no_unselected_orphan_or_timer_change(
    machine: Machine, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    if failure == "uv":
        machine.failure = "uv"
    if failure == "probe":
        monkeypatch.setattr(
            ops,
            "probe",
            lambda path, env: (_ for _ in ()).throw(RuntimeError("probe failed")),
        )
    if failure == "unpack":
        original = Path.write_bytes

        def fail(path: Path, data: bytes) -> int:
            if str(machine.root / NEW / "src") in str(path):
                raise OSError("unpack failed")
            return original(path, data)

        monkeypatch.setattr(Path, "write_bytes", fail)
    with pytest.raises((OSError, RuntimeError)):
        prepare(machine)
    assert not (machine.root / NEW).exists()
    assert not (machine.root / ops.PREPARING).exists()
    assert not list(machine.root.glob(".reader-owner-*"))
    assert ops.selected(machine.root) == OLD and machine.timer == "active"


def test_interrupted_owned_partial_without_manifest_is_recovered(
    machine: Machine,
) -> None:
    import signal
    import time

    marker = machine.root / "fixture-unpack-started"
    child_code = """import sys,time,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('release_child',sys.argv[1]);ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
root=Path(sys.argv[2]);original=Path.write_bytes
new=sys.argv[3];old=sys.argv[4]
def interrupted(path,data):
 if str(root/new/'src') in str(path):
  (root/'fixture-unpack-started').write_text('source owner persisted before payload')
  time.sleep(20)
 return original(path,data)
Path.write_bytes=interrupted
ops.prepare(root,new,old,sys.stdin.buffer.read(),{'GENIE_SERVICE_TOKEN':'fixture-token'})
"""
    operator = Path(__file__).parents[1] / "ops/legacy_release.py"
    with subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            child_code,
            str(operator),
            str(machine.root),
            NEW,
            OLD,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": "/usr/bin:/bin"},
        start_new_session=True,
    ) as child:
        assert child.stdin is not None
        child.stdin.write(machine.archive())
        child.stdin.close()
        child.stdin = None
        try:
            deadline = time.monotonic() + 5
            while not marker.exists():
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise AssertionError("owned source-write boundary was not reached")
                time.sleep(0.01)
            assert (machine.root / NEW / ops.OWNER).is_file()
            assert not (machine.root / NEW / ops.MANIFEST).exists()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.communicate(timeout=5)
    assert child.returncode == -signal.SIGKILL
    assert (machine.root / ops.PREPARING).exists()
    witness = machine.root / NEW / "operator-note.txt"
    witness.write_text("unique operator witness")
    with pytest.raises(RuntimeError, match="unknown preparation data preserved"):
        prepare(machine)
    assert witness.read_text() == "unique operator witness"
    assert (machine.root / ops.PREPARING).exists()
    witness.unlink()  # fixture owns this exact witness; no operator cleanup is inferred
    prepare(machine)
    assert (machine.root / NEW / ops.MANIFEST).is_file()
    assert not (machine.root / ops.PREPARING).exists()


@pytest.mark.parametrize("failure", ["start", "loaded"])
def test_failed_switch_restores_exact_old_reader_and_timer(
    machine: Machine, failure: str
) -> None:
    prepare(machine)
    baseline = machine.receipt(machine.root / OLD)
    machine.failure = failure
    with pytest.raises(RuntimeError):
        activate(machine)
    assert (
        ops.selected(machine.root) == OLD and machine.running == OLD and machine.active
    )
    assert machine.timer == "active"
    assert (
        ops.get(
            machine.port,
            "/resource/version?ready=1",
            {"GENIE_SERVICE_TOKEN": "fixture-token"},
        )["version"]
        == baseline["version"]
    )
    assert json.loads((machine.root / ops.STATE).read_text())["phase"] == "restored"


def test_feed_drift_refuses_before_engine_stop(machine: Machine) -> None:
    prepare(machine)
    machine.feed = b'{"source_revision":"changed"}'
    with pytest.raises(RuntimeError, match="changed after preparation"):
        activate(machine)
    assert ["systemctl", "stop", ops.SERVICE] not in machine.calls
    assert ops.selected(machine.root) == OLD and machine.timer == "active"


def test_rollback_restores_exact_old_version_and_refuses_changed_feed(
    machine: Machine,
) -> None:
    prepare(machine)
    activate(machine)
    machine.feed = b'{"source_revision":"changed"}'
    calls = len(machine.calls)
    with pytest.raises(RuntimeError, match="rollback feed/coverage changed"):
        ops.rollback(
            machine.root, NEW, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port
        )
    assert ["systemctl", "stop", ops.SERVICE] not in machine.calls[calls:]
    assert ops.selected(machine.root) == NEW and machine.timer == "active"
    machine.feed = b'{"source_revision":"source","compatibility_revision":"contract"}'
    result = ops.rollback(
        machine.root, NEW, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port
    )
    assert result["restored"] and ops.selected(machine.root) == OLD
    assert machine.timer == "active"
    with pytest.raises(RuntimeError, match="current/previous runtime is protected"):
        ops.discard(machine.root, NEW, "2" * 40)
    assert (machine.root / NEW).exists()
    assert "_candidate" not in json.loads((machine.root / ops.OWNED).read_text())
    count = len(machine.calls)
    with pytest.raises(RuntimeError, match="cannot be prepared again"):
        prepare(machine)
    assert len(machine.calls) == count
    another = "20261101T030000000000Z-33333333"
    ops.prepare(
        machine.root,
        another,
        OLD,
        machine.archive(),
        {"GENIE_SERVICE_TOKEN": "fixture-token"},
    )
    assert (machine.root / another).is_dir()


def test_real_timer_requires_completed_current_worker_not_stale_success(
    machine: Machine,
) -> None:
    prepare(machine)
    activate(machine)
    machine.trigger = "20"
    with pytest.raises(RuntimeError, match="no completed natural worker"):
        ops.verify(
            machine.root, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port, 0.001
        )
    machine.worker_start, machine.worker_exit = "21", "22"
    result = ops.verify(
        machine.root, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port, 0.01
    )
    assert result["worker_verified"]


def test_prune_protects_pytest_interpreter_unknown_dirs_and_current_pair(
    machine: Machine,
) -> None:
    prepare(machine)
    activate(machine)
    state = json.loads((machine.root / ops.STATE).read_text())
    state["worker_verified"] = True
    ops.write(machine.root / ops.STATE, state)
    owners = json.loads((machine.root / ops.OWNED).read_text())
    older = "20261001T000000000000Z"
    protected = "20260901T000000000000Z"
    unknown = "20260801T000000000000Z"
    for name in (older, protected, unknown):
        path = machine.root / name
        path.mkdir()
        (path / "pyproject.toml").write_bytes(b"owned")
        if name != unknown:
            owners[name] = {
                "revision": "1" * 40,
                "blobs": {"pyproject.toml": oid(b"owned")},
            }
    owners["_protected"] = {protected: "active Linux pytest interpreter dependency"}
    ops.write(machine.root / ops.OWNED, owners)
    result = ops.prune(machine.root, {})
    assert result["retired"] == [older] and unknown in result["unknown_preserved"]
    assert all(
        (machine.root / name).exists() for name in (OLD, NEW, protected, unknown)
    )


def test_safe_command_diagnostics_keep_phase_and_never_print_stderr_secrets() -> None:
    token = "private-test-value-not-a-real-key"
    with pytest.raises(ops.OperatorError) as caught:
        ops.command(
            [
                sys.executable,
                "-c",
                f'import sys;print("ModuleNotFoundError {token}",file=sys.stderr);sys.exit(17)',
            ],
            phase="prepare.native_reader_probe",
        )
    detail = caught.value.diagnostic
    assert (
        detail["phase"] == "prepare.native_reader_probe" and detail["exit_code"] == 17
    )
    assert "module_missing" in detail["categories"]
    assert token not in json.dumps(detail)
    assert token.encode() in caught.value.stderr


def test_source_archive_uses_one_real_git_blob_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    source = repository / "services/engine"
    source.mkdir(parents=True)
    for name, data in {
        "data/plz_de.csv.gz": b"geo",
        "pyproject.toml": b"project",
        "uv.lock": b"lock",
        "ops/legacy_release.py": (
            Path(__file__).parents[1] / "ops/legacy_release.py"
        ).read_bytes(),
    }.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "user.name=fixture",
            "commit",
            "-qm",
            "source",
        ],
        check=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    command = ops.command
    calls = []

    def count(args: list[str], **kwargs: Any) -> bytes:
        calls.append(args)
        output: bytes = command(args, **kwargs)
        return output

    monkeypatch.setattr(ops, "command", count)
    raw = ops.archive(repository, revision, revision)
    assert len([args for args in calls if "cat-file" in args]) == 1
    assert any("--batch" in args for args in calls)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        handle = tar.extractfile("data/plz_de.csv.gz")
        assert handle is not None and handle.read() == b"geo"


def test_ready_never_repeats_an_answered_identity_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def mismatch(*args: Any) -> dict[str, Any]:
        calls.append(1)
        raise RuntimeError("actual Engine loaded receipt differs")

    monkeypatch.setattr(ops, "readback", mismatch)
    with pytest.raises(RuntimeError, match="loaded receipt differs"):
        ops.ready(tmp_path, NEW, {}, {}, 8901)
    assert len(calls) == 1


def test_only_not_yet_bound_socket_is_a_startup_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def binding(*args: Any) -> dict[str, Any]:
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionRefusedError("socket not bound")
        return {"loaded": {"version": "ready"}}

    monkeypatch.setattr(ops, "readback", binding)
    monkeypatch.setattr(ops.time, "sleep", lambda delay: None)
    assert ops.ready(tmp_path, NEW, {}, {}, 8901)["loaded"]["version"] == "ready"
    assert len(calls) == 2


def test_retirement_detects_mapped_library_even_without_open_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "release with spaces"
    root.mkdir()
    proc = tmp_path / "proc"
    pid = proc / "123"
    pid.mkdir(parents=True)
    (pid / "cmdline").write_bytes(b"/usr/bin/python\0")
    mapped = (str(root / "lib.so") + " (deleted)").replace(" ", "\\040")
    (pid / "maps").write_text("70000000-70001000 r-xp 0 00:00 1 " + mapped + "\n")
    original = Path
    monkeypatch.setattr(
        ops, "Path", lambda value: proc if value == "/proc" else original(value)
    )
    assert ops.referenced(root)


def test_native_locked_probe_loads_real_feed_publication_and_geo(
    tmp_path: Path,
) -> None:
    from conftest import publication_feed, publication_manifest

    import linker_engine
    from linker_engine import geo

    project = Path(linker_engine.__file__).resolve().parents[2]
    fixtures = Path(__file__).parent / "fixtures"
    feed = publication_feed(
        json.loads((fixtures / "feed.json").read_text()),
        json.loads((fixtures / "compatibility.json").read_text()),
    )
    manifest = publication_manifest(feed)
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            calls.append(self.path)
            raw = json.dumps(manifest).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()
    feed_path = tmp_path / "feed.json"
    feed_path.write_text(json.dumps(feed))
    compat = tmp_path / "compatibility.json"
    compat.write_text(json.dumps(feed["compatibility"]))
    env = {
        "PATH": "/usr/bin:/bin",
        "GENIE_SERVICE_TOKEN": "fixture-token",
        "LINKER_ENGINE_FEED": str(feed_path),
        "LINKER_ENGINE_COMPATIBILITY": str(compat),
        "LINKER_ENGINE_CACHE": str(tmp_path / "cache"),
        "LINKER_PUBLICATION_URL": f"http://127.0.0.1:{server.server_address[1]}/manifest",
        "NO_PROXY": "127.0.0.1",
    }
    try:
        result = ops.probe(project, env)
        canonical = json.dumps(
            feed["compatibility"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        assert result["version"] == digest(
            source_bytes(project / "src/linker_engine"),
            feed_path.read_bytes(),
            canonical,
        )
        assert result["source_revision"] == feed["source_revision"]
        place = geo.lookup("10115")
        assert (
            place is not None
            and result["prepared_products"]
            and result["geo"]["latitude"] == place.latitude
        )
        assert calls == ["/manifest"]
        assert not (tmp_path / "cache").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_timer_uses_exact_dbus_uint64_not_systemctl_formatted_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def bus(args: list[str], **kwargs: Any) -> bytes:
        calls.append(args)
        if "GetUnit" in args:
            return b'o "/org/freedesktop/systemd1/unit/linker_2dengine_2dfeed_2dsync_2etimer"\n'
        return b"t 1295848995211\n"

    monkeypatch.setattr(ops, "command", bus)
    assert ops.timer_tick() == 1295848995211
    assert len(calls) == 2 and calls[-1][-1] == "LastTriggerUSecMonotonic"


@pytest.mark.parametrize("phase", ["quiescing", "switching"])
def test_interrupted_before_selector_recovers_stopped_old_process_and_timer(
    machine: Machine, phase: str
) -> None:
    prepare(machine)
    timer = machine.unit(ops.TIMER)
    state = {
        "current": NEW,
        "previous": OLD,
        "phase": phase,
        "timer": timer,
        "timer_baseline": 10,
        "worker_verified": False,
    }
    if phase == "switching":
        state.update(
            before=machine.receipt(machine.root / OLD),
            after=machine.receipt(machine.root / NEW),
        )
    ops.write(machine.root / ops.STATE, state)
    machine.active = False
    machine.timer = "inactive"
    assert ops.selected(machine.root) == OLD
    result = ops.rollback(
        machine.root, OLD, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port
    )
    assert result["restored"] and result["current"] == OLD
    assert machine.active and machine.running == OLD and machine.timer == "active"
    assert json.loads((machine.root / ops.STATE).read_text())["current"] == OLD


def test_failed_rollback_target_start_reinstates_working_current_reader(
    machine: Machine,
) -> None:
    prepare(machine)
    activate(machine)
    machine.failure = "old-start-once"
    with pytest.raises(ops.OperatorError):
        ops.rollback(
            machine.root, NEW, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port
        )
    assert (
        ops.selected(machine.root) == NEW and machine.running == NEW and machine.active
    )
    assert machine.timer == "active"
    assert json.loads((machine.root / ops.STATE).read_text())["phase"] == "ready"


def test_one_prepared_candidate_limit_allows_same_name_git_reuse_only(
    machine: Machine,
) -> None:
    prepare(machine)
    # An earlier verified release state must not authorize deleting a new candidate.
    ops.write(
        machine.root / ops.STATE,
        {
            "current": OLD,
            "previous": "20261031T010000000000Z",
            "phase": "ready",
            "worker_verified": True,
        },
    )
    assert ops.prune(machine.root, {})["retired"] == []
    assert (machine.root / NEW).exists()
    original_inode = (machine.root / NEW).stat().st_ino
    environment = machine.root / NEW / ".venv"
    external = machine.root / "external-fixture-environment"
    environment.rename(external)
    environment.symlink_to(external)
    count = len(machine.calls)
    with pytest.raises(RuntimeError, match="linked candidate environment"):
        prepare(machine)
    assert len(machine.calls) == count and (external / "bin/python").is_file()
    environment.unlink()
    external.rename(environment)
    owners = json.loads((machine.root / ops.OWNED).read_text())
    owners["_protected"] = {NEW: "fixture external interpreter dependency"}
    ops.write(machine.root / ops.OWNED, owners)
    with pytest.raises(
        RuntimeError, match="protected interpreter cannot be prepared again"
    ):
        prepare(machine)
    owners["_protected"] = {}
    ops.write(machine.root / ops.OWNED, owners)
    prepare(machine)
    assert (machine.root / NEW).stat().st_ino == original_inode
    another = "20261101T030000000000Z-33333333"
    with pytest.raises(RuntimeError, match="one prepared candidate already exists"):
        ops.prepare(
            machine.root,
            another,
            OLD,
            machine.archive(),
            {"GENIE_SERVICE_TOKEN": "fixture-token"},
        )
    assert not (machine.root / another).exists()
    assert json.loads((machine.root / ops.OWNED).read_text())["_candidate"] == NEW
    ops.discard(machine.root, NEW, "2" * 40)
    assert not (machine.root / NEW).exists()
    assert "_candidate" not in json.loads((machine.root / ops.OWNED).read_text())


def test_discard_never_removes_selected_or_referenced_candidate(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare(machine)
    monkeypatch.setattr(ops, "referenced", lambda path: path == machine.root / NEW)
    count = len(machine.calls)
    with pytest.raises(
        RuntimeError, match="referenced runtime cannot be prepared again"
    ):
        prepare(machine)
    assert len(machine.calls) == count
    with pytest.raises(RuntimeError, match="referenced"):
        ops.discard(machine.root, NEW, "2" * 40)
    assert (machine.root / NEW).exists()
    monkeypatch.setattr(ops, "referenced", lambda path: False)
    activate(machine)
    with pytest.raises(RuntimeError, match="current/previous runtime is protected"):
        ops.discard(machine.root, NEW, "2" * 40)
    assert ops.selected(machine.root) == NEW


def test_successful_worker_with_bad_loaded_receipt_cannot_enable_prune(
    machine: Machine,
) -> None:
    prepare(machine)
    activate(machine)
    machine.trigger = "20"
    machine.worker_start = "21"
    machine.worker_exit = "22"
    machine.failure = "loaded"
    with pytest.raises(RuntimeError, match="loaded receipt differs"):
        ops.verify(
            machine.root, {"GENIE_SERVICE_TOKEN": "fixture-token"}, machine.port, 0.01
        )
    assert (
        json.loads((machine.root / ops.STATE).read_text())["worker_verified"] is False
    )


def test_candidate_environment_drops_apify_aliases_without_changing_needed_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(os, "environ", {"PATH": "/usr/bin:/bin"})
    monkeypatch.setenv("APIFY_API_TOKEN", "investigation-private-value")
    monkeypatch.setenv("APIFY_BASE_URL", "https://investigation.invalid")
    monkeypatch.setenv("NEEDED_DEPLOYMENT_VALUE", "preserved")
    assert ops.runtime_environment({"UNRELATED_APIFY_HINT": "retained"}) == {
        "UNRELATED_APIFY_HINT": "retained"
    }
    raw = ops.command(
        [
            sys.executable,
            "-c",
            'import os,json;print(json.dumps({"apify":[k for k in os.environ if k.upper().startswith("APIFY_")],"needed":os.environ["NEEDED_DEPLOYMENT_VALUE"]}))',
        ]
    )
    assert json.loads(raw) == {"apify": [], "needed": "preserved"}
    assert os.environ["APIFY_API_TOKEN"] == "investigation-private-value"
    path = tmp_path / "runtime.env"
    path.write_text(
        "GENIE_SERVICE_TOKEN=fixture-token\nAPIFY_API_KEY=misplaced-investigation-key\n"
    )
    path.chmod(0o600)
    with pytest.raises(ValueError, match="investigation-only provider alias"):
        ops.environment(path)
    path.write_text(
        "GENIE_SERVICE_TOKEN=fixture-token\nLINKER_ENGINE_FEED=/owned/feed.json\n"
    )
    values = ops.environment(path)
    assert values["LINKER_ENGINE_FEED"] == "/owned/feed.json"
    assert values["GENIE_SERVICE_TOKEN"] == "fixture-token"
    assert not any(key.upper().startswith("APIFY_") for key in values)


def test_real_python_c_status_inspects_stopped_old_selector_without_file_global(
    machine: Machine, tmp_path: Path
) -> None:
    import shlex

    binary = tmp_path / "bin"
    binary.mkdir()
    systemctl = binary / "systemctl"
    systemctl.write_text(
        '#!/bin/sh\nprintf "%s\\n" '
        + shlex.join(
            [
                "ActiveState=inactive",
                "MainPID=0",
                "Unit=" + ops.WORKER,
                "LastTriggerUSecMonotonic=2w 23h 57min 28.995211s",
            ]
        )
        + "\n"
    )
    systemctl.chmod(0o755)
    private = tmp_path / "runtime.env"
    private.write_text("GENIE_SERVICE_TOKEN=fixture-token\n")
    private.chmod(0o600)
    operator = Path(__file__).parents[1] / "ops/legacy_release.py"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            operator.read_text(),
            "status",
            "--remote",
            "--root",
            str(machine.root),
            "--env-file",
            str(private),
            "--port",
            str(machine.port),
        ],
        env={
            "PATH": str(binary) + os.pathsep + "/usr/bin:/bin",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status["selected"] == OLD and status["actual_available"] is False
    assert status["source"]["data"][0]["path"].startswith(
        str(machine.root / OLD / "data")
    )
