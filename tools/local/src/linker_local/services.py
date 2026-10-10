"""The Python services of an instance, started with uv; their addresses go into WordPress.

The plugins find them through two options, set by `linker-local serve`:
linker_engine_url (the Solution Configurator's engine) and linker_genie_url
(Genie's agent loop).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from linker_local.checkout import Checkout
from linker_local.instance import HOST, Instance
from linker_local.processes import Background, ProcessError
from linker_local.wpcli import WpCli

# Seconds to wait for a service's port: uvicorn listened 0.55–0.7 s after
# `uv run` on this Mac (measured 2026-10-09; the environment is synced before,
# outside this wait); the margin covers a first import that compiles bytecode.
START_TIMEOUT = 10


@dataclass(frozen=True)
class Service:
    name: str
    app: str
    option: str
    port: Callable[[Instance], int]

    def process(self, instance: Instance) -> Background:
        return Background(
            instance.run_dir / f"{self.name}.pid", instance.log_dir / f"{self.name}.log"
        )


SERVICES = (
    Service(
        "engine", "linker_engine.app:app", "linker_engine_url", lambda i: i.engine_port
    ),
    Service(
        "genie", "linker_genie.app:app", "linker_genie_url", lambda i: i.genie_port
    ),
)


def serve(instance: Instance, checkout: Checkout, wp: WpCli) -> list[str]:
    """(Re)start both services from this checkout; return their URLs."""
    uv = _uv()
    urls = []
    for service in SERVICES:
        project = checkout.service(service.name)
        port = service.port(instance)
        subprocess.run(
            [str(uv), "sync", "--locked", "--project", str(project)], check=True
        )
        # Genie calls this instance's WordPress back (the abilities); without
        # the explicit address its default `http://127.0.0.1` hits whatever
        # answers on port 80 of this Mac and every ability call fails.
        env = dict(os.environ)
        env["GENIE_WP_URL"] = instance.url
        service.process(instance).restart(
            [
                str(uv),
                "run",
                "--locked",
                "--project",
                str(project),
                "uvicorn",
                service.app,
                "--host",
                HOST,
                "--port",
                str(port),
            ],
            env,
            port,
            START_TIMEOUT,
        )
        url = f"http://{HOST}:{port}"
        wp.run("option", "update", service.option, url)
        urls.append(f"{service.name} {url}")
    return urls


def stop(instance: Instance) -> list[str]:
    """Stop the services; return the names of those that were running."""
    return [service.name for service in SERVICES if service.process(instance).stop()]


def running(instance: Instance) -> list[str]:
    return [
        service.name
        for service in SERVICES
        if service.process(instance).pid() is not None
    ]


def _uv() -> Path:
    found = shutil.which("uv")
    if found is None:
        raise ProcessError("uv is not installed: brew install uv")
    return Path(found)
