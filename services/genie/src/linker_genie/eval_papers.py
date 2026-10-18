"""PDFs with a text layer, written by hand: no PDF generator is a dependency.

`text_pdf` lays strings out at points on A4 pages in Helvetica, as a datasheet's
cells are: what PDFium reads back is the page's text in its rectangles. The tests use
`datasheet`; the evaluation (`nameplates.py`) sends `price_list` and `delivery_terms`
as a customer would send a supplier's paper (review round 1 of PR #309, item 8).
Both are marked as evaluation documents on their face and name no real company.
"""

from __future__ import annotations


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(pages: list[list[tuple[float, float, str]]]) -> bytes:
    """A PDF whose pages carry `(x, y, text)` strings; y counts from the bottom."""
    objects: list[bytes] = []
    kids = []
    font = 3
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")  # the page tree, written below
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for cells in pages:
        stream = "".join(
            f"BT /F1 9 Tf {x:.1f} {y:.1f} Td ({_escape(text)}) Tj ET\n"
            for x, y, text in cells
        ).encode("cp1252")
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream"
        )
        content = len(objects)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (font, content)
        )
        kids.append(len(objects))
    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % kid for kid in kids),
        len(kids),
    )
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


def datasheet() -> bytes:
    """One datasheet page: a model header row and rows whose label names the unit."""
    rows = [
        ("MODEL", ["H2-10K-T3", "H2-12K-T3"]),
        ("Max. PV Array Power [Wp]@STC", ["20000", "24000"]),
        ("Max. DC Voltage [V]", ["1000"]),
        ("Max. DC Input Current [A]", ["40/40/40", "40/40"]),
        ("Rated Output Current [A]@230Vac", ["14.5", "17.4"]),
    ]
    cells: list[tuple[float, float, str]] = []
    y = 780.0
    for label, values in rows:
        cells.append((40, y, label))
        cells.extend((260 + 90 * n, y, value) for n, value in enumerate(values))
        y -= 14
    # Enough text that the page counts as a text page (attachments.TEXT_PAGE_CHARS).
    cells.extend(
        (40, 500 - 12 * n, f"Note {n}: values at 25 degrees ambient.") for n in range(8)
    )
    return text_pdf([cells])


def _page(title: str, rows: list[list[str]], notes: list[str]) -> bytes:
    cells: list[tuple[float, float, str]] = [(40, 800, title)]
    y = 770.0
    for row in rows:
        cells.extend((40 + 150 * n, y, text) for n, text in enumerate(row))
        y -= 16
    cells.extend((40, y - 20 - 14 * n, note) for n, note in enumerate(notes))
    return text_pdf([cells])


def price_list(locale: str) -> bytes:
    """A distributor's net price list, as a customer might forward one."""
    if locale == "de":
        return _page(
            "Beispiel-Solarhandel GmbH - Netto-Preisliste 2026 (Evaluationsdokument)",
            [
                ["Modell", "Beschreibung", "Nettopreis"],
                ["H2-10K-T3", "Hybrid-Wechselrichter 10 kW", "1.750,00 EUR"],
                ["GW10K-ET", "Hybrid-Wechselrichter 10 kW", "1.680,00 EUR"],
                ["B2-10.0-HV1", "Batterie 10 kWh", "3.190,00 EUR"],
            ],
            [
                "Alle Preise netto zzgl. MwSt., ab Lager.",
                "Gueltig bis 31.12.2026. Mindestbestellmenge 1 Stueck.",
            ],
        )
    return _page(
        "Example Solar Trading GmbH - net price list 2026 (evaluation document)",
        [
            ["Model", "Description", "Net price"],
            ["H2-10K-T3", "Hybrid inverter 10 kW", "1,750.00 EUR"],
            ["GW10K-ET", "Hybrid inverter 10 kW", "1,680.00 EUR"],
            ["B2-10.0-HV1", "Battery 10 kWh", "3,190.00 EUR"],
        ],
        [
            "All prices net, excluding VAT, ex warehouse.",
            "Valid until 31 December 2026. Minimum order quantity 1 piece.",
        ],
    )


def delivery_terms(locale: str) -> bytes:
    """A supplier's delivery terms, as a customer might forward them."""
    if locale == "de":
        return _page(
            "Beispiel-Solarhandel GmbH - Lieferbedingungen (Evaluationsdokument)",
            [
                ["Ziel", "Frachtkosten", "Lieferzeit"],
                ["Deutschland", "95,00 EUR je Palette", "5 Werktage"],
                ["Oesterreich", "140,00 EUR je Palette", "7 Werktage"],
                ["Polen", "160,00 EUR je Palette", "8 Werktage"],
            ],
            [
                "Lieferung frei Bordsteinkante. Abladen durch den Empfaenger.",
                "Ab 6 Paletten frachtfrei innerhalb Deutschlands.",
            ],
        )
    return _page(
        "Example Solar Trading GmbH - delivery terms (evaluation document)",
        [
            ["Destination", "Freight", "Lead time"],
            ["Germany", "EUR 95.00 per pallet", "5 working days"],
            ["Austria", "EUR 140.00 per pallet", "7 working days"],
            ["Poland", "EUR 160.00 per pallet", "8 working days"],
        ],
        [
            "Delivery to the kerbside. Unloading by the recipient.",
            "Free freight within Germany from 6 pallets.",
        ],
    )
