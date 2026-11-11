"""A fresh pull acknowledges its own engine's loaded generation.

`repair-bindings` renews every product revision, so the receipts a production
worker left behind name a generation that no longer exists
(docs/acceptance/2026-11-11/review-readiness-fix.md). `serve` starts the engine
on this site's current feed and then acknowledges exactly what it loaded; the
native ACK still verifies every revision, and a refusal never breaks a working
serve.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from linker_local import services
from linker_local.checkout import Checkout
from linker_local.instance import HOST, Instance
from linker_local.wpcli import WpCli, WpCliError


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (None, "engineering readiness: acknowledged"),
        (
            WpCliError(
                "wp linker-commerce publication ack-engineering: "
                "engine_source_mismatch: the engine loaded aa, this site publishes bb"
            ),
            "engineering readiness: not acknowledged (",
        ),
    ],
)
def test_the_acknowledgement_names_the_engine_and_reports_its_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: WpCliError | None,
    expected: str,
) -> None:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    wp = WpCli(Path(sys.executable), instance)
    runs: list[tuple[tuple[str, ...], dict[str, str] | None]] = []

    def run(*args: str, env: dict[str, str] | None = None) -> str:
        runs.append((args, env))
        if failure is not None:
            raise failure
        return ""

    monkeypatch.setattr(wp, "run", run)
    line = services._acknowledge_engineering(wp, "http://127.0.0.1:8890", "token")

    assert line.startswith(expected)
    if failure is not None:
        # A refusal is reported with the engine's own diagnostic, never raised.
        assert "engine_source_mismatch" in line
    assert runs == [
        (
            (
                "linker-commerce",
                "publication",
                "ack-engineering",
                "--engine=http://127.0.0.1:8890",
            ),
            {"LINKER_ENGINE_SERVICE_TOKEN": "token"},
        )
    ]


def test_serve_acknowledges_the_generation_its_engine_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    checkout = Checkout(tmp_path / "checkout")
    python = checkout.service("engine") / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    feed = tmp_path / "feed.json"
    feed.write_bytes(
        json.dumps(
            {"compatibility_version": "v1", "compatibility": {"version": "v1"}}
        ).encode()
    )
    engine_url = f"http://{HOST}:{instance.engine_port}"
    order: list[str] = []

    class CapturedLaunch:
        def pid(self) -> None:
            return None

        def stop(self) -> None:
            pass

        def restart(
            self, argv: list[str], env: dict[str, str], port: int, timeout: float
        ) -> None:
            order.append("engine-started")

    class Worker:
        project = checkout.service("engine")

        def ensure_policy(self) -> None:
            pass

        def compatible_release(self) -> dict[str, object]:
            return {"runtime_sha256": "a" * 64}

        def drain(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def start(self, identity: dict[str, object], timeout: float) -> None:
            pass

        def control(self, command: str) -> None:
            pass

    monkeypatch.setattr(services, "_uv", lambda: Path(sys.executable))
    monkeypatch.setattr(services, "service_token", lambda _: "synthetic-service")
    monkeypatch.setattr(
        services, "_engine_environment", lambda *args: {"LINKER_ENGINE_FEED": str(feed)}
    )
    monkeypatch.setattr(services, "PlannerWorker", lambda *args, **kwargs: Worker())
    monkeypatch.setattr(
        services, "_planner_probe", lambda *args: {"runtime_sha256": "a" * 64}
    )
    monkeypatch.setattr(services.Service, "process", lambda *args: CapturedLaunch())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )
    wp = WpCli(Path(sys.executable), instance)
    writes: list[tuple[tuple[str, ...], dict[str, str] | None]] = []

    def run(*args: str, env: dict[str, str] | None = None) -> str:
        writes.append((args, env))
        if args[:3] == ("linker-commerce", "publication", "ack-engineering"):
            order.append("acknowledged")
        return ""

    monkeypatch.setattr(wp, "run", run)
    lines = services.serve(instance, checkout, wp, only="engine")
    assert [
        (args, env)
        for args, env in writes
        if args[:3] == ("linker-commerce", "publication", "ack-engineering")
    ] == [
        (
            (
                "linker-commerce",
                "publication",
                "ack-engineering",
                f"--engine={engine_url}",
            ),
            {"LINKER_ENGINE_SERVICE_TOKEN": "synthetic-service"},
        )
    ]
    # The engine answered readiness before its loaded generation is acknowledged.
    assert order == ["engine-started", "acknowledged"]
    assert lines == [
        "planner worker ready",
        f"engine {engine_url}",
        "engineering readiness: acknowledged",
    ]
