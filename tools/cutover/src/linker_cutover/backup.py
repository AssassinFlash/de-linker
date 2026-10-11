"""Step 1 of the cutover, and the other half of step 8 (docs/specs/17-cutover.md).

`create` writes a complete, restorable copy of the site to
`~/de-linker-data/cutover-<date>/` (outside the repository, as every snapshot
is): the database, `wp-content/uploads`, `wp-content/plugins`, `.htaccess`, an
options export, and a sha256 manifest of everything it wrote.

`restore` puts that copy back; the rollback runs it. The database comes back
whole, so the plugin activation state comes back with it; the file trees come
back over the live ones, so the directories agree with the database again.

The dump is mysqldump, not `wp db export`. WP-CLI's export calls `exec()`
before it reaches mysqldump (wp-cli/db-command DB_Command.php:655) and the
production host disables `exec` (disable_functions, read 2026-10-09), so the
command spec 17 §1 names cannot run there. tools/pull reached the same
conclusion for the same reason (docs/specs/6-live-pull.md, change record);
the dump below is that script with this target's WP-CLI prefix substituted.
The password stays on the machine that runs the dump, in mysqldump's
environment, and never reaches this Mac.

Both scripts read and write the dump on the process's standard streams, so one
implementation covers a local instance (where the file happens to be local) and
the host (where it is piped through ssh): nothing in the script names a path
that only one of the two machines has.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

from linker_cutover.target import (
    HTACCESS,
    PLUGINS,
    UPLOADS,
    CutoverError,
    Target,
    wp_prefix_for,
)

MANIFEST = "manifest.json"
DUMP = "db.sql.gz"
OPTIONS = "options.json"


@dataclass(frozen=True)
class Backup:
    """A written backup, and what it holds."""

    directory: Path
    files: int
    dump_sha256: str


# The WordPress convention for DB_HOST is not mysqldump's: WP-CLI accepts
# `host`, `host:port` and `host:/path/to/socket`, and a local instance has the
# third form (docs/local-stack.md: `localhost:/tmp/mysql.sock`). mysqldump
# reads that whole string as a host name and fails with "Unknown MySQL server
# host". One function turns the WordPress form into the client's, so the dump
# is one script for both targets.
_DB_TARGET = """db_target() {
  local raw
  raw="$($wp config get DB_HOST)"
  DB_ARGS=()
  case "$raw" in
    *:/*) DB_ARGS+=(--host="${raw%%:*}" --socket="${raw#*:}") ;;
    *:*)  DB_ARGS+=(--host="${raw%%:*}" --port="${raw##*:}") ;;
    *)    DB_ARGS+=(--host="$raw") ;;
  esac
  DB_ARGS+=(--user="$($wp config get DB_USER)")
}"""

# Two flags keep the dump inside what the site's own database user can do.
# `--no-tablespaces` is for the dump end: reading the tablespaces needs the
# PROCESS privilege the site's user does not have (and a logical restore does
# not use them). The rest is for the import end, which is where it matters: a
# statement the import cannot run makes the backup unrestorable, and the
# rollback is the one thing that has to work. MySQL's mysqldump writes the
# server's GTID position (SET @@GLOBAL.GTID_PURGED) when the server has GTIDs;
# MariaDB's does not, and MariaDB's mysqldump does not know
# `--set-gtid-purged` at all. So the script asks mysqldump itself what it takes
# -- its own help output is the authority -- and passes the flag where it exists.
_DUMP_FLAGS = """dump_extra() {
  local help
  DUMP_EXTRA=()
  help="$(mysqldump --help 2>/dev/null || true)"
  case "$help" in
    *--set-gtid-purged*) DUMP_EXTRA=(--set-gtid-purged=OFF) ;;
  esac
}
"""


def _expansion(name: str) -> str:
    """A bash array expansion that is empty-array safe under `set -u`.

    bash 3.2 — macOS's /bin/bash — treats `"${a[@]}"` of an empty array as an
    unbound variable when `set -u` is on, and these scripts run on both
    machines. The `+` form expands to nothing instead, which is what an empty
    array means.
    """
    return "${" + name + '[@]+"${' + name + '[@]}"}'


def dump_script(target: Target) -> str:
    """The shell script that writes the database, gzip-compressed, to standard output."""
    wp = wp_prefix_for(target)
    return f"""set -euo pipefail
cd {shlex.quote(target.root)}
wp="{wp}"
{_DB_TARGET}
{_DUMP_FLAGS}
db_target
dump_extra
MYSQL_PWD="$($wp config get DB_PASSWORD)" mysqldump \\
  --single-transaction --quick --skip-dump-date --order-by-primary \\
  --default-character-set=utf8mb4 --no-tablespaces \\
  {_expansion("DUMP_EXTRA")} \\
  {_expansion("DB_ARGS")} \\
  "$($wp config get DB_NAME)" | gzip
"""


def restore_script(target: Target) -> str:
    """The shell script that replaces the database with a dump read from standard input."""
    wp = wp_prefix_for(target)
    return f"""set -euo pipefail
cd {shlex.quote(target.root)}
wp="{wp}"
{_DB_TARGET}
db_target
gunzip -c | MYSQL_PWD="$($wp config get DB_PASSWORD)" mysql \\
  --default-character-set=utf8mb4 \\
  {_expansion("DB_ARGS")} \\
  "$($wp config get DB_NAME)"
"""


def sha256(path: Path) -> str:
    """The SHA-256 of a file, read in chunks so a database dump fits in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_manifest(directory: Path) -> dict[str, dict[str, object]]:
    """Every file under `directory`, with its sha256 and size, keyed by relative path."""
    entries: dict[str, dict[str, object]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not path.is_symlink():
            entries[str(path.relative_to(directory))] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    return entries


def destination(home: Path, *, now: datetime | None = None) -> Path:
    """`~/de-linker-data/cutover-<YYYYMMDD-HHMM>/`, the directory spec 17 §1 names."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M")
    return home / f"cutover-{stamp}"


def create(target: Target, home: Path, *, now: datetime | None = None) -> Backup:
    """Take the backup: database, uploads, plugins, .htaccess, options, manifest."""
    directory = destination(home, now=now)
    # An empty directory is a run that died before it wrote anything (the
    # window would otherwise be blocked for the rest of that minute); anything
    # in it is somebody's backup, and a second one must not merge into it.
    if directory.exists() and any(directory.iterdir()):
        # A complete backup is somebody's rollback: never write into it. A
        # partial one is a run that died, and the operator has to decide
        # whether the dump in it is the one they want — saying which it is is
        # the whole message.
        state = (
            "a complete backup"
            if (directory / MANIFEST).is_file()
            else "a partial backup"
        )
        raise CutoverError(
            f"{directory} already holds {state}; move it aside to take a new one"
        )
    directory.mkdir(parents=True, exist_ok=True)
    print(f"backup: {directory}")

    print("backup: database")
    dump = directory / DUMP
    with dump.open("wb") as handle:
        _stream(target, dump_script(target), stdout=handle)
    if not readable_gzip(dump):
        raise CutoverError(f"{dump} is not a readable gzip — the backup is not usable")
    dump_sha = sha256(dump)
    print(f"backup: database {dump.stat().st_size} bytes, sha256 {dump_sha[:16]}…")

    for relative in (UPLOADS, PLUGINS):
        print(f"backup: {relative}")
        target.copy_out(relative, directory / relative)

    htaccess = directory / HTACCESS
    try:
        target.copy_out(HTACCESS, htaccess)
    except CutoverError as error:
        # A site without .htaccess is legal — the rewrite rules then live in the
        # server config. The absence is recorded, not fatal.
        print(f"backup: no {HTACCESS} ({error})")
        htaccess.write_text("", encoding="utf-8")

    print(f"backup: {OPTIONS}")
    (directory / OPTIONS).write_text(
        target.wp("option", "list", "--format=json") + "\n", encoding="utf-8"
    )

    manifest = directory_manifest(directory)
    (directory / MANIFEST).write_text(
        json.dumps(
            {
                "target": target.label,
                "taken_at": datetime.now(UTC).isoformat(),
                "files": manifest,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"backup: {len(manifest)} files, manifest written")
    return Backup(directory=directory, files=len(manifest), dump_sha256=dump_sha)


def restore(target: Target, directory: Path) -> None:
    """Put a backup back: the database, the file trees, then the caches."""
    directory = Path(directory)
    dump = directory / DUMP
    if not dump.is_file():
        raise CutoverError(f"{dump} is missing — {directory} is not a usable backup")
    expected = manifest_of(directory).get(DUMP)
    if expected is not None and sha256(dump) != expected["sha256"]:
        raise CutoverError(f"{dump} was modified since the backup was taken")

    print("rollback: database")
    with dump.open("rb") as handle:
        _stream(target, restore_script(target), stdin=handle)
    print(f"rollback: {PLUGINS}")
    target.copy_in(directory / PLUGINS, PLUGINS)
    print(f"rollback: {UPLOADS}")
    target.copy_in(directory / UPLOADS, UPLOADS)
    htaccess = directory / HTACCESS
    if htaccess.is_file() and htaccess.stat().st_size > 0:
        print(f"rollback: {HTACCESS}")
        # `.htaccess` is one file, not a tree: rsync it through the same seam a
        # directory copy uses, so both targets behave identically.
        target.rsync(str(htaccess), target.path_of(HTACCESS))
    print("rollback: caches")
    target.wp("cache", "flush")
    target.wp("rewrite", "flush")


def manifest_of(directory: Path) -> dict[str, dict[str, object]]:
    """The `files` section of a backup's manifest, or an empty map without one."""
    path = Path(directory) / MANIFEST
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files", {})
    if not isinstance(files, dict):
        return {}
    return {str(key): dict(value) for key, value in files.items()}


def readable_gzip(path: Path) -> bool:
    """Whether the file is a gzip stream that decompresses to its end.

    Read to the end, not just the header: gzip's CRC and length live in the
    last eight bytes, so a dump truncated by a dropped connection decompresses
    happily for as far as it goes and only fails here. A backup that cannot be
    imported is not a backup, and this is the cheapest place to find out.
    """
    try:
        with gzip.open(path, "rb") as handle:
            for _ in iter(lambda: handle.read(1024 * 1024), b""):
                pass
    except (OSError, EOFError):
        return False
    return True


def _stream(
    target: Target,
    script: str,
    *,
    stdin: IO[bytes] | None = None,
    stdout: IO[bytes] | None = None,
) -> None:
    """Run a script on the target with the given standard streams."""
    command = (
        ["bash", "-c", script]
        if target.shell_prefix is None
        else [*target.shell_prefix, script]
    )
    with tempfile.TemporaryFile() as error:
        completed = subprocess.run(
            command, stdin=stdin, stdout=stdout, stderr=error, check=False
        )
        error.seek(0)
        message = error.read().decode(errors="replace").strip()
    if completed.returncode != 0:
        raise CutoverError(f"{script.splitlines()[0]}: {message}")
