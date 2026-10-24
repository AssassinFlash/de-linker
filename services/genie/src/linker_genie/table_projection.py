"""Deterministic model-column projections of immutable native table cells.

This module has no parser, provider or storage dependency. The offline compiler,
SQLite preparation and live retrieval all use the same reconstruction rule.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

from linker_genie.source_models import (
    family_labels,
    model_pattern,
    model_shapes,
    unknown_models,
)


class SourceSpan(TypedDict):
    """One original visible PDF text-layer token, in cropped page coordinates."""

    text: str
    bbox: tuple[float, float, float, float]
    char_start: int
    char_end: int
    page: int
    source_sha256: str
    page_size: tuple[float, float]


class SourceCell(TypedDict):
    """Original Docling cell coordinates; end offsets are exclusive."""

    row_start: int
    row_end: int
    col_start: int
    col_end: int
    text: str
    column_header: bool
    row_header: bool
    row_section: bool
    bbox: tuple[float, float, float, float] | None
    bbox_origin: str
    model_spans: NotRequired[list[SourceSpan]]


TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]*")


def read_cells(value: object) -> tuple[SourceCell, ...] | None:
    """Validate native coordinates without guessing across gaps or overlaps."""
    if not isinstance(value, (list, tuple)) or not value:
        return None
    output: list[SourceCell] = []
    for cell in value:
        if not isinstance(cell, dict):
            return None
        if any(
            type(cell.get(key)) is not int or cell[key] < 0
            for key in ["row_start", "row_end", "col_start", "col_end"]
        ) or any(
            type(cell.get(key)) is not bool
            for key in ["column_header", "row_header", "row_section"]
        ):
            return None
        if (
            cell["row_end"] <= cell["row_start"]
            or cell["col_end"] <= cell["col_start"]
            or not isinstance(cell.get("text"), str)
        ):
            return None
        box = cell.get("bbox")
        if box is not None:
            if (
                not isinstance(box, (tuple, list))
                or len(box) != 4
                or any(type(n) not in (int, float) or not math.isfinite(n) for n in box)
                or cell.get("bbox_origin") not in {"TOPLEFT", "BOTTOMLEFT"}
            ):
                return None
        elif cell.get("bbox_origin") != "":
            return None
        spans = cell.get("model_spans", [])
        if not isinstance(spans, list):
            return None
        for span in spans:
            if (
                not isinstance(span, dict)
                or not isinstance(span.get("text"), str)
                or not isinstance(span.get("source_sha256"), str)
                or any(
                    type(span.get(k)) is not int
                    for k in ["char_start", "char_end", "page"]
                )
                or span["char_start"] < 0
                or span["char_end"] <= span["char_start"]
                or span["page"] <= 0
                or not isinstance(span.get("bbox"), (list, tuple))
                or len(span["bbox"]) != 4
                or any(
                    type(n) not in (int, float) or not math.isfinite(n)
                    for n in span["bbox"]
                )
                or not isinstance(span.get("page_size"), (list, tuple))
                or len(span["page_size"]) != 2
                or any(
                    type(n) not in (int, float) or not math.isfinite(n) or n <= 0
                    for n in span["page_size"]
                )
                or not (0 <= span["bbox"][0] < span["bbox"][2] <= span["page_size"][0])
                or not (0 <= span["bbox"][1] < span["bbox"][3] <= span["page_size"][1])
            ):
                return None
        typed = SourceCell(
            row_start=cell["row_start"],
            row_end=cell["row_end"],
            col_start=cell["col_start"],
            col_end=cell["col_end"],
            text=cell["text"],
            column_header=cell["column_header"],
            row_header=cell["row_header"],
            row_section=cell["row_section"],
            bbox=(box[0], box[1], box[2], box[3]) if box is not None else None,
            bbox_origin=cell["bbox_origin"],
        )
        if spans:
            typed["model_spans"] = spans
        output.append(typed)
    return tuple(output)


def cells_digest(cells: Sequence[SourceCell]) -> str:
    """Bind native text, ordering, spans and role flags together."""
    return hashlib.sha256(
        json.dumps(list(cells), ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def cell_at(cells: Sequence[SourceCell], row: int, col: int) -> SourceCell | None:
    """A cell applies only where one original span explicitly covers the slot."""
    found = [
        cell
        for cell in cells
        if cell["row_start"] <= row < cell["row_end"]
        and cell["col_start"] <= col < cell["col_end"]
    ]
    return found[0] if len(found) == 1 else None


def _axis_labels(text: str) -> list[str]:
    tokens = TOKEN.findall(text)
    labels = [
        token
        for token in tokens
        if any(c.isalpha() for c in token) and any(c.isdigit() for c in token)
    ]
    # A few native heading cells also contain the first numeric value. It is
    # not an extra model and is never emitted as a property value from the axis.
    residual = text
    for token in tokens:
        if token in labels or not any(c.isalpha() for c in token):
            residual = residual.replace(token, "", 1)
    return labels if not residual.strip(" \t,;•⚫") else []


def _model_axis_data(
    cells: Sequence[SourceCell],
) -> tuple[list[str], list[float], tuple[float, float]] | None:
    """The first native header row supplies one exact ordered label per column.

    A merged model-list cell needs one original physical text span per value
    column; its extracted string order is not trusted. An ambiguous or incomplete
    axis cannot be repaired by current-product names or parameter values.
    """
    width = max((cell["col_end"] for cell in cells), default=0)
    if width < 2:
        return None
    axis: list[str] = []
    positions: list[float] = []
    page_size: tuple[float, float] | None = None
    col = 1
    while col < width:
        cell = cell_at(cells, 0, col)
        if (
            cell is None
            or cell["row_start"] != 0
            or cell["row_end"] != 1
            or not cell["column_header"]
            or cell["col_start"] != col
        ):
            return None
        labels = _axis_labels(cell["text"])
        if len(labels) != cell["col_end"] - cell["col_start"]:
            return None
        # A single-label native header needs the same visible text-layer proof
        # as a merged one. Logical offsets cannot make hidden/off-crop text
        # into the axis of a displayed table.
        spans = cell.get("model_spans", [])
        box = cell["bbox"]
        if (
            len(spans) != len(labels)
            or sorted(s["text"].casefold() for s in spans)
            != sorted(label.casefold() for label in labels)
            or box is None
            or cell["bbox_origin"] != "TOPLEFT"
        ):
            return None
        ordered = sorted(spans, key=lambda s: (s["bbox"][0] + s["bbox"][2]) / 2)
        if any(
            a["bbox"][2] >= b["bbox"][0]
            for a, b in zip(ordered, ordered[1:], strict=False)
        ):
            return None
        for span in ordered:
            sx, sy = (
                (span["bbox"][0] + span["bbox"][2]) / 2,
                (span["bbox"][1] + span["bbox"][3]) / 2,
            )
            if not (
                box[0] <= sx <= box[2]
                and min(box[1], box[3]) <= sy <= max(box[1], box[3])
            ):
                return None
            size = (span["page_size"][0], span["page_size"][1])
            if page_size is not None and page_size != size:
                return None
            page_size = size
            positions.append(sx)
        labels = [span["text"] for span in ordered]
        axis.extend(labels)
        col = cell["col_end"]
    if (
        len({label.casefold() for label in axis}) != len(axis)
        or any(a >= b for a, b in zip(positions, positions[1:], strict=False))
        or page_size is None
    ):
        return None
    return axis, positions, page_size


def model_axis(cells: Sequence[SourceCell]) -> list[str] | None:
    data = _model_axis_data(cells)
    return data[0] if data is not None else None


def row_cells(
    cells: Sequence[SourceCell], row: int, column: int
) -> tuple[str, str] | None:
    """Original property and value; a blank neighbour never inherits a value."""
    label, value = cell_at(cells, row, 0), cell_at(cells, row, column)
    if (
        row <= 0
        or label is None
        or value is None
        or label["col_end"] != 1
        or value["col_start"] < 1
        or label["column_header"]
        or value["column_header"]
        or label["row_section"]
        or value["row_section"]
        or not label["text"]
        or not value["text"]
        or any("|" in cell["text"] or "\n" in cell["text"] for cell in [label, value])
        # A parser-merged pair of different unit-bearing properties is not a
        # single field. The source cannot tell which value belongs to which.
        or len(re.findall(r"\[[^\]]+\]", label["text"])) > 1
        or any(
            value["text"].count(left) != value["text"].count(right)
            for left, right in [("(", ")"), ("[", "]")]
        )
        # A star or dagger points to a source qualification. Without a separately
        # proven applicable footnote, the bare rating must not become an answer.
        or re.search(r"[*†‡]+\s*$", value["text"]) is not None
    ):
        return None
    if not aligned_property(cells, label, value):
        return None
    if not aligned_column(cells, value, column):
        return None
    return label["text"], value["text"]


def aligned_column(cells: Sequence[SourceCell], value: SourceCell, column: int) -> bool:
    """The value's physical column must agree with the original header axis."""
    data, box = _model_axis_data(cells), value["bbox"]
    if data is None or box is None or value["bbox_origin"] != "TOPLEFT":
        return False
    _, positions, size = data
    if not (
        0 <= box[0] < box[2] <= size[0]
        and 0 <= min(box[1], box[3]) < max(box[1], box[3]) <= size[1]
    ):
        return False
    centre = (box[0] + box[2]) / 2
    distances = [abs(centre - x) for x in positions]
    nearest = [i + 1 for i, d in enumerate(distances) if d == min(distances)]
    return (
        len(nearest) == 1
        and value["col_start"] <= nearest[0] < value["col_end"]
        and value["col_start"] <= column < value["col_end"]
    )


