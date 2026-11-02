"""One delegated Linux cgroup for a frozen expanded PV evaluation."""

from __future__ import annotations

import http.client
import logging
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from threading import Event
from typing import Any, cast

from .asset_publication import AssetResult
from .canonical import Object, decode_object, encode
from .errors import (
    Conflict,
    EvidenceMissing,
    ExpandedResourceUnavailable,
    GeometricPvExpandedScopeRequired,
    InvalidInput,
    LeaseLost,
    MethodDomainExceeded,
    NotFound,
    NumericalFailure,
    PlanningError,
    ProductEvidenceChanged,
    VersionUnavailable,
)
from .records import Lease
from .storage import _sync_directory
from .worker import Control, Published, RetryableExecution
from .worker_policy import ExpandedJobPolicy

LOG = logging.getLogger(__name__)


class DelegatedGroup:
    """The existing service owns exactly one temporary child cgroup."""

    def __init__(self) -> None:
        line = Path("/proc/self/cgroup").read_text().strip().split(":", 2)
        if len(line) != 3 or line[:2] != ["0", ""]:
            raise ExpandedResourceUnavailable("cgroup v2 is required")
        current = Path("/sys/fs/cgroup") / line[2].lstrip("/")
        if current.name != "supervisor" or not current.is_dir():
            raise ExpandedResourceUnavailable("delegated supervisor subgroup required")
        self.parent = current.parent
        if not {"cpu", "memory", "pids"}.issubset(
            set((self.parent / "cgroup.controllers").read_text().split())
        ):
            raise ExpandedResourceUnavailable(
                "delegated CPU, memory and process controllers required"
            )
        (self.parent / "cgroup.subtree_control").write_text("+cpu +memory +pids")
        self.group = self.parent / "expanded-pv"

    def create(self, policy: ExpandedJobPolicy) -> None:
        if self.group.exists():
            if "populated 0" not in (self.group / "cgroup.events").read_text():
                raise ExpandedResourceUnavailable("expanded job cgroup is occupied")
            self.group.rmdir()
        self.group.mkdir()
        try:
            (self.group / "cpu.max").write_text(
                f"{policy.cpu_quota_percent * 1000} 100000"
            )
            (self.group / "memory.max").write_text(str(policy.memory_max_bytes))
            (self.group / "memory.swap.max").write_text("0")
            (self.group / "memory.oom.group").write_text("1")
            (self.group / "pids.max").write_text("16")
        except Exception:
            self.close()
            raise

    def freeze(self, paused: bool) -> None:
        (self.group / "cgroup.freeze").write_text("1" if paused else "0")

    def close(self) -> None:
        if not self.group.exists():
            return
        self.freeze(False)
        (self.group / "cgroup.kill").write_text("1")
        deadline = time.monotonic() + 5
        while "populated 0" not in (self.group / "cgroup.events").read_text():
            if time.monotonic() >= deadline:
                raise ExpandedResourceUnavailable("expanded cgroup did not empty")
            time.sleep(0.05)
        self.group.rmdir()


def available_memory() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise ExpandedResourceUnavailable("host memory availability is unknown")


def cleanup_owned_temps(directory: Path, token: str) -> None:
    """Remove only this completed lease's deterministic CAS write names."""
    if re.fullmatch(r"[a-f0-9]{32}", token) is None:
        raise ExpandedResourceUnavailable("invalid private lease token")
    for prefix in range(256):
        parent = directory / f"{prefix:02x}"
        candidate = parent / (".incoming-" + token)
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if parent.is_symlink() or not stat.S_ISREG(mode):
            raise ExpandedResourceUnavailable("invalid owned CAS temporary file")
        candidate.unlink()
        _sync_directory(parent)


def healthy(ports: tuple[int, int]) -> bool:
    for port in ports:
        started = time.monotonic()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            if response.status != 200:
                return False
            response.read(256)
        except (OSError, ValueError, http.client.HTTPException):
            return False
        finally:
            connection.close()
        if time.monotonic() - started > 0.5:
            return False
    return True


