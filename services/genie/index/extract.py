"""Extract: a cached Docling parse -> the text blocks of each physical page.

Reads what `index.parse` cached for one document and returns, page by page, the body
in reading order as headings, text and tables (rows of cell texts, column-header rows
first). A page whose text layer is unreadable takes its blocks from the OCR of its
rendered image instead. Page furniture (running headers and footers) is not body text
and is left out, as Docling classifies it.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from docling_core.types.doc.base import BoundingBox
from docling_core.types.doc.common.reference import ProvenanceItem
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.node import NodeItem
from docling_core.types.doc.items.picture.picture import PictureItem
from docling_core.types.doc.items.table.table import TableItem
from docling_core.types.doc.items.text import SectionHeaderItem, TextItem, TitleItem

from linker_genie.table_projection import (
    TOKEN,
    ExternalAxis,
    SourceCell,
    SourceFootnote,
    SourceFragment,
    SourceSpan,
    SourceTextSpan,
)
from linker_genie.warranty_scope import STS_COVER_SUBTITLE

BlockKind = Literal["heading", "text", "table"]


@dataclass(frozen=True)
class Block:
    """One unit of a page body."""

    kind: BlockKind
    text: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    header_rows: int = 0
    # Native Docling identity; equality of the extracted body remains textual.
    source_id: str = field(default="", compare=False)
    row_indices: tuple[int, ...] = field(default=(), compare=False)
    source_cells: tuple[SourceCell, ...] = field(default=(), compare=False)
    # Text inside a picture is local to that figure, not a document heading.
    source_picture: str = field(default="", compare=False)
    # Exact Docling provenance stays in memory for physical table-axis proof.
    source_original: str = field(default="", compare=False)
    source_prov: tuple[ProvenanceItem, ...] = field(default=(), compare=False)


@dataclass
class Page:
    """The body of one physical page (numbered from 1) and where it came from."""

    number: int
    source: Literal["docling", "ocr"]
    blocks: list[Block] = field(default_factory=list)


def clean(text: str) -> str:
    """Whitespace collapsed to single spaces.

    U+FFFE becomes a hyphen: it is how PDFium hands back a hyphen at a line break,
    and in the corpus it sits inside model codes (`GW99.99K\\ufffeBTR-G10`).
    """
    return " ".join(text.replace("￾", "-").split())


def _table_rows(item: TableItem) -> tuple[tuple[tuple[str, ...], ...], int]:
    rows = tuple(tuple(clean(cell.text) for cell in row) for row in item.data.grid)
    rows = tuple(row for row in rows if any(row))
    header_rows = 0
    for row in item.data.grid:
        cells = [cell for cell in row if clean(cell.text)]
        if not cells or not all(cell.column_header for cell in cells):
            break
        header_rows += 1
    return rows, min(header_rows, len(rows))


def _picture_ancestor(document: DoclingDocument, item: NodeItem) -> str:
    parent = item.parent
    while parent is not None:
        node = parent.resolve(document)
        if isinstance(node, PictureItem):
            return node.self_ref
        parent = node.parent
    return ""


def _blocks(document: DoclingDocument) -> Iterable[tuple[int, Block]]:
    """(page number, block) in reading order, for every body item that holds text."""
    for item, _level in document.iterate_items(traverse_pictures=True):
        if isinstance(item, TableItem) and item.prov:
            picture = _picture_ancestor(document, item)
            rows, header_rows = _table_rows(item)
            if rows:
                yield (
                    item.prov[0].page_no,
                    Block(
                        kind="table",
                        rows=rows,
                        header_rows=header_rows,
                        source_id=item.self_ref,
                        source_picture=picture,
                        source_prov=tuple(item.prov),
                        row_indices=tuple(
                            i
                            for i, row in enumerate(item.data.grid)
                            if any(clean(cell.text) for cell in row)
                        ),
                        source_cells=tuple(
                            SourceCell(
                                row_start=cell.start_row_offset_idx,
                                row_end=cell.end_row_offset_idx,
                                col_start=cell.start_col_offset_idx,
                                col_end=cell.end_col_offset_idx,
                                text=clean(cell.text),
                                column_header=cell.column_header,
                                row_header=cell.row_header,
                                row_section=cell.row_section,
                                bbox=(
                                    (
                                        cell.bbox.l,
                                        cell.bbox.t,
                                        cell.bbox.r,
                                        cell.bbox.b,
                                    )
                                    if cell.bbox is not None
                                    else None
                                ),
                                bbox_origin=(
                                    cell.bbox.coord_origin.value
                                    if cell.bbox is not None
                                    else ""
                                ),
                            )
                            for cell in item.data.table_cells
                        ),
                    ),
                )
        elif isinstance(item, TextItem) and item.prov:
            text = clean(item.text)
            if text:
                picture = _picture_ancestor(document, item)
                heading = isinstance(item, (SectionHeaderItem, TitleItem))
                yield (
                    item.prov[0].page_no,
                    Block(
                        kind="heading" if heading else "text",
                        text=text,
                        source_id=item.self_ref,
                        source_picture=picture,
                        source_original=item.text,
                        source_prov=tuple(item.prov),
                    ),
                )


def load_document(path: Path) -> DoclingDocument:
    """A DoclingDocument cached by `index.parse`."""
    return DoclingDocument.model_validate_json(path.read_text(encoding="utf-8"))


def pages_of(document: DoclingDocument) -> dict[int, list[Block]]:
    """Page number -> blocks of that page."""
    pages: dict[int, list[Block]] = {}
    for page, block in _blocks(document):
        pages.setdefault(page, []).append(block)
    return pages


def _visible_pdf_line(
    pdf: object,
    page: object,
    textpage: object,
    text: str,
    start: int,
    end: int,
    page_box: tuple[float, float, float, float],
) -> bool:
    """Require the original characters to make a visible mark on the page.

    A PDF text layer can describe text that never appears in the rendering.
    Compare the real page with each candidate text object disabled, and compare
    each character's visible ink to that object's isolated rendering. Unknown
    object, clipping, annotation, or raster state is not source evidence.
    """
    import ctypes
    from typing import Any, cast

    import pypdfium2
    import pypdfium2.raw as raw

    document = cast(Any, pdf)
    pdf_page = cast(Any, page)
    text_page = cast(Any, textpage)
    box_type = tuple[float, float, float, float]
    try:
        # A genuine series title is short; bound work on malformed text layers.
        if end <= start or end - start > 256:
            return False
        # Widgets and annotations can have viewer-dependent appearance streams.
        # Reject them rather than omit a possible cover or transparency.
        if raw.FPDFPage_GetAnnotCount(pdf_page.raw) != 0:
            return False
        left, bottom, right, top = page_box
        if (
            not all(math.isfinite(v) for v in page_box)
            or left >= right
            or bottom >= top
        ):
            return False
        width, height = right - left, top - bottom
        if not math.isclose(
            pdf_page.get_width(), width, abs_tol=0.01
        ) or not math.isclose(pdf_page.get_height(), height, abs_tol=0.01):
            return False

        # At 3 pixels per PDF point the original GoodWe EHA footer has enough
        # raster detail to check individual glyphs, including the narrow ones.
        scale = 3
        full_width, full_height = math.ceil(width * scale), math.ceil(height * scale)
        # Bound PDFium bitmap sizes and integer render dimensions for malformed PDFs.
        if max(full_width, full_height) > 32767:
            return False

        objects: dict[int, tuple[Any, list[tuple[int, box_type]]]] = {}
        boxes: list[box_type] = []
        for i in range(start, end):
            if text[i].isspace():
                continue
            if raw.FPDFText_GetUnicode(text_page.raw, i) != ord(text[i]):
                return False
            if raw.FPDFText_IsGenerated(text_page.raw, i) != 0:
                return False
            obj = raw.FPDFText_GetTextObject(text_page.raw, i)
            if not obj or raw.FPDFPageObj_GetType(obj) != raw.FPDF_PAGEOBJ_TEXT:
                return False
            # Text clipping modes can affect later page objects when removed.
            if raw.FPDFTextObj_GetTextRenderMode(obj) not in (0, 1, 2):
                return False
            active = ctypes.c_int()
            if (
                not raw.FPDFPageObj_GetIsActive(obj, ctypes.byref(active))
                or not active.value
            ):
                return False
            clip = raw.FPDFPageObj_GetClipPath(obj)
            # PDFium reports -1 for the uninitialized clip path in both the
            # original EHA and unclipped fixtures. Any explicit path is unknown.
            if not clip or raw.FPDFClipPath_CountPaths(clip) != -1:
                return False
            box: box_type = text_page.get_charbox(i)
            if not all(math.isfinite(v) for v in box) or not (
                left <= box[0] < box[2] <= right and bottom <= box[1] < box[3] <= top
            ):
                return False
            address = ctypes.cast(obj, ctypes.c_void_p).value
            if address is None:
                return False
            objects.setdefault(address, (obj, []))[1].append((i, box))
            boxes.append(box)
        # Do not rasterize an unbounded number of independent page objects.
        if not boxes or len(objects) > 64:
            return False

        # Render only the title strip, with a two-point margin for antialiasing.
        crop = (
            max(0, math.floor(min(b[0] for b in boxes) - left - 2)),
            max(0, math.floor(min(b[1] for b in boxes) - bottom - 2)),
            max(0, math.floor(right - max(b[2] for b in boxes) - 2)),
            max(0, math.floor(top - max(b[3] for b in boxes) - 2)),
        )
        if (full_width - (crop[0] + crop[2]) * scale) * (
            full_height - (crop[1] + crop[3]) * scale
        ) > 10_000_000:
            return False

        def render_page() -> Any:
            bitmap = pdf_page.render(scale=scale, crop=crop, draw_annots=True)
            try:
                return bitmap.to_pil().convert("RGB").copy()
            finally:
                bitmap.close()

        def image_box(
            box: box_type,
            origin_left: float,
            origin_top: float,
            x_scale: float,
            y_scale: float,
            x_offset: int = 0,
            y_offset: int = 0,
        ) -> tuple[int, int, int, int]:
            return (
                math.floor((box[0] - origin_left) * x_scale) - x_offset,
                math.floor((origin_top - box[3]) * y_scale) - y_offset,
                math.ceil((box[2] - origin_left) * x_scale) - x_offset,
                math.ceil((origin_top - box[1]) * y_scale) - y_offset,
            )

        # WCAG's 3:1 large-text contrast (w3.org/TR/WCAG22/#contrast-minimum)
        # is a conservative pixel signal here, not an accessibility claim.
        def linear(v: int) -> float:
            c = v / 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        values = [linear(v) for v in range(256)]

        def luminance(pixel: tuple[int, int, int]) -> float:
            return (
                0.2126 * values[pixel[0]]
                + 0.7152 * values[pixel[1]]
                + 0.0722 * values[pixel[2]]
            )

        original = render_page()
        for obj, chars in objects.values():
            obj_bounds = [ctypes.c_float() for _ in range(4)]
            if not raw.FPDFPageObj_GetBounds(
                obj, *(ctypes.byref(v) for v in obj_bounds)
            ):
                return False
            obj_left, obj_bottom, obj_right, obj_top = (v.value for v in obj_bounds)
            if not all(
                math.isfinite(v) for v in (obj_left, obj_bottom, obj_right, obj_top)
            ):
                return False
            if not (
                left <= obj_left < obj_right <= right
                and bottom <= obj_bottom < obj_top <= top
            ):
                return False
            obj_width, obj_height = obj_right - obj_left, obj_top - obj_bottom
            if (
                math.ceil(obj_width * scale) * math.ceil(obj_height * scale)
                > 10_000_000
            ):
                return False
            isolated_raw = raw.FPDFTextObj_GetRenderedBitmap(
                document.raw, pdf_page.raw, obj, scale
            )
            if not isolated_raw:
                return False
            isolated_bitmap = pypdfium2.PdfBitmap.from_raw(isolated_raw)
            try:
                isolated = isolated_bitmap.to_pil().convert("RGBA").copy()
            finally:
                # The image above is copied before destroying this owned bitmap.
                isolated_bitmap.warn_on_close = False
                isolated_bitmap.close()
            if isolated.width < 1 or isolated.height < 1:
                return False

            if not raw.FPDFPageObj_SetIsActive(obj, False):
                return False
            restored = False
            try:
                without = render_page()
            finally:
                restored = bool(raw.FPDFPageObj_SetIsActive(obj, True))
            if not restored or original.size != without.size:
                return False

            for _, box in chars:
                # Exclude areas also occupied by other characters of this same
                # object, so a neighbour cannot prove a hidden glyph visible.
                regions = [box]
                for _, other in chars:
                    if other is box:
                        continue
                    remaining = []
                    for region_left, region_bottom, region_right, region_top in regions:
                        ol = max(region_left, other[0])
                        ob = max(region_bottom, other[1])
                        or_ = min(region_right, other[2])
                        ot = min(region_top, other[3])
                        if ol >= or_ or ob >= ot:
                            remaining.append(
                                (region_left, region_bottom, region_right, region_top)
                            )
                        else:
                            remaining.extend(
                                (x1, y1, x2, y2)
                                for x1, y1, x2, y2 in (
                                    (region_left, region_bottom, ol, region_top),
                                    (or_, region_bottom, region_right, region_top),
                                    (ol, region_bottom, or_, ob),
                                    (ol, ot, or_, region_top),
                                )
                                if x1 < x2 and y1 < y2
                            )
                    regions = remaining
                if not regions:
                    return False
                region = max(regions, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
                page_rect = image_box(
                    region,
                    left,
                    top,
                    full_width / width,
                    full_height / height,
                    crop[0] * scale,
                    crop[3] * scale,
                )
                isolated_rect = image_box(
                    region,
                    obj_left,
                    obj_top,
                    isolated.width / obj_width,
                    isolated.height / obj_height,
                )
                if not (
                    0 <= page_rect[0] < page_rect[2] <= original.width
                    and 0 <= page_rect[1] < page_rect[3] <= original.height
                    and 0 <= isolated_rect[0] < isolated_rect[2] <= isolated.width
                    and 0 <= isolated_rect[1] < isolated_rect[3] <= isolated.height
                ):
                    return False
                alpha = isolated.getchannel("A").crop(isolated_rect)
                expected = sum(v >= 128 for v in alpha.get_flattened_data())
                before = original.crop(page_rect).get_flattened_data()
                after = without.crop(page_rect).get_flattened_data()
                visible = 0
                for a, b in zip(before, after, strict=True):
                    x, y = luminance(a), luminance(b)
                    if (max(x, y) + 0.05) / (min(x, y) + 0.05) >= 3:
                        visible += 1
                # Raster phase changes the count slightly; the EHA original's
                # lowest observed proportion is 75.7%. Require 70% of the
                # isolated glyph so a tiny exposed sliver is not accepted.
                if expected == 0 or visible < 0.7 * expected:
                    return False
        return True
    except Exception:
        # PDFium may report unsupported or malformed content through different
        # exceptions. Inability to prove visibility must never become an anchor.
        return False


def pdf_series_cover(pdf_path: Path) -> dict[str, object] | None:
    """Recover one independently visible first-page manufacturer series title.

    Docling can classify the product title as page furniture. The original ESA
    datasheet prints the series and its power range on one physical line there.
    The hosted STS originals instead put a standalone series title first,
    above an aligned Static Transfer Switch subtitle. Accept only those
    physically visible cover forms, not a compatibility mention in the body.
    """
    import pypdfium2

    with pdf_path.open("rb") as handle:
        sha = hashlib.file_digest(handle, "sha256").hexdigest()
    if pdf_path.stem != sha:
        raise ValueError("source PDF bytes do not match their content identity")
    pdf = pypdfium2.PdfDocument(pdf_path)
    try:
        if not len(pdf):
            return None
        page = pdf[0]
        try:
            if page.get_rotation() != 0:
                return None
            left, bottom, right, top = page.get_bbox()
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_range()
                # Offsets must address the exact original physical characters.
                if len(text) != textpage.count_chars():
                    return None
                ranged = re.compile(
                    r"(?im)^[ \t]*(?P<family>[a-z][a-z0-9]*[ \t]+series)"
                    r"[ \t]+Residential Energy Storage System[ \t]+I[ \t]+"
                    r"(?P<power>\d+(?:[.,]\d+)?[ \t]*[-–][ \t]*"
                    r"\d+(?:[.,]\d+)?[ \t]*kW)"
                    r"[ \t]*/[ \t]*\d+(?:[.,]\d+)?[ \t]*[-–][ \t]*"
                    r"\d+(?:[.,]\d+)?[ \t]*kWh[ \t\r]*$"
                )
                sts = re.compile(r"(?im)^[ \t]*(?P<family>STS[ \t]+series)[ \t\r]*$")
                matches = [
                    match
                    for pattern in (ranged, sts)
                    for match in pattern.finditer(text)
                ]
                if len(matches) != 1:
                    return None
                match = matches[0]

                def span_bounds(
                    start: int, end: int
                ) -> tuple[float, float, float, float]:
                    boxes = [
                        textpage.get_charbox(i)
                        for i in range(start, end)
                        if not text[i].isspace()
                    ]
                    return (
                        min(b[0] for b in boxes),
                        min(b[1] for b in boxes),
                        max(b[2] for b in boxes),
                        max(b[3] for b in boxes),
                    )

                family = span_bounds(match.start("family"), match.end("family"))
                power = (
                    span_bounds(match.start("power"), match.end("power"))
                    if "power" in match.re.groupindex
                    else None
                )
                subtitle_match = None
                subtitle = None
                if power is None:
                    # Both manufacturer originals place this as the first text
                    # on the page, followed by their switch/model subtitle.
                    # Other standalone series lines make the cover ambiguous.
                    series_lines = re.findall(
                        r"(?im)^[ \t]*[a-z][a-z0-9]*[ \t]+series[ \t\r]*$", text
                    )
                    subtitle_match = re.compile(r"\r?\n([^\r\n]+)").match(
                        text, match.end("family")
                    )
                    if (
                        match.start("family") != 0
                        or len(series_lines) != 1
                        or subtitle_match is None
                        or STS_COVER_SUBTITLE.fullmatch(subtitle_match.group(1)) is None
                    ):
                        return None
                    subtitle = span_bounds(
                        subtitle_match.start(1), subtitle_match.end(1)
                    )
                    height = family[3] - family[1]
                    if not (
                        left <= subtitle[0] < subtitle[2] <= right
                        and bottom <= subtitle[1] < subtitle[3] <= top
                        and subtitle[3] < family[1]
                        and family[1] - subtitle[3] < height
                        and abs(subtitle[0] - family[0]) < height
                        and subtitle[3] - subtitle[1] < height
                    ):
                        return None
                    # A later-extracted object can still be physically above
                    # the line or a larger heading. Neither is a cover title.
                    for i in range(match.end("family"), len(text)):
                        if text[i].isspace():
                            continue
                        box = textpage.get_charbox(i)
                        if box[3] > family[3] or box[3] - box[1] >= height:
                            return None
                    if not _visible_pdf_line(
                        pdf,
                        page,
                        textpage,
                        text,
                        subtitle_match.start(1),
                        subtitle_match.end(1),
                        (left, bottom, right, top),
                    ):
                        return None
                if not all(
                    left <= box[0] < box[2] <= right
                    and bottom <= box[1] < box[3] <= top
                    for box in (family, *([power] if power is not None else []))
                ):
                    return None
                if power is not None and (
                    family[2] >= power[0]
                    or max(family[1], power[1]) >= min(family[3], power[3])
                ):
                    return None
                if not _visible_pdf_line(
                    pdf,
                    page,
                    textpage,
                    text,
                    match.start(),
                    match.end(),
                    (left, bottom, right, top),
                ):
                    return None
                line = match.group(0).strip(" \t\r")
                line_start = (
                    match.start()
                    + len(match.group(0))
                    - len(match.group(0).lstrip(" \t"))
                )
                result: dict[str, object] = {
                    "kind": "pdf_cover",
                    "source_sha256": sha,
                    "source_page": 1,
                    "text": line,
                    "line_start": line_start,
                    "line_end": line_start + len(line),
                    "page_size": [right - left, top - bottom],
                    "family": {
                        "text": match.group("family"),
                        "char_start": match.start("family"),
                        "char_end": match.end("family"),
                        "bbox": [
                            family[0] - left,
                            family[1] - bottom,
                            family[2] - left,
                            family[3] - bottom,
                        ],
                    },
                }
                if power is not None:
                    result["power"] = {
                        "text": match.group("power"),
                        "char_start": match.start("power"),
                        "char_end": match.end("power"),
                        "bbox": [
                            power[0] - left,
                            power[1] - bottom,
                            power[2] - left,
                            power[3] - bottom,
                        ],
                    }
                if subtitle is not None and subtitle_match is not None:
                    result["subtitle"] = {
                        "text": subtitle_match.group(1),
                        "char_start": subtitle_match.start(1),
                        "char_end": subtitle_match.end(1),
                        "bbox": [
                            subtitle[0] - left,
                            subtitle[1] - bottom,
                            subtitle[2] - left,
                            subtitle[3] - bottom,
                        ],
                    }
                return result
            finally:
                textpage.close()
        finally:
            page.close()
    finally:
        pdf.close()


def _pdf_model_spans(
    pdf: object,
    number: int,
    sha: str,
    *,
    wrapped_spans: set[tuple[int, int]] | None = None,
) -> list[SourceSpan]:
    """Read original visible text positions, including a cropped spread's offset."""
    # PDFium's Python helper deliberately ships no type stubs. The object is
    # supplied only by enrich_model_axes, keeping parser dependencies offline.
    from typing import Any, cast

    page = cast(Any, pdf)[number - 1]
    try:
        if page.get_rotation() != 0:
            return []
        left, bottom, right, top = page.get_bbox()
        text_page = page.get_textpage()
        try:
            text = text_page.get_text_range()
            count = text_page.count_chars()
            indices: list[int] | None = None
            if len(text) != count:
                parts = []
                indices = []
                for index in range(count):
                    value = text_page.get_text_range(index, 1)
                    parts.append(value)
                    indices.extend([index] * len(value))
                text = "".join(parts)

            def bounds(begin: int, end: int) -> tuple[float, float, float, float]:
                first = indices[begin] if indices is not None else begin
                last = indices[end - 1] + 1 if indices is not None else end
                boxes = [text_page.get_charbox(index) for index in range(first, last)]
                return (
                    min(b[0] for b in boxes),
                    min(b[1] for b in boxes),
                    max(b[2] for b in boxes),
                    max(b[3] for b in boxes),
                )

            output: list[SourceSpan] = []
            # The same one-character normalization as clean(), retaining original
            # char offsets. An explicit PDFium wrap must also occupy one column.
            for match in TOKEN.finditer(text.replace("￾", "-")):
                if not (
                    any(c.isalpha() for c in match[0])
                    and any(c.isdigit() for c in match[0])
                ):
                    continue
                start = indices[match.start()] if indices is not None else match.start()
                end = (
                    indices[match.end() - 1] + 1 if indices is not None else match.end()
                )
                written = text[match.start() : match.end()]
                source_fragments: list[SourceFragment] = []
                if "￾" in written:
                    fragments = []
                    offset = match.start()
                    for part in written.split("￾"):
                        if not part:
                            break
                        end_offset = offset + len(part)
                        box_part = bounds(offset, end_offset)
                        fragments.append(box_part)
                        source_fragments.append(
                            SourceFragment(
                                text=part,
                                bbox=(
                                    box_part[0] - left,
                                    top - box_part[3],
                                    box_part[2] - left,
                                    top - box_part[1],
                                ),
                                char_start=indices[offset]
                                if indices is not None
                                else offset,
                                char_end=(
                                    indices[end_offset - 1] + 1
                                    if indices is not None
                                    else end_offset
                                ),
                            )
                        )
                        offset += len(part) + 1
                    if (
                        len(fragments) != len(written.split("￾"))
                        or any(
                            not (
                                a[0] <= (b[0] + b[2]) / 2 <= a[2]
                                and b[0] <= (a[0] + a[2]) / 2 <= b[2]
                                # Adjacent original text lines: the gap cannot exceed
                                # either fragment's own glyph height.
                                and 0 <= a[1] - b[3] <= min(a[3] - a[1], b[3] - b[1])
                            )
                            for a, b in zip(fragments, fragments[1:], strict=False)
                        )
                    ):
                        continue
                box = bounds(match.start(), match.end())
                # A PDF spread can contain an entire off-crop page's text.
                # Hidden words cannot become the displayed table's model axis.
                if box[0] < left or box[2] > right or box[1] < bottom or box[3] > top:
                    continue
                if wrapped_spans is not None and "￾" in written:
                    wrapped_spans.add((start, end))
                span = SourceSpan(
                    text=match[0],
                    bbox=(box[0] - left, top - box[3], box[2] - left, top - box[1]),
                    char_start=start,
                    char_end=end,
                    page=number,
                    source_sha256=sha,
                    page_size=(right - left, top - bottom),
                )
                if source_fragments:
                    span["fragments"] = source_fragments
                output.append(span)
            return output
        finally:
            text_page.close()
    finally:
        page.close()


