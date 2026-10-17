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
    for part in ("plugins", "themes", "uploads"):
        (built.wp_content / part).mkdir(parents=True)
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


def test_only_the_plugins_the_site_ran_active_activate(
    tmp_path: Path, instance: Instance
) -> None:
    taken = tmp_path / "20261010-0033"
    write(taken / "plugins" / "livecanvas" / "livecanvas.php", "<?php")
    write(taken / "plugins" / "windpress" / "windpress.php", "<?php")
    write(taken / "plugins" / "wp-seopress" / "wp-seopress.php", "<?php")
    write(
        taken / "site" / "plugins.json",
        '[{"name": "livecanvas", "status": "active", "file": "livecanvas/livecanvas.php"},'
        ' {"name": "windpress", "status": "inactive", "file": "windpress/windpress.php"},'
        ' {"name": "wp-seopress", "status": "active", "file": "wp-seopress/wp-seopress.php"}]',
    )

    slugs = snapshot.install(instance, taken)

    # The files all arrive; only what the live site ran active activates
    # (a local instance must look like live, AGENTS.md 2026-10-10).
    assert slugs == ["livecanvas", "wp-seopress"]
    assert (instance.wp_content / "plugins" / "windpress" / "windpress.php").exists()


def test_a_snapshot_without_the_manifest_activates_every_plugin(
    tmp_path: Path, instance: Instance
) -> None:
    taken = tmp_path / "fixture"
    write(taken / "plugins" / "snapshot-fixture" / "snapshot-fixture.php", "<?php")

    slugs = snapshot.install(instance, taken)

    assert slugs == ["snapshot-fixture"]


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


def test_installs_themes_and_leaves_choosing_one_to_the_database(
    tmp_path: Path, instance: Instance
) -> None:
    write(instance.wp_content / "themes" / "picostrap5-child-base" / "old.css", "")
    taken = tmp_path / "snapshot"
    write(taken / "themes" / "picostrap5" / "style.css", "/* Theme Name: picostrap5 */")
    write(taken / "themes" / "picostrap5-child-base" / "style.css", "/* child */")

    slugs = snapshot.install(instance, taken)

    assert slugs == []  # nothing to activate: themes are not plugins
    themes = instance.wp_content / "themes"
    assert (themes / "picostrap5" / "style.css").exists()
    assert sorted(
        path.name for path in (themes / "picostrap5-child-base").iterdir()
    ) == ["style.css"]


def test_our_plugins_never_come_from_a_snapshot(
    tmp_path: Path, instance: Instance
) -> None:
    write(
        tmp_path / "snapshot" / "plugins" / "linker-i18n" / "linker-i18n.php", "<?php"
    )

    with pytest.raises(SnapshotError, match="checkout"):
        snapshot.install(instance, tmp_path / "snapshot")


def test_the_live_third_party_plugins_install_at_the_live_version(
    tmp_path: Path, instance: Instance
) -> None:
    """User Switching was on live and on no instance; Polylang ran 3.8.10
    locally against live's 3.8.11 (2026-10-17, #252): the live site's
    third-party plugins come with every snapshot, ours stay the checkout's."""
    write(instance.wp_content / "plugins" / "polylang" / "polylang.php", "<?php 3.8.10")
    taken = tmp_path / "snapshot"
    write(taken / "uploads" / "2026" / "logo.webp", "webp")
    write(taken / "live" / "plugins" / "polylang" / "polylang.php", "<?php 3.8.11")
    write(taken / "live" / "plugins" / "user-switching" / "user-switching.php", "<?php")
    write(
        taken / "live" / "plugins" / "hostinger-reach" / "hostinger-reach.php", "<?php"
    )
    write(
        taken / "live" / "plugins" / "linker-tools" / "linker-tools.php", "<?php live"
    )
    write(
        taken / "site" / "plugins.json",
        '[{"name": "polylang", "status": "active"},'
        ' {"name": "user-switching", "status": "active"},'
        ' {"name": "hostinger-reach", "status": "inactive"},'
        ' {"name": "linker-tools", "status": "active"}]',
    )

    slugs = snapshot.install(instance, taken)

    plugins = instance.wp_content / "plugins"
    assert slugs == ["polylang", "user-switching"]
    assert (plugins / "polylang" / "polylang.php").read_text() == "<?php 3.8.11"
    assert (plugins / "user-switching" / "user-switching.php").is_file()
    assert (plugins / "hostinger-reach").is_dir()  # installed, as inactive as on live
    assert not (plugins / "linker-tools").exists()


def test_live_code_installs_the_live_trees_without_it_it_does_not(
    tmp_path: Path, instance: Instance
) -> None:
    """The live/ trees are linker-pull's `load --live-code` (a copy of the live
    site): its plugins (linker-* among them) and its must-use plugin files."""
    write(instance.wp_content / "plugins" / "old-custom" / "gone.php", "<?php old")
    write(instance.wp_content / "mu-plugins" / "a-local-mu.php", "<?php stays")
    taken = tmp_path / "snapshot"
    write(taken / "uploads" / "2026" / "logo.webp", "webp")
    write(taken / "live" / "plugins" / "linker-i18n" / "linker-i18n.php", "<?php new")
    write(taken / "live" / "mu-plugins" / "old-loader.php", "<?php new")

    snapshot.install(instance, taken)  # without live_code the live trees wait

    plugins = instance.wp_content / "plugins"
    assert not (plugins / "linker-i18n").exists()
    assert (plugins / "old-custom" / "gone.php").read_text() == "<?php old"
    mu = instance.wp_content / "mu-plugins"
    assert not (mu / "old-loader.php").exists()
    assert (mu / "a-local-mu.php").is_file()

    snapshot.install(instance, taken, live_code=True)

    assert (plugins / "linker-i18n" / "linker-i18n.php").read_text() == "<?php new"
    assert (mu / "old-loader.php").read_text() == "<?php new"
    assert (mu / "a-local-mu.php").is_file()


def test_live_code_replaces_same_named_plugins_and_mu_files(
    tmp_path: Path, instance: Instance
) -> None:
    write(instance.wp_content / "plugins" / "old-custom" / "gone.php", "<?php old")
    write(instance.wp_content / "mu-plugins" / "old-loader.php", "<?php old")
    taken = tmp_path / "snapshot"
    write(taken / "uploads" / "2026" / "logo.webp", "webp")
    write(taken / "live" / "plugins" / "old-custom" / "replaced.php", "<?php new")
    write(taken / "live" / "mu-plugins" / "old-loader.php", "<?php new")

    snapshot.install(instance, taken, live_code=True)

    plugins = instance.wp_content / "plugins"
    assert sorted(path.name for path in (plugins / "old-custom").iterdir()) == [
        "replaced.php"
    ]
    assert (instance.wp_content / "mu-plugins" / "old-loader.php").read_text() == (
        "<?php new"
    )


def test_a_directory_without_plugins_or_uploads_is_not_a_snapshot(
    tmp_path: Path, instance: Instance
) -> None:
    with pytest.raises(SnapshotError, match="none of"):
        snapshot.install(instance, tmp_path)
