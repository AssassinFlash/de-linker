"""Explicit complete-input writers; omitted metadata keeps legacy command hashes.

Import-time dependencies stay in the standard library so the native read-only
deployment probe can use the same retained-feature detector without a workspace.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .canonical import Object

type InputContract = Literal["installation_pv_string_links_v1"]
INPUT_CONTRACT: InputContract = "installation_pv_string_links_v1"
SUPPORTED_INPUT_CONTRACTS: tuple[str, ...] = (INPUT_CONTRACT,)


def required_contracts(inputs: Mapping[str, object]) -> tuple[str, ...]:
    installation = inputs.get("installation")
    return (
        (INPUT_CONTRACT,)
        if isinstance(installation, Mapping) and "pv_string_links" in installation
        else ()
    )


def require_input_contract(
    existing: Mapping[str, object] | None,
    incoming: Mapping[str, object],
    input_contract: str | None,
) -> None:
    from .errors import InvalidInput, ProjectInputContractRequired

    if input_contract is not None and input_contract != INPUT_CONTRACT:
        raise InvalidInput("unsupported project input contract")
    if input_contract != INPUT_CONTRACT and (
        required_contracts(incoming)
        or (existing is not None and required_contracts(existing))
    ):
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
