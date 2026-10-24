"""A draft may select a real candidate from its own saved search result."""

from __future__ import annotations

from typing import Annotated, cast

from pydantic import Field

from .canonical import Object, encode
from .energy_inputs import Document
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_inputs import EquipmentSelection
from .errors import InvalidInput, VersionUnavailable
from .product_sources import ProductSources
from .records import Actor
from .workspace import Workspace


class EquipmentCandidateChoice(Document):
    run_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    candidate_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    assessment_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def check_equipment_candidate(
    workspace: Workspace,
    actor: Actor,
    project_id: str | None,
    inputs: Object,
    *,
    products: ProductSources | None = None,
    previous: Object | None = None,
) -> None:
    if "equipment_candidate" not in inputs:
        return
    choice = EquipmentCandidateChoice.read(inputs["equipment_candidate"])
    run = workspace.run(actor, choice.run_id)
    if project_id is None or run.project_id != project_id:
        raise InvalidInput("candidate must belong to this project")
    reply = EquipmentCandidateStore(workspace).read(
        actor, choice.run_id, choice.candidate_id
    )
    assert run.result is not None
    search = cast(Object, run.result["search"])
    candidate = next(
        row
        for row in cast(list[Object], search["candidates"])
        if row["id"] == choice.candidate_id
    )
    # Browser JSON does not retain the textual distinction between 10 and
    # 10.0. Compare strict typed fields, preserving ID and revision checks.
    if reply[
        "assessment_sha256"
    ] != choice.assessment_sha256 or EquipmentSelection.read(
        inputs.get("equipment_selection")
    ) != EquipmentSelection.read(candidate["selection"]):
        raise InvalidInput("candidate choice does not match the frozen selection")
    if previous is not None and encode(previous.get("equipment_candidate")) == encode(
        inputs["equipment_candidate"]
    ):
        return
    # A historical read or an unchanged saved choice needs no new permission.
    # First adoption is a new action and must validate the frozen Woo proof on
    # the server, including a withdrawal after the browser's initial check.
    pinned = run.result.get("pinned_assets")
    proof = pinned.get("woo.equipment_inputs") if isinstance(pinned, dict) else None
    if products is None or not isinstance(proof, str):
        raise VersionUnavailable("current equipment publication proof is unavailable")
    products.confirm_basis(workspace.blobs.object(proof), require_reference=False)
