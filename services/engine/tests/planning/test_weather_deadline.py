"""Real blocking sockets and owned process cleanup; no external endpoint."""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from subprocess import Popen
from typing import Any

import pytest

from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.errors import LeaseLost
from linker_engine.planning.pvgis_transport import PvgisTransport
from linker_engine.planning.weather_fetch_errors import (
    WeatherProviderUnavailable,
    WeatherResponseTooLarge,
)
from linker_engine.planning.weather_fetch_plan import WeatherFetchPlan
from linker_engine.planning.weather_journal import WeatherDeadlineExceeded

from .test_official_weather import plan
from .test_pv_profile import LIMITS
from .test_pvgis_tmy import raw

# The child genuinely enters urllib3's full-block socket read while a peer
# sends one byte each 20 ms. A 50 ms inactivity timeout never fires, reproducing
# the initial review finding independently of the supervisor implementation.
SLOW_BODY = """
import socket, threading, time
from urllib3.response import HTTPResponse
left, right = socket.socketpair()
left.settimeout(0.05)
def write():
    for _ in range(100):
        right.sendall(b'x')
        time.sleep(0.02)
    right.close()
threading.Thread(target=write, daemon=True).start()
print('entered-blocking-body-read', flush=True)
response = HTTPResponse(body=left.makefile('rb'), preload_content=False)
response.read(65536)
"""


def command(monkeypatch: pytest.MonkeyPatch, script: str, *arguments: str) -> None:
    def selected_command(
        self: PvgisTransport, selected: WeatherFetchPlan, remaining: float
    ) -> list[str]:
        return [sys.executable, "-c", script, *arguments]

    monkeypatch.setattr(PvgisTransport, "_command", selected_command)


@pytest.mark.parametrize("mode", ["deadline", "lease_lost", "clock_backwards"])
def test_continuous_socket_trickle_cannot_hold_the_worker(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    original = subprocess.Popen
    children: list[Popen[bytes]] = []

    def observe(*args: Any, **kwargs: Any) -> Popen[bytes]:
        child: Popen[bytes] = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe)
    command(monkeypatch, SLOW_BODY)
    start = time.monotonic()
    clock: Callable[[], float] = time.time
    deadline = clock() + 0.25
    if mode == "clock_backwards":
        initial = clock()

        def backwards() -> float:
            return initial if time.monotonic() - start < 0.05 else initial - 100

        clock = backwards

    def guard() -> None:
        if mode == "lease_lost" and time.monotonic() - start >= 0.10:
            raise LeaseLost("isolated revoked lease")

    with pytest.raises(LeaseLost if mode == "lease_lost" else WeatherDeadlineExceeded):
        PvgisTransport().download(plan(), deadline=deadline, clock=clock, guard=guard)
    assert time.monotonic() - start < 1.0  # The unbounded read takes > 2 seconds.
    assert len(children) == 1 and children[0].returncode is not None


def test_transfer_roundtrip_excludes_credentials_and_preserves_original(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in (
        "APIFY_TOKEN",
        "APIFY_API_TOKEN",
        "GENIE_SERVICE_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setenv(name, "synthetic-never-forward")
    response = tmp_path / "original.json"
    response.write_bytes(raw())
    capture: Object = {
        "schema_version": 1,
        "requested_url": plan().request.url,
        "loaded_url": plan().request.url,
        "status": 200,
        "content_type": "application/json",
        "received_at_utc": "2026-10-24T00:00:00Z",
        "capture_basis": "official_jrc_https_get_original_v1",
        "source_identifiers": {"provider": "EC_JRC_PVGIS", "api_version": "5.3"},
    }
    metadata = encode(
        {
            "schema_version": 1,
            "capture": capture,
            "provenance": {"label": "isolated original"},
        }
    )
    script = r"""
import os, pathlib, sys
assert not any(key in os.environ for key in ('APIFY_TOKEN', 'APIFY_API_TOKEN', 'GENIE_SERVICE_TOKEN', 'AWS_SECRET_ACCESS_KEY'))
sys.stdout.buffer.write(sys.argv[1].encode() + b'\n')
sys.stdout.buffer.write(pathlib.Path(sys.argv[2]).read_bytes())
"""
    command(monkeypatch, script, metadata.decode(), str(response))
    result = PvgisTransport().download(
        plan(),
        deadline=time.time() + 5,
        clock=time.time,
        guard=lambda: None,
    )
    assert result.source.content == raw()
    assert len(result.source.weather(LIMITS).points) == 8760


@pytest.mark.parametrize("body", [b"unframed metadata", b"x" * 100_001])
def test_missing_receipt_and_unbounded_metadata_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    body: bytes,
) -> None:
    payload = tmp_path / "transfer"
    payload.write_bytes(body)
    command(
        monkeypatch,
        "import sys,pathlib;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())",
        str(payload),
    )
    expected = (
        WeatherResponseTooLarge if len(body) > 100_000 else WeatherProviderUnavailable
    )
    with pytest.raises(expected):
        PvgisTransport().download(
            plan(),
            deadline=time.time() + 5,
            clock=time.time,
            guard=lambda: None,
        )


def test_the_http_child_has_its_own_exit_deadline_if_parent_disappears() -> None:
    script = """
import sys, time
from linker_engine.planning import weather_http_host as host
class BlockedTransfer:
    def download(self, *args, **kwargs):
        time.sleep(10)
    def close(self):
        pass
host.PvgisHttpTransfer = BlockedTransfer
sys.argv = ['isolated-host', sys.argv[1], '0.15']
host.main()
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, encode(plan().document()).decode()],
        capture_output=True,
        timeout=3,
        check=False,
    )
    assert completed.returncode == 124
