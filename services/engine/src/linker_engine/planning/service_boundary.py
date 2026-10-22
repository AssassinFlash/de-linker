"""Private WP-to-planner authentication, on every HTTP method and read.

WP must derive the principal from its verified native identity. These headers
are trusted only after the service credential is checked; public/browser routes
must never forward browser-supplied principal headers. This boundary does not
replace WP session/CSRF checks or resource admission. It has no off mode.
"""

from __future__ import annotations

import hmac
import re
from collections.abc import Callable
from typing import cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .access import positive_integer
from .canonical import encode
from .errors import NotFound
from .records import Actor, ActorKind

ACTOR_SCOPE = "linker.planning.verified_actor"
TOKEN_HEADER = b"x-linker-service-token"
KIND_HEADER = b"x-linker-planner-principal-kind"
SUBJECT_HEADER = b"x-linker-planner-principal-subject"


async def answer(send: Send, status: int, code: str) -> None:
    body = encode({"error": {"code": code}})
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


class ServiceBoundary:
    def __init__(
        self,
        app: ASGIApp,
        *,
        credential: Callable[[], str],
        max_body_bytes: int,
        max_json_depth: int,
    ) -> None:
        positive_integer(max_body_bytes, "private planner body limit")
        positive_integer(max_json_depth, "private planner JSON depth limit")
        self.app = app
        self.credential = credential
        self.max_body_bytes = max_body_bytes
        self.max_json_depth = max_json_depth

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def private_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                # No intermediary/browser may cache an owned result, including
                # errors. Downstream code cannot accidentally weaken this.
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower()
                    not in (b"cache-control", b"pragma", b"x-content-type-options")
                ]
                message["headers"] = headers + [
                    (b"cache-control", b"no-store, private"),
                    (b"pragma", b"no-cache"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        headers: dict[bytes, list[bytes]] = {}
        for key, value in scope.get("headers", []):
            headers.setdefault(key.lower(), []).append(value)
        expected = self.credential()
        if not expected:
            await answer(private_send, 503, "service_unconfigured")
            return
        token = headers.get(TOKEN_HEADER, [])
        if len(token) != 1 or not hmac.compare_digest(
            token[0], expected.encode("utf-8")
        ):
            await answer(private_send, 401, "unauthorized")
            return
        kinds, subjects = headers.get(KIND_HEADER, []), headers.get(SUBJECT_HEADER, [])
        if (
            len(kinds) != 1
            or kinds[0] not in (b"guest", b"user", b"team")
            or len(subjects) != 1
            or re.fullmatch(rb"[a-zA-Z0-9][a-zA-Z0-9:_-]{0,255}", subjects[0]) is None
        ):
            await answer(private_send, 400, "verified_principal_required")
            return
        # The trusted hop carries a stable namespace/subject, not the one-day
        # quota cookie. Header values are never taken from command JSON.
        actor = Actor(
            cast(ActorKind, kinds[0].decode("ascii")), subjects[0].decode("ascii")
        )
        declared = headers.get(b"content-length", [])
        if len(declared) > 1 or (
            declared and re.fullmatch(rb"[0-9]+", declared[0]) is None
        ):
            await answer(private_send, 400, "invalid_content_length")
            return
        expected_size: int | None = None
        if declared:
            digits = declared[0].lstrip(b"0") or b"0"
            ceiling = str(self.max_body_bytes).encode("ascii")
            if len(digits) > len(ceiling) or int(digits) > self.max_body_bytes:
                await answer(private_send, 413, "body_too_large")
                return
            expected_size = int(digits)
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                await answer(private_send, 400, "incomplete_request")
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_body_bytes:
                await answer(private_send, 413, "body_too_large")
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        if expected_size is not None and size != expected_size:
            await answer(private_send, 400, "incomplete_request")
            return
        body = b"".join(chunks)
        if _too_deep(body, self.max_json_depth):
            await answer(private_send, 422, "json_too_deep")
            return
        scope = dict(scope)
        scope[ACTOR_SCOPE] = actor
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay, private_send)


def _too_deep(body: bytes, ceiling: int) -> bool:
    """Bound nesting before Pydantic's recursive JSON union, ignoring strings.

    This is a resource precheck, not a second JSON parser. Malformed syntax
    still goes through the framework's typed invalid-input response.
    """
    depth = 0
    quoted = False
    escaped = False
    for char in body:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > ceiling:
                return True
        elif char in (93, 125):
            depth -= 1
    return False


def verified_actor(scope: Scope, *, write: bool = False) -> Actor:
    # Called only behind the boundary; a missing scope is a configuration bug,
    # not a reason to generate a guest or accept an owner from the body.
    actor = scope.get(ACTOR_SCOPE)
    if not isinstance(actor, Actor):
        raise RuntimeError("private service identity boundary is absent")
    if write and actor.kind == "team":
        raise NotFound("project not found")
    return actor
