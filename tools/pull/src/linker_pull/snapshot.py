"""`linker-pull snapshot`: the live site, read-only, into ~/de-linker-data/<YYYYMMDD-HHMM>/.

A snapshot holds (README of the layout, also in docs/specs/6-live-pull.md):

    db.sql.gz          the database, pseudonymized while it streams in (never stored as dumped)
    uploads/           wp-content/uploads: the media library's year folders, the
                       WooCommerce placeholder image and WindPress's compiled CSS
    plugins/<slug>/    the licensed plugins every local instance installs
    themes/<slug>/     the active theme and its parent
    live/plugins/      every other entry of wp-content/plugins (the live custom
                       code, free plugins, leftovers), for a local copy of the live site
    live/mu-plugins/   the live must-use plugins but the hosting platform's
    site/              options.json (wp_options after the anonymizer),
                       plugins.json, themes.json, sitemaps/ (the live XML sitemaps)
    manifest.json      every file with sha256 and size; every table with rows and sha256

It is built in .<name>.partial/ and renamed when complete, so a directory with
a snapshot name is always a whole snapshot. Unchanged files are hard links into
the previous snapshot (rsync --link-dest), and into what an interrupted run
left in its .partial directory, which the next complete run removes. One
snapshot is taken at a time (a lock in the data root): the worktrees of every
ticket share ~/de-linker-data.
"""

from __future__ import annotations

import fcntl
import gzip
import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from linker_pull import live, manifest, scan, sqldump
from linker_pull.anonymize import TABLE_PREFIX, Account, Anonymizer
from linker_pull.sqldump import Insert, Line

Say = Callable[[str], None]

NAME_FORMAT = "%Y%m%d-%H%M"
NAME = re.compile(r"\d{8}-\d{4}")
DATABASE = "db.sql.gz"
UPLOADS = "uploads"
PLUGINS = "plugins"
THEMES = "themes"
LIVE_PLUGINS = "live/plugins"
LIVE_MU_PLUGINS = "live/mu-plugins"
SITE = "site"
LOCK = ".snapshot.lock"
# What of wp-content/uploads is copied: the media library (year folders, as
# uploads_use_yearmonth_folders files them), WooCommerce's placeholder image
# (an attachment at the top level) and WindPress's CSS, which the pages load.
# Everything else stays on the host: on 2026-10-09 that was wc-logs/ (mail and
# error logs), tv-b2b-private/ (a customer's business document) and
# woocommerce_uploads/ (empty, access-protected).
UPLOAD_FILTERS = (
    "--include=/[0-9][0-9][0-9][0-9]/",
    "--include=/[0-9][0-9][0-9][0-9]/**",
    "--include=/woocommerce-placeholder*",
    "--include=/windpress/",
    "--include=/windpress/**",
    "--exclude=*",
)
# A long step says how far it got at least this often: the working rule for
# long commands is visible progress at least every 30 seconds.
PROGRESS_SECONDS = 30


class SnapshotError(RuntimeError):
    """The snapshot could not be taken; nothing was kept under its name."""


def data_root() -> Path:
    """Where snapshots live: $LINKER_PULL_DATA, else ~/de-linker-data (outside the repository)."""
    return Path(os.environ.get("LINKER_PULL_DATA", str(Path.home() / "de-linker-data")))


def latest(root: Path) -> Path | None:
    names = sorted(
        path.name
        for path in root.glob("*")
        if path.is_dir() and NAME.fullmatch(path.name)
    )
    return root / names[-1] if names else None


def take(root: Path, say: Say) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    with _alone(root):
        return _take(root, say)


@contextmanager
def _alone(root: Path) -> Iterator[None]:
    """Hold the data root's lock, or fail at once if another snapshot holds it."""
    with (root / LOCK).open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SnapshotError(f"another snapshot is being taken in {root}") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _take(root: Path, say: Say) -> Path:
    name = datetime.now().strftime(NAME_FORMAT)
    target = root / name
    if target.exists():
        raise SnapshotError(f"{target} exists; snapshots are a minute apart at least")
    staging = root / f".{name}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    # Files already copied: the last snapshot, then what interrupted runs left.
    earlier = [path for path in (latest(root),) if path is not None]
    earlier += sorted(root.glob(".*.partial"), reverse=True)
    site = staging / SITE
    site.mkdir(parents=True)
    say(f"snapshot {name} from {live.HOST} into {staging}")
    if earlier:
        say(f"unchanged files link to {', '.join(path.name for path in earlier)}")

    core = live.wp("core", "version").strip()
    plugins = live.wp_json("plugin", "list", "--fields=name,status,version,file")
    themes = live.wp_json("theme", "list", "--fields=name,status,version")
    assert isinstance(plugins, list) and isinstance(themes, list)
    accounts = live.accounts()

    database = _database(staging, accounts, say)
    _files(staging, earlier, themes, say)
    _write_json(site / "plugins.json", plugins)
    _write_json(site / "themes.json", themes)
    (site / "sitemaps").mkdir()
    for sitemap, xml in live.sitemaps().items():
        (site / "sitemaps" / sitemap).write_bytes(xml)

    say("hashing files for the manifest")
    manifest.write(
        staging,
        {
            "format": manifest.FORMAT,
            "name": name,
            "created": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": {"host": live.HOST, "url": live.URL, "wordpress": core},
            "database": database,
            "files": manifest.file_entries(staging),
        },
    )
    staging.rename(target)
    for leftover in earlier:
        if leftover.name.endswith(".partial"):
            shutil.rmtree(leftover)
    say(f"snapshot {target}")
    return target


