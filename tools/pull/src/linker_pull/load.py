"""`linker-pull load <name> <snapshot>`: a snapshot into a local WordPress instance.

The instance (the contract with linker-local, docs/specs/5-local-stack.md):

- its directory is $LINKER_LOCAL_HOME/<name> (default ~/de-linker-local/<name>),
  with WordPress installed in wordpress/ and its wp-config.php there;
- its database is linker_<name>, and that wp-config.php must name it, with
  the live table prefix wp_;
- it answers at http://127.0.0.1:<port>; the port is --port, or the `port` of
  table [<name>] in $LINKER_LOCAL_HOME/instances.toml.

Loading replaces every wp_ table with the snapshot's, rewrites the live
address to the local one (as written, JSON-escaped and URL-encoded; WP-CLI
keeps serialized values valid) and empties the object cache, which still
holds the old database's values (the local stack runs Redis). It then installs
the snapshot's plugins, themes and uploads by linker-local's rule (plugin and
theme directories replace the instance's, uploads are merged in; #5's
snapshot.install applies the same rule, and is the one implementation once
both tickets are on main) and leaves active the plugins the instance had plus
the licensed ones. With live_code the live plugins and must-use plugins come
too and the live list of active plugins stays, so the instance is a copy of
the live site. Code Snippets stays off either way: its table is data here.
The instance must keep mail and outgoing requests on this Mac (linker-local's
isolation mu-plugin does).

The users afterwards are the snapshot's: staff accounts keep their logins,
so a login link for one of them (`just login <name> --user <login>`) opens
wp-admin; the result lists those logins.

Finally it compares the instance with the snapshot's manifest (published
products, attachments, the files of the attachments, leftovers of the live
address) and reports what differs.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from linker_pull import live, manifest
from linker_pull.anonymize import TABLE_PREFIX
from linker_pull.snapshot import (
    DATABASE,
    LIVE_MU_PLUGINS,
    LIVE_PLUGINS,
    PLUGINS,
    THEMES,
    UPLOADS,
)

Say = Callable[[str], None]

DATABASE_PREFIX = "linker_"
# Code Snippets' table travels as data; the plugin never runs locally (docs/specs/6-live-pull.md).
NEVER_ACTIVE = ("code-snippets",)
# WP-CLI with the live plugins loaded (`wp rewrite flush`) peaks at 171 MB
# (measured 2026-10-09) and dies at PHP's default 128M. 2048M is the live
# host's limit, which the local stack's php.ini copies (docs/specs/5-local-stack.md).
MEMORY_LIMIT = "2048M"
# Commands that only touch the database need neither plugins nor themes; the
# live plugins would otherwise run on every one of them.
SKIP = ("--skip-plugins", "--skip-themes")


class LoadError(RuntimeError):
    """The snapshot could not be loaded into the instance."""


@dataclass(frozen=True)
class Instance:
    name: str
    directory: Path
    port: int

    @property
    def docroot(self) -> Path:
        return self.directory / "wordpress"

    @property
    def database(self) -> str:
        return DATABASE_PREFIX + self.name

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def wp_content(self) -> Path:
        return self.docroot / "wp-content"


def local_home() -> Path:
    return Path(
        os.environ.get("LINKER_LOCAL_HOME", str(Path.home() / "de-linker-local"))
    )


def instance(name: str, port: int | None, home: Path | None = None) -> Instance:
    home = home or local_home()
    if port is None:
        registry = home / "instances.toml"
        try:
            with registry.open("rb") as handle:
                port = int(tomllib.load(handle)[name]["port"])
        except (FileNotFoundError, KeyError) as missing:
            raise LoadError(
                f"no port for {name}: pass --port, or register it in {registry}"
            ) from missing
    found = Instance(name, home / name, port)
    if not (found.docroot / "wp-config.php").is_file():
        raise LoadError(
            f"{found.docroot} has no wp-config.php: not a WordPress instance"
        )
    return found


class WpCli:
    """WP-CLI on the instance, with the PHP in $PHP (the justfile's PHP 8.3)."""

    def __init__(self, target: Instance) -> None:
        php = shutil.which(os.environ.get("PHP", "php"))
        wp = shutil.which("wp")
        if php is None or wp is None:
            raise LoadError("PHP ($PHP) and WP-CLI (`wp`) are needed")
        self.prefix = [
            php,
            "-d",
            f"memory_limit={MEMORY_LIMIT}",
            wp,
            f"--path={target.docroot}",
        ]

    def run(self, *args: str, stdin: Iterator[bytes] | None = None) -> str:
        """A command; its standard output without the trailing newline.

        `stdin` is streamed in; the output goes to temporary files meanwhile, so
        a command that writes while it reads cannot block on a full pipe.
        """
        environment = {**os.environ, "WP_CLI_DISABLE_AUTO_CHECK_UPDATE": "1"}
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            with subprocess.Popen(
                [*self.prefix, *args],
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env=environment,
            ) as process:
                if stdin is not None:
                    assert process.stdin is not None
                    try:
                        for chunk in stdin:
                            process.stdin.write(chunk)
                    except BrokenPipeError:
                        pass  # the command stopped reading; its status says why
            out.seek(0)
            err.seek(0)
            output = out.read().decode(errors="replace")
            error = err.read().decode(errors="replace")
        if process.returncode != 0:
            raise LoadError(f"wp {' '.join(args)}: {(error or output).strip()}")
        return output.rstrip("\n")

    def query(self, sql: str) -> list[str]:
        """Rows of a read-only query, one tab-separated line each."""
        output = self.run("db", "query", sql, "--skip-column-names", *SKIP)
        return output.splitlines() if output else []


def load(
    target: Instance, snapshot: Path, live_code: bool, say: Say
) -> dict[str, object]:
    data = manifest.read(snapshot)
    wp = WpCli(target)
    database = wp.run("config", "get", "DB_NAME")
    if database != target.database:
        raise LoadError(
            f"{target.docroot}/wp-config.php names database {database}, not {target.database}"
        )
    # The dump's tables are wp_ tables; WordPress must read those.
    prefix = wp.run("config", "get", "table_prefix")
    if prefix != TABLE_PREFIX:
        raise LoadError(
            f"{target.docroot}/wp-config.php has table prefix {prefix}, not {TABLE_PREFIX}"
        )
    plugins_dir = target.wp_content / "plugins"
    linked = sorted(path.name for path in plugins_dir.glob("*") if path.is_symlink())
    if live_code and linked:
        raise LoadError(
            f"{target.name} runs plugins from a checkout ({', '.join(linked)}); "
            "the live code would replace them, so a copy of the live site needs an instance without"
        )
    before = _active_plugins(wp)

    say(f"database: importing {snapshot / DATABASE} into {target.database}")
    wp.run("db", "clean", "--yes", *SKIP)
    wp.run("db", "import", "-", *SKIP, stdin=_dump(snapshot / DATABASE))
    for old, new in replacements(live.URL, target.url):
        count = wp.run(
            "search-replace",
            old,
            new,
            "--all-tables-with-prefix",
            "--format=count",
            *SKIP,
        )
        say(f"search-replace {old} -> {new}: {count} replacements")
    # The tables changed under WordPress: what a persistent object cache holds is stale.
    wp.run("cache", "flush", *SKIP)

    say("files: uploads, plugins, themes")
    _merge_tree(snapshot / UPLOADS, target.wp_content / "uploads")
    _replace_entries(snapshot / PLUGINS, plugins_dir)
    _replace_entries(snapshot / THEMES, target.wp_content / "themes")
    if live_code:
        _replace_entries(snapshot / LIVE_PLUGINS, plugins_dir)
        _replace_entries(snapshot / LIVE_MU_PLUGINS, target.wp_content / "mu-plugins")

    live_active = _active_plugins(wp)
    if live_code:
        wanted = live_active
    else:
        licensed = {
            path.name for path in (snapshot / PLUGINS).iterdir() if path.is_dir()
        }
        wanted = before + [
            entry for entry in live_active if entry.split("/")[0] in licensed
        ]
    active = [
        entry
        for entry in dict.fromkeys(wanted)
        if (plugins_dir / entry).is_file() and entry.split("/")[0] not in NEVER_ACTIVE
    ]
    wp.run(
        "option", "update", "active_plugins", json.dumps(active), "--format=json", *SKIP
    )
    say(f"active plugins: {', '.join(entry.split('/')[0] for entry in active)}")
    wp.run("rewrite", "flush")
    return verify(wp, target, data["database"]["posts"])


def replacements(live_url: str, local_url: str) -> list[tuple[str, str]]:
    """The live address in the forms the live tables hold it, each with its local twin.

    Counted in the 2026-10-09 dump: 36,748 plain, 10,940 JSON-escaped
    (https:\\/\\/de-linker.com), 578 URL-encoded (https%3A%2F%2Fde-linker.com);
    no http:// or www. form.
    """
    return [
        (live_url, local_url),
        (live_url.replace("/", "\\/"), local_url.replace("/", "\\/")),
        (quote(live_url, safe=""), quote(local_url, safe="")),
    ]


def verify(wp: WpCli, target: Instance, posts: dict[str, int]) -> dict[str, object]:
    """What the loaded instance holds, next to what the snapshot says."""
    counts = {
        key: int(
            wp.query(
                f"SELECT COUNT(*) FROM {TABLE_PREFIX}posts"
                f" WHERE post_type = '{key.split('/')[0]}' AND post_status = '{key.split('/')[1]}'"
            )[0]
        )
        for key in ("product/publish", "attachment/inherit")
    }
    uploads = target.wp_content / "uploads"
    attached = wp.query(
        f"SELECT meta_value FROM {TABLE_PREFIX}postmeta WHERE meta_key = '_wp_attached_file'"
    )
    missing = [path for path in attached if not (uploads / path).is_file()]
    leftovers = {
        old: int(
            wp.run(
                "search-replace",
                old,
                "x",
                "--all-tables-with-prefix",
                "--dry-run",
                "--format=count",
                *SKIP,
            )
        )
        for old, _ in replacements(live.URL, target.url)
    }
    staff = wp.run(
        "user",
        "list",
        "--role__in=administrator,shop_manager",
        "--field=user_login",
        *SKIP,
    )
    result: dict[str, object] = {
        "home": wp.run("option", "get", "home", *SKIP),
        "published_products": {
            "snapshot": posts.get("product/publish", 0),
            "instance": counts["product/publish"],
        },
        "attachments": {
            "snapshot": posts.get("attachment/inherit", 0),
            "instance": counts["attachment/inherit"],
        },
        "attachment_files_missing": len(missing),
        "live_address_left": leftovers,
        "staff_logins": staff.splitlines(),
    }
    result["ok"] = (
        result["home"] == target.url
        and counts["product/publish"] == posts.get("product/publish", 0)
        and counts["attachment/inherit"] == posts.get("attachment/inherit", 0)
        and not missing
        and not any(leftovers.values())
    )
    return result


def _active_plugins(wp: WpCli) -> list[str]:
    try:
        value = json.loads(
            wp.run("option", "get", "active_plugins", "--format=json", *SKIP)
        )
    except LoadError:
        return []
    return [str(entry) for entry in value] if isinstance(value, list) else []


def _dump(path: Path) -> Iterator[bytes]:
    """The snapshot's SQL as it is: MySQL 9.6's client imports MariaDB's dump,
    first line ("enable the sandbox mode") included (tests/test_load.py)."""
    with gzip.open(path, "rb") as dump:
        yield from dump


def _replace_entries(source: Path, target: Path) -> None:
    """Every entry of `source` replaces the same-named entry of `target` (a link included)."""
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        destination = target / entry.name
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        elif destination.exists():
            shutil.rmtree(destination)
        if entry.is_dir():
            _merge_tree(entry, destination)
        else:
            shutil.copy2(entry, destination)


def _merge_tree(source: Path, target: Path) -> None:
    """Copy a directory's contents into `target`, keeping what only `target` has.

    On macOS the copies are APFS clones, which take no space until changed.
    """
    if sys.platform == "darwin":
        target.mkdir(parents=True, exist_ok=True)
        # A source ending in "/" copies its contents into the existing target (cp(1)).
        result = subprocess.run(
            ["cp", "-cR", f"{source}/", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
    shutil.copytree(source, target, symlinks=True, dirs_exist_ok=True)
