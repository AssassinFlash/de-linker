"""A project can attach only its own source/manifest to a named geometry source."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .assets import Assets
from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput, VersionUnavailable
from .geometry import read_geometry
from .geometry_documents import Identifier
from .geometry_import import PURPOSE
from .records import Actor


class GeometryImports(Document):
    schema_version: SchemaVersion
    selected: dict[Identifier, Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]]


def check_geometry_imports(
    assets: Assets, actor: Actor, project_id: str | None, inputs: Object
) -> None:
    if "geometry_imports" not in inputs:
        return
    selections = GeometryImports.read(inputs["geometry_imports"])
    if project_id is None:
        if selections.selected:
            raise InvalidInput(
                "a new project cannot attach another project's geometry files"
            )
        return
    if not selections.selected:
        return
    geometry = read_geometry(inputs.get("geometry"))
    sources = {source.id: source for source in geometry.sources}
    for source_id, asset_id in selections.selected.items():
        if source_id not in sources:
            raise InvalidInput("import attachment requires its current geometry source")
        asset = assets.get(actor, project_id, asset_id)
        prepared = asset.metadata.get("geometry_import")
        if asset.purpose != PURPOSE or not isinstance(prepared, dict):
            raise InvalidInput("selected asset is not a geometry import")
        if sources[source_id].reference_sha256 != asset.content_sha256:
            raise InvalidInput("a bound original source hash cannot be changed")
        candidate = read_geometry(prepared.get("geometry"))
        if (
            len(candidate.sources) != 1
            or candidate.sources[0].id != source_id
            or candidate.sources[0].reference_sha256 != asset.content_sha256
            or prepared.get("original_content_sha256") != asset.content_sha256
        ):
            raise VersionUnavailable("geometry source/manifest association is invalid")
        # A database reference alone does not prove that its original bytes exist.
        assets.content(actor, project_id, asset_id)
