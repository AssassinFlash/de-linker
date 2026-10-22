"""Read-only source-column preview, never a time-series quality verdict."""

from __future__ import annotations

import csv
import io

from .canonical import Json, Object, digest, encode
from .csv_issue import CsvIssue
from .errors import InvalidInput


def inspect_csv(
    content: bytes, delimiter: str, *, page_size: int, max_reply_bytes: int
) -> Object:
    if len(delimiter) != 1 or delimiter in ('"', "\r", "\n"):
        raise InvalidInput("one unambiguous CSV delimiter required")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError as error:
        raise CsvIssue("encoding") from error
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    completed_line = 0
    rows: list[Json] = []
    records = 0
    try:
        header = next(reader, [])
        completed_line = reader.line_num
        if not header or len(set(header)) != len(header):
            raise CsvIssue("headers", line=1, field="header")
        for values in reader:
            line = completed_line + 1
            completed_line = reader.line_num
            if not values:
                continue
            if len(values) != len(header):
                raise CsvIssue("row_width", line=line)
            records += 1
            if len(rows) < page_size:
                rows.append({"line": line, "cells": list(values)})
    except csv.Error as error:
        raise CsvIssue("csv_syntax", line=completed_line + 1) from error
    if not records:
        raise CsvIssue("empty")
    result: Object = {
        "schema_version": 1,
        "evaluation_scope": "csv_structure_only",
        "content_sha256": digest(content),
        "delimiter": delimiter,
        "columns": list(header),
        "record_count": records,
        "rows": rows,
        "rows_truncated": records > len(rows),
    }
    # The deployment JSON-body ceiling also bounds raw private previews.
    # Refuse an unrepresentable preview; never silently truncate cell values.
    if len(encode(result)) > max_reply_bytes:
        raise InvalidInput("CSV preview exceeds deployment reply limit")
    return result
