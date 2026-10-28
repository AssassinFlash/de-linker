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


class SourceFragment(TypedDict):
    """One physical line of a model code split by PDFium's line-break marker."""

    text: str
    bbox: tuple[float, float, float, float]
    char_start: int
    char_end: int


class SourceSpan(TypedDict):
    """One original visible PDF text-layer token, in cropped page coordinates."""

    text: str
    bbox: tuple[float, float, float, float]
    char_start: int
    char_end: int
    page: int
    source_sha256: str
    page_size: tuple[float, float]
    fragments: NotRequired[list[SourceFragment]]


class SourceTextSpan(TypedDict):
    """A Docling text item's original character range and cropped-page box."""

    bbox: tuple[float, float, float, float]
    char_start: int
    char_end: int
    source_id: str


class SourceFootnote(TypedDict):
    """One complete original note with matching Docling and PDF text geometry."""

    source_id: str
    text: str
    source_span: SourceTextSpan
    pdf_span: SourceSpan


class ExternalAxis(TypedDict):
    """Native text items immediately preceding, but outside, a table."""

    source_ids: list[str]
    source_text: str
    source_spans: list[SourceTextSpan]
    table_bbox: tuple[float, float, float, float]
    model_spans: list[SourceSpan]
    section_rows: list[int]
    section_barriers: list[int]
    footnotes: list[SourceFootnote]
    value_col_start: int
    first_row_is_data: bool


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
    external_axis: NotRequired[ExternalAxis]


TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]*")


def _box(value: object) -> bool:
    return (
        isinstance(value, (tuple, list))
        and len(value) == 4
        and all(type(n) in (int, float) and math.isfinite(n) for n in value)
        and value[0] < value[2]
        and value[1] < value[3]
    )


def _pdf_span(span: object) -> bool:
    if not isinstance(span, dict):
        return False
    size, box = span.get("page_size"), span.get("bbox")
    valid = (
        isinstance(span.get("text"), str)
        and bool(span["text"])
        and isinstance(span.get("source_sha256"), str)
        and all(type(span.get(k)) is int for k in ["char_start", "char_end", "page"])
        and 0 <= span["char_start"] < span["char_end"]
        and span["page"] > 0
        and isinstance(size, (list, tuple))
        and len(size) == 2
        and all(type(n) in (int, float) and math.isfinite(n) and n > 0 for n in size)
        and isinstance(box, (tuple, list))
        and _box(box)
        and 0 <= box[0] < box[2] <= size[0]
        and 0 <= box[1] < box[3] <= size[1]
    )
    if not valid:
        return False
    if "fragments" not in span:
        return True
    assert isinstance(box, (tuple, list))
    fragments = span["fragments"]
    if not isinstance(fragments, list) or len(fragments) < 2:
        return False
    for part in fragments:
        if (
            not isinstance(part, dict)
            or not isinstance(part.get("text"), str)
            or not part["text"]
            or TOKEN.fullmatch(part["text"]) is None
            or not _box(part.get("bbox"))
            or type(part.get("char_start")) is not int
            or type(part.get("char_end")) is not int
            or not span["char_start"]
            <= part["char_start"]
            < part["char_end"]
            <= span["char_end"]
            or not (
                box[0] <= part["bbox"][0] < part["bbox"][2] <= box[2]
                and box[1] <= part["bbox"][1] < part["bbox"][3] <= box[3]
            )
        ):
            return False
    if (
        "-".join(part["text"] for part in fragments).casefold()
        != span["text"].casefold()
    ):
        return False
    for a, b in zip(fragments, fragments[1:], strict=False):
        first, second = a["bbox"], b["bbox"]
        if (
            a["char_end"] + 1 != b["char_start"]
            or not first[0] <= (second[0] + second[2]) / 2 <= first[2]
            or not second[0] <= (first[0] + first[2]) / 2 <= second[2]
            or not 0
            <= second[1] - first[3]
            <= min(first[3] - first[1], second[3] - second[1])
        ):
            return False
    return True