def _single_line_cells(
    pdf: object,
    number: int,
    cells: list[SourceCell],
    *,
    section_rows: set[int] | None = None,
) -> list[SourceCell]:
    """A recovered axis cannot release body cells merged across physical lines."""
    from typing import Any, cast

    page = cast(Any, pdf)[number - 1]
    try:
        left, bottom, right, top = page.get_bbox()
        text_page = page.get_textpage()
        try:
            text = text_page.get_text_range().replace("￾", "-")
            # Ambiguous character offsets cannot supply physical cell evidence.
            if len(text) != text_page.count_chars():
                text = ""
            retained = []
            for cell in cells:
                if (
                    cell["column_header"]
                    or cell["row_section"]
                    or cell.get("external_axis")
                    or (
                        section_rows is not None
                        and cell["col_start"] == 0
                        and cell["row_start"] in section_rows
                    )
                ):
                    retained.append(cell)
                    continue
                box = cell["bbox"]
                if box is None or cell["bbox_origin"] != "TOPLEFT" or not cell["text"]:
                    continue
                words = cell["text"].split()
                if not words:
                    continue
                pattern = r"(?<!\S)" + re.escape(words[0])
                for word in words[1:]:
                    # Docling may add a space before an original superscript
                    # note marker; all other word boundaries stay strict.
                    pattern += r"\s*" if re.fullmatch(r"\*\d+", word) else r"\s+"
                    pattern += re.escape(word)
                pattern += r"(?!\S)"
                proven = 0
                proven_box = None
                for match in re.finditer(pattern, text):
                    characters = [
                        (text[i], text_page.get_charbox(i))
                        for i in range(match.start(), match.end())
                        if not text[i].isspace()
                    ]
                    glyphs = [b for char, b in characters if char.isalnum()]
                    # A shared vertical glyph band proves one original line.
                    # Punctuation may sit below that band; it still must be visible.
                    if not glyphs or max(b[1] for b in glyphs) >= min(
                        b[3] for b in glyphs
                    ):
                        continue
                    x0 = min(b[0] for _, b in characters)
                    y0 = min(b[1] for _, b in characters)
                    x1 = max(b[2] for _, b in characters)
                    y1 = max(b[3] for _, b in characters)
                    if (
                        left <= x0 <= x1 <= right
                        and bottom <= y0 <= y1 <= top
                        and box[0] <= (x0 + x1) / 2 - left <= box[2]
                        and min(box[1], box[3])
                        <= top - (y0 + y1) / 2
                        <= max(box[1], box[3])
                    ):
                        proven += 1
                        proven_box = (x0 - left, top - y1, x1 - left, top - y0)
                if proven == 1 and proven_box is not None:
                    # Later row/column alignment must use the matched visible
                    # glyphs, never a parser box spanning neighbouring lines.
                    retained.append({**cell, "bbox": proven_box})
            return retained
        finally:
            text_page.close()
    finally:
        page.close()


