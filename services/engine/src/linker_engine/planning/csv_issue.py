"""Bounded CSV diagnostics: stable issues and line/role, never private cell text."""

from __future__ import annotations

from typing import Literal

from .canonical import Object
from .errors import InvalidInput
from .wire_numbers import MAX_WIRE_NUMBER

type CsvField = Literal["timestamp", "end_timestamp", "value", "header"]

REASONS = {
    "timestamp_format": "ISO date/time required",
    "timestamp_range": "instant is outside the supported UTC date/time domain",
    "fold_value": "fold must be explicitly 0 or 1",
    "offset_and_fold": "use an explicit offset or fold, not both",
    "local_time_range": "local time exceeds supported domain",
    "local_time_nonexistent": "local time does not exist in this timezone",
    "fold_mismatch": "fold does not identify this local time",
    "local_time_ambiguous": "repeated local time requires offset or fold",
    "number_format": "ungrouped number in the selected decimal convention required",
    "number_nonfinite": "finite number required",
    "encoding": "profile must use UTF-8 encoding",
    "headers": "CSV needs unique headers and every mapped column",
    "row_width": "value count differs from CSV headers",
    "interval_duration": "interval duration exceeds time domain or is not positive",
    "interval_order": "intervals must be ordered and must not overlap",
    "value_sign": "finite power and a valid sign at this boundary required",
    "energy_range": "integrated energy is not finite",
    "csv_syntax": "invalid CSV syntax",
    "empty": "profile contains no intervals",
}


class CsvIssue(InvalidInput):
    """An import issue safe for translation in an authorised client."""

    def __init__(
        self, issue: str, *, line: int | None = None, field: CsvField | None = None
    ) -> None:
        if (
            issue not in REASONS
            or (
                line is not None
                and (type(line) is not int or not 1 <= line <= MAX_WIRE_NUMBER)
            )
            or field not in (None, "timestamp", "end_timestamp", "value", "header")
        ):
            raise ValueError("invalid CSV diagnostic")
        self.issue = issue
        self.line = line
        self.field = field
        super().__init__(
            (f"line {line}: " if line is not None else "") + REASONS[issue]
        )

    def document(self) -> Object:
        return {"issue": self.issue, "line": self.line, "field": self.field}
