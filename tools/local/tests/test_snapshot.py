from pathlib import Path

import pytest

from linker_local import snapshot
from linker_local.instance import Instance
from linker_local.snapshot import SnapshotError


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def instance(tmp_path: Path) -> Instance:
    built = Instance("a", 1, 2, 3, tmp_path / "home")
    (built.wp_content / "plugins").mkdir(parents=True)
    (built.wp_content / "uploads").mkdir()
    return built


def test_installs_the_plugins_and_uploads_of_a_snapshot(
    tmp_path: Path, instance: Instance
) -> None:
    taken = tmp_path / "20261010-0900"
    write(taken / "plugins" / "livecanvas" / "livecanvas.php", "<?php // 4.9.3")
    write(taken / "plugins" / "windpress" / "windpress.php", "<?php")
    write(taken / "uploads" / "2026" / "10" / "datasheet.pdf", "pdf")

    slugs = snapshot.install(instance, taken)

    assert slugs == ["livecanvas", "windpress"]
    plugins = instance.wp_content / "plugins"
    assert (plugins / "livecanvas" / "livecanvas.php").read_text() == "<?php // 4.9.3"
    assert (
        instance.wp_content / "uploads" / "2026" / "10" / "datasheet.pdf"
    ).read_text() == "pdf"


def test_a_plugin_from_a_newer_snapshot_replaces_the_installed_one(
    tmp_path: Path, instance: Instance
) -> None:
    write(
        instance.wp_content / "plugins" / "livecanvas" / "removed-in-4.9.4.php", "<?php"
    )
    write(instance.wp_content / "uploads" / "kept.jpg", "jpg")
    taken = tmp_path / "snapshot"
    write(taken / "plugins" / "livecanvas" / "livecanvas.php", "<?php // 4.9.4")
    write(taken / "uploads" / "new.jpg", "jpg")

    snapshot.install(instance, taken)

    plugin = instance.wp_content / "plugins" / "livecanvas"
    assert sorted(path.name for path in plugin.iterdir()) == ["livecanvas.php"]
    uploads = sorted(path.name for path in (instance.wp_content / "uploads").iterdir())
    assert uploads == ["kept.jpg", "new.jpg"]


def test_our_plugins_never_come_from_a_snapshot(
    tmp_path: Path, instance: Instance
) -> None:
    write(
        tmp_path / "snapshot" / "plugins" / "linker-i18n" / "linker-i18n.php", "<?php"
    )

    with pytest.raises(SnapshotError, match="checkout"):
        snapshot.install(instance, tmp_path / "snapshot")


def test_a_directory_without_plugins_or_uploads_is_not_a_snapshot(
    tmp_path: Path, instance: Instance
) -> None:
    with pytest.raises(SnapshotError, match="neither"):
        snapshot.install(instance, tmp_path)
