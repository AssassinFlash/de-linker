"""Project observations bound to selected Woo devices, never product facts."""

from __future__ import annotations

from typing import Annotated, Literal, cast

from pydantic import Field, model_validator

from .canonical import Json, Object, encode
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count, EquipmentSelection
from .equipment_plant import EquipmentPlant, Identity, Revision
from .errors import InvalidInput

type Role = Literal["inverter", "battery", "accessory"]
# Transport limits for private observations, not device/version constraints.
type Observation = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"\S")]


class ConditionBindingChanged(InvalidInput):
    code = "equipment_condition_binding_changed"


class ConditionRevisionChanged(InvalidInput):
    code = "equipment_condition_revision_changed"


class ConditionPreparationRequired(InvalidInput):
    code = "equipment_condition_requires_preparation"


class SingleDeviceRef(Document):
    kind: Literal["single"]
    role: Role


class PlantDeviceRef(Document):
    kind: Literal["plant_unit"]
    unit_id: Identity
    role: Role


class PlantControllerRef(Document):
    kind: Literal["plant_controller"]
    group_id: Identity


type SelectionRef = Annotated[
    SingleDeviceRef | PlantDeviceRef | PlantControllerRef,
    Field(discriminator="kind"),
]


class DeviceConditionInput(Document):
    selection_ref: SelectionRef
    product_id: Count
    product_revision: Revision
    declared_model: Observation | None
    declared_firmware: Observation | None
    source_note: Observation | None


