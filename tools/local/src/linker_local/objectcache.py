"""The persistent object cache of an instance: Redis Object Cache on the local Redis.

Production gets a Redis object cache at the cutover (docs/specs/17-cutover.md,
"主机卫生"), so every instance runs one too (docs/specs/5-local-stack.md). All
instances share Homebrew's Redis server and its database 0; each keeps to its
own key prefix, and nothing here deletes another instance's keys.

The plugin's own `wp redis enable` / `disable` / `update-dropin` and its
deactivation hook run FLUSHDB (redis-cache 3.0.0: includes/cli/class-commands.php
and includes/class-plugin.php call (new Predis)->flush(), which runs flushdb()
in includes/class-predis.php without the prefix filter), emptying the shared
database for every instance, so the drop-in is copied here instead.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable

from linker_local import downloads
from linker_local.instance import HOST, Instance
from linker_local.processes import port_is_free
from linker_local.wpcli import WpCli

# Redis's port: `port 6379` in redis.conf (read via Apify on 2026-10-09), the
# file Homebrew's redis service starts with (/opt/homebrew/etc/redis.conf,
# which binds the loopback only).
REDIS_PORT = 6379
# Redis Object Cache, one of the two object caches docs/specs/17-cutover.md
# lists for production. 3.0.0 is its release of 2026-09-18, tested up to
# WordPress 7.1.3 (wordpress.org plugin API, read via Apify on 2026-10-09); its
# files are checked against wordpress.org's checksums like WooCommerce's.
PLUGIN = "redis-cache"
PLUGIN_VERSION = "3.0.0"
PLUGIN_ZIP = f"https://downloads.wordpress.org/plugin/{PLUGIN}.{PLUGIN_VERSION}.zip"


class RedisError(RuntimeError):
    """The local Redis server is not there or did not answer."""


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
        # wp_cache_flush() deletes this instance's keys only.
        "define( 'WP_REDIS_SELECTIVE_FLUSH', true );",
        # A Redis hiccup must not kill the request. Without this constant the
        # drop-in dies on the first failed cache read (its fail_gracefully
        # flag defaults off; the review instance's PHP log carried a burst of
        # Predis connection exceptions, each one a request that answered
        # nothing). With it, the drop-in logs the exception, serves the rest
        # of the request from its per-request cache, and the next command
        # reconnects - the reads degrade to cache misses, the pages and the
        # abilities keep answering.
        "define( 'WP_REDIS_GRACEFUL', true );",
    ]


# Operational batch bound: at most 128 keys per UNLINK, regardless of SCAN's
# advisory COUNT. Keep argv and memory bounded even for large retired caches.
BATCH_SIZE = 128


def forget(instance: Instance, *, permitted: Callable[[], bool] = lambda: True) -> int:
    """Bounded, prefix-only reclamation; retirement rechecks ownership per batch.

    Reset/install deliberately use the default: their instance remains registered.
    SCAN may return duplicates; UNLINK's integer reply counts actual removals.
    """
    cursor = "0"
    removed = 0
    while True:
        if not permitted():
            raise RedisError("instance was reused; cache reclamation stopped")
        reply = json.loads(
            _redis_cli(
                "--json",
                "SCAN",
                cursor,
                "MATCH",
                f"{prefix(instance)}*",
                "COUNT",
                str(BATCH_SIZE),
            )
        )
        if (
            not isinstance(reply, list)
            or len(reply) != 2
            or not isinstance(reply[1], list)
        ):
            raise RedisError("invalid Redis SCAN response")
        cursor = str(reply[0])
        keys = reply[1]
        if any(
            not isinstance(key, str) or not key.startswith(prefix(instance))
            for key in keys
        ):
            raise RedisError("Redis SCAN returned a foreign key")
        for offset in range(0, len(keys), BATCH_SIZE):
            if not permitted():
                raise RedisError("instance was reused; cache reclamation stopped")
            removed += int(_redis_cli("UNLINK", *keys[offset : offset + BATCH_SIZE]))
        if cursor == "0":
            return removed


def install(instance: Instance, wp: WpCli) -> None:
    """Install the plugin and its object-cache.php drop-in.

    The instance's old keys go first, before any WordPress run reads through
    the drop-in: after a reset, the new database must not see what the old
    one left under the same prefix.
    """
    forget(instance)
    archive = downloads.fetch(PLUGIN_ZIP)
    wp.run("plugin", "install", str(archive))
    wp.run("plugin", "verify-checksums", PLUGIN)
    wp.run("plugin", "activate", PLUGIN)
    # What `wp redis enable` copies, without the FLUSHDB around it
    # (includes/cli/class-commands.php, enable()).
    shutil.copyfile(
        instance.wp_content / "plugins" / PLUGIN / "includes" / "object-cache.php",
        instance.wp_content / "object-cache.php",
    )
    status = wp.run("redis", "status")
    if "Status: Connected" not in status:
        raise RedisError(f"the object cache is not connected:\n{status}")


def _redis_cli(*args: str) -> str:
    cli = shutil.which("redis-cli")
    if cli is None:
        raise RedisError("redis-cli is not installed: brew install redis")
    result = subprocess.run(
        [cli, "-h", HOST, "-p", str(REDIS_PORT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RedisError(
            f"redis-cli {args[0]}: {(result.stderr or result.stdout).strip()}"
        )
    return result.stdout
