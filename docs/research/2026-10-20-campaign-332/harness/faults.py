"""Local fault injectors. Nothing here dials a production host.

Chat modes stand in for api.deepseek.com. The OpenRouter mode stands in for
the Jev endpoint. The cut proxy sits in front of this instance's Genie and
returns a shortened SSE body.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from sse import cut_sse

# A 1x1 JPEG. Magic is FF D8 FF, which Attachments::MAGIC requires.
TINY_JPEG = (
    b"/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEBAPDw8PDw8PDw8PDw8PDw8P"
    b"FREWFhURFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGhAQGy0l"
    b"HyUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf"
    b"/AABEIAQAAgAMBIgACEQEDEQH/xAAbAAABBQEBAAAAAAAAAAAAAAADAAIEBQYBB//EABQB"
    b"AQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAH"
    b"/2Q=="
)


def chat_payload(mode: str, body: bytes, slow_s: float) -> tuple[int, bytes, str]:
    """The status, body and content type for one chat-completions call.

    `body` is the client's request. The recorded empty turn did not ask for
    a stream, so the empty modes do not branch on it.
    """
    if mode == "slow":
        time.sleep(slow_s)
        mode = "500"
    if mode == "500":
        payload: dict[str, Any] = {
            "error": {
                "message": "injected chat 500",
                "type": "server_error",
                "code": "internal_error",
            }
        }
        return 500, json.dumps(payload).encode(), "application/json"
    if mode == "429":
        limited: dict[str, Any] = {
            "error": {
                "message": "injected chat 429",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
            }
        }
        return 429, json.dumps(limited).encode(), "application/json"
    # `empty-stream` is an SSE body with no events. It does not depend on the
    # request's stream flag: the recorded M-EMPTY turn never set that flag, so
    # the branch below it (a JSON completion with no `model`) is what ran.
    if mode == "empty-stream":
        return 200, b"", "text/event-stream"
    if mode == "empty":
        # Non-stream validation shape. The chat client parses this as
        # ChatCompletion and rejects it because `model` is missing. That is
        # the recorded M-EMPTY failure, not an empty event stream.
        empty: dict[str, Any] = {
            "id": "c332",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }
            ],
        }
        return 200, json.dumps(empty).encode(), "application/json"
    refused: dict[str, Any] = {
        "error": {"message": f"unknown chat mode {mode}", "type": "invalid"}
    }
    return 400, json.dumps(refused).encode(), "application/json"


class _State:
    def __init__(self, mode: str, slow_s: float, upstream: str, cut: str) -> None:
        self.mode = mode
        self.slow_s = slow_s
        self.upstream = upstream.rstrip("/")
        self.cut = cut
        self.calls = 0
        self.lock = threading.Lock()


class FaultServer:
    """One local HTTP server. `mode` is read on every request."""

    def __init__(
        self,
        kind: str,
        mode: str = "500",
        # 65s is past Proxy::TURN_BUDGET (60, Proxy.php). The proxy returns
        # 502 before this stub finishes the slow chat call.
        slow_s: float = 65.0,
        upstream: str = "",
        cut: str = "cut",
    ) -> None:
        self.kind = kind
        self.state = _State(mode, slow_s, upstream, cut)
        state = self.state
        kind_name = kind

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(length) if length else b""
                with state.lock:
                    state.calls += 1
                if kind_name == "chat":
                    status, payload, content = chat_payload(
                        state.mode, body, state.slow_s
                    )
                    self._send(status, payload, content)
                    return
                if kind_name == "openrouter":
                    payload = json.dumps(
                        {"error": {"message": "injected openrouter 502"}}
                    ).encode()
                    self._send(502, payload, "application/json")
                    return
                self._proxy(body)

            def _send(self, status: int, payload: bytes, content: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _proxy(self, body: bytes) -> None:
                headers = {
                    "Content-Type": self.headers.get(
                        "Content-Type", "application/json"
                    ),
                    "Accept": self.headers.get("Accept", "text/event-stream"),
                }
                token = self.headers.get("X-Linker-Service-Token")
                if token:
                    headers["X-Linker-Service-Token"] = token
                request = urllib.request.Request(
                    state.upstream + self.path,
                    data=body,
                    headers=headers,
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=180) as reply:
                        raw = reply.read()
                        status = int(reply.status)
                except urllib.error.HTTPError as failure:
                    raw = failure.read()
                    status = int(failure.code)
                if state.cut == "reset":
                    self._reset(raw)
                    return
                # "cut" is the recorded SSE-CUT: the first block is complete.
                where = "after-block" if state.cut == "cut" else state.cut
                shortened = cut_sse(raw, where) if status < 400 else raw
                self._send(
                    status if status >= 400 else 200,
                    shortened,
                    "text/event-stream",
                )

            def _reset(self, raw: bytes) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(raw[:120])
                try:
                    self.wfile.flush()
                except OSError:
                    return
                self.connection.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_LINGER,
                    struct.pack("ii", 1, 0),
                )
                self.connection.close()

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        raw_host, raw_port = self._httpd.server_address[:2]
        host = (
            raw_host.decode("ascii") if isinstance(raw_host, bytes) else str(raw_host)
        )
        return f"http://{host}:{raw_port}"

    def start(self) -> str:
        self._thread.start()
        return self.url

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    def set_mode(self, mode: str) -> None:
        with self.state.lock:
            self.state.mode = mode