class EquipmentConditionInputs(Document):
    schema_version: SchemaVersion
    devices: list[DeviceConditionInput]

    @model_validator(mode="after")
    def distinct_devices(self) -> EquipmentConditionInputs:
        keys = [
            (encode(d.selection_ref.model_dump(mode="json")), d.product_id)
            for d in self.devices
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("each selected device needs at most one observation")
        return self


def binding_key(device: Object) -> tuple[bytes, int]:
    return encode(device["selection_ref"]), cast(int, device["product_id"])


def selected_condition_devices(
    inputs: Object, *, allow_setup: bool = False
) -> list[Object]:
    """Retain physical node identities even when nodes share a Woo product."""
    devices: list[Object] = []

    def selection_devices(selection: EquipmentSelection, reference: Object) -> None:
        for role, identities in (
            ("inverter", [selection.inverter_product_id]),
            (
                "battery",
                []
                if selection.battery_product_id is None
                else [selection.battery_product_id],
            ),
            ("accessory", selection.accessory_product_ids),
        ):
            for identity in identities:
                devices.append(
                    {
                        "selection_ref": {**reference, "role": role},
                        "product_id": identity,
                        "product_revision": selection.product_revisions[str(identity)],
                    }
                )

    if allow_setup and isinstance(inputs.get("equipment_plant_setup"), dict):
        setup = cast(Object, inputs["equipment_plant_setup"])
        units = setup.get("units")
        groups = setup.get("parallel_groups")
        if isinstance(units, list):
            for raw_unit in units:
                if not isinstance(raw_unit, dict) or not isinstance(
                    raw_unit.get("inputs"), dict
                ):
                    continue
                values = cast(Object, raw_unit["inputs"])
                add_setup_devices(
                    devices,
                    values.get("equipment_setup", values.get("equipment_selection")),
                    {"kind": "plant_unit", "unit_id": raw_unit.get("id")},
                )
        if isinstance(groups, list):
            for raw_group in groups:
                if (
                    isinstance(raw_group, dict)
                    and type(raw_group.get("controller_product_id")) is int
                ):
                    devices.append(
                        {
                            "selection_ref": {
                                "kind": "plant_controller",
                                "group_id": raw_group.get("id"),
                            },
                            "product_id": raw_group["controller_product_id"],
                            "product_revision": None,
                        }
                    )
        # A draft can retain an observation while preparation is absent. When
        # a prepared revision exists, it is still binding for that device.
        if isinstance(inputs.get("equipment_plant"), dict):
            prepared = selected_condition_devices(
                {"equipment_plant": inputs["equipment_plant"]}
            )
            revisions = {binding_key(d): d["product_revision"] for d in prepared}
            for device in devices:
                device["product_revision"] = revisions.get(binding_key(device))
    elif allow_setup and isinstance(inputs.get("equipment_setup"), dict):
        add_setup_devices(devices, inputs["equipment_setup"], {"kind": "single"})
        if isinstance(inputs.get("equipment_selection"), dict):
            prepared = selected_condition_devices(
                {"equipment_selection": inputs["equipment_selection"]}
            )
            revisions = {binding_key(d): d["product_revision"] for d in prepared}
            for device in devices:
                device["product_revision"] = revisions.get(binding_key(device))
    elif "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
        if inputs.get("equipment_plant") is None:
            return []
        plant = EquipmentPlant.from_inputs(inputs)
        for unit in plant.units:
            selection_devices(
                unit.selection, {"kind": "plant_unit", "unit_id": unit.id}
            )
        for group in plant.parallel_groups:
            if group.controller_product_id is not None:
                devices.append(
                    {
                        "selection_ref": {
                            "kind": "plant_controller",
                            "group_id": group.id,
                        },
                        "product_id": group.controller_product_id,
                        "product_revision": group.controller_revision,
                    }
                )
    elif inputs.get("equipment_selection") is not None:
        selection_devices(
            EquipmentSelection.read(inputs["equipment_selection"]), {"kind": "single"}
        )
    return devices


def add_setup_devices(devices: list[Object], setup: Json, reference: Object) -> None:
    if not isinstance(setup, dict):
        return
    accessories = setup.get("accessory_product_ids", [])
    for role, identities in (
        ("inverter", [setup.get("inverter_product_id")]),
        ("battery", [setup.get("battery_product_id")]),
        ("accessory", accessories if isinstance(accessories, list) else []),
    ):
        for identity in identities:
            if type(identity) is int and identity > 0:
                devices.append(
                    {
                        "selection_ref": {**reference, "role": role},
                        "product_id": identity,
                        "product_revision": None,
                    }
                )


def validate_condition_inputs(
    inputs: Object, *, require_prepared: bool = False
) -> EquipmentConditionInputs | None:
    """Unanswered observations save; stale or foreign selection bindings do not."""
    if "equipment_condition_inputs" not in inputs:
        return None
    observations = EquipmentConditionInputs.read(inputs["equipment_condition_inputs"])
    if (
        require_prepared
        and not isinstance(inputs.get("equipment_plant"), dict)
        and not isinstance(inputs.get("equipment_selection"), dict)
    ):
        raise ConditionPreparationRequired(
            "prepare the selected device before reviewing observations"
        )
    if require_prepared and isinstance(inputs.get("equipment_setup"), dict):
        setup = cast(Object, inputs["equipment_setup"])
        selection = EquipmentSelection.read(inputs.get("equipment_selection"))
        if {
            key: setup.get(key)
            for key in EquipmentSelection.model_fields
            if key != "product_revisions"
        } != selection.model_dump(mode="json", exclude={"product_revisions"}):
            raise ConditionPreparationRequired(
                "prepare the changed device selection before reviewing observations"
            )
    selected = {
        binding_key(d): d
        for d in selected_condition_devices(inputs, allow_setup=not require_prepared)
    }
    for observation in observations.devices:
        row = cast(Object, observation.model_dump(mode="json"))
        device = selected.get(binding_key(row))
        if device is None:
            raise ConditionBindingChanged(
                "device observation differs from the saved node or product"
            )
        if (
            device["product_revision"] is not None
            and device["product_revision"] != observation.product_revision
        ):
            raise ConditionRevisionChanged(
                "device observation refers to a different Woo revision"
            )
        if require_prepared and device["product_revision"] is None:
            raise ConditionPreparationRequired(
                "prepare the selected device before reviewing observations"
            )
    return observations
