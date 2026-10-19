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
    assert prod_smoke.is_production("https://DE-LINKER.COM./de")
    assert prod_smoke.is_production("https://WWW.DE-LINKER.COM.")
    assert not prod_smoke.is_production("http://127.0.0.1:9162")
    assert not prod_smoke.is_production("http://localhost:9162")
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


def test_module_does_not_call_the_run_read_only() -> None:
    text = prod_smoke.__doc__ or ""
    assert "This client writes" in text
    assert "7444" in text
    assert "90" in text


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
                self.send_header("Date", "Mon, 19 Oct 2026 09:44:00 GMT")
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or "0")
            self.rfile.read(length)
            stream = 'data: {"turn_id": 7, "language": "en", "route": "products"}\n\n'
            body = json.dumps({"conversation_id": 42, "stream": stream}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=UTF-8")
            self.send_header("Server", "test-smoke")
            self.send_header("Date", "Mon, 19 Oct 2026 09:44:01 GMT")
            self.send_header("X-Robots-Tag", "noindex")
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
    assert result["redirect_chain"] == [
        {
            "status": 307,
            "from": result["requested_url"],
            "location": result["final_url"],
        }
    ]
    headers = result["selected_headers"]
    assert headers["Server"] == "test-smoke"
    assert headers["Content-Type"] == "application/json; charset=UTF-8"
    assert headers["X-Robots-Tag"] == "noindex"
    assert "X-Powered-By" not in headers
    assert "Location" not in headers
    cookie = seen["cookie"] or ""
    assert "linker_conversation=abc" in cookie
    assert str(seen["path"]).endswith("/conversations/42")
    assert result["error"] is None
    assert result["stream_truncated"] is False


def _probe_item(probe_id: str, content: str) -> dict[str, Any]:
    return {
        "id": probe_id,
        "local": probe_id,
        "locale": "en",
        "messages": [{"role": "user", "content": content}],
    }


def _serve(
    handler: type[BaseHTTPRequestHandler],
) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    port = server.server_address[1]
    assert isinstance(port, int)
    return server, thread, port


def test_502_deletes_from_the_cookie_and_keeps_the_next_line(tmp_path: Any) -> None:
    deleted: list[str] = []
    gets: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(length))
            content = payload["messages"][0]["content"]
            if content == "fail":
                body = json.dumps(
                    {
                        "code": "linker_genie_upstream",
                        "message": "Genie did not answer.",
                    }
                ).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header(
                    "Set-Cookie", "linker_conversation=77.deadbeef; Path=/; HttpOnly"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            stream = 'data: {"turn_id": 8, "language": "en"}\n\n'
            body = json.dumps({"conversation_id": 42, "stream": stream}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            gets.append(self.path)
            body = b'{"conversation_id": 0, "messages": [], "stream": ""}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self) -> None:  # noqa: N802
            deleted.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

    server, thread, port = _serve(Handler)
    sink = tmp_path / "smoke.jsonl"
    try:
        results = prod_smoke.run(
            f"http://127.0.0.1:{port}",
            probes=[_probe_item("P1", "fail"), _probe_item("P2", "ok")],
            timeout=5,
            sink=sink,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert results[0]["http"] == 502
    assert results[0]["error"] == "HTTP 502"
    assert results[0]["conversation_id"] == 77
    assert results[0]["writes_conversation"] is True
    assert results[0]["delete_http"] == 200
    assert results[1]["conversation_id"] == 42
    assert results[1]["error"] is None
    assert results[1]["delete_http"] == 200
    assert gets == []
    assert any(path.endswith("/conversations/77") for path in deleted)
    assert any(path.endswith("/conversations/42") for path in deleted)
    lines = [json.loads(line) for line in sink.read_text().splitlines() if line]
    assert [line["probe"] for line in lines] == ["P1", "P2"]
    assert prod_smoke.failed_probes(results) == ["P1"]


def test_502_without_a_parseable_cookie_reads_then_deletes() -> None:
    deleted: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            self.rfile.read(length)
            body = b'{"code":"linker_genie_upstream","message":"Genie did not answer."}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            body = b'{"conversation_id": 88, "messages": [], "stream": ""}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self) -> None:  # noqa: N802
            deleted.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

    server, thread, port = _serve(Handler)
    try:
        result = prod_smoke.probe(
            _probe_item("P", "fail"), f"http://127.0.0.1:{port}", 5
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result["conversation_id"] == 88
    assert result["delete_http"] == 200
    assert result["error"] == "HTTP 502"
    assert any(path.endswith("/conversations/88") for path in deleted)


def test_non_envelope_200_is_an_error_and_still_deletes() -> None:
    deleted: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            self.rfile.read(length)
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Set-Cookie", "linker_conversation=55.sig; Path=/; HttpOnly"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self) -> None:  # noqa: N802
            deleted.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

    server, thread, port = _serve(Handler)
    try:
        result = prod_smoke.probe(
            _probe_item("P", "odd"), f"http://127.0.0.1:{port}", 5
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result["http"] == 200
    assert result["error"] == "HTTP 200 body is not a conversation envelope"
    assert result["conversation_id"] == 55
    assert result["writes_conversation"] is True
    assert result["delete_http"] == 200
    assert prod_smoke.failed_probes([result]) == ["P"]
    assert any(path.endswith("/conversations/55") for path in deleted)
