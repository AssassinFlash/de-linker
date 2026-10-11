#!/usr/bin/env python3
"""Restore the featured-image binding (`_thumbnail_id`) the snapshot carries.

The media library itself is complete on the instance (attachments, files,
`_product_image_gallery`), but the `_thumbnail_id` rows that bind a post to its
featured image are absent: measured on 2026-10-11, the instance table has 0
rows where the live snapshot has 273, so every product page and catalogue card
renders without its featured image. The values are not derived anywhere - they
are data the live site holds, and the snapshot is the authoritative copy of it.
This reads that copy and writes back the bindings the instance is missing.

    python3 tools/migrate/13-media-meta.py --snapshot ~/de-linker-data/<date> plan
    python3 tools/migrate/13-media-meta.py --snapshot ~/de-linker-data/<date> apply --write

Only rows the snapshot has and the instance lacks are written; a binding that
differs on purpose (a post re-imaged in the instance) is left alone and
reported. The snapshot is read by importing its dump into a scratch database
(`linker_snapshot_scratch`), which is reused when its checksum still matches.
"""

from __future__ import annotations

import argparse
import hashlib
import shlex
import subprocess
import sys
from pathlib import Path

SCRATCH_DB = "linker_snapshot_scratch"
META_KEY = "_thumbnail_id"


def run(command: list[str], *, stdin: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, input=stdin, check=check, capture_output=True)


def mysql(sql: str, database: str | None = None, *, check: bool = True) -> list[list[str]]:
    command = ["mysql", "-u", "root", "--batch", "--skip-column-names"]
    if database:
        command.append(database)
    command += ["-e", sql]
    result = run(command, check=check)
    return [line.split("\t") for line in result.stdout.decode().splitlines() if line]


def snapshot_rows(snapshot: Path) -> dict[int, int]:
    """post_id -> _thumbnail_id from the snapshot, importing it once."""
    dump = snapshot / "db.sql.gz"
    if not dump.is_file():
        sys.exit(f"no dump at {dump}")
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()[:16]
    marker = mysql(f"SELECT option_value FROM {SCRATCH_DB}.wp_options WHERE option_name='linker_snapshot_marker'", check=False)
    current = marker[0][0] if marker else ""
    if current != digest:
        print(f"importing {dump} into {SCRATCH_DB} (marker {digest})", flush=True)
        mysql(f"DROP DATABASE IF EXISTS {SCRATCH_DB}; CREATE DATABASE {SCRATCH_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci")
        result = subprocess.run(
            f"gunzip -c {shlex.quote(str(dump))} | mysql -u root {SCRATCH_DB}",
            shell=True,
            capture_output=True,
        )
        if result.returncode != 0:
            sys.exit("import failed: " + result.stderr.decode(errors="replace")[-400:])
        mysql(
            f"INSERT INTO {SCRATCH_DB}.wp_options (option_name, option_value, autoload) "
            f"VALUES ('linker_snapshot_marker', '{digest}', 'no') ON DUPLICATE KEY UPDATE option_value='{digest}'"
        )
    rows = mysql(f"SELECT post_id, meta_value FROM {SCRATCH_DB}.wp_postmeta WHERE meta_key='{META_KEY}' AND meta_value REGEXP '^[0-9]+$'")
    return {int(post_id): int(value) for post_id, value in rows}


def instance_rows(wp: str) -> dict[int, int]:
    output = run([*wp.split(), "db", "query", f"SELECT post_id, meta_value FROM wp_postmeta WHERE meta_key='{META_KEY}'"]).stdout.decode()
    rows = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].strip().isdigit():
            rows[int(parts[0])] = int(parts[1])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--wp", required=True, help="the instance's wp.sh (prints the WP-CLI invocation)")
    parser.add_argument("--write", action="store_true", help="apply needs this to write")
    args = parser.parse_args()

    snapshot = snapshot_rows(args.snapshot)
    instance = instance_rows(args.wp)
    missing = {post: image for post, image in snapshot.items() if post not in instance}
    differing = {post: (instance[post], image) for post, image in snapshot.items() if post in instance and instance[post] != image}
    print(f"snapshot bindings: {len(snapshot)}, instance bindings: {len(instance)}, missing: {len(missing)}, differing: {len(differing)}")
    for post, (here, there) in list(differing.items())[:10]:
        print(f"  differing: post {post} instance {here} snapshot {there}")
    if args.command == "plan" or not args.write:
        if args.command == "apply":
            print("dry run: add --write to write")
        return
    written = 0
    for post, image in sorted(missing.items()):
        result = run([*args.wp.split(), "post", "meta", "update", str(post), META_KEY, str(image)], check=False)
        if result.returncode != 0:
            print(f"  post {post}: {result.stderr.decode().strip()[-120:]}")
        else:
            written += 1
    print(f"wrote {written} bindings")


if __name__ == "__main__":
    main()
