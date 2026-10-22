"""The typed measurement boundary between aligned profiles and AC replay."""

from __future__ import annotations

from .dispatch_frame import Frame
from .errors import InvalidInput
from .operating_limits import OperatingLimits
from .power_series import PowerSeries


def scenario_frames(
    load: PowerSeries,
    pv: PowerSeries,
    aux: PowerSeries,
    limits: tuple[OperatingLimits, ...],
) -> tuple[Frame, ...]:
    if load.measurement not in ("gross_load", "critical_load"):
        raise InvalidInput("gross/critical load required; net import cannot substitute")
    if pv.measurement != "pv_available_ac" or aux.measurement != "aux_ac":
        raise InvalidInput(
            "modeled available AC PV and separate system auxiliary power required"
        )
    if (
        load.intervals != pv.intervals
        or load.intervals != aux.intervals
        or len(limits) != len(load.intervals)
    ):
        raise InvalidInput(
            "profiles and mode schedule must share the exact interval axis"
        )
    return tuple(
        Frame(interval, power, solar, auxiliary, conditions)
        for interval, power, solar, auxiliary, conditions in zip(
            load.intervals,
            load.values_kw,
            pv.values_kw,
            aux.values_kw,
            limits,
            strict=True,
        )
    )
