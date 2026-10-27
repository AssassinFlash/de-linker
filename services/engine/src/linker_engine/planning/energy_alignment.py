"""Shared real-time schedule alignment for explicitly typed AC/DC producers."""

from __future__ import annotations

from bisect import bisect_left

from .canonical import Object
from .energy_schedule import EnergySchedule
from .errors import InvalidInput
from .interval import Interval
from .operating_limits import OperatingLimits
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile


def schedule_axis(
    scenario: EnergySchedule,
    profiles: dict[str, PowerSeries] | dict[str, PowerSeries | DcPvProfile],
    *,
    max_intervals: int,
    measurements: dict[str, str] | None = None,
) -> tuple[tuple[Interval, OperatingLimits, tuple[Interval, ...]], ...]:
    schedule = tuple((item.interval(), item.limits()) for item in scenario.schedule)
    if any(
        previous[0].end != current[0].start
        for previous, current in zip(schedule, schedule[1:], strict=False)
    ):
        raise InvalidInput("operating schedule must be ordered and continuous")
    if (
        any(item.mode == "outage" for item in scenario.schedule)
        and "critical_load" not in profiles
    ):
        raise InvalidInput("outage periods require an explicit critical-load profile")
    start, end = schedule[0][0].start, schedule[-1][0].end
    edges = {start, end}
    for interval, _ in schedule:
        edges.update((interval.start, interval.end))
    if measurements is not None and set(measurements) != set(profiles):
        raise InvalidInput("each named profile requires its explicit measurement stage")
    for role, profile in profiles.items():
        if profile.measurement != (
            measurements[role] if measurements is not None else role
        ):
            raise InvalidInput(f"{role}: profile measurement boundary differs")
        for interval in profile.intervals:
            if start < interval.start < end:
                edges.add(interval.start)
            if start < interval.end < end:
                edges.add(interval.end)
    if len(edges) - 1 > max_intervals:
        raise InvalidInput("aligned horizon exceeds the configured interval limit")
    axis = sorted(edges)
    return tuple(
        (
            interval,
            limits,
            tuple(
                Interval(axis[index], axis[index + 1])
                for index in range(
                    bisect_left(axis, interval.start), bisect_left(axis, interval.end)
                )
            ),
        )
        for interval, limits in schedule
    )


def interpretation(
    interval: Interval,
    limits: OperatingLimits,
    profiles: dict[str, PowerSeries] | dict[str, PowerSeries | DcPvProfile],
) -> Object:
    notes: Object = {}
    for role, item in profiles.items():
        notes[role] = {
            "measurement": item.measurement,
            "source": item.source.document(),
            "effective_max_interval_seconds": item.effective_max_interval_seconds,
            "reconstructed_means": item.reconstructed_means,
            "transformations": [
                transform.document() for transform in item.transformations
            ],
        }
    return {
        "start_utc": interval.start.isoformat(),
        "end_utc": interval.end.isoformat(),
        "mode": limits.mode,
        "profiles": notes,
    }
