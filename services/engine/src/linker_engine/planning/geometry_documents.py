"""Versioned, metre-based design inputs; renderers never own project truth."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from .energy_inputs import Document, SchemaVersion

# Wire string/integer limits, not engineering dimensions (548-design-geometry).
type Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
type Text = Annotated[str, Field(min_length=1, max_length=4096)]
type Number = Annotated[float, Field(allow_inf_nan=False)]
type Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=2**53 - 1)]
type Vec2 = Annotated[list[Number], Field(min_length=2, max_length=2)]
type Vec3 = Annotated[list[Number], Field(min_length=3, max_length=3)]
type Ring = Annotated[list[Vec2], Field(min_length=3)]
type Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
type Permission = Literal["permitted", "unknown", "prohibited"]


def public_source_url(value: str | None) -> str | None:
    """A source reference is never fetched by validating or reviewing a design."""
    if value is None:
        return None
    if any(ord(character) < 32 for character in value) or value != value.strip():
        raise ValueError("source URL contains whitespace controls")
    try:
        url = urlsplit(value)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username
            or url.password
        ):
            raise ValueError("source requires a credential-free HTTP URL")
        _ = url.port
    except ValueError as error:
        raise ValueError("invalid source URL") from error
    return value


class SourcePermissions(Document):
    derive: Permission
    retain: Permission
    export: Permission


class GeometrySource(Document):
    id: Identifier
    kind: Literal[
        "user_measurement", "user_drawing", "licensed_dataset", "synthetic_fixture"
    ]
    note: Text
    rights_note: Text
    reference_url: Text | None
    reference_sha256: Hash | None
    acquired_at_utc: (
        Annotated[
            Text,
            Field(
                pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|\+00:00)$"
            ),
        ]
        | None
    )
    spatial_precision_m: Nonnegative | None
    calibration_note: Text
    rights_basis: Literal["user_attestation", "referenced_licence", "synthetic"]
    permissions: SourcePermissions

    _source_url = field_validator("reference_url")(public_source_url)

    @field_validator("acquired_at_utc")
    @classmethod
    def explicit_utc(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                stamp = datetime.fromisoformat(value)
                offset = stamp.utcoffset()
                if offset is None or offset.total_seconds() != 0:
                    raise ValueError("UTC timestamp required")
            except ValueError as error:
                raise ValueError(
                    "explicit acquisition UTC timestamp required"
                ) from error
        return value

    @model_validator(mode="after")
    def retention_claim(self) -> Self:
        if (
            self.permissions.retain != "permitted"
            or self.permissions.derive != "permitted"
        ):
            raise ValueError(
                "permanent editable geometry needs explicit retention and derivation claims"
            )
        if self.kind == "licensed_dataset" and (
            self.rights_basis != "referenced_licence"
            or self.reference_url is None
            or self.reference_sha256 is None
        ):
            raise ValueError("dataset geometry requires its referenced licence")
        if (self.kind == "synthetic_fixture") != (self.rights_basis == "synthetic"):
            raise ValueError("synthetic source basis must be explicit")
        return self


class GeographicAnchor(Document):
    latitude_deg: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    longitude_deg: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    source_id: Identifier
    datum: Literal["EPSG:4326"]


class CoordinateSystem(Document):
    kind: Literal["local_enu"]
    unit: Literal["m"]
    height_reference: Literal["relative_to_project_origin"]
    north_reference: Literal["true_north", "user_declared", "unreferenced"]
    north_source_id: Identifier | None
    anchor: GeographicAnchor | None


class RoofFace(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    origin_enu: Vec3
    u_axis_enu: Vec3
    v_axis_enu: Vec3
    boundary_uv: Ring
    holes_uv: list[Ring]


class ModuleSource(Document):
    kind: Literal["datasheet", "user_declared"]
    note: Text
    document_sha256: Hash | None
    url: Text | None
    page: PositiveInteger | None

    _source_url = field_validator("url")(public_source_url)

    @model_validator(mode="after")
    def complete_datasheet_claim(self) -> Self:
        if self.kind == "datasheet" and (
            self.document_sha256 is None or self.url is None or self.page is None
        ):
            raise ValueError("datasheet claim needs document hash, URL and page")
        return self


class ModuleSpec(Document):
    id: Identifier
    model: Text
    width_m: Positive
    length_m: Positive
    thickness_m: Positive
    stc_power_w: Positive
    source: ModuleSource


class PanelArray(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    roof_id: Identifier
    module_spec_id: Identifier
    origin_uv: Vec2
    rotation_deg: Number
    mount_tilt_deg: Annotated[float, Field(ge=0, le=90, allow_inf_nan=False)]
    lower_edge_clearance_m: Nonnegative
    rows: PositiveInteger
    columns: PositiveInteger
    column_gap_m: Nonnegative
    row_gap_m: Nonnegative
    excluded_slots: list[Annotated[str, Field(pattern=r"^[0-9]+:[0-9]+$")]]
    mounting_note: Text


class Obstacle(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    roof_id: Identifier
    footprint_uv: Ring
    extrusion_axis_enu: Vec3
    height_m: Positive


class Keepout(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    roof_id: Identifier
    footprint_uv: Ring
    reason: Text


class RoofLayoutRules(Document):
    roof_id: Identifier
    source_id: Identifier
    edge_clearance_m: Nonnegative | None
    obstacle_clearance_m: Nonnegative | None
    source_note: Text


class GeometryDocument(Document):
    schema_version: SchemaVersion
    coordinate_system: CoordinateSystem
    sources: list[GeometrySource]
    roofs: list[RoofFace]
    module_specs: list[ModuleSpec]
    arrays: list[PanelArray]
    obstacles: list[Obstacle]
    keepouts: list[Keepout]
    layout_rules: list[RoofLayoutRules]


def geometry_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **GeometryDocument.model_json_schema(),
    }
