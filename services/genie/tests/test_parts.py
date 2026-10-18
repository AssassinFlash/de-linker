"""A customer's parts list: parsed, matched row by row, asked one by one (#251).

Seams: `parts.parse_text` / `parts.parse_table` / `parts.rows_of` (what a pasted
line, a CSV table and an Excel workbook become), `parts.find` (is this turn a
list, and does it continue one), `parts.build` (the row states, decided by the
product vocabulary), `parts._answer` (the customer's answer to one unclear row),
and `parts.answer` (the turn the service ships, with the single add-to-draft
action). The fixture vocabulary is the live snapshot of 2026-10-15 (conftest).
"""

from __future__ import annotations

import io
import zipfile
from typing import Literal

import pytest

from linker_genie import parts
from linker_genie.lexicon import Vocabulary
from linker_genie.schema import PartsBlock, TextBlock, TurnMessage


def _msg(content: str, role: Literal["user", "assistant"] = "user") -> TurnMessage:
    return TurnMessage(role=role, content=content)


def test_pasted_lines_keep_their_quantities() -> None:
    text = "\n".join(
        [
            "Item;Qty",
            "2x SAJ H2-10K-T3",
            "3 Stk. GoodWe GW10K-ETA-G20",
            "4 pcs SAJ B2-10.0-HV1",
            "- 1 × Chint DTSU666",
            "SAJ H2-15K-T3 x2",
            "SAJ H2-15K-T3 - 2",
            "1. 10 x Wechselrichter",
            "2) 5 kW inverter SAJ",
            "",
        ]
    )
    rows = parts.parse_text(text)
    assert [(row.text, row.quantity) for row in rows] == [
        ("SAJ H2-10K-T3", 2),
        ("GoodWe GW10K-ETA-G20", 3),
        ("SAJ B2-10.0-HV1", 4),
        ("Chint DTSU666", 1),
        ("SAJ H2-15K-T3", 2),
        ("SAJ H2-15K-T3", 2),
        ("Wechselrichter", 10),
        ("5 kW inverter SAJ", 1),
    ]


def test_a_csv_table_uses_its_quantity_column() -> None:
    rows = parts.parse_table(
        [
            ["Item", "Qty", "Brand"],
            ["H2-10K-T3", "2", "SAJ"],
            ["GW10K-ETA-G20", "3", "GoodWe"],
            ["", "", ""],
        ]
    )
    assert [(row.text, row.quantity) for row in rows] == [
        ("H2-10K-T3 SAJ", 2),
        ("GW10K-ETA-G20 GoodWe", 3),
    ]


def test_a_german_csv_without_header_takes_the_standalone_number() -> None:
    rows = parts.parse_table(
        [["5", "SAJ", "H2-10K-T3"], ["2 Stück", "Wechselrichter", "GoodWe"]]
    )
    assert [(row.text, row.quantity) for row in rows] == [
        ("SAJ H2-10K-T3", 5),
        ("Wechselrichter GoodWe", 2),
    ]


def test_csv_semicolons_quotes_and_cp1252_read() -> None:
    text = 'Menge;"Produkt";Preis\n2;"Wechselrichter SAJ H2-10K-T3";10,00\n'
    assert [
        (r.text, r.quantity) for r in parts.parse_table(parts.rows_of(text.encode()))
    ] == [("Wechselrichter SAJ H2-10K-T3", 2)]
    latin = "2;Zubehör SAJ\n".encode("cp1252")
    parsed = parts.parse_table(parts.rows_of(latin))
    assert [(r.text, r.quantity) for r in parsed] == [("Zubehör SAJ", 2)]


