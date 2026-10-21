"""Private ledger and actual transports; no provider network is contacted."""

from __future__ import annotations

import asyncio
import concurrent.futures
import multiprocessing
import os
import sqlite3
import uuid
from pathlib import Path

import httpx
import pytest
from linker_judges.budget import CAPACITIES, BudgetError, Ledger, take

from linker_genie.provider_budget import AsyncTransport, Transport


def attempt() -> str:
    return str(uuid.uuid4())


def debit_in_process(path: str) -> None:
    Ledger(Path(path)).take("jev", attempt())


def test_atomic_workers_and_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(CAPACITIES, "jev", 7)
    path = tmp_path / "private" / "provider.sqlite"

    def compete(_: int) -> bool:
        try:
            Ledger(path).take("jev", attempt())
            return True
        except BudgetError as error:
            assert error.reason == "quota"
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(compete, range(30))) == 7
    with pytest.raises(BudgetError, match="quota"):
        Ledger(path).take("jev", attempt())
    assert path.stat().st_mode & 0o077 == 0


def test_dispatch_survives_process_exit_replay_and_midnight(tmp_path: Path) -> None:
    path = tmp_path / "provider.sqlite"
    process = multiprocessing.get_context("spawn").Process(
        target=debit_in_process, args=(str(path),)
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM dispatch").fetchone()[0] == 1
    ident = attempt()
    assert Ledger(path, lambda: 86400.0 * 30000).take("deepseek", ident) == 1999
    with pytest.raises(BudgetError, match="replayed"):
        Ledger(path, lambda: 86400.0 * 30001).take("deepseek", ident)
    assert Ledger(path, lambda: 86400.0 * 30001).take("deepseek", attempt()) == 1999


def test_invalid_and_damaged_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.sqlite"
    with pytest.raises(BudgetError, match="attempt"):
        Ledger(path).take("deepseek", "invalid")
    assert not path.exists()
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.delenv("LINKER_PROVIDER_BUDGET_PATH", raising=False)
    with pytest.raises(BudgetError, match="configuration"):
        take("deepseek")
    path.write_bytes(b"broken database")
    os.chmod(path, 0o600)
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(path))
    with pytest.raises(BudgetError, match="unavailable"):
        take("deepseek")
    assert path.read_bytes() == b"broken database"


def test_transport_attempts_timeout_no_refund(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(tmp_path / "provider.sqlite"))
    monkeypatch.setitem(CAPACITIES, "deepseek", 2)
    sent: list[str] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        raise httpx.ReadTimeout("synthetic timeout")

    with httpx.Client(
        transport=Transport("deepseek", httpx.MockTransport(upstream))
    ) as client:
        for _ in range(2):
            with pytest.raises(httpx.ReadTimeout):
                client.post("https://api.deepseek.com/chat/completions", json={})
        with pytest.raises(BudgetError, match="quota"):
            client.post("https://api.deepseek.com/chat/completions", json={})
    assert len(sent) == 2
    assert take("jev") == 199


@pytest.mark.anyio
async def test_async_transport_each_tool_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(tmp_path / "provider.sqlite"))
    monkeypatch.setitem(CAPACITIES, "deepseek", 1)
    sent = 0

    async def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal sent
        sent += 1
        return httpx.Response(200, json={"choices": []})

    async with httpx.AsyncClient(
        transport=AsyncTransport("deepseek", httpx.MockTransport(upstream))
    ) as client:
        assert (
            await client.post("https://api.deepseek.com/v1/chat/completions")
        ).status_code == 200
        with pytest.raises(BudgetError, match="quota"):
            await client.post("https://api.deepseek.com/v1/chat/completions")
    assert sent == 1


@pytest.mark.anyio
async def test_installed_openai_sdk_uses_guarded_httpx2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx2
    from openai import AsyncOpenAI

    from linker_genie.provider_budget import OpenAITransport

    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(tmp_path / "provider.sqlite"))
    monkeypatch.setitem(CAPACITIES, "deepseek", 1)
    calls = 0

    async def upstream(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-flash",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "synthetic"},
                    }
                ],
            },
        )

    async with AsyncOpenAI(
        api_key="synthetic",
        base_url="https://api.deepseek.com/v1",
        max_retries=0,
        http_client=httpx2.AsyncClient(
            transport=OpenAITransport(httpx2.MockTransport(upstream))
        ),
    ) as client:
        await client.chat.completions.create(
            model="deepseek-flash", messages=[{"role": "user", "content": "synthetic"}]
        )
        with pytest.raises(BudgetError, match="quota"):
            await client.chat.completions.create(
                model="deepseek-flash",
                messages=[{"role": "user", "content": "synthetic"}],
            )
    assert calls == 1


def test_private_gateway_authentication_replay_and_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conftest import SHELL
    from fastapi.testclient import TestClient

    from linker_genie.app import app

    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(tmp_path / "provider.sqlite"))
    monkeypatch.setitem(CAPACITIES, "jev", 1)
    body = {"provider": "jev", "attempt": attempt()}
    with TestClient(app) as client:
        assert client.post("/budget/take", json=body).status_code == 401
        assert not (tmp_path / "provider.sqlite").exists()
        assert client.post("/budget/take", headers=SHELL, json=body).json() == {
            "remaining": 0
        }
        assert client.post("/budget/take", headers=SHELL, json=body).status_code == 409
        assert (
            client.post(
                "/budget/take", headers=SHELL, json={**body, "attempt": attempt()}
            ).status_code
            == 429
        )
        monkeypatch.delenv("LINKER_PROVIDER_BUDGET_PATH")
        assert (
            client.post(
                "/budget/take", headers=SHELL, json={**body, "attempt": attempt()}
            ).status_code
            == 503
        )


@pytest.mark.anyio
async def test_locked_journal_respects_callers_absolute_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.sqlite"
    Ledger(path).take("jev", attempt())
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(path))
    sent = 0

    async def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal sent
        sent += 1
        return httpx.Response(200, json={})

    # A real SQLite write lock must not block the event loop or the 10 s Jev
    # caller's absolute deadline. Cancellation cannot dispatch the paid call.
    with sqlite3.connect(path) as lock:
        lock.execute("BEGIN IMMEDIATE")
        async with httpx.AsyncClient(
            transport=AsyncTransport("jev", httpx.MockTransport(upstream))
        ) as client:
            start = asyncio.get_running_loop().time()
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.03):
                    await client.post("https://openrouter.ai/api/v1/systemone", json={})
            assert asyncio.get_running_loop().time() - start < 0.3
            assert sent == 0
        lock.rollback()
    # The detached private debit can conservatively finish; it cannot replay
    # the cancelled HTTP coroutine or refund an already sent API request.
    await asyncio.sleep(0.1)
    assert sent == 0
