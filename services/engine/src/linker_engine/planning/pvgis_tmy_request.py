"""An exact versioned TMY request and separately acknowledged response identity."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Self
from urllib.parse import parse_qsl, urlencode, urlsplit

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion
from .pvgis_request import Finite, Year


class PvgisTmyRequest(Document):
    schema_version: SchemaVersion
    api_version: Literal["5.3"]
    latitude_deg: Annotated[Finite, Field(ge=-90, le=90)]
    longitude_deg: Annotated[Finite, Field(ge=-180, le=180)]
    start_year: Year
    end_year: Year
    use_terrain_horizon: bool
    # The TMY endpoint has no database selector. Expected actual echoes are
    # still explicit, so a changed provider default cannot be concealed.
    radiation_database_policy: Literal["provider_default_with_verified_echo"]
    expected_radiation_database: Literal["PVGIS-SARAH3", "PVGIS-ERA5"]
    expected_meteo_database: Literal["ERA5"]

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_year < self.start_year:
            raise ValueError("TMY selection years must be ordered")
        return self

    def parameters(self) -> dict[str, str]:
        return {
            "lat": str(self.latitude_deg),
            "lon": str(self.longitude_deg),
            "startyear": str(self.start_year),
            "endyear": str(self.end_year),
            "usehorizon": "1" if self.use_terrain_horizon else "0",
            "outputformat": "json",
        }

    @property
    def url(self) -> str:
        return "https://re.jrc.ec.europa.eu/api/v5_3/tmy?" + urlencode(
            self.parameters()
        )

    def matches_url(self, value: str) -> bool:
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "re.jrc.ec.europa.eu"
                or parsed.path != "/api/v5_3/tmy"
                or parsed.fragment
            ):
                return False
            pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
            actual, wanted = dict(pairs), self.parameters()
            if len(actual) != len(pairs) or set(actual) != set(wanted):
                return False
            return all(
                actual[name] == expected
                if name == "outputformat"
                else Decimal(actual[name]).is_finite()
                and Decimal(actual[name]) == Decimal(expected)
                for name, expected in wanted.items()
            )
        except (ValueError, InvalidOperation):
            return False


class PvgisTmyInterpretation(Document):
    schema_version: SchemaVersion
    synthetic_energy_year: Year
    solar_date_policy: Literal["original_selected_year_plus_reported_irradiance_offset"]
    output_axis_policy: Literal["nonleap_synthetic_utc_hourly_scenario_v1"]
    power_reconstruction: Literal["representative_pv_output_over_declared_intervals_v1"]
