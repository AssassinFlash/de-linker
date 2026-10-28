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
    "installation_pv_string_links_v1",
    "pv_string_links_direct_beam_visibility_v1",
    "pv_string_links_direct_beam_geometric_pv_v1",
]
INPUT_CONTRACT: InputContract = "installation_pv_string_links_v1"
DIRECT_BEAM_INPUT_CONTRACT: InputContract = "pv_string_links_direct_beam_visibility_v1"
GEOMETRIC_PV_INPUT_CONTRACT: InputContract = (
    "pv_string_links_direct_beam_geometric_pv_v1"
)
SUPPORTED_INPUT_CONTRACTS: tuple[str, ...] = (
    INPUT_CONTRACT,
    DIRECT_BEAM_INPUT_CONTRACT,
    GEOMETRIC_PV_INPUT_CONTRACT,
)


def required_contracts(inputs: Mapping[str, object]) -> tuple[str, ...]:
    installation = inputs.get("installation")
    required = []
    if isinstance(installation, Mapping) and "pv_string_links" in installation:
        required.append(INPUT_CONTRACT)
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
    # The new writer explicitly understands both features. Keep these concrete
    # coverage sets separate: neither token silently covers future additions.
    covered = (
        (INPUT_CONTRACT, DIRECT_BEAM_INPUT_CONTRACT, GEOMETRIC_PV_INPUT_CONTRACT)
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
