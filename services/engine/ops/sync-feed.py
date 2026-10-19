#!/usr/bin/env python3
"""Refresh the design engine's product feed from the site's engineering feed.

The engine loads LINKER_ENGINE_FEED (state/feed.json) at start and refuses a
feed that does not match schemas/feed.schema.json. This sync keeps that file
current: fetch, validate with the engine's own loader, atomic swap. A failed
fetch or validation preserves the previous feed — the engine keeps running on
the last good data, and the log says why (the same failure semantics the
old material-registry sync had).

Deployed by hand: this file goes to /opt/linker-engine/ops/sync-feed.py (a
stable path outside the release symlink, like state/), the units beside this
file go to /etc/systemd/system, `systemctl enable --now
linker-engine-feed-sync.timer` once. `just cutover services` also ships a copy
under current/ops/, but the unit runs the stable path so a release swap cannot
change the sync; update the stable copy when this file changes.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

FEED_URL = "https://de-linker.com/wp-json/linker/v1/engineering-feed"
TARGET = Path("/opt/linker-engine/state/feed.json")
STATE = Path("/var/log/linker-engine-feed-sync.log")
# The engine's own loader, run with the release venv, validates against the
# shipped schema — the same gate the engine applies at start.
PROBE = (
    "import pathlib, sys; "
    "from linker_engine.products import Products; "
    "Products.load(pathlib.Path(sys.argv[1])); "
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


def main() -> int:
    try:
        request = urllib.request.Request(
            FEED_URL, headers={"User-Agent": "linker-engine-feed-sync/1.0"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        document = json.loads(raw)
    except Exception as error:  # noqa: BLE001 — the log line is the contract.
        log(f"fetch failed; previous feed preserved: <{error!r}>")
        return 1
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        log("fetch ok but shape unexpected; previous feed preserved")
        return 1
    products = document.get("products")
    if not isinstance(products, list) or not products:
        log("feed carries no products; previous feed preserved")
        return 1

    directory = TARGET.parent
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=".feed-", suffix=".json")
    os.close(descriptor)  # The file is written through its own path below.
    temporary = Path(name)
    try:
        os.chmod(temporary, 0o644)
        temporary.write_bytes(raw)
        probe = subprocess.run(
            [PROBE_PYTHON, "-c", PROBE, str(temporary)],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0 or "validated" not in probe.stdout:
            log(
                "engine loader rejected the fetched feed; previous feed "
                f"preserved: {probe.stderr.strip()[-300:]}"
            )
            return 1
        os.replace(temporary, TARGET)
    finally:
        temporary.unlink(missing_ok=True)
    generated = document.get("generated_at", "?")
    log(f"feed refreshed ({len(products)} products, generated {generated})")
    # The engine loads the feed at start; the restart makes it current now.
    restart = subprocess.run(
        ["systemctl", "restart", "linker-engine"],
        capture_output=True,
        text=True,
        check=False,
    )
    if restart.returncode != 0:
        log(f"feed swapped but engine restart failed: {restart.stderr.strip()}")
        return 1
    log("engine restarted on the fresh feed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
