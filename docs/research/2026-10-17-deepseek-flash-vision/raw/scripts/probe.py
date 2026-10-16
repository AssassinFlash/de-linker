"""One raw chat completion against the official DeepSeek API (model deepseek-flash only).

Usage: python3 -I probe.py image <png> <out.json>
       python3 -I probe.py pdf   <pdf> <out.json>

The request is recorded with the base64 payload replaced by a placeholder and
without the Authorization header; the key is read from
~/.config/terravolt-builder/deepseek.env and never printed or written.
"""

import base64
import datetime
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

NAMEPLATE_PROMPT = (
    "This photo shows the nameplate (rating label) of a device. Transcribe it exactly as "
    "printed: the brand, the model, the product type, every rating with its label and value, "
    "the serial number and any marks. Do not correct, complete or guess anything; write null "
    "for anything you cannot read. Answer in JSON: {\"brand\": str|null, \"model\": str|null, "
    "\"product_type\": str|null, \"ratings\": [{\"label\": str, \"value\": str}], "
    "\"serial\": str|null, \"marks\": [str]}"
)
PDF_PROMPT = "What does the attached PDF say? Quote its text."


def key() -> str:
    env = pathlib.Path("~/.config/terravolt-builder/deepseek.env").expanduser()
    for line in env.read_text().splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("no key")


def main() -> None:
    kind, path, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    placeholder = f"<base64 of raw/{path.name}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}>"
    if kind == "image":
        part = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}
        shown = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + placeholder}}
        prompt = NAMEPLATE_PROMPT
        extra = {"response_format": {"type": "json_object"}}
    elif kind == "pdf":
        # The `file` content part as the Chat Completions reference documents it (flat
        # `file_data` data URL + optional `filename`).
        part = {"type": "file", "file_data": "data:application/pdf;base64," + b64, "filename": path.name}
        shown = {"type": "file", "file_data": "data:application/pdf;base64," + placeholder, "filename": path.name}
        prompt = PDF_PROMPT
        extra = {}
    else:
        raise SystemExit("kind must be image or pdf")
    body = {"model": MODEL, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, part]}], **extra}
    shown_body = {"model": MODEL, "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, shown]}], **extra}
    raw = json.dumps(body).encode()
    req = urllib.request.Request(
        URL,
        data=raw,
        method="POST",
        headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json", "Accept": "application/json"},
    )
    started = datetime.datetime.now(datetime.UTC)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            status, headers, text = resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as err:
        status, headers, text = err.code, dict(err.headers), err.read().decode()
    elapsed = time.monotonic() - t0
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = text
    record = {
        "request": {
            "method": "POST",
            "url": URL,
            "headers": {"Authorization": "Bearer <DEEPSEEK_API_KEY>", "Content-Type": "application/json"},
            "body_bytes": len(raw),
            "body": shown_body,
        },
        "requested_at_utc": started.isoformat(timespec="seconds"),
        "wall_seconds": round(elapsed, 2),
        "status": status,
        "response_headers": {k: v for k, v in headers.items() if k.lower() not in {"set-cookie"}},
        "response": parsed,
    }
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(status, round(elapsed, 2), "s")


main()
