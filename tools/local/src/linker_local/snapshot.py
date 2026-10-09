"""Files from a snapshot of the production site: plugins, themes and uploads.

Ticket #6 writes the snapshot; this module installs the files it holds, and
#6's `load` reuses it next to its own database import:

    <snapshot>/plugins/<slug>/   a plugin directory, as in wp-content/plugins
    <snapshot>/themes/<slug>/    a theme directory, as in wp-content/themes
    <snapshot>/uploads/          wp-content/uploads
    <snapshot>/live/plugins/     the live site's other plugins (only live_code)
    <snapshot>/live/mu-plugins/  the live site's must-use plugins (only live_code)

Plugins and themes replace the instance's directories of the same name;
uploads are merged in. Which theme is active is the database's business.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from linker_local.instance import Instance


class SnapshotError(RuntimeError):
    """The directory is not a snapshot this module can install."""


def check(snapshot: Path) -> None:
    """Raise SnapshotError unless `snapshot` is a directory install() can use.

    `up` and `reset` call it first, so a mistyped path fails before an
    instance is built or deleted.
    """
    parts = [snapshot / part for part in ("plugins", "themes", "uploads")]
    if not any(part.is_dir() for part in parts):
        raise SnapshotError(f"{snapshot} has none of plugins/, themes/, uploads/")
    for source in _directories(snapshot / "plugins"):
        if source.name.startswith("linker-"):
            raise SnapshotError(
                f"{source}: linker-* plugins come from the checkout, not from a snapshot"
            )


def install(instance: Instance, snapshot: Path, live_code: bool = False) -> list[str]:
    """Copy the snapshot's files into the instance; return the plugin slugs.

    live_code also installs the live/ trees, whose only consumer is
    linker-pull's `load --live-code` (a local copy of the live site, #6):
    the live site's other plugins and its must-use plugins, each entry
    replacing the same-named one. `up --snapshot` never passes live_code, so
    an instance's linker-* plugins keep coming from its checkout.
    """
    check(snapshot)
    plugins, themes, uploads = (
        snapshot / part for part in ("plugins", "themes", "uploads")
    )
    slugs = [
        _replace(source, instance.wp_content / "plugins")
        for source in _directories(plugins)
    ]
    for source in _directories(themes):
        _replace(source, instance.wp_content / "themes")
    if uploads.is_dir():
        shutil.copytree(
            uploads, instance.wp_content / "uploads", symlinks=True, dirs_exist_ok=True
        )
    if live_code:
        _replace_entries(snapshot / "live" / "plugins", instance.wp_content / "plugins")
        _replace_entries(
            snapshot / "live" / "mu-plugins", instance.wp_content / "mu-plugins"
        )
    return slugs


def _directories(parent: Path) -> list[Path]:
    return (
        sorted(path for path in parent.iterdir() if path.is_dir())
        if parent.is_dir()
        else []
    )


def _replace(source: Path, parent: Path) -> str:
    """Copy `source` to parent/<its name>, removing what was there; return the name."""
    target = parent / source.name
    if target.is_symlink():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)
    return source.name


def _replace_entries(source: Path, target: Path) -> None:
    """Every entry of `source` (a directory or a file) replaces the same-named
    entry of `target` (a link included); what only `target` has stays."""
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
            shutil.copytree(entry, destination, symlinks=True)
        else:
            shutil.copy2(entry, destination)
