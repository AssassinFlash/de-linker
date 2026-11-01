"""Recover the reviewed ESA 5–30 kW rows from the original IoT PDF."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from index.chunking import Chunk

IOT = "6f33b8361fe25fa2798c424fd30c2601036a56212b9e62a312e6aadb060b8b3d"
TARGETS = {
    6: "6f33b8361fe2-p6-d2bb94e7",
    9: "6f33b8361fe2-p9-7a4f8c43",
    13: "6f33b8361fe2-p13-7680004c",
}
ROWS = {
    6: "ESA 5~30K Mass Production 745 √ √ √ √",
    9: (
        "ESA 5~30K Mass Production 745 √*1 *1 ARM≥03, DSP≥01; BMS≥06, "
        "DCDC≥ 08; DCDC-08 must be bound to BMS-06 or above versions. "
        "It cannot be upgraded to BMS-06 alone or DCDC-08 alone. "
        "BMS: 410-02167-06, DCDC: 410-04081-08"
    ),
    13: (
        "ESA 5-30K Three-phase parallel : 4+4 In total ≤4 √ √ DSP：2 ARM：4 "
        "Ezmanager：04 WIFILAN 2.0 Module（Cyber Security version）≥05"
    ),
}


def _span(tp: Any, text: str, start: int, end: int, height: float) -> dict[str, Any]:
    boxes = [tp.get_charbox(i) for i in range(start, end) if not text[i].isspace()]
    if not boxes:
        raise ValueError("empty PDF text span")
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


def _matches(tp: Any, text: str, pattern: str, height: float) -> list[dict[str, Any]]:
    return [
        _span(tp, text, m.start(), m.end(), height) for m in re.finditer(pattern, text)
    ]


def _center(span: dict[str, Any]) -> float:
    box = span["bbox"]
    return (float(box[0]) + float(box[2])) / 2


def extract_esa_evidence(
    pdf: Any, sha: str, chunks: Sequence[Chunk]
) -> list[dict[str, object]]:
    """Extract only the original row, its correct columns, and its complete note."""
    if sha != IOT:
        return []
    result: list[dict[str, object]] = []
    for number, target_id in TARGETS.items():
        candidates = [
            c
            for c in chunks
            if c.id == target_id
            and c.doc_sha256 == sha
            and c.page == number
            and c.kind == "table"
            and c.source_cells
        ]
        if len(candidates) != 1:
            continue
        page = pdf[number - 1]
        try:
            if page.get_rotation() != 0:
                continue
            width, height = page.get_size()
            tp = page.get_textpage()
            try:
                text = tp.get_text_range()
                start_name = "ESA 5-30K" if number == 13 else "ESA 5~30K"
                end_name = {6: "ES LD", 9: "XS G1/XS PLUS+", 13: "ETT"}[number]
                starts = list(re.finditer(re.escape(start_name), text))
                if len(starts) != 1:
                    continue
                start = starts[0].start()
                end_match = re.search(re.escape(end_name), text[start:])
                if end_match is None:
                    continue
                end = start + end_match.start()
                row = " ".join(text[start:end].split())
                if row != ROWS[number]:
                    continue
                model = _span(tp, text, starts[0].start(), starts[0].end(), height)
                row_marks = [
                    s
                    for s in _matches(tp, text, r"√(?:\*1)?", height)
                    if start < s["char_start"] < end
                ]
                if number == 6:
                    headers = _matches(tp, text[:start], r"GMK330", height)
                    ratios = _matches(
                        tp, text[:start], r"\((?:200A:50mA|120A:40mA)\)", height
                    )
                    if len(headers) != 2 or len(ratios) != 2 or len(row_marks) != 4:
                        continue
                    if any(
                        abs(_center(headers[i]) - _center(ratios[i])) > 2
                        for i in range(2)
                    ):
                        continue
                    chosen = row_marks[-2:]
                    if any(
                        abs(_center(headers[i]) - _center(chosen[i])) > 2
                        for i in range(2)
                    ):
                        continue
                    extras = ratios
                elif number == 9:
                    headers = _matches(tp, text[:start], r"EzManager3000", height)
                    chosen = row_marks
                    extras = []
                    if (
                        len(headers) != 1
                        or len(chosen) != 1
                        or abs(_center(headers[0]) - _center(chosen[0])) > 3
                    ):
                        continue
                else:
                    headers = _matches(
                        tp, text[:start], r"Ezmanager3000|WIFI/LAN Kit-20", height
                    )
                    chosen = row_marks
                    extra_matches = [
                        match
                        for pat in (r"Three-phase", r"parallel : 4\+4", r"In total ≤4")
                        for match in re.finditer(pat, text[start:end])
                    ]
                    # Offsets for the merged cells must refer to the full page.
                    extras = [
                        _span(
                            tp,
                            text,
                            start + match.start(),
                            start + match.end(),
                            height,
                        )
                        for match in extra_matches
                    ]
                    if (
                        len(headers) != 2
                        or len(chosen) != 2
                        or len(extras) != 3
                        or any(
                            abs(_center(headers[i]) - _center(chosen[i])) > 4
                            for i in range(2)
                        )
                    ):
                        continue
                if any(abs(mark["bbox"][1] - model["bbox"][1]) > 3 for mark in chosen):
                    continue
                result.append(
                    {
                        "kind": "esa_iot_row",
                        "source_sha256": sha,
                        "source_page": number,
                        "target_chunk_id": target_id,
                        "source_text": candidates[0].text,
                        "page_size": [round(width, 2), round(height, 2)],
                        "model": model,
                        "headers": headers,
                        "marks": chosen,
                        "extra_spans": extras,
                        "row_text": row,
                    }
                )
            finally:
                tp.close()
        finally:
            page.close()
    return result


def compile_esa(
    original: list[Chunk],
    source: Any,
    statuses: dict[str, str],
    tokenizer: Any,
    max_tokens: int,
    anchors: dict[str, dict[str, Any]],
) -> tuple[list[Chunk], dict[str, Any]]:
    """Compile separate IoT products; the inverter keeps its own manual grant."""
    from dataclasses import replace

    from linker_genie.compatibility_esa import (
        AXIS,
        IOT,
        MANUAL,
        MANUAL_METER,
        MODEL,
        P6,
        P9,
        P13,
        chunk_id,
        rendered,
        row_key,
        source_key,
        valid_row,
    )

    by_model = {str(p.get("model", "")): pid for pid, p in source.products.items()}
    inverter_id = by_model.get(MODEL)
    if (
        inverter_id is None
        or statuses.get(MODEL.casefold()) != "published"
        or source_key(AXIS) not in anchors
    ):
        return [], {}
    manuals = [
        d
        for d in source.documents.values()
        if d.get("blob_sha256") == MANUAL
        and (
            str(d.get("role", "")).strip() or str(d.get("type", "")).strip()
        ).casefold()
        in {"manual", "user_manual"}
        and inverter_id in d.get("product_ids", [])
        and d["document_id"] in source.products[inverter_id].get("documents", [])
    ]
    if len(manuals) != 1:
        return [], {}
    manual = manuals[0]
    output, scopes = [], {}
    for name, pages in (("GMK330", [(P6, 6)]), ("EzManager3000", [(P9, 9), (P13, 13)])):
        pid = by_model.get(name)
        if pid is None or statuses.get(name.casefold()) != "published":
            continue
        docs = [
            d
            for d in source.documents.values()
            if d.get("blob_sha256") == IOT
            and (
                str(d.get("role", "")).strip() or str(d.get("type", "")).strip()
            ).casefold()
            in {"compatibility", "compatibility_list"}
            and pid in d.get("product_ids", [])
            and d["document_id"] in source.products[pid].get("documents", [])
        ]
        needed = (
            [x[0] for x in pages]
            + [AXIS]
            + ([MANUAL_METER] if name == "GMK330" else [])
        )
        if len(docs) != 1 or any(
            source_key(x) not in anchors for x in needed if x in (AXIS, MANUAL_METER)
        ):
            continue
        if any(
            not isinstance(anchors.get(row_key(cid)), dict)
            or not valid_row(
                anchors[row_key(cid)],
                IOT,
                cid,
                str(anchors[row_key(cid)].get("source_text", "")),
            )
            or anchors[row_key(cid)].get("source_page") != page
            for cid, page in pages
        ):
            continue
        target = next((c for c in original if c.id == pages[0][0]), None)
        if target is None:
            continue
        text = rendered(name)
        cid = chunk_id(text, pages[0][1])
        header = f"{MODEL} | {name} | ESA 5–30 kW"
        tokens = tokenizer.count(header + "\n" + text)
        if tokens > max_tokens:
            continue
        doc = docs[0]
        link = {
            "document_id": doc["document_id"],
            "document_revision": doc["document_revision"],
            "blob_sha256": IOT,
            "product_id": pid,
            "product_revision": source.products[pid]["product_revision"],
        }
        proof = {
            "product_ids": [pid],
            "basis": "compatibility_esa",
            "source_chunk_ids": needed,
            "document_ids": [doc["document_id"]],
            "associations": [link],
            "compatibility_esa": {
                "device_id": pid,
                "inverter_id": inverter_id,
                "support_document": {
                    "document_id": manual["document_id"],
                    "document_revision": manual["document_revision"],
                    "product_revision": source.products[inverter_id][
                        "product_revision"
                    ],
                },
            },
        }
        output.append(
            replace(
                target,
                id=cid,
                kind="text",
                header=header,
                text=text,
                tokens=tokens,
                source_table="",
                source_rows=(),
                source_cells=(),
                source_headings=(),
                preceding_text=(),
                source_physical_evidence=(),
            )
        )
        scopes[cid] = proof
    return output, scopes
