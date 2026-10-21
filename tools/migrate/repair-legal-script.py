#!/usr/bin/env python3
"""Restore only a demonstrably unslashed legal-page script, preserving current copy.

The reference revisions are supplied explicitly. A write needs a local backup;
production additionally needs the completed full site backup's manifest. Payloads
travel as base64 over STDIN, with only a small loader in SSH's command. WordPress receives wp_slash()
and both pages are read back byte for byte, with rollback on a partial failure.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCRIPT = re.compile(
    r'<script\b[^>]*\bid=["\']tv-legal-js["\'][^>]*>.*?</script>', re.S | re.I
)
MARKER = "@@legal-script@@"
PHP = Path(__file__).with_suffix(".php")


def restore_script(current: str, reference: str) -> str:
    """Accept exactly one intact script or exactly its one-unslash corruption."""
    saved, normal = list(SCRIPT.finditer(current)), list(SCRIPT.finditer(reference))
    if len(saved) != 1 or len(normal) != 1:
        raise ValueError("Expected one tv-legal-js block in each document")
    old, good = saved[0], normal[0].group()
    if old.group() == good:
        return current
    if "\\" not in good or old.group() != good.replace("\\", ""):
        raise ValueError(
            "Script differs beyond missing backslashes; refusing to overwrite"
        )
    return current[: old.start()] + good + current[old.end() :]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_full_backup(directory: Path) -> None:
    """Reject an incomplete manifest, missing file, or truncated database dump."""
    manifest = json.loads((directory / "manifest.json").read_text())
    files = manifest.get("files", {})
    required = ("wp-content/uploads/", "wp-content/plugins/", "wp-content/mu-plugins/")
    if manifest.get("target") != "hostinger-de-linker" or any(
        not any(name.startswith(prefix) for name in files) for prefix in required
    ):
        raise ValueError("Backup is not a complete production snapshot")
    for name, entry in files.items():
        path = (directory / name).resolve()
        if (
            not path.is_relative_to(directory.resolve())
            or not path.is_file()
            or path.stat().st_size != entry["bytes"]
        ):
            raise ValueError("Backup file is missing or has changed size")
    dump = directory / "db.sql.gz"
    with dump.open("rb") as handle:
        if (
            hashlib.file_digest(handle, "sha256").hexdigest()
            != files["db.sql.gz"]["sha256"]
        ):
            raise ValueError("Backup database hash differs")
    with gzip.open(dump, "rb") as handle:
        for _ in iter(lambda: handle.read(1024 * 1024), b""):
            pass


def invoke(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    source = (
        PHP.read_text()
        .removeprefix("<?php")
        .replace("__LEGAL_SCRIPT_PAYLOAD__", encoded)
    )
    command = shlex.split(prefix)
    # Two full documents exceed Linux's single-argument limit. Stream the
    # source to WP-CLI; neither page content nor credentials enter argv.
    # WP-CLI eval-file silently reads no code from a large /dev/stdin pipe
    # on this stack; a tiny eval loader explicitly drains STDIN instead.
    tail = ["eval", "eval( stream_get_contents( STDIN ) );"]
    # ssh re-parses its trailing arguments in the remote shell.
    command = (
        [*command, shlex.join(tail)]
        if Path(command[0]).name == "ssh"
        else [*command, *tail]
    )
    result = subprocess.run(
        command, input=source, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"WordPress failed ({result.returncode}): {result.stderr[:800]}"
        )
    for line in result.stdout.splitlines():
        if line.startswith(MARKER):
            decoded = json.loads(line[len(MARKER) :])
            if not isinstance(decoded, dict):
                raise RuntimeError("WordPress readback must be a JSON object")
            return decoded
    raise RuntimeError("WordPress returned no structured readback")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument(
        "--pair", action="append", required=True, help="page ID:normal revision ID"
    )
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument(
        "--full-backup", type=Path, help="completed full site backup directory"
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    pairs = [tuple(map(int, pair.split(":"))) for pair in args.pair]
    if any(len(pair) != 2 for pair in pairs):
        parser.error("Each --pair must be page:revision")
    ids = list(dict.fromkeys(item for pair in pairs for item in pair))
    snapshot = invoke(args.wp, {"operation": "read", "ids": ids})
    changes = []
    for page, revision in pairs:
        current, reference = (
            snapshot["rows"][str(page)],
            snapshot["rows"][str(revision)],
        )
        if reference["parent"] != page or reference["type"] != "revision":
            raise ValueError("Reference is not this page's revision")
        fixed = restore_script(current["content"], reference["content"])
        changes.append({"id": page, "before": current["content"], "after": fixed})
    if args.write:
        if args.backup_dir is None:
            parser.error("--write requires --backup-dir")
        if urlsplit(snapshot["home"]).hostname in {
            "de-linker.com",
            "www.de-linker.com",
        }:
            if (
                args.full_backup is None
                or not (args.full_backup / "manifest.json").is_file()
            ):
                parser.error("Production requires a completed --full-backup")
            verify_full_backup(args.full_backup)
        args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = args.backup_dir / f"legal-script-before-{stamp}.json"
        with backup.open("x") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        invoke(args.wp, {"operation": "save", "changes": changes})
        readback = invoke(
            args.wp, {"operation": "read", "ids": [pair[0] for pair in pairs]}
        )
        if any(
            readback["rows"][str(c["id"])]["content"] != c["after"] for c in changes
        ):
            raise RuntimeError(f"Independent readback failed; backup: {backup}")
    print(
        json.dumps(
            {
                "write": args.write,
                "pages": [
                    {
                        "id": c["id"],
                        "changed": c["before"] != c["after"],
                        "before_sha256": digest(c["before"]),
                        "after_sha256": digest(c["after"]),
                        "backslashes_before": c["before"].count("\\"),
                        "backslashes_after": c["after"].count("\\"),
                    }
                    for c in changes
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
