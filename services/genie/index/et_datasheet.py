"""Recover independent ET inverter columns from GoodWe's original PDF text runs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pypdfium2.raw as raw

from linker_genie.table_projection import SourceCell, SourceSpan

EMEA_EN = "4534dd428973160226c57c7e14d364b6f6dbf30bfe1e9761f45e05917cbcedd0"
SOURCES = {
    EMEA_EN,
    "d4dea0be60dc736a139ead31cdc687a38c0f392859994e008d3ef3a5e1b1bcbe",
    "22c0b75575dc400a85bfc1fef0ae85dacbf112d86d5aa04ac1f60eab1a5e6d4f",
}


@dataclass(frozen=True)
class Run:
    text: str
    box: tuple[float, float, float, float]
    bold: bool

    def cell(self, row: int, col: int) -> SourceCell:
        return SourceCell(
            row_start=row,
            row_end=row + 1,
            col_start=col,
            col_end=col + 1,
            column_header=row == 0,
            row_header=False,
            row_section=row > 0 and self.bold,
            text=self.text,
            bbox=self.box,
            bbox_origin="TOPLEFT",
        )


def independent_cells(
    page: Any,
    sha: str,
    spans: Sequence[SourceSpan],
    table_box: tuple[float, float, float, float],
) -> list[SourceCell]:
    """Match full native PDF lines to the separate, horizontally aligned text objects."""
    tp = page.get_textpage()
    try:
        source = tp.get_text_range()
        if len(source) != tp.count_chars():
            return []
        lines = set(source.splitlines())
        header_match = re.fullmatch(
            r"(Technical Data|Technische Daten)(?: GW\d+K-ET-10(?:\*\d+)?){2,}",
            source.partition("\r\n")[0],
        )
        if header_match is None:
            return []
        heading = header_match[1]
        labels = list(re.finditer(r"GW\d+K-ET-10(?:\*\d+)?", header_match[0]))
        height = page.get_height()
        runs: list[Run] = []
        for obj in page.get_objects(filter=[raw.FPDF_PAGEOBJ_TEXT], textpage=tp):
            text = obj.extract().strip()
            left, bottom, right, top = obj.get_bounds()
            box = (left, height - top, right, height - bottom)
            if (
                text
                and table_box[0] <= left < right <= table_box[2]
                and box[1] < table_box[3]
            ):
                runs.append(
                    Run(text, box, obj.get_font().get_base_name().endswith("-Bold"))
                )
        headings = [run for run in runs if run.text == heading]
        if len(headings) != 1:
            return []
        caption = headings[0]
        cells = [caption.cell(0, 0)]
        centres = []
        for col, label in enumerate(labels, 1):
            model = label[0].split("*")[0]
            matched = [
                s
                for s in spans
                if s["text"] == model and s["char_start"] == label.start()
            ]
            if len(matched) != 1:
                return []
            span = matched[0].copy()
            # The original superscript shares the label's source range and stays
            # part of its identity. A region-limited model cannot resolve as an
            # unqualified Woo product.
            last = tp.get_charbox(label.end() - 1)
            a, b, c, d = span["bbox"]
            box = (
                min(a, last[0]),
                min(b, height - last[3]),
                max(c, last[2]),
                max(d, height - last[1]),
            )
            if not (caption.box[1] < box[3] and box[1] < caption.box[3] < table_box[1]):
                return []
            span["text"] = label[0]
            span["char_end"] = label.end()
            span["bbox"] = box
            cell = Run(label[0], box, True).cell(0, col)
            cell["model_spans"] = [span]
            cells.append(cell)
            centres.append((box[0] + box[2]) / 2)
        if centres != sorted(set(centres)):
            return []
        # The input, grid and backup sections each start with a bold run at
        # the technical-data caption's left edge. Only complete single-line
        # rows with a distinct object centred under every model are unambiguous.
        body = [
            r for r in runs if table_box[1] <= (r.box[1] + r.box[3]) / 2 <= table_box[3]
        ]
        fields = sorted(
            (r for r in body if abs(r.box[0] - caption.box[0]) < 1),
            key=lambda r: r.box[1],
        )
        section = ""
        for row, field in enumerate(fields, 1):
            if field.bold:
                section = field.text if field.text in lines else ""
                if section:
                    cells.append(field.cell(row, 0))
                continue
            # This EMEA English original prints its STS condition on the grid
            # heading. Neither AC subsection can establish the condition for
            # a grid or backup rating across the two EMEA editions.
            if not section or (sha == EMEA_EN and section.startswith("AC Output Data")):
                continue
            siblings = sorted(
                (
                    r
                    for r in body
                    if r is not field
                    and r.box[1] < field.box[3]
                    and field.box[1] < r.box[3]
                ),
                key=lambda r: r.box[0],
            )
            if len(siblings) != len(centres) or not all(
                value.box[0] <= centre <= value.box[2]
                for value, centre in zip(siblings, centres, strict=True)
            ):
                continue
            if " ".join(r.text for r in [field, *siblings]) not in lines:
                continue
            cells.extend(r.cell(row, col) for col, r in enumerate([field, *siblings]))
        return cells if any(c["row_start"] and c["col_start"] for c in cells) else []
    finally:
        tp.close()
