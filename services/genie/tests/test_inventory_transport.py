"""Actual REST transport keeps its Basic credential inside the configured origin."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from index.inventory import RestClient


@contextmanager
def endpoint(redirects: dict[str, str], received_auth: list[bool]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            pass

        def do_GET(self) -> None:
            received_auth.append(self.headers.get("Authorization") is not None)
            path = self.path.split("?", 1)[0]
            if path in redirects:
                self.send_response(302)
                self.send_header("Location", redirects[path])
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-WP-Total", "0")
            self.send_header("X-WP-TotalPages", "0")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"[]")

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def client(tmp_path: Path, base: str) -> RestClient:
    config = tmp_path / "rest.json"
    config.write_text(
        json.dumps(
            {
                "site_url": base,
                "username": "synthetic",
                "application_password": "synthetic-only",
            }
        )
    )
    config.chmod(0o600)
    return RestClient(config)


def test_inventory_never_forwards_authentication_to_another_origin(
    tmp_path: Path,
) -> None:
    source: list[bool] = []
    destination: list[bool] = []
    blocked = False
    with (
        endpoint({}, destination) as other,
        endpoint({"/wp-json/wp/v2/media": other + "/received"}, source) as base,
    ):
        try:
            client(tmp_path, base).get("/wp/v2/media", {"mime_type": "application/pdf"})
        except RuntimeError as error:
            blocked = "origin" in str(error)
    assert source == [True]
    assert destination == []
    assert blocked


def test_same_origin_redirect_preserves_the_native_authenticated_read(
    tmp_path: Path,
) -> None:
    received: list[bool] = []
    with endpoint({"/wp-json/redirect": "/wp-json/wp/v2/media"}, received) as base:
        assert client(tmp_path, base).get("/redirect", {}) == ([], 0, 0)
    assert received == [True, True]
