"""The production gate refuses before connecting. A local probe records the write."""

from __future__ import annotations

import json
import threading
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
