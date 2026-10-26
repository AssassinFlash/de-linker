"""An explicit plant search fixes demand and relationships, not product facts."""

from __future__ import annotations

from typing import Annotated, cast

from pydantic import Field, model_validator

from .canonical import Json, Object
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .equipment_plant import EquipmentPlant, Identity, assert_plant_exclusivity
from .equipment_requirements import EquipmentRequirements
from .errors import InvalidInput


class SearchUnit(Document):
    id: Identity
    name: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")]
    requirements: EquipmentRequirements


class SearchGroup(Document):
    id: Identity
    unit_ids: Annotated[list[Identity], Field(min_length=2)]
    # A selected controller constrains the search; null asks the Woo contract.
    controller_product_id: Count | None


class PlantSearchPlan(Document):
    schema_version: SchemaVersion
    requirements: EquipmentRequirements
    units: Annotated[list[SearchUnit], Field(min_length=1)]
    parallel_groups: list[SearchGroup]

    @model_validator(mode="after")
    def relationships(self) -> PlantSearchPlan:
        ids = {u.id for u in self.units}
        if len(ids) != len(self.units) or len(
            {g.id for g in self.parallel_groups}
        ) != len(self.parallel_groups):
            raise ValueError("plant search identities must be unique")
        used: set[str] = set()
        for group in self.parallel_groups:
            members = set(group.unit_ids)
            if (
                len(members) != len(group.unit_ids)
                or not members.issubset(ids)
                or members & used
            ):
                raise ValueError("a search system belongs to at most one known group")
            used.update(members)
        for unit in self.units:
            if (unit.requirements.grid_phase, unit.requirements.operating_mode) != (
                self.requirements.grid_phase,
                self.requirements.operating_mode,
            ):
                raise ValueError(
                    "unit search requirements must match the plant connection"
                )
        return self

    @classmethod
    def from_inputs(cls, inputs: Object) -> PlantSearchPlan:
        assert_plant_exclusivity(inputs)
        prepared = cls.read(inputs.get("equipment_plant_requirements"))
        raw = inputs.get("equipment_plant_setup")
        if not isinstance(raw, dict):
            raise InvalidInput("plant search requires an editable demand plan")
        requirements = EquipmentRequirements.read(raw.get("requirements"))
        units = raw.get("units")
        if not isinstance(units, list):
            raise InvalidInput("plant search requires named systems")
        projected: list[Json] = []
        for raw_unit in units:
            if not isinstance(raw_unit, dict) or not isinstance(
                raw_unit.get("inputs"), dict
            ):
                raise InvalidInput("plant search needs each system demand")
            unit_inputs = cast(Object, raw_unit["inputs"])
            setup = unit_inputs.get(
                "equipment_setup", unit_inputs.get("equipment_selection")
            )
            if not isinstance(setup, dict):
                raise InvalidInput("plant search needs each system demand")
            values = {key: setup.get(key) for key in EquipmentRequirements.model_fields}
            values.update(
                grid_phase=requirements.grid_phase,
                operating_mode=requirements.operating_mode,
            )
            projected.append(
                {
                    "id": raw_unit.get("id"),
                    "name": raw_unit.get("name"),
                    "requirements": values,
                }
            )
        current = cls.read(
            {
                "schema_version": raw.get("schema_version"),
                "requirements": requirements.model_dump(mode="json"),
                "units": projected,
                "parallel_groups": raw.get("parallel_groups"),
            }
        )
        if current != prepared:
            raise InvalidInput("prepare the updated multi-system search requirements")
        return prepared

    def matches_plant(self, plant: EquipmentPlant) -> bool:
        """Equipment may change; a search cannot relabel different project demand."""
        if self.requirements != plant.requirements or len(self.units) != len(
            plant.units
        ):
            return False
        for request, unit in zip(self.units, plant.units, strict=True):
            if (request.id, request.name) != (unit.id, unit.name):
                return False
            demand = EquipmentRequirements.read(
                {
                    key: getattr(unit.selection, key)
                    for key in EquipmentRequirements.model_fields
                }
            )
            if request.requirements != demand:
                return False
        return len(self.parallel_groups) == len(plant.parallel_groups) and all(
            (request.id, request.unit_ids) == (group.id, group.unit_ids)
            and request.controller_product_id in (None, group.controller_product_id)
            for request, group in zip(
                self.parallel_groups, plant.parallel_groups, strict=True
            )
        )
