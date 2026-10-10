"""Reading and writing mysqldump text.

Fixture: tests/fixtures/live-dump.sql has the live site's table structure as
MariaDB 11.8's mysqldump wrote it on 2026-10-09 (header, CREATE TABLE, one row
per line) with synthetic rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from linker_pull.sqldump import DumpError, Insert, Value, quote, read, unquote, write

FIXTURE = Path(__file__).parent / "fixtures" / "live-dump.sql"


def lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def test_the_live_format_is_written_back_byte_for_byte() -> None:
    text = FIXTURE.read_text()

    assert "".join(write(read(iter(lines(text))))) == text


def test_rows_on_the_insert_line_mysql_form_round_trip() -> None:
    text = (
        "CREATE TABLE `t` (\n  `id` int,\n  `s` text\n) ENGINE=InnoDB;\n"
        "INSERT INTO `t` VALUES (1,'a'),(2,NULL),(3,'it\\'s');\n"
    )

    items = list(read(iter(lines(text))))

    insert = items[-1]
    assert isinstance(insert, Insert) and not insert.row_per_line
    assert [[value.text for value in row] for row in insert.rows] == [
        ["1", "a"],
        ["2", None],
        ["3", "it's"],
    ]
    assert "".join(write(iter(items))) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "plain",
        'it\'s "quoted"',
        "back\\slash",
        "line\nbreak\r\n",
        "nul\0 and ctrl-z\x1a",
        "tab\tstays",
        "Umlaut ä, emoji 🔋",
        'a:1:{s:3:"url";s:21:"https://de-linker.com";}',
    ],
)
def test_unquote_reverses_quote(text: str) -> None:
    assert unquote(quote(text)) == text


def test_quote_escapes_what_mysql_real_escape_string_escapes_and_nothing_else() -> None:
    assert quote("\0\n\r\\'\"\x1a") == "'\\0\\n\\r\\\\\\'\\\"\\Z'"
    assert quote("a\tb") == "'a\tb'"


def test_a_changed_value_is_escaped_and_others_keep_their_bytes() -> None:
    text = (
        "CREATE TABLE `t` (\n  `id` int,\n  `s` text\n) ENGINE=InnoDB;\n"
        "INSERT INTO `t` VALUES\n(1,'keep \\'me\\''),\n(2,'old');\n"
    )
    items = list(read(iter(lines(text))))
    insert = items[-1]
    assert isinstance(insert, Insert)

    insert.rows[1][1] = Value.of("new's\nline")

    assert "".join(write(iter(items))).endswith(
        "INSERT INTO `t` VALUES\n(1,'keep \\'me\\''),\n(2,'new\\'s\\nline');\n"
    )


def test_dropping_rows_keeps_the_statement_valid() -> None:
    text = (
        "CREATE TABLE `t` (\n  `id` int\n) ENGINE=InnoDB;\n"
        "INSERT INTO `t` VALUES\n(1),\n(2),\n(3);\n"
    )
    items = list(read(iter(lines(text))))
    insert = items[-1]
    assert isinstance(insert, Insert)

    insert.rows = insert.rows[:2]
    assert "".join(write(iter(items))).endswith("INSERT INTO `t` VALUES\n(1),\n(2);\n")

    insert.rows = []
    assert "INSERT" not in "".join(write(iter(items)))


def test_columns_come_from_the_create_table() -> None:
    insert = next(
        item
        for item in read(iter(lines(FIXTURE.read_text())))
        if isinstance(item, Insert)
    )

    assert insert.table.name == "wp_users"
    assert insert.table.columns[:3] == ["ID", "user_login", "user_pass"]
    assert insert.table.index("user_email") == 4


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("INSERT INTO `t` VALUES (1);\n", "before its CREATE TABLE"),
        (
            "CREATE TABLE `t` (\n  `id` int\n) ;\nINSERT INTO `t` VALUES (1,2);\n",
            "1 columns",
        ),
        (
            "CREATE TABLE `t` (\n  `id` int\n) ;\nINSERT INTO `t` VALUES\n(1),\n",
            "ends inside",
        ),
        (
            "CREATE TABLE `t` (\n  `id` int\n) ;\nINSERT INTO `t` VALUES ('open);\n",
            "no value",
        ),
        # Rows the reader cannot see would pass the anonymizer unchanged.
        ("INSERT INTO `t` (`id`) VALUES (1);\n", "does not parse"),
        ("INSERT IGNORE INTO `t` VALUES (1);\n", "does not parse"),
        ("REPLACE INTO `t` VALUES (1);\n", "does not parse"),
    ],
)
def test_what_is_not_a_dump_is_refused(text: str, message: str) -> None:
    with pytest.raises(DumpError, match=message):
        list(read(iter(lines(text))))
