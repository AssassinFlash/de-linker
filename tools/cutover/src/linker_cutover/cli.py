"""`linker-cutover <step>|drill`: the one-time switch of docs/specs/17-cutover.md.

    linker-cutover backup       take the complete backup (step 1)
    linker-cutover maintenance  on|off (steps 2 and 7)
    linker-cutover deploy       files: the three plugins, the theme file and Polylang (step 3)
    linker-cutover plugins      export the snippets, remove the legacy plugins (step 3)
    linker-cutover data         the migrations (step 4)
    linker-cutover schema       retire the retained SEO plugin's Product template
    linker-cutover services     publish the two services, write their addresses (step 5)
    linker-cutover hygiene      host housekeeping (step 6)
    linker-cutover verify       the read-only regression subset (step 7)
    linker-cutover rollback     put the backup back (step 8)
    linker-cutover drill        rehearse all of it on a local instance

`--target local:<name>` runs a step against a local instance — the same code
path the maintenance window runs, which is what makes the drill evidence about
the window rather than about a rehearsal harness. Without it the target is the
production host.

Nothing writes unless `--write` is given; `drill` writes by design and says so.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import drill as drill_module
from linker_cutover import plan, steps
from linker_cutover.target import CutoverError, Target, local_target, remote_target

# The data root the local stack and tools/pull share (docs/local-stack.md).
DATA_HOME = Path.home() / "de-linker-data"


def repository_root() -> Path:
    """The repository this tool was run from: `<repo>/tools/cutover/src/linker_cutover/cli.py`."""
    return Path(__file__).resolve().parents[4]


def _target(name: str | None) -> Target:
    """`local:<instance>` for an instance, nothing for the production host."""
    if not name:
        return remote_target()
    if name.startswith("local:"):
        return local_target(name[len("local:") :])
    raise CutoverError(f"--target wants `local:<instance>`, got {name!r}")


def _common() -> argparse.ArgumentParser:
    """The options every step takes, so `just cutover verify --target …` works.

    They live on a shared parent parser rather than on the top-level one: the
    recipes pass the step name first (`just cutover verify --target local:t81`),
    and argparse would refuse a top-level option that comes after it.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--target",
        help="a local instance to run against (`--target local:t81`); without it, the production host",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="perform the changes; without it each step reports what it would do",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        help="the backup directory (default: the newest under ~/de-linker-data/cutover-*)",
    )
    parser.add_argument(
        "--administrator",
        default="",
        help="an administrator login for steps that need one",
    )
    parser.add_argument("--acceptance", type=Path, help="where a record is written")
    return parser


