"""The Python services of an instance, started with uv; their addresses go into WordPress.

The plugins find them through two options, set by `linker-local serve`:
linker_engine_url (the Solution Configurator's engine) and linker_genie_url
(Genie's agent loop).
"""

from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from linker_local.checkout import Checkout
from linker_local.instance import HOST, Instance
from linker_local.processes import Background, ProcessError
from linker_local.wpcli import WpCli, WpCliError

# The engine reads the site's data as two files, not over HTTP
# (services/engine/src/linker_engine/app.py, Settings.from_environment): the
# checkout's compatibility contract, and the feed the site itself serves
# (linker-commerce's linker/v1/engineering-feed), which is fetched here so the
# engine sizes against the same catalogue WordPress shows. Without them the
# engine refuses every design request, which is a config error a `serve` must
# not leave behind.
ENGINE_FEED_PATH = "/wp-json/linker/v1/engineering-feed"
ENGINE_FEED_TIMEOUT = 120.0

# Genie's document index (docs/specs/10-knowledge-index.md, 唯一检索源): the builds
# the index tooling writes under $LINKER_DATA/index/builds/<version>/index.sqlite
# (services/genie/index/paths.py; LINKER_DATA defaults to ~/de-linker-data). Without
# GENIE_INDEX the service opens the VPS path /opt/linker-genie/index/current, which
# does not exist on this Mac: every document question fell back (issue #257).
INDEX_FILE = "index.sqlite"


@dataclass(frozen=True)
class GenieIndex:
    path: Path
    source: str

    def line(self) -> str:
        return f"genie index {self.path} ({self.source})"


# The token the shell and Genie share (docs/specs/13-genie.md "附件与铭牌", review round
# 1 of PR #309, item 5): the instance's wp-config.php constant, and the service's
# GENIE_SERVICE_TOKEN. Made once per instance, 32 random bytes as hex.
SERVICE_TOKEN_CONSTANT = "LINKER_GENIE_SERVICE_TOKEN"


def service_token(wp: WpCli) -> str:
    """This instance's shared token: read from wp-config.php, made when missing."""
    try:
        token = wp.run("config", "get", SERVICE_TOKEN_CONSTANT, "--type=constant")
    except WpCliError:
        token = ""
    if not token:
        token = secrets.token_hex(32)
        wp.run(
            "config",
            "set",
            SERVICE_TOKEN_CONSTANT,
            token,
            "--type=constant",
            "--quiet",
        )
    return token


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
    """(Re)start both services from this checkout; return their URLs.

    The document index is found before anything restarts: a Genie without one
    would answer every document question with its fallback.
    """
    uv = _uv()
    index = genie_index()
    token = service_token(wp)
    urls = []
    for service in SERVICES:
        project = checkout.service(service.name)
        port = service.port(instance)
        subprocess.run(
            [str(uv), "sync", "--locked", "--project", str(project)], check=True
        )
        env = dict(os.environ)
        if service.name == "engine":
            env.update(_engine_environment(instance, checkout))
            source = checkout.root / "services/engine/src/linker_engine"
            release = hashlib.sha256()
            for path in sorted(source.rglob("*.py")):
                release.update(path.read_bytes())
            release.update(Path(env["LINKER_ENGINE_FEED"]).read_bytes())
            release.update(Path(env["LINKER_ENGINE_COMPATIBILITY"]).read_bytes())
            wp.run(
                "config",
                "set",
                "LINKER_ENGINE_RESOURCE_VERSION",
                release.hexdigest(),
                "--type=constant",
            )
            env.update(
                {"GENIE_SERVICE_TOKEN": token, "LINKER_ENGINE_GATE_MODE": "enforce"}
            )
        else:
            env.update(genie_environment(instance, index.path, token))
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
    urls.append(index.line())
    return urls


