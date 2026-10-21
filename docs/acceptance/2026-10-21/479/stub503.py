"""Local engine stub for ticket #479, row C22's second half.

The real engine answers 200 for the fixture postcode, and PVGIS is cached, so
the "yield service did not answer" path cannot be produced by a real request
on this machine. The walk starts this stub, points the site's
`linker_engine_url` option at it, submits the residential form, reads the
screens, then restores the option to the real engine. The browser request is
unchanged: page -> WP's EngineProxy -> this stub -> 503 back through the
proxy. No response is rewritten in the browser.

Run: python3 -I stub503.py [port]   (default 9333)
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9333


class Handler(BaseHTTPRequestHandler):
    """Answers the one path the residential submit calls."""

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server's spelling
        if self.path == "/design/residential":
            self._json(
                503,
                {
                    "detail": {
                        "error": "yield_unavailable",
                        "message": "stub: PVGIS did not answer",
                    }
                },
            )
        else:
            self._json(404, {"detail": "not found"})

    def do_GET(self) -> None:  # noqa: N802 - http.server's spelling
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"detail": "not found"})

    def log_message(self, fmt: str, *args: object) -> None:
        print("stub503:", fmt % args, flush=True)


if __name__ == "__main__":
    print(f"stub503: listening on 127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
