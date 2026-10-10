"""The production host, read-only. Every command this tool runs there is built in this module.

`ssh hostinger-de-linker` reaches the host (~/.ssh/config). The host is only
ever a source: WP-CLI runs the read-only commands in READ_ONLY, the database is
read by mysqldump, and rsync copies from the host, never to it.

The host's PHP has exec() disabled (disable_functions, read 2026-10-09), and
`wp db export` calls exec() before it starts mysqldump
(wp-cli/db-command DB_Command.php:655), so it fails there with a fatal error.
dump_script() runs the mysqldump that WP-CLI would run, with the connection
settings `wp config get` reads from wp-config.php; the password stays on the
host, in mysqldump's environment.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
import urllib.request
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import IO
from xml.etree import ElementTree

from linker_pull.anonymize import Account

HOST = "hostinger-de-linker"
WP_ROOT = "/home/u388076051/domains/de-linker.com/public_html"
WP_CLI = "/usr/local/bin/wp"
URL = "https://de-linker.com"
# The namespace of sitemap elements (sitemaps.org protocol).
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Where rsync copies from: the WordPress root on the host.
ORIGIN = f"{HOST}:{WP_ROOT}"
# The licensed plugins every local instance installs (docs/specs/5-local-stack.md).
LICENSED_PLUGINS = ("livecanvas", "wp-seopress", "wp-seopress-pro", "windpress")
# The hosting platform's own must-use plugins (preview domain, forced
# auto-updates); they are not part of the site.
PLATFORM_MU_PLUGINS = ("hostinger-auto-updates.php", "hostinger-preview-domain.php")

READ_ONLY = frozenset(
    {
        ("core", "version"),
        ("config", "get"),
        ("plugin", "list"),
        ("theme", "list"),
        ("user", "list"),
    }
)
# Every read-only command runs with these global WP-CLI flags
# (Runner.php reads both): none of the commands needs plugin or theme code,
# so the live site's old plugins never initialize under our read.
SKIP_LOADING = ("--skip-plugins", "--skip-themes")
# `plugin list` and `theme list` without --skip-update-check first delete the
# update_plugins/update_themes site transient and ask WordPress to rebuild it
# (extension-command CommandWithUpgrade::_list(), wp-cli 2.12.0 phar) — a
# write. The flag is documented on exactly these two commands
# (Plugin_Command.php:1431, Theme_Command.php:880), so it goes to no other.
UPDATE_CHECKING = frozenset({("plugin", "list"), ("theme", "list")})


def dump_script(root: str = WP_ROOT, wp_cli: str = WP_CLI) -> str:
    """The shell script that dumps the database on the host, gzip-compressed.

    --single-transaction reads one consistent InnoDB snapshot without locking
    the live tables (every live table is InnoDB, information_schema
    2026-10-09); --skip-dump-date and --order-by-primary make two dumps of the
    same data equal. The `wp config get` calls run with the same SKIP_LOADING
    flags as every read-only command (wp() is not available inside the script;
    it only reads wp-config.php, but the old plugins shall not initialize
    under a read either way). The password only reaches mysqldump's
    environment.
    """
    flags = " --skip-plugins --skip-themes"
    return f"""set -euo pipefail
cd {shlex.quote(root)}
wp={shlex.quote(wp_cli)}
MYSQL_PWD="$($wp{flags} config get DB_PASSWORD)" mysqldump \\
  --single-transaction --quick --skip-dump-date --order-by-primary \\
  --default-character-set=utf8mb4 \\
  --host="$($wp{flags} config get DB_HOST)" \\
  --user="$($wp{flags} config get DB_USER)" \\
  "$($wp{flags} config get DB_NAME)" | gzip
