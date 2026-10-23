"""Explicit intake/calibration; raw source bytes are not a geometry authority."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion
from .geographic import GeographicReference
from .geometry_documents import Nonnegative, Text, Vec3

type Index = Annotated[int, Field(strict=True, ge=0)]


class ImportedPlane(Document):
    origin_enu: Vec3
    u_axis_enu: Vec3
    v_axis_enu: Vec3
    basis_note: Text


class GeometryImportDeclaration(Document):
    label: Text
    rights_note: Text
    spatial_precision_m: Nonnegative | None
    export_permission: Literal["permitted", "unknown", "prohibited"]


class GeometryImportOptions(Document):
    schema_version: SchemaVersion
    format: Literal["geojson_wgs84_horizontal_v1"]
    feature_index: Index
    polygon_index: Index
    roof_name: Text
    reference: GeographicReference
    plane: ImportedPlane
    source: GeometryImportDeclaration

    @model_validator(mode="after")
    def horizontal_reference(self) -> Self:
        if self.reference.height_basis != "zero_height_horizontal_convention":
            raise ValueError("2D GeoJSON needs its explicit horizontal-only reference")
        if not all(
            value.strip()
            for value in (
                self.roof_name,
                self.plane.basis_note,
                self.source.label,
                self.source.rights_note,
            )
        ):
            raise ValueError(
                "roof, plane basis and source declarations must be nonblank"
            )
        return self
