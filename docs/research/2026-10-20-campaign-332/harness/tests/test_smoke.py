from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prod_smoke import (
    PROBES,
    SMOKE_CAP,
    deletion_holds,
    is_production,
    main,
    probe_failed,
    read_thread,
    thread_id,
)


def test_production_host_check() -> None:
    assert is_production("https://de-linker.com")
    assert is_production("https://DE-LINKER.com.")
    assert is_production("https://www.de-linker.com/path")
    assert not is_production("http://127.0.0.1:9187")


def test_smoke_is_at_most_five_turns() -> None:
    assert 1 <= len(PROBES) <= SMOKE_CAP


def test_production_is_refused_without_confirmation() -> None:
    assert main(["--site", "https://de-linker.com"]) == 2


def test_confirmed_run_requires_an_evidence_path() -> None:
    assert main(["--site", "https://de-linker.com", "--confirm-production"]) == 2
    assert main(["--site", "http://127.0.0.1:9187", "--confirm-production"]) == 2


def _clean(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "http": 200,
        "done": True,
        "delete_http": 200,
        "fallback": False,
        "failures": [],
        "deletion_holds": True,
        "probe": "P",
    }
    row.update(extra)
    return row


def test_a_degraded_turn_fails_the_smoke() -> None:
    assert probe_failed(_clean()) is False
    assert probe_failed(_clean(fallback=True)) is True
    assert probe_failed(_clean(failures=["chat 500"])) is True
    assert probe_failed(_clean(failures="chat 500")) is True
    assert probe_failed(_clean(deletion_holds=False)) is True
    assert probe_failed(_clean(delete_http=404)) is True


def test_deletion_holds_when_the_get_no_longer_names_the_id() -> None:
    assert deletion_holds(200, 0, 7572) is True
    assert deletion_holds(200, 7573, 7572) is True
    assert deletion_holds(200, 7572, 7572) is False
    assert deletion_holds(404, None, 7572) is True
    assert deletion_holds(None, None, 7572) is False
    assert deletion_holds(200, None, 7572) is False
    assert thread_id('{"conversation_id": 0}') == 0
    assert thread_id("not json") is None


def test_read_thread_gets_the_conversation_id() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            payload = json.dumps({"conversation_id": 0}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    host_text = host.decode("ascii") if isinstance(host, bytes) else str(host)
    try:
        opener = urllib.request.build_opener()
        http, found = read_thread(opener, f"http://{host_text}:{port}")
        assert http == 200
        assert found == 0
        assert deletion_holds(http, found, 7572) is True
    finally:
        server.shutdown()
        server.server_close()
