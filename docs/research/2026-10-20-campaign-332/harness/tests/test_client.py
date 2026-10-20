from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from client import (
    HttpResult,
    cookie_opener,
    describe,
    proxy_body,
    request_json,
    selected_headers,
    stream_of,
    turn_body,
    wp_error,
)


def test_selected_headers_keep_the_named_ones() -> None:
    picked = selected_headers(
        [("date", "Mon"), ("X-Ignored", "no"), ("Content-Type", "application/json")]
    )
    assert picked == {"Date": "Mon", "Content-Type": "application/json"}


def test_bodies_carry_the_question() -> None:
    service = turn_body("BASE-EN", "Do you stock it?", "en")
    assert service["messages"][0]["content"] == "Do you stock it?"
    proxy = proxy_body("Do you stock it?", "de", None)
    assert proxy["locale"] == "de"
    assert "attachments" not in proxy
    with_file = proxy_body("Read this.", "en", {"name": "a.jpg"})
    assert with_file["attachments"] == [{"name": "a.jpg"}]


def test_stream_of_unwraps_the_proxy_envelope() -> None:
    raw = 'event: done\ndata: {"ok": true}\n\n'
    assert stream_of(raw) == raw
    assert stream_of(json.dumps({"stream": raw})) == raw
    assert wp_error(json.dumps({"code": "x", "message": "no"})) == ("x", "no")


def test_describe_reads_sse_meta() -> None:
    stream = (
        'event: meta\ndata: {"fallback": true, "failures": ["chat 500"], '
        '"route": "products"}\n\n'
        'event: done\ndata: {"ok": true}\n\n'
    )
    result = HttpResult(
        200,
        "http://127.0.0.1/turn",
        [("Content-Type", "text/event-stream"), ("Date", "now")],
        json.dumps({"stream": stream}),
        None,
        1.25,
    )
    described = describe(result)
    assert described["done"] is True
    assert described["fallback"] is True
    assert described["failures"] == ["chat 500"]
    assert described["selected_headers"]["Date"] == "now"
    assert "token" not in described


def test_request_json_and_cookie_opener() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            payload = b'event: done\ndata: {"ok": true}\n\n'
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Set-Cookie", "linker_conversation=12.sig; Path=/")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    host_text = host.decode("ascii") if isinstance(host, bytes) else str(host)
    try:
        jar, opener = cookie_opener()
        result = request_json(
            f"http://{host_text}:{port}/turn",
            {"messages": []},
            {},
            5,
            opener,
        )
        assert result.http == 200
        assert describe(result)["done"] is True
        assert any(cookie.name == "linker_conversation" for cookie in jar)
    finally:
        server.shutdown()
        server.server_close()
