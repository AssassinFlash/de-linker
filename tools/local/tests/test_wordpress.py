from pathlib import Path

import pytest

from linker_local import wordpress
from linker_local.checkout import Checkout
from linker_local.instance import Instance


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def checkout(tmp_path: Path) -> Checkout:
    root = tmp_path / "checkout"
    for plugin in ("linker-commerce", "linker-tools"):
        write(root / "plugins" / plugin / f"{plugin}.php", "<?php")
    write(root / "plugins" / "README.md")  # not a plugin directory
    write(
        root / "tools" / "local" / "mu" / "000-linker-local-isolation.php",
        "<?php // new",
    )
    return Checkout(root)


@pytest.fixture
def instance(tmp_path: Path) -> Instance:
    built = Instance("a", 8888, 8889, 8890, tmp_path / "home")
    (built.wp_content / "plugins").mkdir(parents=True)
    return built


def test_links_our_plugins_to_the_checkout(
    checkout: Checkout, instance: Instance
) -> None:
    linked = wordpress.link_plugins(instance, checkout)

    assert linked == ["linker-commerce", "linker-tools"]
    link = instance.wp_content / "plugins" / "linker-tools"
    assert link.is_symlink()
    assert link.resolve() == (checkout.root / "plugins" / "linker-tools").resolve()
    assert wordpress.linked_checkout(instance) == checkout.root


def test_linking_from_another_checkout_moves_the_links(
    tmp_path: Path, checkout: Checkout, instance: Instance
) -> None:
    wordpress.link_plugins(instance, checkout)
    other = tmp_path / "other"
    write(other / "plugins" / "linker-commerce" / "linker-commerce.php", "<?php")

    wordpress.link_plugins(instance, Checkout(other))

    assert wordpress.linked_checkout(instance) == other
    # linker-tools is not in the other checkout, so its old link goes.
    assert sorted(
        path.name for path in (instance.wp_content / "plugins").iterdir()
    ) == ["linker-commerce"]


def test_does_not_replace_a_real_plugin_directory(
    checkout: Checkout, instance: Instance
) -> None:
    write(
        instance.wp_content / "plugins" / "linker-tools" / "linker-tools.php",
        "<?php // old",
    )

    with pytest.raises(RuntimeError, match="not a link"):
        wordpress.link_plugins(instance, checkout)


def test_mu_plugins_are_copied_and_renamed_ones_removed(
    checkout: Checkout, instance: Instance
) -> None:
    mu = instance.wp_content / "mu-plugins"
    write(mu / "001-linker-local-old-name.php", "<?php // renamed since")
    write(mu / "000-linker-local-isolation.php", "<?php // old")
    write(mu / "host-plugin.php", "<?php // not ours")

    wordpress.install_mu_plugins(instance, checkout)

    assert sorted(path.name for path in mu.iterdir()) == [
        "000-linker-local-isolation.php",
        "host-plugin.php",
    ]
    assert (mu / "000-linker-local-isolation.php").read_text() == "<?php // new"
    assert not (mu / "000-linker-local-isolation.php").is_symlink()


def test_wp_config_names_the_instance_and_its_directory(instance: Instance) -> None:
    extra = wordpress.wp_config_constants(instance)

    assert "define( 'WP_HOME', 'http://127.0.0.1:8888' );" in extra
    assert "define( 'WP_SITEURL', 'http://127.0.0.1:8888' );" in extra
    assert "define( 'WP_ENVIRONMENT_TYPE', 'local' );" in extra
    assert "define( 'DISABLE_WP_CRON', true );" in extra
    assert f"define( 'LINKER_LOCAL_MAIL_DIR', '{instance.mail_dir}' );" in extra
    assert (
        f"define( 'LINKER_LOCAL_ISOLATION_LOG', '{instance.isolation_log}' );" in extra
    )
    for salt in wordpress.SALTS:
        assert f"define( '{salt}', '" in extra
    assert "define( 'WP_REDIS_PREFIX', 'linker_a:' );" in extra
    assert "define( 'WP_REDIS_SELECTIVE_FLUSH', true );" in extra


def test_reads_the_installed_versions(instance: Instance) -> None:
    write(
        instance.docroot / "wp-includes" / "version.php",
        "<?php\n$wp_version = '7.1.3';\n",
    )
    write(
        instance.wp_content / "plugins" / "woocommerce" / "woocommerce.php",
        "<?php\n/**\n * Plugin Name: WooCommerce\n * Version: 11.2.0\n */\n",
    )
    write(
        instance.wp_content / "plugins" / "redis-cache" / "redis-cache.php",
        "<?php\n/**\n * Plugin Name: Redis Object Cache\n * Version: 3.0.0\n */\n",
    )
    write(
        instance.wp_content / "plugins" / "polylang" / "polylang.php",
        "<?php\n/**\n * Plugin Name: Polylang\n * Version: 3.8.10\n */\n",
    )

    assert wordpress.versions(instance) == wordpress.PINNED


def test_reads_no_versions_from_an_empty_instance(instance: Instance) -> None:
    assert set(wordpress.versions(instance).values()) == {None}
