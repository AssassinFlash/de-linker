"""Attach source-bound physical evidence to unique native PDF chunks."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import replace
from typing import Any

from index.chunking import Chunk
from linker_genie.manual_diagram import model_list_descriptor, physical_descriptor
from linker_genie.manual_diagram_records import DIAGRAMS


def needs_diagram_evidence(sha: str) -> bool:
    return any(record["sha256"] == sha for record in DIAGRAMS)


def extract_diagram_evidence(
    pdf: Any, sha: str, chunks: list[Chunk]
) -> list[dict[str, object]]:
    """Check pixels on one SHA-verified source PDF, rendering each page once."""
    chunk_ids = {chunk.id for chunk in chunks}
    records = [
        record
        for record in DIAGRAMS
        if record["sha256"] == sha
        and record["source_id"] in chunk_ids
        and record["anchor_id"] in chunk_ids
    ]
    descriptors: list[dict[str, Any]] = []
    for record in records:
        for descriptor in (physical_descriptor(record), model_list_descriptor(record)):
            if descriptor not in descriptors:
                descriptors.append(descriptor)
    output: list[dict[str, object]] = []
    for number in sorted({descriptor["source_page"] for descriptor in descriptors}):
        if number < 1 or number > len(pdf):
            continue
        page = pdf[number - 1]
        try:
            if page.get_rotation() != 0:
                continue
            width, height = page.get_size()
            bitmap = page.render(scale=2)
            try:
                image = bitmap.to_pil().convert("RGB")
                for descriptor in descriptors:
                    if descriptor["source_page"] != number:
                        continue
                    left, top, right, bottom = descriptor["bbox"]
                    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                        continue
                    region = image.crop((left * 2, top * 2, right * 2, bottom * 2))
                    if (
                        list(region.size) == descriptor["pixel_size"]
                        and hashlib.sha256(region.tobytes()).hexdigest()
                        == descriptor["pixel_sha256"]
                    ):
                        output.append(descriptor)
            finally:
                bitmap.close()
        finally:
            page.close()
    return output


def attach_physical_evidence(
    chunks: list[Chunk], evidence: list[dict[str, object]]
) -> list[Chunk]:
    """Never attach evidence to an ambiguous, different-page or derived chunk."""
    counts = Counter(chunk.id for chunk in chunks)
    by_target: dict[str, list[dict[str, object]]] = {}
    for item in evidence:
        target = item.get("target_chunk_id")
        if isinstance(target, str) and counts[target] == 1:
            by_target.setdefault(target, []).append(item)
    output = []
    for chunk in chunks:
        attached = [
            item
            for item in by_target.get(chunk.id, [])
            if item.get("source_sha256") == chunk.doc_sha256
            and item.get("source_page") == chunk.page
            and (
                (
                    item.get("kind") == "manual_diagram"
                    and chunk.kind == "text"
                    and chunk.source_picture
                )
                or (
                    item.get("kind") == "manual_model_list"
                    and chunk.kind == "text"
                    and not chunk.source_picture
                )
                or (item.get("kind") == "iot_matrix" and chunk.kind == "table")
                or (item.get("kind") == "esa_iot_row" and chunk.kind == "table")
                or (item.get("kind") == "series_axis" and chunk.kind == "text")
            )
        ]
        output.append(
            replace(
                chunk,
                source_physical_evidence=(*chunk.source_physical_evidence, *attached),
            )
            if attached
            else chunk
        )
    return output
