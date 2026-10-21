#!/usr/bin/env python3
"""Refresh the design engine's data from the site's engineering feed.

The engine loads LINKER_ENGINE_FEED (state/feed.json) and
LINKER_ENGINE_COMPATIBILITY (state/compatibility.json) at start and refuses a
file that does not match its schema. This sync keeps both current from one
fetch of the engineering feed, which carries the compatibility contract
beside the products: validate each file with the engine's own loader, atomic
swap, restart once. The two fail independently — a rejected contract keeps
the previous contract without rolling back a freshly swapped feed, and a
rejected feed keeps the previous feed without touching the contract — and the
log says which file kept its previous version, so a bad night costs nothing.

Deployed by hand: this file goes to /opt/linker-engine/ops/sync-feed.py (a
stable path outside the release symlink, like state/), the units beside this
file go to /etc/systemd/system, `systemctl enable --now
linker-engine-feed-sync.timer` once. `just cutover services` also ships a copy
under current/ops/, but the unit runs the stable path so a release swap cannot
change the sync; update the stable copy when this file changes, and note that
it now owns both target paths: the feed and the compatibility contract.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

FEED_URL = "https://de-linker.com/wp-json/linker/v1/engineering-feed"
TARGET = Path("/opt/linker-engine/state/feed.json")
COMPATIBILITY_TARGET = Path("/opt/linker-engine/state/compatibility.json")
STATE = Path("/var/log/linker-engine-feed-sync.log")
# The engine's own loaders, run with the release venv, validate against the
# shipped schemas — the same gate the engine applies at start.
PROBE = (
    "import pathlib, sys; "
    "from linker_engine.products import Products; "
    "Products.load(pathlib.Path(sys.argv[1])); "
    "print('validated')"
)
COMPATIBILITY_PROBE = (
    "import pathlib, sys; "
    "from linker_engine.compatibility import Compatibility; "
    "Compatibility.load(pathlib.Path(sys.argv[1])); "
    "print('validated')"
)
PROBE_PYTHON = "/opt/linker-engine/current/.venv/bin/python"


def log(message: str) -> None:
    stamp = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    line = f"{stamp} {message}"
    print(line)
    try:
        with STATE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "linker-engine-feed-sync/1.0"}
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
    """The bytes in a file beside the target, removed when the block ends."""
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".json")
    os.close(descriptor)  # The file is written through its own path below.
    temporary = Path(name)
    try:
        os.chmod(temporary, 0o644)
        temporary.write_bytes(raw)
        yield temporary
    finally:
        temporary.unlink(missing_ok=True)


def probe(python: str, code: str, path: Path) -> tuple[bool, str]:
    """The engine's loader on the staged file: (accepted, error detail)."""
    completed = subprocess.run(
        [python, "-c", code, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return (
        completed.returncode == 0 and "validated" in completed.stdout,
        completed.stderr.strip()[-300:],
    )


def swap_feed(
    raw: bytes,
    target: Path,
    probe_python: str,
    log: Callable[[str], None],
    *,
    products: int,
    generated: str,
) -> bool:
    """Atomically replace the feed; a rejected file leaves the old one."""
    try:
        with staged(target.parent, ".feed-", raw) as temporary:
            accepted, detail = probe(probe_python, PROBE, temporary)
            if not accepted:
                log(
                    "engine loader rejected the fetched feed; previous feed "
                    f"preserved: {detail}"
                )
                return False
            os.replace(temporary, target)
    except OSError as error:
        log(f"feed write failed; previous feed preserved: <{error!r}>")
        return False
    log(f"feed refreshed ({products} products, generated {generated})")
    return True


def swap_compatibility(
    document: dict[str, Any],
    target: Path,
    probe_python: str,
    log: Callable[[str], None],
) -> bool:
    """Atomically replace the contract the feed carries; the old one on failure."""
    compatibility = document.get("compatibility")
    if compatibility is None:
        log("feed carries no compatibility; previous contract preserved")
        return False
    if not isinstance(compatibility, dict):
        log("feed's compatibility is not an object; previous contract preserved")
        return False
    version = compatibility.get("version")
    if version != document.get("compatibility_version"):
        log(
            "feed's compatibility version does not match the contract it "
            "carries; previous contract preserved"
        )
        return False
    raw = (json.dumps(compatibility, ensure_ascii=False, indent=2) + "\n").encode()
    try:
        with staged(target.parent, ".compatibility-", raw) as temporary:
            accepted, detail = probe(probe_python, COMPATIBILITY_PROBE, temporary)
            if not accepted:
                log(
                    "engine loader rejected the fetched contract; previous "
                    f"contract preserved: {detail}"
                )
                return False
            os.replace(temporary, target)
    except OSError as error:
        log(f"contract write failed; previous contract preserved: <{error!r}>")
        return False
    pairs = compatibility.get("pairs")
    count = len(pairs) if isinstance(pairs, list) else "?"
    log(f"compatibility refreshed (version {version}, {count} pairs)")
    return True


def sync(
    *,
    feed_url: str = FEED_URL,
    feed_target: Path = TARGET,
    compatibility_target: Path = COMPATIBILITY_TARGET,
    probe_python: str = PROBE_PYTHON,
    fetch: Callable[[str], bytes] = fetch_feed,
    restart: Callable[[], subprocess.CompletedProcess[str]] = restart_engine,
    log: Callable[[str], None] = log,
) -> int:
    """One run: fetch, validate and swap each file; 0 only when both swapped."""
    try:
        raw = fetch(feed_url)
    except Exception as error:  # noqa: BLE001 — the log line is the contract.
        log(f"fetch failed; previous feed and contract preserved: <{error!r}>")
        return 1
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        log(f"fetch is not JSON; previous feed and contract preserved: <{error!r}>")
        return 1
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        log("fetch ok but shape unexpected; previous feed and contract preserved")
        return 1
    products = document.get("products")
    if not isinstance(products, list) or not products:
        log("feed carries no products; previous feed and contract preserved")
        return 1

    feed_swapped = swap_feed(
        raw,
        feed_target,
        probe_python,
        log,
        products=len(products),
        generated=str(document.get("generated_at", "?")),
    )
    if feed_swapped:
        compatibility_swapped = swap_compatibility(
            document, compatibility_target, probe_python, log
        )
    else:
        # The contract came out of the same fetch; a feed the loader rejects
        # leaves both files as they were.
        compatibility_swapped = False
        log("feed not refreshed; previous contract preserved")
    if not feed_swapped:
        return 1
    # The engine loads both files at start; the restart makes them current now.
    try:
        restarted = restart()
    except OSError as error:
        log(f"data swapped but engine restart failed: <{error!r}>")
        return 1
    if restarted.returncode != 0:
        log(f"data swapped but engine restart failed: {restarted.stderr.strip()}")
        return 1
    log("engine restarted on the fresh data")
    return 0 if compatibility_swapped else 1


def main() -> int:
    return sync()


if __name__ == "__main__":
    sys.exit(main())