def _xlsx(rows: list[list[str]]) -> bytes:
    """A minimal Excel workbook, as Excel writes one (shared strings, one sheet)."""
    from xml.sax.saxutils import escape

    shared: list[str] = []
    sheet_rows = []
    for number, row in enumerate(rows, start=1):
        cells = []
        for index, value in enumerate(row):
            column = chr(ord("A") + index)
            shared.append(value)
            cells.append(f'<c r="{column}{number}" t="s"><v>{len(shared) - 1}</v></c>')
        sheet_rows.append(f'<row r="{number}">{"".join(cells)}</row>')
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Liste" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    strings = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{escape(value)}</t></si>" for value in shared)
        + "</sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        book.writestr("xl/workbook.xml", workbook)
        book.writestr("xl/_rels/workbook.xml.rels", rels)
        book.writestr("xl/sharedStrings.xml", strings)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def test_an_excel_workbook_reads_its_first_sheet() -> None:
    raw = _xlsx(
        [
            ["Produkt", "Menge"],
            ["SAJ H2-10K-T3", "2"],
            ["GoodWe GW10K-ETA-G20", "3"],
        ]
    )
    rows = parts.parse_table(
        parts.rows_of(
            raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    )
    assert [(row.text, row.quantity) for row in rows] == [
        ("SAJ H2-10K-T3", 2),
        ("GoodWe GW10K-ETA-G20", 3),
    ]


def test_the_row_count_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parts, "MAX_ROWS", 3)
    text = "\n".join(f"{n} x SAJ H2-10K-T3" for n in range(1, 8))
    rows = parts.parse_text(text)
    assert len(rows) == 3
    assert parts.rows_truncated(text, rows)


def test_a_prose_message_is_no_list(vocabulary: Vocabulary) -> None:
    assert not parts.looks_like_list(
        "Is the SAJ H2-10K-T3 better than the GoodWe GW10K-ETA-G20?", vocabulary
    )
    assert not parts.looks_like_list("SAJ H2-10K-T3", vocabulary)
    assert parts.looks_like_list("2 x SAJ H2-10K-T3", vocabulary)
    assert parts.looks_like_list(
        "Please add these to my solution draft:\nSAJ H2-10K-T3\nGoodWe GW10K-ETA-G20",
        vocabulary,
    )


LIST_EN = """\
Item | Qty
2x SAJ H2-10K-T3
1 x S.A.J. H2-12K-T3
3 Stk. GoodWe GW10K-ETA-G20
SAJ H2-15K-T3 - 2
1× SAJ H2-20K T3
4 x GoodWe GW5.1-BAT-D-G21
2 x SAJ B2-10.0-HV1
1 x EcoFlow EF BD-8-S2
2 x EcoFlow EF BD-5-S2
10 x GoodWe GM330
1 x Chint DTSU666
2 x Pylontech L260-OMNI
1 x GoodWe GW7K-HCA-20
3 x SAJ eSolar AIO3
1 x SAJ BC2-HV1
2 x SAJ BU2-5.0-HV1
2 x GoodWe HCA
4 x SAJ H2
2 x SMA Sunny Boy 5.0
1 x Fronius Symo 10
"""

LIST_DE = """\
Produkt;Menge
2x SAJ H2-10K-T3
1 x S.A.J. H2-12K-T3
3 Stück GoodWe GW10K-ETA-G20
2 Stk. SAJ H2-15K-T3
1× SAJ H2-20K T3
4 x GoodWe GW5.1-BAT-D-G21
2 x SAJ B2-10.0-HV1
1 x EcoFlow EF BD-8-S2
2 x EcoFlow EF BD-5-S2
10 x GoodWe GM330
1 x Chint DTSU666
2 x Pylontech L260-OMNI
1 x GoodWe GW7K-HCA-20
3 x SAJ eSolar AIO3
1 x SAJ BC2-HV1
2 x SAJ BU2-5.0-HV1
2 x GoodWe HCA
4 x SAJ H2
2 x SMA Sunny Boy 5.0
1 x Fronius Symo 10
"""

