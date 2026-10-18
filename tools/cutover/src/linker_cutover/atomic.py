"""One staged deployment, its consistent backup set, and rename operations."""

from __future__ import annotations

import json
import math
import re
import shlex
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from linker_cutover.target import CutoverError, Target


@dataclass(frozen=True)
class Artifact:
    """One complete plugin tree or one owned mu/theme file."""

    source: Path
    relative: str


@dataclass(frozen=True)
class Receipt:
    """A publication result, independent of shell output formatting."""

    deploy_id: str
    switch_seconds: float | None
    backup_directory: str
    paths: tuple[str, ...]
    readbacks: tuple[str, ...] = ()
    # Lines the after-switch step reported, marked AFTER_SWITCH_MARKER.
    after_switch: tuple[str, ...] = ()


@dataclass(frozen=True)
class Siblings:
    """Reserved sibling names; deploy and rollback use this one spelling."""

    next: str
    previous: str
    absent: str
    failed: str


@dataclass(frozen=True)
class Backup:
    """The provenance and expected identities of one backup and its new live."""

    relative: str
    deploy_id: str
    directory: bool
    existed: bool
    inode: str
    new_inode: str


@dataclass(frozen=True)
class Manifest:
    """One deploy's complete inventory, stored outside the web root."""

    deploy_id: str
    state: str
    backups: tuple[Backup, ...]


# GNU stat on Hostinger/Linux; BSD stat on the development Mac. Both return
# device:inode so a cross-device move is rejected before any live path moves.
_IDENTITY = """identity() {
    stat -c '%d:%i' "$1" 2>/dev/null || stat -f '%d:%i' "$1"
}
"""


# Lines an after-switch step prints for the receipt start with this.
AFTER_SWITCH_MARKER = "LINKER_AFTER_SWITCH "


def _switch_seconds(output: str, deploy_id: str) -> float:
    """Ignore transport/command diagnostics; accept exactly one timing record."""
    marker = "LINKER_CUTOVER_SWITCH_SECONDS="
    records = [line for line in output.splitlines() if line.startswith(marker)]
    if len(records) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", records[0][len(marker) :]):
        elapsed = float(records[0][len(marker) :])
        if math.isfinite(elapsed):
            return elapsed
    raise CutoverError(
        f"invalid switch timing for deployment {deploy_id}; inspect the manifest; "
        "use resume-deploy to verify/archive a pending deploy"
    )


def _siblings(relative: str) -> Siblings:
    path = Path(relative)
    return Siblings(
        *(
            str(path.with_name(f".{path.name}.{suffix}"))
            for suffix in ("next", "prev", "prev-absent", "failed")
        )
    )


def _quoted(target: Target, relative: str) -> str:
    return shlex.quote(target.path_of(relative))


def backup_root(target: Target) -> str:
    """Host account's private ~/deploy-prev; a temp/local target's sibling."""
    if target.rsync_remote is None:
        return str(Path(target.root).parent / "deploy-prev")
    return target.shell('printf "%s/deploy-prev" "$HOME"').strip()


def _check_id(deploy_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9-]+", deploy_id) is None:
        raise CutoverError(f"invalid deploy id {deploy_id!r}")
    return deploy_id


def identities(target: Target, paths: list[str]) -> dict[str, str]:
    """Read actual target identities; '-' means absent, including absent parents."""
    commands = ["set -eu", _IDENTITY]
    for path in dict.fromkeys(paths):
        quoted = shlex.quote(path)
        commands.append(
            f"if [ -e {quoted} ] || [ -L {quoted} ]; then value=$(identity {quoted}); else value=-; fi\nprintf '%s\\t%s\\n' {quoted} \"$value\""
        )
    return dict(
        line.split("\t", 1) for line in target.shell("\n".join(commands)).splitlines()
    )


def _manifest_path(directory: str) -> str:
    return str(Path(directory) / "manifest.json")


def _write_manifest(manifest: Manifest, directory: str) -> str:
    path = shlex.quote(_manifest_path(directory))
    temporary = shlex.quote(_manifest_path(directory) + ".next")
    return f"printf '%s' {shlex.quote(json.dumps(asdict(manifest)))} > {temporary}\nmv -f {temporary} {path}"


