"""Extract: a cached Docling parse -> the text blocks of each physical page.

Reads what `index.parse` cached for one document and returns, page by page, the body
in reading order as headings, text and tables (rows of cell texts, column-header rows
first). A page whose text layer is unreadable takes its blocks from the OCR of its
rendered image instead. Page furniture (running headers and footers) is not body text
and is left out, as Docling classifies it.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table import TableItem
from docling_core.types.doc.items.text import SectionHeaderItem, TextItem, TitleItem

from linker_genie.table_projection import TOKEN, SourceCell, SourceSpan

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


def _blocks(document: DoclingDocument) -> Iterable[tuple[int, Block]]:
    """(page number, block) in reading order, for every body item that holds text."""
    for item, _level in document.iterate_items(traverse_pictures=True):
        if isinstance(item, TableItem) and item.prov:
            rows, header_rows = _table_rows(item)
            if rows:
                yield (
                    item.prov[0].page_no,
                    Block(
                        kind="table",
                        rows=rows,
                        header_rows=header_rows,
                        source_id=item.self_ref,
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
                heading = isinstance(item, (SectionHeaderItem, TitleItem))
                yield (
                    item.prov[0].page_no,
                    Block(
                        kind="heading" if heading else "text",
                        text=text,
                        source_id=item.self_ref,
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


def _pdf_model_spans(pdf: object, number: int, sha: str) -> list[SourceSpan]:
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
            output: list[SourceSpan] = []
            for match in TOKEN.finditer(text):
                if not (
                    any(c.isalpha() for c in match[0])
                    and any(c.isdigit() for c in match[0])
                ):
                    continue
                start = indices[match.start()] if indices is not None else match.start()
                end = (
                    indices[match.end() - 1] + 1 if indices is not None else match.end()
                )
                boxes = [text_page.get_charbox(index) for index in range(start, end)]
                box = (
                    min(b[0] for b in boxes),
                    min(b[1] for b in boxes),
                    max(b[2] for b in boxes),
                    max(b[3] for b in boxes),
                )
                # A PDF spread can contain an entire off-crop page's text.
                # Hidden words cannot become the displayed table's model axis.
                if box[0] < left or box[2] > right or box[1] < bottom or box[3] > top:
                    continue
                output.append(
                    SourceSpan(
                        text=match[0],
                        bbox=(box[0] - left, top - box[3], box[2] - left, top - box[1]),
                        char_start=start,
                        char_end=end,
                        page=number,
                        source_sha256=sha,
                    )
                )
            return output
        finally:
            text_page.close()
    finally:
        page.close()


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
    try:
        for page in pages:
            if not any(block.source_cells for block in page.blocks):
                output.append(page)
                continue
            spans = _pdf_model_spans(pdf, page.number, sha)
            blocks = []
            for block in page.blocks:
                cells: list[SourceCell] = []
                for cell in block.source_cells:
                    own: SourceCell = {**cell}
                    box = cell["bbox"]
                    if (
                        cell["row_start"] == 0
                        and cell["row_end"] == 1
                        and cell["col_start"] > 0
                        and cell["column_header"]
                        and box is not None
                        and cell["bbox_origin"] == "TOPLEFT"
                    ):
                        labels = {
                            token.casefold() for token in TOKEN.findall(cell["text"])
                        }
                        matched = [
                            span
                            for span in spans
                            if span["text"].casefold() in labels
                            and box[0]
                            <= (span["bbox"][0] + span["bbox"][2]) / 2
                            <= box[2]
                            and min(box[1], box[3])
                            <= (span["bbox"][1] + span["bbox"][3]) / 2
                            <= max(box[1], box[3])
                        ]
                        if matched:
                            own["model_spans"] = matched
                    cells.append(own)
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
