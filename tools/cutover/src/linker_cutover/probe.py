"""Concurrent page/REST proof around the real deployment command (#298)."""

from __future__ import annotations

import json
import shlex
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import atomic, plan
from linker_cutover.target import CutoverError, Target

# Chosen acceptance sampling: #298's former ~30 s window gets ~300 samples per
# endpoint at 0.1 s. This is a probe setting, not a production service threshold.
INTERVAL_SECONDS = 0.1


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


def _sample(target: Target, endpoint: plan.ProbeEndpoint, phase: str) -> Sample:
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
        endpoint.name, phase, stamp, time.monotonic() - start, status, valid, error
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


def observe(target: Target, deploy: Callable[[], int], *, evidence: Path) -> Proof:
    """Baseline all endpoints, continuously probe each during deploy, then read back."""
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
    lock = threading.Lock()

    def watch(endpoint: plan.ProbeEndpoint) -> None:
        while True:
            sample = _sample(target, endpoint, "during")
            with lock:
                samples.append(sample)
            if stop.wait(INTERVAL_SECONDS):
                return

    threads = [
        threading.Thread(target=watch, args=(endpoint,)) for endpoint in endpoints
    ]
    for thread in threads:
        thread.start()
    try:
        exit_code = deploy()
    finally:
        stop.set()
        for thread in threads:
            thread.join()
    samples += [_sample(target, endpoint, "after") for endpoint in endpoints]
    after_logs = _fatal_metadata(target)
    unchanged = all(
        after_logs.get(path) == value for path, value in before_logs.items()
    ) and all(
        path in before_logs or value[1] == "0" for path, value in after_logs.items()
    )
    notes: list[str] = []
    try:
        renamed = _rename_proof(target, before)
    except CutoverError as error:
        renamed = False
        notes.append(str(error))
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
