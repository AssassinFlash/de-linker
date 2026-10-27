"""A common AC meter and explicit, separately owned storage unit inputs.

This contract describes separate AC PV generation and battery-only use of
each declared storage converter. Shared-DC PV must use its actual bridge
model rather than smuggling pre-converted PV into a battery-only equivalent.
"""

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


class PlantStorageInputs(Document):
    unit_id: Identity
    battery_parameters_asset_id: Identifier
    initial_inventory: InitialInventory
    reserve_kwh: Nonnegative
    terminal_min_kwh: Nonnegative | None
    pv_dc_input_unused: Annotated[bool, Field(json_schema_extra={"const": True})]

    @model_validator(mode="after")
    def separate_ac_boundary(self) -> Self:
        if self.pv_dc_input_unused is not True:
            raise ValueError(
                "the AC storage equivalent requires explicitly unused DC PV inputs"
            )
        return self


class PlantEnergyInputs(Document):
    schema_version: SchemaVersion
    coupling: Literal["plant_ac"]
    gross_load_asset_id: Identifier
    critical_load_asset_id: Identifier | None
    pv_available_asset_id: Identifier
    aux_ac_asset_id: Identifier
    schedule: Annotated[list[ScheduleSegment], Field(min_length=1)]
    units: Annotated[list[PlantStorageInputs], Field(min_length=1)]
    controller: Literal["proportional_available_power_self_consumption_v1"]

    @model_validator(mode="after")
    def explicit_reserves(self) -> Self:
        if len({unit.unit_id for unit in self.units}) != len(self.units):
            raise ValueError("each storage instance needs its own state")
        if any(period.reserve_kwh != 0 for period in self.schedule):
            raise ValueError(
                "allocate the reserve to each unit; no global battery reserve is applied"
            )
        return self

    @classmethod
    def from_project(cls, inputs: Object) -> Self:
        plant = EquipmentPlant.from_inputs(inputs)
        scenario = cls.read(inputs.get("energy_plant"))
        if any(p.mode == "outage" and p.pv_enabled for p in scenario.schedule):
            raise EvidenceMissing(
                "joint outage AC PV requires an explicitly documented island bus",
                constraint_id="joint_outage_ac_pv_topology",
            )
        if {u.unit_id for u in scenario.units} != {u.id for u in plant.units}:
            raise InvalidInput(
                "the energy scenario must reference every prepared plant unit"
            )
        if plant.requirements.pv_dc_kw != 0 or any(
            unit.selection.pv_dc_kw != 0 for unit in plant.units
        ):
            raise InvalidInput(
                "separate-AC plant replay requires an explicit zero DC PV allocation at each storage converter"
            )
        return scenario

    def profiles(self) -> dict[str, str]:
        result = {
            "gross_load": self.gross_load_asset_id,
            "pv_available_ac": self.pv_available_asset_id,
            "aux_ac": self.aux_ac_asset_id,
        }
        if self.critical_load_asset_id is not None:
            result["critical_load"] = self.critical_load_asset_id
        return result
