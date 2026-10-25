"""Align all real profile and operating-mode boundaries for one energy run."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import Json, Object
from .dispatch_frame import Frame
from .energy_alignment import interpretation, schedule_axis
from .energy_inputs import EnergyInputs
from .errors import InvalidInput
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
    if scenario.coupling != "independent_ac":
        raise InvalidInput("AC replay requires the independent AC boundary")
    frames: list[Frame] = []
    interpretations: list[Json] = []
    for interval, limits, target in schedule_axis(
        scenario, profiles, max_intervals=max_intervals
    ):
        control.checkpoint()
        load_role = "critical_load" if limits.mode == "outage" else "gross_load"
        selected = {
            role: regrid(profiles[role], target)
            for role in (load_role, "pv_available_ac", "aux_ac")
        }
        load, pv, aux = (
            selected[role] for role in (load_role, "pv_available_ac", "aux_ac")
        )
        frames.extend(scenario_frames(load, pv, aux, (limits,) * len(target)))
        interpretations.append(interpretation(interval, limits, selected))
    return PreparedEnergy(tuple(frames), {"operating_periods": interpretations})
