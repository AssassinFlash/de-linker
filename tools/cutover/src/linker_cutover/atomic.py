"""One staged deployment, its consistent backup set, and rename operations."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import re
import shlex
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from linker_cutover import planner_contracts, public_assets
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


def _source_bytes(source: Path) -> int:
    """Every regular file's size under a source tree (0 for a single file)."""
    return (
        sum(item.stat().st_size for item in source.rglob("*") if item.is_file())
        if source.is_dir()
        else source.stat().st_size
    )


def _human(size: int) -> str:
    """A byte count for the deploy log: 23.4 MB."""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} kB"
    return f"{size} B"


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


def _discard_unswitched_preparation(
    target: Target,
    manifest: Manifest,
    directory: str,
    before: dict[str, str],
    prepared: dict[str, str],
    prior_id: str,
) -> str:
    """Discard only this shell's inode-recorded preparation while live is unchanged."""
    batch = shlex.quote(directory)
    pointer = shlex.quote(str(Path(backup_root(target)) / "latest"))
    checks = [
        _IDENTITY,
        'test -n "$batch_inode"',
        f"test ! -L {batch}",
        f'test "$(identity {batch})" = "$batch_inode"',
        f'test "$(if [ -f {pointer} ]; then cat {pointer}; fi)" = {shlex.quote(prior_id)}',
        shlex.join(
            [
                "python3",
                "-c",
                "import os,sys\nwith os.scandir(sys.argv[1]) as entries:\n"
                " if next(entries,None) is not None:raise RuntimeError('preparation batch not empty')",
                directory,
            ]
        ),
    ]
    cleanup: list[str] = []
    for entry in manifest.backups:
        live = _quoted(target, entry.relative)
        if entry.existed:
            checks.append(
                f'test "$(identity {live})" = '
                + shlex.quote(before[target.path_of(entry.relative)])
            )
        else:
            checks.append(f"test ! -e {live}\ntest ! -L {live}")
        names = _siblings(entry.relative)
        staged = _quoted(target, names.next)
        checks.append(
            f'test "$(identity {staged})" = '
            + shlex.quote(before[target.path_of(names.next)])
        )
        for sibling in (
            names.failed,
            names.absent if entry.existed else names.previous,
        ):
            quoted = _quoted(target, sibling)
            checks.append(f"test ! -e {quoted}\ntest ! -L {quoted}")
        if entry.directory and entry.existed:
            # The original live directory becomes .prev only after rename.
            previous = _quoted(target, names.previous)
            checks.append(f"test ! -e {previous}\ntest ! -L {previous}")
            continue
        copied = _quoted(target, names.previous if entry.existed else names.absent)
        variable = prepared[entry.relative]
        owned = [
            f"test -f {copied}\ntest ! -L {copied}",
            f'test "$(identity {copied})" = "${variable}"',
        ]
        if not entry.existed:
            owned.append(f'test "$(cat {copied})" = {shlex.quote(manifest.deploy_id)}')
        checks.append(
            f'if [ -n "${variable}" ]; then\n'
            + "\n".join(owned)
            + f"\nelse\ntest ! -e {copied}\ntest ! -L {copied}\nfi"
        )
        cleanup.append(f'if [ -n "${variable}" ]; then rm -f {copied}; fi')
    # Validate the whole preparation before deleting any of it. A nonempty or
    # replaced batch, changed live path or foreign marker is retained for review.
    return "\n".join([*checks, *cleanup, f"rmdir {batch}"])


