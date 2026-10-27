"""An explicit calendar-year system-output model, never a TMY fallback."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from .energy_inputs import Document, SchemaVersion
from .pvgis_profile import PvgisInterpretation


class PvgisReferenceInputs(Document):
    schema_version: SchemaVersion
    model: Literal["pvgis_5_3_roof_ac_reference_v1"]
    radiation_database: Literal["PVGIS-ERA5", "PVGIS-SARAH3"]
    year: Annotated[int, Field(strict=True, ge=1, le=9998)]
    # Unknown returned no P in the retained official capability probe.
    pv_technology: Literal["crystSi", "crystSi2025", "CIS", "CdTe"]
    mounting_place: Literal["free", "building"]
    system_loss_percent: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    use_terrain_horizon: bool
    source_note: Annotated[str, Field(max_length=4096)] | None = None

    @field_validator("source_note")
    @classmethod
    def meaningful_note(cls, value: str | None) -> str | None:
        return None if value is None or not value.strip() else value

    def interpretation(self) -> PvgisInterpretation:
        return PvgisInterpretation(
            schema_version=1,
            temporal_policy="era5_centered_hourly_means_v1"
            if self.radiation_database == "PVGIS-ERA5"
            else "sample_value_over_containing_utc_hour_v1",
            output_role="pv_available_ac",
            system_power_policy="provider_system_output_no_second_loss_chain",
        )
