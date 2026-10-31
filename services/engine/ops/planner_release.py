#!/usr/bin/env python3
"""Activate a prepared private planning HTTP/worker pair, independently of Genie.

Preparation supplies an immutable engine/venv and explicit runtime/worker
policies. This operator never changes the public proxy or WordPress address.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import pwd
import re
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PUBLIC_SOURCE_KEYS = {
    "LINKER_ENGINE_FEED",
    "LINKER_ENGINE_COMPATIBILITY",
    "LINKER_PUBLICATION_URL",
}
HASH = re.compile(r"[a-f0-9]{64}")


def write(path: Path, value: str, mode: int = 0o600) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    owned = False
    try:
        with temporary.open("x") as stream:
            owned = True
            os.chmod(temporary, mode)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if owned:
            temporary.unlink(missing_ok=True)


def environment(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text().splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key) is None:
            raise ValueError("invalid environment key")
        parsed = shlex.split(value)
        if len(parsed) != 1 or any(ord(c) < 32 for c in parsed[0]):
            raise ValueError("invalid environment value")
        result[key] = parsed[0]
    return result


def env_text(values: dict[str, str]) -> str:
    if any(any(ord(c) < 32 for c in v) for v in values.values()):
        raise ValueError("environment controls are forbidden")
    return "".join(k + "=" + shlex.quote(v) + "\n" for k, v in sorted(values.items()))


def command(
    arguments: list[str], *, env: dict[str, str] | None = None, timeout: float = 30
) -> str:
    # runuser forks the actual control/GC process. Killing only the launcher
    # on timeout or cancellation can leave deletion running as writers restart.
    # Own the entire subprocess group and finish terminating it before return.
    with subprocess.Popen(
        arguments,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    ) as process:
        try:
            stdout, _ = process.communicate(timeout=timeout)
            if process.returncode:
                # A crashed launcher may have surviving descendants too.
                raise RuntimeError(
                    "operator command failed: " + Path(arguments[0]).name
                )
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        return stdout


def unit_state(name: str) -> dict[str, str]:
    text = command(
        [
            "systemctl",
            "show",
            name,
            "--property=MainPID,InvocationID,ActiveState,FragmentPath,DropInPaths,ControlGroup",
            "--no-pager",
        ]
    )
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


class Release:
    def __init__(self, spec_file: Path):
        self.spec_file = spec_file.resolve(strict=True)
        spec = json.loads(self.spec_file.read_text())
        if (
            set(spec)
            != {
                "schema_version",
                "root",
                "release",
                "prefix",
                "port",
                "user",
                "start_seconds",
                "stop_seconds",
            }
            or type(spec["schema_version"]) is not int
            or spec["schema_version"] != 1
        ):
            raise ValueError("unsupported release specification")
        for key in ("root", "release"):
            if (
                not isinstance(spec[key], str)
                or re.fullmatch(r"/[A-Za-z0-9_./-]+", spec[key]) is None
            ):
                raise ValueError("absolute unquoted deployment paths required")
        self.root, self.path = Path(spec["root"]), Path(spec["release"])
        if (
            self.root.is_symlink()
            or self.root.resolve() != self.root
            or self.path.resolve() != self.path
            or self.path.parent != self.root / "releases"
            or HASH.fullmatch(self.path.name) is None
        ):
            raise ValueError("release must be a retained owned directory")
        if not re.fullmatch(
            r"linker-planner(?:-[a-z0-9-]+)?", spec["prefix"]
        ) or not re.fullmatch(r"[a-z][a-z0-9-]*", spec["user"]):
            raise ValueError("invalid service namespace")
        if type(spec["port"]) is not int or not 1024 < spec["port"] < 65536:
            raise ValueError("explicit service port required")
        for key in ("start_seconds", "stop_seconds"):
            v = spec[key]
            if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
                raise ValueError("positive finite process budgets required")
        if self.root.name != spec["prefix"] or len(self.root.parts) < 3:
            raise ValueError("deployment root must identify its service namespace")
        if pwd.getpwnam(spec["user"]).pw_uid == 0:
            raise ValueError("a dedicated non-root service account is required")
        self.spec = spec
        self.deploy = self.path / ".deploy"
        if self.spec_file != self.deploy / "spec.json":
            raise ValueError("specification must stay with its prepared release")
        self.runtime_file = self.deploy / "runtime.json"
        self.worker_file = self.deploy / "worker.json"
        self.check_paths()
        self.runtime = json.loads(self.runtime_file.read_text())
        self.policy = json.loads(self.worker_file.read_text())
        if (
            Path(self.runtime["directory"]) != self.root / "state/workspace"
            or Path(self.policy["ready_file"]) != self.root / "run/worker.ready.json"
        ):
            raise ValueError("workspace and readiness must belong to this deployment")
        if (
            not (self.path / ".venv/bin/python").is_file()
            or (self.path / ".venv").is_symlink()
        ):
            raise ValueError("release requires an environment built in place")
        self.http_unit = spec["prefix"] + "-http.service"
        self.worker_unit = spec["prefix"] + "-worker.service"

    def check_paths(self) -> None:
        for path in (
            self.deploy,
            self.deploy / "runtime.json",
            self.deploy / "worker.json",
            self.deploy / "http.env",
            self.deploy / "prepared.json",
            self.root / "selection.json",
            self.root / "operator.lock",
            self.root / "state",
            self.root / "state/workspace",
            self.root / "state/source-cache",
            self.root / "run",
            self.root / "run/worker.ready.json",
            *(
                self.root / "state/workspace" / name
                for name in (
                    "workspace.sqlite",
                    "workspace.sqlite-wal",
                    "workspace.sqlite-shm",
                    "blobs",
                )
            ),
        ):
            if path.resolve() != path or not path.is_relative_to(self.root):
                raise ValueError("deployment paths must not follow symbolic links")

    def namespace(self) -> tuple[Path, str, int, str]:
        return self.root, self.spec["prefix"], self.spec["port"], self.spec["user"]

    def operator(self, *args: str) -> dict[str, Any]:
        env = {
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            **environment(self.deploy / "http.env"),
        }
        # Operator control and numerical startup never inherit service credentials.
        env.pop("GENIE_SERVICE_TOKEN", None)
        env["LINKER_PLANNER_WORKER_CONFIG"] = str(self.worker_file)
        result: dict[str, Any] = json.loads(
            command(
                [
                    "runuser",
                    "--preserve-environment",
                    "-u",
                    self.spec["user"],
                    "--",
                    str(self.path / ".venv/bin/python"),
                    "-m",
                    "linker_engine.planning.worker_host",
                    *args,
                ],
                env=env,
                timeout=self.spec["start_seconds"],
            )
        )
        return result

    def preflight(
        self, *, prepared: bool = True, check_inputs: bool = True
    ) -> dict[str, Any]:
        self.check_paths()
        origin = json.loads(
            command(
                [
                    str(self.path / ".venv/bin/python"),
                    "-c",
                    "import json,sys,pathlib,linker_engine;print(json.dumps({'prefix':str(pathlib.Path(sys.prefix).resolve()),'package':str(pathlib.Path(linker_engine.__file__).resolve())}))",
                ],
                env={
                    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
        )
        if origin != {
            "prefix": str(self.path / ".venv"),
            "package": str(self.path / "src/linker_engine/__init__.py"),
        }:
            raise RuntimeError("environment imports code outside its retained release")
        public = {
            k: v
            for k, v in environment(self.deploy / "http.env").items()
            if k != "GENIE_SERVICE_TOKEN"
        }
        # Validate the actual source under the service identity before stopping
        # a working release; root's successful read proves no reader access.
        command(
            [
                "runuser",
                "--preserve-environment",
                "-u",
                self.spec["user"],
                "--",
                str(self.path / ".venv/bin/python"),
                "-c",
                "from linker_engine.app import Services,Settings,SOURCE; Services(Settings.from_environment(),SOURCE)",
            ],
            env={
                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                **public,
            },
        )
        release = self.operator("release")
        db = Path(self.runtime["directory"]) / "workspace.sqlite"
        if db.exists():
            stored = int(
                command(
                    [
                        "runuser",
                        "--preserve-environment",
                        "-u",
                        self.spec["user"],
                        "--",
                        str(self.path / ".venv/bin/python"),
                        "-c",
                        "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]+'?mode=ro',uri=True); print(c.execute('pragma user_version').fetchone()[0]); c.close()",
                        db.as_uri(),
                    ],
                    env={
                        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )
            )
            if stored != release["storage_schema_version"]:
                raise RuntimeError(
                    "storage migration requires a separate verified plan"
                )
        for key in ("runtime_sha256",):
            if HASH.fullmatch(str(release.get(key))) is None:
                raise ValueError("invalid executable identity")
        if check_inputs:
            self.input_compatibility(release)
        receipt = self.deploy / "prepared.json"
        if prepared:
            frozen = json.loads(receipt.read_text())
            files = {
                name: hashlib.sha256((self.deploy / name).read_bytes()).hexdigest()
                for name in (
                    "spec.json",
                    "runtime.json",
                    "worker.json",
                    "http.env",
                    self.http_unit,
                    self.worker_unit,
                )
            }
            if frozen != {"release": release, "files": files}:
                raise RuntimeError("prepared executable or configuration changed")
        return release

    def input_compatibility(self, release: dict[str, Any]) -> None:
        """The operator's current guard can reject even an older rollback binary.

        Read as the service UID with a read-only SQLite snapshot, not through
        the candidate's Workspace constructor. start() repeats preflight after
        the old HTTP has stopped, closing the final concurrent-save window.
        """
        directory = Path(self.runtime["directory"])
        if (
            not (self.root / "selection.json").exists()
            and not (directory / "workspace.sqlite").exists()
            and (not directory.exists() or not any(directory.iterdir()))
        ):
            return  # First unselected, wholly empty deployment only.
        guard_source = Path(__file__).resolve().parents[1] / "src"
        try:
            command(
                [
                    "runuser",
                    "--preserve-environment",
                    "-u",
                    self.spec["user"],
                    "--",
                    str(self.path / ".venv/bin/python"),
                    "-c",
                    "import json,sys; from pathlib import Path; "
                    "sys.path.insert(0,sys.argv[1]); "
                    "from linker_engine.planning.project_input_floor import check_project_input_contracts; "
                    "check_project_input_contracts(Path(sys.argv[2]),json.loads(sys.argv[3]))",
                    str(guard_source),
                    str(directory),
                    json.dumps(release.get("project_input_contracts", [])),
                ],
                env={
                    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
        except (OSError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                "retained project input compatibility refused; a compatible executable is required"
            ) from error

    def prepare(self, source_env: Path, publication_url: str) -> None:
        self.check_paths()
        selected = self.root / "selection.json"
        if selected.exists():
            old = Release(Path(json.loads(selected.read_text())["current"]))
            if old.namespace() != self.namespace():
                raise RuntimeError("deployment namespace changed")
            old.preflight(check_inputs=False)
        source = environment(source_env)
        public = {k: source[k] for k in PUBLIC_SOURCE_KEYS if k in source}
        endpoint = urlsplit(publication_url)
        if (
            not endpoint.hostname
            or endpoint.username is not None
            or endpoint.password is not None
            or endpoint.query
            or endpoint.fragment
            or any(ord(c) < 33 for c in publication_url)
            or not (
                endpoint.scheme == "https"
                or (
                    endpoint.scheme == "http"
                    and endpoint.hostname in ("127.0.0.1", "::1")
                )
            )
        ):
            raise ValueError("explicit credential-free publication endpoint required")
        public["LINKER_PUBLICATION_URL"] = publication_url
        for key in ("LINKER_ENGINE_FEED", "LINKER_ENGINE_COMPATIBILITY"):
            if key not in public or not Path(public[key]).is_file():
                raise ValueError("current Woo source file missing")
        public.update(
            LINKER_ENGINE_CACHE=str(self.root / "state/source-cache"),
            LINKER_ENGINE_GATE_MODE="enforce",
            LINKER_PLANNER_CONFIG=str(self.runtime_file),
        )
        token = source.get("GENIE_SERVICE_TOKEN", "")
        if not token:
            raise ValueError("existing service credential required")
        desired_env = env_text({**public, "GENIE_SERVICE_TOKEN": token})
        if (self.deploy / "prepared.json").exists():
            self.preflight()
            if (self.deploy / "http.env").read_text() != desired_env:
                raise RuntimeError(
                    "changed credentials require a newly prepared release"
                )
            return
        os.chmod(self.deploy, 0o755)
        for policy in (self.runtime_file, self.worker_file, self.spec_file):
            os.chmod(policy, 0o644)
        write(self.deploy / "http.env", desired_env)
        account = pwd.getpwnam(self.spec["user"])
        for shared in (
            self.root / "state",
            self.root / "state/source-cache",
            self.root / "state/workspace",
            self.root / "run",
        ):
            if shared.exists() and (
                shared.stat().st_uid != account.pw_uid or shared.stat().st_mode & 0o077
            ):
                raise RuntimeError(
                    "existing service directory ownership or privacy differs"
                )
        for path in (
            self.root / "state",
            self.root / "state/source-cache",
            self.root / "state/workspace",
            self.root / "run",
        ):
            if path.exists():
                if path.stat().st_uid != account.pw_uid or path.stat().st_mode & 0o077:
                    raise RuntimeError(
                        "existing service directory ownership or privacy differs"
                    )
            else:
                path.mkdir(exist_ok=False, parents=True, mode=0o700)
                os.chown(path, account.pw_uid, account.pw_gid)
        self.preflight(prepared=False)
        base = f"[Unit]\nAfter=network.target\n[Service]\nType=exec\nUser={self.spec['user']}\nWorkingDirectory={self.path}\nUMask=0077\nRestart=on-failure\nRestartSec=2\nTimeoutStopSec={self.spec['stop_seconds']}\nKillMode=control-group\n"
        write(
            self.deploy / self.http_unit,
            base
            + f"EnvironmentFile={self.deploy}/http.env\nExecStart={self.path}/.venv/bin/python -m uvicorn linker_engine.application:app --host 127.0.0.1 --port {self.spec['port']}\n",
            0o644,
        )
        write(
            self.deploy / self.worker_unit,
            base
            + f"EnvironmentFile={self.deploy}/worker.env\nExecStart={self.path}/.venv/bin/python -m linker_engine.planning.worker_host serve --expected-runtime ${{LINKER_PLANNER_RUNTIME_SHA256}} --expected-execution ${{LINKER_PLANNER_EXECUTION_KEY}} --expected-storage ${{LINKER_PLANNER_STORAGE_BINDING}} --generation ${{INVOCATION_ID}}\n",
            0o644,
        )
        command(
            [
                "systemd-analyze",
                "verify",
                str(self.deploy / self.http_unit),
                str(self.deploy / self.worker_unit),
            ]
        )
        names = [
            "spec.json",
            "runtime.json",
            "worker.json",
            "http.env",
            self.http_unit,
            self.worker_unit,
        ]
        write(
            self.deploy / "prepared.json",
            json.dumps(
                {
                    "release": self.preflight(prepared=False),
                    "files": {
                        name: hashlib.sha256(
                            (self.deploy / name).read_bytes()
                        ).hexdigest()
                        for name in names
                    },
                },
                sort_keys=True,
            )
            + "\n",
        )

    def own_units(self) -> None:
        for name in (self.http_unit, self.worker_unit):
            for directory in (
                Path("/etc/systemd/system"),
                Path("/etc/systemd/system/multi-user.target.wants"),
            ):
                path = directory / name
                if path.exists() or path.is_symlink():
                    if not path.is_symlink() or not path.resolve().is_relative_to(
                        self.root / "releases"
                    ):
                        raise RuntimeError(
                            "service name is not owned by this deployment"
                        )
            actual = unit_state(name)
            fragment = actual.get("FragmentPath", "")
            if fragment and not Path(fragment).resolve().is_relative_to(
                self.root / "releases"
            ):
                raise RuntimeError("loaded service belongs to another deployment")
            if actual.get("DropInPaths"):
                raise RuntimeError("unreviewed service override exists")

    def link(self) -> None:
        self.own_units()
        for name in (self.http_unit, self.worker_unit):
            dest = Path("/etc/systemd/system") / name
            temp = dest.with_suffix(".service.tmp")
            temp.symlink_to(self.deploy / name)
            os.replace(temp, dest)
            # A stable unit link survives retirement of the first release.
            wanted = Path("/etc/systemd/system/multi-user.target.wants") / name
            temporary = wanted.with_suffix(".service.tmp")
            temporary.symlink_to(dest)
            os.replace(temporary, wanted)
            if wanted.readlink() != dest:
                raise RuntimeError("boot dependency does not follow the current unit")
        command(["systemctl", "daemon-reload"])

    def drain(self) -> None:
        state = self.operator("control", "drain")
        deadline = time.monotonic() + self.policy["drain_timeout_seconds"]
        while not (state.get("quiescent") is True and state.get("pending") == 0):
            if (
                time.monotonic() >= deadline
                or unit_state(self.worker_unit).get("ActiveState") != "active"
            ):
                raise RuntimeError(
                    "drain incomplete; preserve executable, queue and service"
                )
            time.sleep(0.2)
            state = self.operator("control", "status")

    def stop(self) -> None:
        self.own_units()
        self.drain()
        command(
            ["systemctl", "stop", self.worker_unit, self.http_unit],
            timeout=self.spec["stop_seconds"] + 10,
        )

    def check_stopped(self) -> None:
        """Read back both process groups and the private listener before GC."""
        for name in (self.worker_unit, self.http_unit):
            state = unit_state(name)
            if (
                state.get("ActiveState") not in ("inactive", "failed")
                or state.get("MainPID") != "0"
            ):
                raise RuntimeError("planning writer did not stop")
            group = state.get("ControlGroup", "")
            if group:
                members = Path("/sys/fs/cgroup") / group.lstrip("/") / "cgroup.procs"
                if members.exists() and members.read_text().strip():
                    raise RuntimeError("planning process group still has writers")
        if command(["ss", "-ltnpH", f"sport = :{self.spec['port']}"]).strip():
            raise RuntimeError("planning listener is still active")

    def check_http_process(self) -> None:
        state = unit_state(self.http_unit)
        pid = int(state.get("MainPID", "0"))
        if (
            state.get("ActiveState") != "active"
            or pid <= 0
            or Path(f"/proc/{pid}/cwd").resolve() != self.path
        ):
            raise RuntimeError("HTTP process is not the intended release")
        listeners = command(["ss", "-ltnpH", f"sport = :{self.spec['port']}"])
        if set(re.findall(r"pid=(\d+),", listeners)) != {str(pid)}:
            raise RuntimeError("planning listener is not owned by the HTTP process")

    def probe(self) -> dict[str, Any]:
        self.check_http_process()
        env = environment(self.deploy / "http.env")
        # HTTPConnection neither follows redirects nor consults proxy settings.
        # Never send the service credential anywhere except this owned loopback socket.
        connection = HTTPConnection("127.0.0.1", self.spec["port"], timeout=1)
        try:
            connection.request(
                "POST",
                "/planning/version",
                body=b'{"schema_version":1}',
                headers={
                    "Content-Type": "application/json",
                    "X-Linker-Service-Token": env["GENIE_SERVICE_TOKEN"],
                    "X-Linker-Planner-Principal-Kind": "team",
                    "X-Linker-Planner-Principal-Subject": "deployment-readiness",
                },
            )
            response = connection.getresponse()
            raw = response.read(
                32 * 1024 + 1
            )  # Bounded operational metadata, not a model limit.
            if response.status != 200 or len(raw) > 32 * 1024:
                raise RuntimeError("private planning readiness was refused")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("readiness must be an object")
            return value
        finally:
            connection.close()

    def wait_for(self, read: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        deadline = time.monotonic() + self.spec["start_seconds"]
        while True:
            try:
                result = read()
                if result:
                    return result
            except (OSError, ValueError, RuntimeError, HTTPException):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("paired service readiness deadline expired")
            time.sleep(0.2)

    def start(self) -> dict[str, Any]:
        release = self.preflight()
        # Initialise a fresh store and close admission before exposing HTTP.
        self.operator("control", "drain")
        self.link()
        command(["systemctl", "start", self.http_unit])
        identity = self.wait_for(self.probe)
        if identity["runtime_sha256"] != release["runtime_sha256"]:
            raise RuntimeError("HTTP source differs from executable")
        public = {
            k: v
            for k, v in environment(self.deploy / "http.env").items()
            if k != "GENIE_SERVICE_TOKEN"
        }
        public.update(
            LINKER_PLANNER_WORKER_CONFIG=str(self.worker_file),
            LINKER_PLANNER_RUNTIME_SHA256=identity["runtime_sha256"],
            LINKER_PLANNER_EXECUTION_KEY=identity["execution_key"],
            LINKER_PLANNER_STORAGE_BINDING=identity["storage_binding"],
        )
        write(self.deploy / "worker.env", env_text(public))
        command(["systemctl", "start", self.worker_unit])
        self.wait_for(lambda: self.ready(identity))
        return identity

    def ready(self, identity: dict[str, Any]) -> dict[str, Any]:
        state = unit_state(self.worker_unit)
        if state.get("ActiveState") != "active":
            return {}
        record: dict[str, Any] = json.loads(Path(self.policy["ready_file"]).read_text())
        if (
            record.get("pid") != int(state["MainPID"])
            or record.get("generation") != state["InvocationID"]
        ):
            return {}
        if any(
            record.get(k) != identity.get(k)
            for k in ("runtime_sha256", "execution_key", "storage_binding")
        ):
            raise RuntimeError("worker identity differs from HTTP")
        for name in (self.worker_unit, self.http_unit):
            pid = int(unit_state(name)["MainPID"])
            if Path(f"/proc/{pid}/cwd").resolve() != self.path:
                raise RuntimeError("running process imports a different release")
        return record


@contextmanager
def locked(root: Path) -> Iterator[None]:
    with (root / "operator.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def activate(target: Release) -> dict[str, Any]:
    with locked(target.root):
        target.preflight()
        target.own_units()
        selected = target.root / "selection.json"
        before: dict[str, Any] | None = (
            json.loads(selected.read_text()) if selected.exists() else None
        )
        old = Release(Path(before["current"])) if before else None
        if old:
            if old.namespace() != target.namespace():
                raise RuntimeError("deployment namespace changed")
            # Verify the stopped/replaced binary's identity, not its ability to
            # admit new writes. The target and every fallback start check the
            # floor; an old declaration must not prevent a compatible upgrade.
            old.preflight(check_inputs=False)
        if old and (old.spec["prefix"], old.spec["port"], old.spec["user"]) != (
            target.spec["prefix"],
            target.spec["port"],
            target.spec["user"],
        ):
            raise RuntimeError("deployment namespace changed")
        if old and old.spec_file == target.spec_file:
            assert before is not None
            try:
                identity = target.probe()
                if (
                    target.ready(identity)
                    and target.operator("control", "status")["draining"] is False
                ):
                    return before
            except (OSError, ValueError, RuntimeError, HTTPException):
                pass
        if old:
            if unit_state(old.worker_unit).get("ActiveState") != "active":
                # A stopped current executor must recover its own queue before
                # any replacement; the target never leases an old execution key.
                old.start()
            old.stop()
        previous = (
            before["previous"]
            if before and old and old.spec_file == target.spec_file
            else str(old.spec_file)
            if old
            else None
        )
        try:
            identity = target.start()
            state = {
                "schema_version": 1,
                "current": str(target.spec_file),
                "previous": previous,
                "identity": {
                    k: identity[k]
                    for k in ("runtime_sha256", "execution_key", "storage_binding")
                },
            }
            write(selected, json.dumps(state, sort_keys=True) + "\n")
            target.operator("control", "resume")
        except BaseException:
            try:
                active = [
                    name
                    for name in (target.worker_unit, target.http_unit)
                    if unit_state(name).get("ActiveState") not in ("inactive", "failed")
                ]
                if active:
                    command(
                        ["systemctl", "stop", *active],
                        timeout=target.spec["stop_seconds"] + 10,
                    )
            finally:
                if before:
                    write(selected, json.dumps(before, sort_keys=True) + "\n")
                else:
                    selected.unlink(missing_ok=True)
                if old:
                    old.start()
                    old.operator("control", "resume")
            raise
        # The old global drain proved that no pending request needs a retired
        # executable. Keep only current and its single paired rollback.
        if (
            before
            and before.get("previous")
            and before["previous"] not in (state["current"], state["previous"])
        ):
            retired = Release(Path(before["previous"]))
            if retired.root != target.root:
                raise RuntimeError("foreign retention entry")
            shutil.rmtree(retired.path)
        return state


def maintain(
    release: Release,
    *,
    apply: bool = False,
    recovery: Path | None = None,
    snapshots: tuple[Path, ...] = (),
) -> dict[str, Any]:
    """Read-only default; apply owns a stopped pair and always restores it."""
    arguments = ["retention"]
    if recovery is not None:
        arguments.extend(("--recovery", str(recovery.absolute())))
    for snapshot in snapshots:
        arguments.extend(("--snapshot", str(snapshot.absolute())))
    if not apply:
        return release.operator(*arguments)
    if recovery is None:
        raise ValueError("apply requires an existing verified recovery archive")
    with locked(release.root):
        selected = json.loads((release.root / "selection.json").read_text())
        if selected["current"] != str(release.spec_file):
            raise RuntimeError("maintenance must use the selected release")
        release.preflight()
        identity = release.probe()
        if not release.ready(identity):
            raise RuntimeError("paired service is not ready before maintenance")
        draining = release.operator("control", "status")["draining"]
        failure: BaseException | None = None
        try:
            release.stop()
            release.check_stopped()
            for directory, names in (
                (release.deploy, ("worker.env", "http.env", "prepared.json")),
                (release.root, ("selection.json",)),
            ):
                for name in names:
                    path = directory / (name + ".tmp")
                    if path.is_file() and not path.is_symlink():
                        path.unlink()
            # Stale readiness writes belong only to this worker. Never scan
            # /tmp or remove unrelated run/deployment files.
            ready = Path(release.policy["ready_file"])
            for path in ready.parent.glob("." + ready.name + ".incoming-*"):
                if (
                    re.fullmatch(
                        re.escape("." + ready.name + ".incoming-") + r"[a-z0-9_]{8}",
                        path.name,
                    )
                    and path.is_file()
                    and not path.is_symlink()
                ):
                    path.unlink()
            result = release.operator(*arguments, "--apply", "--offline")
            return result
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                try:
                    identity = release.probe()
                    ready_pair = bool(release.ready(identity))
                except (OSError, ValueError, RuntimeError, HTTPException):
                    ready_pair = False
                if not ready_pair:
                    release.start()
                if not draining:
                    release.operator("control", "resume")
            except BaseException as error:
                if failure is None:
                    raise
                failure.add_note("paired service recovery failed: " + repr(error))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "activate", "status", "rollback", "stop", "retention"),
    )
    parser.add_argument("spec", type=Path)
    parser.add_argument("--source-environment", type=Path)
    parser.add_argument("--publication-url")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply offline retention; default is read-only plan",
    )
    parser.add_argument(
        "--recovery",
        type=Path,
        help="existing independently verified archive covering deleted bytes",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        default=[],
        help="external snapshot to verify; DB-only/shared/unknown layouts refuse apply",
    )
    args = parser.parse_args()
    release = Release(args.spec)
    if args.operation == "prepare":
        if args.source_environment is None or args.publication_url is None:
            parser.error("explicit source environment and publication URL required")
        release.prepare(args.source_environment, args.publication_url)
        result = {"prepared": str(release.spec_file), "executable": release.preflight()}
    elif args.operation == "activate":
        result = activate(release)
    elif args.operation == "rollback":
        state = json.loads((release.root / "selection.json").read_text())
        if not state["previous"]:
            raise RuntimeError("no retained rollback release")
        result = activate(Release(Path(state["previous"])))
    elif args.operation == "retention":
        result = maintain(
            release,
            apply=args.apply,
            recovery=args.recovery,
            snapshots=tuple(args.snapshot),
        )
    elif args.operation == "stop":
        with locked(release.root):
            release.stop()
        result = {"stopped": release.spec["prefix"]}
    else:
        identity = release.probe()
        result = {
            "identity": identity,
            "ready": release.ready(identity),
            "control": release.operator("control", "status"),
        }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
