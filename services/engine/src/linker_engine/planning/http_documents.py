"""Versioned private commands; identity/runtime/source authority is not a field."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator

from .brief import PlanningBrief
from .canonical import Object
from .dc_energy_parameters import DcLossScenario
from .energy_inputs import BatteryParameters, Document, MappingDocument, SchemaVersion
from .geometry_documents import GeometryDocument
from .geometry_import_documents import GeometryImportOptions
from .report_inputs import ReportOptions
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
        if "geometry_imports" in value:
            from .geometry_import_selections import GeometryImports

            GeometryImports.model_validate(value["geometry_imports"])
        if "pv_generation" in value:
            from .pv_parameters import PvGenerationParameters

            PvGenerationParameters.model_validate(value["pv_generation"])
        if "pv_preparation" in value:
            from .pv_preparation import PvPreparationInputs

            PvPreparationInputs.model_validate(value["pv_preparation"])
        if "weather_acquisition" in value:
            from .weather_inputs import WeatherAcquisitionInputs

            WeatherAcquisitionInputs.model_validate(value["weather_acquisition"])
        if "equipment_selection" in value:
            from .equipment_inputs import EquipmentSelection

            EquipmentSelection.model_validate(value["equipment_selection"])
        if "pv_string_plan" in value:
            from .pv_string_inputs import PvStringPlan

            PvStringPlan.model_validate(value["pv_string_plan"])
        if "equipment_requirements" in value:
            from .equipment_requirements import EquipmentRequirements

            EquipmentRequirements.model_validate(value["equipment_requirements"])
        if "equipment_candidate" in value:
            from .equipment_candidate_choice import EquipmentCandidateChoice

            EquipmentCandidateChoice.model_validate(value["equipment_candidate"])
        return value


class ProjectCreate(ProjectInputs):
    title: Annotated[str, Field(min_length=1, max_length=256)]
    key: Key


class ProjectRead(Command):
    project_id: Id
    revision: Revision | None


class RunCompare(Command):
    project_id: Id
    baseline_run_id: Id
    candidate_run_id: Id


class GeometryReview(Command):
    project_id: Id
    geometry: Object


class GeometryImportCommand(Command):
    project_id: Id
    content_base64: str
    options: GeometryImportOptions
    key: Key


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


class ReportEvaluate(EnergyEvaluate):
    options: ReportOptions


class EquipmentCandidateRead(RunRead):
    candidate_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class TraceRead(RunRead):
    offset: Annotated[int, Field(strict=True, ge=0)] | None = None
    page_size: Annotated[int, Field(strict=True, gt=0)] | None = None

    @model_validator(mode="after")
    def paired_window(self) -> TraceRead:
        if (self.offset is None) != (self.page_size is None):
            raise ValueError("trace window requires offset and page size")
        return self


class AssetRead(Command):
    project_id: Id
    asset_id: Id


class HandoffPrepare(Command):
    project_id: Id
    report_run_id: Id
    expected_revision: Revision
    key: Key


class HandoffRead(Command):
    handoff_id: Id


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
    parameters: BatteryParameters | DcLossScenario
    source_note: Note
    key: Key
    expected_revision: Revision | None = None

    @model_validator(mode="after")
    def dc_revision(self) -> BatteryScenario:
        if (
            isinstance(self.parameters, DcLossScenario)
            and self.expected_revision is None
        ):
            raise ValueError(
                "Woo-derived DC parameters require the selected project revision"
            )
        if (
            isinstance(self.parameters, BatteryParameters)
            and self.expected_revision is not None
        ):
            raise ValueError(
                "independent AC parameter upload does not consume a project revision"
            )
        return self
