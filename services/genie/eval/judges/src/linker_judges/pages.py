"""Table excerpts from our hosted datasheet PDFs, as a retrieval chunk would carry them.

`pdftotext -layout` keeps each table row on one line; the excerpt cuts every line at the
table's left edge (where the anchor label starts), so marketing text in a left-hand
column falls away, and joins the remaining columns with " | ".
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Single cells longer than this, left after the cut, are wrapped marketing text, not a
# section heading such as "DC Input" or "Battery Parameters".
MAX_HEADING_CHARS = 40


@dataclass(frozen=True)
class Excerpt:
    lines: tuple[str, ...]
    values: tuple[str, ...]
    """The target row's value cells, left to right."""

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def page_text(pdf: Path, page: int) -> list[str]:
    """One page of `pdf` in layout mode (poppler's pdftotext must be installed)."""
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def cells(line: str) -> list[str]:
    """Columns of a layout line: runs of two or more spaces separate them."""
    return [cell.strip() for cell in re.split(r" {2,}", line.strip()) if cell.strip()]


def _word_start(line: str, edge: int) -> int:
    """`edge`, moved left to the start of a word it would cut: row labels can start a
    character or two left of the header label."""
    while edge > 0 and line[edge - 1] != " ":
        edge -= 1
    return edge


def table_excerpt(
    raw: list[str], anchor: str, occurrence: int, above: int, row: str, after: int
) -> Excerpt:
    """Rows from the header (and `above` lines over it) to `after` lines past `row`.

    `anchor` is the header's first cell; its `occurrence`-th appearance sets both the
    first line and the left edge of the cut.
    """
    hits = [(i, line.find(anchor)) for i, line in enumerate(raw) if anchor in line]
    if len(hits) <= occurrence:
        raise ValueError(f"anchor {anchor!r} occurs {len(hits)} times")
    start, edge = hits[occurrence]
    kept: list[list[str]] = []
    target: int | None = None
    for number, line in enumerate(raw[start - above :]):
        parts = cells(line[_word_start(line, edge) :]) if len(line) > edge else []
        header = number <= above
        if not parts or (
            not header and len(parts) == 1 and len(parts[0]) > MAX_HEADING_CHARS
        ):
            continue
        kept.append(parts)
        if target is None and parts[0] == row:
            target = len(kept) - 1
        if target is not None and len(kept) - 1 >= target + after:
            break
    if target is None:
        raise ValueError(f"row {row!r} not found under {anchor!r}")
    return Excerpt(tuple(" | ".join(parts) for parts in kept), tuple(kept[target][1:]))
