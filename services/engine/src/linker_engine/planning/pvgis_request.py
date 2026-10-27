"""Explicit, fixed-plane PVGIS 5.3 system-output requests, without rounding.

JRC seriescalc parameter definitions and the captured response contract:
docs/research/2026-10-23-pv-inputs/PVGIS-SERIES.md. This model has no provider
default years, angles, technology or loss. It is not a real inverter model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion

type Finite = Annotated[float, Field(allow_inf_nan=False)]
type Year = Annotated[int, Field(strict=True, ge=1, le=9998)]


class PvgisRequest(Document):
    schema_version: SchemaVersion
    api_version: Literal["5.3"]
    radiation_database: Literal["PVGIS-ERA5", "PVGIS-SARAH3"]
    latitude_deg: Annotated[Finite, Field(ge=-90, le=90)]
    longitude_deg: Annotated[Finite, Field(ge=-180, le=180)]
    start_year: Year
    end_year: Year
    peak_power_kwp: Annotated[Finite, Field(gt=0)]
    system_loss_percent: Annotated[Finite, Field(ge=0, le=100)]
    # Exact provider response labels for all five were captured via Apify;
    # technology-mapping-probes.json includes URLs, hashes and metadata.
    pv_technology: Literal["crystSi", "crystSi2025", "CIS", "CdTe", "Unknown"]
    mounting_place: Literal["free", "building"]
    tilt_deg: Annotated[Finite, Field(ge=0, le=90)]
    azimuth_north_clockwise_deg: Annotated[Finite, Field(ge=0, lt=360)]
    use_terrain_horizon: bool

    @model_validator(mode="after")
    def ordered_years(self) -> PvgisRequest:
        if self.end_year < self.start_year:
            raise ValueError("end_year must not precede start_year")
        return self

    @property
    def start(self) -> datetime:
        return datetime(self.start_year, 1, 1, tzinfo=UTC)

    @property
    def end(self) -> datetime:
        return datetime(self.end_year + 1, 1, 1, tzinfo=UTC)

    def parameters(self) -> dict[str, str]:
        return {
            "lat": str(self.latitude_deg),
            "lon": str(self.longitude_deg),
            "raddatabase": self.radiation_database,
            "startyear": str(self.start_year),
            "endyear": str(self.end_year),
            "pvcalculation": "1",
            "peakpower": str(self.peak_power_kwp),
            "loss": str(self.system_loss_percent),
            "pvtechchoice": self.pv_technology,
            "mountingplace": self.mounting_place,
            "angle": str(self.tilt_deg),
            # PVGIS REST: south=0, east=-90, west=90. The application uses
            # true north=0, east=90, south=180, west=270, exactly once.
            "aspect": str(self.azimuth_north_clockwise_deg - 180),
            "trackingtype": "0",
            "usehorizon": "1" if self.use_terrain_horizon else "0",
            "components": "1",
            "optimalinclination": "0",
            "optimalangles": "0",
            "outputformat": "json",
        }

    @property
    def url(self) -> str:
        return "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?" + urlencode(
            self.parameters()
        )

    def matches_url(self, value: str) -> bool:
        """Require the same official endpoint and the complete explicit query.

        Numeric spellings such as 1/1.0 are equivalent, but duplicate, omitted,
        added or changed parameters and redirects to another host are not.
        """
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "re.jrc.ec.europa.eu"
                or parsed.path != "/api/v5_3/seriescalc"
                or parsed.fragment
            ):
                return False
            pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
            actual = dict(pairs)
            expected = self.parameters()
            if len(actual) != len(pairs) or set(actual) != set(expected):
                return False
            text = {"raddatabase", "pvtechchoice", "mountingplace", "outputformat"}
            return all(
                actual[name] == wanted
                if name in text
                else Decimal(actual[name]).is_finite()
                and Decimal(actual[name]) == Decimal(wanted)
                for name, wanted in expected.items()
            )
        except (ValueError, InvalidOperation):
            return False

    def document(self) -> Object:
        # Pydantic's JSON mode returns only JSON-compatible primitives here.
        return {**self.model_dump(mode="json")}
