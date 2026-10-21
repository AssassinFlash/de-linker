"""Private engine writes, before JSON parsing or engineering work (#521).

LINKER_ENGINE_GATE_MODE=enforce requires the existing GENIE_SERVICE_TOKEN.
Health and the bundled postcode lookup remain non-sensitive read-only routes.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
import sqlite3
from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

from .slots import Slots

log = logging.getLogger(__name__)

HEADER = "x-linker-service-token"
TOKEN_VARIABLE = "GENIE_SERVICE_TOKEN"

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
App = Callable[[Scope, Receive, Send], Awaitable[None]]


class Gate:
    """ASGI middleware: the shared token on every POST, the body cap on each."""

    def __init__(self, app: App, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        mode = os.environ.get("LINKER_ENGINE_GATE_MODE", "off")
        if scope["type"] != "http" or scope.get("method") != "POST" or mode == "off":
            await self.app(scope, receive, send)
            return
        if mode != "enforce":
            await _answer(send, 503, "engine gate is not configured")
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers") or []
        }
        expected = os.environ.get(TOKEN_VARIABLE, "")
        if not expected:
            log.error(
                "engine gate: %s is not set; the endpoints are closed", TOKEN_VARIABLE
            )
            await _answer(send, 503, "the service token is not configured")
            return
        # Bytes: headers arrive latin-1-decoded, and compare_digest raises
        # TypeError on a non-ASCII string, where a hostile header would get a
        # 500 instead of 401 (review round 1 of PR #309).
        given = headers.get(HEADER, "").encode("latin-1", "ignore")
        if not hmac.compare_digest(given, expected.encode("utf-8")):
            log.warning(
                "engine gate: %s %s without the service token",
                scope["method"],
                scope["path"],
            )
            await _answer(send, 401, "unauthorized")
            return
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self.limit:
            log.warning(
                "engine gate: a %s-byte body refused (cap %d)", declared, self.limit
            )
            await _answer(send, 413, "request body too large")
            return
        # The body is read here, counted as it arrives, and handed on whole:
        # FastAPI reads the whole body before the endpoint anyway, and turns an
        # error raised while reading it into a 400, so the cap must be met first.
        chunks: list[bytes] = []
        seen = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            seen += len(chunk)
            if seen > self.limit:
                log.warning(
                    "engine gate: a streamed body past %d bytes refused", self.limit
                )
                await _answer(send, 413, "request body too large")
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        subject = headers.get("x-linker-resource-subject", "")
        if not re.fullmatch(r"[a-f0-9]{64}", subject):
            await _answer(send, 400, "resource subject is required")
            return
        directory = Path(
            os.environ.get(
                "LINKER_ENGINE_CACHE", str(Path.home() / ".cache" / "linker-engine")
            )
        )
        slots = Slots(directory / "private" / "slots.sqlite")
        try:
            ident = slots.acquire(subject)
        except (OSError, sqlite3.Error):
            await _answer(send, 503, "engine slots are unavailable")
            return
        if ident is None:
            await _answer(send, 429, "a calculation is already running")
            return
        try:
            await self.app(scope, replay, send)
        finally:
            slots.release(ident)


async def _answer(send: Send, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
