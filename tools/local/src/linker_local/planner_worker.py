"""One instance's numerical executor, including true process readiness/draining."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import subprocess
import time
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from .instance import Instance
from .private_config import publish_once
from .processes import POLL, Background, ProcessError

# Private control/start command budget in the development worker contract;
# not a numerical-task or engineering deadline.
CONTROL_TIMEOUT = 10.0


class PlannerWorker:
    def __init__(self, instance: Instance, project: Path, uv: Path) -> None:
        self.instance = instance
        self.project = project
        self.uv = uv
        self.policy_file = instance.dir / "planner/worker.json"
        self.runtime_file = instance.dir / "planner/runtime.json"
        self.process = Background(
            instance.run_dir / "planner-worker.pid",
            instance.log_dir / "planner-worker.log",
        )

    def ensure_policy(self) -> None:
        # Explicit development lifecycle policy, documented with its purposes
        # in docs/specs/548-managed-energy-worker.md; no equipment defaults.
        publish_once(
            self.policy_file,
            {
                "schema_version": 1,
                "name": "local-" + self.instance.name,
                "lease_seconds": 30,
                "heartbeat_seconds": 5,
                "retry_seconds": 2,
                "poll_seconds": 0.5,
                "routing_batch_size": 128,
                "drain_timeout_seconds": 30,
                "ready_file": str(self.instance.run_dir / "planner-worker.ready.json"),
            },
        )
        self._policy()

    def _workspace(self) -> Path:
        runtime: object = json.loads(self.runtime_file.read_bytes())
        if (
            not isinstance(runtime, dict)
            or not isinstance(runtime.get("directory"), str)
            or not Path(runtime["directory"]).is_absolute()
            or not Path(runtime["directory"])
            .resolve()
            .is_relative_to(self.instance.dir.resolve())
        ):
            raise ProcessError(
                "local worker workspace must remain in its owned instance"
            )
        return Path(runtime["directory"]).resolve()

    def environment(self) -> dict[str, str]:
        # Customer calculation and weather execution never receive research,
        # service or model credentials. Apify belongs to R&D only.
        self._workspace()
        names = (
            "PATH",
            "HOME",
            "TMPDIR",
            "TEMP",
            "TMP",
            "LANG",
            "LC_ALL",
            "UV_CACHE_DIR",
            "UV_PYTHON",
        )
        environment = {
            **{name: os.environ[name] for name in names if name in os.environ},
            "LINKER_PLANNER_CONFIG": str(self.runtime_file),
            "LINKER_PLANNER_WORKER_CONFIG": str(self.policy_file),
            # Explicit source root also supports an owned immutable release
            # using the existing, already-synced interpreter environment.
            "PYTHONPATH": str(self.project / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            # Current Woo permission is public; the worker needs no service or
            # research credential to validate its frozen product dependencies.
            "LINKER_ENGINE_FEED": str(self.instance.dir / "engine/feed.json"),
            "LINKER_ENGINE_COMPATIBILITY": str(
                self.instance.dir / "engine/compatibility.json"
            ),
            "LINKER_ENGINE_CACHE": str(self.instance.dir / "engine/cache"),
            "LINKER_PUBLICATION_URL": self.instance.url
            + "/wp-json/linker/v1/publication/manifest",
        }
        policy: object = json.loads(self.runtime_file.read_bytes())
        if isinstance(policy, dict) and policy.get("weather_acquisition") is not None:
            # Public-source HTTPS needs only requests' proxy/CA policy. No
            # research account, service token or model key is inherited.
            network_names = (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "no_proxy",
                "REQUESTS_CA_BUNDLE",
                "CURL_CA_BUNDLE",
            )
            environment.update(
                {name: os.environ[name] for name in network_names if name in os.environ}
            )
        return environment

    def release(self) -> dict[str, object]:
        """Inspect source/dependencies without opening the live project store."""
        result = subprocess.run(
            self.command("release"),
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
            timeout=CONTROL_TIMEOUT,
        )
        if result.returncode:
            raise ProcessError("planning executable release probe failed")
        try:
            value: object = json.loads(result.stdout)
        except ValueError as error:
            raise ProcessError(
                "planning release probe returned invalid JSON"
            ) from error
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema_version", "runtime_sha256", "storage_schema_version"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or not isinstance(value["runtime_sha256"], str)
            or re.fullmatch(r"[a-f0-9]{64}", value["runtime_sha256"]) is None
            or type(value["storage_schema_version"]) is not int
            or value["storage_schema_version"] <= 0
        ):
            raise ProcessError("planning release probe returned an invalid version")
        return value

    def compatible_release(self) -> dict[str, object]:
        """Refuse implicit migration/downgrade and mismatched live executors."""
        release = self.release()
        database = self._workspace() / "workspace.sqlite"
        if database.exists():
            try:
                with closing(
                    sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
                ) as connection:
                    version = connection.execute("PRAGMA user_version").fetchone()[0]
                    empty = (
                        connection.execute(
                            "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
                        ).fetchone()
                        is None
                    )
                    if (
                        not (empty and version == 0)
                        and version != release["storage_schema_version"]
                    ):
                        raise ProcessError(
                            "planning storage/executable versions differ; "
                            "a verified paired upgrade and recovery point are required"
                        )
            except sqlite3.Error as error:
                raise ProcessError(
                    "planning storage version could not be read"
                ) from error
        if self.process.pid() is not None:
            ready = self.readiness({"runtime_sha256": release["runtime_sha256"]})
            if ready is None:
                raise ProcessError(
                    "running planning worker differs from this executable; "
                    "preserve it for a verified paired upgrade"
                )
        return release

    def command(self, *arguments: str) -> list[str]:
        # Existing engine environment is synced before start; neither a new
        # dependency copy nor a network resolver is needed for lifecycle calls.
        return [
            str(self.uv),
            "run",
            "--locked",
            "--no-sync",
            "--offline",
            "--project",
            str(self.project),
            "python",
            "-m",
            "linker_engine.planning.worker_host",
            *arguments,
        ]

    def control(self, operation: str) -> dict[str, object]:
        result = subprocess.run(
            self.command("control", operation),
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
            timeout=CONTROL_TIMEOUT,
        )
        if result.returncode:
            raise ProcessError("planning control failed: " + result.stderr.strip())
        value: object = json.loads(result.stdout)
        if (
            not isinstance(value, dict)
            or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or type(value.get("draining")) is not bool
            or type(value.get("pending")) is not int
            or value["pending"] < 0
        ):
            raise ProcessError("planning control returned an invalid status")
        if "quiescent" in value or "remote_weather" in value:
            remote = value.get(
                "remote_weather",
                {"unknown": 0, "active": 0, "terminal": 0, "unresolved": 0},
            )
            if (
                type(value.get("quiescent")) is not bool
                or not isinstance(remote, dict)
                or any(
                    type(remote.get(key)) is not int or remote[key] < 0
                    for key in ("unknown", "active", "terminal", "unresolved")
                )
                or remote["unresolved"] != remote["unknown"] + remote["active"]
                or value["quiescent"]
                != (
                    value["draining"]
                    and value["pending"] == 0
                    and remote["unresolved"] == 0
                )
            ):
                raise ProcessError(
                    "planning control returned invalid remote quiescence"
                )
        return value

    def _drained(self, state: Mapping[str, object]) -> bool:
        if state["pending"] != 0 or state.get("draining") is not True:
            return False
        if "quiescent" in state:
            return state["quiescent"] is True
        # A pre-upgrade executable has no remote-aware status. Prove locally
        # that its journal has issued no remote starts, without migrating or
        # creating its database. Any issued operation requires reconciliation.
        database = self._workspace() / "workspace.sqlite"
        if not database.exists():
            raise ProcessError(
                "legacy planning database is unavailable for drain verification"
            )
        try:
            with closing(
                sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
            ) as connection:
                connection.execute("BEGIN")
                table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='weather_acquisitions'"
                ).fetchone()
                if (
                    table is not None
                    and connection.execute(
                        "SELECT 1 FROM weather_acquisitions WHERE post_claimed=1 LIMIT 1"
                    ).fetchone()
                    is not None
                ):
                    raise ProcessError(
                        "legacy planning status has issued remote weather; verified reconciliation required"
                    )
        except sqlite3.Error as error:
            raise ProcessError(
                "legacy planning database could not prove drain safety"
            ) from error
        return True

    def _policy(self) -> dict[str, object]:
        value: object = json.loads(self.policy_file.read_bytes())
        if not isinstance(value, dict):
            raise ProcessError("worker policy is not an object")
        ready = value.get("ready_file")
        if (
            not isinstance(ready, str)
            or not Path(ready).is_absolute()
            or not Path(ready).resolve().is_relative_to(self.instance.run_dir.resolve())
        ):
            raise ProcessError("local readiness must remain in its owned instance")
        return value

    def readiness(
        self,
        expected: Mapping[str, object] | None = None,
        generation: str | None = None,
    ) -> dict[str, object] | None:
        group = self.process.pid()
        if group is None or not self.policy_file.is_file():
            return None
        policy = self._policy()
        ready_path = policy.get("ready_file")
        if not isinstance(ready_path, str) or not Path(ready_path).is_absolute():
            return None
        try:
            value: object = json.loads(Path(ready_path).read_bytes())
            if (
                not isinstance(value, dict)
                or type(value.get("schema_version")) is not int
                or value["schema_version"] != 1
                or type(value.get("pid")) is not int
                or value["pid"] <= 0
                or not isinstance(value.get("generation"), str)
                or re.fullmatch(r"[a-f0-9]{32}", value["generation"]) is None
                or os.getpgid(value["pid"]) != group
            ):
                return None
            for name in ("runtime_sha256", "execution_key", "storage_binding"):
                actual = value.get(name)
                if (
                    not isinstance(actual, str)
                    or re.fullmatch(r"[a-f0-9]{64}", actual) is None
                    or (
                        expected is not None
                        and name in expected
                        and actual != expected[name]
                    )
                ):
                    return None
            if generation is not None and value["generation"] != generation:
                return None
            return value
        except (OSError, ValueError):
            return None

    def start(self, identity: Mapping[str, object], timeout: float) -> None:
        self.ensure_policy()
        if self.process.pid() is not None:
            if self.readiness(identity) is not None:
                return
            raise ProcessError(
                "owned worker is running with a different/unready identity"
            )
        for name in ("runtime_sha256", "execution_key", "storage_binding"):
            if (
                not isinstance(identity.get(name), str)
                or re.fullmatch(r"[a-f0-9]{64}", str(identity[name])) is None
            ):
                raise ProcessError("ready HTTP execution identity is required")
        generation = uuid4().hex
        self.process.start(
            self.command(
                "serve",
                "--expected-runtime",
                str(identity["runtime_sha256"]),
                "--expected-execution",
                str(identity["execution_key"]),
                "--expected-storage",
                str(identity["storage_binding"]),
                "--generation",
                generation,
            ),
            self.environment(),
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.readiness(identity, generation) is not None:
                return
            if self.process.pid() is None:
                raise ProcessError(
                    "planning worker exited during start: " + self.process.output()
                )
            time.sleep(POLL)
        self.process.stop()
        raise ProcessError("planning worker readiness deadline expired")

    def drain(self) -> None:
        state = self.control("drain")
        if (
            self.process.pid() is not None
            and self.readiness({"storage_binding": state.get("storage_binding")})
            is None
        ):
            raise ProcessError(
                "live worker readiness does not match the configured workspace"
            )
        if self._drained(state):
            return
        # An unregistered/missing process is not a wait condition. Preserve
        # jobs for its actual retained executable rather than restarting over it.
        if self.readiness() is None:
            raise ProcessError("pending planning work has no live matching worker")
        value = self._policy().get("drain_timeout_seconds")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ProcessError("worker drain deadline is invalid")
        deadline = time.monotonic() + value
        while time.monotonic() < deadline:
            if self.readiness() is None:
                raise ProcessError("planning worker stopped while draining")
            if self._drained(self.control("status")):
                return
            time.sleep(POLL)
        raise ProcessError(
            "planning drain deadline expired; tasks and processes preserved"
        )

    def stop(self) -> bool:
        return self.process.stop()
