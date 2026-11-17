"""Procurement intent travels with the selection; physics keeps every part.

`equipment_use` records whether each primary device is new, retained or a
replacement. Retained and replaced devices keep their product identity and
join every physics and compatibility check; only the purchase list differs.
"""

from __future__ import annotations

import pytest

from linker_engine.planning.canonical import Json, Object
from linker_engine.planning.equipment_inputs import EquipmentSelection
from linker_engine.planning.equipment_plant import EquipmentPlant, matches_setup
from linker_engine.planning.errors import InvalidInput

REQUIREMENTS: Object = {
    "schema_version": 1,
    "grid_phase": 3,
    "operating_mode": "grid_connected",
    "pv_dc_kw": 10.0,
    "required_usable_kwh": 20.0,
    "required_discharge_ac_kw": 5.0,
}


def selection(**overrides: Json) -> Object:
    value: Object = {
        "schema_version": 1,
        "inverter_product_id": 2092,
        "battery_product_id": 2090,
        "modules_per_stack": 2,
        "parallel_stacks": 1,
        "accessory_product_ids": [],
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": 10.0,
        "required_usable_kwh": 20.0,
        "required_discharge_ac_kw": 5.0,
        "product_revisions": {"2092": "a" * 64, "2090": "b" * 64},
    }
    value.update(overrides)
    return value


def plant(unit_use: Object | None, controller_use: str | None) -> EquipmentPlant:
    group: Object = {
        "id": "ac",
        "unit_ids": ["a", "b"],
        "controller_product_id": 2091,
        "controller_revision": "c" * 64,
    }
    if controller_use is not None:
        group["controller_use"] = controller_use
    return EquipmentPlant.read(
        {
            "schema_version": 1,
            "requirements": REQUIREMENTS,
            "units": [
                {"id": "a", "name": "A", "selection": selection(**_use(unit_use))},
                {"id": "b", "name": "B", "selection": selection(**_use(unit_use))},
            ],
            "parallel_groups": [group],
        }
    )


def _use(unit_use: Object | None) -> Object:
    return {"equipment_use": unit_use} if unit_use is not None else {}


def setup_draft(unit_use: Object | None, controller_use: str | None) -> Object:
    group: Object = {
        "id": "ac",
        "unit_ids": ["a", "b"],
        "controller_product_id": 2091,
    }
    if controller_use is not None:
        group["controller_use"] = controller_use
    row = selection(**_use(unit_use))
    return {
        "schema_version": 1,
        "requirements": REQUIREMENTS,
        "units": [
            {"id": "a", "name": "A", "inputs": {"equipment_setup": row}},
            {"id": "b", "name": "B", "inputs": {"equipment_setup": dict(row)}},
        ],
        "parallel_groups": [group],
    }


def test_an_unanswered_equipment_use_stays_absent() -> None:
    # Retained projects keep their canonical representation: the field is
    # omitted, never written as an explicit null.
    assert "equipment_use" not in EquipmentSelection.read(selection()).model_dump(
        mode="json"
    )


def test_retain_and_replace_travel_with_the_selected_products() -> None:
    read = EquipmentSelection.read(
        selection(equipment_use={"inverter": "retain", "battery": "replace"})
    )
    dumped = read.model_dump(mode="json")
    assert dumped["equipment_use"] == {"inverter": "retain", "battery": "replace"}
    # Physics and compatibility keep every part, whatever its purchase intent.
    assert dumped["inverter_product_id"] == 2092
    assert dumped["battery_product_id"] == 2090
    assert dumped["product_revisions"] == {"2092": "a" * 64, "2090": "b" * 64}


def test_a_partial_use_plan_is_rejected() -> None:
    with pytest.raises(InvalidInput):
        EquipmentSelection.read(selection(equipment_use={"inverter": "retain"}))
    with pytest.raises(InvalidInput):
        EquipmentSelection.read(selection(equipment_use={"inverter": "keep"}))


def test_retaining_a_battery_requires_the_declared_product() -> None:
    with pytest.raises(InvalidInput):
        EquipmentSelection.read(
            selection(
                battery_product_id=None,
                product_revisions={"2092": "a" * 64},
                equipment_use={"inverter": "new", "battery": "retain"},
            )
        )
    # Without a battery nothing is retained or replaced.
    EquipmentSelection.read(
        selection(
            battery_product_id=None,
            product_revisions={"2092": "a" * 64},
            equipment_use={"inverter": "new", "battery": "new"},
        )
    )


def test_a_controller_use_needs_its_declared_controller() -> None:
    retained = plant(None, "retain")
    assert (
        retained.parallel_groups[0].model_dump(mode="json")["controller_use"]
        == "retain"
    )
    with pytest.raises(InvalidInput):
        EquipmentPlant.read(
            {
                "schema_version": 1,
                "requirements": REQUIREMENTS,
                "units": [
                    {"id": "a", "name": "A", "selection": selection()},
                    {"id": "b", "name": "B", "selection": selection()},
                ],
                "parallel_groups": [
                    {
                        "id": "ac",
                        "unit_ids": ["a", "b"],
                        "controller_product_id": None,
                        "controller_revision": None,
                        "controller_use": "replace",
                    }
                ],
            }
        )


def test_old_saved_plants_still_match_their_setup() -> None:
    # Projects saved before `equipment_use` exists carry neither the unit nor
    # the controller field; they must keep matching their prepared draft.
    assert matches_setup(plant(None, None), setup_draft(None, None))


def test_a_declared_use_must_match_on_both_sides() -> None:
    assert matches_setup(
        plant({"inverter": "retain", "battery": "new"}, "replace"),
        setup_draft({"inverter": "retain", "battery": "new"}, "replace"),
    )
    # An edited draft that drops the declared use is no longer the prepared
    # plant, exactly like any other edited hardware field.
    assert not matches_setup(
        plant({"inverter": "retain", "battery": "new"}, None),
        setup_draft(None, None),
    )
    assert not matches_setup(
        plant(None, None),
        setup_draft({"inverter": "new", "battery": "new"}, None),
    )