EXPECTED = [
    ("matched", 4107, 2),
    ("matched", 4108, 1),
    ("matched", 3556, 3),
    ("matched", 2063, 2),
    ("matched", 2064, 1),
    ("matched", 6521, 4),
    ("matched", 2067, 2),
    ("matched", 3582, 1),
    ("matched", 3581, 2),
    ("matched", 2394, 10),
    ("matched", 2281, 1),
    ("matched", 2003, 2),
    ("matched", 3586, 1),
    ("matched", 3573, 3),
    ("matched", 2092, 1),
    ("matched", 2090, 2),
    ("uncertain", None, 2),
    ("uncertain", None, 4),
    ("missing", None, 2),
    ("missing", None, 1),
]


@pytest.mark.parametrize("text", [LIST_EN, LIST_DE], ids=["en", "de"])
def test_a_mixed_list_matches_row_by_row(vocabulary: Vocabulary, text: str) -> None:
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    result = parts.build(source, [], vocabulary)
    assert [
        (row.line, row.status, row.product_id, row.quantity) for row in result.rows
    ] == [(number, *expected) for number, expected in enumerate(EXPECTED, start=1)]
    # The unclear family rows offer products; the brand-only row offers its brand.
    assert 4107 not in {option.product_id for option in result.rows[16].options}
    assert len(result.rows[17].options) == parts.MAX_OPTIONS
    assert all(
        option.product_id in vocabulary.series_members["saj-h2"]
        for option in result.rows[17].options
    )
    assert result.ask_line == 17
    # While the two unclear rows wait there is no write yet; once they are
    # answered, every confirmed row goes in one write, merged by product.
    assert result.add is None
    settled = parts.build(
        source,
        [
            _msg(text),
            _msg("Row 17: GW7K-HCA-20"),
            _msg("Row 18: H2-15K-T3"),
        ],
        vocabulary,
    )
    assert settled.ask_line is None and settled.add is not None
    # The two answers name products the list already had: row 17 is the same
    # GW7K-HCA-20 as row 13, row 18 the same H2-15K-T3 as row 4, so their
    # quantities add onto those lines (16 products, 18 rows).
    assert [(item.product_id, item.quantity) for item in settled.add.items] == [
        (4107, 2),
        (4108, 1),
        (3556, 3),
        (2063, 6),
        (2064, 1),
        (6521, 4),
        (2067, 2),
        (3582, 1),
        (3581, 2),
        (2394, 10),
        (2281, 1),
        (2003, 2),
        (3586, 3),
        (3573, 3),
        (2092, 1),
        (2090, 2),
    ]
    assert (settled.add.products, settled.add.rows) == (16, 18)


def test_two_rows_of_one_product_are_one_cart_line(vocabulary: Vocabulary) -> None:
    text = "2x SAJ H2-10K-T3\n3 x S.A.J. H2-10K-T3\n1 x SAJ H2-12K-T3"
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    result = parts.build(source, [], vocabulary)
    assert result.add is not None
    assert [(item.product_id, item.quantity) for item in result.add.items] == [
        (4107, 5),
        (4108, 1),
    ]
    assert (result.add.products, result.add.rows) == (2, 3)


def test_the_customer_answers_the_unclear_rows_one_by_one(
    vocabulary: Vocabulary,
) -> None:
    text = "4 x SAJ H2\n2 x GoodWe GW10K-ET\n2 x SMA Sunny Boy 5.0"
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    first = parts.build(source, [_msg(text)], vocabulary)
    assert first.ask_line == 1
    messages = [
        _msg(text),
        _msg("checked", "assistant"),
        _msg("Row 1: SAJ H2-15K-T3"),
    ]
    second = parts.build(source, messages, vocabulary)
    assert (second.rows[0].status, second.rows[0].product_id) == ("matched", 2063)
    assert second.ask_line == 2
    messages.append(_msg("skip"))
    third = parts.build(source, messages, vocabulary)
    assert third.rows[1].status == "skipped"
    assert third.ask_line is None
    assert third.add is not None
    assert [item.product_id for item in third.add.items] == [2063]


