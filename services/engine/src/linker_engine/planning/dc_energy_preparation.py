"""Align native DC PV artifacts and AC load profiles without changing stages."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import Json, Object
from .dc_frame import DcFrame
from .energy_alignment import interpretation, schedule_axis
from .energy_inputs import EnergyInputs
from .errors import InvalidInput
from .power_series import PowerSeries
from .pv_dc_profile import DcPvProfile
from .regrid import regrid
from .worker import Control


@dataclass(frozen=True)
class PreparedDcEnergy:
    frames: tuple[DcFrame, ...]
    profile_interpretation: Object


def prepare_dc_energy(
    scenario: EnergyInputs,
    profiles: dict[str, PowerSeries | DcPvProfile],
    control: Control,
    *,
    max_intervals: int,
) -> PreparedDcEnergy:
    pv = profiles.get("pv_available_dc")
    if (
        scenario.coupling != "shared_dc"
        or not isinstance(pv, DcPvProfile)
        or scenario.aux_dc_kw is None
        or pv.converter_id != scenario.pv_converter_id
    ):
        raise InvalidInput(
            "shared DC requires its explicitly selected, typed converter profile"
        )
    frames: list[DcFrame] = []
    notes: list[Json] = []
    for interval, limits, target in schedule_axis(
        scenario, profiles, max_intervals=max_intervals
    ):
        control.checkpoint()
        role = "critical_load" if limits.mode == "outage" else "gross_load"
        load, aux = profiles[role], profiles["aux_ac"]
        if not isinstance(load, PowerSeries) or not isinstance(aux, PowerSeries):
            raise InvalidInput(
                "DC replay requires AC customer and auxiliary demand profiles"
            )
        aligned_load, aligned_aux, aligned_pv = (
            regrid(load, target),
            regrid(aux, target),
            regrid(pv, target),
        )
        for index, step in enumerate(target):
            frames.append(
                DcFrame(
                    step,
                    aligned_load.values_kw[index],
                    aligned_pv.values_kw[index],
                    aligned_aux.values_kw[index],
                    scenario.aux_dc_kw,
                    limits,
                    "critical_load" if limits.mode == "outage" else "gross_load",
                )
            )
        notes.append(
            interpretation(
                interval,
                limits,
                {
                    role: aligned_load,
                    "aux_ac": aligned_aux,
                    "pv_available_dc": aligned_pv,
                },
            )
        )
    return PreparedDcEnergy(tuple(frames), {"operating_periods": notes})
