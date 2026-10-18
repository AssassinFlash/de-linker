"""A customer's parts list becomes products: pasted, uploaded or photographed (#251).

docs/specs/13-genie.md goal 2: "零件清单 → 产品：粘贴、上传表格或拍照的清单逐行匹配，
有疑问逐条问，一次填进 Lösungsentwurf". This module is the whole of that, before
the shell: it finds the list in the turn (a pasted message, a CSV or Excel file read
through the #236 attachment channel, or a photo's transcription), parses each row
deterministically, matches it against the product vocabulary of #233 (`lexicon.py`),
and marks every row:

- `matched`: the row names one of our products (brand, model, SKU or family);
- `uncertain`: the row names a brand, a family or a category but not one product,
  or names several: the customer answers the first such row, one at a time;
- `missing`: nothing in the row is one of our products (the customer's brand or
  model is not in our range);
- `skipped`: the customer set an uncertain row aside.

The list is never stored as a list: the source text stays where it already lives
(a pasted message in the thread, or the attachment reading the proxy keeps with the
conversation, #236), and the customer's answers are ordinary messages after it. Every
turn rebuilds the same rows from those two, so a reload loses nothing and no new
state is written.

The model does not take part: the answer and the card are code's (like a request for
a person, contact.py), so a row count, a product or a quantity can never be a model's
invention, and `parts` turns record provider "service".

Copy: docs/acceptance/2026-10-19/251/copy-review.md.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, replace
from itertools import islice
from typing import Any, Literal
from xml.etree import ElementTree

from linker_genie.lexicon import Match, Vocabulary
from linker_genie.schema import (
    AttachmentReading,
    PartsAdd,
    PartsBlock,
    PartsCandidate,
    PartsItem,
    PartsRow,
    PartsStatus,
    TextBlock,
    TurnMessage,
    TurnOutput,
)

# Rows read of one list. The largest list in the research is 61 items (Taobao's
# 61-item bill of materials in 10 minutes, docs/research/2026-10-17-ai-assistants/
# CN.md S32); 200 leaves three times that and keeps one turn's card sane.
MAX_ROWS = 200
# Products a row's confirmation offers: search-products shows six cards
# (route.SEARCH_LIMIT), and six labels fit the card at 390 px in two columns
# (docs/acceptance/2026-10-19/251).
MAX_OPTIONS = 6
# A quantity above this is a typo, not an order: the row still matches, and the
# number is clamped so one line cannot ask the draft for a million units. The
# Store API's own per-product ceiling is 9999 (`add_to_cart.maximum` of every
# product in the 2026-10-19 snapshot), so a larger line could not reach the draft
# anyway. Six digits are read, so "12000" is not mistaken for "1", and clamped
# here.
MAX_QUANTITY = 9_999
# The longest cell/line kept for display and matching: a product description in
# the research's lists is a model and a few words, not a paragraph; 300 characters
# keep a full German product name (the longest title in the 2026-10-15 snapshot is
# 95) with room for a brand and a note.
TEXT_CHARS = 300
# Rows a sheet's header is looked for in: the research's list exports (Home Depot,
# Lowe's, 京东 AI 清单选品, docs/research/2026-10-17-ai-assistants/) put the header in
# the first row; five leaves room for a title line or two.
HEADER_ROWS = 5
# The wire type of an Excel list (schema.UploadType); the same string as the
# proxy and the shell use (Attachments.php, prepare.ts).
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# The compressed workbook and the single sheet/shared-strings entries read at most:
# a list workbook is a few hundred kilobytes, and these ceilings stop a zip bomb
# before it is decompressed into memory. The sheet holds MAX_ROWS rows; 8 MiB is
# far above the largest real sheet that fits them.
MAX_XLSX_ENTRY = 8 * 1024 * 1024
# Excel's own sheet limits: 16,384 columns (XFD) and 1,048,576 rows (Microsoft
# support, "Excel specifications and limits"). A parts list uses a handful of
# columns; 1,024 leaves a hundredfold margin and stops a forged reference
# ("ZZZZZZ1") from allocating a sparse row.
MAX_XLSX_COLUMNS = 1_024
MAX_XLSX_ROWS = 1_048_576
# Cell references like "AB12": the column letters and the row number.
_CELL = re.compile(r"^([A-Z]+)(\d+)$")

# A list word, EN and DE: it lets a pasted list without quantities through (the
# rows themselves still have to name products). "Order"/"quote" are here because a
# customer pastes a list with "please quote these"; the row count decides the shape,
# never the word alone.
_LIST_WORDS = re.compile(
    r"\b(?:parts?[ -]list|list|bill of materials|st(?:ü|ue)ckliste|teileliste|"
    r"materialliste|liste|these|them|add|order|quote|angebot|anfrage|best(?:e|ä)llen|"
    r"hinzuf(?:ü|ue)gen|entwurf|l(?:ö|oe)sungsentwurf)\b",
    re.IGNORECASE,
)
# A noun that names a list, for a fresh photo/document: "here is my parts list".
# The add/quote/order words above only help a *pasted* list be recognised; they
# do not make a datasheet photo a list, and they do not continue an earlier list
# (see `_continues`).
_LIST_NOUNS = re.compile(
    r"\b(?:parts?[ -]list|list|bill of materials|st(?:ü|ue)ckliste|teileliste|"
    r"materialliste|liste)\b",
    re.IGNORECASE,
)
# A request to add the list to the draft, which continues an earlier list after
# all its rows are settled. It needs both a verb and a target: "quote these" is
# an inquiry, not an add.
_ADD_VERB = re.compile(
    r"\b(?:add|adds|adding|added|put|take|"
    r"hinzuf(?:ü|ue)gen|hinzugef(?:ü|ue)gt|f(?:ü|ue)gen|"
    r"(?:ü|ue)bernehmen|aufnehmen)\b",
    re.IGNORECASE,
)
_ADD_TARGET = re.compile(
    r"\b(?:draft|list|them|these|it|entwurf|liste|sie|diese|"
    r"l(?:ö|oe)sungsentwurf)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Parsing: a line, a table row, a CSV file, an Excel sheet → Parsed(text, quantity)

# Six digits: enough to read "12000" as a count (and clamp it to the cart's
# 9999), while a longer run is a model code or an id, not a quantity.
# The ways a customer writes a quantity, EN and DE:
#   "2x", "2 x", "2×", "2 pcs", "2 Stk.", "2 Stück", "qty 2", "menge: 2"
# and the same after the product ("SAJ H2-10K-T3 x2", "... - 2").
_QTY_UNIT = r"(?:x|×|\*|pcs?|pieces?|stk|st(?:ü|ue)ck|units?|qty|quantity|anzahl|menge)"
_LEAD_QTY = re.compile(
    rf"^(?P<qty>\d{{1,6}})\s*{_QTY_UNIT}\.?(?![A-Za-z0-9])\s*", re.IGNORECASE
)
_LEAD_NUMBER_QTY = re.compile(r"^(?P<qty>\d{1,6})\s+(?=[A-Za-zÄÖÜäöü])", re.IGNORECASE)
_TRAIL_QTY = re.compile(
    rf"\s*(?:(?:x|×|\*)\s*(?P<qty1>\d{{1,6}})|(?P<qty2>\d{{1,6}})\s*{_QTY_UNIT}|"
    # " - 2" with spaces around the dash: a model code ends in "-20" without
    # spaces ("GW7K-HCA-20") and is never a quantity.
    r"\s+[-–—]\s+(?P<qty3>\d{1,6}))\s*$",
    re.IGNORECASE,
)
_QTY_WORD = re.compile(
    r"\b(?:qty|quantity|anzahl|menge)\s*[:.]?\s*(?P<qty>\d{1,6})\b", re.IGNORECASE
)
# A row number before the text ("1.", "2)", "(3)"): a list's own numbering, not a
# quantity. It is removed before any quantity is read.
_NUMBERING = re.compile(r"^\s*\(?\d{1,3}[.)]\s+")
_BULLET = re.compile(r"^[\s\-–—*•·]+")
# A bare number followed by one of these is a rating, not a quantity ("5 kW").
_UNITS_HINT = re.compile(
    r"^\s*(?:kw|kwh|w|wh|v|a|mm|cm|m|kg|kva|hz|%|°|℃)\b", re.IGNORECASE
)

# What a column header says, EN and DE. A row whose cells are all header words is
# the table's heading, not a product.
_HEADER_QTY = frozenset(
    {
        "qty",
        "quantity",
        "menge",
        "anzahl",
        "stk",
        "stück",
        "stueck",
        "pcs",
        "pieces",
        "units",
        "count",
    }
)
_HEADER_TEXT = frozenset(
    {
        "item",
        "items",
        "no",
        "nr",
        "pos",
        "position",
        "product",
        "products",
        "produkt",
        "produkte",
        "model",
        "modell",
        "article",
        "artikel",
        "sku",
        "description",
        "beschreibung",
        "bezeichnung",
        "brand",
        "marke",
        "hersteller",
        "unit",
        "einheit",
        "price",
        "preis",
    }
)
_HEADER_PRICE = frozenset({"price", "preis", "eur", "euro", "€", "total", "summe"})


@dataclass(frozen=True)
class Parsed:
    """One row as the customer wrote it, before matching: the text and the count."""

    text: str
    quantity: int


def _key(cell: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]+", "", cell.strip().lower())


def _cells(line: str) -> list[str]:
    """A pasted line cut into cells when it carries a table separator."""
    for delimiter in ("\t", "|", ";"):
        if delimiter in line:
            cells = [cell.strip() for cell in line.split(delimiter)]
            if len([cell for cell in cells if cell]) >= 2:
                return cells
    return [line.strip()]


def _quantity(value: str) -> int | None:
    """The count a cell or a fragment states, None when it states none."""
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        number = int(value)
        return min(number, MAX_QUANTITY) if number > 0 else None
    found = _QTY_WORD.search(value)
    if found:
        number = int(found.group("qty"))
        return min(number, MAX_QUANTITY) if number > 0 else None
    stripped = _NUMBERING.sub("", value)
    stripped = _BULLET.sub("", stripped)
    found = _LEAD_QTY.match(stripped)
    if found:
        number = int(found.group("qty"))
        return min(number, MAX_QUANTITY) if number > 0 else None
    found = _TRAIL_QTY.search(stripped)
    if found:
        number = int(found.group("qty1") or found.group("qty2") or found.group("qty3"))
        return min(number, MAX_QUANTITY) if number > 0 else None
    found = _LEAD_NUMBER_QTY.match(stripped)
    if found and not _UNITS_HINT.match(stripped[found.end() - 1 :]):
        number = int(found.group("qty"))
        return min(number, MAX_QUANTITY) if number > 0 else None
    return None


def _without_quantity(value: str) -> str:
    """The text without the row numbering, bullet and quantity it led/trailed with."""
    text = _NUMBERING.sub("", value.strip())
    text = _BULLET.sub("", text)
    text = _LEAD_QTY.sub("", text, count=1)
    text = _QTY_WORD.sub("", text, count=1)
    text = _TRAIL_QTY.sub("", text, count=1)
    found = _LEAD_NUMBER_QTY.match(text)
    if found and not _UNITS_HINT.match(text[found.end() - 1 :]):
        text = text[found.end() :]
    return text.strip(" \t-–—:;,")


def _header(cells: list[str]) -> bool:
    """Whether a row is a table heading (product/qty/price words)."""
    keys = [_key(cell) for cell in cells if cell.strip()]
    if len(keys) < 2:
        return False
    return all(
        key in _HEADER_QTY | _HEADER_TEXT | _HEADER_PRICE for key in keys
    ) and any(key in _HEADER_QTY | _HEADER_TEXT for key in keys)


# A money cell: digits with separators and an optional currency, never a product
# ("10,00", "1.299 €"). Shared by the table shapes so the two filters cannot
# drift.
_MONEY = re.compile(r"[\d.,]+\s*(?:€|eur)?", re.IGNORECASE)


def _money(cell: str) -> bool:
    return bool(_MONEY.fullmatch(cell.strip()))


def _parsed(text: str, quantity: int) -> Parsed | None:
    text = text.strip(" \t-–—:;,")
    if not text or not any(character.isalpha() for character in text):
        return None
    return Parsed(text[:TEXT_CHARS], min(max(quantity, 1), MAX_QUANTITY))


def _from_cells(cells: list[str]) -> Parsed | None:
    """A table row: the quantity cell is the count, the other cells the product."""
    kept = [cell.strip() for cell in cells]
    if _header(kept):
        return None
    quantities: list[int] = []
    texts: list[str] = []
    qty_at: set[int] = set()
    for index, cell in enumerate(kept):
        if not cell:
            continue
        number = _quantity(cell)
        if number is not None and _looks_like_quantity_cell(cell):
            quantities.append(number)
            qty_at.add(index)
    for index, cell in enumerate(kept):
        if not cell or index in qty_at:
            continue
        if _key(cell) in _HEADER_PRICE or _money(cell):
            continue
        texts.append(cell)
    quantity = quantities[0] if quantities else 1
    return _parsed(" ".join(texts), quantity)


def _looks_like_quantity_cell(cell: str) -> bool:
    """A cell that is a count, not a model or a rating: "2", "2 Stück", "qty 2"."""
    if cell.strip().isdigit():
        return True
    return bool(
        re.fullmatch(rf"\s*\d{{1,6}}\s*{_QTY_UNIT}\.?\s*", cell, re.IGNORECASE)
        or re.fullmatch(
            r"\s*(?:qty|quantity|anzahl|menge)\s*[:.]?\s*\d{1,6}\s*",
            cell,
            re.IGNORECASE,
        )
    )


def parse_text(text: str) -> list[Parsed]:
    """A pasted list: one row per non-empty line, a delimiter line as a table row."""
    rows: list[Parsed] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cells = _cells(line)
        if len(cells) > 1:
            parsed = _from_cells(cells)
        else:
            quantity = _quantity(line) or 1
            parsed = _parsed(_without_quantity(line), quantity)
        if parsed is not None:
            rows.append(parsed)
        if len(rows) >= MAX_ROWS:
            break
    return rows


def rows_of(
    data: bytes, kind: str = "text/csv", limit: int = MAX_ROWS
) -> list[list[str]]:
    """The rows of a CSV file or an Excel workbook, header row included.

    CSV: UTF-8 (a BOM is dropped), else Windows-1252 — the encoding Excel writes
    a German CSV in when "Unicode" is not chosen. The delimiter is the one that
    occurs most often among comma, semicolon and tab, so a German Excel export
    (`;`) reads like an English one (`,`). Excel: the first worksheet, shared
    strings and inline strings; the file is a zip and is read with a size ceiling
    per entry (a workbook that decompresses to more is refused).
    """
    if kind == XLSX_TYPE:
        return _xlsx_rows(data, limit)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    sample = text[:8192]
    delimiter = max(",;\t", key=sample.count)
    if sample.count(delimiter) == 0:
        delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        return list(islice(reader, limit))
    except csv.Error as error:
        raise ValueError(f"unreadable csv: {error}") from error


def _xlsx_rows(data: bytes, limit: int) -> list[list[str]]:
    """The first worksheet of an .xlsx workbook as cell strings (stdlib only)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as book:
            names = set(book.namelist())
            if "xl/workbook.xml" not in names:
                raise ValueError("no workbook")
            target = _first_sheet(book)
            strings = _shared_strings(book) if "xl/sharedStrings.xml" in names else []
            if target not in names:
                raise ValueError("no first sheet")
            return _sheet(_read(book, target), strings, limit)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise ValueError(f"unreadable workbook: {error}") from error


