"""An explicit import mapping; row counts and column positions imply no units."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from .canonical import Object
from .errors import InvalidInput
from .power_series import MEASUREMENTS, Measurement
from .series_source import Origin
from .timezone_rules import validate_zone_name


@dataclass(frozen=True)
class CsvMapping:
    timestamp_column: str
    value_column: str
    measurement: Measurement
    value_kind: Literal["interval_average_kw", "interval_energy_kwh"]
    timestamp_role: Literal["start", "end"]
    timezone: str
    origin: Origin
    interval_seconds: float | None
    delimiter: str
    decimal: Literal[".", ","]
    end_timestamp_column: str | None = None
    fold_column: str | None = None
    end_fold_column: str | None = None

    def __post_init__(self) -> None:
        if not self.timestamp_column or not self.value_column:
            raise InvalidInput("timestamp and value columns required")
        if self.measurement not in MEASUREMENTS or self.origin not in (
            "measured",
            "modelled",
            "template",
            "synthetic",
        ):
            raise InvalidInput("measurement and origin must be explicit")
        if self.value_kind not in ("interval_average_kw", "interval_energy_kwh"):
            raise InvalidInput("interval-average kW or interval-energy kWh required")
        if self.timestamp_role not in ("start", "end"):
            raise InvalidInput("timestamp start/end convention required")
        if len(self.delimiter) != 1 or self.delimiter in ("\n", "\r", '"'):
            raise InvalidInput("one unambiguous CSV delimiter required")
        if self.decimal not in (".", ","):
            raise InvalidInput("decimal convention required")
        fixed = self.interval_seconds
        if self.end_timestamp_column is not None:
            if (
                not self.end_timestamp_column
                or fixed is not None
                or self.timestamp_role != "start"
            ):
                raise InvalidInput(
                    "explicit ends require starts and no inferred/fixed duration"
                )
        elif (
            fixed is None
            or type(fixed) not in (int, float)
            or not math.isfinite(fixed)
            or fixed <= 0
        ):
            raise InvalidInput("an explicit positive interval duration is required")
        if self.end_fold_column and self.end_timestamp_column is None:
            raise InvalidInput("end fold requires an explicit end column")
        columns = [self.timestamp_column, self.value_column]
        columns.extend(
            value
            for value in (
                self.end_timestamp_column,
                self.fold_column,
                self.end_fold_column,
            )
            if value is not None
        )
        if any(not column for column in columns) or len(set(columns)) != len(columns):
            raise InvalidInput("mapped columns must be distinct and nonempty")
        validate_zone_name(self.timezone)

    def document(self) -> Object:
        return {
            "timestamp_column": self.timestamp_column,
            "value_column": self.value_column,
            "measurement": self.measurement,
            "value_kind": self.value_kind,
            "timestamp_role": self.timestamp_role,
            "timezone": self.timezone,
            "origin": self.origin,
            "interval_seconds": self.interval_seconds,
            "delimiter": self.delimiter,
            "decimal": self.decimal,
            "end_timestamp_column": self.end_timestamp_column,
            "fold_column": self.fold_column,
            "end_fold_column": self.end_fold_column,
            "offset_rule": "explicit_offset_precedes_naive_timezone",
            "within_interval_assumption": "constant_mean_no_new_observations",
        }
