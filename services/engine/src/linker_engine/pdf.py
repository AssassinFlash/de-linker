"""The design report as an A4 PDF, with the installer's own logo when one is given.

Rendered from the same report model as the screen (`report.py`), so the PDF
uses the same wording. Bundled DejaVu Sans fonts cover European source titles
and engineering notation in the offline render.
"""

from __future__ import annotations

import base64
import binascii
import io
import math
import re
from datetime import UTC, datetime
from functools import cache
from html import escape
from pathlib import Path

from PIL import Image as PillowImage
from reportlab.graphics.shapes import Drawing, Line, Rect, String
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
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

from .models import (
    Report,
    ReportMonthlyChart,
    ReportRow,
    ReportSection,
    ReportSummaryCard,
)
from .report_logo import logo_dimensions
from .texts import t

# Print palette of the configurator's WindPress design system.
INK = colors.HexColor("#0c0f0f")
MUTED_HEX = "#5a6363"
MUTED = colors.HexColor(MUTED_HEX)
RULE = colors.HexColor("#e2e5e5")
ACCENT_HEX = "#084d46"
ACCENT = colors.HexColor(ACCENT_HEX)
LOGO_MAX_HEIGHT = 16 * mm
LOGO_MAX_WIDTH = 60 * mm
BRAND_MAX_HEIGHT = 9 * mm
BRAND_MAX_WIDTH = 34 * mm
# The brand mark the site itself uses, converted from
# plugins/linker-commerce/assets/linker-logo-wordmark.webp (ReportLab reads no WebP).
BRAND = Path(__file__).resolve().parents[2] / "data" / "brand" / "linker-wordmark.png"
_DATA_URL = re.compile(r"^data:image/(png|jpeg);base64,(?P<data>[A-Za-z0-9+/=\s]+)$")


class LogoError(ValueError):
    """The logo is not a PNG or JPEG data URL."""


@cache
def _fonts() -> None:
    folder = BRAND.parents[1] / "fonts"
    for name in ("DejaVuSans", "DejaVuSans-Bold"):
        pdfmetrics.registerFont(TTFont(name, str(folder / (name + ".ttf"))))


def _styles() -> dict[str, ParagraphStyle]:
    _fonts()
    base = ParagraphStyle(
        "base",
        fontName="DejaVuSans",
        fontSize=8.8,
        leading=12,
        textColor=INK,
        alignment=TA_LEFT,
    )
    heading = ParagraphStyle(
        "h2",
        parent=base,
        fontName="DejaVuSans-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
        textColor=ACCENT,
    )
    return {
        "base": base,
        "small": ParagraphStyle(
            "small", parent=base, fontSize=7.6, leading=10, textColor=MUTED
        ),
        "title": ParagraphStyle(
            "title", parent=base, fontName="DejaVuSans-Bold", fontSize=17, leading=21
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base, fontSize=10, leading=14, textColor=MUTED
        ),
        "h2": heading,
        "commercial_heading": ParagraphStyle(
            "commercial_heading", parent=heading, spaceBefore=5, spaceAfter=2
        ),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.2, leading=10.6),
        "label": ParagraphStyle(
            "label", parent=base, fontSize=8.2, leading=10.6, textColor=MUTED
        ),
        "head": ParagraphStyle(
            "head", parent=base, fontName="DejaVuSans-Bold", fontSize=8.2, leading=10.6
        ),
    }


def _escape(text: str) -> str:
    return escape(text, quote=True)


def _text(text: str) -> str:
    return _escape(text)


def _linked(text: str) -> str:
    # Font spans belong only to visible text, never to a link's URI attribute.
    parts = re.split(r"""(https://de-linker\.com/[^\s"'<>]+)""", text)
    return "".join(
        f'<link href="{_escape(part)}" color="{ACCENT_HEX}">{_text(part)}</link>'
        if index % 2
        else _text(part)
        for index, part in enumerate(parts)
    )