def test_an_answer_before_the_list_is_not_about_it(vocabulary: Vocabulary) -> None:
    text = "2 x SAJ H2"
    source = parts.Source("text", tuple(parts.parse_text(text)), since=1)
    messages = [
        _msg("SAJ H2-10K-T3"),
        _msg(text),
    ]
    result = parts.build(source, messages, vocabulary)
    assert result.rows[0].status == "uncertain"


def test_a_photographed_list_is_a_list_without_a_list_word(
    vocabulary: Vocabulary,
) -> None:
    """A photo of a handwritten list is the transcription; no list word needed."""
    from linker_genie.schema import AttachmentReading

    reading = AttachmentReading(
        id="att1",
        name="IMG_0001.jpg",
        kind="document",
        text="SAJ H2-10K-T3 2 Stk\nGoodWe GW10K-ETA-G20 3 Stk\nSAJ H2 4 Stk",
    )
    messages = [_msg("Attached: IMG_0001.jpg")]
    source = parts.find(messages, [reading], [], vocabulary)
    assert source is not None and source.kind == "photo"
    assert len(source.parsed) == 3
    result = parts.build(source, messages, vocabulary)
    assert [row.status for row in result.rows] == ["matched", "matched", "uncertain"]


def test_a_datasheet_pdf_is_not_taken_for_a_list(vocabulary: Vocabulary) -> None:
    from linker_genie.schema import AttachmentReading

    reading = AttachmentReading(
        id="att1",
        name="datasheet.pdf",
        kind="document",
        text="SAJ H2-10K-T3 2 Stk\nGoodWe GW10K-ETA-G20 3 Stk",
    )
    assert (
        parts.find([_msg("Attached: datasheet.pdf")], [reading], [], vocabulary) is None
    )


def _text(
    text: str, vocabulary: Vocabulary, locale: str = "en", truncated: bool = False
) -> tuple[str, PartsBlock]:
    source = parts.Source(
        "text", tuple(parts.parse_text(text)), since=0, truncated=truncated
    )
    result = parts.build(source, [_msg(text)], vocabulary)
    output, block = parts.answer(result, locale)
    first = output.blocks[0]
    assert isinstance(first, TextBlock)
    return first.text, block


def test_one_line_reads_as_one_line(vocabulary: Vocabulary) -> None:
    text, block = _text("2x SAJ H2-10K-T3", vocabulary)
    assert text == (
        "I checked your list: the line matches our products. "
        "You can add the confirmed product to your solution draft."
    )
    assert block.add is not None and block.add.products == 1
    german, _ = _text("2x SAJ H2-10K-T3", vocabulary, "de")
    assert german == (
        "Ich habe Ihre Liste geprüft: Die Zeile passt zu unseren Produkten. "
        "Sie können das bestätigte Produkt Ihrem Lösungsentwurf hinzufügen."
    )


def test_one_match_among_several_reads_as_one(vocabulary: Vocabulary) -> None:
    text, _ = _text("2x SAJ H2-10K-T3\n1 x SMA Sunny Boy 5.0", vocabulary)
    assert text == (
        "I checked your list: one of 2 lines matches our products. "
        "One line is not in our product range. "
        "You can add the confirmed product to your solution draft."
    )
    german, _ = _text("2x SAJ H2-10K-T3\n1 x SMA Sunny Boy 5.0", vocabulary, "de")
    assert german == (
        "Ich habe Ihre Liste geprüft: Eine von 2 Zeilen passt zu unseren Produkten. "
        "Eine Zeile ist nicht in unserem Sortiment. "
        "Sie können das bestätigte Produkt Ihrem Lösungsentwurf hinzufügen."
    )