def _database(staging: Path, accounts: list[Account], say: Say) -> dict[str, Any]:
    """Stream the dump through the anonymizer into db.sql.gz; check what was written."""
    say("database: mysqldump on the host, pseudonymized on arrival")
    anonymizer = Anonymizer(accounts)
    stats = manifest.DatabaseStats()
    options: list[dict[str, str | None]] = []
    path = staging / DATABASE
    broken: Exception | None = None
    with tempfile.TemporaryFile() as error:
        # Leaving the `with` closes the pipe and waits for ssh.
        with live.dump(error) as process:
            assert process.stdout is not None
            try:
                items = stats.observe(
                    _options(
                        anonymizer.process(sqldump.read(_lines(process.stdout))),
                        options,
                    )
                )
                _write_gzip(
                    path, sqldump.write(_progress(items, say, "database", _insert_rows))
                )
            except (sqldump.DumpError, EOFError, OSError) as failure:
                # A dump cut short reads as broken SQL or gzip; the host says why.
                broken = failure
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        error.seek(0)
        message = error.read().decode(errors="replace").strip()
    if broken is not None or process.returncode != 0:
        path.unlink(missing_ok=True)
        raise SnapshotError(f"the dump failed: {message or broken}") from broken

    staff = [account.email for account in accounts if account.staff]
    findings = scan.scan_dump(path, staff)
    if not findings.clean:
        path.unlink()
        raise SnapshotError(
            "the pseudonymized dump failed its check and was deleted: "
            + json.dumps(findings.as_dict())
        )
    _write_json(staging / SITE / "options.json", options)
    say(
        f"database: {sum(stats.rows.values()):,} rows in {len(stats.tables())} tables, check passed"
    )
    return {
        "file": DATABASE,
        "tables": stats.tables(),
        "posts": dict(sorted(stats.posts.items())),
        "anonymization": anonymizer.report.as_dict(anonymizer.emails),
        "check": findings.as_dict(),
    }


def _lines(stream: IO[bytes]) -> Iterator[str]:
    """The gzip-compressed dump as text lines; bytes that are not UTF-8 survive."""
    with gzip.open(stream, "rt", encoding="utf-8", errors="surrogateescape") as dump:
        yield from dump


def _write_gzip(path: Path, lines: Iterable[str]) -> None:
    """Write gzip without a time stamp, so the same rows give the same file."""
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as out,
    ):
        for line in lines:
            out.write(line.encode("utf-8", "surrogateescape"))


def _options(
    items: Iterator[Line], options: list[dict[str, str | None]]
) -> Iterator[Line]:
    """Collect wp_options as `wp option list --format=json` lists them (after the anonymizer)."""
    for item in items:
        if isinstance(item, Insert) and item.table.name == TABLE_PREFIX + "options":
            table = item.table
            name, value, autoload = (
                table.index("option_name"),
                table.index("option_value"),
                table.index("autoload"),
            )
            options.extend(
                {
                    "option_name": row[name].text,
                    "option_value": row[value].text,
                    "autoload": row[autoload].text,
                }
                for row in item.rows
            )
        yield item


def _files(staging: Path, earlier: list[Path], themes: list[Any], say: Say) -> None:
    steps: list[tuple[str, str, Path, tuple[str, ...]]] = [
        ("uploads", "wp-content/uploads/", staging / UPLOADS, UPLOAD_FILTERS),
    ]
    for slug in live.LICENSED_PLUGINS:
        steps.append(
            (
                f"plugin {slug}",
                f"wp-content/plugins/{slug}/",
                staging / PLUGINS / slug,
                (),
            )
        )
    for theme in themes:
        if theme["status"] in ("active", "parent"):
            slug = str(theme["name"])
            steps.append(
                (
                    f"theme {slug}",
                    f"wp-content/themes/{slug}/",
                    staging / THEMES / slug,
                    (),
                )
            )
    steps.append(
        (
            "live plugins",
            "wp-content/plugins/",
            staging / LIVE_PLUGINS,
            tuple(f"--exclude=/{slug}/" for slug in live.LICENSED_PLUGINS),
        )
    )
    steps.append(
        (
            "live mu-plugins",
            "wp-content/mu-plugins/",
            staging / LIVE_MU_PLUGINS,
            tuple(f"--exclude=/{name}" for name in live.PLATFORM_MU_PLUGINS),
        )
    )
    for label, source, target, filters in steps:
        say(f"{label}: rsync from {live.HOST}")
        relative = target.relative_to(staging).as_posix()
        names = live.rsync(
            source,
            target,
            filters=filters,
            link_dest=[
                path / relative for path in earlier if (path / relative).is_dir()
            ],
        )
        # rsync names every entry it creates — a hard link into an earlier
        # snapshot counts as created — with directories ending in "/".
        created = list(_progress(names, say, label, lambda _: 1))
        files = sum(1 for name in created if not name.endswith("/"))
        directories = len(created) - files
        say(
            f"{label}: {files:,} files copied or hard-linked"
            + (f", {directories:,} directories" if directories else "")
        )


def _insert_rows(item: object) -> int:
    return len(item.rows) if isinstance(item, Insert) else 0


def _progress[T](
    items: Iterable[T], say: Say, label: str, weight: Callable[[T], int]
) -> Iterator[T]:
    """Pass `items` through, saying how many were done at least every PROGRESS_SECONDS."""
    done = 0
    last = time.monotonic()
    for item in items:
        done += weight(item)
        now = time.monotonic()
        if now - last >= PROGRESS_SECONDS:
            say(f"{label}: {done:,} so far")
            last = now
        yield item


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
