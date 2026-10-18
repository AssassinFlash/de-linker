"""Concurrent page/REST proof around the real deployment command (#298)."""

from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import atomic, plan
from linker_cutover.target import CutoverError, Target

# PR #299 round 3 decision 5: operator-selected acceptance rates, not a claim
# about Hostinger capacity. The existing 0.1 s cadence (#298's ~30 s incident)
# now applies to ONE aggregate stream during switch/readback, not each endpoint.
# Build/upload uses a tenfold slower 1 s delay. One worker caps in-flight GETs
# at one; response time adds to each delay, so slow hosting reduces the rate.
STEADY_INTERVAL_SECONDS = 1.0
DENSE_INTERVAL_SECONDS = 0.1
SWITCH_MARKER = "LINKER_CUTOVER_SWITCH_START"


@dataclass(frozen=True)
class Sample:
    """Only timing/status are saved; response bodies never enter the evidence."""

    endpoint: str
    phase: str
    started_at: str
    elapsed_seconds: float
    status: int | None
    valid: bool
    error_type: str = ""
    cadence: str = "snapshot"


@dataclass(frozen=True)
class Proof:
    """The independent availability, error-log and rename acceptance gates."""

    deploy_exit: int
    samples: tuple[Sample, ...]
    fatal_logs_unchanged: bool
    directory_rename_proved: bool
    before_logs: dict[str, tuple[str, str]]
    after_logs: dict[str, tuple[str, str]]
    notes: tuple[str, ...]

    @property
    def successful(self) -> bool:
        return (
            self.deploy_exit == 0
            and all(sample.valid for sample in self.samples)
            and self.fatal_logs_unchanged
            and self.directory_rename_proved
            and not self.notes
        )


def _valid(endpoint: plan.ProbeEndpoint, body: str, target: Target) -> bool:
    if endpoint.response == "html":
        return "<html" in body.lower()
    payload = json.loads(body)
    if endpoint.response == "items":
        return isinstance(payload, dict) and isinstance(payload.get("items"), list)
    if endpoint.response == "thread":
        return (
            isinstance(payload, dict)
            and "conversation_id" in payload
            and isinstance(payload.get("messages"), list)
        )
    if endpoint.response == "german-pages":
        return (
            isinstance(payload, list)
            and bool(payload)
            and all(
                isinstance(page, dict)
                and str(page.get("link", "")).startswith(
                    target.base_url.rstrip("/") + "/de/"
                )
                for page in payload
            )
        )
    raise CutoverError(f"unknown probe contract {endpoint.response}")


def _sample(
    target: Target, endpoint: plan.ProbeEndpoint, phase: str, cadence: str = "snapshot"
) -> Sample:
    stamp = datetime.now(UTC).isoformat()
    start = time.monotonic()
    status = None
    try:
        status, body = target.http(endpoint.path, cache_buster=str(time.time_ns()))
        valid = status == 200 and _valid(endpoint, body, target)
        error = ""
    except (CutoverError, ValueError) as error_object:
        valid, error = False, type(error_object).__name__
    return Sample(
        endpoint.name,
        phase,
        stamp,
        time.monotonic() - start,
        status,
        valid,
        error,
        cadence,
    )


def _fatal_metadata(target: Target) -> dict[str, tuple[str, str]]:
    directory = shlex.quote(target.path_of("wp-content/uploads/wc-logs"))
    # Identity and size only: a missing/rotated/truncated file invalidates the
    # comparison; no log content, account configuration or credentials are read.
    output = target.shell(f"""set -euo pipefail
test -d {directory}
size() {{ stat -c '%s' "$1" 2>/dev/null || stat -f '%z' "$1"; }}
find {directory} -type f -name 'fatal-errors-*.log' -print0 |
while IFS= read -r -d '' path; do
    printf '%s\\t%s\\n' "$path" "$(size "$path")"
done
""")
    sizes = dict(line.split("\t", 1) for line in output.splitlines())
    inodes = atomic.identities(target, list(sizes)) if sizes else {}
    if any(inode == "-" for inode in inodes.values()):
        raise CutoverError("fatal log changed while reading metadata")
    return {path: (inodes[path], size) for path, size in sizes.items()}


