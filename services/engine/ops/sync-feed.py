#!/usr/bin/env python3
"""Publish one validated Woo feed/contract generation, then verify the process.

The existing timer is an automatic retry/reconciliation path. Revocation is
independent: requests read current Woo permission before and after work.
Two immutable generations are retained for rollback; no independent swaps.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

FEED_URL = "https://de-linker.com/wp-json/linker/v1/engineering-feed"
TARGET = Path("/opt/linker-engine/state/feed.json")
COMPATIBILITY_TARGET = Path("/opt/linker-engine/state/compatibility.json")
PROBE_PYTHON = "/opt/linker-engine/current/.venv/bin/python"
MANAGED_STATE = Path("/opt/linker-engine/state")
PROBE = "import pathlib,sys; from linker_engine.products import Products; Products.load(pathlib.Path(sys.argv[1])); print('validated')"
COMPATIBILITY_PROBE = "import pathlib,sys; from linker_engine.compatibility import Compatibility; Compatibility.load(pathlib.Path(sys.argv[1])); print('validated')"


def log(message: str) -> None:
    print(
        f"{dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} {message}", flush=True
    )


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


def public_generation(directory: Path) -> None:
    # These are public Woo projections. mkdtemp's private directory otherwise
    # blocks the dedicated non-root planner, including a legacy rollback pair.
    for published in directory.iterdir():
        os.chmod(published, 0o644)
    os.chmod(directory, 0o755)


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
        previous: Path | None = None
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
            public_generation(generation)
            current = directory / "current"
            previous = current.resolve() if current.is_symlink() else None
            if (
                previous is None
                and feed_target.is_file()
                and compatibility_target.is_file()
            ):
                # Preserve the initial legacy pair before replacing regular
                # files with managed links. Code rollback may need this pair.
                previous = Path(
                    tempfile.mkdtemp(dir=directory, prefix="publication-generation-")
                )
                (previous / "feed.json").write_bytes(feed_target.read_bytes())
                (previous / "compatibility.json").write_bytes(
                    compatibility_target.read_bytes()
                )
                public_generation(previous)
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
            if (
                generation is not None
                and (directory / "current").is_symlink()
                and (directory / "current").resolve() == generation
            ):
                for obsolete in directory.glob("publication-generation-*"):
                    if (
                        obsolete not in {generation, previous}
                        and obsolete.is_dir()
                        and not obsolete.is_symlink()
                    ):
                        shutil.rmtree(obsolete)
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
                f"publication sync did not complete; current Woo checks remain enforced: {type(error).__name__}: {error}"
            )
            return 1


def receipt_path(*, state_root: Path = MANAGED_STATE) -> Path:
    """Both units must use the same explicit cache under their writable state."""
    configured = os.environ.get("LINKER_ENGINE_CACHE", "")
    if not configured:
        raise ValueError("LINKER_ENGINE_CACHE must explicitly name the shared cache")
    directory = Path(configured)
    if (
        not directory.is_absolute()
        or directory.resolve() == state_root.resolve()
        or not directory.resolve().is_relative_to(state_root.resolve())
    ):
        raise ValueError("LINKER_ENGINE_CACHE must remain inside managed engine state")
    path = directory / "private" / "selections.sqlite"
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("private receipt data must remain inside the shared cache")
    return path


def cache_preflight(*, state_root: Path = MANAGED_STATE) -> bool:
    """Exercise SQLite writes in the real unit namespace without keeping a probe."""
    try:
        path = receipt_path(state_root=state_root)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(
            dir=path.parent, prefix=".receipt-preflight-"
        ) as temporary:
            # Match Selections' SQLite journal writes, not merely os.access().
            # One second yields to the minute retry instead of holding up work.
            with sqlite3.connect(
                Path(temporary) / "probe.sqlite", timeout=1
            ) as database:
                database.execute("CREATE TABLE probe (value INTEGER NOT NULL)")
                database.execute("INSERT INTO probe VALUES (1)")
                database.execute("DELETE FROM probe")
        if path.is_file():
            with sqlite3.connect(
                f"{path.as_uri()}?mode=rw", uri=True, timeout=1
            ) as database:
                database.execute("BEGIN IMMEDIATE")
                database.execute("DELETE FROM selections WHERE 0")
                database.rollback()
        log(f"receipt retention preflight passed: {path}")
        return True
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        log(f"receipt retention preflight failed: {type(error).__name__}: {error}")
        return False


def cleanup_receipts(*, state_root: Path = MANAGED_STATE) -> bool:
    """Expiry is independent of source work; an invisible cache is never success."""
    try:
        path = receipt_path(state_root=state_root)
        if not path.is_file():
            if not cache_preflight(state_root=state_root):
                return False
            log("receipt retention: database not yet created; shared cache is writable")
            return True
        with sqlite3.connect(
            f"{path.as_uri()}?mode=rw", uri=True, timeout=1
        ) as database:
            deleted = database.execute(
                "DELETE FROM selections WHERE expires < ?", (int(time.time()),)
            ).rowcount
        log(
            f"receipt retention: deleted {deleted} expired confirmed-result receipts at {path}"
        )
        return True
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        log(
            f"receipt retention failed; publication preparation still runs: {type(error).__name__}: {error}"
        )
        return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--cache-preflight", action="store_true")
    modes.add_argument("--cleanup-receipts", action="store_true")
    options = parser.parse_args(argv)
    if options.cache_preflight:
        return 0 if cache_preflight() else 1
    retained = cleanup_receipts()
    if options.cleanup_receipts:
        return 0 if retained else 1
    prepared = sync(jobs=job_request)
    return prepared if prepared else (0 if retained else 1)


if __name__ == "__main__":
    sys.exit(main())