def _external_axis(value: object) -> ExternalAxis | None:
    if not isinstance(value, dict):
        return None
    text, items, spans = (
        value.get("source_text"),
        value.get("source_spans"),
        value.get("model_spans"),
    )
    ids = value.get("source_ids")
    sections, barriers = value.get("section_rows"), value.get("section_barriers")
    footnotes = value.get("footnotes")
    value_col_start, first_data = (
        value.get("value_col_start"),
        value.get("first_row_is_data"),
    )
    if (
        not isinstance(ids, list)
        or not ids
        or any(
            not isinstance(item, str) or re.fullmatch(r"#/texts/\d+", item) is None
            for item in ids
        )
        or len(set(ids)) != len(ids)
        or not isinstance(text, str)
        or not text
        or any(" ".join(line.split()) != line or not line for line in text.split("\n"))
        or not _box(value.get("table_bbox"))
        or not isinstance(items, list)
        or not items
        or not isinstance(spans, list)
        or not spans
        or not all(_pdf_span(span) for span in spans)
        or not isinstance(footnotes, list)
        or type(value_col_start) is not int
        or value_col_start < 1
        or type(first_data) is not bool
        or not isinstance(sections, list)
        or not isinstance(barriers, list)
        or any(type(row) is not int or row < 0 for row in [*sections, *barriers])
        or sections != sorted(set(sections))
        or barriers != sorted(set(barriers))
        or (not first_data and (not barriers or barriers[0] != 0))
        or (first_data and 0 in barriers)
        or not set(sections).issubset(barriers)
    ):
        return None
    for item in items:
        if (
            not isinstance(item, dict)
            or not _box(item.get("bbox"))
            or item.get("source_id") not in ids
            or type(item.get("char_start")) is not int
            or type(item.get("char_end")) is not int
            or not 0 <= item["char_start"] < item["char_end"] <= len(text)
        ):
            return None
    lines = text.split("\n")
    if len(ids) != len(lines):
        return None
    start = 0
    for source_id, line in zip(ids, lines, strict=True):
        end = start + len(line)
        if not any(item["source_id"] == source_id for item in items) or any(
            item["source_id"] == source_id
            and not start <= item["char_start"] < item["char_end"] <= end
            for item in items
        ):
            return None
        start = end + 1
    markers: set[str] = set()
    for note in footnotes:
        if not isinstance(note, dict):
            return None
        quote, source_id, native, pdf = (
            note.get("text"),
            note.get("source_id"),
            note.get("source_span"),
            note.get("pdf_span"),
        )
        if (
            not isinstance(quote, str)
            or "\n" in quote
            or "|" in quote
            or re.fullmatch(r"\*\d+:\s+\S.*", quote) is None
            or not isinstance(source_id, str)
            or re.fullmatch(r"#/texts/\d+", source_id) is None
            or not isinstance(native, dict)
            or native.get("source_id") != source_id
            or type(native.get("char_start")) is not int
            or type(native.get("char_end")) is not int
            or native.get("char_start") != 0
            or native.get("char_end") != len(quote)
            or not _box(native.get("bbox"))
            or not isinstance(pdf, dict)
            or not _pdf_span(pdf)
            or pdf.get("text") != quote
            or pdf["char_end"] - pdf["char_start"] != len(quote)
            or "fragments" in pdf
            or not (
                0 <= native["bbox"][0] < native["bbox"][2] <= pdf["page_size"][0]
                and 0 <= native["bbox"][1] < native["bbox"][3] <= pdf["page_size"][1]
            )
            or not _inside(pdf["bbox"], native["bbox"])
        ):
            return None
        marker = quote.split(":", 1)[0]
        if marker in markers:
            return None
        markers.add(marker)
    return ExternalAxis(
        source_ids=ids,
        source_text=text,
        source_spans=items,
        table_bbox=value["table_bbox"],
        model_spans=spans,
        section_rows=sections,
        section_barriers=barriers,
        footnotes=footnotes,
        value_col_start=value_col_start,
        first_row_is_data=first_data,
    )


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
        if not all(_pdf_span(span) for span in spans):
            return None
        external = None
        if "external_axis" in cell:
            external = _external_axis(cell["external_axis"])
            if external is None:
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
        if external is not None:
            typed["external_axis"] = external
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


