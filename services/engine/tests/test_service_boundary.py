"""Actual endpoint inventory: unauthorized requests never enter engineering work."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from linker_engine.app import create_app
from linker_engine.gate import Gate, Message

POSTS = {
    "/design/residential",
    "/design/commercial",
    "/roof/outline",
    "/roof/pack",
    "/report/pdf",
}


def test_service_exposes_only_business_routes_without_schema_ui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-boundary-token")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    app = create_app()
    # Enumerating the actual native routes catches a newly unreviewed POST.
    assert {
        getattr(r, "path", "")
        for r in app.routes
        if "POST" in getattr(r, "methods", set())
    } == POSTS
    with TestClient(app) as client:
        for path in ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]:
            assert client.get(path).status_code == 404
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/resource/version").status_code == 401
        assert client.get("/geo/plz/80538").status_code == 200
        for path in POSTS:
            assert client.post(path, content="{invalid JSON").status_code == 401
    assert not list(tmp_path.rglob("*.sqlite"))


def test_unauthorized_headers_are_refused_without_reading_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-boundary-token")
    messages: list[Message] = []

    async def never(*_: Any) -> Any:
        raise AssertionError("neither upstream nor body may be read")

    async def send(message: Message) -> None:
        messages.append(message)

    asyncio.run(
        Gate(never, limit=6 * 1024 * 1024)(
            {"type": "http", "method": "POST", "path": "/roof/outline", "headers": []},
            never,
            send,
        )
    )
    assert messages[0]["status"] == 401
