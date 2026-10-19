from __future__ import annotations

from sse import cut_sse, parse_sse

STREAM = (
    'event: meta\ndata: {"turn_id": 1, "fallback": false}\n\n'
    'event: block\ndata: {"type": "text", "text": "Half."}\n\n'
    'event: block\ndata: {"type": "text", "text": "Rest."}\n\n'
    'event: done\ndata: {"ok": true}\n\n'
)


def test_parse_keeps_names_and_done() -> None:
    parsed = parse_sse(STREAM)
    assert parsed["event_names"] == ["meta", "block", "block", "done"]
    assert parsed["done"] is True
    assert parsed["answer_text"] == "Half.\nRest."


def test_cut_stops_at_the_first_block_and_drops_done() -> None:
    shortened = cut_sse(STREAM.encode())
    parsed = parse_sse(shortened.decode())
    assert parsed["event_names"] == ["meta", "block"]
    assert parsed["done"] is False
    assert parsed["answer_text"] == "Half."