def _rename_proof(target: Target, before: dict[str, str]) -> bool:
    directory, manifest = atomic.latest_manifest(target)
    if manifest.state != "archived":
        return False
    entries = {entry.relative: entry for entry in manifest.backups}
    paths = [f"{plan.PLUGINS_DIR}/{slug}" for slug in plan.NEW_PLUGINS]
    saved = [str(Path(directory) / "files" / path) for path in paths]
    actual = atomic.identities(target, saved)
    return all(
        path in entries
        and entries[path].deploy_id == manifest.deploy_id
        and entries[path].inode == before[target.path_of(path)] == actual[backup]
        and actual[backup] != "-"
        for path, backup in zip(paths, saved, strict=True)
    )


def run_deployment(
    command: list[str], *, repository: Path, log: Path, on_switch: Callable[[], None]
) -> int:
    """Stream the real CLI's switch marker while retaining its local deploy log."""
    with (
        log.open("w") as output,
        subprocess.Popen(
            command,
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as process,
    ):
        assert process.stdout is not None
        for line in process.stdout:
            output.write(line)
            output.flush()
            # The deploy prints each phase and artifact as it starts; without
            # this the terminal showed nothing until the end (measured
            # 2026-10-18: a 26-minute deploy looked like a hang).
            print(line, end="", flush=True)
            if line.rstrip("\n") == SWITCH_MARKER:
                on_switch()
        return process.wait()


def observe(
    target: Target, deploy: Callable[[Callable[[], None]], int], *, evidence: Path
) -> Proof:
    """Probe slowly through builds/uploads, densely from switch through readback."""
    evidence.mkdir(parents=True, exist_ok=True)
    endpoints = plan.DEPLOY_PROBE_ENDPOINTS
    samples = [_sample(target, endpoint, "before") for endpoint in endpoints]
    failed = [sample.endpoint for sample in samples if not sample.valid]
    if failed:
        (evidence / "proof.json").write_text(
            json.dumps(
                {
                    "baseline_failed": failed,
                    "samples": [asdict(sample) for sample in samples],
                },
                indent=2,
            )
            + "\n"
        )
        raise CutoverError("probe baseline failed: " + ", ".join(failed))
    before_logs = _fatal_metadata(target)
    before = atomic.identities(
        target,
        [target.path_of(f"{plan.PLUGINS_DIR}/{slug}") for slug in plan.NEW_PLUGINS],
    )
    stop = threading.Event()
    switching = threading.Event()
    wake = threading.Event()
    dense_or_stopped = threading.Event()
    worker_errors: list[str] = []

    def switch_started() -> None:
        switching.set()
        wake.set()

    def watch() -> None:
        index = 0
        dense_seen: set[str] = set()
        try:
            while not stop.is_set():
                endpoint = endpoints[index % len(endpoints)]
                cadence = "dense" if switching.is_set() else "steady"
                sample = _sample(target, endpoint, "during", cadence)
                samples.append(sample)
                if cadence == "dense":
                    dense_seen.add(endpoint.name)
                    if len(dense_seen) == len(endpoints):
                        dense_or_stopped.set()
                index += 1
                wake.wait(
                    DENSE_INTERVAL_SECONDS
                    if switching.is_set()
                    else STEADY_INTERVAL_SECONDS
                )
                wake.clear()
        except Exception as error:
            # A failed worker must wake its observer, including transport errors
            # outside _sample's normal contract (e.g. a truncated HTTP body).
            worker_errors.append(f"probe worker failed: {type(error).__name__}")
        finally:
            dense_or_stopped.set()

    thread = threading.Thread(target=watch)
    thread.start()
    notes: list[str] = []
    try:
        exit_code = deploy(switch_started)
        if switching.is_set():
            # Even a very fast local switch must sample every endpoint in the
            # dense phase before the final log/inode readback closes the window.
            dense_or_stopped.wait()
        else:
            notes.append("deployment did not report the switch marker")
    finally:
        stop.set()
        wake.set()
        thread.join()
    notes += worker_errors
    samples += [_sample(target, endpoint, "after") for endpoint in endpoints]
    after_logs = _fatal_metadata(target)
    try:
        renamed = _rename_proof(target, before)
    except CutoverError as error:
        renamed = False
        notes.append(str(error))
    unchanged = all(
        after_logs.get(path) == value for path, value in before_logs.items()
    ) and all(
        path in before_logs or value[1] == "0" for path, value in after_logs.items()
    )
    result = Proof(
        exit_code,
        tuple(samples),
        unchanged,
        renamed,
        before_logs,
        after_logs,
        tuple(notes),
    )
    (evidence / "proof.json").write_text(
        json.dumps(asdict(result) | {"successful": result.successful}, indent=2) + "\n"
    )
    return result