def _inside(box: Sequence[float], outer: Sequence[float]) -> bool:
    """The original glyph or cell centre must be in its claimed source box."""
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _nearest_column(positions: Sequence[float], centre: float) -> int | None:
    distances = [abs(centre - x) for x in positions]
    nearest = [
        i + 1 for i, distance in enumerate(distances) if distance == min(distances)
    ]
    return nearest[0] if len(nearest) == 1 else None


def _external_axis_data(
    cells: Sequence[SourceCell], width: int
) -> tuple[list[str], list[float], tuple[float, float]] | None:
    """Prove a detached native text header against the PDF and table geometry.

    The parser must have recorded the immediately preceding native text items.
    Each model token or wrapped fragment must match its original Docling
    character range and visible PDF glyph box. Only physical x positions
    establish the column order.
    """
    owners = [cell for cell in cells if "external_axis" in cell]
    if len(owners) != 1:
        return None
    owner = owners[0]
    evidence = owner["external_axis"]
    offset = evidence["value_col_start"]
    first_data = evidence["first_row_is_data"]
    if (
        owner["row_start"] != 0
        or owner["row_end"] != 1
        or owner["col_start"] != 0
        or owner["col_end"] != offset
        or not owner["text"]
        or (
            not first_data
            and any(
                cell is not owner
                and cell["row_start"] == 0
                and cell["col_end"] > offset
                for cell in cells
            )
        )
    ):
        return None
    if first_data:
        first_value = cell_at(cells, 0, offset)
        if (
            owner["column_header"]
            or owner["row_section"]
            or first_value is None
            or first_value["col_start"] != offset
            or first_value["row_section"]
            or not first_value["text"]
        ):
            return None
    source_text = evidence["source_text"]
    match = re.fullmatch(
        r"(?:technical data|technische daten)\s+(.+)",
        source_text,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    spans, native = evidence["model_spans"], evidence["source_spans"]
    labels = [span["text"] for span in spans]
    if (
        len(labels) < 2
        or len(labels) != width - offset
        or len({s.casefold() for s in labels}) != len(labels)
        or any(_axis_labels(label) != [label] for label in labels)
        or TOKEN.sub("", match[1]).strip()
    ):
        return None
    if first_data:
        native_first = " ".join(
            cell["text"] for cell in cells if cell["row_start"] == 0
        )
        if (
            any(model_pattern(label).search(native_first) for label in labels)
            or unknown_models(
                native_first,
                set(),
                model_shapes(labels),
                families=family_labels(set(labels)),
            )
            or any(
                "-" in token
                and any(c.isalpha() for c in token)
                and any(c.isdigit() for c in token)
                for token in TOKEN.findall(native_first)
            )
        ):
            return None
    size = (spans[0]["page_size"][0], spans[0]["page_size"][1])
    page_box = (0.0, 0.0, *size)
    table_box = evidence["table_bbox"]
    if (
        not (
            0 <= table_box[0] < table_box[2] <= size[0]
            and 0 <= table_box[1] < table_box[3] <= size[1]
        )
        or owner["bbox"] is None
        or owner["bbox_origin"] != "TOPLEFT"
        or not _inside(owner["bbox"], table_box)
        or any(
            tuple(s["page_size"]) != size
            or s["page"] != spans[0]["page"]
            or s["source_sha256"] != spans[0]["source_sha256"]
            for s in spans
        )
    ):
        return None
    # The source item must be wholly represented by its original nonoverlapping
    # Docling text ranges, and its visible boxes must sit above this table.
    native = sorted(native, key=lambda item: item["char_start"])
    if any(
        a["char_end"] > b["char_start"]
        for a, b in zip(native, native[1:], strict=False)
    ) or any(
        not char.isspace()
        and not any(item["char_start"] <= i < item["char_end"] for item in native)
        for i, char in enumerate(source_text)
    ):
        return None
    if any(
        not _inside(item["bbox"], page_box)
        or item["bbox"][0] < 0
        or item["bbox"][2] > size[0]
        or item["bbox"][1] < 0
        or item["bbox"][3] > table_box[1]
        for item in native
    ):
        return None
    offsets = sorted((s["char_start"], s["char_end"]) for s in spans)
    if any(a[1] > b[0] for a, b in zip(offsets, offsets[1:], strict=False)):
        return None
    ordered = sorted(spans, key=lambda s: (s["bbox"][0] + s["bbox"][2]) / 2)
    if any(
        a["bbox"][2] >= b["bbox"][0] for a, b in zip(ordered, ordered[1:], strict=False)
    ) or max(s["bbox"][1] for s in spans) >= min(s["bbox"][3] for s in spans):
        return None
    tokens = list(TOKEN.finditer(source_text, match.start(1)))
    used: set[tuple[int, int]] = set()
    for span in ordered:
        if (
            not table_box[0] <= (span["bbox"][0] + span["bbox"][2]) / 2 <= table_box[2]
            or span["bbox"][3] > table_box[1]
        ):
            return None
        fragments = span.get("fragments", [])
        pieces = (
            [
                (part["text"] + ("-" if i < len(fragments) - 1 else ""), part["bbox"])
                for i, part in enumerate(fragments)
            ]
            if fragments
            else [(span["text"], span["bbox"])]
        )
        for piece, box in pieces:
            matches = [
                token
                for token in tokens
                if token[0].casefold() == piece.casefold()
                and any(
                    item["char_start"]
                    <= token.start()
                    < token.end()
                    <= item["char_end"]
                    and _inside(box, item["bbox"])
                    for item in native
                )
            ]
            if len(matches) != 1 or matches[0].span() in used:
                return None
            used.add(matches[0].span())
    if used != {token.span() for token in tokens}:
        return None
    positions = [(s["bbox"][0] + s["bbox"][2]) / 2 for s in ordered]
    # At least one original row must independently demonstrate all value
    # columns. A merged or missing cell cannot establish the detached axis.
    rows = sorted({cell["row_start"] for cell in cells if cell["row_start"] > 0})
    for row in rows:
        label = cell_at(cells, row, 0)
        values = [cell_at(cells, row, column) for column in range(offset, width)]
        if (
            label is None
            or label["col_start"] != 0
            or label["col_end"] != offset
            or label["row_start"] != row
            or label["row_end"] != row + 1
            or label["column_header"]
            or label["row_section"]
            or not label["text"]
            or label["bbox"] is None
            or label["bbox_origin"] != "TOPLEFT"
            or not _inside(label["bbox"], table_box)
            or any(
                cell is None
                or cell["col_start"] != col
                or cell["col_end"] != col + 1
                or cell["row_start"] != row
                or cell["row_end"] != row + 1
                or cell["column_header"]
                or cell["row_section"]
                or not cell["text"]
                or cell["bbox"] is None
                or cell["bbox_origin"] != "TOPLEFT"
                or not _inside(cell["bbox"], table_box)
                or not aligned_property(cells, label, cell)
                or _nearest_column(positions, (cell["bbox"][0] + cell["bbox"][2]) / 2)
                != col - offset + 1
                for col, cell in enumerate(values, offset)
            )
        ):
            continue
        return [span["text"] for span in ordered], positions, size
    return None


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
    if any("external_axis" in cell for cell in cells):
        return _external_axis_data(cells, width)
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
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    offset = external["value_col_start"] if external is not None else 1
    native_column = column + offset - 1
    label, value = cell_at(cells, row, 0), cell_at(cells, row, native_column)
    if (
        row < 0
        or (row == 0 and (external is None or not external["first_row_is_data"]))
        or label is None
        or value is None
        or label["col_end"] != offset
        or value["col_start"] < offset
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
        or (
            external is None
            and any(
                re.search(r"[*†‡]+(?:\s*\d+)?\s*$", cell["text"]) is not None
                for cell in (label, value)
            )
        )
    ):
        return None
    if external is not None and (
        # A detached header does not establish that a parser-merged body cell
        # applies across multiple columns or rows.
        value["col_start"] > native_column
        or value["col_end"] <= native_column
        or any(
            cell["row_start"] != row or cell["row_end"] != row + 1
            for cell in (label, value)
        )
        or label["bbox"] is None
        or value["bbox"] is None
        or not _inside(label["bbox"], external["table_bbox"])
        or not _inside(value["bbox"], external["table_bbox"])
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
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    offset = external["value_col_start"] if external is not None else 1
    if not (
        0 <= box[0] < box[2] <= size[0]
        and 0 <= min(box[1], box[3]) < max(box[1], box[3]) <= size[1]
    ):
        return False
    centre = (box[0] + box[2]) / 2
    if external is not None and value["col_end"] - value["col_start"] > 1:
        first = value["col_start"] - offset
        last = value["col_end"] - offset - 1
        if not 0 <= first < last < len(positions):
            return False
        midpoint = (positions[first] + positions[last]) / 2
        # The native cell explicitly spans these columns, and the one visible
        # source value must occupy their centre rather than an individual model's
        # position. A wide or parser-shifted value cannot prove sharing merely
        # by reaching the midpoint with its edge.
        return (
            value["col_start"] <= column + offset - 1 < value["col_end"]
            and box[0] <= midpoint <= box[2]
            and abs(centre - midpoint)
            < min(abs(centre - positions[first]), abs(centre - positions[last]))
        )
    nearest = _nearest_column(positions, centre)
    return (
        nearest is not None
        and value["col_start"] <= nearest + offset - 1 < value["col_end"]
        and value["col_start"] <= column + offset - 1 < value["col_end"]
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
            or other["col_end"] > label["col_end"]
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
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    sections = [
        (cell["row_start"], cell["text"])
        for cell in cells
        if cell["col_start"] == 0
        and cell["row_start"] < row
        and cell["text"]
        and (
            cell["row_start"] in external["section_rows"]
            if external is not None
            else (
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
        )
    ]
    if not sections:
        return None
    latest = max(r for r, _ in sections)
    texts = {text for r, text in sections if r == latest}
    if len(texts) != 1:
        return None
    return latest, texts.pop()


def row_footnotes(
    cells: Sequence[SourceCell], row: int, column: int
) -> list[SourceFootnote] | None:
    """Every marker affecting a row needs one complete original PDF note."""
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    offset = external["value_col_start"] if external is not None else 1
    label, value = cell_at(cells, row, 0), cell_at(cells, row, column + offset - 1)
    if label is None or value is None:
        return None
    context = row_context(cells, row)
    original = " ".join(
        [*(context[1:2] if context else ()), label["text"], value["text"]]
    )
    markers = [
        match.group().replace(" ", "")
        for match in re.finditer(r"[*†‡]\s*\d*", original)
    ]
    if not markers:
        return []
    if any(re.fullmatch(r"\*\d+", marker) is None for marker in markers):
        return None
    if external is None:
        return None
    output: list[SourceFootnote] = []
    for marker in dict.fromkeys(markers):
        notes = [
            note
            for note in external["footnotes"]
            if note["text"].startswith(marker + ":")
        ]
        if len(notes) != 1:
            return None
        output.append(notes[0])
    return output


def render_projection(
    cells: Sequence[SourceCell], column: int, rows: Sequence[int]
) -> str | None:
    """Reconstruct the exact answer text; no numeric inference or alias expansion."""
    axis = model_axis(cells)
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    if (
        axis is None
        or not 1 <= column <= len(axis)
        or not rows
        or any(
            type(row) is not int
            or row < 0
            or (row == 0 and (external is None or not external["first_row_is_data"]))
            for row in rows
        )
        or list(rows) != sorted(set(rows))
    ):
        return None
    heading = cell_at(cells, 0, 0)
    label = (
        heading["text"]
        if heading and heading["text"] and "external_axis" not in heading
        else "Model"
    )
    if "|" in label or "\n" in label:
        return None
    lines = [f"| {label} | {axis[column - 1]} |"]
    previous_context = None
    notes: dict[str, SourceFootnote] = {}
    for row in rows:
        pair = row_cells(cells, row, column)
        required = row_footnotes(cells, row, column)
        if pair is None or required is None:
            return None
        for note in required:
            notes[note["text"].split(":", 1)[0]] = note
        context = row_context(cells, row)
        if context is not None and context != previous_context:
            if "|" in context[1] or "\n" in context[1]:
                return None
            lines.append(f"| {context[1]} |  |")
        lines.append("| " + " | ".join(pair) + " |")
        previous_context = context
    for note in notes.values():
        lines.append(f"{note['text']} (p. {note['pdf_span']['page']})")
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
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    for row in rows:
        pair = row_cells(cells, row, column)
        if pair is None:
            return False
        context = row_context(cells, row)
        if external is not None:
            barriers = [
                number for number in external["section_barriers"] if number < row
            ]
            if not barriers:
                if not external["first_row_is_data"] or context is not None:
                    return False
            else:
                if (
                    barriers[-1] not in external["section_rows"]
                    or context is None
                    or context[0] != barriers[-1]
                ):
                    return False
                section = cell_at(cells, barriers[-1], 0)
                if (
                    section is None
                    or section["row_start"] != barriers[-1]
                    or section["row_end"] != barriers[-1] + 1
                    or section["col_start"] != 0
                    or section["col_end"] != external["value_col_start"]
                    or section["bbox"] is None
                    or section["bbox_origin"] != "TOPLEFT"
                    or not _inside(section["bbox"], external["table_bbox"])
                ):
                    return False
        notes = row_footnotes(cells, row, column)
        if notes is None:
            return False
        text = " ".join(
            [*(context[1:2] if context else ()), *pair, *(n["text"] for n in notes)]
        )
        if any(
            label != own and model_pattern(label).search(text) for label in labels
        ) or unknown_models(text, {own}, shapes, section=True, families=families):
            return False
    return True


def projection_id(sha: str, page: int, table: str, model: str, text: str) -> str:
    """A new answer unit cannot reuse the original multi-model chunk identity."""
    digest = hashlib.sha256(f"{table}\0{model}\0{text}".encode()).hexdigest()[:16]
    return f"{sha[:12]}-p{page}-model-{digest}"


def native_chunk_id_matches(
    sha: str, page: int, kind: str, text: str, cid: str
) -> bool:
    """Bind an original chunk ID to the actual body used by the chunker."""
    digest = hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()[:8]
    expected = f"{sha[:12]}-p{page}-{digest}"
    return (
        re.fullmatch(re.escape(expected) + r"(?:-(?:[2-9]|[1-9]\d+))?", cid) is not None
    )


def _unresolved_table_marker(line: str, label: str, notes: set[str]) -> bool:
    """Keep explicit three-axis dimensions only when no suffix looks like a note."""
    axes = re.search(r"\b(?:[WwHhDdLl]\s*\*\s*){2}[WwHhDdLl]\b", label)
    if axes and re.search(
        r"\b(?:dimensions?|abmessungen|maße)\b", label, re.IGNORECASE
    ):
        line = re.sub(
            r"\b(?:[WwHhDdLl]\s*\*\s*){2}[WwHhDdLl]\b",
            "",
            line,
        )

        def dimensions(match: re.Match[str]) -> str:
            values = re.findall(r"\d+(?:[.,]\d+)?", match.group())
            # A same-number source declaration takes precedence over
            # the label's three-axis multiplication notation.
            if any(
                value.split(".")[0].split(",")[0].lstrip("0") in notes
                for value in values[1:]
            ):
                return match.group()
            return ""

        line = re.sub(
            r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*\*\s*\d+(?:[.,]\d+)?){2}(?![\w.*])",
            dimensions,
            line,
        )
    return re.search(r"[*†‡]", line) is not None


def unqualified_table_columns(
    chunks: Sequence[tuple[str, int, str, str, str]],
    scopes: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """Retain only complete native rows without unresolved note conditions.

    The applicability proof's basis does not change the source's conditions.
    Walk every native table, including fragments without an individual scope,
    in source order. Old indexes without fragment provenance use a conservative
    same-page grouping. Qualified projections already have their own validator.
    """
    records: dict[str, tuple[str, int, str, int]] = {}
    result: dict[str, str] = {}
    notes_by_sha: dict[str, set[str]] = {}
    for position, (sha, page, kind, cid, text) in enumerate(chunks):
        if kind == "text":
            notes_by_sha.setdefault(sha, set()).update(
                match.group(1).lstrip("0")
                for match in re.finditer(r"(?<!\w)\*\s*(\d+)(?!\d)", text)
            )
        if kind != "table":
            continue
        scope = scopes.get(cid, {})
        if scope.get("basis") == "table_projection" or "table_projection" in scope:
            continue
        if not native_chunk_id_matches(sha, page, kind, text, cid):
            # Keep the fragment's original position as an unknown barrier.
            text = ""
        records[cid] = (sha, page, text, position)

    claims: dict[tuple[str, int, str], tuple[str, ...]] = {}
    bad_pages: set[tuple[str, int]] = set()
    rejected: set[str] = set()
    owners: dict[str, tuple[str, int, str]] = {}
    for cid, (sha, page, _, _) in records.items():
        scope = scopes.get(cid, {})
        native = scope.get("native_table")
        if native is None:
            continue
        ids = native.get("source_chunk_ids") if isinstance(native, dict) else None
        table = native.get("source_table") if isinstance(native, dict) else None
        if (
            isinstance(ids, list)
            and all(isinstance(item, str) for item in ids)
            and any(item not in records for item in ids)
        ):
            rejected.update(item for item in ids if item in records)
            rejected.add(cid)
            continue
        if (
            not isinstance(table, str)
            or not table
            or not isinstance(ids, list)
            or not ids
            or not all(isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids)
            or cid not in ids
            or any(
                item not in records or records[item][:2] != (sha, page) for item in ids
            )
            or [records[item][3] for item in ids]
            != sorted(records[item][3] for item in ids)
        ):
            bad_pages.add((sha, page))
            continue
        key = (sha, page, table)
        part_ids = tuple(ids)
        if key in claims and claims[key] != part_ids:
            bad_pages.add((sha, page))
        claims[key] = part_ids
        for item in ids:
            if item in owners and owners[item] != key:
                bad_pages.add((sha, page))
            owners[item] = key

    groups: dict[tuple[str, int, str], list[tuple[str, str]]] = {}
    for cid, (sha, page, text, _) in records.items():
        if cid in rejected:
            result[cid] = ""
            continue
        owner = owners.get(cid)
        if owner is None or (sha, page) in bad_pages:
            # Older indexes have no table membership; include every native
            # table fragment on the page rather than dropping a condition.
            owner = (sha, page, "")
        groups.setdefault(owner, []).append((cid, text))
    for parts in groups.values():
        conditional = False
        text_by_id: dict[str, list[str]] = {}
        data_by_id: dict[str, int] = {}
        last_data: tuple[str, int] | None = None
        for cid, text in parts:
            lines: list[str] = []
            text_by_id[cid] = lines
            data_by_id[cid] = 0
            if not text and last_data is not None:
                previous, index = last_data
                del text_by_id[previous][index]
                data_by_id[previous] -= 1
                last_data = None
            for line in text.splitlines() if text else [""]:
                if not line.startswith("|") or not line.endswith("|"):
                    conditional = True
                    continue
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                if len(cells) < 2:
                    conditional = True
                    continue
                if not cells[0]:
                    # A bare value continuation cannot be a section heading.
                    # A note marker on it may qualify the preceding row, even
                    # if that row was emitted in the previous fragment.
                    if _unresolved_table_marker(line, "", set()):
                        if last_data is not None:
                            previous, index = last_data
                            del text_by_id[previous][index]
                            data_by_id[previous] -= 1
                            last_data = None
                        conditional = True
                    continue
                marked = _unresolved_table_marker(
                    line, cells[0], notes_by_sha.get(records[cid][0], set())
                )
                section = not any(cells[1:])
                if section:
                    last_data = None
                    conditional = conditional or marked
                    if not conditional:
                        lines.append(line)
                elif not conditional and not marked:
                    lines.append(line)
                    data_by_id[cid] += 1
                    last_data = (cid, len(lines) - 1)
        result.update(
            {
                cid: "\n".join(lines) if data_by_id[cid] else ""
                for cid, lines in text_by_id.items()
            }
        )
    return result


def external_axis_anchored(
    scope: Mapping[str, Any],
    anchors: Mapping[str, Any] | None,
    *,
    required: bool = False,
) -> bool:
    """Compare a projection with separately recorded canonical table evidence."""
    projection = scope.get("table_projection")
    if not isinstance(projection, dict):
        return False
    if not required and "axis_source" not in projection:
        return True
    source_ids = scope.get("source_chunk_ids")
    if not isinstance(source_ids, list) or not isinstance(anchors, Mapping):
        return False
    fields = (
        "source_sha256",
        "source_page",
        "source_table",
        "source_cells_sha256",
    )
    return any(
        isinstance(cid, str)
        and isinstance(anchors.get(cid), Mapping)
        and all(anchors[cid].get(field) == projection.get(field) for field in fields)
        and anchors[cid].get("axis_source", []) == projection.get("axis_source", [])
        and isinstance(projection.get("footnote_sources", []), list)
        and isinstance(anchors[cid].get("footnote_sources", []), list)
        and all(
            source in anchors[cid].get("footnote_sources", [])
            for source in projection.get("footnote_sources", [])
        )
        for cid in source_ids
    )


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
    external = [cell["external_axis"] for cell in cells if "external_axis" in cell]
    if external:
        if len(external) != 1 or any(
            span["source_sha256"] != sha or span["page"] != value["source_page"]
            for span in external[0]["model_spans"]
        ):
            return False
        if any(
            note["pdf_span"]["source_sha256"] != sha
            for note in external[0]["footnotes"]
        ):
            return False
        origins = value.get("axis_source")
        if not isinstance(origins, list) or not origins:
            return False
        if any(
            not isinstance(origin, dict)
            or not isinstance(origin.get("chunk_id"), str)
            or not isinstance(origin.get("text"), str)
            or origin["chunk_id"] not in scope["source_chunk_ids"]
            or not native_chunk_id_matches(
                sha, value["source_page"], "text", origin["text"], origin["chunk_id"]
            )
            for origin in origins
        ) or len({origin["chunk_id"] for origin in origins}) != len(origins):
            return False
        origin_text = "\n".join(origin["text"] for origin in origins)
        if (
            not origin_text.endswith(external[0]["source_text"])
            or origin_text.count(external[0]["source_text"]) != 1
            or (
                len(origin_text) > len(external[0]["source_text"])
                and origin_text[-len(external[0]["source_text"]) - 1] != "\n"
            )
        ):
            return False
    elif "axis_source" in value or "footnote_sources" in value:
        return False
    axis = model_axis(cells)
    column = value["model_column"]
    if axis is None or not 1 <= column <= len(axis):
        return False
    if axis[column - 1].casefold() != value["model"].casefold():
        return False
    if external:
        required: dict[str, SourceFootnote] = {}
        for row in value["source_rows"]:
            if type(row) is not int:
                return False
            notes = row_footnotes(cells, row, column)
            if notes is None:
                return False
            required.update({note["text"]: note for note in notes})
        sources = value.get("footnote_sources", [])
        if not isinstance(sources, list) or len(sources) != len(required):
            return False
        for source in sources:
            if not isinstance(source, dict):
                return False
            quote = source.get("quote")
            note = required.pop(quote, None) if isinstance(quote, str) else None
            if (
                note is None
                or source.get("source_id") != note["source_id"]
                or source.get("page") != note["pdf_span"]["page"]
                or source.get("lang") not in ("en", "de")
                or not isinstance(source.get("chunk_id"), str)
                or source["chunk_id"] not in scope["source_chunk_ids"]
                or not isinstance(source.get("text"), str)
                or source["text"].splitlines().count(note["text"]) != 1
                or not native_chunk_id_matches(
                    sha, source["page"], "text", source["text"], source["chunk_id"]
                )
            ):
                return False
        if required:
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