def _visible_box(
    box: BoundingBox, width: float, height: float
) -> tuple[float, float, float, float] | None:
    """A native box expressed in the same visible page coordinates as PDF spans."""
    if box.coord_origin.value == "BOTTOMLEFT":
        bounds = (box.l, height - box.t, box.r, height - box.b)
    elif box.coord_origin.value == "TOPLEFT":
        bounds = (box.l, box.t, box.r, box.b)
    else:
        return None
    if not all(math.isfinite(value) for value in bounds):
        return None
    x0, y0, x1, y1 = bounds
    return bounds if 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height else None


def _external_sections(
    pdf: object,
    number: int,
    cells: Sequence[SourceCell],
    table_bbox: tuple[float, float, float, float],
) -> tuple[list[int], list[int]]:
    """Verify native section labels and keep unverified empty rows as barriers."""
    from typing import Any, cast

    candidates = [
        cell
        for cell in cells
        if cell["col_start"] == 0
        and cell["row_end"] == cell["row_start"] + 1
        and cell["text"]
        and not any(
            other is not cell
            and other["col_start"] >= 1
            and other["row_start"] <= cell["row_start"] < other["row_end"]
            and other["text"]
            for other in cells
        )
    ]
    barriers = sorted({cell["row_start"] for cell in candidates})
    page = cast(Any, pdf)[number - 1]
    try:
        left, bottom, right, top = page.get_bbox()
        text_page = page.get_textpage()
        try:
            text = text_page.get_text_range()
            if len(text) != text_page.count_chars():
                return [], barriers
            indexes = [index for index, char in enumerate(text) if not char.isspace()]
            compact = "".join(text[index] for index in indexes).replace("￾", "-")
            boxes = {index: text_page.get_charbox(index) for index in indexes}
            proven: list[int] = []
            for cell in candidates:
                native = cell["bbox"]
                if native is None or cell["bbox_origin"] != "TOPLEFT":
                    continue
                written = "".join(cell["text"].split()).replace("￾", "-")
                hits = []
                start = compact.find(written)
                while start >= 0:
                    selected = indexes[start : start + len(written)]
                    glyphs = [
                        boxes[index] for index in selected if text[index].isalnum()
                    ]
                    if glyphs and max(box[1] for box in glyphs) < min(
                        box[3] for box in glyphs
                    ):
                        x0 = min(boxes[index][0] for index in selected)
                        x1 = max(boxes[index][2] for index in selected)
                        y0 = min(boxes[index][1] for index in selected)
                        y1 = max(boxes[index][3] for index in selected)
                        if (
                            left <= x0 < x1 <= right
                            and bottom <= y0 < y1 <= top
                            and native[0] <= (x0 + x1) / 2 - left <= native[2]
                            and native[1] <= top - (y0 + y1) / 2 <= native[3]
                        ):
                            hits.append(
                                (
                                    x1,
                                    max(box[1] for box in glyphs),
                                    min(box[3] for box in glyphs),
                                )
                            )
                    start = compact.find(written, start + 1)
                if len(hits) != 1:
                    continue
                x1, band_bottom, band_top = hits[0]
                right_text = any(
                    x1 < (box[0] + box[2]) / 2 - left <= table_bbox[2]
                    and band_bottom <= (box[1] + box[3]) / 2 <= band_top
                    and left <= box[0] < box[2] <= right
                    and bottom <= box[1] < box[3] <= top
                    for box in boxes.values()
                )
                if not right_text:
                    proven.append(cell["row_start"])
            return sorted(set(proven)), barriers
        finally:
            text_page.close()
    finally:
        page.close()


