"""Operator boundary and one lifecycle; numerical and browser evidence is reused."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from linker_engine.planning.project_input_contracts import INPUT_CONTRACT
from linker_engine.planning.project_input_floor import (
    check_project_input_contracts,
    read_project_input_floor,
)

SPEC = importlib.util.spec_from_file_location(
    "planner_release", Path(__file__).resolve().parents[1] / "ops/planner_release.py"
)
assert SPEC is not None and SPEC.loader is not None
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)


def test_prepared_policy_is_frozen_and_numerical_operator_has_no_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ops.pwd,
        "getpwnam",
        lambda _: SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid()),
    )
    root = tmp_path / "linker-planner-test"
    release = root / "releases" / ("a" * 64)
    private = release / ".deploy"
    private.mkdir(parents=True)
    (release / ".venv/bin").mkdir(parents=True)
    (release / ".venv/bin/python").touch()
    spec = {
        "schema_version": 1,
        "root": str(root),
        "release": str(release),
        "prefix": root.name,
        "port": 18911,
        "user": "planner-test",
        "start_seconds": 3,
        "stop_seconds": 3,
    }
    (private / "spec.json").write_text(json.dumps(spec))
    (private / "runtime.json").write_text(
        json.dumps({"directory": str(root / "state/workspace")})
    )
    (private / "worker.json").write_text(
        json.dumps({"ready_file": str(root / "run/worker.ready.json")})
    )
    feed, compat = tmp_path / "feed.json", tmp_path / "compat.json"
    feed.write_text("{}")
    compat.write_text("{}")
    env = tmp_path / "source.env"
    env.write_text(
        ops.env_text(
            {
                "GENIE_SERVICE_TOKEN": "fixture-secret",
                "APIFY_TOKEN": "must-not-copy",
                "LINKER_PUBLICATION_PASSWORD": "must-not-copy",
                "LINKER_ENGINE_FEED": str(feed),
                "LINKER_ENGINE_COMPATIBILITY": str(compat),
            }
        )
    )
    calls = []
    identity = {
        "schema_version": 1,
        "storage_schema_version": 5,
        "runtime_sha256": "c" * 64,
    }

    def run(
        arguments: list[str], *, env: dict[str, str] | None = None, timeout: float = 30
    ) -> str:
        calls.append((arguments, env))
        if any("pragma user_version" in item for item in arguments):
            return "5"
        if "-c" in arguments:
            return json.dumps(
                {
                    "prefix": str(release / ".venv"),
                    "package": str(release / "src/linker_engine/__init__.py"),
                }
            )
        return json.dumps(identity)

    monkeypatch.setattr(ops, "command", run)
    monkeypatch.setattr(ops.os, "chown", lambda *_: None)
    target = ops.Release(private / "spec.json")
    target.prepare(
        env, "https://fixture.invalid/wp-json/linker/v1/publication/manifest"
    )
    assert set(ops.environment(private / "http.env")) == {
        "GENIE_SERVICE_TOKEN",
        "LINKER_ENGINE_FEED",
        "LINKER_ENGINE_COMPATIBILITY",
        "LINKER_PUBLICATION_URL",
        "LINKER_ENGINE_CACHE",
        "LINKER_ENGINE_GATE_MODE",
        "LINKER_PLANNER_CONFIG",
    }
    operator_calls = [(a, e) for a, e in calls if a[0] == "runuser"]
    assert operator_calls and all(
        e is not None and "GENIE_SERVICE_TOKEN" not in e and "APIFY_TOKEN" not in e
        for _, e in operator_calls
    )
    assert any(
        "Services(Settings.from_environment(),SOURCE)" in a[-1]
        for a, _ in operator_calls
    )
    assert os.stat(private / "http.env").st_mode & 0o777 == 0o600
    target.preflight()
    # Latest inputs may omit a feature while an immutable older revision still
    # needs it. Duplicate CAS references are read once; no schema/open upgrade.
    store = root / "state/workspace"
    database = store / "workspace.sqlite"
    historical = b'{"installation":{"pv_string_links":[]}}'
    latest = b"{}"
    hashes = []
    for body in (historical, latest):
        sha = hashlib.sha256(body).hexdigest()
        path = store / "blobs" / sha[:2] / sha
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        hashes.append(sha)
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE projects(id TEXT, revision INTEGER)")
        db.execute(
            "CREATE TABLE revisions(project_id TEXT, number INTEGER, input_sha256 TEXT)"
        )
        db.execute("PRAGMA user_version=5")
        db.execute("INSERT INTO projects VALUES (?,3)", ("a" * 32,))
        db.executemany(
            "INSERT INTO revisions VALUES (?,?,?)",
            [
                ("a" * 32, index, sha)
                for index, sha in enumerate([hashes[0], hashes[1], hashes[1]], 1)
            ],
        )
    before_storage = {
        str(path.relative_to(store)): path.read_bytes()
        for path in store.rglob("*")
        if path.is_file()
    }
    floor = read_project_input_floor(store)
    assert floor["required_input_contracts"] == [INPUT_CONTRACT]
    assert floor["retained_revision_count"] == 3 and floor["retained_input_count"] == 2
    assert check_project_input_contracts(store, [INPUT_CONTRACT]) == floor
    with pytest.raises(ValueError, match="does not support"):
        check_project_input_contracts(store, [])
    assert before_storage == {
        str(path.relative_to(store)): path.read_bytes()
        for path in store.rglob("*")
        if path.is_file()
    }
    missing = store / "blobs" / hashes[0][:2] / hashes[0]
    missing.unlink()
    with pytest.raises(ValueError, match="could not be verified"):
        read_project_input_floor(store)
    missing.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="could not be verified"):
        read_project_input_floor(store)
    missing.write_bytes(historical)
    ordinary_command = run

    def unreadable_source(arguments: list[str], **kwargs: Any) -> str:
        if "Services(Settings.from_environment(),SOURCE)" in arguments[-1]:
            raise RuntimeError("operator command failed: runuser")
        return ordinary_command(arguments, **kwargs)

    monkeypatch.setattr(ops, "command", unreadable_source)
    with pytest.raises(RuntimeError, match="runuser"):
        target.preflight()
    monkeypatch.setattr(ops, "command", ordinary_command)
    monkeypatch.setattr(
        ops,
        "unit_state",
        lambda _: {"FragmentPath": "/usr/lib/systemd/system/foreign.service"},
    )
    with pytest.raises(RuntimeError, match="another deployment"):
        target.own_units()
    external = tmp_path / "other-service"
    external.mkdir()
    (root / "run").rmdir()
    (root / "run").symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        target.preflight()
    (root / "run").unlink()
    (root / "run").mkdir(mode=0o700)
    monkeypatch.setattr(
        ops.pwd, "getpwnam", lambda _: SimpleNamespace(pw_uid=0, pw_gid=0)
    )
    with pytest.raises(ValueError, match="non-root"):
        ops.Release(private / "spec.json")
    monkeypatch.setattr(
        ops.pwd,
        "getpwnam",
        lambda _: SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid()),
    )
    requests = []

    class RejectedSocket:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            requests.append((host, port))

        def request(self, *args: Any, **kwargs: Any) -> None:
            pass

        def getresponse(self) -> SimpleNamespace:
            return SimpleNamespace(status=302, read=lambda _: b"")

        def close(self) -> None:
            pass

    monkeypatch.setattr(ops, "HTTPConnection", RejectedSocket)
    monkeypatch.setattr(target, "check_http_process", lambda: None)
    with pytest.raises(RuntimeError, match="refused"):
        target.probe()
    assert requests == [("127.0.0.1", 18911)]
    (private / "worker.json").write_text((private / "worker.json").read_text() + " ")
    with pytest.raises(RuntimeError, match="configuration changed"):
        target.preflight()


def test_one_activation_lifecycle_refuses_pending_restores_failure_and_retires_only_old_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "linker-planner-test"
    root.mkdir()
    events = []
    items = {}
    required = False

    class Candidate:
        def __init__(self, letter: str) -> None:
            self.root = root
            self.path = root / "releases" / (letter * 64)
            self.path.mkdir(parents=True)
            self.spec_file = self.path / "spec.json"
            self.spec_file.write_text("{}")
            self.spec: dict[str, Any] = {
                "prefix": root.name,
                "port": 18911,
                "user": "planner-test",
                "stop_seconds": 3,
            }
            self.http_unit = "http"
            self.worker_unit = "worker"
            self.pending = False
            self.broken = False
            self.capable = True
            self.write_on_stop = False
            items[str(self.spec_file)] = self

        def preflight(self, *, check_inputs: bool = True) -> dict[str, Any]:
            if check_inputs and required and not self.capable:
                raise RuntimeError("retained input contract")
            return {}

        def namespace(self) -> tuple[Path, str, int, str]:
            return self.root, self.spec["prefix"], self.spec["port"], self.spec["user"]

        def own_units(self) -> None:
            pass

        def probe(self) -> dict[str, Any]:
            return {
                "runtime_sha256": "c" * 64,
                "execution_key": "d" * 64,
                "storage_binding": "e" * 64,
            }

        def ready(self, _: object) -> dict[str, Any]:
            return {"pid": 123}

        def operator(self, *args: Any) -> dict[str, Any]:
            events.append((self.path.name[:1], *args))
            return {"draining": False}

        def stop(self) -> None:
            nonlocal required
            if self.pending:
                raise RuntimeError("pending")
            events.append((self.path.name[:1], "stop"))
            if self.write_on_stop:
                required = True

        def start(self) -> dict[str, Any]:
            self.preflight()  # The real start repeats this after the old HTTP stops.
            events.append((self.path.name[:1], "start"))
            if self.broken:
                raise RuntimeError("candidate failed")
            return self.probe()

    a, b, c = (Candidate(letter) for letter in "abc")
    monkeypatch.setattr(ops, "Release", lambda path: items[str(path)])
    monkeypatch.setattr(ops, "unit_state", lambda _: {"ActiveState": "active"})
    monkeypatch.setattr(ops, "command", lambda *args, **kwargs: "")
    first = ops.activate(a)
    before = list(events)
    assert ops.activate(a) == first and all(
        row[1] != "stop" for row in events[len(before) :]
    )
    a.pending = True
    with pytest.raises(RuntimeError, match="pending"):
        ops.activate(b)
    assert json.loads((root / "selection.json").read_text()) == first
    a.pending = False
    a.write_on_stop = True
    b.capable = False
    stopped_at = len(events)
    with pytest.raises(RuntimeError, match="retained input contract"):
        ops.activate(b)
    assert ("a", "stop") in events[stopped_at:]
    assert ("b", "start") not in events[stopped_at:]
    assert json.loads((root / "selection.json").read_text()) == first
    assert events[-2:] == [("a", "start"), ("a", "control", "resume")]
    b.capable = True
    a.write_on_stop = False
    b.broken = True
    with pytest.raises(RuntimeError, match="candidate failed"):
        ops.activate(b)
    assert json.loads((root / "selection.json").read_text()) == first
    assert events[-2:] == [("a", "start"), ("a", "control", "resume")]
    b.broken = False
    # Replacing an already-incompatible old declaration is legitimate; it is
    # only identity-checked before stop, never started without its own floor.
    a.capable = False
    second = ops.activate(b)
    assert second["previous"] == str(a.spec_file)
    third = ops.activate(c)
    assert third["current"] == str(c.spec_file) and third["previous"] == str(
        b.spec_file
    )
    assert not a.path.exists() and b.path.exists() and c.path.exists()
