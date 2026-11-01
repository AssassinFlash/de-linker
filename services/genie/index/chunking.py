"""Chunking: the blocks of one document -> chunks of at most MAX_TOKENS tokens.

Rules (docs/specs/10-knowledge-index.md, Build 2):
- A chunk never spans two pages, so its page is the page every citation of it shows.
- A heading closes the chunk before it and names the section of the chunks after it;
  the section carries over page breaks until the next heading.
- A table is a chunk of its own. A table too long for one chunk is cut between rows,
  and every piece repeats the table's column-header rows.
- Every chunk starts with a context header `brand | models | type | title | section | p. N`,
  built from the inventory, never generated; header and text are both what BM25 and
  the embedding see, and the header counts towards the limit.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from index.extract import Block, Page
from linker_genie.source_roles import meter_references, pack_model_row
from linker_genie.table_projection import SourceCell

# Spec (docs/specs/10-knowledge-index.md, Build 2): at most 512 tokens per chunk.
# Evidence behind it: arXiv 2605.27444 (2026-05, RAG over technical documents) found a
# "preference for passages up to 512 tokens" (docs/research/2026-10-09/knowledge-audit.md B2).
MAX_TOKENS = 512


class Tokenizer(Protocol):
    """The embedding model's tokenizer: the limit is counted in its tokens."""

    def count(self, text: str) -> int:
        """Tokens in `text`, without the model's special tokens."""
        ...

    def split(self, text: str, max_tokens: int) -> list[str]:
        """`text` cut into pieces of at most `max_tokens` tokens each."""
        ...


@dataclass(frozen=True)
class DocumentMeta:
    """What the inventory knows about the document a chunk comes from."""

    sha256: str
    title_en: str
    title_de: str
    brands: tuple[str, ...]
    models: tuple[str, ...]
    doc_type: str
    lang: str


ChunkKind = Literal["text", "table"]


@dataclass(frozen=True)
class Chunk:
    """One retrievable passage."""

    id: str
    doc_sha256: str
    page: int
    section: str
    kind: ChunkKind
    header: str
    text: str
    lang: str
    tokens: int
    source_table: str = ""
    preceding_text: tuple[str, ...] = ()
    source_rows: tuple[int, ...] = ()
    # One copy on a TableItem's first chunk; unchanged native cell coordinates
    # distinguish a shared merged value from an empty, unproven neighbour.
    source_cells: tuple[SourceCell, ...] = ()
    # Original headings encountered since the preceding emitted chunk. Keeping
    # even empty heading transitions prevents a generic child from erasing a
    # narrower authored parent before the applicability compiler sees it.
    source_headings: tuple[str, ...] = ()
    # A figure may contain its own model labels and restrictions. They must
    # not become headings or document-wide scope for later body passages.
    source_picture: str = ""
    # A cover line recovered directly from a visible PDF text layer. Its
    # physical provenance is stored independently and checked at retrieval.
    source_pdf_cover: dict[str, object] | None = None
    # SHA-bound PDF text-layer evidence for a certificate page marker or a
    # model split across two physically adjacent lines in its original cell.
    source_certificate_evidence: tuple[dict[str, object], ...] = ()


def context_header(meta: DocumentMeta, section: str, page: int) -> str:
    """`brand | models | type | title | section | p. N`, empty parts left out."""
    title = meta.title_en
    if meta.title_de and meta.title_de != meta.title_en:
        title = f"{meta.title_en} / {meta.title_de}"
    parts = [
        ", ".join(meta.brands),
        ", ".join(meta.models),
        meta.doc_type,
        title,
        section,
    ]
    return " | ".join([part for part in parts if part] + [f"p. {page}"])


def table_lines(block: Block) -> tuple[list[str], list[str]]:
    """A table as `| a | b |` lines: (column-header rows, the other rows)."""
    lines = ["| " + " | ".join(row) + " |" for row in block.rows]
    return lines[: block.header_rows], lines[block.header_rows :]