def _native_footnotes(
    pages: Sequence[Page],
    pdf: object,
    sha: str,
    table_page: Page,
    table: Block,
    pdf_counts: dict[str, dict[int, int]],
    pdf_references: dict[
        str, list[tuple[int, tuple[float, float, float, float] | None]]
    ],
    complete_pages: bool,
) -> list[SourceFootnote]:
    """Capture complete, unambiguous source notes for one original table."""
    from typing import Any, cast

    candidates: dict[str, list[tuple[Page, Block]]] = {}
    for page in pages:
        for block in page.blocks:
            raw = block.source_original or block.text
            for marker in re.findall(r"(?<!\S)\*(\d+)\s*:", raw):
                candidates.setdefault(marker, []).append((page, block))
    output: list[SourceFootnote] = []
    for marker, entries in candidates.items():
        same_page = [entry for entry in entries if entry[0].number == table_page.number]
        if same_page:
            tables = [
                item
                for item in table_page.blocks
                if item.kind == "table" and not item.source_picture
            ]
            if (
                len(same_page) != 1
                or len(tables) != 1
                or tables[0].source_id != table.source_id
                or pdf_counts.get(marker, {}).get(table_page.number) != 1
            ):
                continue
            source_page, block = same_page[0]
            table_index = next(
                i
                for i, item in enumerate(table_page.blocks)
                if item.source_id == table.source_id
            )
            note_index = next(
                i
                for i, item in enumerate(table_page.blocks)
                if item.source_id == block.source_id
            )
            if note_index <= table_index:
                continue
        elif (
            len(entries) == 1
            and complete_pages
            and sum(pdf_counts.get(marker, {}).values()) == 1
            and entries[0][0].number > table_page.number
            and _uncontested_cross_page_marker(
                marker, pages, pdf, table_page, table, pdf_references
            )
        ):
            source_page, block = entries[0]
        else:
            continue
        text = block.source_original
        if (
            block.kind != "text"
            or block.source_picture
            or not block.source_id
            or text != block.text
            or re.fullmatch(r"\*\d+:\s+\S[^\r\n]*", text) is None
            or len(block.source_prov) != 1
        ):
            continue
        prov = block.source_prov[0]
        if prov.page_no != source_page.number or prov.charspan != (0, len(text)):
            continue
        page = cast(Any, pdf)[source_page.number - 1]
        try:
            left, bottom, right, top = page.get_bbox()
            if page.get_rotation() != 0 or left != 0 or bottom != 0:
                continue
            width, height = right - left, top - bottom
            source_box = _visible_box(prov.bbox, width, height)
            if source_box is None:
                continue
            text_page = page.get_textpage()
            try:
                body = text_page.get_text_range()
                start = body.find(text)
                if (
                    len(body) != text_page.count_chars()
                    or start < 0
                    or body.find(text, start + 1) >= 0
                ):
                    continue
                glyphs = [
                    text_page.get_charbox(index)
                    for index in range(start, start + len(text))
                    if not body[index].isspace()
                ]
                if not glyphs or any(
                    not (
                        left <= box[0] < box[2] <= right
                        and bottom <= box[1] < box[3] <= top
                        and source_box[0]
                        <= (box[0] + box[2]) / 2 - left
                        <= source_box[2]
                        and source_box[1]
                        <= top - (box[1] + box[3]) / 2
                        <= source_box[3]
                    )
                    for box in glyphs
                ):
                    continue
                bounds = (
                    min(box[0] for box in glyphs) - left,
                    top - max(box[3] for box in glyphs),
                    max(box[2] for box in glyphs) - left,
                    top - min(box[1] for box in glyphs),
                )
                output.append(
                    SourceFootnote(
                        source_id=block.source_id,
                        text=text,
                        source_span=SourceTextSpan(
                            source_id=block.source_id,
                            bbox=source_box,
                            char_start=0,
                            char_end=len(text),
                        ),
                        pdf_span=SourceSpan(
                            text=text,
                            bbox=bounds,
                            char_start=start,
                            char_end=start + len(text),
                            page=source_page.number,
                            source_sha256=sha,
                            page_size=(width, height),
                        ),
                    )
                )
            finally:
                text_page.close()
        finally:
            page.close()
    return output


