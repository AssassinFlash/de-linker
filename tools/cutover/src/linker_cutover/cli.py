"""`linker-cutover <step>|drill`: the one-time switch of docs/specs/17-cutover.md.

    linker-cutover backup       take the complete backup (step 1)
    linker-cutover maintenance  on|off (steps 2 and 7)
    linker-cutover deploy       files: the three plugins, the theme file and Polylang (step 3)
    linker-cutover rollback-deploy restore the previous deployed files by rename
    linker-cutover probe        run the deployment with concurrent page/REST probes
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
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import backup as backup_module
from linker_cutover import drill as drill_module
from linker_cutover import plan, probe, steps
from linker_cutover import snapshot as snapshot_module
from linker_cutover.target import CutoverError, Target, local_target, remote_target

# The data root on this Mac (backups, snapshots, workspace); one definition in backup.py.
DATA_HOME = backup_module.DATA_HOME


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
        "snapshot",
        parents=[common],
        help="database snapshot to this Mac (deploy takes one itself)",
    )
    sub.add_parser("snapshots", parents=[common], help="list the snapshots on this Mac")
    restoring = sub.add_parser(
        "restore-snapshot", parents=[common], help="put a database snapshot back"
    )
    restoring.add_argument("name", help="db-YYYYMMDDTHHMMSSZ.sql.gz (see `snapshots`)")
    sub.add_parser(
        "resume-deploy", parents=[common], help="verify/archive a pending file deploy"
    )
    sub.add_parser(
        "reconcile",
        parents=[common],
        help="re-point a pending deploy's backup identities before verify",
    )
    sub.add_parser(
        "rollback-deploy", parents=[common], help="restore the previous deployed files"
    )
    proof = sub.add_parser(
        "probe", parents=[common], help="deploy with concurrent page/REST probes"
    )
    proof.add_argument("--evidence", type=Path, help="local evidence directory")
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


@contextmanager
def _local_operation(args: argparse.Namespace) -> Iterator[None]:
    # probe delegates all site writes to its deploy child, which owns this
    # lock itself; holding it in both parent and child would deadlock.
    name = (
        args.instance
        if args.command == "drill"
        else (
            args.target[len("local:") :]
            if args.target and args.target.startswith("local:")
            else None
        )
    )
    if name is None or args.command == "probe":
        yield
        return
    from linker_local import retirement
    from linker_local.instance import home

    with retirement.available(home(), name):
        yield


def main(argv: list[str] | None = None) -> int:
    # A window runs these steps with the output going to a file, where Python
    # buffers by default: nothing would appear until the step ended, and a step
    # that hangs would look exactly like a step that is working. Progress is
    # the point of a cutover script, so every line goes out as it happens.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        with _local_operation(args):
            return _run(args, parser)
    except (CutoverError, RuntimeError, OSError, ValueError) as error:
        print(f"cutover: {error}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    target = _target(args.target)
    repository = repository_root()
    acceptance = args.acceptance or repository / "docs" / "acceptance" / _today() / "17"

    try:
        if args.command == "backup":
            print(f"cutover: backup at {_backup(target, args)}")
            return 0
        if args.command == "snapshot":
            taken = snapshot_module.take(target, DATA_HOME)
            print(
                f"snapshot: {taken.path} ({taken.size} bytes, sha256 {taken.sha256[:16]}…)"
            )
            return 0
        if args.command == "snapshots":
            for name in snapshot_module.available(DATA_HOME):
                print(name)
            return 0
        if args.command == "restore-snapshot":
            path = snapshot_module.existing(DATA_HOME, args.name)
            if not args.write:
                print(
                    f"restore-snapshot: would keep the current database as a snapshot, "
                    f"then replace it with {path}"
                )
                return 0
            for line in snapshot_module.restore(target, DATA_HOME, args.name):
                print(f"restore-snapshot: {line}")
            return 0
        if args.command == "maintenance":
            _print(steps.maintenance(target, on=args.state == "on"))
            return 0
        if args.command == "deploy":
            staging = _workspace() / "staging"
            if not args.write:
                for slug in plan.NEW_PLUGINS:
                    print(
                        f"deploy: would build and stage {slug}, then rename (keep .prev)"
                    )
                print(
                    f"deploy: would stage {plan.MU_PLUGINS_REPO}/*.php and *.pem beside "
                    f"{plan.MU_PLUGINS_DIR} files, then rename (keep .prev)"
                )
                print(
                    f"deploy: would stage {plan.THEMES_REPO}/ files, then rename (keep .prev)"
                )
                print(
                    "deploy: would switch every artifact in one shell, verify, then archive outside the web root (retain latest deploy only)"
                )
                return 0
            deployed = steps.deploy(
                target,
                repository=repository,
                staging=staging,
                on_switch=lambda: print(probe.SWITCH_MARKER, flush=True),
                snapshot_home=DATA_HOME,
            )
            _print(deployed)
            assert deployed.publication is not None
            checked = steps.finish_deploy(
                target, deployed.publication, cache_buster=_cache_buster()
            )
            _print(checked)
            return 1 if checked.notes else 0
        if args.command == "reconcile":
            if not args.write:
                print(
                    "reconcile: would re-read the pending manifest's backup identities"
                )
                return 0
            corrected = steps.reconcile(target)
            _print(corrected)
            return 1 if corrected.notes else 0
        if args.command == "resume-deploy":
            if not args.write:
                print(
                    "resume-deploy: would verify/archive the pending deployment manifest"
                )
                return 0
            resumed = steps.resume_deploy(
                target, repository=repository, cache_buster=_cache_buster()
            )
            _print(resumed)
            return 1 if resumed.notes else 0
        if args.command == "rollback-deploy":
            if not args.write:
                print(
                    "rollback-deploy: would restore the previous deployed files by rename"
                )
                return 0
            restored = steps.rollback_deploy(target, repository=repository)
            _print(restored)
            return 1 if restored.notes else 0
        if args.command == "probe":
            if not args.write:
                for endpoint in plan.DEPLOY_PROBE_ENDPOINTS:
                    print(f"probe: {endpoint.name} GET {endpoint.path}")
                print("probe: dry run; add --write to run deployment")
                return 0
            evidence = args.evidence or DATA_HOME / ("deploy-proof-" + _cache_buster())

            def deployment_command(on_switch: Callable[[], None]) -> int:
                command = [
                    sys.executable,
                    "-m",
                    "linker_cutover.cli",
                    "deploy",
                    "--write",
                ]
                if args.target:
                    command += ["--target", args.target]
                return probe.run_deployment(
                    command,
                    repository=repository,
                    log=evidence / "deploy.log",
                    on_switch=on_switch,
                )

            proof_result = probe.observe(target, deployment_command, evidence=evidence)
            print(
                f"probe: {len(proof_result.samples)} samples, success={proof_result.successful}; {evidence / 'proof.json'}"
            )
            return 0 if proof_result.successful else 1
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
            if args.write:
                # Drafting SEO rows is a data write: a full backup first (AGENTS.md §5).
                print(f"schema: full backup at {_backup(target, args)}")
            _print(steps.retire_stale_schema(target, writes=args.write))
            return 0
        if args.command == "hygiene":
            _print(
                steps.hygiene(target, backup=_backup(target, args), writes=args.write)
            )
            return 0
        if args.command == "verify":
            result = steps.verify_site(target, cache_buster=_cache_buster())
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