def _value(row: ReportRow, appendix: bool) -> str:
    """A row's value; a document is linked and its address printed for the paper copy."""
    if not row.href:
        if appendix and re.fullmatch(r"[0-9a-f]{64}", row.value):
            return f'<font name="Courier" size="7">{row.value}</font>'
        return _linked(row.value)
    href = _escape(row.href)
    label = f'<link href="{href}" color="{ACCENT_HEX}">{_text(row.value)}</link>'
    if appendix and row.value != row.href:
        label += f'<br/><font size="6.8" color="{MUTED_HEX}">{_text(row.href)}</font>'
    return label


def logo_image(data_url: str) -> Image:
    match = _DATA_URL.match(data_url.strip())
    if not match:
        raise LogoError("the logo must be a PNG or JPEG data URL")
    try:
        raw = base64.b64decode(match.group("data"), validate=False)
        with PillowImage.open(io.BytesIO(raw)) as image:
            width, height = logo_dimensions(image)
    except (
        binascii.Error,
        OSError,
        ValueError,
        PillowImage.DecompressionBombError,
    ) as error:
        raise LogoError("the logo cannot be read as an image") from error
    scale = min(LOGO_MAX_HEIGHT / height, LOGO_MAX_WIDTH / width)
    return Image(io.BytesIO(raw), width=width * scale, height=height * scale)


@cache
def _brand_bytes() -> bytes | None:
    return BRAND.read_bytes() if BRAND.is_file() else None


def brand_image() -> Image | None:
    """The Linker wordmark every report carries, not only one with an installer logo.

    The PDF is the tool's own document, so the brand belongs on it even when the
    customer uploads no logo. A missing asset leaves the report without a mark
    rather than failing the download. Each call builds its own flowable: a
    reportlab Image carries layout state and must not be shared between builds.
    """
    raw = _brand_bytes()
    if raw is None:
        return None
    width, height = ImageReader(io.BytesIO(raw)).getSize()
    scale = min(BRAND_MAX_HEIGHT / height, BRAND_MAX_WIDTH / width)
    return Image(io.BytesIO(raw), width=width * scale, height=height * scale)


class _ReportRows(Table):
    def split(self, width: float, height: float, /) -> list[Flowable]:
        # Move complete rows to the next page. Only a row that cannot fit an
        # empty frame needs to continue on a second page.
        self.splitInRow = int(self._frame._atTop)  # type: ignore[attr-defined]
        return super().split(width, height)


def _section(
    section: ReportSection, styles: dict[str, ParagraphStyle], width: float
) -> list[Flowable]:
    commercial = section.tier == "commercial"
    row_padding = 1.5 if commercial else 3
    style = styles["commercial_heading" if commercial else "h2"]
    parts: list[Flowable] = [Paragraph(_text(section.title), style)]
    # The shared report document and application present scope before data.
    # Keep assumptions beside the heading instead of pushing them after a
    # potentially multi-page table.
    for paragraph in section.paragraphs:
        parts += [Spacer(1, 3), Paragraph(_linked(paragraph), styles["base"])]
    if section.rows:
        rows = [
            [
                Paragraph(_text(row.label), styles["label"]),
                Paragraph(_value(row, section.tier == "appendix"), styles["cell"]),
            ]
            for row in section.rows
        ]
        # Private project entries can span a page. Keep normal rows intact,
        # allowing an oversized row's paragraphs to continue without truncation.
        table = _ReportRows(rows, colWidths=[width * 0.42, width * 0.58])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), row_padding),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), row_padding),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        parts.append(table)
    if section.table:
        header = [Paragraph(_text(c), styles["head"]) for c in section.table.columns]
        body = [
            [Paragraph(_text(cell), styles["cell"]) for cell in row]
            for row in section.table.rows
        ]
        weights = section.table.column_weights
        # The equipment and installation schedules share the same printed grid.
        if section.id in {"bom", "site-materials"} and len(header) == 4:
            weights = [1, 1.45, 1, 1.55]
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
        table = _ReportRows(
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
                    ("TOPPADDING", (0, 0), (-1, -1), row_padding),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), row_padding),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        parts.append(table)
    # Keep the summary and its figures together when they fit a page.
    # ReportLab can still split a section taller than an empty frame.
    if section.id in {
        "self-consumption-comparison",
        "grid-connection-evidence",
        "pv",
    } or (section.table and len(section.table.rows) == 1 and not section.rows):
        return [KeepTogether(parts)]
    # A heading stays with the first paragraph, including its leading spacer;
    # a spacer alone must not make a heading look safe at the page bottom.
    first_content = 3 if section.paragraphs else 2
    return [KeepTogether(parts[:first_content]), *parts[first_content:]]