class _Chunker:
    """Packs the blocks of a document into chunks, page by page."""

    def __init__(
        self,
        meta: DocumentMeta,
        tokenizer: Tokenizer,
        detect_lang: Callable[[str], str],
        max_tokens: int,
    ) -> None:
        self.meta = meta
        self.tokenizer = tokenizer
        self.detect_lang = detect_lang
        self.max_tokens = max_tokens
        self.chunks: list[Chunk] = []
        self._ids: set[str] = set()
        self._preceding_text: list[str] = []
        self._pending_headings: list[str] = []
        self._source_picture = ""
        self._body_preceding_text: list[str] = []

    def _tokens(self, header: str, lines: Sequence[str]) -> int:
        return self.tokenizer.count(header + "\n" + "\n".join(lines))

    def _emit(
        self,
        page: int,
        section: str,
        kind: ChunkKind,
        lines: Sequence[str],
        source_table: str = "",
        preceding_text: tuple[str, ...] = (),
        source_rows: tuple[int, ...] = (),
    ) -> None:
        header = context_header(self.meta, section, page)
        text = "\n".join(lines)
        lang = (
            self.meta.lang if self.meta.lang in ("en", "de") else self.detect_lang(text)
        )
        digest = hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()[:8]
        chunk_id = base = f"{self.meta.sha256[:12]}-p{page}-{digest}"
        suffix = 1
        while chunk_id in self._ids:
            suffix += 1
            chunk_id = f"{base}-{suffix}"
        self._ids.add(chunk_id)
        self.chunks.append(
            Chunk(
                id=chunk_id,
                doc_sha256=self.meta.sha256,
                page=page,
                section=section,
                kind=kind,
                header=header,
                text=text,
                lang=lang,
                tokens=self._tokens(header, lines),
                source_table=source_table,
                preceding_text=preceding_text,
                source_rows=source_rows,
                source_headings=tuple(self._pending_headings),
                source_picture=self._source_picture,
            )
        )
        self._pending_headings = []

    def _pieces(self, header: str, fixed: Sequence[str], line: str) -> list[str]:
        """`line` cut so that each piece fits a chunk after the header and `fixed`."""
        room = self.max_tokens - self._tokens(header, [*fixed, ""])
        if room < 1:
            raise ValueError(f"no room left after the context header: {header}")
        pieces = self.tokenizer.split(line, room)
        # Token counts are not additive at the seams, so check each piece as placed.
        while any(
            self._tokens(header, [*fixed, piece]) > self.max_tokens for piece in pieces
        ):
            room -= 1
            if room < 1:
                raise ValueError(f"cannot fit a piece of: {line[:80]}")
            pieces = self.tokenizer.split(line, room)
        return pieces

    def _pack(
        self,
        page: int,
        section: str,
        kind: ChunkKind,
        fixed: list[str],
        lines: list[str],
        source_table: str = "",
        preceding_text: tuple[str, ...] = (),
        row_indices: tuple[int, ...] = (),
    ) -> None:
        """`lines` into as few chunks as fit; every chunk starts with the `fixed` lines."""
        if row_indices and len(row_indices) != len(fixed) + len(lines):
            raise ValueError("native table row provenance does not match its rows")
        header = context_header(self.meta, section, page)
        if fixed and self._tokens(header, fixed) >= self.max_tokens:
            # Header rows that fill a chunk on their own are not repeated: they are rows.
            fixed, lines = [], [*fixed, *lines]
        fixed_rows = row_indices[: len(fixed)]
        line_rows = row_indices[len(fixed) :]
        current: list[str] = []
        current_rows: list[int] = []
        for offset, line in enumerate(lines):
            # A component model is its own authored property row. Isolate it so
            # its denial cannot force unrelated, independently proven rows to
            # carry its text. All original cells/columns are retained.
            isolated = kind == "table" and pack_model_row(line)
            if isolated and current:
                self._emit(
                    page,
                    section,
                    kind,
                    [*fixed, *current],
                    source_table,
                    preceding_text,
                    tuple([*fixed_rows, *current_rows]),
                )
                current, current_rows = [], []
            for piece in self._pieces(header, fixed, line):
                if (
                    current
                    and self._tokens(header, [*fixed, *current, piece])
                    > self.max_tokens
                ):
                    self._emit(
                        page,
                        section,
                        kind,
                        [*fixed, *current],
                        source_table,
                        preceding_text,
                        tuple([*fixed_rows, *current_rows]),
                    )
                    current, current_rows = [], []
                current.append(piece)
                if line_rows:
                    current_rows.append(line_rows[offset])
            if isolated:
                self._emit(
                    page,
                    section,
                    kind,
                    [*fixed, *current],
                    source_table,
                    preceding_text,
                    tuple([*fixed_rows, *current_rows]),
                )
                current, current_rows = [], []
        if current or fixed:
            self._emit(
                page,
                section,
                kind,
                [*fixed, *current],
                source_table,
                preceding_text,
                tuple([*fixed_rows, *current_rows]),
            )

    def _text(self, page: int, section: str, texts: list[str]) -> None:
        start = len(self.chunks)
        self._pack(page, section, "text", [], texts)
        self._preceding_text.extend(chunk.id for chunk in self.chunks[start:])

    def add_page(self, page: Page, section: str) -> str:
        """The chunks of one page; returns the section in force at its end."""
        texts: list[str] = []
        for block_index, block in enumerate(page.blocks):
            if block.source_picture != self._source_picture:
                if texts:
                    self._text(page.number, section, texts)
                    texts = []
                # Keep body and figure text separate. A non-table figure may
                # sit between two body fragments of a real table heading.
                if not self._source_picture:
                    self._body_preceding_text = self._preceding_text
                self._preceding_text = (
                    [] if block.source_picture else self._body_preceding_text
                )
                self._source_picture = block.source_picture
            if block.kind != "text" and texts:
                self._text(page.number, section, texts)
                texts = []
            if block.kind == "heading" and block.source_picture:
                # Keep the figure label as an isolated original text passage.
                # It can constrain that figure, but is not a document heading.
                self._text(page.number, section, [block.text])
            elif block.kind == "heading":
                section = block.text
                self._pending_headings.append(block.text)
                self._preceding_text = []
            elif block.kind == "text":
                # Keep the manufacturer's role sentence apart from following
                # diagrams or a different model's paragraphs. Recognition here
                # grants no permission; publication.py proves its full scope.
                if meter_references(block.text):
                    if texts:
                        self._text(page.number, section, texts)
                        texts = []
                    self._text(page.number, section, [block.text])
                else:
                    texts.append(block.text)
            else:
                if block.source_picture:
                    # An independent table interrupts any earlier body axis.
                    self._body_preceding_text = []
                header_rows, rows = table_lines(block)
                start = len(self.chunks)
                self._pack(
                    page.number,
                    section,
                    "table",
                    header_rows,
                    rows,
                    f"{page.source}:p{page.number}:"
                    + (block.source_id or f"block{block_index}"),
                    tuple(self._preceding_text),
                    block.row_indices or tuple(range(len(block.rows))),
                )
                if block.source_cells and len(self.chunks) > start:
                    self.chunks[start] = replace(
                        self.chunks[start], source_cells=block.source_cells
                    )
                # The next independent TableItem needs its own original header.
                self._preceding_text = []
        if texts:
            self._text(page.number, section, texts)
        return section


def chunk_document(
    meta: DocumentMeta,
    pages: Sequence[Page],
    tokenizer: Tokenizer,
    detect_lang: Callable[[str], str],
    max_tokens: int = MAX_TOKENS,
) -> list[Chunk]:
    """Every chunk of one document, in page order."""
    chunker = _Chunker(meta, tokenizer, detect_lang, max_tokens)
    section = ""
    for page in pages:
        section = chunker.add_page(page, section)
    return chunker.chunks
