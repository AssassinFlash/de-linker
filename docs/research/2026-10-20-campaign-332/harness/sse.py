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


# Dossier §2 item 4 (2026-10-19): cut inside a half-written block, and cut
# inside an attachment event. The reading event is the pair the proxy stores
# with that attachment (app.py `_sse`). `after-block` is the cut the recorded
# SSE-CUT turn used: the first block event is complete, and `done` is gone.
# One table: cut_sse shortens at this line, and the proxy's cut report reads it.
_MARKERS = {
    "after-block": "event: block",
    "partial-block": "event: block",
    "attachment": "event: attachment",
    "reading": "event: reading",
}
CUTS = tuple(_MARKERS)


def cut_marker(where: str) -> str:
    """The event line a cut looks for. Empty for `reset` and any non-cut."""
    return _MARKERS.get(where, "")


def cut_sse(raw: bytes, where: str = "after-block") -> bytes:
    """Shorten a Genie SSE body and drop `done`.

    `after-block` keeps every complete event through the first `block`.
    `partial-block`, `attachment` and `reading` stop inside that event, so
    the event's own payload is not a finished SSE record.
    """
    if where not in CUTS:
        raise ValueError(f"unknown cut {where}")
    text = raw.decode("utf-8", "replace")
    marker = cut_marker(where)
    if where == "after-block":
        return _cut_after(text, marker)
    return _cut_inside(text, marker)


def _cut_after(text: str, marker: str) -> bytes:
    kept: list[str] = []
    for part in text.split("\n\n"):
        if not part.strip():
            continue
        kept.append(part)
        if part.startswith(marker):
            break
    if not kept:
        return b""
    return ("\n\n".join(kept) + "\n\n").encode()


def _cut_inside(text: str, marker: str) -> bytes:
    """Bytes through the middle of `marker`'s event, with no closing blank line."""
    start = text.find(marker)
    if start < 0:
        return b""
    end = text.find("\n\n", start)
    if end < 0:
        end = len(text)
    event = text[start:end]
    # Past the event name, inside the data line, so the JSON does not close
    # and the following events (including `done`) are not in the body.
    midpoint = start + max(len(marker) + 1, len(event) // 2)
    return text[:midpoint].encode()
