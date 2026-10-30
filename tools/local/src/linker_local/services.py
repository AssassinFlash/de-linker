"""The Python services of an instance, started with uv; their addresses go into WordPress.

The plugins find them through two options, set by `linker-local serve`:
linker_engine_url (the Solution Configurator's engine) and linker_genie_url
(Genie's agent loop).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from linker_local.checkout import Checkout
from linker_local.engine_release import engine_project
from linker_local.instance import HOST, Instance
from linker_local.planner_worker import PlannerWorker
from linker_local.private_config import lifecycle_lock, publish_once
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
        "engine",
        "linker_engine.application:app",
        "linker_engine_url",
        lambda i: i.engine_port,
    ),
    Service(
        "genie", "linker_genie.app:app", "linker_genie_url", lambda i: i.genie_port
    ),
)


def serve(
    instance: Instance, checkout: Checkout, wp: WpCli, *, only: str | None = None
) -> list[str]:
    with lifecycle_lock(instance.run_dir / "services.lock"):
        return _serve(instance, checkout, wp, only=only)


def _serve(
    instance: Instance, checkout: Checkout, wp: WpCli, *, only: str | None
) -> list[str]:
    """(Re)start both services from this checkout; return their URLs.

    The document index is found before anything restarts: a Genie without one
    would answer every document question with its fallback.
    """
    uv = _uv()
    if only is not None and only not in ("engine", "genie"):
        raise ProcessError("unknown local service selection")
    selected = tuple(
        service for service in SERVICES if only is None or service.name == only
    )
    index = (
        genie_index() if any(service.name == "genie" for service in selected) else None
    )
    token = service_token(wp)
    worker: PlannerWorker | None = None
    engine_synced = False
    engine_pinned = False
    if any(service.name == "engine" for service in selected):
        project = engine_project(instance, checkout.service("engine"))
        engine_pinned = project != checkout.service("engine")
        planner_environment(instance)
        worker = PlannerWorker(instance, project, uv, checkout=checkout)
        # First startup needs an environment for the private control CLI.
        # Never sync dependencies underneath an existing numerical process.
        if not (project / ".venv/bin/python").is_file():
            if engine_pinned:
                raise ProcessError("the retained engine environment is unavailable")
            if worker.process.pid() is not None:
                raise ProcessError("live worker has no retained engine environment")
            subprocess.run(
                [str(uv), "sync", "--locked", "--project", str(project)], check=True
            )
            engine_synced = True
        worker.ensure_policy()
        target_release = worker.compatible_release()
        if SERVICES[0].process(instance).pid() is not None:
            current = _planner_probe(f"http://{HOST}:{instance.engine_port}", token)
            if current["runtime_sha256"] != target_release["runtime_sha256"]:
                raise ProcessError(
                    "running planning HTTP differs from this executable; "
                    "preserve it for a verified paired upgrade"
                )
        worker.drain()
        worker.stop()
        # Dependency synchronization must not replace files underneath either
        # half of the old pair. Both identities were checked before draining.
        SERVICES[0].process(instance).stop()
        # A save admitted just before the old HTTP stopped is part of history.
        worker.compatible_release()
    urls = []
    for service in selected:
        project = (
            worker.project
            if service.name == "engine" and worker is not None
            else checkout.service(service.name)
        )
        port = service.port(instance)
        if service.name != "engine" or (not engine_synced and not engine_pinned):
            subprocess.run(
                [str(uv), "sync", "--locked", "--project", str(project)], check=True
            )
        env = dict(os.environ)
        # Apify is an R&D tool, never a customer application dependency.
        env.pop("APIFY_TOKEN", None)
        env.pop("APIFY_API_TOKEN", None)
        if service.name == "engine":
            env.update(_engine_environment(instance, checkout))
            source = project / "src/linker_engine"
            release = hashlib.sha256()
            for path in sorted(source.rglob("*.py")):
                release.update(path.read_bytes())
            feed = Path(env["LINKER_ENGINE_FEED"]).read_bytes()
            document = json.loads(feed)
            projection = document.get("compatibility")
            if not isinstance(projection, dict) or projection.get(
                "version"
            ) != document.get("compatibility_version"):
                raise ProcessError("managed feed needs shared publication preparation")
            release.update(feed)
            release.update(
                json.dumps(
                    projection,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            )
            wp.run(
                "config",
                "set",
                "LINKER_ENGINE_RESOURCE_VERSION",
                release.hexdigest(),
                "--type=constant",
            )
            env.update(
                {
                    "GENIE_SERVICE_TOKEN": token,
                    "LINKER_ENGINE_GATE_MODE": "enforce",
                    "PYTHONPATH": str(project / "src"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
        else:
            assert index is not None
            env.update(genie_environment(instance, index.path, token))
        service.process(instance).restart(
            [
                str(uv),
                "run",
                "--locked",
                "--no-sync",
                "--offline",
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
        if service.name == "engine":
            identity = _planner_probe(url, token)
            assert worker is not None
            worker.start(identity, START_TIMEOUT)
            worker.control("resume")
            wp.run("option", "update", "linker_planner_url", url + "/planning")
            urls.append("planner worker ready")
        wp.run("option", "update", service.option, url)
        urls.append(f"{service.name} {url}")
    if index is not None:
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
    with lifecycle_lock(instance.run_dir / "services.lock"):
        return _stop(instance)


def _stop(instance: Instance) -> list[str]:
    worker = Background(
        instance.run_dir / "planner-worker.pid", instance.log_dir / "planner-worker.log"
    )
    stopped = ["planner-worker"] if worker.stop() else []
    return stopped + [
        service.name for service in SERVICES if service.process(instance).stop()
    ]


def running(instance: Instance) -> list[str]:
    worker = Background(
        instance.run_dir / "planner-worker.pid", instance.log_dir / "planner-worker.log"
    )
    return (["planner-worker"] if worker.pid() is not None else []) + [
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
    directory = instance.dir / "engine"
    directory.mkdir(exist_ok=True)
    feed = directory / "feed.json"
    compatibility = checkout.engine_contract(feed)
    if not compatibility.is_file():
        raise ProcessError(f"{compatibility} is missing from the selected generation")
    url = instance.url + ENGINE_FEED_PATH
    try:
        with urllib.request.urlopen(url, timeout=ENGINE_FEED_TIMEOUT) as reply:
            raw = reply.read()
        if feed.is_symlink():
            # The shared publication worker swaps a complete generation. A
            # restart must not write through its link into immutable bytes.
            target = feed.resolve()
            if not target.is_relative_to(directory.resolve()):
                raise ValueError("managed feed is outside this instance")
            manifest = json.loads((target.parent / "manifest.json").read_bytes())
            current = json.loads(raw)
            if any(
                manifest[key] != current[key]
                for key in ("source_revision", "compatibility_revision")
            ):
                raise ValueError("managed feed needs shared publication preparation")
        else:
            # The first publication swap can race the check above. Never
            # follow a managed link that appeared before opening this file.
            descriptor = os.open(
                feed, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "wb") as output:
                output.write(raw)
    except (
        urllib.error.URLError,
        OSError,
        TimeoutError,
        ValueError,
        KeyError,
    ) as error:
        raise ProcessError(
            f"could not read the engineering feed from {url}: {error}. "
            "Is the instance up with linker-commerce active?"
        ) from error
    return {
        "LINKER_ENGINE_FEED": str(feed),
        "LINKER_ENGINE_CACHE": str(directory / "cache"),
        "LINKER_ENGINE_COMPATIBILITY": str(compatibility),
        # The local engine must verify this instance's Woo authority, including
        # withdrawals made by its isolated acceptance fixtures.
        "LINKER_PUBLICATION_URL": instance.url
        + "/wp-json/linker/v1/publication/manifest",
        # The configurator calls the engine cross-origin from the page; without
        # this allowance the browser blocks every call (the roof step first).
        "LINKER_ENGINE_CORS_ORIGINS": instance.url,
        **planner_environment(instance),
    }


def planner_environment(instance: Instance) -> dict[str, str]:
    """Create an explicit local policy once; preserve operator changes.

    These are development resource bounds, not project/engineering limits or
    production capacity promises. Arithmetic settings are the independently
    tested replay tolerances, frozen in each manifest (548-service-hosting).
    """
    directory = instance.dir / "planner"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = directory / "runtime.json"
    if not config.exists():
        payload = {
            "schema_version": 1,
            "directory": str(directory / "workspace"),
            "max_body_bytes": 16 * 1024 * 1024,
            "max_csv_bytes": 8 * 1024 * 1024,
            "max_page_size": 100,
            "max_json_depth": 32,
            "max_intervals": 100_000,
            "max_attempts": 2,
            "absolute_kwh": 1e-7,
            "absolute_kw": 1e-7,
            "relative": 1e-9,
        }
        publish_once(config, payload)
    return {"LINKER_PLANNER_CONFIG": str(config)}


def _planner_probe(base: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        base + "/planning/version",
        data=b'{"schema_version":1}',
        headers={
            "Content-Type": "application/json",
            "X-Linker-Service-Token": token,
            "X-Linker-Planner-Principal-Kind": "team",
            "X-Linker-Planner-Principal-Subject": "local:readiness",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=START_TIMEOUT) as response:
            value = json.loads(response.read())
        if (
            not isinstance(value, dict)
            or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or not isinstance(value.get("runtime_sha256"), str)
            or re.fullmatch(r"[a-f0-9]{64}", value["runtime_sha256"]) is None
            or any(
                not isinstance(value.get(name), str)
                or re.fullmatch(r"[a-f0-9]{64}", value[name]) is None
                for name in ("execution_key", "storage_binding")
            )
            or not isinstance(value.get("limits"), dict)
            or any(
                type(value["limits"].get(name)) is not int or value["limits"][name] <= 0
                for name in (
                    "max_body_bytes",
                    "max_csv_bytes",
                    "max_page_size",
                    "max_json_depth",
                )
            )
        ):
            raise ValueError("planning version response is invalid")
        return value
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
        raise ProcessError(
            "the private planning service did not pass readiness"
        ) from error


def _uv() -> Path:
    found = shutil.which("uv")
    if found is None:
        raise ProcessError("uv is not installed: brew install uv")
    return Path(found)
