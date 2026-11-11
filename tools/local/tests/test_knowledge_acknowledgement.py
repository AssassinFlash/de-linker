"""A fresh pull acknowledges the knowledge generation its own Genie opened.

Knowledge readiness is recipe-aware: it names the compiler, the index generation
and the serving rules, and an engine feed readback carries none of them
(docs/acceptance/2026-11-11/review-readiness-fix.md). `serve` starts Genie on this
instance's newest index and then acknowledges exactly what that process opened;
the native ACK still verifies every field, and a refusal never breaks a working
serve.
"""

from __future__ import annotations

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
        (None, "knowledge readiness: acknowledged"),
        (
            WpCliError(
                "wp linker-commerce publication ack-knowledge: "
                "genie_source_mismatch: Genie loaded aa, this site publishes bb"
            ),
            "knowledge readiness: not acknowledged (",
        ),
    ],
)
def test_the_knowledge_acknowledgement_names_genie_and_reports_its_outcome(
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
    line = services._acknowledge_knowledge(wp, "http://127.0.0.1:8891", "token")

    assert line.startswith(expected)
    if failure is not None:
        # A refusal is reported with Genie's own diagnostic, never raised.
        assert "genie_source_mismatch" in line
    assert runs == [
        (
            (
                "linker-commerce",
                "publication",
                "ack-knowledge",
                "--genie=http://127.0.0.1:8891",
            ),
            {"LINKER_GENIE_SERVICE_TOKEN": "token"},
        )
    ]


def test_serve_acknowledges_the_generation_its_genie_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = Instance("owned", 1, 2, 3, tmp_path / "instances")
    checkout = Checkout(tmp_path / "checkout")
    genie_url = f"http://{HOST}:{instance.genie_port}"
    order: list[str] = []

    class CapturedLaunch:
        def pid(self) -> None:
            return None

        def stop(self) -> None:
            pass

        def restart(
            self, argv: list[str], env: dict[str, str], port: int, timeout: float
        ) -> None:
            order.append("genie-started")

    monkeypatch.setattr(services, "_uv", lambda: Path(sys.executable))
    monkeypatch.setattr(services, "service_token", lambda _: "synthetic-service")
    monkeypatch.setattr(
        services,
        "genie_index",
        lambda: services.GenieIndex(tmp_path / "index.sqlite", "fixture"),
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
        if args[:3] == ("linker-commerce", "publication", "ack-knowledge"):
            order.append("acknowledged")
        return ""

    monkeypatch.setattr(wp, "run", run)
    lines = services.serve(instance, checkout, wp, only="genie")

    assert [
        (args, env)
        for args, env in writes
        if args[:3] == ("linker-commerce", "publication", "ack-knowledge")
    ] == [
        (
            (
                "linker-commerce",
                "publication",
                "ack-knowledge",
                f"--genie={genie_url}",
            ),
            {"LINKER_GENIE_SERVICE_TOKEN": "synthetic-service"},
        )
    ]
    # Genie answered readiness before its open generation is acknowledged.
    assert order == ["genie-started", "acknowledged"]
    assert lines == [
        f"genie {genie_url}",
        "knowledge readiness: acknowledged",
        f"genie index {tmp_path / 'index.sqlite'} (fixture)",
    ]
