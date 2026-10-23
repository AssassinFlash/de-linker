"""Versioned private commands; identity/runtime/source authority is not a field."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator

from .brief import PlanningBrief
from .canonical import Object
from .energy_inputs import BatteryParameters, Document, MappingDocument, SchemaVersion
from .geometry_documents import GeometryDocument
from .wire_numbers import check_wire_numbers

# Protocol string limits, not engineering quantities; see 548-private-gateway.md.
type Key = Annotated[str, Field(min_length=1, max_length=256)]
type Note = Annotated[str, Field(min_length=1, max_length=4096)]
type Id = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
type Revision = Annotated[int, Field(strict=True, gt=0)]


class Command(Document):
    schema_version: SchemaVersion

    @model_validator(mode="before")
    @classmethod
    def interoperable_numbers(cls, value: object) -> object:
        check_wire_numbers(value)
        return value


class SessionClaim(Command):
    key: Key


class Cursor(Document):
    updated_at: Annotated[float, Field(allow_inf_nan=False)]
    id: Id


class ProjectList(Command):
    page_size: Annotated[int, Field(strict=True, gt=0)]
    after: Cursor | None


class ProjectInputs(Command):
    inputs: Object

    @field_validator("inputs")
    @classmethod
    def validate_brief(cls, value: Object) -> Object:
        if "brief" in value:
            PlanningBrief.model_validate(value["brief"])
        if "profile_selections" in value:
            from .profile_selections import ProfileSelections

            ProfileSelections.model_validate(value["profile_selections"])
        if "geometry" in value:
            GeometryDocument.model_validate(value["geometry"])
        return value


class ProjectCreate(ProjectInputs):
    title: Annotated[str, Field(min_length=1, max_length=256)]
    key: Key


class ProjectRead(Command):
    project_id: Id
    revision: Revision | None


class GeometryReview(Command):
    project_id: Id
    geometry: Object


class ProjectRevise(ProjectInputs):
    project_id: Id
    expected_revision: Revision
    key: Key


class ProjectRuns(Command):
    project_id: Id
    page_size: Annotated[int, Field(strict=True, gt=0)]
    before_created_at: Annotated[float, Field(allow_inf_nan=False)] | None
    before_id: Id | None


class EnergyEvaluate(Command):
    project_id: Id
    expected_revision: Revision
    key: Key


class RunRead(Command):
    run_id: Id


class AssetRead(Command):
    project_id: Id
    asset_id: Id


class ProfilePreviewRead(AssetRead):
    offset: Annotated[int, Field(strict=True, ge=0)]
    page_size: Annotated[int, Field(strict=True, gt=0)]


class CsvImport(Command):
    project_id: Id
    content_base64: str
    mapping: MappingDocument
    source_label: Key
    rights_note: Note
    key: Key


class CsvInspect(Command):
    project_id: Id
    content_base64: str
    delimiter: str
    page_size: Annotated[int, Field(strict=True, gt=0)]


class BatteryScenario(Command):
    project_id: Id
    parameters: BatteryParameters
    source_note: Note
    key: Key
