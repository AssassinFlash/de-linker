"""Geometric visibility contracts; no irradiance or power scaling."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion
from .geometry_documents import Hash, PositiveInteger

type Count = PositiveInteger
# Same exact-integer wire domain as geometry; not a sampling recommendation.
type RowIndex = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]
type Identity = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class DirectBeamSampling(Document):
    coarse_cells_per_edge: Count
    fine_cells_per_edge: Count

    @model_validator(mode="after")
    def refinement(self) -> Self:
        if self.fine_cells_per_edge <= self.coarse_cells_per_edge:
            raise ValueError("fine midpoint sampling must refine coarse sampling")
        return self


class DirectBeamTaskInputs(Document):
    schema_version: SchemaVersion
    weather_asset_id: Identity
    row_indices: Annotated[list[RowIndex], Field(min_length=1)]
    sampling: DirectBeamSampling

    @model_validator(mode="after")
    def ordered_rows(self) -> Self:
        # Check the request without parsing weather; FrozenWeatherSelection
        # repeats this check with the actual complete source hash in the worker.
        if self.row_indices != sorted(set(self.row_indices)):
            raise ValueError("selected source rows must be unique and ordered")
        return self


class DirectBeamLimits(Document):
    """Explicit caller resource policy; none of these is a physical threshold."""

    max_selected_rows: Count
    max_samples: Count
    max_ray_face_checks: Count
    # AABB query checks are separate from exact face intersections. These are
    # computational policies, not physical resolution or error tolerances.
    max_bounds_checks: Count
    index_leaf_size: Count


class FrozenWeatherSelection(Document):
    """Caller-owned asset read, not authentication or a browser-supplied claim.

    The native worker resolves ownership before constructing this
    value. The pure core neither authenticates a principal nor opens an asset.
    """

    schema_version: SchemaVersion
    project_id: Identity
    project_revision: Count
    asset_id: Identity
    asset_metadata_sha256: Hash
    weather_document_sha256: Hash
    row_indices: Annotated[list[RowIndex], Field(min_length=1)]

    @model_validator(mode="after")
    def ordered_rows(self) -> Self:
        if self.row_indices != sorted(set(self.row_indices)):
            raise ValueError("selected source rows must be unique and ordered")
        return self


class DirectBeamBinding(Document):
    schema_version: SchemaVersion
    project_id: Identity
    project_revision: Count
    geometry_sha256: Hash
    woo_module_basis_sha256: Hash
    weather_document_sha256: Hash
    weather_asset_metadata_sha256: Hash
    weather_selection_sha256: Hash
