"""Read reviewed compatibility axes from their original, already-open PDFs.

These source documents are immutable content-addressed manufacturer originals.
The small allowlist limits physical inspection to the documents reviewed for
this capability; every returned item is still bound to its native text/table.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from index.chunking import Chunk
from index.extract import _pdf_model_spans

ET = "4f7178042e8faf03bd926dc33a5ff0b85ffcd4f46e12f1dcf86d6db10befee4d"
ETR = "76df70ea8474531fb1f1d168b6faf3262cf2242358be9ba9d17b5f2fb5e75afd"
IOT = "6f33b8361fe25fa2798c424fd30c2601036a56212b9e62a312e6aadb060b8b3d"
SOURCES = frozenset({ET, ETR, IOT})
ESA_MODEL = "GW125/261-ESA-LCN-G10"


def needs_compatibility_evidence(sha: str) -> bool:
    return sha in SOURCES


def _box(span: Mapping[str, Any]) -> list[float]:
    return [round(float(v), 2) for v in span["bbox"]]


def _span(
    textpage: Any, text: str, start: int, end: int, height: float
) -> dict[str, Any]:
    boxes = [
        textpage.get_charbox(i) for i in range(start, end) if not text[i].isspace()
    ]
    if not boxes:
        raise ValueError("empty physical span")
    return {
        "text": text[start:end],
        "char_start": start,
        "char_end": end,
        "bbox": [
            round(min(b[0] for b in boxes), 2),
            round(height - max(b[3] for b in boxes), 2),
            round(max(b[2] for b in boxes), 2),
            round(height - min(b[1] for b in boxes), 2),
        ],
    }


def _one_target(
    chunks: Sequence[Chunk], sha: str, page: int, kind: str
) -> Chunk | None:
    candidates = [
        chunk
        for chunk in chunks
        if chunk.doc_sha256 == sha
        and chunk.page == page
        and chunk.kind == kind
        and (
            (kind == "table" and bool(chunk.source_cells))
            or (kind == "text" and "Technical Data" in chunk.text)
        )
    ]
    return candidates[0] if len(candidates) == 1 else None


def _series_axis(
    pdf: Any, sha: str, chunks: Sequence[Chunk]
) -> list[dict[str, object]]:
    target = _one_target(chunks, sha, 2, "text")
    if target is None:
        return []
    family = "ET" if sha == ET else "ETR"
    pattern = re.compile(rf"GW\d+(?:\.\d+)?K-{family}-G10")
    parsed = re.sub(r"(?<=-)\s+(?=[A-Za-z0-9])", "", target.text)
    labels = pattern.findall(parsed)
    if len(labels) < 2 or len(labels) != len(set(labels)):
        return []
    page = pdf[1]
    try:
        if page.get_rotation() != 0:
            return []
        height = page.get_height()
        tp = page.get_textpage()
        try:
            text = tp.get_text_range()
            if len(text) != tp.count_chars():
                return []
            title_match = list(re.finditer(rf"\b{family} Series\b", text))
            heading_match = list(re.finditer(r"\bTechnical Data\b", text))
            if len(title_match) != 1 or len(heading_match) != 1:
                return []
            title = _span(tp, text, *title_match[0].span(), height)
            heading = _span(tp, text, *heading_match[0].span(), height)
            spans = [
                s
                for s in _pdf_model_spans(pdf, 2, sha)
                if s["text"] in labels and s["bbox"][1] < 115
            ]
            if len(spans) != len(labels) or [s["text"] for s in spans] != labels:
                return []
            models: list[dict[str, Any]] = [
                {
                    "text": s["text"],
                    "char_start": s["char_start"],
                    "char_end": s["char_end"],
                    "bbox": _box(s),
                }
                for s in spans
            ]
            if (
                title["bbox"][3] >= heading["bbox"][1]
                or any(s["bbox"][0] <= heading["bbox"][2] for s in models)
                or any(abs(s["bbox"][1] - heading["bbox"][1]) > 8 for s in models)
                or any(
                    a["bbox"][2] >= b["bbox"][0]
                    for a, b in zip(models, models[1:], strict=False)
                )
            ):
                return []
            return [
                {
                    "kind": "series_axis",
                    "source_sha256": sha,
                    "source_page": 2,
                    "target_chunk_id": target.id,
                    "source_text": target.text,
                    "page_size": [round(page.get_width(), 2), round(height, 2)],
                    "family": family,
                    "title": title,
                    "heading": heading,
                    "models": models,
                }
            ]
        finally:
            tp.close()
    finally:
        page.close()


def _iot_axis(
    pdf: Any, sha: str, chunks: Sequence[Chunk], number: int
) -> list[dict[str, object]]:
    target = _one_target(chunks, sha, number, "table")
    if target is None:
        return []
    page = pdf[number - 1]
    try:
        if page.get_rotation() != 0:
            return []
        height = page.get_height()
        tp = page.get_textpage()
        try:
            text = tp.get_text_range()
            if len(text) != tp.count_chars():
                return []
            spans = _pdf_model_spans(pdf, number, sha)
            rows = [s for s in spans if s["text"] in (ESA_MODEL, ESA_MODEL[:-1] + "1")]
            if len(rows) != 2 or rows[0]["text"] != ESA_MODEL:
                return []
            start, end = rows[0]["char_start"], rows[1]["char_start"]
            raw_row = text[start:end].replace("￾", "-")
            row = " ".join(raw_row.split())
            expected = (
                "GW125/261-ESA-LCN-G10 ESA261 Mass Production 745 √*1 "
                "*1 Supports single-unit anti-reflux: overseas ESA261 connects to "
                "SEC3000C, SEC3000C connects to GM330; requires paired SEC3000C version ≥03."
                if number == 7
                else "GW125/261-ESA-LCN-G10 ESA261 Mass Production 745 √*3 "
                "*3 ARM：LC：410-02134-01(66) DSP：master:410-04077-02(29) "
                "DSP：slave：410-04078-01(06) Control board:410-02193-01(14)Dual "
                "network ports、410-02174-01(14) Single network port "
                "*For global, Can't parellel with ET50 and ESA261"
            )
            if row != expected:
                return []
            names = (
                ("GM3000C", "GM330", "GMK120")
                if number == 7
                else ("SEC3000", "SEC3000C", "EzManager3000")
            )
            heads = [
                next(
                    (s for s in spans if s["text"] == name and s["bbox"][1] < 180), None
                )
                for name in names
            ]
            if any(h is None for h in heads):
                return []
            marks = [m for m in re.finditer(r"√\*[13]", text[start:end])]
            if len(marks) != 1:
                return []
            mark = _span(
                tp, text, start + marks[0].start(), start + marks[0].end(), height
            )
            boxes = [_box(h) for h in heads if h is not None]
            centres = [(b[0] + b[2]) / 2 for b in boxes]
            x = (mark["bbox"][0] + mark["bbox"][2]) / 2
            row_box = _box(rows[0])
            if (
                not (centres[0] < centres[1] < centres[2])
                or min(range(3), key=lambda i: abs(centres[i] - x)) != 1
                or not (row_box[1] - 3 <= mark["bbox"][1] <= row_box[3] + 3)
                or mark["bbox"][3] >= rows[1]["bbox"][1]
            ):
                return []
            return [
                {
                    "kind": "iot_matrix",
                    "source_sha256": sha,
                    "source_page": number,
                    "target_chunk_id": target.id,
                    "source_text": target.text,
                    "page_size": [round(page.get_width(), 2), round(height, 2)],
                    "model": ESA_MODEL,
                    "model_box": row_box,
                    "neighbour_box": _box(rows[1]),
                    "headers": [
                        {"text": h["text"], "bbox": _box(h)} for h in heads if h
                    ],
                    "mark": mark,
                    "row_text": row,
                }
            ]
        finally:
            tp.close()
    finally:
        page.close()


def extract_compatibility_evidence(
    pdf: Any, sha: str, chunks: list[Chunk]
) -> list[dict[str, object]]:
    """Extract only complete, physically aligned reviewed rows and source axes."""
    if sha not in SOURCES:
        return []
    if sha == IOT:
        return _iot_axis(pdf, sha, chunks, 7) + _iot_axis(pdf, sha, chunks, 9)
    return _series_axis(pdf, sha, chunks)
