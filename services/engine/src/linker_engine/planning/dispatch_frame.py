"""Input and measured-flow records for one real-time AC interval."""

from __future__ import annotations

from dataclasses import dataclass

from .battery_model import nonnegative
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .interval import Interval
from .operating_limits import OperatingLimits


@dataclass(frozen=True)
class Frame:
    interval: Interval
    load_kw: float
    pv_potential_kw: float
    aux_ac_kw: float
    limits: OperatingLimits

    def __post_init__(self) -> None:
        for name in ("load_kw", "pv_potential_kw", "aux_ac_kw"):
            nonnegative(getattr(self, name), name)


@dataclass(frozen=True)
class Command:
    charge_kw: float
    discharge_kw: float

    def __post_init__(self) -> None:
        nonnegative(self.charge_kw, "charge command")
        nonnegative(self.discharge_kw, "discharge command")
        if self.charge_kw and self.discharge_kw:
            raise InvalidInput(
                "one device cannot be commanded to charge and discharge together"
            )


@dataclass(frozen=True)
class Flows:
    frame: Frame
    command: Command
    before: EnergyOrigins
    after: EnergyOrigins
    standing_loss: EnergyOrigins
    internal_aux: EnergyOrigins
    internal_aux_unserved_kwh: float
    discharged_internal: EnergyOrigins
    discharged_to_load_ac: EnergyOrigins
    pv_available_kw: float
    pv_to_load_kw: float
    pv_to_aux_kw: float
    pv_charge_kw: float
    grid_charge_kw: float
    discharge_kw: float
    charge_kw: float
    grid_to_load_kw: float
    grid_to_aux_kw: float
    import_kw: float
    export_kw: float
    curtailed_kw: float
    unserved_load_kw: float
    unserved_aux_kw: float
    charge_command_unmet_kw: float
    discharge_command_unmet_kw: float

    @property
    def served_load_kw(self) -> float:
        return self.frame.load_kw - self.unserved_load_kw

    @property
    def served_aux_kw(self) -> float:
        return self.frame.aux_ac_kw - self.unserved_aux_kw