def aligned_property(
    cells: Sequence[SourceCell], label: SourceCell, value: SourceCell
) -> bool:
    """Logical row offsets alone cannot prove a property/value relationship.

    Cached native output includes rows shifted by a merged line: e.g. a weight
    label beside a warranty value. Both original bounding-box centres must lie
    inside the other's vertical extent, and no other property centre may share
    that value box. No guessed distance or numeric-value heuristic is used.
    """
    a, b = label["bbox"], value["bbox"]
    if a is None or b is None or label["bbox_origin"] != value["bbox_origin"]:
        return False
    a_low, a_high = sorted((a[1], a[3]))
    b_low, b_high = sorted((b[1], b[3]))
    a_mid, b_mid = (a_low + a_high) / 2, (b_low + b_high) / 2
    if not (a_low <= b_mid <= a_high and b_low <= a_mid <= b_high):
        return False
    for other in cells:
        if (
            other is label
            or other["col_start"] != 0
            or other["col_end"] != 1
            or other["column_header"]
            or other["row_section"]
            or not other["text"]
            or other["bbox"] is None
        ):
            continue
        box = other["bbox"]
        if other["bbox_origin"] != value["bbox_origin"]:
            return False
        low, high = sorted((box[1], box[3]))
        if low <= b_mid <= high or b_low <= (low + high) / 2 <= b_high:
            return False
    return True


