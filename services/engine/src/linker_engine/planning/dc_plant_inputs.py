"""Explicit assignment of retained PV conversion groups to named Woo units."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import (
    Document,
    Identifier,
    InitialInventory,
    Nonnegative,
    ScheduleSegment,
    SchemaVersion,
)
from .equipment_plant import EquipmentPlant, Identity
from .errors import EvidenceMissing, InvalidInput


class DcPlantStorageInputs(Document):
    unit_id: Identity
    battery_parameters_asset_id: Identifier
    initial_inventory: InitialInventory
    reserve_kwh: Nonnegative
    terminal_min_kwh: Nonnegative | None
    pv_converter_id: Identifier | None
    aux_dc_kw: Nonnegative
    allow_ac_charge: bool


class DcPlantEnergyInputs(Document):
    schema_version: SchemaVersion
    coupling: Literal["plant_shared_dc"]
    gross_load_asset_id: Identifier
    critical_load_asset_id: Identifier | None
    pv_available_asset_id: Identifier | None
    pv_reference_asset_id: Identifier | None
    ac_pv_converter_ids: list[Identifier]
    aux_ac_asset_id: Identifier
    schedule: Annotated[list[ScheduleSegment], Field(min_length=1)]
    units: Annotated[list[DcPlantStorageInputs], Field(min_length=1)]
    controller: Literal["local_dc_then_proportional_ac_self_consumption_v1"]

    @model_validator(mode="after")
    def assignments(self) -> Self:
        dc = [u.pv_converter_id for u in self.units if u.pv_converter_id is not None]
        groups = [*dc, *self.ac_pv_converter_ids]
        if len({u.unit_id for u in self.units}) != len(self.units) or len(
            set(groups)
        ) != len(groups):
            raise ValueError(
                "each storage unit and PV conversion group must be assigned exactly once"
            )
        if bool(groups) != (self.pv_reference_asset_id is not None):
            raise ValueError(
                "assigned PV groups require their explicit retained reference source"
            )
        if any(p.reserve_kwh != 0 for p in self.schedule):
            raise ValueError(
                "allocate reserves to named units rather than a summed battery"
            )
        return self

    @classmethod
    def from_project(cls, inputs: Object) -> Self:
        scenario, plant = (
            cls.read(inputs.get("energy_plant")),
            EquipmentPlant.from_inputs(inputs),
        )
        if {u.unit_id for u in scenario.units} != {u.id for u in plant.units}:
            raise InvalidInput(
                "the DC energy scenario must include every prepared plant unit"
            )
        selections = {u.id: u.selection for u in plant.units}
        for unit in scenario.units:
            if selections[unit.unit_id].pv_dc_kw is None:
                raise InvalidInput(
                    "each converter requires an explicit DC PV nameplate allocation"
                )
            if unit.pv_converter_id is None and selections[unit.unit_id].pv_dc_kw != 0:
                raise InvalidInput(
                    "a converter with allocated DC PV requires its actual PV group"
                )
        # A collection of documented single-device backup ratings does not
        # establish an interconnected island. Retain this explicit full-goal
        # gap instead of summing incompatible grid-forming output ratings.
        if any(p.mode == "outage" for p in scenario.schedule):
            raise EvidenceMissing(
                "multi-converter island operation needs its documented connection and control arrangement",
                constraint_id="joint_outage_dc_topology",
            )
        return scenario

    def profiles(self) -> dict[str, str]:
        result = {
            "gross_load": self.gross_load_asset_id,
            "aux_ac": self.aux_ac_asset_id,
        }
        if self.critical_load_asset_id is not None:
            result["critical_load"] = self.critical_load_asset_id
        if self.pv_available_asset_id is not None:
            result["pv_available_ac"] = self.pv_available_asset_id
        return result
