"""Saved source choices, separate from server-owned provider/resource policy."""

from .energy_inputs import Document, SchemaVersion
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest
from .weather_fetch_plan import WeatherFetchLimits, WeatherFetchPlan


class WeatherAcquisitionInputs(Document):
    schema_version: SchemaVersion
    request: PvgisTmyRequest
    interpretation: PvgisTmyInterpretation

    def plan(self, limits: WeatherFetchLimits) -> WeatherFetchPlan:
        return WeatherFetchPlan(
            schema_version=1,
            kind="pvgis_tmy_apify_acquisition_v1",
            request=self.request,
            interpretation=self.interpretation,
            limits=limits,
        )
