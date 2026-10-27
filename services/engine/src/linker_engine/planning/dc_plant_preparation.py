"""One aligned real-time axis, with per-unit PV groups retaining their stages."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .canonical import Json, Object
from .dc_plant_inputs import DcPlantEnergyInputs
from .dc_plant_model import DcPlantFrame
from .dispatch_frame import Frame
from .energy_alignment import interpretation, schedule_axis
from .errors import InvalidInput
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile
from .regrid import regrid
from .worker import Control


@dataclass(frozen=True)
class PreparedDcPlant:
    frames: tuple[DcPlantFrame, ...]
    profile_interpretation: Object


def prepare(
    scenario: DcPlantEnergyInputs,
    profiles: dict[str, PowerSeries],
    dc: dict[str, DcPvProfile],
    reference_ac: PowerSeries | None,
    control: Control,
    *,
    max_intervals: int,
) -> PreparedDcPlant:
    expected = {u.unit_id for u in scenario.units if u.pv_converter_id is not None}
    if set(dc) != expected or any(
        dc[u.unit_id].converter_id != u.pv_converter_id
        for u in scenario.units
        if u.pv_converter_id is not None
    ):
        raise InvalidInput(
            "each DC unit requires its exactly assigned retained PV group"
        )
    all_profiles: dict[str, PowerSeries | DcPvProfile] = dict(profiles)
    measurements = {role: role for role in profiles}
    for uid, value in dc.items():
        key = "unit:" + uid + ":pv_available_dc"
        all_profiles[key], measurements[key] = value, "pv_available_dc"
    if reference_ac is not None:
        all_profiles["reference_ac"], measurements["reference_ac"] = (
            reference_ac,
            "pv_available_ac",
        )
    frames: list[DcPlantFrame] = []
    notes: list[Json] = []
    budget = max_intervals // len(scenario.units)
    if budget < 1:
        raise InvalidInput("DC plant device count exceeds the execution budget")
    for interval, limits, target in schedule_axis(
        scenario, all_profiles, max_intervals=budget, measurements=measurements
    ):
        control.checkpoint()
        aligned = {
            role: regrid(profile, target) for role, profile in all_profiles.items()
        }
        load_role = "critical_load" if limits.mode == "outage" else "gross_load"
        ac_roles = [
            role for role in ("pv_available_ac", "reference_ac") if role in aligned
        ]
        for i, step in enumerate(target):
            frames.append(
                DcPlantFrame(
                    Frame(
                        step,
                        aligned[load_role].values_kw[i],
                        math.fsum(aligned[role].values_kw[i] for role in ac_roles),
                        aligned["aux_ac"].values_kw[i],
                        limits,
                        "critical_load" if limits.mode == "outage" else "gross_load",
                    ),
                    {
                        u.unit_id: aligned[
                            "unit:" + u.unit_id + ":pv_available_dc"
                        ].values_kw[i]
                        if u.pv_converter_id is not None
                        else 0.0
                        for u in scenario.units
                    },
                    {u.unit_id: u.aux_dc_kw for u in scenario.units},
                    {u.unit_id: u.reserve_kwh for u in scenario.units},
                )
            )
        notes.append(
            interpretation(
                interval,
                limits,
                {
                    role: profile
                    for role, profile in aligned.items()
                    if role not in {"gross_load", "critical_load"} or role == load_role
                },
            )
        )
    return PreparedDcPlant(
        tuple(frames),
        {
            "operating_periods": notes,
            "pv_group_assignments": [
                {"unit_id": u.unit_id, "pv_converter_id": u.pv_converter_id}
                for u in scenario.units
            ],
            "ac_pv_converter_ids": list(scenario.ac_pv_converter_ids),
        },
    )
