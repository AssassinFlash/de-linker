"""Earlier complete-input writers cannot erase supported AC operating modes."""

import pytest

from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.project_input_contracts import require_input_contract


@pytest.mark.parametrize(
    "inputs",
    [
        {"energy_scenario": {"controller": "peak_shaving_with_reserve_v1"}},
        {"energy_scenario": {"controller": "self_consumption_with_reserve_v1"}},
        {"energy_scenario": {"aux_ac_kw": 0}},
        {"energy_plant_setup": {"controller": "proportional_peak_shaving_v1"}},
        {"energy_plant_setup": {"aux_ac_kw": 1}},
        {"energy_replay": {"controller": "peak_shaving_with_reserve_v1"}},
        {"energy_replay": {"pv_available_asset_id": None}},
        {"energy_replay": {"aux_ac_asset_id": None, "aux_ac_kw": 0}},
        {"energy_plant": {"controller": "proportional_peak_shaving_v1"}},
        {"energy_plant": {"coupling": "plant_ac", "pv_available_asset_id": None}},
        {"energy_plant": {"aux_ac_asset_id": None, "aux_ac_kw": 1}},
    ],
)
def test_operating_modes_require_a_writer_that_preserves_them(
    inputs: dict[str, object],
) -> None:
    for before, after in ((None, inputs), (inputs, inputs), (inputs, {})):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(before, after, "equipment_use_v1")
        require_input_contract(before, after, "energy_operating_modes_v1")


def test_dc_plant_reference_does_not_become_a_storage_only_mode() -> None:
    require_input_contract(
        None,
        {
            "energy_plant": {
                "coupling": "plant_shared_dc",
                "controller": "local_dc_then_proportional_ac_self_consumption_v1",
                "pv_available_asset_id": None,
                "pv_reference_asset_id": "a" * 32,
                "aux_ac_asset_id": "b" * 32,
            },
        },
        "pv_plant_string_plan_v1",
    )


def test_existing_profile_based_self_consumption_still_accepts_prior_writers() -> None:
    inputs = {
        "energy_scenario": {"schema_version": 1},
        "energy_replay": {
            "controller": "self_consumption_with_reserve_v1",
            "pv_available_asset_id": "a" * 32,
            "aux_ac_asset_id": "b" * 32,
        },
        "energy_plant": {
            "controller": "proportional_available_power_self_consumption_v1",
            "pv_available_asset_id": "a" * 32,
            "aux_ac_asset_id": "b" * 32,
        },
    }
    require_input_contract(None, inputs, "equipment_use_v1")
