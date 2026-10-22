"""CSV to real intervals, preserving DST, measurement semantics and provenance."""

from __future__ import annotations

import csv
import io
import math
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .canonical import digest, encode
from .csv_mapping import CsvMapping
from .errors import InvalidInput
from .interval import Interval
from .power_series import PowerSeries
from .series_source import SeriesSource
from .timezone_rules import TimezoneRules


def _timestamp(text: str, zone: ZoneInfo, fold: str | None, line: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.strip())
    except ValueError as error:
        raise InvalidInput(f"row {line}: ISO date/time required") from error
    if fold is not None and fold not in ("0", "1"):
        raise InvalidInput(f"row {line}: fold must be explicitly 0 or 1")
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        if fold is not None:
            raise InvalidInput(f"row {line}: use an explicit offset or fold, not both")
        return parsed.astimezone(UTC)
    # Round trips detect spring's nonexistent local times. Fall's repeated
    # local times keep two distinct UTC candidates and require a stated fold.
    candidates: dict[int, datetime] = {}
    for occurrence in (0, 1):
        aware = parsed.replace(tzinfo=zone, fold=occurrence)
        instant = aware.astimezone(UTC)
        back = instant.astimezone(zone)
        if back.replace(tzinfo=None) == parsed and back.fold == occurrence:
            candidates[occurrence] = instant
    if not candidates:
        raise InvalidInput(f"row {line}: local time does not exist in this timezone")
    if fold is not None:
        selected = candidates.get(int(fold))
        if selected is None:
            raise InvalidInput(f"row {line}: fold does not identify this local time")
        return selected
    if len(candidates) != 1:
        raise InvalidInput(f"row {line}: repeated local time requires offset or fold")
    return next(iter(candidates.values()))


def _number(text: str, decimal: str, line: int) -> float:
    value = text.strip()
    separator = re.escape(decimal)
    if not re.fullmatch(
        rf"[+-]?(?:\d+(?:{separator}\d*)?|{separator}\d+)(?:[eE][+-]?\d+)?", value
    ):
        raise InvalidInput(
            f"row {line}: ungrouped number in the selected decimal convention required"
        )
    parsed = float(value.replace(decimal, "."))
    if not math.isfinite(parsed):
        raise InvalidInput(f"row {line}: finite number required")
    return parsed


def read_profile(
    content: bytes, mapping: CsvMapping, rules: TimezoneRules
) -> PowerSeries:
    if rules.name != mapping.timezone:
        raise InvalidInput("pinned timezone rules do not match the import mapping")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError as error:
        raise InvalidInput("profile must use UTF-8 encoding") from error
    zone = rules.zone()
    reader = csv.reader(
        io.StringIO(text, newline=""), delimiter=mapping.delimiter, strict=True
    )
    try:
        header = next(reader, [])
        required = [mapping.timestamp_column, mapping.value_column]
        required.extend(
            value
            for value in (
                mapping.end_timestamp_column,
                mapping.fold_column,
                mapping.end_fold_column,
            )
            if value is not None
        )
        if len(set(header)) != len(header) or any(
            value not in header for value in required
        ):
            raise InvalidInput("CSV needs unique headers and every mapped column")
        positions = {value: header.index(value) for value in required}
        intervals: list[Interval] = []
        powers: list[float] = []
        for values in reader:
            line = reader.line_num
            if not values:
                continue
            if len(values) != len(header):
                raise InvalidInput(f"row {line}: value count differs from CSV headers")
            timestamp = _timestamp(
                values[positions[mapping.timestamp_column]],
                zone,
                values[positions[mapping.fold_column]].strip()
                if mapping.fold_column
                else None,
                line,
            )
            if mapping.end_timestamp_column is not None:
                end = _timestamp(
                    values[positions[mapping.end_timestamp_column]],
                    zone,
                    values[positions[mapping.end_fold_column]].strip()
                    if mapping.end_fold_column
                    else None,
                    line,
                )
                interval = Interval(timestamp, end)
            else:
                if mapping.interval_seconds is None:
                    raise InvalidInput("interval duration required")
                try:
                    step = timedelta(seconds=mapping.interval_seconds)
                    interval = (
                        Interval(timestamp, timestamp + step)
                        if mapping.timestamp_role == "start"
                        else Interval(timestamp - step, timestamp)
                    )
                except OverflowError as error:
                    raise InvalidInput(
                        f"row {line}: interval duration exceeds time domain"
                    ) from error
            number = _number(
                values[positions[mapping.value_column]], mapping.decimal, line
            )
            power = (
                number / interval.hours
                if mapping.value_kind == "interval_energy_kwh"
                else number
            )
            intervals.append(interval)
            powers.append(power)
    except csv.Error as error:
        raise InvalidInput(f"invalid CSV at line {reader.line_num}") from error
    if not intervals:
        raise InvalidInput("profile contains no intervals")
    source = SeriesSource(
        raw_sha256=digest(content),
        origin=mapping.origin,
        timezone=mapping.timezone,
        native_max_interval_seconds=max(interval.duration_us for interval in intervals)
        / 1_000_000,
        details_json=encode(
            {"csv_mapping": mapping.document(), "timezone_rules_sha256": rules.sha256}
        ),
    )
    return PowerSeries(tuple(intervals), tuple(powers), mapping.measurement, source)
