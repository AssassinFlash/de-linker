"""Align all real profile and operating-mode boundaries for one energy run."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import Json, Object, digest, encode
from .dispatch_frame import Frame
from .energy_alignment import interpretation, schedule_axis
from .energy_inputs import EnergyInputs
from .errors import InvalidInput
from .plant_energy_inputs import PlantEnergyInputs
from .power_series import Measurement, PowerSeries
from .regrid import regrid
from .scenario_frames import scenario_frames
from .series_source import SeriesSource
from .worker import Control


@dataclass(frozen=True)
class PreparedEnergy:
    frames: tuple[Frame, ...]
    profile_interpretation: Object


def prepare_energy(
    scenario: EnergyInputs | PlantEnergyInputs,
    profiles: dict[str, PowerSeries],
    control: Control,
    *,
    max_intervals: int,
) -> PreparedEnergy:
    if scenario.coupling not in {"independent_ac", "plant_ac"}:
        raise InvalidInput("AC replay requires the independent AC boundary")
    declarations: dict[Measurement, tuple[float, str]] = {}
    if scenario.pv_available_asset_id is None:
        declarations["pv_available_ac"] = (0.0, "pv_disabled_for_entire_schedule")
    if scenario.aux_ac_kw is not None:
        declarations["aux_ac"] = (
            scenario.aux_ac_kw,
            "user_declared_constant_auxiliary_demand",
        )
    profiles = dict(profiles)
    for role, (power, basis) in declarations.items():
        # Constants are explicit physical inputs, not missing observations filled
        # from a neighbouring profile. Retain their own declaration in the result.
        intervals = tuple(period.interval() for period in scenario.schedule)
        declaration = encode({"basis": basis, "power_kw": power})
        profiles[role] = PowerSeries(
            intervals,
            (power,) * len(intervals),
            role,
            SeriesSource(
                digest(declaration),
                "modelled",
                "UTC",
                max(i.hours * 3600 for i in intervals),
                declaration,
            ),
        )
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
