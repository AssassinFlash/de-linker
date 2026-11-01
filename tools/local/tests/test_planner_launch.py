"""Refusing a version mismatch precedes lifecycle writes and dependency sync."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from linker_local import planner_worker, services
from linker_local.checkout import Checkout
from linker_local.instance import Instance
from linker_local.planner_worker import PlannerWorker
from linker_local.processes import ProcessError
from linker_local.wpcli import WpCli


@pytest.mark.parametrize("mismatch", ["schema", "http", "late_inputs"])
def test_serve_refuses_before_drain_stop_sync_or_wp_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    checkout = Checkout(tmp_path / "checkout")
    python = checkout.service("engine") / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    runtime = Path(services.planner_environment(instance)["LINKER_PLANNER_CONFIG"])
    directory = Path(json.loads(runtime.read_bytes())["directory"])
    directory.mkdir(parents=True)
    database = directory / "workspace.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE projects(id TEXT,revision INTEGER)")
        connection.execute(
            "CREATE TABLE revisions(project_id TEXT,number INTEGER,input_sha256 TEXT)"
        )
        connection.execute(
            "PRAGMA user_version=" + ("2" if mismatch == "schema" else "4")
        )
    before = database.read_bytes()
    monkeypatch.setattr(services, "_uv", lambda: Path(sys.executable))
    monkeypatch.setattr(services, "service_token", lambda _: "synthetic-service")
    # Read-only floor subprocess is covered by the real retained-input fixture;
    # this case isolates the pre-existing schema/HTTP refusal ordering.
    monkeypatch.setattr(
        planner_worker, "require_input_compatibility", lambda *args: None
    )
    monkeypatch.setattr(
        PlannerWorker,
        "release",
        lambda _: {
            "schema_version": 1,
            "runtime_sha256": "a" * 64,
            "storage_schema_version": 4,
        },
    )
    monkeypatch.setattr(PlannerWorker, "drain", lambda _: pytest.fail("drain called"))
    monkeypatch.setattr(PlannerWorker, "stop", lambda _: pytest.fail("stop called"))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: pytest.fail("dependency sync called"),
    )
    wp = WpCli(Path(sys.executable), instance)
    monkeypatch.setattr(
        wp, "run", lambda *a, **k: pytest.fail("WordPress write called")
    )

    order: list[str] = []
    if mismatch == "late_inputs":

        def compatible(_: PlannerWorker) -> dict[str, object]:
            order.append("preflight")
            if order.count("preflight") == 2:
                raise ProcessError("retained inputs require a verified paired upgrade")
            return {"runtime_sha256": "a" * 64}

        class StoppedHttp:
            def pid(self) -> None:
                return None

            def stop(self) -> None:
                order.append("http-stop")

        monkeypatch.setattr(PlannerWorker, "compatible_release", compatible)
        monkeypatch.setattr(PlannerWorker, "drain", lambda _: order.append("drain"))
        monkeypatch.setattr(
            PlannerWorker, "stop", lambda _: order.append("worker-stop")
        )
        monkeypatch.setattr(services.Service, "process", lambda *a: StoppedHttp())

    if mismatch == "http":

        class RunningHttp:
            def pid(self) -> int:
                return 17  # Only a sentinel; no process is signalled by this fixture.

        monkeypatch.setattr(services.Service, "process", lambda *a: RunningHttp())
        monkeypatch.setattr(
            services, "_planner_probe", lambda *a: {"runtime_sha256": "d" * 64}
        )
    with pytest.raises(ProcessError, match="paired upgrade"):
        services.serve(instance, checkout, wp, only="engine")
    assert database.read_bytes() == before
    assert sorted(path.name for path in directory.iterdir()) == ["workspace.sqlite"]
    if mismatch == "late_inputs":
        assert order == ["preflight", "drain", "worker-stop", "http-stop", "preflight"]


def test_genie_launch_omits_weather_credential_and_keeps_its_own_model_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    checkout = Checkout(tmp_path / "checkout")
    launches: list[dict[str, str]] = []
    commands: list[list[str]] = []

    class CapturedLaunch:
        def restart(
            self, argv: list[str], env: dict[str, str], port: int, timeout: float
        ) -> None:
            commands.append(argv)
            launches.append(env)

    monkeypatch.setattr(
        services.os, "environ", {"APIFY_TOKEN": "synthetic-private-weather"}
    )
    monkeypatch.setenv("APIFY_TOKEN_PRIMARY", "synthetic-research-alias")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-private-genie-model")
    monkeypatch.setattr(services, "_uv", lambda: Path(sys.executable))
    monkeypatch.setattr(services, "service_token", lambda _: "synthetic-service")
    monkeypatch.setattr(
        services,
        "genie_index",
        lambda: services.GenieIndex(tmp_path / "index.sqlite", "fixture"),
    )
    monkeypatch.setattr(services.Service, "process", lambda *a: CapturedLaunch())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )
    wp = WpCli(Path(sys.executable), instance)
    monkeypatch.setattr(wp, "run", lambda *a, **k: "")
    services.serve(instance, checkout, wp, only="genie")
    assert len(launches) == 1
    assert not any(key.startswith("APIFY_") for key in launches[0])
    assert launches[0]["DEEPSEEK_API_KEY"] == "synthetic-private-genie-model"
    assert "--no-sync" in commands[0] and "--offline" in commands[0]
    assert "synthetic-private-weather" not in " ".join(commands[0])
