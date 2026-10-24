"""One server-owned official JRC request and explicit operational budgets.

Provider facts and pinned schema: 2026-10-24-pv-managed-intake/FINDINGS.md.
Counts of one constrain this operation to its single official weather URL;
they are application resource policy, not weather-accuracy thresholds.
"""

from __future__ import annotations

import calendar
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Json, Object, encode
from .energy_inputs import Document, SchemaVersion
from .errors import VersionUnavailable
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest

type PositiveInteger = Annotated[int, Field(strict=True, gt=0)]
type PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class WeatherFetchLimits(Document):
    max_response_bytes: PositiveInteger
    max_metadata_bytes: PositiveInteger
    max_weather_rows: PositiveInteger
    connect_timeout_seconds: PositiveNumber
    read_timeout_seconds: PositiveNumber
    max_elapsed_seconds: PositiveNumber

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.max_metadata_bytes > self.max_response_bytes:
            raise ValueError("metadata response budget exceeds weather response budget")
        return self


class WeatherFetchPlan(Document):
    schema_version: SchemaVersion
    kind: Literal["pvgis_tmy_official_https_acquisition_v1"]
    request: PvgisTmyRequest
    interpretation: PvgisTmyInterpretation
    limits: WeatherFetchLimits

    @model_validator(mode="after")
    def nonleap_axis(self) -> Self:
        if calendar.isleap(self.interpretation.synthetic_energy_year):
            raise ValueError("TMY reconstruction requires a non-leap scenario year")
        return self

    def document(self) -> Object:
        return {
            **self.model_dump(mode="json"),
            "provider": {
                "name": "EC_JRC_PVGIS",
                "method": "GET",
                "url": self.request.url,
            },
        }

    @classmethod
    def from_document(cls, value: Json) -> WeatherFetchPlan:
        if not isinstance(value, dict):
            raise VersionUnavailable("pinned weather acquisition plan required")
        plan = cls.read(
            {name: item for name, item in value.items() if name != "provider"}
        )
        if encode(value) != encode(plan.document()):
            raise VersionUnavailable(
                "weather acquisition provider differs from its plan"
            )
        return plan
