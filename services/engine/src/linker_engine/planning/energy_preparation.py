"""Align all real profile and operating-mode boundaries for one energy run."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

from .canonical import Json, Object
from .dispatch_frame import Frame
from .energy_inputs import EnergyInputs
from .errors import InvalidInput
from .interval import Interval
from .power_series import PowerSeries
from .regrid import regrid
from .scenario_frames import scenario_frames
from .worker import Control


@dataclass(frozen=True)
class PreparedEnergy:
    frames: tuple[Frame, ...]
    profile_interpretation: Object


def prepare_energy(
    scenario: EnergyInputs,
    profiles: dict[str, PowerSeries],
    control: Control,
    *,
    max_intervals: int,
) -> PreparedEnergy:
    schedule = tuple((item.interval(), item.limits()) for item in scenario.schedule)
    for previous, current in zip(schedule, schedule[1:], strict=False):
        if previous[0].end != current[0].start:
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
    for role, profile in profiles.items():
        if profile.measurement != role:
            raise InvalidInput(f"{role}: profile measurement boundary differs")
        for interval in profile.intervals:
            if start < interval.start < end:
                edges.add(interval.start)
            if start < interval.end < end:
                edges.add(interval.end)
    if len(edges) - 1 > max_intervals:
        raise InvalidInput("aligned horizon exceeds the configured interval limit")
    axis = sorted(edges)
    frames: list[Frame] = []
    interpretations: list[Json] = []
    for interval, limits in schedule:
        control.checkpoint()
        left, right = bisect_left(axis, interval.start), bisect_left(axis, interval.end)
        target = tuple(
            Interval(axis[index], axis[index + 1]) for index in range(left, right)
        )
        load_role = "critical_load" if limits.mode == "outage" else "gross_load"
        selected = {
            role: regrid(profiles[role], target)
            for role in (load_role, "pv_available_ac", "aux_ac")
        }
        load, pv, aux = (
            selected[role] for role in (load_role, "pv_available_ac", "aux_ac")
        )
        frames.extend(scenario_frames(load, pv, aux, (limits,) * len(target)))
        profile_notes: Object = {}
        for role, item in selected.items():
            profile_notes[role] = {
                "measurement": item.measurement,
                "source": item.source.document(),
                "effective_max_interval_seconds": item.effective_max_interval_seconds,
                "reconstructed_means": item.reconstructed_means,
                "transformations": [
                    transform.document() for transform in item.transformations
                ],
            }
        interpretations.append(
            {
                "start_utc": interval.start.isoformat(),
                "end_utc": interval.end.isoformat(),
                "mode": limits.mode,
                "profiles": profile_notes,
            }
        )
    return PreparedEnergy(tuple(frames), {"operating_periods": interpretations})
