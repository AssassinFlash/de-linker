"""PHP's built-in web server for an instance, with the production host's PHP limits."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from linker_local.checkout import Checkout
from linker_local.instance import Instance
from linker_local.processes import Background, ProcessError
from linker_local.registry import port_is_free

# Worker processes of PHP's built-in server (PHP_CLI_SERVER_WORKERS, PHP 7.4+,
# PHP manual "Built-in web server"; read via Apify on 2026-10-09). Six because
# Chromium opens up to six connections to one host
# (net/socket/client_socket_pool_manager.cc; read via Apify on 2026-10-09): a
# page's parallel requests, or a long streamed answer beside them, are served
# side by side instead of queueing behind a single process.
WORKERS = 6

# The production host's limits: the CloudLinux PHP Selector options in
# ~/.cl.selector/alt_php83.cfg on the de-linker.com host, read over SSH on
# 2026-10-09. The host's other options there are PHP's defaults or hosting
# hardening (disable_functions, session paths) and are not copied.
PRODUCTION_LIMITS = {
    "memory_limit": "2048M",
    "post_max_size": "2048M",
    "upload_max_filesize": "2048M",
    "max_execution_time": "360",
    "max_input_time": "360",
    "max_input_vars": "5000",
}

# Seconds to wait for the port: PHP's server listened 0.12 s after the start on
# this Mac (measured 2026-10-09); the margin covers a cold disk cache.
START_TIMEOUT = 10


def install(instance: Instance, checkout: Checkout) -> None:
    """Write the instance's php.ini and copy the router next to it.

    Copied, not linked: the server keeps working when the checkout that
    started it is removed.
    """
    instance.php_ini.write_text(php_ini(instance))
    shutil.copyfile(checkout.router, instance.router)


def php_ini(instance: Instance) -> str:
    lines = [
        "; Written by linker-local; rewritten on every `up`.",
        "; Limits of the production host's PHP (~/.cl.selector/alt_php83.cfg, 2026-10-09).",
        *(f"{key} = {value}" for key, value in PRODUCTION_LIMITS.items()),
        "; Errors go to the instance's log, not into the page.",
        "display_errors = Off",
        "log_errors = On",
        f'error_log = "{instance.log_dir / "php-error.log"}"',
    ]
    return "\n".join(lines) + "\n"


def process(instance: Instance) -> Background:
    return Background(instance.run_dir / "server.pid", instance.log_dir / "server.log")


def start(instance: Instance, php: Path) -> None:
    """(Re)start the server, so it runs the files of the checkout that called `up`."""
    server = process(instance)
    server.stop()
    if not port_is_free(instance.port):
        raise ProcessError(
            f"port {instance.port} of {instance.name} is in use by another program "
            f"(lsof -nP -iTCP:{instance.port} -sTCP:LISTEN)"
        )
    server.start(
        [
            str(php),
            "-c",
            str(instance.php_ini),
            "-S",
            f"127.0.0.1:{instance.port}",
            "-t",
            str(instance.docroot),
            str(instance.router),
        ],
        {**os.environ, "PHP_CLI_SERVER_WORKERS": str(WORKERS)},
    )
    server.wait_for_port(instance.port, START_TIMEOUT)


def stop(instance: Instance) -> bool:
    return process(instance).stop()
