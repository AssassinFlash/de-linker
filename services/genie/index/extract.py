"""Extract: a cached Docling parse -> the text blocks of each physical page.

Reads what `index.parse` cached for one document and returns, page by page, the body
in reading order as headings, text and tables (rows of cell texts, column-header rows
first). A page whose text layer is unreadable takes its blocks from the OCR of its
rendered image instead. Page furniture (running headers and footers) is not body text
and is left out, as Docling classifies it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table import TableItem
from docling_core.types.doc.items.text import SectionHeaderItem, TextItem, TitleItem

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


def extract(parsed_dir: Path, page_count: int, garbled: Iterable[int]) -> list[Page]:
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
    return pages
