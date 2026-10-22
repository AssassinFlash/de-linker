"""Versioned private commands; identity/runtime/source authority is not a field."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .canonical import Object
from .energy_inputs import BatteryParameters, Document, MappingDocument, SchemaVersion

# Protocol string limits, not engineering quantities; see 548-private-gateway.md.
type Key = Annotated[str, Field(min_length=1, max_length=256)]
type Note = Annotated[str, Field(min_length=1, max_length=4096)]
type Id = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
type Revision = Annotated[int, Field(strict=True, gt=0)]


class Command(Document):
    schema_version: SchemaVersion


class Cursor(Document):
    updated_at: Annotated[float, Field(allow_inf_nan=False)]
    id: Id


class ProjectList(Command):
    page_size: Annotated[int, Field(strict=True, gt=0)]
    after: Cursor | None


class ProjectCreate(Command):
    title: Annotated[str, Field(min_length=1, max_length=256)]
    inputs: Object
    key: Key


class ProjectRead(Command):
    project_id: Id
    revision: Revision | None


class ProjectRevise(Command):
    project_id: Id
    expected_revision: Revision
    inputs: Object
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


class CsvImport(Command):
    project_id: Id
    content_base64: str
    mapping: MappingDocument
    source_label: Key
    rights_note: Note
    key: Key


class BatteryScenario(Command):
    project_id: Id
    parameters: BatteryParameters
    source_note: Note
    key: Key