def _uncontested_cross_page_marker(
    marker: str,
    pages: Sequence[Page],
    pdf: object,
    table_page: Page,
    table: Block,
    pdf_references: dict[
        str, list[tuple[int, tuple[float, float, float, float] | None]]
    ],
) -> bool:
    """A cross-page note must not be claimed by another original table."""
    from typing import Any, cast

    if any(page.source != "docling" for page in pages):
        return False
    pattern = re.compile(r"\*\s*" + re.escape(marker) + r"(?!\d)")
    if not any(pattern.search(cell["text"]) for cell in table.source_cells):
        return False
    for page in pages:
        for other in page.blocks:
            if other is table or other.kind != "table":
                continue
            if any(pattern.search(cell["text"]) for cell in other.source_cells) or any(
                pattern.search(text) for row in other.rows for text in row
            ):
                return False
    references = pdf_references.get(marker, [])
    if not references or len(table.source_prov) != 1:
        return False
    physical_page = cast(Any, pdf)[table_page.number - 1]
    try:
        left, bottom, right, top = physical_page.get_bbox()
        if physical_page.get_rotation() != 0 or left != 0 or bottom != 0:
            return False
        table_box = _visible_box(table.source_prov[0].bbox, right - left, top - bottom)
    finally:
        physical_page.close()
    if table_box is None or table.source_prov[0].page_no != table_page.number:
        return False
    x0, y0, x1, y1 = table_box
    return all(
        page == table_page.number
        and box is not None
        and x0 <= box[0] < box[2] <= x1
        and y0 <= box[1] < box[3] <= y1
        for page, box in references
    )