def row_context(cells: Sequence[SourceCell], row: int) -> tuple[int, str] | None:
    """Keep the last explicitly marked source section alongside its properties."""
    sections = [
        (cell["row_start"], cell["text"])
        for cell in cells
        if cell["col_start"] == 0
        and cell["row_start"] < row
        and cell["text"]
        and (
            cell["row_section"]
            or (
                cell["col_end"] == 1
                and not cell["column_header"]
                and not any(
                    other["col_start"] >= 1
                    and other["row_start"] <= cell["row_start"] < other["row_end"]
                    and other["text"]
                    for other in cells
                )
            )
        )
    ]
    if not sections:
        return None
    latest = max(r for r, _ in sections)
    texts = {text for r, text in sections if r == latest}
    if len(texts) != 1:
        return None
    return latest, texts.pop()


def render_projection(
    cells: Sequence[SourceCell], column: int, rows: Sequence[int]
) -> str | None:
    """Reconstruct the exact answer text; no numeric inference or alias expansion."""
    axis = model_axis(cells)
    if (
        axis is None
        or not 1 <= column <= len(axis)
        or not rows
        or any(type(row) is not int or row <= 0 for row in rows)
        or list(rows) != sorted(set(rows))
    ):
        return None
    heading = cell_at(cells, 0, 0)
    label = heading["text"] if heading and heading["text"] else "Model"
    if "|" in label or "\n" in label:
        return None
    lines = [f"| {label} | {axis[column - 1]} |"]
    previous_context = None
    for row in rows:
        pair = row_cells(cells, row, column)
        if pair is None:
            return None
        context = row_context(cells, row)
        if context is not None and context != previous_context:
            if "|" in context[1] or "\n" in context[1]:
                return None
            lines.append(f"| {context[1]} |  |")
        lines.append("| " + " | ".join(pair) + " |")
        previous_context = context
    return "\n".join(lines)


