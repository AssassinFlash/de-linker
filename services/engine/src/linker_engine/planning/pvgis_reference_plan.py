"""Frozen official per-array requests and existing deployment resource budgets."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .pvgis_reference_array import PvgisReferenceArray
from .pvgis_reference_inputs import PvgisReferenceInputs
from .weather_fetch_plan import WeatherFetchLimits

type Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class PvgisReferencePlan(Document):
    schema_version: SchemaVersion
    kind: Literal["pvgis_5_3_roof_ac_reference_plan_v1"]
    parameters: PvgisReferenceInputs
    geometry_sha256: Hash
    parameters_sha256: Hash
    module_basis_sha256: Hash
    limits: WeatherFetchLimits
    max_array_steps: Annotated[int, Field(strict=True, gt=0)]
    arrays: Annotated[list[PvgisReferenceArray], Field(min_length=1)]

    @model_validator(mode="after")
    def bounded_complete_arrays(self) -> Self:
        start = datetime(self.parameters.year, 1, 1, tzinfo=UTC)
        end = datetime(self.parameters.year + 1, 1, 1, tzinfo=UTC)
        rows = (end - start).days * 24
        if rows > self.limits.max_weather_rows or (
            rows * len(self.arrays) > self.max_array_steps
        ):
            raise ValueError("roof reference exceeds the configured array/hour budget")
        if len({row.id for row in self.arrays}) != len(self.arrays):
            raise ValueError("roof reference arrays must be distinct")
        if len({m for a in self.arrays for m in a.module_ids}) != sum(
            a.module_count for a in self.arrays
        ):
            raise ValueError("roof modules cannot appear in multiple requests")
        for row in self.arrays:
            request = row.request
            if (
                request.start_year != self.parameters.year
                or request.end_year != self.parameters.year
                or request.radiation_database != self.parameters.radiation_database
                or request.pv_technology != self.parameters.pv_technology
                or request.mounting_place != self.parameters.mounting_place
                or request.system_loss_percent != self.parameters.system_loss_percent
                or request.use_terrain_horizon != self.parameters.use_terrain_horizon
            ):
                raise ValueError(
                    "every array must use the explicit saved model choices"
                )
        return self

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}