def _pdf_footnote_counts(
    pages: Sequence[Page], pdf: object
) -> tuple[
    dict[str, dict[int, int]],
    dict[str, list[tuple[int, tuple[float, float, float, float] | None]]],
]:
    """Find original numbered declarations and visible marker references."""
    from typing import Any, cast

    counts: dict[str, dict[int, int]] = {}
    references: dict[
        str, list[tuple[int, tuple[float, float, float, float] | None]]
    ] = {}
    for source_page in pages:
        page = cast(Any, pdf)[source_page.number - 1]
        try:
            text_page = page.get_textpage()
            try:
                body = text_page.get_text_range()
                left, bottom, right, top = page.get_bbox()
                visible = (
                    len(body) == text_page.count_chars()
                    and page.get_rotation() == 0
                    and left == 0
                    and bottom == 0
                )
                for match in re.finditer(r"\*\s*(\d+)(?!\d)", body):
                    marker = match.group(1)
                    if re.match(r"\s*:", body[match.end() :]):
                        per_page = counts.setdefault(marker, {})
                        per_page[source_page.number] = (
                            per_page.get(source_page.number, 0) + 1
                        )
                        continue
                    bounds = None
                    if visible:
                        glyphs = [
                            text_page.get_charbox(index)
                            for index in range(match.start(), match.end())
                            if not body[index].isspace()
                        ]
                        if glyphs and all(
                            all(math.isfinite(value) for value in box)
                            and left <= box[0] < box[2] <= right
                            and bottom <= box[1] < box[3] <= top
                            for box in glyphs
                        ):
                            bounds = (
                                min(box[0] for box in glyphs) - left,
                                top - max(box[3] for box in glyphs),
                                max(box[2] for box in glyphs) - left,
                                top - min(box[1] for box in glyphs),
                            )
                    references.setdefault(marker, []).append(
                        (source_page.number, bounds)
                    )
            finally:
                text_page.close()
        finally:
            page.close()
    return counts, references


