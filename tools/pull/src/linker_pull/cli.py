"""`linker-pull`: read-only snapshots of de-linker.com and loading them locally (docs/specs/6-live-pull.md)."""

from __future__ import annotations

import argparse
import gzip
import http.client
import json
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO
from urllib.parse import urlsplit

from linker_pull import live, load, manifest, scan, snapshot
from linker_pull.anonymize import Anonymizer, accounts_from_dump
from linker_pull.sqldump import DumpError

ERRORS = (
    DumpError,
    load.LoadError,
    live.LiveError,
    snapshot.SnapshotError,
    OSError,
    ValueError,
    subprocess.CalledProcessError,
)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result: int = args.run(args)
    except ERRORS as error:
        print(f"linker-pull: {error}", file=sys.stderr)
        return 1
    return result


def say(message: str) -> None:
    print(message, flush=True)


def take_snapshot(args: argparse.Namespace) -> int:
    snapshot.take(snapshot.data_root(), say)
    return 0


def anonymize(args: argparse.Namespace) -> int:
    """Pseudonymize a dump file (one pass for the accounts, one for the rows), then check it.

    The result is deleted if it fails the check, as a snapshot's would be.
    """
    with _text(args.source) as dump:
        accounts = accounts_from_dump(dump)
    anonymizer = Anonymizer(accounts)
    with (
        _text(args.source) as dump,
        gzip.open(args.target, "wt", encoding="utf-8", errors="surrogateescape") as out,
    ):
        out.writelines(anonymizer.run(dump))
    findings = scan.scan_dump(
        args.target, [account.email for account in accounts if account.staff]
    )
    if not findings.clean:
        args.target.unlink()
    say(
        json.dumps(
            {
                "anonymization": anonymizer.report.as_dict(anonymizer.emails),
                "check": findings.as_dict(),
            },
            indent=1,
        )
    )
    return 0 if findings.clean else 1


def load_snapshot(args: argparse.Namespace) -> int:
    target = load.instance(args.name, args.port)
    result = load.load(target, _snapshot(args.snapshot), args.live_code, say)
    say(json.dumps(result, indent=1))
    return 0 if result["ok"] else 1


def diff(args: argparse.Namespace) -> int:
    changes = manifest.diff(
        manifest.read(_snapshot(args.old)), manifest.read(_snapshot(args.new))
    )
    if args.json:
        say(json.dumps(changes.as_dict(), indent=1))
    else:
        for line in changes.lines():
            say(line)
    return 0


def scan_snapshot(args: argparse.Namespace) -> int:
    path = (
        args.dump if args.dump.is_file() else _snapshot(args.dump) / snapshot.DATABASE
    )
    with _text(path) as dump:
        staff = [account.email for account in accounts_from_dump(dump) if account.staff]
    findings = scan.scan_dump(path, staff)
    say(json.dumps(findings.as_dict(), indent=1))
    return 0 if findings.clean else 1


def check_urls(args: argparse.Namespace) -> int:
    """GET every address of the snapshot's sitemaps from a local instance; count the statuses."""
    sitemaps = sorted(
        (_snapshot(args.snapshot) / snapshot.SITE / "sitemaps").glob("*.xml")
    )
    if args.sitemap:
        sitemaps = [path for path in sitemaps if path.name == args.sitemap]
    if not sitemaps:
        raise ValueError("the snapshot has no such sitemap")
    base = urlsplit(args.base)
    statuses: Counter[int] = Counter()
    failures: list[str] = []
    started = time.monotonic()
    last_said = started
    for sitemap in sitemaps:
        for url in live.sitemap_urls(sitemap.read_bytes()):
            path = urlsplit(url)._replace(scheme="", netloc="").geturl() or "/"
            # A bound on a hung request: the slowest live-copy page took 5.3 s on
            # 2026-10-09 (the product archive on one PHP worker).
            connection = http.client.HTTPConnection(
                base.hostname or "127.0.0.1", base.port, timeout=120
            )
            connection.request("GET", path)
            status = connection.getresponse().status
            connection.close()
            statuses[status] += 1
            if status != 200:
                failures.append(f"{status} {path}")
            now = time.monotonic()
            if now - last_said >= snapshot.PROGRESS_SECONDS:
                say(
                    f"check-urls: {sum(statuses.values()):,} of the addresses answered "
                    f"({', '.join(f'{code}: {count}' for code, count in sorted(statuses.items()))})"
                )
                last_said = now
    say(
        json.dumps(
            {
                "sitemaps": [path.name for path in sitemaps],
                "base": args.base,
                "statuses": dict(sorted(statuses.items())),
                "not_200": failures,
                "seconds": round(time.monotonic() - started),
            },
            indent=1,
        )
    )
    return 0 if not failures else 1


def _snapshot(name: str | Path) -> Path:
    """A snapshot directory, by path, by name in the data root, or `latest`."""
    path = Path(name)
    if path.is_dir():
        return path
    root = snapshot.data_root()
    found = snapshot.latest(root) if str(name) == "latest" else root / str(name)
    if found is None or not found.is_dir():
        raise ValueError(f"no snapshot {name} (in {root})")
    return found


@contextmanager
def _text(path: Path) -> Iterator[IO[str]]:
    """A dump file as text lines, gzip-compressed or not."""
    opener: Callable[..., IO[str]] = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="surrogateescape") as handle:
        yield handle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linker-pull",
        description="Read-only snapshots of the live de-linker.com, loaded into local instances.",
    )
    commands = parser.add_subparsers(required=True, metavar="command")

    def command(
        name: str, run: Callable[[argparse.Namespace], int], text: str
    ) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=text, description=text)
        sub.set_defaults(run=run)
        return sub

    command(
        "snapshot",
        take_snapshot,
        "copy the live site into a new snapshot in $LINKER_PULL_DATA or ~/de-linker-data"
        " (read-only on the host)",
    )
    sub = command(
        "anonymize",
        anonymize,
        "pseudonymize a mysqldump file (.sql or .sql.gz) into a .sql.gz and check it",
    )
    sub.add_argument("source", type=Path)
    sub.add_argument("target", type=Path)
    sub = command("load", load_snapshot, "load a snapshot into a local instance")
    sub.add_argument(
        "name", help="the instance: ~/de-linker-local/<name>, database linker_<name>"
    )
    sub.add_argument("snapshot", help="a snapshot directory, its name, or latest")
    sub.add_argument(
        "--port", type=int, help="default: the instance's port in instances.toml"
    )
    sub.add_argument(
        "--live-code",
        action="store_true",
        help="also the live plugins: a copy of the live site",
    )
    sub = command("diff", diff, "what changed between two snapshots")
    sub.add_argument("old")
    sub.add_argument("new")
    sub.add_argument("--json", action="store_true")
    sub = command(
        "scan",
        scan_snapshot,
        "check a snapshot's SQL for hashes, credentials and addresses",
    )
    sub.add_argument(
        "dump", type=Path, help="a snapshot (directory, name, latest) or a .sql.gz file"
    )
    sub = command(
        "check-urls",
        check_urls,
        "request every sitemap address of a snapshot from a local instance",
    )
    sub.add_argument("snapshot")
    sub.add_argument(
        "--base", required=True, help="the instance, e.g. http://127.0.0.1:8106"
    )
    sub.add_argument("--sitemap", help="one sitemap file, e.g. de-sitemap.xml")
    return parser
