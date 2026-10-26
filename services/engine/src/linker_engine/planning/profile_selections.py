"""Owned source choices; a source role is not inferred from its numeric values."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .assets import Assets
from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput, VersionUnavailable
from .power_series import Measurement
from .pv_profile import PURPOSE
from .records import Actor

type ProfileRole = Measurement | Literal["pv_reference"]


class ProfileSelections(Document):
    schema_version: SchemaVersion
    selected: dict[ProfileRole, Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]]


def check_profile_selections(
    assets: Assets, actor: Actor, project_id: str | None, inputs: Object
) -> None:
    if "profile_selections" not in inputs:
        return
    selections = ProfileSelections.read(inputs["profile_selections"])
    if project_id is None:
        if selections.selected:
            raise InvalidInput(
                "a new project cannot reference another project's assets"
            )
        return
    for measurement, asset_id in selections.selected.items():
        asset = assets.get(actor, project_id, asset_id)
        if asset.purpose == "csv_profile_v1":
            mapping = asset.metadata.get("csv_mapping")
            if (
                not isinstance(mapping, dict)
                or mapping.get("measurement") != measurement
            ):
                raise InvalidInput(
                    "selected source has a different measurement boundary"
                )
        elif asset.purpose == PURPOSE:
            if measurement not in {"pv_available_ac", "pv_reference"}:
                raise InvalidInput("PV source cannot become a consumption profile")
        elif asset.purpose == "pvgis_system_profile_v1":
            if measurement != "pv_available_ac":
                raise InvalidInput("PV source cannot become a consumption profile")
        else:
            raise VersionUnavailable("selected profile format unavailable")