def _external_axis(
    pdf: object,
    page: int,
    previous: Sequence[Block],
    table: Block,
    spans: list[SourceSpan],
) -> ExternalAxis | None:
    """Capture consecutive, visible original body text preceding a native table."""
    from typing import Any, cast

    if (
        not previous
        or table.source_picture
        or any(
            block.kind != "text"
            or not block.source_id
            or block.source_picture
            or block.source_original != block.text
            or not block.source_prov
            for block in previous
        )
        or len({block.source_id for block in previous}) != len(previous)
        or len(table.source_prov) != 1
        or table.source_prov[0].page_no != page
    ):
        return None
    source_text = "\n".join(block.text for block in previous)
    match = re.fullmatch(
        r"(?:Technical\s+Data|Technische\s+Daten)\s+"
        r"[A-Za-z0-9][A-Za-z0-9./\s-]*",
        source_text,
        re.IGNORECASE,
    )
    if match is None:
        return None
    header = [
        cell
        for cell in table.source_cells
        if cell["row_start"] == 0 and cell["row_end"] == 1 and cell["text"]
    ]
    first = [cell for cell in header if cell["col_start"] == 0]
    if len(first) != 1:
        return None
    value_col_start = first[0]["col_end"]
    first_row_is_data = any(cell["col_start"] >= value_col_start for cell in header)
    if (
        value_col_start < 1
        or (not first_row_is_data and value_col_start != 1)
        or (first_row_is_data and (value_col_start != 2 or first[0]["column_header"]))
        or any(
            cell is not first[0] and cell["col_start"] < value_col_start
            for cell in header
        )
    ):
        return None
    physical_page = cast(Any, pdf)[page - 1]
    try:
        left, bottom, right, top = physical_page.get_bbox()
        if physical_page.get_rotation() != 0 or left != 0 or bottom != 0:
            return None
        width, height = right - left, top - bottom
    finally:
        physical_page.close()
    table_bbox = _visible_box(table.source_prov[0].bbox, width, height)
    if table_bbox is None:
        return None
    source_spans: list[SourceTextSpan] = []
    offset = 0
    for block in previous:
        for prov in block.source_prov:
            box = _visible_box(prov.bbox, width, height)
            start, end = prov.charspan
            if (
                prov.page_no != page
                or box is None
                or not 0 <= start < end <= len(block.text)
            ):
                return None
            source_spans.append(
                SourceTextSpan(
                    source_id=block.source_id,
                    bbox=box,
                    char_start=offset + start,
                    char_end=offset + end,
                )
            )
        offset += len(block.text) + 1

    def original_piece(
        piece: SourceFragment | SourceSpan, *, wrapped_prefix: bool
    ) -> tuple[int, int] | None:
        box = piece["bbox"]
        pattern = re.compile(
            r"(?<![A-Za-z0-9./-])"
            + re.escape(piece["text"])
            + (r"-?" if wrapped_prefix else "")
            + r"(?![A-Za-z0-9./-])",
            re.IGNORECASE,
        )
        occurrences = [
            (s["char_start"] + match.start(), s["char_start"] + match.end())
            for s in source_spans
            if s["bbox"][0] <= (box[0] + box[2]) / 2 <= s["bbox"][2]
            and s["bbox"][1] <= (box[1] + box[3]) / 2 <= s["bbox"][3]
            for match in pattern.finditer(source_text[s["char_start"] : s["char_end"]])
        ]
        return occurrences[0] if len(occurrences) == 1 else None

    matched: list[SourceSpan] = []
    covered: set[tuple[int, int]] = set()
    for span in spans:
        pieces: list[SourceFragment | SourceSpan] = list(span.get("fragments", [])) or [
            span
        ]
        positions = [
            original_piece(piece, wrapped_prefix=index < len(pieces) - 1)
            for index, piece in enumerate(pieces)
        ]
        if all(position is not None for position in positions):
            matched.append(span)
            covered.update(position for position in positions if position is not None)
    heading = re.match(r"(?:Technical\s+Data|Technische\s+Daten)\s+", source_text, re.I)
    assert heading is not None
    if (
        len(matched) < 2
        or max((cell["col_end"] for cell in table.source_cells), default=0)
        != len(matched) + value_col_start
        or len({s["text"].casefold() for s in matched}) != len(matched)
        or any(
            m.span() not in covered for m in TOKEN.finditer(source_text, heading.end())
        )
        or any(s["bbox"][3] > table_bbox[1] for s in matched)
        or (
            first_row_is_data
            and any(
                "-" in token
                and any(c.isalpha() for c in token)
                and any(c.isdigit() for c in token)
                for cell in header
                if cell is not first[0]
                for token in TOKEN.findall(cell["text"])
            )
        )
        or (
            first_row_is_data
            and any(
                re.search(
                    r"(?<![\w./-])" + re.escape(span["text"]) + r"(?![\w./-])",
                    cell["text"],
                    re.IGNORECASE,
                )
                for cell in header
                if cell is not first[0]
                for span in matched
            )
        )
    ):
        return None
    section_rows, section_barriers = _external_sections(
        pdf, page, table.source_cells, table_bbox
    )
    return ExternalAxis(
        source_ids=[block.source_id for block in previous],
        source_text=source_text,
        source_spans=source_spans,
        table_bbox=table_bbox,
        model_spans=matched,
        section_rows=section_rows,
        section_barriers=section_barriers,
        footnotes=[],
        value_col_start=value_col_start,
        first_row_is_data=first_row_is_data,
    )


