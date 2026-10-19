from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from faults import TINY_JPEG, FaultServer, chat_payload


def test_chat_modes() -> None:
    status, body, content = chat_payload("500", b"{}", 0)
    assert status == 500
    assert content == "application/json"
    assert json.loads(body)["error"]["code"] == "internal_error"
    status, body, content = chat_payload("empty", b'{"stream": true}', 0)
    assert status == 200
    assert content == "text/event-stream"
    assert b"[DONE]" in body
    status, body, _content = chat_payload("429", b"{}", 0)
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
