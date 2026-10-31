"""Project wiring choices refer to real roof objects, never device limits."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .geometry_documents import Identifier


class PvString(Document):
    id: Identifier
    mppt: Count
    input: Count
    module_ids: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1)
    ]


class PvOperatingConditions(Document):
    irradiance_w_m2: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None
    hot_cell_c: Annotated[float, Field(ge=-273.15, allow_inf_nan=False)] | None
    cold_cell_c: Annotated[float, Field(ge=-273.15, allow_inf_nan=False)] | None
    source_note: Annotated[str, Field(min_length=1, max_length=4096)] | None


class PvStringPlan(Document):
    schema_version: SchemaVersion
    inverter_product_id: Count
    # Absolute zero is a physical input boundary, not a location default.
    minimum_ambient_c: Annotated[float, Field(ge=-273.15, allow_inf_nan=False)] | None
    temperature_source: Annotated[str, Field(min_length=1, max_length=4096)] | None
    strings: list[PvString]
    operating_conditions: PvOperatingConditions | None = None

    @model_validator(mode="after")
    def unique_connections(self) -> Self:
        ids = [item.id for item in self.strings]
        ports = [(item.mppt, item.input) for item in self.strings]
        modules = [mid for item in self.strings for mid in item.module_ids]
        if any(len(rows) != len(set(rows)) for rows in (ids, ports, modules)):
            raise ValueError(
                "strings, physical inputs and assigned modules must be unique"
            )
        return self


class PvPlantStringUnit(Document):
    unit_id: Identifier
    inverter_instance_id: Identifier | None
    plan: PvStringPlan


class PvPlantStringPlan(Document):
    schema_version: SchemaVersion
    units: Annotated[list[PvPlantStringUnit], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_plant_assignments(self) -> Self:
        identities = [unit.unit_id for unit in self.units]
        strings = [string.id for unit in self.units for string in unit.plan.strings]
        modules = [
            mid
            for unit in self.units
            for string in unit.plan.strings
            for mid in string.module_ids
        ]
        instances = [
            unit.inverter_instance_id
            for unit in self.units
            if unit.inverter_instance_id is not None
        ]
        if any(
            len(rows) != len(set(rows))
            for rows in (identities, strings, modules, instances)
        ):
            raise ValueError(
                "plant units, strings, assigned modules and bound inverter instances must be unique"
            )
        return self

    @classmethod
    def from_inputs(cls, inputs: Object) -> Self:
        from .equipment_plant import EquipmentPlant
        from .errors import InvalidInput

        if inputs.get("pv_string_plan") is not None:
            raise InvalidInput(
                "single-system and plant PV string plans are mutually exclusive"
            )
        plant = EquipmentPlant.from_inputs(inputs)
        value = cls.read(inputs.get("pv_plant_string_plan"))
        units = {unit.id: unit for unit in plant.units}
        for unit in value.units:
            if unit.unit_id not in units:
                raise InvalidInput(
                    "plant PV strings refer to an unknown equipment unit"
                )
            if (
                unit.plan.inverter_product_id
                != units[unit.unit_id].selection.inverter_product_id
            ):
                raise InvalidInput(
                    "plant PV strings belong to a different inverter selection"
                )
        return value


def plant_instance_statuses(inputs: Object, plan: PvPlantStringPlan) -> dict[str, str]:
    """Review declared physical identities without inferring one from a product."""
    from .equipment_plant import EquipmentPlant
    from .installation_inputs import InstallationInputs

    plant = (
        EquipmentPlant.read(inputs["equipment_plant"])
        if inputs.get("equipment_plant") is not None
        else None
    )
    units = {unit.id: unit for unit in plant.units} if plant else {}
    installation = (
        InstallationInputs.read(inputs["installation"])
        if inputs.get("installation") is not None
        else None
    )
    instances = (
        {item.id: item for item in installation.instances} if installation else {}
    )
    result = {}
    for unit in plan.units:
        instance = (
            instances.get(unit.inverter_instance_id)
            if unit.inverter_instance_id
            else None
        )
        if plant is None:
            result[unit.unit_id] = "unprepared_plant"
            continue
        plant_unit = units.get(unit.unit_id)
        if plant_unit is None:
            result[unit.unit_id] = "unknown_unit"
            continue
        selection = plant_unit.selection
        result[unit.unit_id] = (
            "plan_product_mismatch"
            if unit.plan.inverter_product_id != selection.inverter_product_id
            else "not_recorded"
            if unit.inverter_instance_id is None
            else "stale_instance"
            if instance is None
            else "product_mismatch"
            if instance.product_id != selection.inverter_product_id
            else "revision_mismatch"
            if instance.product_revision
            != selection.product_revisions.get(str(selection.inverter_product_id))
            else "declared"
        )
    return result


def plant_instance_projection(inputs: Object) -> list[Object]:
    """PV electrical work depends on bound identities, not cable or route edits."""
    plan = PvPlantStringPlan.read(inputs.get("pv_plant_string_plan"))
    saved = inputs.get("installation")
    instances = saved.get("instances", []) if isinstance(saved, dict) else []
    rows = (
        {row["id"]: row for row in instances if isinstance(row, dict)}
        if isinstance(instances, list)
        else {}
    )
    result: list[Object] = []
    for unit in plan.units:
        if unit.inverter_instance_id is None:
            continue
        instance = rows.get(unit.inverter_instance_id)
        result.append(
            {
                "unit_id": unit.unit_id,
                "instance_id": unit.inverter_instance_id,
                "identity": {
                    key: instance.get(key)
                    for key in ("product_id", "product_revision", "source_id")
                }
                if instance
                else None,
            }
        )
    return result
