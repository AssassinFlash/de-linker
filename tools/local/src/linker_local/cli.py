"""`linker-local`: create, start, stop and reset the local WordPress instances (docs/local-stack.md)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from linker_local import (
    objectcache,
    retirement,
    server,
    services,
    snapshot,
    wordpress,
    wpcli,
)
from linker_local.checkout import Checkout
from linker_local.instance import Instance, check_name, database_of, directory_of, home
from linker_local.mysql import CREDENTIALS, MySQL
from linker_local.processes import without_research_credentials
from linker_local.registry import Registry
from linker_local.wpcli import WpCli

# The production host runs PHP 8.3 (docs/research/2026-10-09/framework-choice.md §2).
PHP_VERSION = "8.3"

# Failures the user can act on, printed as one line. Every error class of this
# package (DownloadError, MySQLError, ProcessError, RedisError, SnapshotError,
# WpCliError) is a RuntimeError; ValueError is a bad instance name.
ERRORS = (RuntimeError, ValueError, OSError, subprocess.CalledProcessError)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result: int = args.run(args)
    except ERRORS as error:
        print(f"linker-local: {error}", file=sys.stderr)
        return 1
    return result


def up(args: argparse.Namespace) -> int:
    # Everything that can refuse is checked before a new name takes ports.
    check_name(args.name)
    php, checkout = _preconditions(args.snapshot)
    with retirement.available(home(), args.name):
        return _up(args, php, checkout)


def _up(args: argparse.Namespace, php: Path, checkout: Checkout) -> int:
    registry = Registry(home())
    instance = registry.get(args.name)
    if instance is None:
        _refuse_foreign(args.name)
        instance = registry.register(args.name)
    say = _sayer(instance)
    if instance.is_provisioned():
        wordpress.refresh(instance, php, checkout, say, args.snapshot)
    elif instance.dir.exists() or MySQL(CREDENTIALS).database_exists(instance.database):
        raise RuntimeError(
            f"{instance.name} is incomplete (an earlier `up` stopped part-way); "
            f"`just reset {instance.name}` builds it again"
        )
    else:
        say(f"new instance on port {instance.port}")
        wordpress.provision(
            instance, php, checkout, MySQL(CREDENTIALS), say, args.snapshot
        )
    server.start(instance, php)
    _summary(instance)
    return 0


def down(args: argparse.Namespace) -> int:
    _registered(args.name)
    with retirement.available(home(), args.name):
        return _down(args)


def _down(args: argparse.Namespace) -> int:
    instance = _registered(args.name)
    stopped = (["server"] if server.stop(instance) else []) + services.stop(instance)
    print(
        f"{instance.name}: stopped {', '.join(stopped)}"
        if stopped
        else f"{instance.name}: not running"
    )
    return 0


def reset(args: argparse.Namespace) -> int:
    _registered(args.name)
    php, checkout = _preconditions(args.snapshot)  # before anything is deleted
    with retirement.available(home(), args.name):
        return _reset(args, _registered(args.name), php, checkout)


def _reset(
    args: argparse.Namespace, instance: Instance, php: Path, checkout: Checkout
) -> int:
    say = _sayer(instance)
    server.stop(instance)
    services.stop(instance)
    mysql = MySQL(CREDENTIALS)
    say(f"deleting database {instance.database} and {instance.dir}")
    mysql.drop_database(instance.database)
    if instance.dir.exists():
        shutil.rmtree(instance.dir)
    wordpress.provision(instance, php, checkout, mysql, say, args.snapshot)
    server.start(instance, php)
    _summary(instance)
    return 0


def login(args: argparse.Namespace) -> int:
    _built(args.name)
    with retirement.available(home(), args.name):
        return _login(args)


def _login(args: argparse.Namespace) -> int:
    instance = _built(args.name)
    # The token is a transient, which lives in Redis once the object cache is on.
    objectcache.require_redis()
    # The login name travels in the environment, so no quoting puts it into PHP code.
    url = WpCli(require_php(), instance).run(
        "eval",
        "echo linker_local_login_url( (string) getenv( 'LINKER_LOCAL_LOGIN' ) );",
        env={"LINKER_LOCAL_LOGIN": args.user},
    )
    if not url:
        raise RuntimeError(f"{instance.name} has no user {args.user}")
    print(url)
    if server.process(instance).pid() is None:
        print(
            f"(the server is stopped: `just up {instance.name}` first)", file=sys.stderr
        )
    return 0


def snapshot_taken(instance: Instance) -> str:
    """When the live snapshot the instance holds was taken, "-" without one (#252)."""
    try:
        note = json.loads(instance.snapshot_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return "-"
    taken = str(note.get("taken", "")) if isinstance(note, dict) else ""
    # The manifest's ISO time, to the minute, in UTC: 2026-10-17T11:28:22+00:00.
    return taken[:16].replace("T", " ") + " UTC" if taken else "-"


def status(args: argparse.Namespace) -> int:
    instances = Registry(home()).all()
    if not instances:
        print(f"no instances in {home()}")
        return 0
    rows = [
        (
            "name",
            "url",
            "database",
            "server",
            "services",
            "WordPress",
            "Woo",
            "snapshot",
            "checkout",
        )
    ]
    for instance in instances:
        found = wordpress.versions(instance)
        checkout = wordpress.linked_checkout(instance)
        rows.append(
            (
                instance.name,
                instance.url,
                instance.database,
                "running" if server.process(instance).pid() else "stopped",
                ", ".join(services.running(instance)) or "-",
                found["WordPress"] or "-",
                found["WooCommerce"] or "-",
                snapshot_taken(instance),
                str(checkout) if checkout else "-",
            )
        )
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    for row in rows:
        print(
            "  ".join(
                cell.ljust(width) for cell, width in zip(row, widths, strict=True)
            ).rstrip()
        )
    return 0


def serve(args: argparse.Namespace) -> int:
    instance = _built(args.name)
    with retirement.available(home(), args.name):
        instance = _built(args.name)
        for line in services.serve(
            instance, Checkout.here(), WpCli(require_php(), instance), only=args.service
        ):
            print(f"{instance.name}: {line}")
    return 0


def retire(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            retirement.retire(
                home(),
                args.name,
                write=args.write,
                preserve=args.preserve,
                discard=args.discard,
                preserve_to=args.preserve_to,
            ),
            indent=2,
        )
    )
    return 0


def wp(args: argparse.Namespace) -> int:
    _built(args.name)
    with retirement.available(home(), args.name):
        return WpCli(require_php(), _built(args.name)).passthrough(args.args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linker-local", description="Local WordPress instances of de-linker.com."
    )
    commands = parser.add_subparsers(required=True, metavar="command")

    def command(
        name: str, run: Callable[[argparse.Namespace], int], help_text: str
    ) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.set_defaults(run=run)
        return sub

    snapshot_help = (
        "a snapshot directory (#6): install its plugins/, themes/ and uploads/"
    )
    sub = command(
        "up", up, "create the instance if it does not exist, then (re)start its server"
    )
    sub.add_argument("name")
    sub.add_argument("--snapshot", type=Path, help=snapshot_help)
    sub = command("down", down, "stop the instance's server and services")
    sub.add_argument("name")
    sub = command(
        "reset", reset, "delete the instance's database and files, then build it again"
    )
    sub.add_argument("name")
    sub.add_argument("--snapshot", type=Path, help=snapshot_help)
    sub = command(
        "retire",
        retire,
        "plan permanent retirement; --write requires explicit evidence decisions",
    )
    sub.add_argument("name")
    sub.add_argument("--write", action="store_true")
    sub.add_argument("--preserve", action="append", default=[])
    sub.add_argument("--discard", action="append", default=[])
    sub.add_argument("--preserve-to", type=Path)
    sub = command("login", login, "print a one-time login link (ten minutes, one use)")
    sub.add_argument("name")
    sub.add_argument("--user", default=wordpress.ADMIN_USER)
    command("status", status, "list the instances")
    sub = command("serve", serve, "(re)start the engine and Genie of the instance")
    sub.add_argument("name")
    sub.add_argument("--service", choices=("engine", "genie"))
    sub = command("wp", wp, "run WP-CLI against the instance")
    sub.add_argument("name")
    sub.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def require_php() -> Path:
    """PHP 8.3 ($PHP; the justfile passes Homebrew's php@8.3), checked with WP-CLI 2.12."""
    name = os.environ.get("PHP", "php")
    found = shutil.which(name)
    version = ""
    if found is not None:
        version = subprocess.run(
            [found, "-r", "echo PHP_MAJOR_VERSION, '.', PHP_MINOR_VERSION;"],
            env=without_research_credentials(),
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    if found is None or version != PHP_VERSION:
        raise RuntimeError(
            f"PHP {PHP_VERSION} is required, {name} is {version or 'not runnable'}: "
            "brew install php@8.3, then run through `just` (docs/local-stack.md)"
        )
    wpcli.require_version(Path(found))
    return Path(found)


def _preconditions(snapshot_dir: Path | None) -> tuple[Path, Checkout]:
    """What up and reset need, checked before they register, build or delete anything."""
    if snapshot_dir is not None:
        snapshot.check(snapshot_dir)
    php = require_php()
    objectcache.require_redis()
    checkout = Checkout.here()
    wordpress.require_plugin_dependencies(checkout)
    return php, checkout


def _refuse_foreign(name: str) -> None:
    """A new name must not take over a database or directory that something else made."""
    directory = directory_of(home(), name)
    if directory.exists():
        raise RuntimeError(f"{directory} exists but is not a registered instance")
    if MySQL(CREDENTIALS).database_exists(database_of(name)):
        raise RuntimeError(
            f"database {database_of(name)} exists but is not a registered instance"
        )


def _registered(name: str) -> Instance:
    instance = Registry(home()).get(name)
    if instance is None:
        raise RuntimeError(f"there is no instance {name}; `just up {name}` creates it")
    return instance


def _built(name: str) -> Instance:
    instance = _registered(name)
    if not instance.is_provisioned():
        raise RuntimeError(
            f"{name} is not built; `just up {name}` or `just reset {name}`"
        )
    return instance


def _sayer(instance: Instance) -> wordpress.Say:
    def say(message: str) -> None:
        print(f"{instance.name}: {message}", flush=True)

    return say


def _summary(instance: Instance) -> None:
    print(
        f"{instance.name}: {instance.url}/ (wp-admin: {wordpress.ADMIN_USER}, password in {instance.admin_file})"
    )
    print(
        f"{instance.name}: mail in {instance.mail_dir}/, blocked requests in {instance.isolation_log}"
    )
