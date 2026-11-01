"""Explicit complete-input writers; omitted metadata keeps legacy command hashes.

Import-time dependencies stay in the standard library so the native read-only
deployment probe can use the same retained-feature detector without a workspace.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .canonical import Object

type InputContract = Literal[
    "installation_circuit_electrical_v1",
    "pv_plant_string_plan_v1",
    "installation_pv_string_links_v1",
    "pv_string_links_direct_beam_visibility_v1",
    "pv_string_links_direct_beam_geometric_pv_v1",
    "grid_connection_evidence_v1",
]
GRID_CONNECTION_INPUT_CONTRACT: InputContract = "grid_connection_evidence_v1"
INPUT_CONTRACT: InputContract = "installation_pv_string_links_v1"
DIRECT_BEAM_INPUT_CONTRACT: InputContract = "pv_string_links_direct_beam_visibility_v1"
GEOMETRIC_PV_INPUT_CONTRACT: InputContract = (
    "pv_string_links_direct_beam_geometric_pv_v1"
)
PLANT_PV_INPUT_CONTRACT: InputContract = "pv_plant_string_plan_v1"
ELECTRICAL_INPUT_CONTRACT: InputContract = "installation_circuit_electrical_v1"
SUPPORTED_INPUT_CONTRACTS: tuple[str, ...] = (
    INPUT_CONTRACT,
    DIRECT_BEAM_INPUT_CONTRACT,
    GEOMETRIC_PV_INPUT_CONTRACT,
    PLANT_PV_INPUT_CONTRACT,
    ELECTRICAL_INPUT_CONTRACT,
    GRID_CONNECTION_INPUT_CONTRACT,
)


def required_contracts(inputs: Mapping[str, object]) -> tuple[str, ...]:
    installation = inputs.get("installation")
    required = []
    if "grid_connection" in inputs:
        required.append(GRID_CONNECTION_INPUT_CONTRACT)
    if "pv_plant_string_plan" in inputs:
        required.append(PLANT_PV_INPUT_CONTRACT)
    if isinstance(installation, Mapping) and "pv_string_links" in installation:
        required.append(INPUT_CONTRACT)
    if isinstance(installation, Mapping):
        circuits, runs = installation.get("circuits"), installation.get("cable_runs")
        electrical = any(
            isinstance(row, Mapping) and "operating_conditions" in row
            for row in (circuits if isinstance(circuits, list) else [])
        ) or any(
            isinstance(row, Mapping)
            and (
                "core_roles" in row
                or isinstance(row.get("conductor"), Mapping)
                and "cable_reference" in row["conductor"]
            )
            for row in (runs if isinstance(runs, list) else [])
        )
        if electrical:
            required.append(ELECTRICAL_INPUT_CONTRACT)
    if "direct_beam_visibility" in inputs:
        required.append(DIRECT_BEAM_INPUT_CONTRACT)
    if "geometric_pv_preparation" in inputs:
        required.append(GEOMETRIC_PV_INPUT_CONTRACT)
    return tuple(required)


def require_input_contract(
    existing: Mapping[str, object] | None,
    incoming: Mapping[str, object],
    input_contract: str | None,
) -> None:
    from .errors import InvalidInput, ProjectInputContractRequired

    if input_contract is not None and input_contract not in SUPPORTED_INPUT_CONTRACTS:
        raise InvalidInput("unsupported project input contract")
    required = set(required_contracts(incoming))
    if existing is not None:
        required.update(required_contracts(existing))
    # Each complete writer understands only its declared feature generation.
    # Concrete coverage sets keep older tokens from covering future additions.
    covered = (
        (
            INPUT_CONTRACT,
            DIRECT_BEAM_INPUT_CONTRACT,
            GEOMETRIC_PV_INPUT_CONTRACT,
            PLANT_PV_INPUT_CONTRACT,
            ELECTRICAL_INPUT_CONTRACT,
            GRID_CONNECTION_INPUT_CONTRACT,
        )
        if input_contract == GRID_CONNECTION_INPUT_CONTRACT
        else (
            INPUT_CONTRACT,
            DIRECT_BEAM_INPUT_CONTRACT,
            GEOMETRIC_PV_INPUT_CONTRACT,
            PLANT_PV_INPUT_CONTRACT,
            ELECTRICAL_INPUT_CONTRACT,
        )
        if input_contract == ELECTRICAL_INPUT_CONTRACT
        else (
            INPUT_CONTRACT,
            DIRECT_BEAM_INPUT_CONTRACT,
            GEOMETRIC_PV_INPUT_CONTRACT,
            PLANT_PV_INPUT_CONTRACT,
        )
        if input_contract == PLANT_PV_INPUT_CONTRACT
        else (INPUT_CONTRACT, DIRECT_BEAM_INPUT_CONTRACT, GEOMETRIC_PV_INPUT_CONTRACT)
        if input_contract == GEOMETRIC_PV_INPUT_CONTRACT
        else (INPUT_CONTRACT, DIRECT_BEAM_INPUT_CONTRACT)
        if input_contract == DIRECT_BEAM_INPUT_CONTRACT
        else (INPUT_CONTRACT,)
        if input_contract == INPUT_CONTRACT
        else ()
    )
    if not required.issubset(covered):
        raise ProjectInputContractRequired(
            "this complete-input write requires an updated editor"
        )


def create_command(
    title: str, inputs: Object, *, input_contract: str | None = None
) -> Object:
    value: Object = {"title": title, "inputs": inputs}
    if input_contract is not None:
        value["input_contract"] = input_contract
    return value


def revise_command(
    expected_revision: int, inputs: Object, *, input_contract: str | None = None
) -> Object:
    value: Object = {"expected_revision": expected_revision, "inputs": inputs}
    if input_contract is not None:
        value["input_contract"] = input_contract
    return value