def test_a_list_with_only_unclear_rows_asks(vocabulary: Vocabulary) -> None:
    text, block = _text("4 x SAJ H2\n2 x SMA Sunny Boy 5.0", vocabulary)
    assert text == (
        "One line needs your confirmation. One line is not in our product range."
    )
    assert block.add is None and block.ask_line == 1


def test_a_truncated_list_scopes_its_counts(vocabulary: Vocabulary) -> None:
    text, _ = _text("2x SAJ H2-10K-T3", vocabulary, truncated=True)
    assert text.startswith(
        "I checked the first part of your list: one matches our products."
    )
    german, _ = _text("2x SAJ H2-10K-T3", vocabulary, "de", truncated=True)
    assert german.startswith(
        "Ich habe den ersten Teil Ihrer Liste geprüft: Eine passt zu unseren Produkten."
    )


def test_no_matches_says_so_once(vocabulary: Vocabulary) -> None:
    text, _ = _text("1 x SMA Sunny Boy 5.0\n1 x Fronius Symo 10", vocabulary)
    assert text == "I could not match any line of your list to our products."


def test_a_sku_a_spaced_code_a_category_and_a_brand_match(
    vocabulary: Vocabulary,
) -> None:
    """The ticket's four words (#251): SKU, hyphen/spelling variant, category, brand."""
    text = (
        "1 x DLK-SAJ-H210KT3\n"
        "2 x h2 10k t3\n"
        "3 x Wechselrichter SAJ\n"
        "4 x inverter saj\n"
        "5 x SAJ battery systems\n"
    )
    result = parts.build(
        parts.Source("text", tuple(parts.parse_text(text)), 0), [], vocabulary
    )
    assert [(row.status, row.product_id) for row in result.rows[:2]] == [
        ("matched", 4107),
        ("matched", 4107),
    ]
    # Brand + category narrows to that brand's inverters, in both languages.
    for row in result.rows[2:4]:
        assert row.status == "uncertain"
        assert row.options
        assert all(
            vocabulary.device_class.get(option.product_id) == "inverters"
            and "saj" in vocabulary.brand_of.get(option.product_id, set())
            for option in row.options
        )
    # A battery word narrows the brand to its storage.
    assert result.rows[4].status == "uncertain"
    assert all(
        vocabulary.device_class.get(option.product_id)
        in ("home-storage", "battery-systems")
        for option in result.rows[4].options
    )


def test_a_datasheet_question_after_a_settled_list_goes_to_the_model(
    vocabulary: Vocabulary,
) -> None:
    text = "2x SAJ H2-10K-T3\n1 x GoodWe GW10K-ETA-G20"
    messages = [_msg(text), _msg("Attached: x"), _msg("H2-10K-T3 datasheet")]
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    assert parts.find(messages, [], [], vocabulary) is None
    # The service did not settle anything; the list itself is untouched.
    assert [row.status for row in parts.build(source, messages, vocabulary).rows] == [
        "matched",
        "matched",
    ]


def test_an_unrelated_short_message_does_not_settle_an_open_row(
    vocabulary: Vocabulary,
) -> None:
    text = "4 x SAJ H2\n1 x GoodWe GW10K-ETA-G20"
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    messages = [_msg(text), _msg("GoodWe GW10K-ETA-G20")]
    assert parts.find(messages, [], [], vocabulary) is None
    built = parts.build(source, messages, vocabulary)
    assert built.rows[0].status == "uncertain"


def test_a_family_model_outside_the_options_settles_the_open_row(
    vocabulary: Vocabulary,
) -> None:
    text = "2 x SAJ"
    source = parts.Source("text", tuple(parts.parse_text(text)), since=0)
    messages = [_msg(text), _msg("CHS2-50K-T6-X")]
    assert parts.find(messages, [], [], vocabulary) is not None
    built = parts.build(source, messages, vocabulary)
    assert (built.rows[0].status, built.rows[0].product_id) == ("matched", 1961)


