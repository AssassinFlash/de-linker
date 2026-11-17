"""Complete-input writers must preserve declared retained/replacement devices."""

import pytest

from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.project_input_contracts import (
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
)


@pytest.mark.parametrize(
    "inputs",
    [
        {
            "equipment_setup": {
                "equipment_use": {"inverter": "retain", "battery": "new"}
            }
        },
        {
            "equipment_selection": {
                "equipment_use": {"inverter": "new", "battery": "replace"}
            }
        },
        {
            "equipment_plant": {
                "units": [
                    {
                        "selection": {
                            "equipment_use": {"inverter": "retain", "battery": "new"}
                        }
                    }
                ]
            }
        },
        {
            "equipment_plant_setup": {
                "units": [
                    {
                        "inputs": {
                            "equipment_setup": {
                                "equipment_use": {
                                    "inverter": "retain",
                                    "battery": "new",
                                }
                            }
                        }
                    }
                ]
            }
        },
        {"equipment_plant": {"parallel_groups": [{"controller_use": "retain"}]}},
        {"equipment_plant_setup": {"parallel_groups": [{"controller_use": "replace"}]}},
    ],
)
def test_prior_editors_cannot_add_preserve_or_remove_device_use(
    inputs: dict[str, object],
) -> None:
    for before, after in ((None, inputs), (inputs, inputs), (inputs, {})):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(before, after, "storage_only_brief_v1")
        require_input_contract(before, after, SUPPORTED_INPUT_CONTRACTS[-1])


def test_untouched_legacy_selection_needs_no_device_use_contract() -> None:
    require_input_contract(None, {"equipment_setup": {"equipment_use": None}}, None)
    require_input_contract(
        None, {"equipment_plant": {"units": [], "parallel_groups": []}}, None
    )