def latest_manifest(target: Target) -> tuple[str, Manifest]:
    """Load the most recent deployment record; no glob can mix backup batches."""
    root = backup_root(target)
    pointer = shlex.quote(str(Path(root) / "latest"))
    deploy_id = target.shell(f"if [ -f {pointer} ]; then cat {pointer}; fi").strip()
    if not deploy_id:
        raise CutoverError("no previous deployment manifest")
    directory = str(Path(root) / _check_id(deploy_id))
    try:
        raw = json.loads(target.shell(f"cat {shlex.quote(_manifest_path(directory))}"))
        manifest = Manifest(
            raw["deploy_id"],
            raw["state"],
            tuple(Backup(**entry) for entry in raw["backups"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CutoverError(f"invalid deployment manifest in {directory}") from error
    if manifest.deploy_id != deploy_id:
        raise CutoverError(f"manifest deploy id mismatch: {directory}")
    return directory, manifest


def _backup_path(
    target: Target, directory: str, manifest: Manifest, entry: Backup
) -> str:
    if manifest.state == "archived":
        return str(Path(directory) / "files" / entry.relative)
    names = _siblings(entry.relative)
    return target.path_of(names.previous if entry.existed else names.absent)


def _same_filesystem(target: Target, root: str, parents: list[str]) -> None:
    quoted = shlex.quote(root)
    web = shlex.quote(target.root)
    # Owner-only POSIX directory mode: archived PHP must not be web-served.
    target.shell(
        f'set -eu\nmkdir -p {quoted}\nchmod 700 {quoted}\nprivate=$(cd {quoted} && pwd -P)\nweb=$(cd {web} && pwd -P)\ncase "$private/" in "$web/"*) echo \'backup root is inside the web root\' >&2; exit 1;; esac'
    )
    values = identities(target, [root, *parents])
    device = values[root].split(":", 1)[0]
    mismatches = [
        path
        for path in parents
        if values[path] == "-" or values[path].split(":", 1)[0] != device
    ]
    if mismatches:
        raise CutoverError(
            "backup filesystem differs from live: " + ", ".join(mismatches)
        )


def publish(
    target: Target,
    artifacts: list[Artifact],
    *,
    deploy_id: str,
    on_switch: Callable[[], None] | None = None,
    after_switch: str = "",
) -> Receipt:
    """Upload everything, then rename everything in one recovery-protected shell.

    `after_switch` runs in the same shell straight after the renames and after
    the recovery trap is cleared: it can never undo the switch, and it starts
    without another ssh round trip (#308's opcode-cache reset).
    """
    _check_id(deploy_id)
    if not artifacts or len({item.relative for item in artifacts}) != len(artifacts):
        raise CutoverError("deployment inventory is empty or duplicated")
    root = backup_root(target)
    pointer = shlex.quote(str(Path(root) / "latest"))
    prior_id = target.shell(f"if [ -f {pointer} ]; then cat {pointer}; fi").strip()
    if prior_id:
        _, prior = latest_manifest(target)
        if prior.state == "pending":
            raise CutoverError(
                f"deployment {prior_id} still needs verify/archive or rollback"
            )
    for artifact in artifacts:
        names = _siblings(artifact.relative)
        if any(
            target.exists(path) for path in (names.previous, names.absent, names.failed)
        ):
            raise CutoverError(f"unresolved previous deployment: {artifact.relative}")
        parent = _quoted(target, str(Path(artifact.relative).parent))
        target.shell(
            f"set -eu\nmkdir -p {parent}\nrm -rf {_quoted(target, names.next)}"
        )
        if artifact.source.is_dir():
            target.copy_in(artifact.source, names.next)
        else:
            target.copy_file_in(artifact.source, names.next)
    _same_filesystem(
        target,
        root,
        [target.path_of(str(Path(item.relative).parent)) for item in artifacts],
    )
    directory = str(Path(root) / deploy_id)
    target.shell(
        f"set -eu\ntest ! -e {shlex.quote(directory)}\nmkdir {shlex.quote(directory)}"
    )
    live_paths = [target.path_of(item.relative) for item in artifacts]
    next_paths = [target.path_of(_siblings(item.relative).next) for item in artifacts]
    before = identities(target, live_paths + next_paths)
    prepare: list[str] = []
    for item, live_path in zip(artifacts, live_paths, strict=True):
        names = _siblings(item.relative)
        if before[live_path] == "-":
            prepare.append(
                f"printf '%s' {shlex.quote(deploy_id)} > {_quoted(target, names.absent)}"
            )
        elif not item.source.is_dir():
            prepare.append(
                f"cp -p {_quoted(target, item.relative)} {_quoted(target, names.previous)}"
            )
    backup_paths = [
        target.path_of(
            _siblings(item.relative).absent
            if before[live_path] == "-"
            else _siblings(item.relative).previous
        )
        if not item.source.is_dir() or before[live_path] == "-"
        else live_path
        for item, live_path in zip(artifacts, live_paths, strict=True)
    ]
    try:
        target.shell("set -eu\n" + "\n".join(prepare))
        saved = identities(target, backup_paths)
    except CutoverError:
        # No live rename has happened yet. Remove only this preparation's
        # file copies/absence markers so a failed copy cannot poison a retry.
        cleanup = [f"rm -rf {shlex.quote(directory)}"]
        for item in artifacts:
            names = _siblings(item.relative)
            cleanup.append(f"rm -f {_quoted(target, names.absent)}")
            if not item.source.is_dir():
                cleanup.append(f"rm -f {_quoted(target, names.previous)}")
        target.shell("set -eu\n" + "\n".join(cleanup))
        raise
    entries = tuple(
        Backup(
            item.relative,
            deploy_id,
            item.source.is_dir(),
            before[live_path] != "-",
            saved[backup_path],
            before[next_path],
        )
        for item, live_path, backup_path, next_path in zip(
            artifacts, live_paths, backup_paths, next_paths, strict=True
        )
    )
    manifest = Manifest(deploy_id, "pending", entries)
    switch: list[str] = []
    restore: list[str] = []
    for entry in entries:
        names = _siblings(entry.relative)
        live, staged, previous, absent = (
            _quoted(target, name)
            for name in (entry.relative, names.next, names.previous, names.absent)
        )
        if entry.directory and entry.existed:
            switch.append(f"mv {live} {previous}")
        switch.append(f"mv {'-f ' if not entry.directory else ''}{staged} {live}")
        if entry.existed:
            recovery = f"mv -f {previous} {live}"
            if entry.directory:
                failed = _quoted(target, names.failed)
                recovery = (
                    f"if [ -e {live} ] || [ -L {live} ]; then\n"
                    f"    mv {live} {failed} && mv {previous} {live} && rm -rf {failed}\n"
                    f"else\n    mv {previous} {live}\nfi"
                )
            restore.insert(
                0,
                f"if [ -e {previous} ] || [ -L {previous} ]; then\n{recovery}\nfi",
            )
        else:
            restore.insert(0, f"rm -rf {live}\nrm -f {absent}")
    restore.append(f"rm -rf {shlex.quote(directory)}")
    restore.append(
        f"printf '%s' {shlex.quote(prior_id)} > {pointer}"
        if prior_id
        else f"rm -f {pointer}"
    )
    script = (
        "set -eu\nrestore_all() {\ntrap - EXIT HUP INT TERM\nset +e\n"
        + "\n".join(restore)
        + "\n}\ntrap restore_all EXIT\ntrap 'exit 1' HUP INT TERM\n"
    )
    script += (
        "TIMEFORMAT='LINKER_CUTOVER_SWITCH_SECONDS=%R'\n{ time {\n"
        + "\n".join(switch)
        + "\n}; } 2>&1\n"
    )
    script += (
        _write_manifest(manifest, directory)
        + f"\nprintf '%s' {shlex.quote(deploy_id)} > {pointer}\ntrap - EXIT HUP INT TERM\n"
    )
    if after_switch:
        script += "set +e\n" + after_switch + "\n"
    if on_switch is not None:
        on_switch()
    output = target.shell(script)
    elapsed = _switch_seconds(output, deploy_id)
    return Receipt(
        deploy_id,
        elapsed,
        directory,
        tuple(item.relative for item in artifacts),
        after_switch=tuple(
            line[len(AFTER_SWITCH_MARKER) :]
            for line in output.splitlines()
            if line.startswith(AFTER_SWITCH_MARKER)
        ),
    )


def _checked_backups(
    target: Target, relatives: list[str]
) -> tuple[str, Manifest, list[str]]:
    """Name every missing, mixed-version or replaced backup before any write."""
    directory, manifest = latest_manifest(target)
    expected = set(relatives)
    found = {entry.relative for entry in manifest.backups}
    problems = [f"inventory mismatch: {path}" for path in sorted(expected ^ found)]
    if manifest.state not in ("pending", "archived"):
        problems.append(f"deployment {manifest.deploy_id} is {manifest.state}")
    for entry in manifest.backups:
        target.path_of(entry.relative)
    if len(found) != len(manifest.backups):
        problems.append("duplicate backup paths in manifest")
    paths = [
        _backup_path(target, directory, manifest, entry) for entry in manifest.backups
    ]
    actual = identities(target, paths)
    for entry, path in zip(manifest.backups, paths, strict=True):
        target.path_of(entry.relative)
        if entry.deploy_id != manifest.deploy_id:
            problems.append(
                f"{entry.relative}: deploy id {entry.deploy_id} differs from {manifest.deploy_id}"
            )
        if actual[path] != entry.inode:
            problems.append(
                f"{entry.relative}: backup inode mismatch ({actual[path]} != {entry.inode})"
            )
    if problems:
        raise CutoverError("rollback preflight: " + "; ".join(problems))
    return directory, manifest, paths


def archive(target: Target, receipt: Receipt) -> None:
    """After site verification, rename every backup into the private deploy set."""
    directory, manifest, paths = _checked_backups(target, list(receipt.paths))
    if manifest.deploy_id != receipt.deploy_id or manifest.state != "pending":
        raise CutoverError("archive requires the pending deployment receipt")
    _same_filesystem(
        target, backup_root(target), [str(Path(path).parent) for path in paths]
    )
    prepare: list[str] = []
    switch: list[str] = []
    recover: list[str] = []
    for entry, path in zip(manifest.backups, paths, strict=True):
        destination = str(Path(directory) / "files" / entry.relative)
        parent = shlex.quote(str(Path(destination).parent))
        source, saved = shlex.quote(path), shlex.quote(destination)
        prepare.append(f"mkdir -p {parent}\ntest ! -e {saved}")
        switch.append(f"mv {source} {saved}")
        recover.insert(
            0, f"if [ -e {saved} ] || [ -L {saved} ]; then mv {saved} {source}; fi"
        )
    # The manifest and the locations are one recoverable state. A signal after
    # its archived-state rename must restore the pending record as well.
    recover.append(_write_manifest(manifest, directory))
    target.shell("set -eu\n" + "\n".join(prepare))
    script = (
        "set -eu\nrestore_archive() {\ntrap - EXIT HUP INT TERM\nset +e\n"
        + "\n".join(recover)
        + "\n}\ntrap restore_archive EXIT\ntrap 'exit 1' HUP INT TERM\n"
    )
    script += (
        "\n".join(switch)
        + "\n"
        + _write_manifest(
            Manifest(manifest.deploy_id, "archived", manifest.backups), directory
        )
    )
    script += "\ntrap - EXIT HUP INT TERM\n"
    target.shell(script)
    _checked_backups(target, list(receipt.paths))
    siblings = [
        target.path_of(name)
        for relative in receipt.paths
        for name in asdict(_siblings(relative)).values()
    ]
    remaining = [
        path for path, value in identities(target, siblings).items() if value != "-"
    ]
    if remaining:
        raise CutoverError(
            "deployment artifacts remain in web root: " + ", ".join(remaining)
        )
    # PR #299 rounds 1/3: this root belongs only to deployment batches. Retain
    # the latest after successful readback, including pruning killed batches
    # that never reached their manifest commit.
    root = shlex.quote(backup_root(target))
    target.shell(
        f'set -eu\nfor old in {root}/*; do\n    [ -d "$old" ] || continue\n    if [ "$old" != {shlex.quote(directory)} ]; then rm -rf "$old"; fi\ndone\n'
    )


def pending_receipt(target: Target, relatives: list[str]) -> Receipt:
    """Recover a lost receipt without inventing timing or republishing live files."""
    directory, manifest, _ = _checked_backups(target, relatives)
    if manifest.state != "pending":
        raise CutoverError(f"deployment {manifest.deploy_id} is not pending")
    actual = identities(target, [target.path_of(path) for path in relatives])
    drifted = [
        entry.relative
        for entry in manifest.backups
        if actual[target.path_of(entry.relative)] != entry.new_inode
    ]
    if drifted:
        raise CutoverError("live changed since deploy: " + ", ".join(drifted))
    return Receipt(manifest.deploy_id, None, directory, tuple(relatives))


def rollback(target: Target, relatives: list[str]) -> Receipt:
    """Restore one consistent deploy and read every restored live identity back."""
    directory, manifest, paths = _checked_backups(target, relatives)
    live_paths = [target.path_of(entry.relative) for entry in manifest.backups]
    live_before = identities(target, live_paths)
    drifted = [
        entry.relative
        for entry, live in zip(manifest.backups, live_paths, strict=True)
        if live_before[live] != entry.new_inode
    ]
    if drifted:
        raise CutoverError("live changed since deploy: " + ", ".join(drifted))
    _same_filesystem(
        target, backup_root(target), [str(Path(path).parent) for path in live_paths]
    )
    prepare: list[str] = []
    checks: list[str] = []
    switch: list[str] = []
    recover: list[str] = []
    cleanup: list[str] = []
    for entry, backup_path in zip(manifest.backups, paths, strict=True):
        names = _siblings(entry.relative)
        live, current, previous = (
            _quoted(target, entry.relative),
            _quoted(target, names.next),
            shlex.quote(backup_path),
        )
        checks.append(f"test ! -e {current}\ntest ! -L {current}")
        if entry.existed and not entry.directory:
            # A same-filesystem hard link keeps the current inode intact if a
            # later rollback rename fails and the whole new batch is restored.
            prepare.append(f"ln {live} {current}")
        else:
            switch.append(f"mv {live} {current}")
        if entry.existed:
            switch.append(f"mv {'-f ' if not entry.directory else ''}{previous} {live}")
            untouched = (
                f"mv {current} {live}" if entry.directory else f"rm -f {current}"
            )
            recover.insert(
                0,
                f"if [ -e {current} ] || [ -L {current} ]; then\n    if [ ! -e {previous} ] && [ ! -L {previous} ]; then\n        mv {live} {previous}\n        mv {'-f ' if not entry.directory else ''}{current} {live}\n    else\n        {untouched}\n    fi\nfi",
            )
        else:
            recover.insert(
                0,
                f"if [ -e {current} ] || [ -L {current} ]; then mv {current} {live}; fi",
            )
        cleanup.append(f"rm -rf {current}")
        if not entry.existed:
            cleanup.append(f"rm -f {previous}")
    target.shell("set -eu\n" + "\n".join(checks))
    try:
        target.shell("set -eu\n" + "\n".join(prepare))
    except CutoverError:
        # Every .next was absent in the read-only checks above; no live rename
        # has run, so only these preparation links can exist here.
        target.shell(
            "set -eu\n"
            + "\n".join(
                f"rm -f {_quoted(target, _siblings(entry.relative).next)}"
                for entry in manifest.backups
                if entry.existed and not entry.directory
            )
        )
        raise
    script = (
        "set -eu\nrestore_all() {\ntrap - EXIT HUP INT TERM\nset +e\n"
        + "\n".join(recover)
        + "\n}\ntrap restore_all EXIT\ntrap 'exit 1' HUP INT TERM\n"
    )
    script += (
        "TIMEFORMAT='LINKER_CUTOVER_SWITCH_SECONDS=%R'\n{ time {\n"
        + "\n".join(switch)
        + "\n}; } 2>&1\ntrap - EXIT HUP INT TERM\n"
    )
    output = target.shell(script)
    restored = identities(target, live_paths)
    readbacks: list[str] = []
    for entry, live in zip(manifest.backups, live_paths, strict=True):
        wanted = entry.inode if entry.existed else "-"
        if restored[live] != wanted:
            raise CutoverError(
                f"rollback readback {entry.relative}: {restored[live]} != {wanted}"
            )
        readbacks.append(
            f"{entry.relative}: {'absent' if wanted == '-' else 'device:inode ' + wanted}"
        )
    target.shell(
        "set -eu\n"
        + "\n".join(cleanup)
        + "\n"
        + _write_manifest(
            Manifest(manifest.deploy_id, "rolled_back", manifest.backups), directory
        )
    )
    return Receipt(
        manifest.deploy_id,
        _switch_seconds(output, manifest.deploy_id),
        directory,
        tuple(relatives),
        tuple(readbacks),
    )
