"""Who may call the service, and how large a request it reads (#236).

The shell is the only caller of the turn, vote and forget endpoints. On the VPS the
service listens on 127.0.0.1:8902 and is reached through nginx's 8443 entry
(`location /genie/`), which the firewall opens to one address: the Hostinger host's
outgoing address (46.202.156.7, read 2026-10-18 from `iptables -S INPUT` on the VPS and
`curl api.ipify.org` on the host). That address is a shared-hosting address, used by
other sites on the same Hostinger server, so the endpoints are reachable from outside
the VPS by more than our shell. They therefore require the shared token the quality
worker's route uses the same way (docs/specs/33-judge-bakeoff.md): `GENIE_SERVICE_TOKEN`
here, `LINKER_GENIE_SERVICE_TOKEN` in the site's wp-config.php, sent in
`X-Linker-Service-Token`. Without the variable the endpoints are closed (503).

A turn's body is capped before it is parsed (`schema.MAX_REQUEST_BYTES`): a declared
length past the cap is refused at once, and a streamed body is counted as it arrives.
/health stays open: the site's daily health check reads it.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

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
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers") or []
        }
        expected = os.environ.get(TOKEN_VARIABLE, "")
        if not expected:
            log.error(
                "genie gate: %s is not set; the endpoints are closed", TOKEN_VARIABLE
            )
            await _answer(send, 503, "the service token is not configured")
            return
        if not hmac.compare_digest(headers.get(HEADER, ""), expected):
            log.warning(
                "genie gate: %s %s without the service token",
                scope["method"],
                scope["path"],
            )
            await _answer(send, 401, "unauthorized")
            return
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self.limit:
            log.warning(
                "genie gate: a %s-byte body refused (cap %d)", declared, self.limit
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
                    "genie gate: a streamed body past %d bytes refused", self.limit
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

        await self.app(scope, replay, send)


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
