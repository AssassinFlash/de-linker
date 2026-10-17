"""Files from a snapshot of the production site: plugins, themes and uploads.

Ticket #6 writes the snapshot; this module installs the files it holds, and
#6's `load` reuses it next to its own database import:

    <snapshot>/plugins/<slug>/   a plugin directory, as in wp-content/plugins
    <snapshot>/themes/<slug>/    a theme directory, as in wp-content/themes
    <snapshot>/uploads/          wp-content/uploads
    <snapshot>/live/plugins/     the live site's other plugins: the third-party
                                 ones always, linker-* only with live_code
    <snapshot>/live/mu-plugins/  the live site's must-use plugins (only live_code)

Plugins and themes replace the instance's directories of the same name;
uploads are merged in. The live site's third-party plugins (User Switching,
Polylang, ACF and the rest of live/plugins that is not linker-*) install
always, at the live version: a local instance must look like live
(AGENTS.md 2026-10-17, #252), and on 2026-10-17 an instance without them ran
Polylang 3.8.10 against live's 3.8.11 and had no User Switching at all.
Which theme is active is the database's business. Which plugins activate is the snapshot's site/plugins.json business: a
plugin the live site ran is active locally too (the local instance must
look like live, AGENTS.md 2026-10-10); without the file every snapshot
plugin activates (a test fixture's default).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from linker_local.instance import Instance

# Our plugins' prefix: a checkout provides them, a snapshot only with live_code.
OURS = "linker-"


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
        if source.name.startswith(OURS):
            raise SnapshotError(
                f"{source}: linker-* plugins come from the checkout, not from a snapshot"
            )


def install(instance: Instance, snapshot: Path, live_code: bool = False) -> list[str]:
    """Copy the snapshot's files into the instance; return the plugin slugs.

    The live site's third-party plugins (live/plugins without linker-*)
    replace the same-named ones and count as snapshot plugins. live_code also
    installs the rest of the live/ trees, whose only consumer is
    linker-pull's `load --live-code` (a local copy of the live site, #6):
    the live linker-* plugins and the must-use plugins, each entry replacing
    the same-named one. `up --snapshot` never passes live_code, so an
    instance's linker-* plugins keep coming from its checkout.
    """
    check(snapshot)
    plugins, themes, uploads = (
        snapshot / part for part in ("plugins", "themes", "uploads")
    )
    slugs = [
        _replace(source, instance.wp_content / "plugins")
        for source in _directories(plugins)
    ]
    slugs += [
        _replace(source, instance.wp_content / "plugins")
        for source in _directories(snapshot / "live" / "plugins")
        if not source.name.startswith(OURS)
    ]
    active = _active_slugs(snapshot / "site" / "plugins.json")
    if active is not None:
        slugs = [slug for slug in slugs if slug in active]
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


def _active_slugs(manifest: Path) -> set[str] | None:
    """The plugin slugs the snapshot's site ran active; None without the file.

    plugins.json is what the live site's `wp plugin list --format=json`
    answered (#6): each entry carries name/status/file, and the live-active
    set is the parity set a local instance must run.
    """
    try:
        entries = json.loads(manifest.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(entries, list):
        return None
    return {
        entry["name"]
        for entry in entries
        if isinstance(entry, dict) and entry.get("status") == "active"
    }


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
