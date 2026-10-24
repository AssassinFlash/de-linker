"""Weather samples and an independent energy axis; neither is a PV power series."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .canonical import Json, Object
from .errors import InvalidInput
from .interval import Interval, utc
from .power_series import check_intervals
from .series_source import SeriesSource


def finite(value: float, name: str) -> None:
    try:
        valid = type(value) in (float, int) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise InvalidInput(f"finite weather {name} required")


@dataclass(frozen=True)
class WeatherPoint:
    interval: Interval
    source_label_utc: datetime
    irradiance_at_utc: datetime
    ghi_w_m2: float
    dni_w_m2: float
    dhi_w_m2: float
    air_temp_2m_c: float
    wind_10m_m_s: float
    pressure_pa: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_label_utc", utc(self.source_label_utc))
        object.__setattr__(self, "irradiance_at_utc", utc(self.irradiance_at_utc))
        for name in (
            "ghi_w_m2",
            "dni_w_m2",
            "dhi_w_m2",
            "air_temp_2m_c",
            "wind_10m_m_s",
            "pressure_pa",
        ):
            finite(getattr(self, name), name)
        if min(self.ghi_w_m2, self.dni_w_m2, self.dhi_w_m2, self.wind_10m_m_s) < 0:
            raise InvalidInput("negative weather irradiance or wind")
        # Absolute zero and positive absolute pressure, not equipment limits.
        if self.air_temp_2m_c <= -273.15 or self.pressure_pa <= 0:
            raise InvalidInput("nonphysical weather temperature or pressure")

    def document(self) -> Object:
        return {
            "start_utc": self.interval.start.isoformat(),
            "end_utc": self.interval.end.isoformat(),
            "source_label_utc": self.source_label_utc.isoformat(),
            "irradiance_at_utc": self.irradiance_at_utc.isoformat(),
            "ghi_w_m2": self.ghi_w_m2,
            "dni_w_m2": self.dni_w_m2,
            "dhi_w_m2": self.dhi_w_m2,
            "air_temp_2m_c": self.air_temp_2m_c,
            "wind_10m_m_s": self.wind_10m_m_s,
            "pressure_pa": self.pressure_pa,
        }


@dataclass(frozen=True)
class WeatherSeries:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    points: tuple[WeatherPoint, ...]
    source: SeriesSource

    def __post_init__(self) -> None:
        for name in ("latitude_deg", "longitude_deg", "altitude_m"):
            finite(getattr(self, name), name)
        if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180:
            raise InvalidInput("weather geographic coordinates out of range")
        object.__setattr__(self, "points", tuple(self.points))
        check_intervals(tuple(point.interval for point in self.points))

    def document(self) -> Object:
        points: list[Json] = [point.document() for point in self.points]
        return {
            "schema_version": 1,
            "kind": "weather_with_explicit_irradiance_instants_v1",
            "latitude_deg": self.latitude_deg,
            "longitude_deg": self.longitude_deg,
            "altitude_m": self.altitude_m,
            "source": self.source.document(),
            "points": points,
        }
