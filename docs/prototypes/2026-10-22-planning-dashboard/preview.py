#!/usr/bin/env python3
"""Loopback-only, no-write preview of a throwaway UI prototype."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes

ROOT = Path(__file__).resolve().parent
FILES = {
    "/": ROOT / "prototype.html",
    "/solution-configurator/": ROOT / "prototype.html",
    "/de/loesungskonfigurator/": ROOT / "prototype.html",
    "/assets/prototype.css": ROOT / "prototype.css",
    "/assets/prototype.js": ROOT / "prototype.js",
    "/assets/linker-logo.webp": ROOT / "assets/linker-logo.webp",
}
for font in ("400", "500", "600", "700"):
    FILES["/assets/plus-jakarta-sans-" + font + ".ttf"] = ROOT / ("assets/plus-jakarta-sans-" + font + ".ttf")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        file = FILES.get(path)
        if file is None:
            self.send_error(404)
            return
        data = file.read_bytes()
        mime = mimetypes.guess_type(file)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8794)
args = parser.parse_args()
server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
print(f"Planning dashboard prototype: http://127.0.0.1:{args.port}/solution-configurator/?variant=A&lang=zh", flush=True)
server.serve_forever()