def _parser() -> argparse.ArgumentParser:
    common = _common()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup", parents=[common], help="step 1: the complete backup")
    maintenance = sub.add_parser(
        "maintenance", parents=[common], help="steps 2 and 7: the maintenance window"
    )
    maintenance.add_argument("state", choices=("on", "off"))
    sub.add_parser("deploy", parents=[common], help="step 3: the files")
    sub.add_parser(
        "plugins",
        parents=[common],
        help="step 3: snippets export, legacy plugins removed",
    )
    sub.add_parser("data", parents=[common], help="step 4: the migrations")
    services = sub.add_parser(
        "services", parents=[common], help="step 5: the two services"
    )
    services.add_argument("--run", action="store_true", help="publish (needs the VPS)")
    sub.add_parser(
        "schema", parents=[common], help="step 4: retire the stale schema templates"
    )
    sub.add_parser("hygiene", parents=[common], help="step 6: host housekeeping")
    sub.add_parser(
        "verify", parents=[common], help="step 7: the read-only regression subset"
    )
    sub.add_parser("rollback", parents=[common], help="step 8: put the backup back")
    rehearsal = sub.add_parser(
        "drill", parents=[common], help="rehearse the whole switch locally"
    )
    rehearsal.add_argument(
        "--instance", required=True, help="the local instance to rehearse on (e.g. t81)"
    )
    rehearsal.add_argument(
        "--staging",
        type=Path,
        help="where the plugin trees are built (default: under --acceptance)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # A window runs these steps with the output going to a file, where Python
    # buffers by default: nothing would appear until the step ended, and a step
    # that hangs would look exactly like a step that is working. Progress is
    # the point of a cutover script, so every line goes out as it happens.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = _parser()
    args = parser.parse_args(argv)
    target = _target(args.target)
    repository = repository_root()
    acceptance = args.acceptance or repository / "docs" / "acceptance" / _today() / "17"

    try:
        if args.command == "backup":
            print(f"cutover: backup at {_backup(target, args)}")
            return 0
        if args.command == "maintenance":
            _print(steps.maintenance(target, on=args.state == "on"))
            return 0
        if args.command == "deploy":
            staging = _workspace() / "staging"
            if not args.write:
                for slug in plan.NEW_PLUGINS:
                    print(f"deploy: would build and copy {slug}")
                print(
                    f"deploy: would install {plan.MU_PLUGINS_REPO}/*.php to "
                    f"{plan.MU_PLUGINS_DIR} (step 3 needs that directory in the checkout)"
                )
                return 0
            _print(steps.deploy(target, repository=repository, staging=staging))
            return 0
        if args.command == "plugins":
            snippets = _backup(target, args) / "snippets"
            _print(steps.export_snippets(target, snippets))
            if not args.write:
                print("plugins: dry run — nothing deactivated or deleted")
                return 0
            _print(
                steps.remove_legacy(
                    target,
                    snippets=snippets / "snippets.json",
                    acceptance=acceptance,
                )
            )
            return 0
        if args.command == "data":
            _print(
                steps.migrations(
                    repository,
                    target,
                    backup=_backup(target, args),
                    administrator=args.administrator,
                    writes=args.write,
                )
            )
            return 0
        if args.command == "services":
            _print(
                steps.services(
                    repository=repository,
                    addresses=_addresses(),
                    run=args.run,
                )
            )
            return 0
        if args.command == "schema":
            _print(steps.retire_stale_schema(target, writes=args.write))
            return 0
        if args.command == "hygiene":
            _print(
                steps.hygiene(target, backup=_backup(target, args), writes=args.write)
            )
            return 0
        if args.command == "verify":
            result = steps.verify(target, cache_buster=_cache_buster())
            _print(result)
            # A note is a check that failed: the window must not read a 200-only
            # page list as a pass when the redirect or a German page is wrong.
            return 1 if result.notes else 0
        if args.command == "rollback":
            result = steps.rollback(target, backup=_backup(target, args))
            _print(result)
            # A rollback that did not bring the old plugins back is the failure
            # the window must hear about, not a line in a log.
            return 1 if result.notes else 0
        if args.command == "drill":
            return _drill(args, repository, acceptance)
    except CutoverError as error:
        print(f"cutover: {error}", file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 2


def _drill(args: argparse.Namespace, repository: Path, acceptance: Path) -> int:
    """The rehearsal. Only its record lands in the repository.

    The staged plugin trees and the exported snippet rows go to the data root
    (`~/de-linker-data/cutover-workspace/`): the first is a build product no
    larger than the plugin it came from, and the second is the old tree's code,
    which the repository does not carry (AGENTS.md §5).
    """
    workspace = _workspace()
    rehearsal = drill_module.Drill(
        target=local_target(args.instance),
        repository=repository,
        home=DATA_HOME,
        staging=args.staging or (workspace / "staging"),
        snippets=workspace / "snippets",
        acceptance=acceptance,
        administrator=args.administrator,
    )
    record = rehearsal.run()
    record["plan"] = {
        "new_plugins": list(plan.NEW_PLUGINS),
        "legacy_plugins": list(plan.LEGACY_PLUGINS),
        "migrations": [asdict(migration) for migration in plan.MIGRATIONS],
    }
    destination = drill_module.write(record, acceptance / "drill.json")
    print(f"drill: record written to {destination}")
    return 0


def _backup(target: Target, args: argparse.Namespace) -> Path:
    """The backup directory a step works from: the one given, or a fresh one.

    Steps that can change the site take their own backup first: the window may
    be interrupted, and a step that only needs "a backup" would otherwise run
    against one taken an hour and a website ago. `--backup` names an existing
    one instead, which is what the drill and the rollback use — the rollback
    must restore the state the switch started from, not the state it created.
    """
    from linker_cutover import backup as backup_module  # noqa: PLC0415 - config, not a dependency

    if args.backup is not None:
        directory = Path(args.backup)
        if not (directory / backup_module.DUMP).is_file():
            raise CutoverError(f"{directory} has no {backup_module.DUMP}")
        return directory
    if args.write or args.command == "backup":
        return backup_module.create(target, DATA_HOME).directory
    newest = _newest()
    if newest is None:
        raise CutoverError(
            "no backup under ~/de-linker-data/cutover-*; run `backup` first"
        )
    return newest


def _workspace() -> Path:
    """Where a step's intermediate files go: outside the repository, beside the backups."""
    return DATA_HOME / "cutover-workspace"


def _newest() -> Path | None:
    """The newest backup under the data root, or None when there is none.

    Two directories under `~/de-linker-data/` start with `cutover-`: a backup
    and the tool's own work directory (`cutover-workspace`). Sorted by name the
    work directory is last — `w` sorts after every digit — so "the newest
    backup" used to be the workspace, which holds no backup at all. A candidate
    is a directory that holds the dump, and nothing else is one.
    """
    from linker_cutover import backup as backup_module  # noqa: PLC0415 - config, not a dependency

    candidates = [
        path
        for path in DATA_HOME.glob("cutover-*")
        if (path / backup_module.DUMP).is_file()
    ]
    return max(candidates, key=lambda path: path.name) if candidates else None


def _addresses() -> dict[str, str]:
    import os  # noqa: PLC0415 - configuration read, not a dependency

    return {name: os.environ.get(name, "") for _, _, name in plan.SERVICE_OPTIONS}


def _cache_buster() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _print(result: steps.Result) -> None:
    print(result.describe())


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


if __name__ == "__main__":
    raise SystemExit(main())