"""


class LiveError(RuntimeError):
    """A command on the host failed or was not allowed."""


def ssh_command(remote: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", HOST, remote]


def wp_command(args: Sequence[str]) -> str:
    """The shell command `wp(*args)` runs on the host; the only place it is built."""
    if tuple(args[:2]) not in READ_ONLY:
        raise LiveError(f"wp {' '.join(args)} is not one of the read-only commands")
    flags = (
        *SKIP_LOADING,
        *(("--skip-update-check",) if tuple(args[:2]) in UPDATE_CHECKING else ()),
    )
    return f"cd {shlex.quote(WP_ROOT)} && {WP_CLI} " + " ".join(
        shlex.quote(arg) for arg in (*flags, *args)
    )


def wp(*args: str) -> str:
    """A read-only WP-CLI command on the host; its standard output."""
    remote = wp_command(args)
    result = subprocess.run(
        ssh_command(remote), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise LiveError(f"wp {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def wp_json(*args: str) -> object:
    return json.loads(wp(*args, "--format=json"))


def accounts() -> list[Account]:
    """Every user with the roles that decide who is staff."""
    users = wp_json("user", "list", "--fields=ID,user_login,user_email,roles")
    assert isinstance(users, list)
    return [
        Account(
            int(user["ID"]),
            str(user["user_login"]),
            str(user["user_email"]),
            frozenset(role for role in str(user["roles"]).split(",") if role),
        )
        for user in users
    ]


def dump(stderr: IO[bytes]) -> subprocess.Popen[bytes]:
    """mysqldump of the live database, gzip-compressed, on the process's standard output."""
    return subprocess.Popen(
        ssh_command("bash -c " + shlex.quote(dump_script())),
        stdout=subprocess.PIPE,
        stderr=stderr,
    )


def rsync_command(
    source: str,
    target: Path,
    *,
    filters: Sequence[str] = (),
    link_dest: Sequence[Path] = (),
) -> list[str]:
    """rsync from ORIGIN/<source> into `target`: the host is the source, never the target."""
    if source.startswith("/") or ".." in source.split("/"):
        raise LiveError(f"{source} is not a path inside the WordPress root")
    command = ["rsync", "-az", "--delete", "--out-format=%n"]
    command += list(filters)
    # An unchanged file becomes a hard link into the first of these that has it
    # (rsync takes up to 20 --link-dest directories).
    command += [f"--link-dest={directory}" for directory in link_dest[:20]]
    if ":" in ORIGIN:
        command += ["-e", "ssh -o BatchMode=yes"]
    command += [f"{ORIGIN}/{source}", str(target)]
    return command


def rsync(
    source: str,
    target: Path,
    *,
    filters: Sequence[str] = (),
    link_dest: Sequence[Path] = (),
) -> Iterator[str]:
    """Run rsync_command(); yields the name of every file it transfers."""
    target.mkdir(parents=True, exist_ok=True)
    # stderr goes to a file: a pipe nobody reads while stdout streams can fill and stall rsync.
    with (
        tempfile.TemporaryFile() as error,
        subprocess.Popen(
            rsync_command(source, target, filters=filters, link_dest=link_dest),
            stdout=subprocess.PIPE,
            stderr=error,
            text=True,
        ) as process,
    ):
        assert process.stdout is not None
        for line in process.stdout:
            yield line.rstrip("\n")
        process.wait()
        error.seek(0)
        message = error.read().decode(errors="replace").strip()
    if process.returncode != 0:
        raise LiveError(f"rsync {source}: {message}")


def sitemaps() -> dict[str, bytes]:
    """The XML sitemaps robots.txt declares and those their indexes list: file name -> XML."""
    robots = _get(URL + "/robots.txt").decode("utf-8", "replace")
    pending = [
        line.split(":", 1)[1].strip()
        for line in robots.splitlines()
        if line.lower().startswith("sitemap:")
    ]
    found: dict[str, bytes] = {}
    while pending:
        url = pending.pop(0)
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if not url.startswith(URL + "/") or name in found:
            continue
        xml = _get(url)
        found[name] = xml
        root = ElementTree.fromstring(xml)
        if root.tag.endswith("sitemapindex"):
            pending += [
                element.text.strip()
                for element in root.iter()
                if element.tag.endswith("loc") and element.text
            ]
    return found


def sitemap_urls(xml: bytes) -> list[str]:
    """The page addresses of a sitemap: each <url>'s <loc>, not the <image:loc> inside it."""
    root = ElementTree.fromstring(xml)
    return [
        location.text.strip()
        for url in root
        if url.tag == SITEMAP_NS + "url"
        for location in url
        if location.tag == SITEMAP_NS + "loc" and location.text
    ]


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "linker-pull"})
    # A bound on a hung connection, not on a slow answer: robots.txt and the
    # sitemaps (76 KB at most) came within 2 seconds on 2026-10-09.
    with urllib.request.urlopen(request, timeout=60) as response:
        body: bytes = response.read()
        return body
