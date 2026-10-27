"""Distinct shared-DC converters connected to one common AC metering point."""

from __future__ import annotations

from dataclasses import dataclass

from .battery_model import nonnegative
from .dc_battery_model import DcBatteryModel
from .dc_port import DcPortFlow
from .dispatch_frame import Frame
from .energy_origins import EnergyOrigins
from .errors import InvalidInput


@dataclass(frozen=True)
class DcPlantUnit:
    id: str
    model: DcBatteryModel
    allow_ac_charge: bool

    def __post_init__(self) -> None:
        if not self.id or type(self.allow_ac_charge) is not bool:
            raise InvalidInput(
                "a named converter and explicit AC charging choice are required"
            )


@dataclass(frozen=True)
class DcPlantFrame:
    site: Frame
    pv_dc_kw: dict[str, float]
    aux_dc_kw: dict[str, float]
    reserves_kwh: dict[str, float]

    def __post_init__(self) -> None:
        if self.site.limits.reserve_kwh != 0:
            raise InvalidInput("allocate DC plant reserves to individual units")
        if set(self.pv_dc_kw) != set(self.aux_dc_kw) or set(self.pv_dc_kw) != set(
            self.reserves_kwh
        ):
            raise InvalidInput(
                "each DC unit requires its own PV, auxiliary and reserve boundary"
            )
        if (
            self.site.limits.mode == "outage"
            and self.site.load_measurement != "critical_load"
        ):
            raise InvalidInput(
                "outage calculation requires an explicit critical AC load"
            )
        for values in (self.pv_dc_kw, self.aux_dc_kw, self.reserves_kwh):
            for value in values.values():
                nonnegative(value, "per-unit DC boundary")


@dataclass(frozen=True)
class DcPlantStorageFlow:
    unit: DcPlantUnit
    port: DcPortFlow

    @property
    def delivered_ac(self) -> EnergyOrigins:
        p = self.port.plan
        return p.battery_forward_ac.plus(
            EnergyOrigins(p.pv_forward_ac_kw * p.frame.interval.hours, 0, 0)
        )


@dataclass(frozen=True)
class DcPlantFlow:
    frame: DcPlantFrame
    units: tuple[DcPlantStorageFlow, ...]
    independent_pv_available_kwh: float
    independent_pv_curtailed_kwh: float
    load_sources: EnergyOrigins
    aux_sources: EnergyOrigins
    battery_to_load_ac: EnergyOrigins
    battery_to_aux_ac: EnergyOrigins
    direct_pv_to_load_kwh: float
    direct_pv_to_aux_kwh: float
    grid_to_load_kwh: float
    grid_to_aux_kwh: float
    grid_to_dc_aux_kwh: float
    grid_charge_kwh: float
    grid_import_kwh: float
    export_sources: EnergyOrigins
    unallocated_sources: EnergyOrigins
    unserved_load_kwh: float
    unserved_aux_kwh: float
