#!/usr/bin/env python3
"""Publish one validated Woo feed/contract generation, then verify the process.

The existing timer is an automatic retry/reconciliation path. Revocation is
independent: requests read current Woo permission before and after work.
Two immutable generations are retained for rollback; no independent swaps.
"""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

FEED_URL = "https://de-linker.com/wp-json/linker/v1/engineering-feed"
TARGET = Path("/opt/linker-engine/state/feed.json")
COMPATIBILITY_TARGET = Path("/opt/linker-engine/state/compatibility.json")
STATE = Path("/var/log/linker-engine-feed-sync.log")
PROBE_PYTHON = "/opt/linker-engine/current/.venv/bin/python"
PROBE = "import pathlib,sys; from linker_engine.products import Products; Products.load(pathlib.Path(sys.argv[1])); print('validated')"
COMPATIBILITY_PROBE = "import pathlib,sys; from linker_engine.compatibility import Compatibility; Compatibility.load(pathlib.Path(sys.argv[1])); print('validated')"


def log(message: str) -> None:
    line = f"{dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} {message}"
    print(line)
    try:
        with STATE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "linker-engine-feed-sync/2.0",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return bytes(response.read())


def restart_engine() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "restart", "linker-engine"],
        capture_output=True,
        text=True,
        check=False,
    )


@contextlib.contextmanager
def staged(directory: Path, prefix: str, raw: bytes) -> Iterator[Path]:
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".json")
    os.close(descriptor)
    temporary = Path(name)
    try:
        os.chmod(temporary, 0o644)
        temporary.write_bytes(raw)
        yield temporary
    finally:
        temporary.unlink(missing_ok=True)


def probe(python: str, code: str, path: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [python, "-c", code, str(path)], capture_output=True, text=True, check=False
    )
    return (
        completed.returncode == 0 and "validated" in completed.stdout,
        completed.stderr.strip()[-300:],
    )


def atomic_link(target: Path, link: Path) -> None:
    temporary = link.with_name(f".{link.name}-{os.getpid()}")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def read_loaded() -> dict[str, Any]:
    request = urllib.request.Request(
        os.environ.get(
            "LINKER_ENGINE_LOADED_URL", "http://127.0.0.1:8901/resource/version?ready=1"
        ),
        headers={"X-Linker-Service-Token": os.environ.get("GENIE_SERVICE_TOKEN", "")},
    )
    with urllib.request.urlopen(request, timeout=10) as reply:
        return dict(json.load(reply))


def job_request(action: str, body: dict[str, Any]) -> dict[str, Any]:
    base = os.environ.get(
        "LINKER_PUBLICATION_JOBS_URL",
        "https://de-linker.com/wp-json/linker/v1/publication/jobs",
    )
    user = os.environ.get("LINKER_PUBLICATION_USER", "")
    password = os.environ.get("LINKER_PUBLICATION_PASSWORD", "")
    if not user or not password:
        raise RuntimeError("publication worker credentials are not configured")
    authorization = base64.b64encode(f"{user}:{password}".encode()).decode()
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{action}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return dict(json.load(response))


