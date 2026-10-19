"""The production gate refuses before connecting. A local probe records the write."""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

import prod_smoke


def test_production_hosts() -> None:
    assert prod_smoke.is_production("https://de-linker.com")
    assert prod_smoke.is_production("https://www.de-linker.com/de")
    assert prod_smoke.is_production("https://DE-LINKER.com")
    assert prod_smoke.is_production("https://de-linker.com.")
    assert prod_smoke.is_production("https://www.de-linker.com.")
    assert not prod_smoke.is_production("http://127.0.0.1:9190")
    assert not prod_smoke.is_production("http://localhost:9190")
    assert not prod_smoke.is_production("https://staging.de-linker.com")


def test_production_without_confirm_exits_2_and_does_not_connect(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_run(*_args: object, **_kwargs: object) -> list[dict[str, Any]]:
        raise AssertionError("the client connected")

    monkeypatch.setattr(prod_smoke, "run", fail_run)
    assert prod_smoke.main(["--site", "https://de-linker.com"]) == 2
    assert prod_smoke.main(["--site", "https://www.de-linker.com"]) == 2
    assert prod_smoke.main(["--site", "https://de-linker.com."]) == 2
    captured = capsys.readouterr()
    assert "not read-only" in captured.err


def test_probes_are_one_question_each_and_do_not_name_inquiry() -> None:
    assert [item["id"] for item in prod_smoke.PROBES] == ["P-EN", "P-DE"]
    for item in prod_smoke.PROBES:
        assert len(item["messages"]) == 1
        assert item["messages"][0]["role"] == "user"
        text = json.dumps(item)
        assert "inquiry" not in text
        assert "contact" not in text


def test_module_says_it_writes() -> None:
    text = prod_smoke.__doc__ or ""
    assert "This client writes" in text
    assert "question-only" in text


def test_probe_records_final_url_headers_and_deletes() -> None:
    seen: dict[str, str | None] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802 - http.server's method name
            if self.path.endswith("/genie/turn"):
                host = self.headers.get("Host")
                location = f"http://{host}/wp-json/linker-ai/v1/genie/landed"
                self.send_response(307)
                self.send_header("Location", location)
                self.send_header("X-LiteSpeed-Cache", "hit")
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or "0")
            self.rfile.read(length)
            stream = (
                'data: {"turn_id": 7, "language": "en", "route": "products"}\n\n'
                'data: {"type": "text", "text": "The SAJ H2-10K-T3 pairs with '
                'the B2 battery."}\n\n'
            )
            body = json.dumps({"conversation_id": 42, "stream": stream}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.send_header("Server", "test-smoke")
            self.send_header("X-LiteSpeed-Cache", "miss")
            self.send_header("Set-Cookie", "linker_conversation=abc; Path=/; HttpOnly")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self) -> None:  # noqa: N802 - http.server's method name
            seen["cookie"] = self.headers.get("Cookie")
            seen["path"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    port = server.server_address[1]
    assert isinstance(port, int)
    try:
        result = prod_smoke.probe(prod_smoke.PROBES[0], f"http://127.0.0.1:{port}", 5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result["conversation_id"] == 42
    assert result["turn_id"] == 7
    assert result["delete_http"] == 200
    assert result["writes_conversation"] is True
    assert str(result["requested_url"]).endswith("/genie/turn")
    assert str(result["final_url"]).endswith("/genie/landed")
    assert result["final_url"] != result["requested_url"]
    headers = result["selected_headers"]
    assert headers["Server"] == "test-smoke"
    assert headers["X-LiteSpeed-Cache"] == "miss"
    assert "Location" not in headers
    cookie = seen["cookie"] or ""
    assert "linker_conversation=abc" in cookie
    assert str(seen["path"]).endswith("/conversations/42")
    assert result["error"] is None
    assert "H2-10K-T3" in result["answer_text"]
    assert result["answer_language"] == "en"


def test_redirect_to_production_is_not_followed_without_confirm() -> None:
    recorder = prod_smoke.RedirectRecord(allow_production=False)
    request = urllib.request.Request(
        "http://127.0.0.1:9190/wp-json/linker-ai/v1/genie/turn",
        data=b"{}",
        method="POST",
    )
    followed = recorder.redirect_request(
        request,
        None,
        307,
        "Temporary Redirect",
        {},
        "https://de-linker.com/wp-json/linker-ai/v1/genie/turn",
    )
    assert followed is None
    assert recorder.blocked_production == (
        "https://de-linker.com/wp-json/linker-ai/v1/genie/turn"
    )


def test_confirmed_production_redirect_keeps_the_post() -> None:
    recorder = prod_smoke.RedirectRecord(allow_production=True)
    request = urllib.request.Request(
        "http://127.0.0.1:9190/wp-json/linker-ai/v1/genie/turn",
        data=b'{"locale":"en"}',
        method="POST",
    )
    followed = recorder.redirect_request(
        request,
        None,
        308,
        "Permanent Redirect",
        {},
        "https://www.de-linker.com/wp-json/linker-ai/v1/genie/turn",
    )
    assert followed is not None
    assert followed.get_method() == "POST"
    assert followed.data == b'{"locale":"en"}'
    assert recorder.blocked_production is None


def test_probe_refuses_a_production_redirect_before_the_post_leaves() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802 - http.server's method name
            length = int(self.headers.get("Content-Length") or "0")
            self.rfile.read(length)
            self.send_response(307)
            self.send_header(
                "Location",
                "https://de-linker.com/wp-json/linker-ai/v1/genie/turn",
            )
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    port = server.server_address[1]
    assert isinstance(port, int)
    try:
        result = prod_smoke.probe(prod_smoke.PROBES[0], f"http://127.0.0.1:{port}", 2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert result["writes_conversation"] is False
    assert result["conversation_id"] is None
    assert "without --confirm-production" in str(result["error"])
    assert "de-linker.com" in str(result["error"])
