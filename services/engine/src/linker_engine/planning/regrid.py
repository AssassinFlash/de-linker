"""Energy-preserving interval overlap; refinement never creates observations."""

from __future__ import annotations

import math

from .canonical import Json, digest, encode
from .errors import InvalidInput
from .interval import Interval, microseconds
from .power_series import PowerSeries, check_intervals
from .series_transform import SeriesTransform


def regrid(source: PowerSeries, target: tuple[Interval, ...]) -> PowerSeries:
    check_intervals(target)
    powers: list[float] = []
    first = 0
    exact_copy = True
    for interval in target:
        while (
            first < len(source.intervals)
            and source.intervals[first].end <= interval.start
        ):
            first += 1
        index, covered = first, 0
        weighted: list[float] = []
        while index < len(source.intervals):
            native = source.intervals[index]
            if native.start >= interval.end:
                break
            overlap_start = max(native.start, interval.start)
            overlap_end = min(native.end, interval.end)
            if overlap_end > overlap_start:
                span = microseconds(overlap_end - overlap_start)
                weighted.append(source.values_kw[index] * span / interval.duration_us)
                covered += span
            index += 1
        if covered != interval.duration_us:
            raise InvalidInput(
                "source does not cover target interval "
                f"{interval.start.isoformat()} to {interval.end.isoformat()}"
            )
        if first >= len(source.intervals) or source.intervals[first] != interval:
            exact_copy = False
        powers.append(math.fsum(weighted))
    axis: list[Json] = [
        {"start_utc": item.start.isoformat(), "end_utc": item.end.isoformat()}
        for item in target
    ]
    transformation = SeriesTransform(
        input_document_sha256=digest(encode(source.document())),
        target_axis_sha256=digest(encode({"intervals": axis})),
        input_max_interval_seconds=max(item.duration_us for item in source.intervals)
        / 1_000_000,
        output_max_interval_seconds=max(item.duration_us for item in target)
        / 1_000_000,
        exact_interval_copy=exact_copy,
    )
    return PowerSeries(
        target,
        tuple(powers),
        source.measurement,
        source.source,
        (*source.transformations, transformation),
    )


def align(*series: PowerSeries) -> tuple[PowerSeries, ...]:
    """Cover the first series' entire horizon, using all actual boundaries."""
    if not series:
        raise InvalidInput("at least one series is required")
    start, end = series[0].intervals[0].start, series[0].intervals[-1].end
    edges = {start, end}
    for item in series:
        for interval in item.intervals:
            if start < interval.start < end:
                edges.add(interval.start)
            if start < interval.end < end:
                edges.add(interval.end)
    ordered = sorted(edges)
    target = tuple(
        Interval(left, right) for left, right in zip(ordered, ordered[1:], strict=False)
    )
    return tuple(regrid(item, target) for item in series)
