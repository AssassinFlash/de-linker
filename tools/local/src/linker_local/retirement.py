"""Explicit, resumable retirement of one owner-released local test instance."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import objectcache, server, services
from .checkout import Checkout
from .engine_release import engine_project
from .instance import Instance, check_name
from .mysql import CREDENTIALS, MySQL
from .planner_worker import PlannerWorker
from .private_config import lifecycle_lock, publish_once
from .processes import Background, port_is_free
from .registry import Registry


def lock_path(root: Path, name: str) -> Path:
    check_name(name)
    # Never unlink these small lock files: a waiting caller must retain the
    # same inode even after the instance directory has been removed.
    return root / ".lifecycle" / f"{name}.lock"


def marker_path(root: Path, name: str) -> Path:
    check_name(name)
    return root / ".lifecycle" / f"{name}.retiring.json"


def require_available(root: Path, name: str) -> None:
    if marker_path(root, name).exists():
        raise RuntimeError(
            f"{name} retirement is incomplete; resume `just retire {name} --write`"
        )


@contextmanager
def available(root: Path, name: str) -> Iterator[None]:
    """Hold one instance generation for the complete local operator action."""
    with lifecycle_lock(lock_path(root, name)):
        require_available(root, name)
        yield


def evidence(instance: Instance) -> list[Path]:
    """Candidate unique bytes; operator must transfer or explicitly discard them.

    WordPress code may contain local edits or unexpected files, so it requires
    the same explicit decision as other instance bytes. Runtime controls are
    reproducible. Shared symlink targets are never traversed or deleted.
    """
    rebuildable = {
        "run",
        "php.ini",
        "router.php",
        "admin.txt",
        ".provisioned",
    }
    roots = (
        [p for p in instance.dir.iterdir() if p.name not in rebuildable]
        if instance.dir.exists()
        else []
    )
    result = []
    for root in roots:
        if root.is_symlink() or root.is_file():
            result.append(root.relative_to(instance.dir))
        else:
            result.extend(
                p.relative_to(instance.dir)
                for p in root.rglob("*")
                if p.is_file() or p.is_symlink()
            )
    return sorted(result)


def _relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or path == Path("."):
        raise ValueError(f"expected an instance-relative evidence path: {value}")
    return path


def _covers(path: Path, choices: list[Path]) -> bool:
    return any(path == choice or path.is_relative_to(choice) for choice in choices)


def retire(
    root: Path,
    name: str,
    *,
    write: bool,
    preserve: list[str],
    discard: list[str],
    preserve_to: Path | None,
) -> dict[str, object]:
    """Plan without writes; explicit write serialises against up/reset/serve."""
    check_name(name)
    if not write:
        return _retire(root, name, False, preserve, discard, preserve_to)
    with lifecycle_lock(lock_path(root, name)):
        return _retire(root, name, True, preserve, discard, preserve_to)


def _record_decision(path: Path, note: dict[str, object]) -> None:
    """Atomically append an owner's decisions to the existing small journal."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix="." + path.name + ".incoming-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(note, indent=2).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _retire(
    root: Path,
    name: str,
    write: bool,
    preserve: list[str],
    discard: list[str],
    preserve_to: Path | None,
) -> dict[str, object]:
    registry = Registry(root)
    marker = marker_path(root, name)
    instance = registry.get(name)
    if marker.exists():
        note = json.loads(marker.read_bytes())
        retained = Instance(
            name, note["port"], note["engine_port"], note["genie_port"], root
        )
        if instance not in (None, retained):
            raise RuntimeError("registration changed; retirement stopped")
        instance = retained
        previous_destination = (
            Path(note["preserve_to"]) if note["preserve_to"] else None
        )
        if previous_destination is not None:
            if (
                preserve_to is not None
                and preserve_to.resolve() != previous_destination
            ):
                raise ValueError(
                    "the preserved evidence destination cannot change during retirement"
                )
            preserve_to = previous_destination
        # New files can appear during drain. Retain every previous decision,
        # allowing the owner to explicitly append decisions for those files.
        preserve = list(dict.fromkeys([*note["preserve"], *preserve]))
        discard = list(dict.fromkeys([*note["discard"], *discard]))
    if instance is None:
        if (root / name).exists() or MySQL(CREDENTIALS).database_exists(
            "linker_" + name
        ):
            raise RuntimeError(
                "unregistered resources have unknown ownership; refusing retirement"
            )
        return {"name": name, "status": "already retired"}
    if instance.dir.is_symlink() or instance.dir.resolve().parent != root.resolve():
        raise RuntimeError("instance directory is outside its registered root")
    # A directory decision already covers its children. Moving a child first
    # otherwise creates the destination that prevents the later parent move.
    keep = sorted(
        set(_relative(p) for p in preserve), key=lambda p: (len(p.parts), str(p))
    )
    keep = [p for index, p in enumerate(keep) if not _covers(p, keep[:index])]
    drop = [_relative(p) for p in discard]
    if any(_covers(p, drop) for p in keep) or any(_covers(p, keep) for p in drop):
        raise ValueError("preserve and discard paths overlap")
    candidates = evidence(instance)
    unconfirmed = [str(p) for p in candidates if not _covers(p, keep + drop)]
    plan: dict[str, object] = {
        "name": name,
        "directory": str(instance.dir),
        "database": instance.database,
        "redis_prefix": objectcache.prefix(instance),
        "evidence": [str(p) for p in candidates],
        "unconfirmed": unconfirmed,
        "preserve": preserve,
        "discard": discard,
        "preserve_to": str(preserve_to) if preserve_to else None,
        "status": "plan",
    }
    if not write:
        return plan
    if unconfirmed:
        raise RuntimeError(
            "confirm evidence with --preserve or --discard: " + ", ".join(unconfirmed)
        )
    destination = preserve_to.resolve() if preserve_to else None
    if keep and (destination is None or destination.is_relative_to(root.resolve())):
        raise ValueError("--preserve-to must be outside the local instance root")
    for path in keep:
        source = instance.dir / path
        # A parent symlink could redirect a move outside the owned instance.
        if (
            source.parent.resolve() != instance.dir.resolve()
            and not source.parent.resolve().is_relative_to(instance.dir.resolve())
        ):
            raise ValueError("evidence parent is outside the instance")
        if (
            destination
            and ((destination / path).exists() or (destination / path).is_symlink())
            and (source.exists() or source.is_symlink())
        ):
            raise RuntimeError(
                f"evidence destination already exists: {destination / path}"
            )
    # Close numerical admission while preserving PHP/Woo and engine HTTP:
    # in-flight workers still need current publication permission and sources.
    if (
        not (instance.dir / "planner/runtime.json").exists()
        and Background(
            instance.run_dir / "planner-worker.pid",
            instance.log_dir / "planner-worker.log",
        ).pid()
        is not None
    ):
        raise RuntimeError(
            "live planning worker has no runtime policy; resources preserved"
        )
    had_marker = marker.exists()
    worker: PlannerWorker | None = None
    was_draining = True
    try:
        if (instance.dir / "planner/runtime.json").exists():
            checkout = Checkout.here()
            worker = PlannerWorker(
                instance,
                engine_project(instance, checkout.service("engine")),
                services._uv(),
                checkout=checkout,
            )
            was_draining = worker.control("status")["draining"] is True
            worker.drain()
        decision: dict[str, object] = {
            "port": instance.port,
            "engine_port": instance.engine_port,
            "genie_port": instance.genie_port,
            "preserve": [str(p) for p in keep],
            "discard": discard,
            "preserve_to": str(destination) if destination else None,
        }
        if not marker.exists():
            publish_once(marker, decision)
        elif json.loads(marker.read_bytes()) != decision:
            _record_decision(marker, decision)
    except BaseException as error:
        # Nothing has stopped or moved. A refusal must leave normal recovery
        # available, preserving the caller's original admission choice.
        if worker is not None and not was_draining:
            try:
                worker.control("resume")
            except BaseException as recovery:
                error.add_note("planning admission recovery failed: " + repr(recovery))
        if not had_marker:
            try:
                marker.unlink(missing_ok=True)
            except OSError as recovery:
                error.add_note(
                    "retirement preparation cleanup failed: " + repr(recovery)
                )
        raise
    # From this point the persisted decision owns a resumable retirement. Stop
    # the pair before its PHP dependency, then inventory the now-frozen files.
    if instance.dir.exists():
        services.stop(instance)
    server.stop(instance)
    if any(
        not port_is_free(port)
        for port in (instance.port, instance.engine_port, instance.genie_port)
    ):
        raise RuntimeError("registered port still in use; resources preserved")
    mysql = MySQL(CREDENTIALS)
    if mysql.query(
        f"SELECT ID FROM information_schema.PROCESSLIST WHERE DB = '{instance.database}'"
    ).strip():
        raise RuntimeError(
            "instance database still has connections; resources preserved"
        )
    unconfirmed = [str(p) for p in evidence(instance) if not _covers(p, keep + drop)]
    if unconfirmed:
        raise RuntimeError(
            "new evidence appeared while draining; preserved resources: "
            + ", ".join(unconfirmed)
        )
    for path in keep:
        source = instance.dir / path
        assert destination is not None
        target = destination / path
        if source.exists() or source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Atomic same-filesystem handoff; never clone a whole snapshot or
            # follow links. A different filesystem must be handled explicitly.
            os.rename(source, target)
        elif not (target.exists() or target.is_symlink()):
            raise RuntimeError(f"preserved evidence is missing: {path}")
    mysql.drop_database(instance.database)
    if mysql.database_exists(instance.database):
        raise RuntimeError("database removal did not read back")
    if instance.dir.exists():
        shutil.rmtree(instance.dir)
    registry.unregister(instance)

    def permitted() -> bool:
        return registry.get(name) is None and not instance.dir.exists()

    removed = objectcache.forget(instance, permitted=permitted)
    # A second bounded pass is the post-delete readback, not a sampled first
    # cursor: MATCH can return empty batches while later cursors contain keys.
    if objectcache.forget(instance, permitted=permitted):
        raise RuntimeError(
            "cache changed after retirement; retry to verify no residual keys"
        )
    marker.unlink()
    plan.update(status="retired", redis_keys_removed=removed)
    return plan
