"""Optional loopback preview for browsers that accept HTTP/HTTPS only.

The prototype itself is a self-contained file and works without this helper.
Only the fixed prototype bytes are served. No directory browsing, arbitrary
file routes, APIs, uploads, cookies, database, or external requests.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PROTOTYPE = Path(__file__).with_name("prototype.html")


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path not in ("/", "/prototype.html"):
            self.send_error(404)
            return
        body = PROTOTYPE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


print("Prototype preview: http://127.0.0.1:8793/", flush=True)
HTTPServer(("127.0.0.1", 8793), Preview).serve_forever()
