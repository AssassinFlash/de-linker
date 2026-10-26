"""Named storage states at one AC connection, never an aggregated battery.

NUMERICAL-MODELS.md sections5–7 define the fixed-window physical model and
source accounting. Each unit has its own declared AC envelope. PV here is an
independent, already converted AC source; a hybrid's shared DC port requires
the separate DC model and must not be silently represented by this contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from .battery_model import BatteryModel, nonnegative
from .dispatch_frame import Command, Frame
from .energy_origins import EnergyOrigins
from .errors import EvidenceMissing, InvalidInput


@dataclass(frozen=True)
class StorageUnit:
    id: str
    model: BatteryModel
    outage_model: BatteryModel | None = None

    def __post_init__(self) -> None:
        if not self.id or (
            self.outage_model is not None
            and self.outage_model.usable_window_kwh != self.model.usable_window_kwh
        ):
            raise InvalidInput(
                "mode changes must preserve a unit's internal energy basis"
            )

    def for_mode(self, mode: str) -> BatteryModel:
        if mode == "connected":
            return self.model
        if mode == "outage" and self.outage_model is not None:
            return self.outage_model
        raise EvidenceMissing("plant_unit_outage_envelope:" + self.id)


@dataclass(frozen=True)
class PlantFrame:
    site: Frame
    reserves_kwh: dict[str, float]

    def __post_init__(self) -> None:
        if self.site.limits.reserve_kwh != 0:
            raise InvalidInput("plant reserves must be allocated to named units")
        for value in self.reserves_kwh.values():
            nonnegative(value, "unit energy reserve")


@dataclass(frozen=True)
class StorageFlow:
    unit: StorageUnit
    mode: str
    reserve_kwh: float
    command: Command
    before: EnergyOrigins
    after: EnergyOrigins
    standing_loss: EnergyOrigins
    internal_aux: EnergyOrigins
    internal_aux_unserved_kwh: float
    withdrawn_internal: EnergyOrigins
    delivered_ac: EnergyOrigins
    received_ac: EnergyOrigins

    @property
    def discharge_loss(self) -> EnergyOrigins:
        return self.withdrawn_internal.scaled(
            1 - self.unit.for_mode(self.mode).eta_discharge
        )

    @property
    def charge_loss(self) -> EnergyOrigins:
        return self.received_ac.scaled(1 - self.unit.for_mode(self.mode).eta_charge)


@dataclass(frozen=True)
class PlantFlow:
    frame: PlantFrame
    units: tuple[StorageFlow, ...]
    pv_available_kwh: float
    direct_pv_to_load_kwh: float
    direct_pv_to_aux_kwh: float
    direct_pv_to_charge_kwh: float
    battery_to_load_ac: EnergyOrigins
    battery_to_aux_ac: EnergyOrigins
    grid_to_load_kwh: float
    grid_to_aux_kwh: float
    load_sources: EnergyOrigins
    aux_sources: EnergyOrigins
    grid_import_kwh: float
    grid_charge_kwh: float
    export_sources: EnergyOrigins
    curtailed_sources: EnergyOrigins
    unserved_load_kwh: float
    unserved_aux_kwh: float