def test_an_add_request_continues_a_settled_list(vocabulary: Vocabulary) -> None:
    text = "2x SAJ H2-10K-T3"
    messages = [_msg(text), _msg("Please add these to my solution draft")]
    source = parts.find(messages, [], [], vocabulary)
    assert source is not None and source.since == 0
    assert parts.build(source, messages, vocabulary).add is not None


def test_quote_alone_does_not_continue_a_settled_list(vocabulary: Vocabulary) -> None:
    text = "2x SAJ H2-10K-T3"
    messages = [_msg(text), _msg("Please quote these")]
    assert parts.find(messages, [], [], vocabulary) is None


def test_a_quantity_past_the_cart_ceiling_is_clamped() -> None:
    [row] = parts.parse_text("12000 x SAJ H2-10K-T3")
    assert row.quantity == parts.MAX_QUANTITY == 9999


def test_a_pasted_list_past_the_row_cap_is_truncated(
    vocabulary: Vocabulary,
) -> None:
    text = "\n".join("1 x SAJ H2-10K-T3" for _ in range(parts.MAX_ROWS + 5))
    source = parts.find([_msg(text)], [], [], vocabulary)
    assert source is not None and source.truncated
    output, block = parts.answer(parts.build(source, [_msg(text)], vocabulary), "en")
    first = output.blocks[0]
    assert isinstance(first, TextBlock)
    assert "first part of your list" in first.text
    assert block.truncated


def _book(sheet: bytes) -> bytes:
    """A workbook whose worksheet is `sheet` (for adversarial cases)."""
    files: dict[str, bytes] = {
        "xl/workbook.xml": (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            b'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            b'<sheets><sheet name="Liste" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" '
            b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            b'Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/worksheets/sheet1.xml": sheet,
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as book:
        for name, content in files.items():
            book.writestr(name, content)
    return out.getvalue()


def test_a_forged_cell_reference_is_refused() -> None:
    sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="ZZZZZZ1" t="inlineStr"><is><t>x</t></is></c>'
        "</row></sheetData></worksheet>"
    )
    with pytest.raises(ValueError):
        parts.rows_of(_book(sheet.encode()), parts.XLSX_TYPE)


def test_a_row_past_excels_limit_is_refused() -> None:
    sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1048577"><c r="A1" t="inlineStr"><is><t>x</t></is></c>'
        "</row></sheetData></worksheet>"
    )
    with pytest.raises(ValueError):
        parts.rows_of(_book(sheet.encode()), parts.XLSX_TYPE)


def test_an_entity_declaration_is_refused() -> None:
    sheet = (
        '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&lol2;</t></is></c>'
        "</row></sheetData></worksheet>"
    )
    with pytest.raises(ValueError, match="entity"):
        parts.rows_of(_book(sheet.encode()), parts.XLSX_TYPE)


def test_an_oversized_sheet_entry_is_refused() -> None:
    sheet = b"<worksheet>" + b" " * parts.MAX_XLSX_ENTRY
    with pytest.raises(ValueError, match="too large"):
        parts.rows_of(_book(sheet), parts.XLSX_TYPE)


def test_a_german_add_request_continues_a_settled_list(
    vocabulary: Vocabulary,
) -> None:
    text = "2x SAJ H2-10K-T3"
    messages = [_msg(text), _msg("Fügen Sie diese dem Lösungsentwurf hinzu")]
    assert parts.find(messages, [], [], vocabulary) is not None


def test_a_datasheet_photo_with_a_question_is_no_list(
    vocabulary: Vocabulary,
) -> None:
    from linker_genie.schema import AttachmentReading

    reading = AttachmentReading(
        id="att1",
        name="IMG_0002.jpg",
        kind="document",
        text="SAJ H2-10K-T3 2 Stk\nGoodWe GW10K-ETA-G20 3 Stk",
    )
    messages = [_msg("Attached: IMG_0002.jpg"), _msg("What is the max PV voltage?")]
    assert parts.find(messages, [reading], [], vocabulary) is None
