"""A plant contains distinct converter/battery systems and explicit AC groups.

Each converter keeps its own battery assembly. A shared controller never makes
those batteries a shared DC bank or establishes a common backup supply.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count, EquipmentSelection
from .equipment_requirements import EquipmentRequirements
from .errors import InvalidInput

type Identity = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
type Revision = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
type ControlNetwork = Literal["lan", "rs485"]


class PlantUnit(Document):
    id: Identity
    name: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")]
    selection: EquipmentSelection


class ParallelGroup(Document):
    id: Identity
    unit_ids: Annotated[list[Identity], Field(min_length=2)]
    controller_product_id: Count | None
    controller_revision: Revision | None
    # Omit an unanswered new field so retained projects/candidates keep their
    # original canonical representation and immutable assessment references.
    control_network: ControlNetwork | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def distinct_members(self) -> ParallelGroup:
        if len(self.unit_ids) != len(set(self.unit_ids)):
            raise ValueError("a parallel group cannot repeat a converter")
        if (self.controller_product_id is None) != (self.controller_revision is None):
            raise ValueError("a controller needs its current Woo product revision")
        return self


class PlantPreparationRequired(InvalidInput):
    code = "equipment_plant_requires_preparation"


def assert_plant_exclusivity(inputs: Object) -> None:
    """Editable and prepared plants both replace the single-system context."""
    if not {"equipment_plant", "equipment_plant_setup"}.intersection(inputs):
        return
    if any(
        inputs.get(key) is not None for key in ("equipment_selection", "pv_string_plan")
    ):
        raise InvalidInput(
            "a plant cannot reuse a single-converter selection or wiring result"
        )


def matches_setup(plant: EquipmentPlant, setup: Object) -> bool:
    """An editable draft cannot silently evaluate an older prepared plant."""
    if setup.get("schema_version") != 1 or setup.get(
        "requirements"
    ) != plant.requirements.model_dump(mode="json"):
        return False
    units = setup.get("units")
    groups = setup.get("parallel_groups")
    if (
        not isinstance(units, list)
        or len(units) != len(plant.units)
        or not isinstance(groups, list)
    ):
        return False
    for raw, unit in zip(units, plant.units, strict=True):
        if (
            not isinstance(raw, dict)
            or raw.get("id") != unit.id
            or raw.get("name") != unit.name
        ):
            return False
        inputs = raw.get("inputs")
        if not isinstance(inputs, dict):
            return False
        selection = inputs.get("equipment_setup", inputs.get("equipment_selection"))
        if not isinstance(selection, dict):
            return False
        actual = {
            key: selection.get(key)
            for key in EquipmentSelection.model_fields
            if key != "product_revisions"
        }
        actual.update(
            grid_phase=plant.requirements.grid_phase,
            operating_mode=plant.requirements.operating_mode,
        )
        if actual != unit.selection.model_dump(
            mode="json", exclude={"product_revisions"}
        ):
            return False
    return groups == [
        g.model_dump(mode="json", exclude={"controller_revision"})
        for g in plant.parallel_groups
    ]


class EquipmentPlant(Document):
    schema_version: SchemaVersion
    requirements: EquipmentRequirements
    units: Annotated[list[PlantUnit], Field(min_length=1)]
    parallel_groups: list[ParallelGroup]

    @model_validator(mode="after")
    def distinct_systems(self) -> EquipmentPlant:
        ids = {u.id for u in self.units}
        if len(ids) != len(self.units):
            raise ValueError("plant converter identities must be unique")
        if len({g.id for g in self.parallel_groups}) != len(self.parallel_groups):
            raise ValueError("parallel group identities must be unique")
        used: set[str] = set()
        controllers: set[int] = set()
        revisions: dict[str, str] = {}
        for group in self.parallel_groups:
            members = set(group.unit_ids)
            if not members.issubset(ids) or members & used:
                raise ValueError("a converter must belong to at most one known group")
            used.update(members)
            if group.controller_product_id is not None:
                controllers.add(group.controller_product_id)
                assert group.controller_revision is not None
                revisions[str(group.controller_product_id)] = group.controller_revision
        for unit in self.units:
            if controllers & {int(k) for k in unit.selection.product_revisions}:
                raise ValueError("a shared controller cannot also be a unit device")
            for key, revision in unit.selection.product_revisions.items():
                if key in revisions and revisions[key] != revision:
                    raise ValueError("a plant must use one Woo revision per product")
                revisions[key] = revision
        for group in self.parallel_groups:
            if (
                group.controller_product_id is not None
                and revisions[str(group.controller_product_id)]
                != group.controller_revision
            ):
                raise ValueError("a plant must use one Woo revision per product")
        return self

    @classmethod
    def from_inputs(cls, inputs: Object) -> EquipmentPlant:
        assert_plant_exclusivity(inputs)
        if inputs.get("equipment_plant") is None and "equipment_plant_setup" in inputs:
            raise PlantPreparationRequired("prepare the updated multi-system plan")
        plant = cls.read(inputs.get("equipment_plant"))
        setup = inputs.get("equipment_plant_setup")
        if "equipment_plant_setup" in inputs and (
            not isinstance(setup, dict) or not matches_setup(plant, setup)
        ):
            raise PlantPreparationRequired("prepare the updated multi-system plan")
        return plant
