"""Building an instance: WordPress, WooCommerce, our plugins and the local mu-plugins.

`provision()` makes a new instance; `refresh()` brings an existing one up to
the files of the checkout that runs it. Every `up` calls one of the two.
"""

from __future__ import annotations

import re
import secrets
import shutil
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from linker_local import downloads, server, snapshot
from linker_local.checkout import Checkout
from linker_local.instance import SHARED, Instance
from linker_local.mysql import USER, MySQL
from linker_local.wpcli import WpCli

# WordPress and WooCommerce as on the production host (WP-CLI over SSH,
# 2026-10-09; docs/research/2026-10-09/framework-choice.md §2).
WORDPRESS_VERSION = "7.1.3"
WORDPRESS_ZIP = "https://wordpress.org/wordpress-7.1.3.zip"
# Published next to the archive, https://wordpress.org/wordpress-7.1.3.zip.sha1
# (read via Apify on 2026-10-09).
WORDPRESS_SHA1 = "13eb1d042b1ca39224e44906cd84fe203112210c"
WOOCOMMERCE_VERSION = "11.1.0"
# The download link of 11.1.0 in the wordpress.org plugin API (read via Apify on
# 2026-10-09). wordpress.org publishes no hash of the archive; its files are
# checked one by one against wordpress.org's checksums (`wp plugin verify-checksums`).
WOOCOMMERCE_ZIP = "https://downloads.wordpress.org/plugin/woocommerce.11.1.0.zip"

ADMIN_USER = "local-admin"
# .test is reserved and never resolves to a real mailbox (RFC 6761 §6.2, read
# via Apify on 2026-10-09).
ADMIN_EMAIL = "local-admin@example.test"
# The production host's table prefix and permalink structure (wp-config.php and
# the permalink_structure option, read over SSH on 2026-10-09).
TABLE_PREFIX = "wp_"
PERMALINKS = "/%postname%/"

CACHE = SHARED / ".cache"
SALTS = (
    "AUTH_KEY",
    "SECURE_AUTH_KEY",
    "LOGGED_IN_KEY",
    "NONCE_KEY",
    "AUTH_SALT",
    "SECURE_AUTH_SALT",
    "LOGGED_IN_SALT",
    "NONCE_SALT",
)

Say = Callable[[str], None]


