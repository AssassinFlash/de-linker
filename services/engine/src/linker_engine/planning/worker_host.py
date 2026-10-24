"""Private numerical process and operator commands, with no HTTP credentials."""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import re
import signal
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event

from .canonical import Object, encode
from .execution_control import ExecutionControl
from .execution_identity import storage_binding
from .execution_registry import service_registry
from .jobs import Jobs
from .runtime_config import RuntimeConfig
from .runtime_snapshot import RuntimeSnapshot
from .schema import SCHEMA_VERSION
from .worker import Worker
from .worker_policy import WorkerPolicy
from .workspace import Workspace

LOG = logging.getLogger(__name__)


@contextmanager
def readiness_owner(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("this worker readiness path is already owned") from error
        yield
    finally:
        os.close(descriptor)


def publish_ready(path: Path, value: Object) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def serve(
    expected_runtime: str,
    expected_execution: str,
    expected_storage: str,
    generation: str,
) -> int:
    policy = WorkerPolicy.from_environment()
    settings = RuntimeConfig.from_environment()
    ready = Path(policy.ready_file)
    # Operational files do not belong in immutable customer/source storage.
    if ready.resolve().is_relative_to(Path(settings.directory).resolve()):
        raise ValueError("worker readiness must be outside the project workspace")
    with readiness_owner(ready):
        workspace, energy = settings.open()
        pv = settings.pv_service(workspace)
        weather = settings.weather_service(workspace)
        registry = service_registry(energy, pv, weather)
        if (registry.runtime.sha256, registry.execution_key()) != (
            expected_runtime,
            expected_execution,
        ):
            raise RuntimeError("worker execution differs from the ready HTTP service")
        if storage_binding(workspace.database.path) != expected_storage:
            raise RuntimeError("worker workspace differs from the ready HTTP service")
        worker = Worker(
            Jobs(workspace),
            policy.name,
            {"evaluate": registry},
            lease_seconds=policy.lease_seconds,
            heartbeat_seconds=policy.heartbeat_seconds,
            retry_seconds=policy.retry_seconds,
            routing=registry.routing(policy.routing_batch_size),
        )
        stop = Event()

        def stopping(_signum: int, _frame: object) -> None:
            stop.set()

        previous = {
            number: signal.signal(number, stopping)
            for number in (signal.SIGTERM, signal.SIGINT)
        }
        identity: Object = {
            "schema_version": 1,
            "pid": os.getpid(),
            "generation": generation,
            "runtime_sha256": expected_runtime,
            "execution_key": expected_execution,
            "storage_binding": expected_storage,
            "name": policy.name,
        }
        try:
            publish_ready(ready, identity)
            LOG.info("planning worker ready: %s", policy.name)
            while not stop.is_set():
                if not worker.run_once():
                    stop.wait(policy.poll_seconds)
            return 0
        finally:
            # A claim already in progress is in-flight and can finish under its
            # lease; a signal stops subsequent loop iterations, not the worker's
            # independently persisted job or its final publication protocol.
            try:
                if json.loads(ready.read_bytes()).get("generation") == generation:
                    ready.unlink()
            except FileNotFoundError:
                pass
            for number, handler in previous.items():
                signal.signal(number, handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("serve")
    run.add_argument("--expected-runtime", required=True)
    run.add_argument("--expected-execution", required=True)
    run.add_argument("--expected-storage", required=True)
    run.add_argument("--generation", required=True)
    control = commands.add_parser("control")
    control.add_argument("operation", choices=("status", "drain", "resume"))
    commands.add_parser("identity")
    commands.add_parser("release")
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        if arguments.command == "release":
            # This probe imports no Workspace and reads no operator policy or
            # project store. A service manager must be able to inspect the
            # executable before deciding whether it may open/migrate a store.
            print(
                encode(
                    {
                        "schema_version": 1,
                        "runtime_sha256": RuntimeSnapshot.capture().sha256,
                        "storage_schema_version": SCHEMA_VERSION,
                    }
                ).decode()
            )
            return 0
        if arguments.command == "serve":
            if (
                any(
                    re.fullmatch(r"[a-f0-9]{64}", value) is None
                    for value in (
                        arguments.expected_runtime,
                        arguments.expected_execution,
                        arguments.expected_storage,
                    )
                )
                or re.fullmatch(r"[a-f0-9]{32}", arguments.generation) is None
            ):
                raise ValueError(
                    "expected execution hashes and launch generation required"
                )
            return serve(
                arguments.expected_runtime,
                arguments.expected_execution,
                arguments.expected_storage,
                arguments.generation,
            )
        settings = RuntimeConfig.from_environment()
        if arguments.command == "identity":
            workspace, energy = settings.open()
            pv = settings.pv_service(workspace)
            weather = settings.weather_service(workspace)
            registry = service_registry(energy, pv, weather)
            print(
                encode(
                    {
                        "schema_version": 1,
                        "runtime_sha256": energy.kernel.runtime.sha256,
                        "execution_key": registry.execution_key(),
                        "storage_binding": storage_binding(workspace.database.path),
                    }
                ).decode()
            )
            return 0
        state = ExecutionControl(Workspace(Path(settings.directory)))
        if arguments.operation != "status":
            state.set_draining(arguments.operation == "drain")
        print(encode(state.status()).decode())
        return 0
    except Exception:
        LOG.exception("planning worker operation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