def _write_prepared_manifest(target: Target, manifest: Manifest, directory: str) -> str:
    """Fill copied-backup inodes inside the same shell that prepares and switches."""
    paths = [
        target.path_of(
            _siblings(entry.relative).previous
            if entry.existed
            else _siblings(entry.relative).absent
        )
        for entry in manifest.backups
    ]
    script = (
        "import json,os\nfrom pathlib import Path\n"
        f"record=json.loads({json.dumps(asdict(manifest))!r})\n"
        f"paths={paths!r}\n"
        "for entry,path in zip(record['backups'],paths,strict=True):\n"
        " info=os.stat(path)\n entry['inode']=f'{info.st_dev}:{info.st_ino}'\n"
        f"path=Path({_manifest_path(directory)!r})\n"
        "temporary=path.with_suffix('.json.next')\n"
        "temporary.write_text(json.dumps(record))\n"
        "temporary.replace(path)\n"
    )
    return shlex.join(["python3", "-c", script])


# The same portable hash runs here and on the target. Ignore interpreter caches:
# source and stage identity must not change merely because a tool was imported.
def source_digest(source: Path, ignored: tuple[str, ...] = ()) -> str:
    """Identity of artifact bytes, paths, modes and symbolic links on either machine."""
    if not source.exists() and not source.is_symlink():
        return "-"
    omitted = {*ignored, "__pycache__"}

    def entries(parent: Path) -> Iterator[Path]:
        for item in sorted(parent.iterdir()):
            if item.name in omitted:
                continue
            if item.suffix != ".pyc":
                yield item
            if not item.is_symlink() and item.is_dir():
                yield from entries(item)

    tree = source.is_dir()
    paths = entries(source) if tree else iter([source])
    result = hashlib.sha256()
    for item in paths:
        if not tree and (item.name in omitted or item.suffix == ".pyc"):
            continue
        relative = str(item.relative_to(source)) if tree else "."
        result.update(relative.encode() + b"\0")
        result.update(str(item.lstat().st_mode & 0o777).encode() + b"\0")
        if item.is_symlink():
            result.update(b"L" + os.readlink(item).encode())
        elif item.is_file():
            content = hashlib.sha256()
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    content.update(chunk)
            result.update(b"F" + content.digest())
        else:
            result.update(b"D")
    return result.hexdigest()


def staged_digests(target: Target, relatives: list[str]) -> dict[str, str]:
    """Read all completed .next hashes in one transport round trip."""
    script = (
        "from __future__ import annotations\nimport hashlib,json,os\nfrom pathlib import Path\n"
        + inspect.getsource(source_digest)
        + "\nprint(json.dumps({key:source_digest(Path(value)) for key,value in "
        + repr(
            {
                relative: target.path_of(_siblings(relative).next)
                for relative in relatives
            }
        )
        + ".items()}))"
    )
    return dict(json.loads(target.shell(shlex.join(["python3", "-c", script]))))