_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _read(book: zipfile.ZipFile, name: str) -> bytes:
    """One zip entry, at most MAX_XLSX_ENTRY bytes read, not only stat'ed.

    `ZipInfo.file_size` is metadata from the archive; reading through the stream
    with a ceiling holds even if a crafted archive lies about it (a zip bomb of a
    few kilobytes expanding to gigabytes).
    """
    info = book.getinfo(name)
    if info.file_size > MAX_XLSX_ENTRY:
        raise ValueError(f"entry {name} is too large")
    with book.open(name) as stream:
        data = stream.read(MAX_XLSX_ENTRY + 1)
    if len(data) > MAX_XLSX_ENTRY:
        raise ValueError(f"entry {name} is too large")
    return data


def _xml(data: bytes) -> ElementTree.Element:
    """Parse a workbook part, refusing a document type or entity declaration.

    Excel writes neither; a `<!DOCTYPE`/`<!ENTITY` is a crafted document (the
    "billion laughs" expansion), not a workbook, and ElementTree's own parser
    expands it. Refusing the declaration keeps the parser on plain XML.
    """
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("a workbook part declares an entity")
    return ElementTree.fromstring(data)


def _first_sheet(book: zipfile.ZipFile) -> str:
    """The path of the first sheet, through the workbook's relationships."""
    workbook = _xml(_read(book, "xl/workbook.xml"))
    sheet = workbook.find("m:sheets/m:sheet", _NS)
    if sheet is None:
        raise ValueError("no sheet")
    rel_id = sheet.get(f"{{{_NS['r']}}}id")
    rels = _xml(_read(book, "xl/_rels/workbook.xml.rels"))
    for relationship in rels.findall("p:Relationship", _NS):
        if relationship.get("Id") == rel_id:
            target = relationship.get("Target") or ""
            return target.lstrip("/") if target.startswith("/") else "xl/" + target
    raise ValueError("no sheet relationship")


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    root = _xml(_read(book, "xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("m:si", _NS):
        values.append(
            "".join(node.text or "" for node in item.iter(f"{{{_NS['m']}}}t"))
        )
    return values


def _column(reference: str) -> int:
    """A cell's zero-based column, bounded by Excel's (and our) sheet limits.

    A forged reference ("ZZZZZZ1") would otherwise allocate a sparse row of
    millions of cells; more than three letters cannot be a valid reference
    (XFD is the last column).
    """
    letters = _CELL.match(reference)
    if letters is None or len(letters.group(1)) > 3:
        raise ValueError(f"bad cell reference {reference}")
    row = int(letters.group(2))
    if not 1 <= row <= MAX_XLSX_ROWS:
        raise ValueError(f"row out of range {reference}")
    value = 0
    for character in letters.group(1):
        value = value * 26 + (ord(character) - ord("A") + 1)
    index = value - 1
    if not 0 <= index < MAX_XLSX_COLUMNS:
        raise ValueError(f"column out of range {reference}")
    return index


def _sheet(data: bytes, strings: list[str], limit: int = MAX_ROWS) -> list[list[str]]:
    root = _xml(data)
    rows: list[list[str]] = []
    for row in root.findall("m:sheetData/m:row", _NS):
        row_number = row.get("r")
        if row_number is not None and (
            not row_number.isdigit() or not 1 <= int(row_number) <= MAX_XLSX_ROWS
        ):
            raise ValueError(f"row out of range {row_number}")
        cells: dict[int, str] = {}
        found = row.findall("m:c", _NS)
        if len(found) > MAX_XLSX_COLUMNS:
            raise ValueError("too many cells in one row")
        for position, cell in enumerate(found):
            reference = cell.get("r")
            index = _column(reference) if reference else position
            if not 0 <= index < MAX_XLSX_COLUMNS:
                raise ValueError("cell column out of range")
            kind = cell.get("t")
            value = cell.find("m:v", _NS)
            if kind == "inlineStr":
                inline = cell.find("m:is", _NS)
                text = (
                    "".join(node.text or "" for node in inline.iter(f"{{{_NS['m']}}}t"))
                    if inline is not None
                    else ""
                )
            elif value is None:
                text = ""
            elif kind == "s":
                shared = int(value.text or "0")
                text = strings[shared] if 0 <= shared < len(strings) else ""
            else:
                text = value.text or ""
            cells[index] = text
        if cells:
            rows.append([cells.get(index, "") for index in range(max(cells) + 1)])
        if len(rows) >= limit:
            break
    return rows


def parse_table(rows: list[list[str]]) -> list[Parsed]:
    """A table (CSV or Excel rows): the header's quantity column, else the number."""
    header_at: int | None = None
    qty_column: int | None = None
    for index, row in enumerate(rows[:HEADER_ROWS]):
        for column, cell in enumerate(row):
            if _key(cell) in _HEADER_QTY:
                header_at, qty_column = index, column
                break
        if qty_column is not None:
            break
    parsed: list[Parsed] = []
    for index, row in enumerate(rows):
        if header_at is not None and index == header_at:
            continue
        if qty_column is not None:
            quantity = 1
            if qty_column < len(row):
                quantity = _quantity(row[qty_column]) or 1
            texts = [
                cell
                for column, cell in enumerate(row)
                if column != qty_column
                and cell.strip()
                and _key(cell) not in _HEADER_PRICE
                and not _money(cell)
            ]
            item = _parsed(" ".join(texts), quantity)
        else:
            item = _from_cells(row)
        if item is not None:
            parsed.append(item)
        if len(parsed) >= MAX_ROWS:
            break
    return parsed


def rows_truncated(source: str | list[list[str]], rows: list[Parsed]) -> bool:
    """Whether the source held more rows than MAX_ROWS (the card says so)."""
    count = (
        len(source)
        if isinstance(source, list)
        else len([line for line in source.splitlines() if line.strip()])
    )
    return count > MAX_ROWS and len(rows) >= MAX_ROWS


# ---------------------------------------------------------------------------
# The list in a turn: where it came from and what its rows are

SourceKind = Literal["text", "table", "photo"]


@dataclass(frozen=True)
class Source:
    """The list a turn works on: its rows, where they came from, and since when."""

    kind: SourceKind
    parsed: tuple[Parsed, ...]
    # The user-message index the list was pasted at (text), or the index of the
    # message that carried the file; answers before it are not about this list.
    since: int
    reading_id: str | None = None
    truncated: bool = False


def find(
    messages: list[TurnMessage],
    fresh: list[AttachmentReading],
    readings: list[AttachmentReading],
    vocabulary: Vocabulary | None,
) -> Source | None:
    """The list this turn is working on, None when the turn is no list turn.

    A CSV or Excel reading of this turn is a list by itself (its file was picked
    as one). A photo or PDF is read as a list when the customer's message names a
    list or the transcription parses as one. A pasted list in the latest message
    wins over an earlier file when both exist.

    An earlier list is continued only on a confirmation (`Row N: …`, a short
    model that fits the open row) or a "skip"/"add to the draft" request; after
    the list is settled a datasheet or model question goes to the model, and an
    unrelated short message does not settle an open row.
    """
    if vocabulary is None:
        # Without the product words a row cannot be called ours; the turn log
        # names the reason (understand.py) and the list is left to the model.
        return None
    latest = messages[-1].content if messages else ""
    list_noun = bool(_LIST_NOUNS.search(latest))
    candidates: list[Source] = []
    for reading in fresh:
        if reading.failed:
            continue
        if reading.kind == "list":
            rows = parse_table(rows_of_reading(reading))
            since = _carried_at(messages, reading)
            candidates.append(
                Source("table", tuple(rows), since, reading.id, reading.truncated)
            )
        elif reading.kind in ("document", "photo") and (
            list_noun or ("?" not in latest and _photo_list(reading, vocabulary))
        ):
            rows = parse_text(reading.text)
            if len(rows) >= 2:
                since = _carried_at(messages, reading)
                candidates.append(Source("photo", tuple(rows), since, reading.id))
    if not candidates:
        for reading in reversed(readings):
            if reading.failed or reading.kind != "list":
                continue
            rows = parse_table(rows_of_reading(reading))
            if rows:
                source = Source(
                    "table",
                    tuple(rows),
                    _carried_at(messages, reading),
                    reading.id,
                    reading.truncated,
                )
                if _continues(source, messages, vocabulary):
                    candidates.append(source)
            break
    if candidates:
        return candidates[-1]
    if not messages or not messages[-1].role == "user":
        return None
    if looks_like_list(latest, vocabulary):
        parsed = parse_text(latest)
        return Source(
            "text",
            tuple(parsed),
            len(messages) - 1,
            truncated=rows_truncated(latest, parsed),
        )
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role != "user" or not looks_like_list(
            messages[index].content, vocabulary
        ):
            continue
        parsed = parse_text(messages[index].content)
        source = Source(
            "text",
            tuple(parsed),
            index,
            truncated=rows_truncated(messages[index].content, parsed),
        )
        return source if _continues(source, messages, vocabulary) else None
    return None


def _continues(
    source: Source, messages: list[TurnMessage], vocabulary: Vocabulary
) -> bool:
    """Whether the latest message continues this earlier list (module docstring)."""
    latest = messages[-1].content if messages else ""
    if not latest.strip():
        return False
    if _row_number(latest) is not None or skip(latest):
        return True
    if _add_request(latest):
        return True
    ids = _model_ids(latest, vocabulary)
    if len(ids) != 1 or len(latest.split()) > 8 or "?" in latest:
        return False
    # A model name settles the open row only if it fits it: an unrelated short
    # message between chip answers is a normal turn.
    before = build(source, list(messages[:-1]), vocabulary)
    row = next((row for row in before.rows if row.status == "uncertain"), None)
    return row is not None and _fits(row, next(iter(ids)), vocabulary)


def _add_request(text: str) -> bool:
    return bool(_ADD_VERB.search(text) and _ADD_TARGET.search(text))


def _model_ids(text: str, vocabulary: Vocabulary) -> set[int]:
    return {
        product_id
        for match in vocabulary.match(text)
        if match.kind == "model"
        for product_id in match.product_ids
    }


def _fits(row: Row, product_id: int, vocabulary: Vocabulary) -> bool:
    """Whether a typed model is an answer to this row: an option, or its family."""
    if any(option.product_id == product_id for option in row.options):
        return True
    series = {match.value for match in row.matches if match.kind == "series"}
    if series and vocabulary.series_of.get(product_id, set()) & series:
        return True
    brands = {match.value for match in row.matches if match.kind == "brand"}
    if brands and vocabulary.brand_of.get(product_id, set()) & brands:
        return True
    devices = {match.value for match in row.matches if match.kind == "category"}
    return bool(devices and vocabulary.device_class.get(product_id) in devices)


def _photo_list(reading: AttachmentReading, vocabulary: Vocabulary) -> bool:
    """A photo whose transcription is a list: two or more rows, each a product.

    A photo opened through the card's list suggestion may arrive with no text
    ("Attached: IMG_0001.jpg"): the transcription is the only clue. A datasheet
    PDF is excluded by its name (a photo is re-encoded to .jpg, #236), so a
    document's product table is not taken for a customer's list.
    """
    if reading.name.lower().endswith(".pdf"):
        return False
    rows = parse_text(reading.text)
    return (
        len(rows) >= 2
        and sum(1 for row in rows if _product_words(row.text, vocabulary)) >= 2
    )


def rows_of_reading(reading: AttachmentReading) -> list[list[str]]:
    """A CSV/Excel reading's table: its text is tab-separated rows (attachments.py)."""
    rows: list[list[str]] = []
    for line in reading.text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            continue
        rows.append(line.split("\t"))
    return rows


def _carried_at(messages: list[TurnMessage], reading: AttachmentReading) -> int:
    """The index of the message that carried a file ("Attached: <name>"), else 0."""
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "user" and reading.name in messages[index].content:
            return index
    return 0


def looks_like_list(text: str, vocabulary: Vocabulary) -> bool:
    """Whether a pasted message is a parts list, not a question about products.

    Two product-bearing lines (or one line that states a quantity and names a
    product) make a list; a question with two models on one line does not. A list
    word lets rows without quantities through, but the rows still have to name
    products.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    product_lines = sum(1 for line in lines if _product_words(line, vocabulary))
    quantities = sum(1 for line in lines if _quantity(line) is not None)
    if len(lines) >= 2 and product_lines >= 2:
        return quantities >= 1 or bool(_LIST_WORDS.search(text))
    if len(lines) == 1 and product_lines == 1 and quantities == 1:
        return True
    return False


def _product_words(line: str, vocabulary: Vocabulary) -> bool:
    return any(
        match.kind in ("brand", "series", "model", "category")
        for match in vocabulary.match(line)
    )


# ---------------------------------------------------------------------------
# Matching: a row's words against the product vocabulary (#233), the same rules
# every Genie turn uses


@dataclass(frozen=True)
class Row:
    """One list row and what code decided about it."""

    line: int
    text: str
    quantity: int
    status: PartsStatus
    product_id: int | None = None
    label: str | None = None
    options: tuple[PartsCandidate, ...] = ()
    matches: tuple[Match, ...] = ()


@dataclass(frozen=True)
class PartsList:
    """A parsed and matched list: its rows and the one cart write they allow."""

    rows: tuple[Row, ...]
    truncated: bool = False

    @property
    def ask_line(self) -> int | None:
        return next((row.line for row in self.rows if row.status == "uncertain"), None)

    @property
    def add(self) -> PartsAdd | None:
        """The confirmed rows as one WooCommerce write, merged by product.

        While a row still needs the customer's answer there is no add: the list
        is settled first ("有疑问的行逐条问；确认后一次加入"), so one click never
        writes a half-answered list.
        """
        if any(row.status == "uncertain" for row in self.rows):
            return None
        items: dict[int, int] = {}
        rows = 0
        for row in self.rows:
            if row.status != "matched" or row.product_id is None:
                continue
            items[row.product_id] = items.get(row.product_id, 0) + row.quantity
            rows += 1
        if not items:
            return None
        return PartsAdd(
            items=[
                PartsItem(product_id=product_id, quantity=quantity)
                for product_id, quantity in items.items()
            ],
            products=len(items),
            rows=rows,
        )


def build(
    source: Source, messages: list[TurnMessage], vocabulary: Vocabulary
) -> PartsList:
    """The list's rows with the customer's answers applied (module docstring)."""
    rows = [
        _row(number, parsed, vocabulary)
        for number, parsed in enumerate(source.parsed, start=1)
    ]
    for message in messages[source.since + 1 :]:
        if message.role != "user":
            continue
        rows = _answer(rows, message.content, vocabulary)
    return PartsList(tuple(rows), source.truncated)


def _row(number: int, parsed: Parsed, vocabulary: Vocabulary) -> Row:
    matches = tuple(vocabulary.match(parsed.text))
    models = [match for match in matches if match.kind == "model"]
    ids = sorted({pid for match in models for pid in match.product_ids})
    if len(ids) == 1:
        return _matched(number, parsed, ids[0], vocabulary, matches)
    if len(ids) > 1:
        return _uncertain(number, parsed, set(ids), vocabulary, matches)
    brands = [match for match in matches if match.kind == "brand"]
    series = [match for match in matches if match.kind == "series"]
    categories = [match for match in matches if match.kind == "category"]
    candidates: set[int] = set()
    if series:
        for match in series:
            candidates |= vocabulary.series_members.get(match.value, set())
        if brands:
            slugs = {match.value for match in brands}
            filtered = {
                pid for pid in candidates if vocabulary.brand_of.get(pid, set()) & slugs
            }
            # A brand that does not belong to the family is more likely a typo in
            # the brand than a reason to drop the family: the family stays.
            candidates = filtered or candidates
    elif brands:
        for match in brands:
            candidates |= vocabulary.brand_members.get(match.value, set())
    if categories and not series:
        # A category word narrows a brand ("SAJ inverter") or stands alone.
        devices = {
            pid
            for match in categories
            for pid, device in vocabulary.device_class.items()
            if device == match.value
        }
        candidates = (candidates & devices) or candidates or devices
    if len(candidates) == 1:
        return _matched(number, parsed, candidates.pop(), vocabulary, matches)
    if candidates:
        return _uncertain(number, parsed, candidates, vocabulary, matches)
    return Row(number, parsed.text, parsed.quantity, "missing", None, None, (), matches)


def _matched(
    number: int,
    parsed: Parsed,
    product_id: int,
    vocabulary: Vocabulary,
    matches: tuple[Match, ...],
) -> Row:
    return Row(
        number,
        parsed.text,
        parsed.quantity,
        "matched",
        product_id,
        vocabulary.labels.get(product_id, str(product_id)),
        (),
        matches,
    )


def _uncertain(
    number: int,
    parsed: Parsed,
    candidates: set[int],
    vocabulary: Vocabulary,
    matches: tuple[Match, ...],
) -> Row:
    ordered = sorted(candidates, key=lambda pid: (vocabulary.labels.get(pid, ""), pid))
    return Row(
        number,
        parsed.text,
        parsed.quantity,
        "uncertain",
        None,
        None,
        tuple(_candidate(pid, vocabulary) for pid in ordered[:MAX_OPTIONS]),
        matches,
    )


def _candidate(product_id: int, vocabulary: Vocabulary) -> PartsCandidate:
    return PartsCandidate(
        product_id=product_id,
        label=vocabulary.labels.get(product_id, str(product_id)),
        name=vocabulary.names.get(product_id, ""),
    )


def _answer(rows: list[Row], text: str, vocabulary: Vocabulary) -> list[Row]:
    """The customer's message applied to the first open row it answers."""
    line = _row_number(text)
    target = next(
        (
            index
            for index, row in enumerate(rows)
            if line is not None and row.line == line
        ),
        None,
    )
    if target is None:
        target = next(
            (index for index, row in enumerate(rows) if row.status == "uncertain"),
            None,
        )
    if target is None:
        return rows
    row = rows[target]
    if line is not None and row.status != "uncertain":
        # A line number that names a settled row is not an answer to it.
        return rows
    rest = _ROW_ANSWER.sub("", text) if line is not None else text
    if skip(rest):
        return [*rows[:target], _replace(row, status="skipped"), *rows[target + 1 :]]
    ids = _model_ids(rest, vocabulary)
    if len(ids) != 1:
        return rows
    product_id = ids.pop()
    if line is None and not _fits(row, product_id, vocabulary):
        # An unnumbered short message that names another product is not an
        # answer to the open row (it is a normal turn).
        return rows
    return [
        *rows[:target],
        _matched(
            row.line,
            Parsed(row.text, row.quantity),
            product_id,
            vocabulary,
            row.matches,
        ),
        *rows[target + 1 :],
    ]


def _replace(row: Row, **changes: Any) -> Row:
    return replace(row, **changes)


_ROW_ANSWER = re.compile(
    r"^\s*(?:row|line|zeile|position|pos\.?)\s*\d+\s*[:：-]\s*", re.IGNORECASE
)
_SKIP = re.compile(
    r"^\s*(?:skip(?: this)?|not now|leave (?:this|it) out|"
    r"(?:diese zeile )?(?:überspringen|ueberspringen)|später|spaeter|nicht jetzt)\b",
    re.IGNORECASE,
)


def skip(text: str) -> bool:
    """Whether the message sets the open row aside."""
    return bool(_SKIP.match(text))


def _row_number(text: str) -> int | None:
    found = _ROW_ANSWER.match(text)
    if not found:
        return None
    digits = re.search(r"\d+", found.group(0))
    return int(digits.group(0)) if digits else None


# ---------------------------------------------------------------------------
# The turn: a code-written sentence and the card the shell renders

# Functional UI text: the service writes this turn, so the wording is fixed here
# and reviewed in docs/acceptance/2026-10-19/251/copy-review.md.
SUMMARY = {
    "en": {
        "lead": "I checked your list: {matched} of {total} lines match our products.",
        "lead_one": "I checked your list: one of {total} lines matches our products.",
        "lead_single": "I checked your list: the line matches our products.",
        "lead_truncated": (
            "I checked the first part of your list: {matched} match our products."
        ),
        "lead_truncated_one": (
            "I checked the first part of your list: one matches our products."
        ),
        "none": "I could not match any line of your list to our products.",
        "none_truncated": (
            "I could not match any of the rows I read of your list to our products."
        ),
        "one_ask": "One line needs your confirmation.",
        "asks": "{count} lines need your confirmation: one at a time.",
        "one_missing": "One line is not in our product range.",
        "missing": "{count} lines are not in our product range.",
        "add_one": "You can add the confirmed product to your solution draft.",
        "add": "You can add the confirmed products to your solution draft.",
    },
    "de": {
        "lead": "Ich habe Ihre Liste geprüft: {matched} von {total} Zeilen passen zu unseren Produkten.",
        "lead_one": "Ich habe Ihre Liste geprüft: Eine von {total} Zeilen passt zu unseren Produkten.",
        "lead_single": "Ich habe Ihre Liste geprüft: Die Zeile passt zu unseren Produkten.",
        "lead_truncated": (
            "Ich habe den ersten Teil Ihrer Liste geprüft: "
            "{matched} passen zu unseren Produkten."
        ),
        "lead_truncated_one": (
            "Ich habe den ersten Teil Ihrer Liste geprüft: "
            "Eine passt zu unseren Produkten."
        ),
        "none": "Ich konnte keine Zeile Ihrer Liste einem unserer Produkte zuordnen.",
        "none_truncated": (
            "Ich konnte keine der gelesenen Zeilen Ihrer Liste "
            "unseren Produkten zuordnen."
        ),
        "one_ask": "Eine Zeile braucht Ihre Bestätigung.",
        "asks": "{count} Zeilen brauchen Ihre Bestätigung: eine nach der anderen.",
        "one_missing": "Eine Zeile ist nicht in unserem Sortiment.",
        "missing": "{count} Zeilen sind nicht in unserem Sortiment.",
        "add_one": "Sie können das bestätigte Produkt Ihrem Lösungsentwurf hinzufügen.",
        "add": "Sie können die bestätigten Produkte Ihrem Lösungsentwurf hinzufügen.",
    },
}


def answer(result: PartsList, locale: str) -> tuple[TurnOutput, PartsBlock]:
    """The code-written turn: its sentence, and the card with rows and the write."""
    language: Literal["en", "de"] = "de" if locale.startswith("de") else "en"
    words = SUMMARY[language]
    total = len(result.rows)
    matched = sum(1 for row in result.rows if row.status == "matched")
    uncertain = sum(1 for row in result.rows if row.status == "uncertain")
    missing = sum(1 for row in result.rows if row.status == "missing")
    sentences: list[str] = []
    if matched:
        if result.truncated:
            key = "lead_truncated_one" if matched == 1 else "lead_truncated"
            sentences.append(words[key].format(matched=matched))
        elif matched == 1 and total == 1:
            sentences.append(words["lead_single"])
        elif matched == 1:
            sentences.append(words["lead_one"].format(total=total))
        else:
            sentences.append(words["lead"].format(matched=matched, total=total))
    if uncertain:
        sentences.append(
            words["one_ask"]
            if uncertain == 1
            else words["asks"].format(count=uncertain)
        )
    if not matched and not uncertain:
        key = "none_truncated" if result.truncated else "none"
        sentences.append(words[key])
    if missing and not (not matched and not uncertain):
        sentences.append(
            words["one_missing"]
            if missing == 1
            else words["missing"].format(count=missing)
        )
    if result.add is not None:
        sentences.append(words["add_one"] if result.add.products == 1 else words["add"])
    add = result.add
    block = PartsBlock(
        rows=[
            PartsRow(
                line=row.line,
                text=row.text,
                quantity=row.quantity,
                status=row.status,
                product_id=row.product_id,
                label=row.label,
                options=list(row.options),
            )
            for row in result.rows
        ],
        ask_line=result.ask_line,
        add=add,
        truncated=result.truncated,
    )
    return (
        TurnOutput(language=language, blocks=[TextBlock(text=" ".join(sentences))]),
        block,
    )
