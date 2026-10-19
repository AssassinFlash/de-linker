from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from faults import (
    TINY_JPEG,
    FaultServer,
    chat_payload,
    requested_model,
    silent_switch_reasons,
)
from sse import cut_marker, parse_sse


def test_requested_model_reads_the_json_field() -> None:
    assert requested_model(b'{"model": "deepseek-flash"}') == "deepseek-flash"
    assert requested_model(b"{}") == ""
    assert requested_model(b'{"model": 1}') == ""
    assert requested_model(b"not-json") == ""


def test_silent_switch_requires_deepseek_flash_and_zero_openrouter_hits() -> None:
    assert silent_switch_reasons(["deepseek-flash", "deepseek-flash"], 0) == []
    assert any(
        "other-model" in reason for reason in silent_switch_reasons(["other-model"], 0)
    )
    assert any(
        "no requested model" in reason for reason in silent_switch_reasons([], 0)
    )
    assert any(
        "OpenRouter" in reason
        for reason in silent_switch_reasons(["deepseek-flash"], 2)
    )


def test_chat_modes() -> None:
    status, body, content = chat_payload("500", 0)
    assert status == 500
    assert content == "application/json"
    assert json.loads(body)["error"]["code"] == "internal_error"
    status, body, content = chat_payload("empty", 0)
    assert status == 200
    assert content == "application/json"
    parsed = json.loads(body)
    assert "model" not in parsed
    status, body, content = chat_payload("empty-stream", 0)
    assert status == 200
    assert content == "text/event-stream"
    assert body == b""
    assert parse_sse(body.decode())["event_names"] == []
    assert parse_sse(body.decode())["done"] is False
    status, body, _content = chat_payload("429", 0)
    assert status == 429
    assert b"429" in body


def test_jpeg_magic() -> None:
    raw = base64.b64decode(TINY_JPEG)
    assert raw.startswith(b"\xff\xd8\xff")


def test_chat_server_answers_500() -> None:
    server = FaultServer("chat", mode="500")
    url = server.start()
    try:
        request = urllib.request.Request(
            url + "/v1/chat/completions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            raise AssertionError("500 should raise")
        except urllib.error.HTTPError as failure:
            try:
                assert failure.code == 500
                assert b"injected chat 500" in failure.read()
            finally:
                failure.close()
    finally:
        server.stop()


def test_stubs_record_the_requested_model_and_openrouter_hits() -> None:
    chat = FaultServer("chat", mode="500")
    router = FaultServer("openrouter")
    chat_url = chat.start()
    router_url = router.start()
    try:
        request = urllib.request.Request(
            chat_url + "/v1/chat/completions",
            data=b'{"model": "deepseek-flash"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as failure:
            failure.close()
        assert chat.requested_models() == ["deepseek-flash"]
        assert chat.openrouter_hits() == 0
        assert (
            silent_switch_reasons(chat.requested_models(), router.openrouter_hits())
            == []
        )
        hit = urllib.request.Request(
            router_url + "/api/v1/systemone",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(hit, timeout=5)
        except urllib.error.HTTPError as failure:
            assert failure.code == 502
            failure.close()
        assert router.openrouter_hits() == 1
        assert silent_switch_reasons(chat.requested_models(), router.openrouter_hits())
    finally:
        chat.stop()
        router.stop()


def test_empty_stream_server_returns_no_events() -> None:
    server = FaultServer("chat", mode="empty-stream")
    url = server.start()
    try:
        request = urllib.request.Request(
            url + "/v1/chat/completions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as reply:
            assert reply.status == 200
            assert reply.headers.get("Content-Type") == "text/event-stream"
            assert reply.read() == b""
    finally:
        server.stop()


def test_proxy_cuts_inside_a_partial_block_and_an_attachment() -> None:
    body = (
        b'event: meta\ndata: {"turn_id": 1}\n\n'
        b'event: attachment\ndata: {"id": "att11", "name": "plate.jpg"}\n\n'
        b'event: reading\ndata: {"id": "att11", "kind": "nameplate"}\n\n'
        b'event: block\ndata: {"type": "text", "text": "Half a block of text."}\n\n'
        b'event: done\ndata: {"ok": true}\n\n'
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    host, port = upstream.server_address[:2]
    host_text = host.decode("ascii") if isinstance(host, bytes) else str(host)
    try:
        for cut, banned in (
            ("partial-block", "event: done"),
            ("attachment", "event: reading"),
        ):
            proxy = FaultServer("cut", upstream=f"http://{host_text}:{port}", cut=cut)
            url = proxy.start()
            try:
                request = urllib.request.Request(
                    url + "/assistant/turn",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as reply:
                    raw = reply.read().decode()
                assert banned not in raw
                assert parse_sse(raw)["done"] is False
                report = proxy.cut_report()
                assert report["where"] == cut
                assert report["marker_present"] is True
                assert cut_marker(cut) in raw
                assert report["done_in_shortened"] is False
            finally:
                proxy.stop()
    finally:
        upstream.shutdown()
        upstream.server_close()
