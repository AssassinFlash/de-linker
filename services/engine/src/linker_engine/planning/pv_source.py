"""One explicit frozen TMY source: bytes, capture, interpretation and rights."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import Object, decode_object, encode
from .errors import VersionUnavailable
from .pv_parameters import PvGenerationLimits
from .pv_weather import WeatherSeries
from .pvgis_response import PvgisCapture
from .pvgis_tmy import tmy_weather
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest
from .storage import Blobs


@dataclass(frozen=True)
class PvSource:
    content: bytes
    request: PvgisTmyRequest
    capture: PvgisCapture
    interpretation: PvgisTmyInterpretation
    provenance_json: bytes

    @classmethod
    def read(cls, blobs: Blobs, raw_sha256: str, metadata: Object) -> PvSource:
        provenance = metadata.get("provenance")
        if not isinstance(provenance, dict):
            raise VersionUnavailable("weather source provenance required")
        return cls(
            blobs.read(raw_sha256),
            PvgisTmyRequest.read(metadata.get("weather_request")),
            PvgisCapture.read(metadata.get("weather_capture")),
            PvgisTmyInterpretation.read(metadata.get("weather_interpretation")),
            encode(provenance),
        )

    def metadata(self) -> Object:
        return {
            "weather_request": {**self.request.model_dump(mode="json")},
            "weather_capture": self.capture.document(),
            "weather_interpretation": {**self.interpretation.model_dump(mode="json")},
            "provenance": decode_object(self.provenance_json),
        }

    def weather(self, limits: PvGenerationLimits) -> WeatherSeries:
        return tmy_weather(
            self.content,
            self.request,
            self.capture,
            self.interpretation,
            max_bytes=limits.max_weather_bytes,
            max_rows=limits.max_weather_rows,
        )
