"""The persistent object cache of an instance: Redis Object Cache on the local Redis.

Production gets a Redis object cache at the cutover (docs/specs/17-cutover.md,
"主机卫生"), so every instance runs one too (docs/specs/5-local-stack.md). All
instances share Homebrew's Redis server; each keeps to its own key prefix, and
flushing removes that prefix only.
"""

from __future__ import annotations

from linker_local import downloads
from linker_local.instance import HOST, Instance
from linker_local.processes import port_is_free
from linker_local.wpcli import WpCli

# Redis's port: `port 6379` in redis.conf (read via Apify on 2026-10-09), the
# file Homebrew's redis service starts with (/opt/homebrew/etc/redis.conf,
# which binds the loopback only).
REDIS_PORT = 6379
# Redis Object Cache, the plugin docs/specs/17-cutover.md names for production.
# 3.0.0 is its release of 2026-09-18, tested up to WordPress 7.1.3 (wordpress.org
# plugin API, read via Apify on 2026-10-09); its files are checked against
# wordpress.org's checksums like WooCommerce's.
PLUGIN = "redis-cache"
PLUGIN_VERSION = "3.0.0"
PLUGIN_ZIP = f"https://downloads.wordpress.org/plugin/{PLUGIN}.{PLUGIN_VERSION}.zip"


class RedisError(RuntimeError):
    """The local Redis server is not there."""


def require_redis() -> None:
    """Fail unless something listens on Redis's port (the plugin checks the rest)."""
    if port_is_free(REDIS_PORT):
        raise RedisError(
            f"Redis is not running on {HOST}:{REDIS_PORT}: "
            "brew install redis && brew services start redis (docs/local-stack.md)"
        )


def prefix(instance: Instance) -> str:
    """Every key of the instance starts with this, e.g. "linker_a:"."""
    return f"{instance.database}:"


def wp_config_constants(instance: Instance) -> list[str]:
    """The plugin's settings (its README's constants) for wp-config.php."""
    return [
        f"define( 'WP_REDIS_HOST', '{HOST}' );",
        f"define( 'WP_REDIS_PORT', {REDIS_PORT} );",
        f"define( 'WP_REDIS_PREFIX', '{prefix(instance)}' );",
        # A flush deletes this instance's keys only, not every instance's.
        "define( 'WP_REDIS_SELECTIVE_FLUSH', true );",
    ]


def install(wp: WpCli) -> None:
    """Install and enable the plugin's object-cache.php, then drop stale keys.

    The flush matters after a reset: the new database must not read the keys
    the old one left under the same prefix.
    """
    archive = downloads.fetch(PLUGIN_ZIP)
    wp.run("plugin", "install", str(archive))
    wp.run("plugin", "verify-checksums", PLUGIN)
    wp.run("plugin", "activate", PLUGIN)
    wp.run("redis", "enable")
    wp.run("cache", "flush")
    status = wp.run("redis", "status")
    if "Status: Connected" not in status:
        raise RedisError(f"the object cache is not connected:\n{status}")
