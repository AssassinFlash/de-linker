"""Actual Genie endpoint inventory; no schema UI or unguarded write outlet."""

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from linker_genie.app import app
from linker_genie.gate import Gate, Message

POSTS = {
    "/budget/take",
    "/turn",
    "/assistant/turn",
    "/assistant/turn/{turn_id}/vote",
    "/turn/{turn_id}/vote",
    "/summary",
    "/assistant/conversation/{conversation_id}/forget",
    "/pages/invalidate",
    "/knowledge/loaded",
    "/inquiries/assess",
}


def test_service_exposes_only_business_routes_without_schema_ui() -> None:
    assert {
        getattr(r, "path", "")
        for r in app.routes
        if "POST" in getattr(r, "methods", set())
    } == POSTS
    with TestClient(app) as client:
        for path in ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]:
            assert client.get(path).status_code == 404
        assert client.get("/health").json() == {"status": "ok"}
        for path in POSTS:
            route = path.replace("{turn_id}", "synthetic").replace(
                "{conversation_id}", "synthetic"
            )
            assert client.post(route, content="{invalid JSON").status_code == 401


def test_unauthorized_headers_are_refused_without_reading_body() -> None:
    messages: list[Message] = []

    async def never(*_: Any) -> Any:
        raise AssertionError("neither upstream nor body may be read")

    async def send(message: Message) -> None:
        messages.append(message)

    asyncio.run(
        Gate(never, limit=30 * 1024 * 1024)(
            {"type": "http", "method": "POST", "path": "/turn", "headers": []},
            never,
            send,
        )
    )
    assert messages[0]["status"] == 401
