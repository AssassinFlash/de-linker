"""Page parsing and the turn client. The live Polylang tag puts href before hreflang."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import client


def test_german_alternate_accepts_the_live_attribute_order() -> None:
    live = (
        '<link rel="alternate" href="http://127.0.0.1:9190/de/" hreflang="de" />'
        '<link rel="alternate" href="http://127.0.0.1:9190/" hreflang="en" />'
    )
    assert client.german_alternate(live) == "http://127.0.0.1:9190/de/"
    href_last = '<link rel="alternate" hreflang="de" href="http://127.0.0.1:9190/de/">'
    assert client.german_alternate(href_last) == "http://127.0.0.1:9190/de/"
    assert client.mount(live)["de_url"] == "http://127.0.0.1:9190/de/"


def test_german_alternate_ignores_other_languages() -> None:
    html = '<link rel="alternate" href="http://127.0.0.1:9190/" hreflang="en" />'
    assert client.german_alternate(html) is None


def test_parse_sse_keeps_meta_and_blocks_and_drops_the_rest() -> None:
    stream = (
        'data: {"turn_id": 3, "route": "products"}\n\n'
        'data: {"type": "text", "text": "Hello"}\n\n'
        'event: done\ndata: {"ok": true}\n\n'
        "data: not-json\n\n"
        "data: [1]\n\n"
        "data: null\n\n"
    )
    meta, blocks = client.parse_sse(stream)
    assert meta is not None
    assert meta["turn_id"] == 3
    assert blocks == [{"type": "text", "text": "Hello"}]


def test_fetch_records_the_final_url_and_an_http_error() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802 - http.server's method name
            if self.path == "/gone":
                body = b"missing"
                self.send_response(404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = b"<main>hello</main>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    port = server.server_address[1]
    assert isinstance(port, int)
    try:
        page = client.fetch(f"http://127.0.0.1:{port}/page")
        missing = client.fetch(f"http://127.0.0.1:{port}/gone")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert page["status"] == 200
    assert page["error"] is None
    assert page["html"] == "<main>hello</main>"
    assert str(page["url"]).endswith("/page")
    assert missing["status"] == 404
    assert missing["error"] == "HTTP 404"

    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise urllib.error.URLError("connection refused")

    # Port 1 on this machine answers HTTP 503, so the refusal is injected.
    original = urllib.request.urlopen
    urllib.request.urlopen = refuse
    try:
        refused = client.fetch("http://127.0.0.1:9/", timeout=0.2)
    finally:
        urllib.request.urlopen = original
    assert refused["status"] == 0
    assert refused["error"] == "URLError: connection refused"
    assert refused["url"] == "http://127.0.0.1:9/"
