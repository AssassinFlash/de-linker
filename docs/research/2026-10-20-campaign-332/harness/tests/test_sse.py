from __future__ import annotations

import pytest

from sse import cut_marker, cut_sse, parse_sse

STREAM = (
    'event: meta\ndata: {"turn_id": 1, "fallback": false}\n\n'
    'event: block\ndata: {"type": "text", "text": "Half."}\n\n'
    'event: block\ndata: {"type": "text", "text": "Rest."}\n\n'
    'event: done\ndata: {"ok": true}\n\n'
)

# app.py `_sse` order: meta, attachment, reading, block, done.
WITH_FILE = (
    'event: meta\ndata: {"turn_id": 2}\n\n'
    'event: attachment\ndata: {"id": "att11", "name": "plate.jpg"}\n\n'
    'event: reading\ndata: {"id": "att11", "kind": "nameplate", "model": "H2-10K-T3"}\n\n'
    'event: block\ndata: {"type": "text", "text": "The nameplate reads H2-10K-T3."}\n\n'
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


def test_cut_inside_a_partial_block_drops_the_rest() -> None:
    shortened = cut_sse(STREAM.encode(), "partial-block")
    text = shortened.decode()
    assert "event: block" in text
    assert "event: done" not in text
    assert not text.endswith("\n\n")
    parsed = parse_sse(text)
    assert parsed["done"] is False
    assert parsed["answer_text"] == ""
    assert "block" not in parsed["event_names"] or parsed["blocks"] == []


def test_cut_inside_an_attachment_event() -> None:
    shortened = cut_sse(WITH_FILE.encode(), "attachment")
    text = shortened.decode()
    assert "event: attachment" in text
    assert "event: reading" not in text
    assert "event: block" not in text
    assert "event: done" not in text
    parsed = parse_sse(text)
    assert parsed["done"] is False
    assert parsed["blocks"] == []


def test_cut_inside_a_reading_event_keeps_the_attachment() -> None:
    shortened = cut_sse(WITH_FILE.encode(), "reading")
    text = shortened.decode()
    assert "event: attachment" in text
    assert "event: reading" in text
    assert "event: block" not in text
    assert "event: done" not in text
    parsed = parse_sse(text)
    assert parsed["done"] is False
    assert parsed["event_names"][0] == "meta"


def test_after_block_keeps_attachment_and_reading() -> None:
    shortened = cut_sse(WITH_FILE.encode(), "after-block")
    parsed = parse_sse(shortened.decode())
    assert parsed["event_names"] == ["meta", "attachment", "reading", "block"]
    assert parsed["done"] is False
    assert "H2-10K-T3" in parsed["answer_text"]


def test_cut_marker_is_the_one_table() -> None:
    assert cut_marker("after-block") == "event: block"
    assert cut_marker("partial-block") == "event: block"
    assert cut_marker("attachment") == "event: attachment"
    assert cut_marker("reading") == "event: reading"
    assert cut_marker("reset") == ""


def test_unknown_cut_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown cut"):
        cut_sse(STREAM.encode(), "middle")
