#!/usr/bin/env python3
"""Replay consent settings through native CookieYes plugins; never connect a GA property.

The deploy path is ``configure_consent`` in tools/cutover. It replays this
PHP after the cutover database snapshot, then reads the site back. That
snapshot is the backup for a deploy. This script is the standalone entry, so
``--write`` refuses to run without ``--backup-dir``: it exports the affected
CookieYes settings, banner, categories, cookies, privacy pages and Site Kit
consent option, writes, then reads the site back and fails unless the plan
reports no drift.

    python3 tools/migrate/201-consent.py --wp ~/de-linker-local/t201/wp
    python3 tools/migrate/201-consent.py --wp ~/de-linker-local/t201/wp --write --backup-dir ~/de-linker-local/t201/backups
"""

from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DIRECTORY = Path(__file__).resolve().parent
PHP = DIRECTORY / "201-consent.php"
PLAN = DIRECTORY / "201-consent.json"
MARKER = "@@201-consent@@"


def marked_json(stdout: str) -> dict[str, Any]:
    """The export line the PHP prints. Other WP-CLI noise stays on the stream."""
    for line in stdout.splitlines():
        index = line.find(MARKER)
        if index < 0:
            continue
        parsed = json.loads(line[index + len(MARKER) :])
        if isinstance(parsed, dict):
            return parsed
    raise SystemExit("consent export did not print a snapshot")


def invoke(wp: list[str], payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    """Run 201-consent.php inside WordPress. The payload is one eval argument."""
    source = PHP.read_text()
    if source.count("__LINKER_CONSENT_PAYLOAD__") != 1:
        raise SystemExit("201-consent.php must contain its payload placeholder once.")
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    return subprocess.run(
        [
            *wp,
            "eval",
            source.removeprefix("<?php").replace("__LINKER_CONSENT_PAYLOAD__", encoded),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def relay(completed: subprocess.CompletedProcess[str]) -> None:
    """Show the PHP answer. A failure is the caller's to report."""
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--user")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--production", action="store_true")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="directory outside the repository for the current consent settings; "
        "required with --write",
    )
    args = parser.parse_args(argv)
    if args.write and args.backup_dir is None:
        parser.error("--write needs --backup-dir")

    plan = json.loads(PLAN.read_text())
    wp = shlex.split(args.wp)
    if args.user:
        wp.append(f"--user={args.user}")
    payload = {"plan": plan, "write": args.write, "production": args.production}
    if not args.write:
        completed = invoke(wp, payload)
        relay(completed)
        return completed.returncode

    exported = invoke(wp, {**payload, "export": True, "write": False})
    if exported.returncode != 0:
        relay(exported)
        print("Consent backup failed; nothing was written.", file=sys.stderr)
        return exported.returncode or 1
    snapshot = marked_json(exported.stdout)
    home = str(snapshot.get("home") or "unknown")
    host = home.split("://", 1)[-1].split("/", 1)[0].replace(":", "_")
    backup = (
        args.backup_dir
        / f"201-consent-backup-{host}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    )
    backup.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n")
    print(f"Backup of the current consent settings: {backup}")

    written = invoke(wp, {**payload, "write": True})
    relay(written)
    if written.returncode != 0:
        print(f"Consent write failed. Backup: {backup}", file=sys.stderr)
        return written.returncode

    readback = invoke(wp, {**payload, "write": False})
    relay(readback)
    if readback.returncode != 0:
        print(f"Consent read-back failed. Backup: {backup}", file=sys.stderr)
        return readback.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