def publish(
    target: Target,
    artifacts: list[Artifact],
    *,
    deploy_id: str,
    on_switch: Callable[[], None] | None = None,
    after_switch: str = "",
    completed_uploads: dict[str, str] | None = None,
    on_uploaded: Callable[[str, str], None] | None = None,
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
    uploaded = completed_uploads or {}
    verified = staged_digests(target, list(uploaded)) if uploaded else {}
    for artifact in artifacts:
        names = _siblings(artifact.relative)
        if any(
            target.exists(path) for path in (names.previous, names.absent, names.failed)
        ):
            raise CutoverError(f"unresolved previous deployment: {artifact.relative}")
        expected = source_digest(artifact.source) if on_uploaded is not None else ""
        if (
            expected
            and uploaded.get(artifact.relative) == expected
            and verified.get(artifact.relative) == expected
        ):
            print(f"reused verified upload {artifact.relative}", flush=True)
            continue
        parent = _quoted(target, str(Path(artifact.relative).parent))
        target.shell(
            f"set -eu\nmkdir -p {parent}\nrm -rf {_quoted(target, names.next)}"
        )
        # The deploy used to say nothing until the very end: the upload is the
        # long part, so each artifact names itself as it starts and ends.
        size = _source_bytes(artifact.source)
        print(f"uploading {artifact.relative} ({_human(size)})", flush=True)
        started = time.monotonic()
        if artifact.source.is_dir():
            target.copy_in(artifact.source, names.next)
        else:
            target.copy_file_in(artifact.source, names.next)
        print(
            f"uploaded {artifact.relative} in {time.monotonic() - started:.1f}s",
            flush=True,
        )
        if on_uploaded is not None:
            # rsync success alone is not an integrity checkpoint.
            if (
                staged_digests(target, [artifact.relative]).get(artifact.relative)
                != expected
            ):
                raise CutoverError(
                    f"uploaded artifact digest mismatch: {artifact.relative}"
                )
            on_uploaded(artifact.relative, expected)
    public_inventory = [(item.relative, item.source.is_dir()) for item in artifacts]
    public_proof = public_assets.prepare(target, public_inventory)
    _same_filesystem(
        target,
        root,
        [target.path_of(str(Path(item.relative).parent)) for item in artifacts],
    )
    directory = str(Path(root) / deploy_id)
    live_paths = [target.path_of(item.relative) for item in artifacts]
    next_paths = [target.path_of(_siblings(item.relative).next) for item in artifacts]
    before = identities(target, [*live_paths, *next_paths])
    prepare: list[str] = []
    prepared: dict[str, str] = {}
    for index, (item, live_path) in enumerate(zip(artifacts, live_paths, strict=True)):
        names = _siblings(item.relative)
        if before[live_path] == "-":
            copied = _quoted(target, names.absent)
            command = f"printf '%s' {shlex.quote(deploy_id)} > {copied}"
        elif not item.source.is_dir():
            copied = _quoted(target, names.previous)
            command = f"cp -p {_quoted(target, item.relative)} {copied}"
        else:
            continue
        variable = f"prepared_{index}"
        prepared[item.relative] = variable
        # HUP/TERM are deferred until this command's actual inode is captured,
        # including a partial failed copy. No later connection guesses ownership.
        prepare.append(
            f"prepare_status=0\n{command} || prepare_status=$?\n"
            f"if [ -e {copied} ] || [ -L {copied} ]; then {variable}=$(identity {copied}); fi\n"
            'test "$prepare_status" = 0\ntest "$interrupted" = 0'
        )
    entries = tuple(
        Backup(
            item.relative,
            deploy_id,
            item.source.is_dir(),
            before[live_path] != "-",
            "",  # Filled by the same remote shell after its preparation/switch.
            before[next_path],
        )
        for item, live_path, next_path in zip(
            artifacts, live_paths, next_paths, strict=True
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
    preflight: list[str] = [_IDENTITY]
    for entry in entries:
        live = _quoted(target, entry.relative)
        preflight.append(
            f'test "$(identity {live})" = {shlex.quote(before[target.path_of(entry.relative)])}'
            if entry.existed
            else f"test ! -e {live}\ntest ! -L {live}"
        )
        for sibling in asdict(_siblings(entry.relative)).values():
            if sibling == _siblings(entry.relative).next:
                continue
            quoted = _quoted(target, sibling)
            preflight.append(f"test ! -e {quoted}\ntest ! -L {quoted}")
    discard = _discard_unswitched_preparation(
        target, manifest, directory, before, prepared, prior_id
    )
    script = (
        "set -eu\n"
        + _IDENTITY
        + "\npreparing=1\ninterrupted=0\nbatch_inode=\n"
        + "\n".join(f"{variable}=" for variable in prepared.values())
        + "\nrestore_all() {\ntrap - EXIT HUP INT TERM\nset +e\n"
        + 'if [ "$preparing" = 1 ]; then\n( set -eu\n'
        + discard
        + "\n)\nreturn\nfi\n"
        + "\n".join(restore)
        + "\n}\ntrap restore_all EXIT\ntrap 'interrupted=1' HUP INT TERM\n"
        + "\n".join(preflight)
        + f"\ntest ! -e {shlex.quote(directory)}\ntest ! -L {shlex.quote(directory)}\n"
        + f"mkdir {shlex.quote(directory)}\nbatch_inode=$(identity {shlex.quote(directory)})\n"
        + 'test "$interrupted" = 0\n'
        + "\n".join(prepare)
        + "\nif ! "
        + "{ "
        + (public_assets.check_script(target, public_inventory, public_proof) or ":")
        + " && "
        + (
            planner_contracts.check_script(
                target,
                [
                    (item.relative, target.path_of(_siblings(item.relative).next))
                    for item in artifacts
                ],
            )
            or ":"
        )
        + "; }"
        + "; then\nexit 1\nfi\n"
        + "trap 'exit 1' HUP INT TERM\ntest \"$interrupted\" = 0\npreparing=0\n"
    )
    script += (
        "TIMEFORMAT='LINKER_CUTOVER_SWITCH_SECONDS=%R'\n{ time {\n"
        + "\n".join(switch)
        + "\n}; } 2>&1\n"
    )
    script += (
        _write_prepared_manifest(target, manifest, directory)
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


def reconcile_pending(target: Target) -> tuple[str, ...]:
    """Re-point a pending manifest at the backup siblings actually on disk.

    The switch renames live -> .prev, so each recorded backup identity should
    survive. It does not when something rewrote the host copy while the batch
    stayed pending (an interrupted earlier batch, or a tool that copies the
    directory instead of renaming it): the switch did finish -- live carries the
    uploaded identity -- but rollback preflight then refuses to touch a batch it
    cannot name. Only that proof of a completed switch admits the correction;
    the backup identities are re-read and nothing else changes.
    """
    directory, manifest = latest_manifest(target)
    if manifest.state != "pending":
        raise CutoverError(f"deployment {manifest.deploy_id} is {manifest.state}")
    live_paths = [target.path_of(entry.relative) for entry in manifest.backups]
    live = identities(target, live_paths)
    problems = [
        f"{entry.relative}: live {live[path]} is not the uploaded {entry.new_inode}"
        for entry, path in zip(manifest.backups, live_paths, strict=True)
        if live[path] != entry.new_inode
    ]
    if problems:
        raise CutoverError("reconcile refused: " + "; ".join(problems))
    backup_paths = [
        _backup_path(target, directory, manifest, entry) for entry in manifest.backups
    ]
    actual = identities(target, backup_paths)
    entries = tuple(
        replace(entry, inode=actual[path])
        for entry, path in zip(manifest.backups, backup_paths, strict=True)
    )
    changed = tuple(
        entry.relative
        for entry, old in zip(entries, manifest.backups, strict=True)
        if entry.inode != old.inode
    )
    if changed:
        target.shell(
            "set -eu\n"
            + _write_manifest(
                Manifest(manifest.deploy_id, "pending", entries), directory
            )
        )
    return changed


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
    if manifest.deploy_id != receipt.deploy_id:
        raise CutoverError("archive requires the pending deployment receipt")
    if manifest.state == "archived":
        _finalize_archive(target, receipt)
        return
    if manifest.state != "pending":
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
    _finalize_archive(target, receipt)


def _finalize_archive(target: Target, receipt: Receipt) -> None:
    """Read back the committed archive and retire old batches, also after a lost reply."""
    directory, manifest, _ = _checked_backups(target, list(receipt.paths))
    if manifest.deploy_id != receipt.deploy_id or manifest.state != "archived":
        raise CutoverError("archive finalization requires the archived deployment")
    live = identities(target, [target.path_of(path) for path in receipt.paths])
    if any(
        live[target.path_of(entry.relative)] != entry.new_inode
        for entry in manifest.backups
    ):
        raise CutoverError("live changed since deploy; checkpoint retained")
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
        planner_contracts.check_script(
            target,
            [
                (entry.relative, path if entry.existed else None)
                for entry, path in zip(manifest.backups, paths, strict=True)
            ],
        )
        or ":"
    ) + "\n"
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
