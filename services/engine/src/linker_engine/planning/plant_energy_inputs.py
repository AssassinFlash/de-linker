"""A common AC meter with explicit storage states or declared PV-only operation.

PV-only plants retain their inverter and electrical evidence without storage
states. Storage-equipped plants describe separate AC PV generation and
battery-only use of each declared storage converter. Shared-DC PV uses its
actual bridge model rather than a pre-converted AC equivalent.
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
    check_pv_boundary,
    storage_only_project,
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
    gross_load_asset_id: Identifier | None
    critical_load_asset_id: Identifier | None
    pv_available_asset_id: Identifier | None
    aux_ac_asset_id: Identifier | None
    aux_ac_kw: Nonnegative | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    schedule: Annotated[list[ScheduleSegment], Field(min_length=1)]
    units: list[PlantStorageInputs]
    controller: Literal[
        "proportional_available_power_self_consumption_v1",
        "proportional_peak_shaving_v1",
    ]

    @model_validator(mode="after")
    def explicit_reserves(self) -> Self:
        if self.gross_load_asset_id is None and any(
            p.mode == "connected" for p in self.schedule
        ):
            raise ValueError("grid-connected periods require a total site load profile")
        if self.critical_load_asset_id is None and any(
            p.mode == "outage" for p in self.schedule
        ):
            raise ValueError("outage periods require a critical-load profile")
        if (self.aux_ac_asset_id is None) == (self.aux_ac_kw is None):
            raise ValueError(
                "select either an auxiliary profile or explicit constant AC auxiliary demand"
            )
        if self.controller == "proportional_peak_shaving_v1" and any(
            p.mode == "connected" and p.import_cap_kw is None for p in self.schedule
        ):
            raise ValueError("peak shaving requires a grid import limit")
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
        check_pv_boundary(inputs, scenario.pv_available_asset_id, scenario.schedule)
        if storage_only_project(inputs) and any(
            u.initial_inventory.pv_kwh != 0 for u in scenario.units
        ):
            raise InvalidInput(
                "storage-only initial inventory cannot contain PV energy"
            )
        if any(p.mode == "outage" and p.pv_enabled for p in scenario.schedule):
            raise EvidenceMissing(
                "joint outage AC PV requires an explicitly documented island bus",
                constraint_id="joint_outage_ac_pv_topology",
            )
        brief = inputs.get("brief")
        if isinstance(brief, dict) and brief.get("system_scope") == "pv_only":
            if scenario.units or any(
                unit.selection.battery_product_id is not None
                or unit.selection.modules_per_stack is not None
                or unit.selection.parallel_stacks is not None
                for unit in plant.units
            ):
                raise InvalidInput(
                    "PV-only plant replay cannot contain storage units or selected batteries"
                )
            return scenario
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
        result = {}
        if self.gross_load_asset_id is not None:
            result["gross_load"] = self.gross_load_asset_id
        if self.aux_ac_asset_id is not None:
            result["aux_ac"] = self.aux_ac_asset_id
        if self.pv_available_asset_id is not None:
            result["pv_available_ac"] = self.pv_available_asset_id
        if self.critical_load_asset_id is not None:
            result["critical_load"] = self.critical_load_asset_id
        return result
