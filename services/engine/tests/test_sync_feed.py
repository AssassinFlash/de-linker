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
    """The fixture feed as the site serves it after #493: contract included."""
    document: dict[str, Any] = json.loads((FIXTURES / "feed.json").read_text())
    contract: dict[str, Any] = json.loads((FIXTURES / "compatibility.json").read_text())
    document["compatibility"] = contract
    document["compatibility_version"] = contract["version"]
    return document


def serve(directory: Path, document: dict[str, Any]) -> None:
    (directory / "feed.json").write_text(json.dumps(document))


def run(
    sync: ModuleType,
    directory: Path,
    url: str,
) -> tuple[int, Restarter, list[str], Path, Path]:
    state = directory / "state"
    state.mkdir()
    feed_target = state / "feed.json"
    compatibility_target = state / "compatibility.json"
    feed_target.write_bytes(b"old feed")
    compatibility_target.write_bytes(b"old contract")
    restarter = Restarter()
    lines: list[str] = []
    code = sync.sync(
        feed_url=url,
        feed_target=feed_target,
        compatibility_target=compatibility_target,
        probe_python=sys.executable,
        restart=restarter,
        log=lines.append,
    )
    return code, restarter, lines, feed_target, compatibility_target


def test_a_successful_run_swaps_both_files_and_restarts_once(
    tmp_path: Path, feed_url: str
) -> None:
    document = feed_document()
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 0
    assert restarter.calls == 1
    assert json.loads(feed_target.read_text())["products"] == document["products"]
    assert json.loads(contract_target.read_text()) == document["compatibility"]
    assert any("feed refreshed (" in line for line in lines), lines
    assert any("compatibility refreshed (version " in line for line in lines)
    assert any("engine restarted on the fresh data" in line for line in lines)
    assert sorted(path.name for path in (tmp_path / "state").iterdir()) == [
        "compatibility.json",
        "feed.json",
    ], "the staging files leave no temp files behind"


def test_the_written_contract_keeps_the_shipped_contracts_content_hash(
    tmp_path: Path, feed_url: str
) -> None:
    """The ticket's acceptance: the VPS contract version is its content hash."""
    contract: dict[str, Any] = json.loads(SHIPPED_COMPATIBILITY.read_text())
    document = feed_document()
    document["compatibility"] = contract
    document["compatibility_version"] = contract["version"]
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 0
    written: dict[str, Any] = json.loads(contract_target.read_text())
    assert written == contract
    stored = written.pop("version")
    canonical = json.dumps(
        written, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    assert stored == hashlib.sha256(canonical.encode()).hexdigest()


def test_a_rejected_contract_keeps_the_old_contract_and_the_feed_still_swaps(
    tmp_path: Path, feed_url: str
) -> None:
    document = feed_document()
    # The version matches, but the contract is not a contract: the loader refuses it.
    document["compatibility"] = {
        "schema_version": 1,
        "version": document["compatibility_version"],
    }
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 1
    assert restarter.calls == 1, "the freshly swapped feed still needs the restart"
    assert json.loads(feed_target.read_text())["products"] == document["products"]
    assert contract_target.read_bytes() == b"old contract"
    assert any("engine loader rejected the fetched contract" in line for line in lines)
    assert any("feed refreshed (" in line for line in lines)


def test_a_rejected_feed_keeps_both_files(tmp_path: Path, feed_url: str) -> None:
    document = feed_document()
    del document["products"][0]["phase"]
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 1
    assert restarter.calls == 0
    assert feed_target.read_bytes() == b"old feed"
    assert contract_target.read_bytes() == b"old contract"
    assert any("engine loader rejected the fetched feed" in line for line in lines)
    assert any(
        "feed not refreshed; previous contract preserved" in line for line in lines
    )


def test_a_contract_that_does_not_match_the_feed_version_keeps_the_old_contract(
    tmp_path: Path, feed_url: str
) -> None:
    document = feed_document()
    document["compatibility_version"] = "not-the-contract-version"
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 1
    assert restarter.calls == 1
    assert json.loads(feed_target.read_text())["products"] == document["products"]
    assert contract_target.read_bytes() == b"old contract"
    assert any("does not match the contract it carries" in line for line in lines)


def test_a_feed_without_the_contract_keeps_the_old_contract_and_swaps_the_feed(
    tmp_path: Path, feed_url: str
) -> None:
    """The feed the site served before #493: products valid, no contract key."""
    document = feed_document()
    del document["compatibility"]
    serve(tmp_path, document)

    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 1
    assert restarter.calls == 1
    assert json.loads(feed_target.read_text())["products"] == document["products"]
    assert contract_target.read_bytes() == b"old contract"
    assert any("feed carries no compatibility" in line for line in lines)


def test_a_fetch_failure_keeps_both_files(tmp_path: Path, feed_url: str) -> None:
    code, restarter, lines, feed_target, contract_target = run(
        load_sync(), tmp_path, feed_url
    )

    assert code == 1
    assert restarter.calls == 0
    assert feed_target.read_bytes() == b"old feed"
    assert contract_target.read_bytes() == b"old contract"
    assert any(
        "fetch failed; previous feed and contract preserved" in line for line in lines
    )
