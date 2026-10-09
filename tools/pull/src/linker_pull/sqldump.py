"""Reading and writing the text of a mysqldump, one table row at a time.

The live host dumps with MariaDB 11.8's mysqldump (`mysqldump --version` over
SSH, 2026-10-09). It writes an INSERT as a line `INSERT INTO `t` VALUES`
followed by one row per line, each ending in "," or, for the last, ";" (seen in
its output on 2026-10-09); MySQL's mysqldump writes the rows on the INSERT's
own line, and both forms are read. A value is NULL, an unquoted number, or a
string quoted and escaped as mysql_real_escape_string() escapes it (NUL, \\n,
\\r, \\, ', " and Ctrl-Z get a backslash; nothing else does), so a row never
spans lines. The live tables have no binary columns (information_schema.columns,
2026-10-09), so --hex-blob output does not occur.

A value keeps the text the dump wrote; a string is decoded only when read, and
re-encoded only when it is changed, so every value nobody touches is written
back byte for byte.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

CREATE_TABLE = re.compile(r"CREATE TABLE `([^`]+)` \(")
# A column line of a CREATE TABLE; key and constraint lines do not start with a backtick.
COLUMN = re.compile(r"  `([^`]+)` ")
INSERT = re.compile(r"INSERT INTO `([^`]+)` VALUES ?")
# Any other statement that writes rows: INSERT IGNORE, a column list
# (--complete-insert), REPLACE (--replace).
UNREAD_INSERT = re.compile(r"(?:INSERT|REPLACE)\b", re.IGNORECASE)
# One value: a quoted string (unrolled, so long strings do not recurse), or
# anything up to the next separator (NULL, numbers).
VALUE = re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'|[^,()']+", re.DOTALL)
ESCAPE = re.compile(r"\\(.)", re.DOTALL)
UNESCAPED = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "b": "\b", "Z": "\x1a"}
NEEDS_ESCAPE = re.compile("[\0\n\r\\\\'\"\x1a]")
ESCAPED = {
    "\0": "\\0",
    "\n": "\\n",
    "\r": "\\r",
    "\\": "\\\\",
    "'": "\\'",
    '"': '\\"',
    "\x1a": "\\Z",
}


class DumpError(ValueError):
    """The text is not mysqldump output this module reads."""


class Value:
    """One value of a row, as the dump writes it."""

    __slots__ = ("_raw", "_text")

    def __init__(self, raw: str) -> None:
        self._raw = raw
        self._text: str | None = None

    @classmethod
    def of(cls, text: str | None) -> Value:
        """A value holding `text` (None is NULL)."""
        if text is None:
            return cls("NULL")
        value = cls(quote(text))
        value._text = text
        return value

    @property
    def raw(self) -> str:
        return self._raw

    @property
    def is_null(self) -> bool:
        return self._raw == "NULL"

    @property
    def is_string(self) -> bool:
        return self._raw.startswith("'")

    @property
    def text(self) -> str | None:
        """The decoded string; the literal itself for a number; None for NULL."""
        if self.is_null:
            return None
        if not self.is_string:
            return self._raw
        if self._text is None:
            self._text = unquote(self._raw)
        return self._text


@dataclass
class Table:
    """A table of the dump: its name and the names of its columns, in order."""

    name: str
    columns: list[str] = field(default_factory=list)

    def index(self, column: str) -> int:
        try:
            return self.columns.index(column)
        except ValueError:
            raise DumpError(f"{self.name} has no column {column}") from None


@dataclass
class Insert:
    """An INSERT statement: the table, its rows, and whether each row had a line of its own."""

    table: Table
    rows: list[list[Value]]
    row_per_line: bool = False

    def line(self) -> str:
        """The statement as the dump wrote it; empty when every row was dropped."""
        if not self.rows:
            return ""
        rows = ["(" + ",".join(value.raw for value in row) + ")" for row in self.rows]
        if self.row_per_line:
            return (
                f"INSERT INTO `{self.table.name}` VALUES\n" + ",\n".join(rows) + ";\n"
            )
        return f"INSERT INTO `{self.table.name}` VALUES " + ",".join(rows) + ";\n"


Line = str | Insert


def read(lines: Iterator[str]) -> Iterator[Line]:
    """The dump's lines, with every INSERT parsed into its rows.

    Lines are text decoded with errors="surrogateescape", so bytes that are not
    UTF-8 survive the round trip.
    """
    tables: dict[str, Table] = {}
    building: Table | None = None
    lines = iter(lines)
    for line in lines:
        if building is not None:
            column = COLUMN.match(line)
            if column:
                building.columns.append(column.group(1))
            elif line.startswith(")"):
                building = None
            yield line
            continue
        insert = INSERT.match(line)
        if insert is None and UNREAD_INSERT.match(line):
            # Rows this reader cannot see would pass every rule unchanged.
            raise DumpError(f"an INSERT this reader does not parse: {line[:60]!r}")
        if insert:
            name = insert.group(1)
            table = tables.get(name)
            if table is None:
                raise DumpError(f"INSERT INTO {name} before its CREATE TABLE")
            width = len(table.columns)
            if line[insert.end() :].strip():
                yield Insert(table, parse_rows(line, insert.end(), width))
            else:
                yield Insert(table, _rows_on_lines(lines, width), row_per_line=True)
            continue
        create = CREATE_TABLE.match(line)
        if create:
            building = Table(create.group(1))
            tables[building.name] = building
        yield line


def _rows_on_lines(lines: Iterator[str], width: int) -> list[list[Value]]:
    """The rows that follow an `INSERT … VALUES` line, one per line, up to the one ending in ;."""
    rows: list[list[Value]] = []
    for line in lines:
        row, position = parse_row(line, 0, width)
        rows.append(row)
        ending = line[position : position + 1]
        if ending == ";":
            return rows
        if ending != ",":
            raise DumpError(f"a row line ends in {ending!r}, not , or ;")
    raise DumpError("the dump ends inside an INSERT")


def write(items: Iterator[Line]) -> Iterator[str]:
    """Dump lines again: INSERTs from their (possibly changed) rows."""
    for item in items:
        if isinstance(item, Insert):
            line = item.line()
            if line:
                yield line
        else:
            yield item


def parse_rows(line: str, start: int, width: int) -> list[list[Value]]:
    """The rows of `(…),(…);` from `start` on one line, each `width` values wide."""
    rows: list[list[Value]] = []
    position = start
    while True:
        row, position = parse_row(line, position, width)
        rows.append(row)
        separator = line[position : position + 1]
        position += 1
        if separator == ";":
            return rows
        if separator != ",":
            raise DumpError(f"expected , or ; at {position - 1}")


def parse_row(line: str, position: int, width: int) -> tuple[list[Value], int]:
    """One `(…)` from `position`: its values and the offset after the closing parenthesis."""
    if line[position : position + 1] != "(":
        raise DumpError(f"expected ( at {position}")
    position += 1
    row: list[Value] = []
    while True:
        found = VALUE.match(line, position)
        if found is None:
            raise DumpError(f"no value at {position}")
        row.append(Value(found.group()))
        position = found.end()
        separator = line[position : position + 1]
        position += 1
        if separator == ")":
            break
        if separator != ",":
            raise DumpError(f"expected , or ) at {position - 1}")
    if len(row) != width:
        raise DumpError(f"a row of {len(row)} values in a table of {width} columns")
    return row, position


def unquote(raw: str) -> str:
    """The string a quoted, escaped SQL literal stands for."""
    body = raw[1:-1]
    if "\\" not in body:
        return body
    return ESCAPE.sub(lambda found: UNESCAPED.get(found.group(1), found.group(1)), body)


def quote(text: str) -> str:
    """`text` as a quoted SQL literal, escaped as mysqldump escapes it."""
    return "'" + NEEDS_ESCAPE.sub(lambda found: ESCAPED[found.group()], text) + "'"