def _cards(
    cards: list[ReportSummaryCard], styles: dict[str, ParagraphStyle], width: float
) -> Table:
    cells = [
        [Paragraph(_text(card.label), styles["label"]) for card in cards],
        [Paragraph(_text(card.value), styles["h2"]) for card in cards],
    ]
    if any(card.note for card in cards):
        cells.append(
            [Paragraph(_text(card.note or ""), styles["small"]) for card in cards]
        )
    table = Table(cells, colWidths=[width / len(cards)] * len(cards))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f6f5")),
                *(
                    ("LINEBEFORE", (i, 0), (i, -1), 3, colors.white)
                    for i in range(1, len(cards))
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
            ]
        )
    )
    return table


def _energy_chart(chart: ReportMonthlyChart, width: float, de: bool) -> Drawing:
    """Scale both energy series to the same zero-based axis."""
    ceiling = max([*chart.pv_kwh, *(chart.load_kwh or [])])
    step_base = 10 ** math.floor(math.log10(ceiling / 4))
    step = next(
        n * step_base for n in (1, 2, 2.5, 5, 10) if n * step_base >= ceiling / 4
    )
    ticks = math.ceil(ceiling / step)
    upper = ticks * step

    def fmt(value: float) -> str:
        return f"{value:g}".replace(".", ",") if de else f"{value:g}"

    labels = [fmt(i * step) for i in range(ticks + 1)]
    left = max(pdfmetrics.stringWidth(label, "DejaVuSans", 7) for label in labels) + 10
    height = 78
    cell = (width - left - 5) / 12
    drawing = Drawing(width, height + 45)
    series = [(chart.pv_kwh, ACCENT, "PV-Erzeugung" if de else "PV generation")]
    if chart.load_kwh is not None:
        series.append(
            (
                chart.load_kwh,
                colors.HexColor("#a5b6c3"),
                "Stromverbrauch" if de else "Electricity use",
            )
        )
    legend_x = left
    for _, color, name in series:
        marker = Rect(legend_x, height + 28, 8, 8)
        marker.fillColor = color
        marker.strokeWidth = 0
        drawing.add(marker)
        drawing.add(
            String(
                legend_x + 12,
                height + 28,
                name,
                fontName="DejaVuSans",
                fontSize=8,
                fillColor=INK,
            )
        )
        legend_x += pdfmetrics.stringWidth(name, "DejaVuSans", 8) + 30
    drawing.add(
        String(
            width - 5,
            height + 28,
            chart.unit,
            textAnchor="end",
            fontName="DejaVuSans",
            fontSize=8,
            fillColor=MUTED,
        )
    )
    for idx, label in enumerate(labels):
        y = 19 + height * idx / ticks
        drawing.add(Line(left, y, width - 5, y, strokeColor=RULE, strokeWidth=0.5))
        drawing.add(
            String(
                left - 5,
                y - 2.5,
                label,
                textAnchor="end",
                fontName="DejaVuSans",
                fontSize=7,
                fillColor=MUTED,
            )
        )
    for month, label in enumerate(chart.months):
        mid = left + (month + 0.5) * cell
        drawing.add(
            String(
                mid,
                6,
                label,
                textAnchor="middle",
                fontName="DejaVuSans",
                fontSize=7.5,
                fillColor=INK,
            )
        )
        bar = cell * 0.7 / len(series)
        for j, (values, color, _) in enumerate(series):
            marker = Rect(
                mid - cell * 0.35 + j * bar, 19, bar - 1, height * values[month] / upper
            )
            marker.fillColor = color
            marker.strokeWidth = 0
            drawing.add(marker)
    return drawing


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
        # The PDF is stored content-addressed, so identical report content must
        # produce identical bytes. reportlab otherwise stamps its own creation
        # time, which changes the hash of a report nothing changed in. The
        # report's own generated_at still carries when it was made.
        invariant=True,
        title=report.title,
        author="Linker Technology GmbH",
        subject=report.subtitle,
        lang=report.locale,
    )
    # The frame of SimpleDocTemplate keeps 6 pt of padding on either side.
    padding = 6
    width = document.width - 2 * padding
    generated_at = report.generated_at
    if "T" in generated_at:
        instant = datetime.fromisoformat(generated_at).astimezone(UTC)
        generated_at = instant.strftime(
            "%d.%m.%Y %H:%M UTC" if report.locale == "de" else "%Y-%m-%d %H:%M UTC"
        )
    project = next((s for s in report.sections if s.id == "project" and s.rows), None)
    site = next((s for s in report.sections if s.id == "site" and s.rows), None)
    title = project.rows[0].value if project else report.title
    location = (
        site.rows[0].value
        if site
        and site.rows[0].label
        in ("Location", "Standort", t("row.postcode", report.locale))
        else ""
    )
    language = "Deutsch" if report.locale == "de" else "English"
    heading: list[Flowable] = [
        Paragraph(_text(title), styles["title"]),
        Paragraph(_text(report.subtitle), styles["subtitle"]),
        Paragraph(
            _text(" · ".join(filter(None, (location, generated_at, language)))),
            styles["small"],
        ),
    ]
    brand = brand_image()
    installer = logo_image(logo) if logo else None
    story: list[Flowable] = []
    if brand or installer:
        marks = Table(
            [[brand or "", installer or ""]], colWidths=[width / 2, width / 2]
        )
        marks.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        if brand:
            brand.hAlign = "LEFT"
        if installer:
            installer.hAlign = "RIGHT"
        story.extend([marks, Spacer(1, 8)])
    story.extend(heading)
    story.append(Spacer(1, 7))
    if report.summary_cards:
        story.extend([_cards(report.summary_cards, styles, width), Spacer(1, 4)])
    if report.monthly_chart and any(report.monthly_chart.pv_kwh):
        chart = report.monthly_chart
        story.extend(
            [
                Paragraph(_text(chart.title), styles["h2"]),
                _energy_chart(chart, width, report.locale == "de"),
                Paragraph(_text(chart.source_note), styles["small"]),
                Spacer(1, 4),
            ]
        )
    appendix = []
    for section in report.sections:
        if section.tier == "appendix":
            appendix.append(section)
        else:
            story += _section(section, styles, width)
    if appendix:
        title = (
            "Technischer &amp; rechtlicher Anhang"
            if report.locale == "de"
            else "Technical &amp; Compliance Appendix"
        )
        story.extend([PageBreak(), Paragraph(title, styles["title"]), Spacer(1, 8)])
        for section in appendix:
            story += _section(section, styles, width)

    footer = t("pdf.footer", report.locale)
    credits = t("pdf.credits", report.locale) if credits is None else credits

    def page(canvas: object, doc: object) -> None:
        canvas.saveState()  # type: ignore[attr-defined]
        canvas.setFont("DejaVuSans", 7)  # type: ignore[attr-defined]
        canvas.setFillColor(MUTED)  # type: ignore[attr-defined]
        left, right = margin + padding, A4[0] - margin - padding
        canvas.drawString(left, 13 * mm, footer)  # type: ignore[attr-defined]
        canvas.drawRightString(right, 13 * mm, str(doc.page))  # type: ignore[attr-defined]
        canvas.drawString(left, 9.5 * mm, credits)  # type: ignore[attr-defined]
        canvas.restoreState()  # type: ignore[attr-defined]

    document.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()
