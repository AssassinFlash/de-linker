"""Real private HTTP disconnects and cross-process actual-turn slots; synthetic work."""

from __future__ import annotations

import json
import multiprocessing
import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from linker_genie.work import Slots, WorkError, hold


def crash_after_acquire(path: str) -> None:
    assert Slots(Path(path)).acquire("a" * 64)
    os._exit(0)


def test_slots_are_atomic_across_workers_and_reclaim_only_dead_workers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "work.sqlite"
    slots = Slots(path)
    first = slots.acquire("1" * 64)
    assert first
    assert slots.acquire("1" * 64) is None
    second = slots.acquire("2" * 64)
    assert second
    assert Slots(path).acquire("3" * 64) is None
    slots.release(first)
    assert Slots(path).acquire("3" * 64)
    assert path.stat().st_mode & 0o077 == 0
    crash_path = tmp_path / "crash.sqlite"
    process = multiprocessing.get_context("spawn").Process(
        target=crash_after_acquire, args=(str(crash_path),)
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    assert Slots(crash_path).acquire("a" * 64)


def test_private_configuration_storage_and_finally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_GENIE_WORK_MODE", "enforce")
    monkeypatch.delenv("LINKER_GENIE_WORK_PATH", raising=False)
    with pytest.raises(WorkError, match="configuration"), hold("a" * 64):
        pytest.fail("missing path admitted work")
    path = tmp_path / "private" / "work.sqlite"
    monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(path))
    with pytest.raises(WorkError, match="subject"), hold("invalid"):
        pytest.fail("invalid subject admitted work")
    assert not path.exists()
    with pytest.raises(RuntimeError, match="synthetic"), hold("a" * 64):
        raise RuntimeError("synthetic worker failure")
    with hold("a" * 64):
        with pytest.raises(WorkError, match="busy"), hold("a" * 64):
            pytest.fail("same subject overlapped")
    path.write_bytes(b"broken database")
    with pytest.raises(WorkError, match="storage"), hold("a" * 64):
        pytest.fail("corrupt store admitted work")


def run_http(sock: socket.socket, path: str, entered: Any, release: Any) -> None:
    """Run the actual app wrapper; replace only its paid sync body with a latch."""
    import uvicorn
    from fastapi import Request
    from fastapi.responses import StreamingResponse

    import linker_genie.app as module
    from linker_genie.schema import TurnRequest

    os.environ.update(
        {
            "GENIE_SERVICE_TOKEN": "synthetic-work-token",
            "LINKER_GENIE_WORK_MODE": "enforce",
            "LINKER_GENIE_WORK_PATH": path,
        }
    )

    def synthetic(body: TurnRequest, request: Request) -> StreamingResponse:
        entered.set()
        assert release.wait(20), "fixture must explicitly finish actual work"
        return StreamingResponse(
            iter(["event: done\ndata: {}\n\n"]), media_type="text/event-stream"
        )

    module._assistant_turn = synthetic
    uvicorn.Server(
        uvicorn.Config(module.app, log_level="error", lifespan="off", ws="none")
    ).run(sockets=[sock])


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with sqlite3.connect(path) as db:
        return int(db.execute("SELECT COUNT(*) FROM slots").fetchone()[0])


def test_http_disconnect_keeps_actual_sync_worker_slot_until_it_finishes(
    tmp_path: Path,
) -> None:
    context = multiprocessing.get_context("spawn")
    entered, release = context.Event(), context.Event()
    path = tmp_path / "private" / "work.sqlite"
    listening = socket.socket()
    listening.bind(("127.0.0.1", 0))
    listening.listen(8)
    port = listening.getsockname()[1]
    process = context.Process(
        target=run_http, args=(listening, str(path), entered, release)
    )
    process.start()
    listening.close()
    connections: list[socket.socket] = []
    base = f"http://127.0.0.1:{port}"
    headers = {
        "X-Linker-Service-Token": "synthetic-work-token",
        "X-Linker-Resource-Subject": "1" * 64,
    }
    body = {
        "conversation_id": "synthetic",
        "messages": [{"role": "user", "content": "Synthetic disconnected question"}],
    }
    try:
        for _ in range(200):
            try:
                if httpx.get(base + "/health", timeout=0.2).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.025)
        else:
            pytest.fail("private HTTP worker did not start")

        def start(subject: str) -> socket.socket:
            connection = socket.create_connection(("127.0.0.1", port), timeout=2)
            payload = json.dumps(body).encode()
            connection.sendall(
                (
                    f"POST /assistant/turn HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\nX-Linker-Service-Token: synthetic-work-token\r\nX-Linker-Resource-Subject: {subject}\r\nConnection: close\r\n\r\n"
                ).encode()
                + payload
            )
            return connection

        first = start("1" * 64)
        connections.append(first)
        assert entered.wait(10)
        first.close()
        assert row_count(path) == 1
        with httpx.Client(timeout=2) as client:
            assert (
                client.post(
                    base + "/assistant/turn", headers=headers, json=body
                ).status_code
                == 429
            )
            second = start("2" * 64)
            connections.append(second)
            for _ in range(100):
                if row_count(path) == 2:
                    break
                time.sleep(0.01)
            assert row_count(path) == 2
            assert (
                client.post(
                    base + "/assistant/turn",
                    headers={**headers, "X-Linker-Resource-Subject": "3" * 64},
                    json=body,
                ).status_code
                == 429
            )
            release.set()
            for _ in range(200):
                if row_count(path) == 0:
                    break
                time.sleep(0.01)
            assert row_count(path) == 0
            assert (
                client.post(
                    base + "/assistant/turn", headers=headers, json=body
                ).status_code
                == 200
            )
    finally:
        release.set()
        for connection in connections:
            connection.close()
        process.terminate()
        process.join(timeout=10)
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
