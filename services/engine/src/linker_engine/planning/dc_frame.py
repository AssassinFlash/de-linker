"""Typed DC-bus inputs and separately metered terminal/bus/AC flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .battery_model import nonnegative
from .dispatch_frame import Command
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .interval import Interval
from .operating_limits import OperatingLimits


@dataclass(frozen=True)
class DcFrame:
    interval: Interval
    load_kw: float
    pv_available_dc_kw: float
    aux_ac_kw: float
    aux_dc_kw: float
    limits: OperatingLimits
    load_measurement: Literal["gross_load", "critical_load"]

    def __post_init__(self) -> None:
        if self.load_measurement not in ("gross_load", "critical_load"):
            raise InvalidInput("explicit gross/critical AC load boundary required")
        if self.limits.mode == "outage" and self.load_measurement != "critical_load":
            raise InvalidInput("outage DC replay requires an explicit critical AC load")
        for name in ("load_kw", "pv_available_dc_kw", "aux_ac_kw", "aux_dc_kw"):
            nonnegative(getattr(self, name), name)


@dataclass(frozen=True)
class DcFlows:
    frame: DcFrame
    command: Command
    before: EnergyOrigins
    after: EnergyOrigins
    standing_loss: EnergyOrigins
    internal_aux: EnergyOrigins
    internal_aux_unserved_kwh: float
    discharged_internal: EnergyOrigins
    discharged_to_load_ac: EnergyOrigins
    pv_available_dc_kw: float
    pv_input_curtailed_dc_kw: float
    pv_to_aux_dc_kw: float
    pv_charge_bus_dc_kw: float
    pv_to_inverter_dc_kw: float
    pv_curtailed_dc_kw: float
    battery_to_aux_dc_kw: float
    battery_to_inverter_dc_kw: float
    grid_to_aux_dc_kw: float
    grid_charge_bus_dc_kw: float
    charge_terminal_dc_kw: float
    discharge_terminal_dc_kw: float
    inverter_forward_dc_kw: float
    inverter_forward_ac_kw: float
    inverter_reverse_dc_kw: float
    inverter_reverse_ac_kw: float
    pv_to_load_ac_kw: float
    pv_to_aux_ac_kw: float
    battery_to_aux_ac_kw: float
    grid_to_load_ac_kw: float
    grid_to_aux_ac_kw: float
    import_ac_kw: float
    export_ac_kw: float
    unserved_load_ac_kw: float
    unserved_aux_ac_kw: float
    unserved_aux_dc_kw: float
    charge_command_unmet_dc_kw: float
    discharge_command_unmet_dc_kw: float
