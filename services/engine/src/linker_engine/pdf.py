"""The design report as an A4 PDF, with the installer's own logo when one is given.

Rendered from the same report model as the screen (`report.py`), so the PDF
never words anything the screen does not. Bitstream Vera (bundled with
ReportLab, Bitstream Vera licence) carries every character the texts use,
German letters, the minus sign and the dashes included.
"""

from __future__ import annotations

import base64
import binascii
import io
import os
import re
from functools import cache

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

from .models import Report, ReportRow, ReportSection
from .texts import t

# The site's colour tokens, as the configurator's screen uses them
# (plugins/linker-tools/src/configurator/configurator.css): --proto-color-ink,
# --proto-color-muted, --proto-color-line and --proto-teal-800.
INK = colors.HexColor("#0c0f0f")
MUTED_HEX = "#5a6363"
MUTED = colors.HexColor(MUTED_HEX)
RULE = colors.HexColor("#e2e5e5")
ACCENT_HEX = "#084d46"
ACCENT = colors.HexColor(ACCENT_HEX)
LOGO_MAX_HEIGHT = 16 * mm
LOGO_MAX_WIDTH = 60 * mm
_DATA_URL = re.compile(r"^data:image/(png|jpeg);base64,(?P<data>[A-Za-z0-9+/=\s]+)$")


class LogoError(ValueError):
    """The logo is not a PNG or JPEG data URL."""


@cache
def _fonts() -> None:
    folder = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    pdfmetrics.registerFont(TTFont("Vera", os.path.join(folder, "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(folder, "VeraBd.ttf")))


def _styles() -> dict[str, ParagraphStyle]:
    _fonts()
    base = ParagraphStyle(
        "base",
        fontName="Vera",
        fontSize=8.8,
        leading=12,
        textColor=INK,
        alignment=TA_LEFT,
    )
    return {
        "base": base,
        "small": ParagraphStyle(
            "small", parent=base, fontSize=7.6, leading=10, textColor=MUTED
        ),
        "title": ParagraphStyle(
            "title", parent=base, fontName="Vera-Bold", fontSize=17, leading=21
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base, fontSize=10, leading=14, textColor=MUTED
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base,
            fontName="Vera-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            textColor=ACCENT,
        ),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.2, leading=10.6),
        "label": ParagraphStyle(
            "label", parent=base, fontSize=8.2, leading=10.6, textColor=MUTED
        ),
        "head": ParagraphStyle(
            "head", parent=base, fontName="Vera-Bold", fontSize=8.2, leading=10.6
        ),
    }


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _linked(text: str) -> str:
    escaped = _escape(text)
    return re.sub(
        r"(https://de-linker\.com/\S+)",
        rf'<link href="\1" color="{ACCENT_HEX}">\1</link>',
        escaped,
    )


def _value(row: ReportRow) -> str:
    """A row's value; a document is linked and its address printed for the paper copy."""
    if not row.href:
        return _linked(row.value)
    href = _escape(row.href)
    return (
        f'<link href="{href}" color="{ACCENT_HEX}">{_escape(row.value)}</link>'
        f'<br/><font size="6.8" color="{MUTED_HEX}">{href}</font>'
    )


def logo_image(data_url: str) -> Image:
    match = _DATA_URL.match(data_url.strip())
    if not match:
        raise LogoError("the logo must be a PNG or JPEG data URL")
    try:
        raw = base64.b64decode(match.group("data"), validate=False)
        reader = ImageReader(io.BytesIO(raw))
        width, height = reader.getSize()
    except (binascii.Error, OSError, ValueError) as error:
        raise LogoError("the logo cannot be read as an image") from error
    scale = min(LOGO_MAX_HEIGHT / height, LOGO_MAX_WIDTH / width)
    return Image(io.BytesIO(raw), width=width * scale, height=height * scale)


def _section(
    section: ReportSection, styles: dict[str, ParagraphStyle], width: float
) -> list[Flowable]:
    parts: list[Flowable] = [Paragraph(_escape(section.title), styles["h2"])]
    # The shared report document and application present scope before data.
    # Keep assumptions beside the heading instead of pushing them after a
    # potentially multi-page table.
    for paragraph in section.paragraphs:
        parts += [Spacer(1, 3), Paragraph(_linked(paragraph), styles["base"])]
    if section.rows:
        rows = [
            [
                Paragraph(_escape(row.label), styles["label"]),
                Paragraph(_value(row), styles["cell"]),
            ]
            for row in section.rows
        ]
        table = Table(rows, colWidths=[width * 0.42, width * 0.58])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        parts.append(table)
    if section.table:
        header = [Paragraph(_escape(c), styles["head"]) for c in section.table.columns]
        body = [
            [Paragraph(_escape(cell), styles["cell"]) for cell in row]
            for row in section.table.rows
        ]
        weights = section.table.column_weights
        # Normalize the scale first: individually finite weights can have an
        # overflowing sum, while their relative layout is still representable.
        scaled = [weight / max(weights) for weight in weights] if weights else []
        shares = (
            [weight / sum(scaled) for weight in scaled]
            if weights
            else [0.13, 0.45, 0.24, 0.18]
            if len(header) == 4
            else [0.13, 0.62, 0.25]
            if len(header) == 3
            else [1 / max(1, len(header))] * len(header)
        )
        table = Table(
            [header, *body],
            colWidths=[width * share for share in shares],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        parts.append(table)
    # A heading stays with the first paragraph, including its leading spacer;
    # a spacer alone must not make a heading look safe at the page bottom.
    first_content = 3 if section.paragraphs else 2
    return [KeepTogether(parts[:first_content]), *parts[first_content:]]


def render(
    report: Report, logo: str | None = None, *, credits: str | None = None
) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    margin = 18 * mm
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin + 6 * mm,
        title=report.title,
        author="Linker Technology GmbH",
        subject=report.subtitle,
        lang=report.locale,
    )
    # The frame of SimpleDocTemplate keeps 6 pt of padding on either side.
    padding = 6
    width = document.width - 2 * padding
    heading: list[Flowable] = [
        Paragraph(_escape(report.title), styles["title"]),
        Paragraph(_escape(report.subtitle), styles["subtitle"]),
        Paragraph(
            _escape(report.generated_at.replace("T", " ").replace("Z", " UTC")),
            styles["small"],
        ),
    ]
    if logo:
        top = Table(
            [[heading, logo_image(logo)]],
            colWidths=[width - LOGO_MAX_WIDTH, LOGO_MAX_WIDTH],
        )
        top.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story: list[Flowable] = [top]
    else:
        story = list(heading)
    story.append(Spacer(1, 6))
    for section in report.sections:
        story += _section(section, styles, width)

    footer = t("pdf.footer", report.locale)
    credits = t("pdf.credits", report.locale) if credits is None else credits

    def page(canvas: object, doc: object) -> None:
        canvas.saveState()  # type: ignore[attr-defined]
        canvas.setFont("Vera", 7)  # type: ignore[attr-defined]
        canvas.setFillColor(MUTED)  # type: ignore[attr-defined]
        left, right = margin + padding, A4[0] - margin - padding
        canvas.drawString(left, 13 * mm, footer)  # type: ignore[attr-defined]
        canvas.drawRightString(right, 13 * mm, str(doc.page))  # type: ignore[attr-defined]
        canvas.drawString(left, 9.5 * mm, credits)  # type: ignore[attr-defined]
        canvas.restoreState()  # type: ignore[attr-defined]

    document.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()