class IsolatedExecutionFailed(PlanningError):
    code = "execution_failed"


_ERRORS: dict[str, type[PlanningError]] = {
    error.code: error
    for error in (
        InvalidInput,
        GeometricPvExpandedScopeRequired,
        NumericalFailure,
        NotFound,
        Conflict,
        LeaseLost,
        MethodDomainExceeded,
        ProductEvidenceChanged,
        RetryableExecution,
        VersionUnavailable,
        ExpandedResourceUnavailable,
        IsolatedExecutionFailed,
    )
}


class ExpandedExecutor:
    """Keep the durable lease in the host while its calculation is isolated."""

    def __init__(
        self,
        group: DelegatedGroup,
        policy: ExpandedJobPolicy,
        normal_active: Event,
        stop: Event,
        blobs_directory: Path,
    ) -> None:
        self.group, self.policy = group, policy
        self.normal_active, self.stop = normal_active, stop
        self.blobs_directory = blobs_directory

    def __call__(self, lease: Lease, control: Control) -> Published:
        if available_memory() < self.policy.minimum_available_bytes:
            raise ExpandedResourceUnavailable(
                "host memory is below the configured minimum"
            )
        read_gate, write_gate = os.pipe()
        process: subprocess.Popen[bytes] | None = None
        paused = False
        owns_group = False
        started = time.monotonic()
        try:
            self.group.create(self.policy)
            owns_group = True
            env = {
                key: os.environ[key]
                for key in (
                    "LINKER_PLANNER_CONFIG",
                    "LINKER_ENGINE_FEED",
                    "LINKER_ENGINE_COMPATIBILITY",
                    "LINKER_ENGINE_CACHE",
                    "LINKER_PUBLICATION_URL",
                )
                if key in os.environ
            }
            env.update(
                PATH="/usr/bin:/bin",
                HOME="/nonexistent",
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONPATH=str(Path(__file__).resolve().parents[2]),
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                NUMEXPR_NUM_THREADS="1",
            )
            # The shell waits on this private pipe before importing Python. The
            # parent places it in the cgroup before releasing the gate.
            script = f'IFS= read -r ready <&{read_gate} || exit 1; exec /usr/bin/nice -n 19 "$@"'
            process = subprocess.Popen(
                [
                    "/bin/sh",
                    "-c",
                    script,
                    "expanded-pv",
                    sys.executable,
                    "-m",
                    "linker_engine.planning.expanded_job",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                pass_fds=(read_gate,),
                env=env,
            )
            os.close(read_gate)
            read_gate = -1
            (self.group.group / "cgroup.procs").write_text(str(process.pid))
            assert process.stdin is not None
            process.stdin.write(encode(cast(Object, asdict(lease))))
            process.stdin.close()
            os.write(write_gate, b"go\n")
            os.close(write_gate)
            write_gate = -1
            next_health = 0.0
            unhealthy = 0
            paused_since: float | None = None
            while process.poll() is None:
                control.checkpoint()
                if self.stop.is_set():
                    raise LeaseLost("worker is stopping")
                now = time.monotonic()
                if now - started > self.policy.timeout_seconds:
                    raise ExpandedResourceUnavailable(
                        "expanded task exceeded its runtime"
                    )
                if available_memory() < self.policy.minimum_available_bytes:
                    raise ExpandedResourceUnavailable(
                        "host memory is below the configured minimum"
                    )
                if now >= next_health:
                    unhealthy = (
                        0 if healthy(self.policy.health_ports) else unhealthy + 1
                    )
                    next_health = now + 5
                should_pause = self.normal_active.is_set() or unhealthy >= 2
                if should_pause != paused:
                    self.group.freeze(should_pause)
                    paused = should_pause
                    paused_since = now if paused else None
                if paused_since is not None and now - paused_since > 60:
                    raise ExpandedResourceUnavailable(
                        "normal work or health stayed busy"
                    )
                self.stop.wait(0.25)
            control.checkpoint()
            assert process.stdout is not None
            data = process.stdout.read(1024 * 1024 + 1)
            if process.returncode != 0 or len(data) > 1024 * 1024:
                raise ExpandedResourceUnavailable("isolated task did not complete")
            response = decode_object(data)
            if "error" in response:
                location = response.get("location")
                if response["error"] == VersionUnavailable.code and isinstance(
                    location, dict
                ):
                    module, function, line = (
                        location.get("module"),
                        location.get("function"),
                        location.get("line"),
                    )
                    if (
                        isinstance(module, str)
                        and re.fullmatch(r"[A-Za-z0-9_.]{1,160}", module)
                        and isinstance(function, str)
                        and re.fullmatch(r"[A-Za-z0-9_.<>]{1,160}", function)
                        and type(line) is int
                        and 0 < line < 1000000
                    ):
                        LOG.warning(
                            "planning job %s version_unavailable during isolated execution at %s.%s:%d",
                            lease.id,
                            module,
                            function,
                            line,
                        )
                if response["error"] == EvidenceMissing.code:
                    details = response.get("details")
                    if not isinstance(details, dict):
                        raise IsolatedExecutionFailed(
                            "isolated evidence error is invalid"
                        )
                    raise EvidenceMissing(
                        "isolated evidence unavailable", **cast(dict[str, Any], details)
                    )
                error = _ERRORS.get(str(response["error"]), IsolatedExecutionFailed)
                raise error("isolated task failed")
            output = response.get("published")
            if (
                not isinstance(output, str)
                or re.fullmatch(r"[a-f0-9]{64}", output) is None
            ):
                raise ExpandedResourceUnavailable("isolated publication is invalid")
            return Published(output)
        finally:
            if read_gate >= 0:
                os.close(read_gate)
            if write_gate >= 0:
                os.close(write_gate)
            cleared = not owns_group
            try:
                if owns_group:
                    self.group.close()
                    cleared = True
            except Exception:
                # A failed delegated cleanup must not leave an untracked job
                # running in an otherwise healthy long-lived service.
                self.stop.set()
                raise
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                if cleared:
                    cleanup_owned_temps(self.blobs_directory, lease.token)


def main() -> int:
    """Execute only the already leased geometric kernel inside the child."""
    from .dependencies import verify_dependencies
    from .jobs import Jobs
    from .runtime_config import RuntimeConfig

    try:
        raw = decode_object(sys.stdin.buffer.read(1024 * 1024 + 1))
        lease = Lease(**cast(dict[str, Any], raw))
        settings = RuntimeConfig.from_environment()
        workspace, _energy = settings.open(temporary_id=lease.token)
        service = settings.geometric_pv_service(workspace)
        if service is None:
            raise VersionUnavailable("geometric PV is disabled")
        control = Control()
        reply = service.kernel(lease, control)
        if isinstance(reply, AssetResult):
            result = reply.result
            asset, attachments = reply.asset, reply.attachments
        else:
            result = reply
            asset, attachments = None, None
        encode(result)
        verify_dependencies(workspace.blobs, result)
        control.checkpoint()
        output = Jobs(workspace).complete(
            lease, result, asset=asset, attachments=attachments
        )
        response: Object = {"published": output}
    except PlanningError as error:
        response = {"error": error.code}
        if isinstance(error, VersionUnavailable):
            frame = error.__traceback__
            while frame is not None and frame.tb_next is not None:
                frame = frame.tb_next
            if frame is not None:
                response["location"] = {
                    "module": str(frame.tb_frame.f_globals.get("__name__", "")),
                    "function": frame.tb_frame.f_code.co_name,
                    "line": frame.tb_lineno,
                }
        if isinstance(error, EvidenceMissing):
            response["details"] = cast(Object, error.public_details)
    except Exception:
        response = {"error": "execution_failed"}
    sys.stdout.buffer.write(encode(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
