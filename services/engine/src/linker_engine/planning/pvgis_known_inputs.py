"""Customer-declared PV planes at the existing project site, without roof geometry."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .brief import PlanningBrief, SiteBrief
from .canonical import Object, digest, encode
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput
from .geometry_documents import Identifier
from .pvgis_reference_inputs import PvgisReferenceSettings
from .pvgis_request import PvgisRequest
from .weather_fetch_plan import WeatherFetchLimits

MODEL = "pvgis_5_3_known_ac_reference_v1"
PROFILE_PURPOSE = "pvgis_known_ac_reference_profile_v1"
MODEL_ROLE = "official_calendar_year_customer_declared_ac_reference"
type Note = Annotated[str, Field(min_length=1, max_length=4096)]
type Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class KnownPvArray(Document):
    id: Identifier
    peak_power_kwp: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    tilt_deg: Annotated[float, Field(ge=0, le=90, allow_inf_nan=False)]
    azimuth_north_clockwise_deg: Annotated[
        float, Field(ge=0, lt=360, allow_inf_nan=False)
    ]
    source_note: Note

    @model_validator(mode="after")
    def meaningful_source(self) -> Self:
        if not self.source_note.strip():
            raise ValueError("known PV needs its declared source")
        return self


class KnownPvInputs(PvgisReferenceSettings):
    model: Literal["pvgis_5_3_known_ac_reference_v1"]
    source_note: Note
    arrays: Annotated[list[KnownPvArray], Field(min_length=1)]

    @model_validator(mode="after")
    def distinct_arrays(self) -> Self:
        if not self.source_note.strip() or len({a.id for a in self.arrays}) != len(
            self.arrays
        ):
            raise ValueError("known PV requires a source and distinct planes")
        return self


class KnownPvRequest(KnownPvArray):
    request: PvgisRequest


class KnownPvPlan(Document):
    schema_version: SchemaVersion
    kind: Literal["pvgis_5_3_known_ac_reference_plan_v1"]
    basis: Literal["customer_declared"]
    parameters: KnownPvInputs
    site: SiteBrief
    site_sha256: Hash
    parameters_sha256: Hash
    limits: WeatherFetchLimits
    max_array_steps: Annotated[int, Field(strict=True, gt=0)]
    arrays: Annotated[list[KnownPvRequest], Field(min_length=1)]

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}


def known_reference_plan(
    inputs: Object, limits: WeatherFetchLimits, max_array_steps: int
) -> KnownPvPlan:
    parameters = KnownPvInputs.read(inputs.get("pvgis_reference"))
    site = PlanningBrief.read(inputs.get("brief")).site
    if (
        site.latitude is None
        or site.longitude is None
        or site.coordinate_basis == "not_provided"
    ):
        raise InvalidInput(
            "known PV requires the declared project coordinates",
            fields=("brief.site.latitude", "brief.site.longitude"),
        )
    rows = (
        datetime(parameters.year + 1, 1, 1, tzinfo=UTC)
        - datetime(parameters.year, 1, 1, tzinfo=UTC)
    ).days * 24
    if (
        rows > limits.max_weather_rows
        or rows * len(parameters.arrays) > max_array_steps
    ):
        raise InvalidInput("known PV exceeds the configured array/hour budget")
    arrays = []
    for array in parameters.arrays:
        arrays.append(
            KnownPvRequest(
                **array.model_dump(mode="json"),
                request=PvgisRequest(
                    schema_version=1,
                    api_version="5.3",
                    radiation_database=parameters.radiation_database,
                    latitude_deg=site.latitude,
                    longitude_deg=site.longitude,
                    start_year=parameters.year,
                    end_year=parameters.year,
                    peak_power_kwp=array.peak_power_kwp,
                    system_loss_percent=parameters.system_loss_percent,
                    pv_technology=parameters.pv_technology,
                    mounting_place=parameters.mounting_place,
                    tilt_deg=array.tilt_deg,
                    azimuth_north_clockwise_deg=array.azimuth_north_clockwise_deg,
                    use_terrain_horizon=parameters.use_terrain_horizon,
                ),
            )
        )
    site_document = site.model_dump(mode="json")
    return KnownPvPlan(
        schema_version=1,
        kind="pvgis_5_3_known_ac_reference_plan_v1",
        basis="customer_declared",
        parameters=parameters,
        site=site,
        site_sha256=digest(encode(site_document)),
        parameters_sha256=digest(encode(inputs.get("pvgis_reference"))),
        limits=limits,
        max_array_steps=max_array_steps,
        arrays=arrays,
    )
