"""Parse a Genie SSE body the way the shell does, and keep every event name.

`parseStream` in plugins/linker-tools/src/genie/api/turn.ts throws when `done`
is missing. This parser records that fact instead of raising, so a cut stream
stays evidence.
"""

from __future__ import annotations

import json
import re
from typing import Any

_NAME = re.compile(r"^event: (.+)$", re.MULTILINE)
_DATA = re.compile(r"^data: (.+)$", re.MULTILINE)


def parse_sse(stream: str) -> dict[str, Any]:
    """Return events, meta, blocks, whether `done` arrived, and joined text."""
    events: list[dict[str, Any]] = []
    meta: dict[str, Any] | None = None
    blocks: list[dict[str, Any]] = []
    done = False
    for raw in stream.split("\n\n"):
        if not raw.strip():
            continue
        name_match = _NAME.search(raw)
        data_match = _DATA.search(raw)
        if name_match is None or data_match is None:
            events.append({"event": "malformed", "raw": raw[:500]})
            continue
        name = name_match.group(1).strip()
        try:
            payload = json.loads(data_match.group(1))
        except json.JSONDecodeError:
            events.append({"event": name, "json_error": True, "raw": raw[:500]})
            continue
        events.append({"event": name, "data": payload})
        if name == "meta" and isinstance(payload, dict):
            meta = payload
        elif name == "block" and isinstance(payload, dict):
            blocks.append(payload)
        elif name == "done":
            done = True
    return {
        "events": events,
        "event_names": [item["event"] for item in events],
        "meta": meta,
        "blocks": blocks,
        "done": done,
        "answer_text": answer_text(blocks),
    }


def answer_text(blocks: list[dict[str, Any]]) -> str:
    """Text the customer can read: text blocks, handoff summaries, document titles."""
    parts: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif kind == "handoff" and isinstance(block.get("summary"), str):
            parts.append(block["summary"])
        elif kind == "document" and isinstance(block.get("title"), str):
            parts.append(block["title"])
    return "\n".join(parts)


def cut_sse(raw: bytes) -> bytes:
    """Keep bytes through the first `block` event and drop `done`.

    A clean close after this body is the mid-stream cut: the HTTP status can
    still be 200, and the shell's parser must refuse the unfinished stream.
    """
    text = raw.decode("utf-8", "replace")
    kept: list[str] = []
    for part in text.split("\n\n"):
        if not part.strip():
            continue
        kept.append(part)
        if part.startswith("event: block"):
            break
    if not kept:
        return b""
    return ("\n\n".join(kept) + "\n\n").encode()
