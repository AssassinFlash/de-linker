"""GET an official DeepSeek API path; write status, headers and body to a file.

Usage: python3 -I dsget.py <path> <outfile>
The key is read from ~/.config/terravolt-builder/deepseek.env and is never
printed or written; the output records the request without it.
"""

import datetime
import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = "https://api.deepseek.com"


def key() -> str:
    env = pathlib.Path("~/.config/terravolt-builder/deepseek.env").expanduser()
    for line in env.read_text().splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("no key")


def main() -> None:
    path, out = sys.argv[1], sys.argv[2]
    url = BASE + path
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key(), "Accept": "application/json"})
    started = datetime.datetime.now(datetime.UTC)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, headers, body = resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as err:
        status, headers, body = err.code, dict(err.headers), err.read().decode()
    record = {
        "request": {"method": "GET", "url": url, "headers": {"Authorization": "Bearer <DEEPSEEK_API_KEY>"}},
        "requested_at_utc": started.isoformat(timespec="seconds"),
        "status": status,
        "response_headers": {k: v for k, v in headers.items() if k.lower() not in {"set-cookie"}},
        "body": json.loads(body) if body.strip().startswith(("{", "[")) else body,
    }
    pathlib.Path(out).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(status)


main()
