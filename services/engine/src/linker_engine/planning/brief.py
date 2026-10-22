"""An incomplete project brief is saveable; missing facts remain explicit nulls.

This is intake, not equipment/country qualification or a time-series model.
Lat/lon are WGS84 degrees (map adapter contract); all string limits are resource
policy, not engineering restrictions. Further tasks state their own readiness.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput
from .timezone_rules import require_iana_timezone

type Text = Annotated[str, Field(max_length=4096)]
type Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class SiteBrief(Document):
    country_code: Country | None
    location_label: Text
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)] | None
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)] | None
    coordinate_basis: Literal["user_entered", "not_provided"]
    timezone: Annotated[str, Field(min_length=1, max_length=128)] | None

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                require_iana_timezone(value)
            except InvalidInput as error:
                raise ValueError("known IANA timezone required") from error
        return value


class AnnualLoadBrief(Document):
    kwh: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    basis: Literal["bill_total", "user_estimate"] | None
    source_note: Text


class PlanningBrief(Document):
    schema_version: SchemaVersion
    project_use: Literal["residential", "commercial", "industrial"] | None
    system_scope: Literal["new_pv_storage", "storage_addition", "pv_only"] | None
    site: SiteBrief
    annual_load: AnnualLoadBrief
    project_note: Text


def brief_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **PlanningBrief.model_json_schema(),
    }