def provision(
    instance: Instance,
    php: Path,
    checkout: Checkout,
    mysql: MySQL,
    say: Say,
    snapshot_dir: Path | None = None,
) -> None:
    """Create the instance's database and files; the instance must not exist yet."""
    _require_plugin_dependencies(checkout)
    for directory in (
        instance.dir,
        instance.mail_dir,
        instance.log_dir,
        instance.run_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    instance.dir.chmod(0o700)

    say(f"database {instance.database}")
    password = mysql.ensure_user()
    mysql.create_database(instance.database)

    say(f"WordPress {WORDPRESS_VERSION}")
    archive = downloads.fetch(WORDPRESS_ZIP, CACHE, sha1=WORDPRESS_SHA1)
    _extract_wordpress(archive, instance.docroot)
    server.install(instance, checkout)
    install_mu_plugins(instance, checkout)

    wp = WpCli(php, instance)
    wp.run(
        "config",
        "create",
        f"--dbname={instance.database}",
        f"--dbuser={USER}",
        f"--dbpass={password}",
        f"--dbhost=localhost:{mysql.socket()}",
        f"--dbprefix={TABLE_PREFIX}",
        "--skip-salts",
        "--extra-php",
        stdin=wp_config_constants(instance),
    )
    (instance.docroot / "wp-config.php").chmod(0o600)
    # 24 characters, the length of the passwords WP-CLI generates
    # (`wp user create`, entity-command User_Command).
    admin_password = secrets.token_urlsafe(18)
    wp.run(
        "core",
        "install",
        f"--url={instance.url}",
        f"--title=Linker (local {instance.name})",
        f"--admin_user={ADMIN_USER}",
        f"--admin_password={admin_password}",
        f"--admin_email={ADMIN_EMAIL}",
        "--skip-email",
    )
    instance.admin_file.touch(mode=0o600)
    instance.admin_file.write_text(
        f"url: {instance.url}/wp-admin/\nuser: {ADMIN_USER}\npassword: {admin_password}\n"
    )

    say(f"WooCommerce {WOOCOMMERCE_VERSION}")
    woocommerce = downloads.fetch(WOOCOMMERCE_ZIP, CACHE)
    wp.run("plugin", "install", str(woocommerce))
    wp.run("plugin", "verify-checksums", "woocommerce")
    wp.run("plugin", "activate", "woocommerce")

    if snapshot_dir is not None:
        install_snapshot(instance, wp, snapshot_dir, say)

    linked = link_plugins(instance, checkout)
    say(f"plugins {', '.join(linked)} -> {checkout.root}")
    wp.run("plugin", "activate", *linked)

    wp.run("rewrite", "structure", PERMALINKS)
    instance.provisioned_marker.write_text(datetime.now(UTC).isoformat() + "\n")


def refresh(
    instance: Instance,
    php: Path,
    checkout: Checkout,
    say: Say,
    snapshot_dir: Path | None = None,
) -> None:
    """Bring a built instance to this checkout: php.ini, router, mu-plugins, plugin links."""
    _require_plugin_dependencies(checkout)
    server.install(instance, checkout)
    install_mu_plugins(instance, checkout)
    wp = WpCli(php, instance)
    if snapshot_dir is not None:
        install_snapshot(instance, wp, snapshot_dir, say)
    known = {path.name for path in (instance.wp_content / "plugins").iterdir()}
    linked = link_plugins(instance, checkout)
    say(f"plugins {', '.join(linked)} -> {checkout.root}")
    new = [name for name in linked if name not in known]
    if new:
        wp.run("plugin", "activate", *new)


def install_snapshot(
    instance: Instance, wp: WpCli, snapshot_dir: Path, say: Say
) -> None:
    say(f"snapshot {snapshot_dir}")
    slugs = snapshot.install(instance, snapshot_dir)
    if slugs:
        wp.run("plugin", "activate", *slugs)
        say(f"snapshot plugins {', '.join(slugs)}")


def link_plugins(instance: Instance, checkout: Checkout) -> list[str]:
    """Point wp-content/plugins/linker-* at this checkout's plugins; drop links to others."""
    plugins_dir = instance.wp_content / "plugins"
    names = [plugin.name for plugin in checkout.plugins()]
    for stale in plugins_dir.glob("linker-*"):
        if stale.is_symlink() and stale.name not in names:
            stale.unlink()
    for plugin in checkout.plugins():
        link = plugins_dir / plugin.name
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise RuntimeError(f"{link} is a directory, not a link to a checkout")
        link.symlink_to(plugin, target_is_directory=True)
    return names


def linked_checkout(instance: Instance) -> Path | None:
    """The checkout the instance's plugins point at, if any."""
    for link in sorted((instance.wp_content / "plugins").glob("linker-*")):
        if link.is_symlink():
            return link.readlink().parent.parent
    return None


def versions(instance: Instance) -> tuple[str | None, str | None]:
    """WordPress and WooCommerce versions read from the instance's files."""
    return (
        _first_match(
            instance.docroot / "wp-includes" / "version.php",
            r"\$wp_version = '([^']+)'",
        ),
        _first_match(
            instance.wp_content / "plugins" / "woocommerce" / "woocommerce.php",
            r"\* Version: (\S+)",
        ),
    )


def _require_plugin_dependencies(checkout: Checkout) -> None:
    missing = [
        p.name
        for p in checkout.plugins()
        if not (p / "vendor" / "autoload.php").is_file()
    ]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)}: vendor/ is missing; `just up` installs it (composer install)"
        )


def _extract_wordpress(archive: Path, docroot: Path) -> None:
    """Unpack the release archive, whose files sit under wordpress/, into the docroot."""
    staging = docroot.with_name(docroot.name + ".unpacking")
    shutil.rmtree(staging, ignore_errors=True)
    with zipfile.ZipFile(archive) as release:
        release.extractall(staging)
    (staging / "wordpress").rename(docroot)
    staging.rmdir()


def install_mu_plugins(instance: Instance, checkout: Checkout) -> None:
    """Copy the local mu-plugins (copies keep working when the checkout is removed)."""
    target = instance.wp_content / "mu-plugins"
    target.mkdir(exist_ok=True)
    wanted = {path.name for path in checkout.mu_plugins()}
    for stale in target.glob("*linker-local*.php"):
        if stale.name not in wanted:
            stale.unlink()
    for source in checkout.mu_plugins():
        shutil.copyfile(source, target / source.name)


def wp_config_constants(instance: Instance) -> str:
    """wp-config.php constants after the database settings."""
    # 64 characters per key, as WordPress makes them itself
    # (wp_generate_password( 64, ... ) in wp-admin/setup-config.php);
    # token_urlsafe(48) gives 64 characters of [A-Za-z0-9_-].
    lines = [
        f"define( '{name}', {_php_string(secrets.token_urlsafe(48))} );"
        for name in SALTS
    ]
    lines += [
        "",
        "// This instance (linker-local, tools/local).",
        f"define( 'WP_HOME', {_php_string(instance.url)} );",
        f"define( 'WP_SITEURL', {_php_string(instance.url)} );",
        "define( 'WP_ENVIRONMENT_TYPE', 'local' );",
        f"define( 'LINKER_LOCAL_DIR', {_php_string(str(instance.dir))} );",
    ]
    return "\n".join(lines) + "\n"


def _php_string(value: str) -> str:
    """A single-quoted PHP string literal."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _first_match(path: Path, pattern: str) -> str | None:
    try:
        found = re.search(pattern, path.read_text(errors="replace"))
    except FileNotFoundError:
        return None
    return found.group(1) if found else None
