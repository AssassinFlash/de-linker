"""One original-TMY metadata projection for trusted import and managed fetch."""

from .canonical import Object
from .pv_source import PvSource
from .pvgis_tmy import tmy_weather

WEATHER_PURPOSE = "pvgis_tmy_weather_v1"


def weather_identity(source: PvSource) -> Object:
    return {
        "schema": 1,
        "source_type": WEATHER_PURPOSE,
        "retention": "permanent",
        **source.metadata(),
    }


def weather_details(source: PvSource, *, max_bytes: int, max_rows: int) -> Object:
    weather = tmy_weather(
        source.content,
        source.request,
        source.capture,
        source.interpretation,
        max_bytes=max_bytes,
        max_rows=max_rows,
    )
    return {
        "latitude_deg": weather.latitude_deg,
        "longitude_deg": weather.longitude_deg,
        "altitude_m": weather.altitude_m,
        "interval_count": len(weather.points),
        "source": weather.source.document(),
    }
