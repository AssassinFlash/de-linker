"""The nightly sync refreshes the feed and the contract from one fetch (#493).

The script is exercised end to end: a stub server answers the engineering
feed, the engine's own loaders validate through the real probe commands, and
the files land in a temporary state directory.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SYNC = Path(__file__).resolve().parents[1] / "ops" / "sync-feed.py"
SHIPPED_COMPATIBILITY = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "linker-commerce"
    / "data"
    / "compatibility.json"
)


def load_sync() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_feed", SYNC)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QuietHandler(SimpleHTTPRequestHandler):
    """The stub answers the feed and keeps the test output clean."""

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def feed_url(tmp_path: Path) -> Iterator[str]:
    class Handler(QuietHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(tmp_path), **kwargs)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = server.server_address
        yield f"http://{str(address[0])}:{int(address[1])}/feed.json"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class Restarter:
    """Counts the restarts the script asks for and succeeds."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> subprocess.CompletedProcess[str]:
        self.calls += 1
        return subprocess.CompletedProcess([], 0, "", "")


def feed_document() -> dict[str, Any]:
    from conftest import publication_feed

    return publication_feed(
        json.loads((FIXTURES / "feed.json").read_text()),
        json.loads((FIXTURES / "compatibility.json").read_text()),
    )


def run(
    sync: ModuleType, directory: Path, url: str, *, loaded=None, jobs=None
) -> tuple[int, Restarter, list[str], Path, Path]:
    state = directory / "state"
    state.mkdir(exist_ok=True)
    feed = state / "feed.json"
    contract = state / "compatibility.json"
    if not feed.exists():
        feed.write_bytes(b"old feed")
        contract.write_bytes(b"old contract")
    restarter = Restarter()
    lines: list[str] = []

    def actual():
        document = json.loads(feed.read_text())
        return {
            "source_revision": document["source_revision"],
            "compatibility_revision": document["compatibility_revision"],
        }

    code = sync.sync(
        feed_url=url,
        feed_target=feed,
        compatibility_target=contract,
        probe_python=sys.executable,
        restart=restarter,
        loaded=loaded or actual,
        jobs=jobs,
        log=lines.append,
    )
    return code, restarter, lines, feed, contract


@pytest.mark.parametrize("empty", [False, True])
def test_complete_generation_including_empty_products(
    tmp_path: Path, feed_url: str, empty: bool
) -> None:
    document = feed_document()
    if empty:
        document["products"] = []
    (tmp_path / "feed.json").write_text(json.dumps(document))
    code, restart, logs, feed, contract = run(load_sync(), tmp_path, feed_url)
    assert code == 0, logs
    assert restart.calls == 1
    assert feed.is_symlink() and contract.is_symlink()
    assert feed.resolve().parent == contract.resolve().parent
    assert json.loads(feed.read_text())["products"] == document["products"]
    assert json.loads(contract.read_text()) == document["compatibility"]
    manifest = json.loads((feed.resolve().parent / "manifest.json").read_text())
    assert manifest["feed_sha256"] == hashlib.sha256(feed.read_bytes()).hexdigest()
    assert (
        manifest["compatibility_sha256"]
        == hashlib.sha256(contract.read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("invalid", ["contract", "feed", "missing", "mismatch"])
def test_any_invalid_part_preserves_both_originals(
    tmp_path: Path, feed_url: str, invalid: str
) -> None:
    document = feed_document()
    if invalid == "contract":
        document["compatibility"]["pairs"] = "invalid"
    elif invalid == "feed":
        document["products"][0]["phase"] = 7
    elif invalid == "missing":
        del document["compatibility"]
    else:
        document["compatibility"]["version"] = "mismatch"
    (tmp_path / "feed.json").write_text(json.dumps(document))
    code, restart, logs, feed, contract = run(load_sync(), tmp_path, feed_url)
    assert code == 1, logs
    assert restart.calls == 0
    assert feed.read_bytes() == b"old feed"
    assert contract.read_bytes() == b"old contract"
    assert not list(feed.parent.glob("publication-generation-*"))


def test_process_readback_failure_rolls_back_the_whole_generation(
    tmp_path: Path, feed_url: str
) -> None:
    document = feed_document()
    (tmp_path / "feed.json").write_text(json.dumps(document))
    code, _, _, feed, contract = run(load_sync(), tmp_path, feed_url)
    assert code == 0
    old = feed.resolve().parent
    document["products"] = []
    document["source_revision"] = "b" * 64
    (tmp_path / "feed.json").write_text(json.dumps(document))
    code, restart, logs, feed, contract = run(
        load_sync(),
        tmp_path,
        feed_url,
        loaded=lambda: {
            "source_revision": "old-process",
            "compatibility_revision": "old",
        },
    )
    assert code == 1, logs
    assert restart.calls == 2
    assert feed.resolve().parent == contract.resolve().parent == old
    assert len(list(feed.parent.glob("publication-generation-*"))) == 2


def test_retains_only_current_and_previous_generation(
    tmp_path: Path, feed_url: str
) -> None:
    for revision in ("a", "b", "c"):
        document = feed_document()
        document["source_revision"] = revision * 64
        (tmp_path / "feed.json").write_text(json.dumps(document))
        code, _, logs, feed, _ = run(load_sync(), tmp_path, feed_url)
        assert code == 0, logs
    assert len(list(feed.parent.glob("publication-generation-*"))) == 2


def test_jobs_ack_only_the_running_source(tmp_path: Path, feed_url: str) -> None:
    document = feed_document()
    (tmp_path / "feed.json").write_text(json.dumps(document))
    calls = []

    def jobs(action, payload):
        calls.append((action, payload))
        return (
            {
                "job": {
                    "job_id": "current",
                    "lease_token": "synthetic",
                    "source_revision": document["source_revision"],
                }
            }
            if action == "claim"
            else {}
        )

    code, _, logs, _, _ = run(load_sync(), tmp_path, feed_url, jobs=jobs)
    assert code == 0, logs
    assert calls[-1][0] == "ack"
    assert calls[-1][1]["status"] == "ready"
    assert calls[-1][1]["loaded_revision"] == document["source_revision"]


def test_no_job_has_no_fetch_or_restart(tmp_path: Path, feed_url: str) -> None:
    code, restart, logs, feed, contract = run(
        load_sync(), tmp_path, feed_url, jobs=lambda action, payload: {"job": None}
    )
    assert code == 0, logs
    assert restart.calls == 0
    assert feed.read_bytes() == b"old feed"
    assert contract.read_bytes() == b"old contract"


def test_fetch_failure_keeps_both_files(tmp_path: Path, feed_url: str) -> None:
    code, restart, logs, feed, contract = run(load_sync(), tmp_path, feed_url)
    assert code == 1, logs
    assert restart.calls == 0
    assert feed.read_bytes() == b"old feed"
    assert contract.read_bytes() == b"old contract"
