"""Files from a snapshot of the production site: its licensed plugins and its uploads.

Ticket #6 writes the snapshot; this module installs the files it holds:

    <snapshot>/plugins/<slug>/   a plugin directory, as in wp-content/plugins
    <snapshot>/uploads/          wp-content/uploads

`linker-local up <name> --snapshot <dir>` calls it; the snapshot's database
is #6's to load.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from linker_local.instance import Instance


class SnapshotError(RuntimeError):
    """The directory is not a snapshot this module can install."""


def install(instance: Instance, snapshot: Path) -> list[str]:
    """Copy the snapshot's plugins and uploads into the instance; return the plugin slugs."""
    plugins = snapshot / "plugins"
    uploads = snapshot / "uploads"
    if not plugins.is_dir() and not uploads.is_dir():
        raise SnapshotError(f"{snapshot} has neither plugins/ nor uploads/")
    slugs: list[str] = []
    if plugins.is_dir():
        for source in sorted(path for path in plugins.iterdir() if path.is_dir()):
            if source.name.startswith("linker-"):
                raise SnapshotError(
                    f"{source}: linker-* plugins come from the checkout, not from a snapshot"
                )
            target = instance.wp_content / "plugins" / source.name
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, symlinks=True)
            slugs.append(source.name)
    if uploads.is_dir():
        shutil.copytree(
            uploads, instance.wp_content / "uploads", symlinks=True, dirs_exist_ok=True
        )
    return slugs