def sync(
    *,
    feed_url: str = FEED_URL,
    feed_target: Path = TARGET,
    compatibility_target: Path = COMPATIBILITY_TARGET,
    probe_python: str = PROBE_PYTHON,
    fetch: Callable[[str], bytes] = fetch_feed,
    restart: Callable[[], subprocess.CompletedProcess[str]] = restart_engine,
    loaded: Callable[[], dict[str, Any]] = read_loaded,
    log: Callable[[str], None] = log,
    jobs: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> int:
    """A single generation or none; an empty product set is a valid withdrawal."""
    directory = feed_target.parent
    if compatibility_target.parent != directory:
        log("feed and compatibility must share the managed generation directory")
        return 1
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".publication-sync.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        generation: Path | None = None
        job = None
        try:
            if jobs is not None:
                job = jobs(
                    "claim",
                    {
                        "consumer": "engineering",
                        "worker_id": f"engine-{socket.gethostname()}",
                        "lease_seconds": 300,
                    },
                ).get("job")
                if job is None:
                    log("no pending engineering preparation")
                    return 0
            raw = fetch(feed_url)
            document = json.loads(raw)
            contract = document.get("compatibility")
            if (
                job is not None
                and document.get("source_revision") != job["source_revision"]
            ):
                raise ValueError("source changed after preparation claim")
            if (
                not isinstance(document.get("products"), list)
                or not isinstance(contract, dict)
                or contract.get("version") != document.get("compatibility_version")
                or not document.get("source_revision")
                or not document.get("compatibility_revision")
            ):
                raise ValueError("incomplete publication generation")
            contract_raw = (
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
            ).encode()
            generation = Path(
                tempfile.mkdtemp(dir=directory, prefix="publication-generation-")
            )
            feed_path = generation / "feed.json"
            contract_path = generation / "compatibility.json"
            feed_path.write_bytes(raw)
            contract_path.write_bytes(contract_raw)
            for code, path in (
                (PROBE, feed_path),
                (COMPATIBILITY_PROBE, contract_path),
            ):
                valid, detail = probe(probe_python, code, path)
                if not valid:
                    raise ValueError(f"loader rejected complete generation: {detail}")
            manifest = {
                "source_revision": document["source_revision"],
                "compatibility_revision": document["compatibility_revision"],
                "feed_sha256": hashlib.sha256(raw).hexdigest(),
                "compatibility_sha256": hashlib.sha256(contract_raw).hexdigest(),
            }
            (generation / "manifest.json").write_text(json.dumps(manifest))
            current = directory / "current"
            previous = current.resolve() if current.is_symlink() else None
            atomic_link(generation, current)
            # Only the initial migration changes these links. The process pins
            # the resolved feed generation, so it never reads a mixed contract.
            for target, name in (
                (feed_target, "feed.json"),
                (compatibility_target, "compatibility.json"),
            ):
                atomic_link(current / name, target)
            try:
                restarted = restart()
                if restarted.returncode != 0:
                    raise RuntimeError("engine restart failed")
                for attempt in range(5):
                    try:
                        actual = loaded()
                        break
                    except OSError:
                        if attempt == 4:
                            raise
                        time.sleep(0.5)
                if (
                    actual.get("source_revision") != manifest["source_revision"]
                    or actual.get("compatibility_revision")
                    != manifest["compatibility_revision"]
                ):
                    raise RuntimeError(
                        "process has not loaded the published generation"
                    )
            except Exception:
                if previous is not None:
                    atomic_link(previous, current)
                    restart()
                raise
            if jobs is not None and job is not None:
                jobs(
                    "ack",
                    {
                        "job_id": job["job_id"],
                        "lease_token": job["lease_token"],
                        "source_revision": job["source_revision"],
                        "loaded_revision": actual["source_revision"],
                        "prepared_products": actual.get("prepared_products", []),
                        "status": "ready",
                    },
                )
            keep = {generation, previous}
            for obsolete in directory.glob("publication-generation-*"):
                if (
                    obsolete not in keep
                    and obsolete.is_dir()
                    and not obsolete.is_symlink()
                ):
                    shutil.rmtree(obsolete)
            log(
                f"published and loaded source {manifest['source_revision']} ({len(document['products'])} products)"
            )
            return 0
        except Exception as error:  # noqa: BLE001 -- timer retry records all failures.
            if (
                generation is not None
                and generation.exists()
                and not (
                    (directory / "current").is_symlink()
                    and (directory / "current").resolve() == generation
                )
            ):
                shutil.rmtree(generation)
            if jobs is not None and job is not None:
                try:
                    jobs(
                        "ack",
                        {
                            "job_id": job["job_id"],
                            "lease_token": job["lease_token"],
                            "source_revision": job["source_revision"],
                            "loaded_revision": "",
                            "status": "failed",
                            "error": type(error).__name__,
                        },
                    )
                except Exception:  # noqa: BLE001 -- the lease remains retryable.
                    pass
            log(
                f"publication sync failed; previous loaded data retained: {type(error).__name__}: {error}"
            )
            return 1


def main() -> int:
    return sync(jobs=job_request)


if __name__ == "__main__":
    sys.exit(main())
