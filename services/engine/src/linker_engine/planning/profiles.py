"""CSV to real intervals, preserving DST, measurement semantics and provenance."""

from __future__ import annotations

import csv
import math
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .canonical import digest, encode
from .csv_issue import CsvField, CsvIssue
from .csv_mapping import CsvMapping
from .csv_reader import source_reader
from .errors import InvalidInput
from .interval import Interval, utc
from .power_series import PowerSeries
from .series_source import SeriesSource
from .timezone_rules import TimezoneRules


def _timestamp(
    text: str,
    zone: ZoneInfo,
    fold: str | None,
    line: int,
    field: CsvField = "timestamp",
) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.strip())
    except ValueError as error:
        raise CsvIssue("timestamp_format", line=line, field=field) from error
    if fold is not None and fold not in ("0", "1"):
        raise CsvIssue("fold_value", line=line, field=field)
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        if fold is not None:
            raise CsvIssue("offset_and_fold", line=line, field=field)
        try:
            return utc(parsed)
        except InvalidInput as error:
            raise CsvIssue("timestamp_range", line=line, field=field) from error
    # Round trips detect spring's nonexistent local times. Fall's repeated
    # local times keep two distinct UTC candidates and require a stated fold.
    candidates: dict[int, datetime] = {}
    for occurrence in (0, 1):
        aware = parsed.replace(tzinfo=zone, fold=occurrence)
        try:
            instant = utc(aware)
            back = instant.astimezone(zone)
        except InvalidInput as error:
            raise CsvIssue("timestamp_range", line=line, field=field) from error
        except (OverflowError, ValueError) as error:
            raise CsvIssue("local_time_range", line=line, field=field) from error
        if back.replace(tzinfo=None) == parsed and back.fold == occurrence:
            candidates[occurrence] = instant
    if not candidates:
        raise CsvIssue("local_time_nonexistent", line=line, field=field)
    if fold is not None:
        selected = candidates.get(int(fold))
        if selected is None:
            raise CsvIssue("fold_mismatch", line=line, field=field)
        return selected
    if len(candidates) != 1:
        raise CsvIssue("local_time_ambiguous", line=line, field=field)
    return next(iter(candidates.values()))


def _number(text: str, decimal: str, line: int) -> float:
    value = text.strip()
    separator = re.escape(decimal)
    if not re.fullmatch(
        rf"[+-]?(?:\d+(?:{separator}\d*)?|{separator}\d+)(?:[eE][+-]?\d+)?", value
    ):
        raise CsvIssue("number_format", line=line, field="value")
    parsed = float(value.replace(decimal, "."))
    if not math.isfinite(parsed):
        raise CsvIssue("number_nonfinite", line=line, field="value")
    return parsed


def read_profile(
    content: bytes, mapping: CsvMapping, rules: TimezoneRules
) -> PowerSeries:
    if rules.name != mapping.timezone:
        raise InvalidInput("pinned timezone rules do not match the import mapping")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError as error:
        raise CsvIssue("encoding") from error
    zone = rules.zone()
    reader = source_reader(text, mapping.delimiter)
    completed_line = 0
    try:
        header = next(reader, [])
        completed_line = reader.line_num
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
            raise CsvIssue("headers", line=1, field="header")
        positions = {value: header.index(value) for value in required}
        intervals: list[Interval] = []
        powers: list[float] = []
        for values in reader:
            line = completed_line + 1
            completed_line = reader.line_num
            if not values:
                continue
            if len(values) != len(header):
                raise CsvIssue("row_width", line=line)
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
                    "end_timestamp",
                )
                if end <= timestamp:
                    raise CsvIssue(
                        "interval_duration", line=line, field="end_timestamp"
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
                except (OverflowError, InvalidInput) as error:
                    raise CsvIssue(
                        "interval_duration", line=line, field="timestamp"
                    ) from error
            number = _number(
                values[positions[mapping.value_column]], mapping.decimal, line
            )
            power = (
                number / interval.hours
                if mapping.value_kind == "interval_energy_kwh"
                else number
            )
            if not math.isfinite(power) or (
                mapping.measurement != "net_import" and power < 0
            ):
                raise CsvIssue("value_sign", line=line, field="value")
            if intervals and interval.start < intervals[-1].end:
                raise CsvIssue("interval_order", line=line, field="timestamp")
            intervals.append(interval)
            powers.append(power)
    except csv.Error as error:
        raise CsvIssue("csv_syntax", line=completed_line + 1) from error
    if not intervals:
        raise CsvIssue("empty")
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
    series = PowerSeries(tuple(intervals), tuple(powers), mapping.measurement, source)
    try:
        _ = series.total_kwh
    except InvalidInput as error:
        raise CsvIssue("energy_range", field="value") from error
    return series