def _preceding_axis_blocks(blocks: Sequence[Block]) -> list[Block]:
    """Keep only the contiguous body axis; figures supply no heading text."""
    result: list[Block] = []
    for block in reversed(blocks):
        if block.source_picture:
            if block.kind == "table":
                break
            continue
        if block.kind != "text":
            break
        result.append(block)
        if re.match(r"^(?:Technical\s+Data|Technische\s+Daten)\b", block.text, re.I):
            return list(reversed(result))
    return []


def enrich_model_axes(pages: list[Page], pdf_path: Path) -> list[Page]:
    """Supplement cached native cells with original physical model-label order.

    Neither PDF bytes nor cached Docling text are rewritten. A merged logical
    header's reading-order string is insufficient; original text-layer token
    coordinates prove which model occupies which physical value column.
    """
    import pypdfium2

    with pdf_path.open("rb") as handle:
        sha = hashlib.file_digest(handle, "sha256").hexdigest()
    if pdf_path.stem != sha:
        raise ValueError("source PDF bytes do not match their content identity")
    output: list[Page] = []
    pdf = pypdfium2.PdfDocument(pdf_path)
    footnotes: dict[tuple[int, str], list[SourceFootnote]] = {}
    pdf_notes: (
        tuple[
            dict[str, dict[int, int]],
            dict[str, list[tuple[int, tuple[float, float, float, float] | None]]],
        ]
        | None
    ) = None
    complete_pages = len(pages) == len(pdf) and {page.number for page in pages} == set(
        range(1, len(pdf) + 1)
    )
    try:
        for page in pages:
            if not any(block.source_cells for block in page.blocks):
                output.append(page)
                continue
            wrapped_spans: set[tuple[int, int]] = set()
            spans = _pdf_model_spans(pdf, page.number, sha, wrapped_spans=wrapped_spans)
            blocks = []
            for index, block in enumerate(page.blocks):
                cells: list[SourceCell] = []
                recovered = False
                external = (
                    _external_axis(
                        pdf,
                        page.number,
                        _preceding_axis_blocks(page.blocks[:index]),
                        block,
                        spans,
                    )
                    if index and block.kind == "table" and block.source_cells
                    else None
                )
                if external:
                    key = (page.number, block.source_id)
                    if key not in footnotes:
                        if pdf_notes is None:
                            pdf_notes = _pdf_footnote_counts(pages, pdf)
                        footnotes[key] = _native_footnotes(
                            pages,
                            pdf,
                            sha,
                            page,
                            block,
                            pdf_notes[0],
                            pdf_notes[1],
                            complete_pages,
                        )
                    external["footnotes"] = footnotes[key]
                for cell in block.source_cells:
                    own: SourceCell = {**cell}
                    if external and cell["row_start"] == 0 and cell["col_start"] == 0:
                        own["external_axis"] = external
                        recovered = True
                    box = cell["bbox"]
                    if (
                        cell["row_start"] == 0
                        and cell["row_end"] == 1
                        and cell["col_start"] > 0
                        and cell["column_header"]
                        and box is not None
                        and cell["bbox_origin"] == "TOPLEFT"
                    ):
                        original = {
                            token.casefold() for token in TOKEN.findall(cell["text"])
                        }
                        labels = {
                            token.casefold()
                            for token in TOKEN.findall(
                                re.sub(r"(?<=-)\s+", "", cell["text"])
                            )
                        }
                        matched = [
                            span
                            for span in spans
                            if (
                                span["text"].casefold() in labels
                                or any(
                                    token.endswith("-")
                                    and span["text"].casefold().startswith(token)
                                    for token in original
                                )
                            )
                            and box[0]
                            <= (span["bbox"][0] + span["bbox"][2]) / 2
                            <= box[2]
                            and min(box[1], box[3])
                            <= (span["bbox"][1] + span["bbox"][3]) / 2
                            <= max(box[1], box[3])
                        ]
                        if matched:
                            # A native header may already be complete while its
                            # physical axis is newly recovered from a PDF wrap.
                            recovered = recovered or any(
                                (s["char_start"], s["char_end"]) in wrapped_spans
                                for s in matched
                            )
                            if (
                                len(matched) == cell["col_end"] - cell["col_start"]
                                and any(
                                    s["text"].casefold() not in original
                                    for s in matched
                                )
                                and all(
                                    any(
                                        s["text"].casefold().startswith(token)
                                        or s["text"].casefold().endswith(token)
                                        for s in matched
                                    )
                                    for token in original
                                )
                            ):
                                # Only the in-memory header is recovered from exact
                                # visible PDF labels. Cached cells and body rows stay
                                # unchanged, including a suffix misplaced by Docling.
                                own["text"] = " ".join(
                                    s["text"]
                                    for s in sorted(matched, key=lambda s: s["bbox"][0])
                                )
                                recovered = True
                            own["model_spans"] = matched
                    cells.append(own)
                if recovered:
                    cells = _single_line_cells(
                        pdf,
                        page.number,
                        cells,
                        section_rows=set(external["section_rows"])
                        if external
                        else None,
                    )
                blocks.append(replace(block, source_cells=tuple(cells)))
            output.append(Page(page.number, page.source, blocks))
    finally:
        pdf.close()
    return output


def extract(
    parsed_dir: Path,
    page_count: int,
    garbled: Iterable[int],
    *,
    pdf_path: Path | None = None,
) -> list[Page]:
    """Every physical page of one document, empty when nothing on it is text."""
    main = parsed_dir / "docling.json"
    blocks = pages_of(load_document(main)) if main.is_file() else {}
    pages = [
        Page(number, "docling", blocks.get(number, []))
        for number in range(1, page_count + 1)
    ]
    for number in garbled:
        ocr = parsed_dir / f"ocr-p{number}.json"
        if ocr.is_file():
            # The rendered page is a one-page document of its own.
            pages[number - 1] = Page(
                number, "ocr", pages_of(load_document(ocr)).get(1, [])
            )
    return enrich_model_axes(pages, pdf_path) if pdf_path is not None else pages