def safe_rows(
    cells: Sequence[SourceCell],
    column: int,
    rows: Sequence[int],
    model: str,
    known_labels: Sequence[str],
) -> bool:
    """Finer model references never borrow the host column's permission.

    Unresolved model-like fields are localized to their row. They do not make
    independent native power/current rows unusable for the current product.
    """
    labels = {label.casefold() for label in known_labels if label}
    own = model.casefold()
    shapes = model_shapes(labels)
    families = family_labels(labels)
    for row in rows:
        pair = row_cells(cells, row, column)
        if pair is None:
            return False
        context = row_context(cells, row)
        text = " ".join([*(context[1:2] if context else ()), *pair])
        if any(
            label != own and model_pattern(label).search(text) for label in labels
        ) or unknown_models(text, {own}, shapes, section=True, families=families):
            return False
    return True


def projection_id(sha: str, page: int, table: str, model: str, text: str) -> str:
    """A new answer unit cannot reuse the original multi-model chunk identity."""
    digest = hashlib.sha256(f"{table}\0{model}\0{text}".encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-model-{digest}"


def valid_projection(
    scope: Mapping[str, Any],
    product_ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
) -> bool:
    """Store and runtime accept only an exact current-model source projection."""
    value = scope.get("table_projection")
    if not isinstance(value, dict) or scope.get("basis") != "table_projection":
        return False
    pid = value.get("product_id")
    cells = read_cells(value.get("source_cells"))
    if (
        type(pid) is not int
        or list(product_ids) != [pid]
        or scope.get("product_ids") != [pid]
        or pid not in products
        or cells is None
        or value.get("source_sha256") != sha
        or value.get("source_cells_sha256") != cells_digest(cells)
        or not isinstance(value.get("source_table"), str)
        or not value["source_table"]
        or type(value.get("source_page")) is not int
        or value["source_page"] <= 0
        or not isinstance(value.get("source_rows"), list)
        or type(value.get("model_column")) is not int
        or not isinstance(value.get("model"), str)
        or value["model"].casefold() != str(products[pid].get("model", "")).casefold()
        or not scope.get("source_chunk_ids")
    ):
        return False
    if any(
        span["source_sha256"] != sha or span["page"] != value["source_page"]
        for cell in cells
        for span in cell.get("model_spans", [])
    ):
        return False
    axis = model_axis(cells)
    column = value["model_column"]
    if axis is None or not 1 <= column <= len(axis):
        return False
    if axis[column - 1].casefold() != value["model"].casefold():
        return False
    rendered = render_projection(cells, column, value["source_rows"])
    return (
        rendered == text
        and safe_rows(
            cells,
            column,
            value["source_rows"],
            value["model"],
            [*(str(p.get("model", "")) for p in products.values()), *axis],
        )
        and value.get("text_sha256") == hashlib.sha256(text.encode()).hexdigest()
        and chunk_id
        == projection_id(
            sha, value["source_page"], value["source_table"], value["model"], text
        )
    )
