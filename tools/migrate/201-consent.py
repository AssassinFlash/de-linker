#!/usr/bin/env python3
"""Replay consent settings through native CookieYes plugins; never connect a GA property."""

from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--user")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    plan = json.loads((directory / "201-consent.json").read_text())
    payload = base64.b64encode(
        json.dumps(
            {"plan": plan, "write": args.write, "production": args.production}
        ).encode()
    ).decode()
    # eval receives source as one argv item. /dev/stdin is not portable through
    # WP-CLI eval-file; no PHP file is copied into the production document root.
    command = shlex.split(args.wp)
    if args.user:
        command.append(f"--user={args.user}")
    command += [
        "eval",
        (directory / "201-consent.php")
        .read_text()
        .removeprefix("<?php")
        .replace("__LINKER_CONSENT_PAYLOAD__", payload),
    ]
    completed = subprocess.run(
        command,
        text=True,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
