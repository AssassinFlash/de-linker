from pathlib import Path

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.project_input_contracts import (
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
    required_contracts,
)
from linker_engine.planning.project_input_floor import check_project_input_contracts
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace


@pytest.mark.parametrize(
    "inputs",
    [
        {"known_panel_details": {"count": 2}},
        {"geometry": {"module_specs": [{"electrical": {"voc_v": 40}}]}},
        {
            "installation": {
                "materials": [
                    {
                        "mounting_quantity_basis": {
                            "module": {
                                "electrical": {"cell_technology": "polycrystalline"}
                            }
                        }
                    }
                ]
            }
        },
    ],
)
def test_old_editors_cannot_overwrite_panel_data(inputs: dict[str, object]) -> None:
    assert "project_panel_parameters_v1" in required_contracts(inputs)
    for before, after in ((None, inputs), (inputs, inputs), (inputs, {})):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(before, after, "existing_system_v1")
        require_input_contract(before, after, SUPPORTED_INPUT_CONTRACTS[-1])


@pytest.mark.parametrize("electrical", [None, {}, {"voc_v": None}])
@pytest.mark.parametrize("saved_mounting", [True, False])
def test_present_electrical_key_requires_a_reader_that_knows_the_field(
    electrical: object, saved_mounting: bool
) -> None:
    module = {"electrical": electrical}
    inputs = (
        {
            "installation": {
                "materials": [{"mounting_quantity_basis": {"module": module}}]
            }
        }
        if saved_mounting
        else {"geometry": {"module_specs": [module]}}
    )
    assert "project_panel_parameters_v1" in required_contracts(inputs)
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(inputs, {}, "existing_system_v1")


def test_existing_layout_and_empty_panel_values_keep_their_editor_floor() -> None:
    cases: list[dict[str, object]] = [
        {"geometry": {"module_specs": [{"stc_power_w": 420}]}},
        {"known_panel_details": {"count": None, "power_w": None, "system_kwp": None}},
    ]
    for inputs in cases:
        assert "project_panel_parameters_v1" not in required_contracts(inputs)


def test_saved_panel_data_survives_old_write_and_requires_supported_rollback(
    workspace: Workspace,
    owner: Actor,
    tmp_path: Path,
) -> None:
    inputs: Object = {"known_panel_details": {"count": 4, "power_w": 430}}
    writer = "project_panel_parameters_v1"
    saved = workspace.create(
        owner, "Roof survey", inputs, key="create-panels", input_contract=writer
    )
    with pytest.raises(ProjectInputContractRequired):
        workspace.revise(
            owner,
            saved.id,
            saved.revision,
            {},
            key="old-editor",
            input_contract="existing_system_v1",
        )
    assert workspace.get(owner, saved.id).inputs == inputs
    revised = workspace.revise(
        owner, saved.id, saved.revision, {}, key="clear-panels", input_contract=writer
    )
    assert revised.inputs == {}
    assert workspace.get(owner, saved.id, revision=1).inputs == inputs
    storage = tmp_path / "private"
    with pytest.raises(ValueError, match="does not support retained"):
        check_project_input_contracts(
            storage,
            list(SUPPORTED_INPUT_CONTRACTS[: SUPPORTED_INPUT_CONTRACTS.index(writer)]),
        )
    assert check_project_input_contracts(storage, list(SUPPORTED_INPUT_CONTRACTS))[
        "required_input_contracts"
    ] == [writer]


def test_requested_quantities_cannot_be_erased_by_an_older_editor() -> None:
    inputs: Object = {
        "inquiry_quantities": {"42": {"planned_purchase": 1, "requested": 2}}
    }
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(inputs, {}, "project_panel_parameters_v1")
    require_input_contract(inputs, {}, "inquiry_quantities_v1")