def genie_environment(instance: Instance, index: Path, token: str) -> dict[str, str]:
    """Where this instance's Genie calls back to, logs its turns and reads documents,
    and the token the instance's shell sends it (`service_token`).

    Genie calls this instance's WordPress back (the abilities); without the
    explicit address its default `http://127.0.0.1` hits whatever answers on
    port 80 of this Mac and every ability call fails. Its turn log goes into
    the instance's own directory (`Instance.genie_log`): the service's default,
    `~/.cache/linker-genie/turns.sqlite`, is one file for every instance. Its
    document index is `index` (`genie_index`). Actual work slots persist in the
    instance's private Genie directory across service restarts.
    """
    return {
        "GENIE_WP_URL": instance.url,
        "GENIE_LOG": str(instance.genie_log),
        "GENIE_INDEX": str(index),
        "GENIE_SERVICE_TOKEN": token,
        "LINKER_GENIE_WORK_MODE": "enforce",
        "LINKER_GENIE_WORK_PATH": str(instance.dir / "genie/private/work.sqlite"),
    }


def genie_index(environ: Mapping[str, str] = os.environ) -> GenieIndex:
    """The document index Genie reads: GENIE_INDEX when set, else the newest build.

    Build directories are named by their UTC build time (20261016T072222Z), so the
    newest sorts last; the line `serve` prints names it, to compare with the VPS's
    `current`. No index is a broken `serve`, not a Genie that silently falls back.
    """
    explicit = environ.get("GENIE_INDEX", "")
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ProcessError(f"GENIE_INDEX={explicit} is not a file")
        return GenieIndex(path, "GENIE_INDEX")
    data = Path(environ.get("LINKER_DATA", "~/de-linker-data")).expanduser()
    builds = data / "index" / "builds"
    found = sorted(builds.glob(f"*/{INDEX_FILE}")) if builds.is_dir() else []
    if not found:
        raise ProcessError(
            f"no Genie document index under {builds}: copy the VPS's build "
            f"(rsync -a linker-services:/opt/linker-genie/index/current/ "
            f"{builds}/<version>/), build one (just index), or set GENIE_INDEX"
        )
    return GenieIndex(found[-1], f"build {found[-1].parent.name}, the newest here")


def stop(instance: Instance) -> list[str]:
    """Stop the services; return the names of those that were running."""
    return [service.name for service in SERVICES if service.process(instance).stop()]


def running(instance: Instance) -> list[str]:
    return [
        service.name
        for service in SERVICES
        if service.process(instance).pid() is not None
    ]


def _engine_environment(instance: Instance, checkout: Checkout) -> dict[str, str]:
    """The engine's data paths and the origin allowance; the feed is fetched from the site.

    The instance serves the feed itself (`linker/v1/engineering-feed`, public
    and cacheable), so the file is a copy of what the running site's catalogue
    holds — not a second source of products. A site that cannot answer is a
    broken `serve`, not a silently data-less engine.
    """
    compatibility = checkout.root / "plugins/linker-commerce/data/compatibility.json"
    if not compatibility.is_file():
        raise ProcessError(f"{compatibility} is missing from this checkout")
    directory = instance.dir / "engine"
    directory.mkdir(exist_ok=True)
    feed = directory / "feed.json"
    url = instance.url + ENGINE_FEED_PATH
    try:
        with urllib.request.urlopen(url, timeout=ENGINE_FEED_TIMEOUT) as reply:
            feed.write_bytes(reply.read())
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        raise ProcessError(
            f"could not read the engineering feed from {url}: {error}. "
            "Is the instance up with linker-commerce active?"
        ) from error
    return {
        "LINKER_ENGINE_FEED": str(feed),
        "LINKER_ENGINE_CACHE": str(directory / "cache"),
        "LINKER_ENGINE_COMPATIBILITY": str(compatibility),
        # The configurator calls the engine cross-origin from the page; without
        # this allowance the browser blocks every call (the roof step first).
        "LINKER_ENGINE_CORS_ORIGINS": instance.url,
    }


def _uv() -> Path:
    found = shutil.which("uv")
    if found is None:
        raise ProcessError("uv is not installed: brew install uv")
    return Path(found)
