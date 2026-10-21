"""Private engine actual-work boundary, using only synthetic work and a temp DB."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from linker_engine.gate import Gate
from linker_engine.slots import Slots


def crash_after_acquire(path: str) -> None:
    assert Slots(Path(path)).acquire("a" * 64)
    os._exit(0)


def test_actual_slots_share_workers_hold_until_completion_and_recover_crash(
    tmp_path: Path,
) -> None:
    path = tmp_path / "slots.sqlite"
    slots = Slots(path)
    first = slots.acquire("1" * 64)
    assert first
    assert slots.acquire("1" * 64) is None
    held = [slots.acquire(str(i) * 64) for i in (2, 3, 4)]
    assert all(held)
    assert slots.acquire("5" * 64) is None
    slots.release(first)
    assert slots.acquire("5" * 64)
    # A separate process that dies without finally leaves a durable row. The
    # next admission checks the PID, never a time-based expiry of live work.
    crash_path = tmp_path / "crash.sqlite"
    process = multiprocessing.get_context("spawn").Process(
        target=crash_after_acquire, args=(str(crash_path),)
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    assert Slots(crash_path).acquire("a" * 64)


def test_private_gate_rejects_before_json_and_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-token")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    app = FastAPI()
    app.add_middleware(Gate, limit=32)
    calls: list[int] = []

    @app.post("/work")
    def work(body: dict[str, int]) -> dict[str, bool]:
        calls.append(body["value"])
        return {"ok": True}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/work", content="invalid JSON").status_code == 401
        headers = {
            "X-Linker-Service-Token": "synthetic-token",
            "X-Linker-Resource-Subject": "f" * 64,
        }
        assert (
            client.post("/work", headers=headers, content="x" * 33).status_code == 413
        )
        assert calls == []
        assert (
            client.post("/work", headers=headers, json={"value": 1}).status_code == 200
        )
        assert calls == [1]
        # Same subject is still running in another worker/caller.
        held = Slots(tmp_path / "private" / "slots.sqlite").acquire("f" * 64)
        assert held
        assert (
            client.post("/work", headers=headers, json={"value": 2}).status_code == 429
        )
        assert calls == [1]
        Slots(tmp_path / "private" / "slots.sqlite").release(held)
        assert (
            client.post("/work", headers=headers, json={"value": 2}).status_code == 200
        )
