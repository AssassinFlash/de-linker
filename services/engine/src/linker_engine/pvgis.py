"""PV yield per kWp from PVGIS, through pvlib, cached on a 0.05 degree grid.

PVGIS computes the yield itself (`seriescalc` with `pvcalculation=1`): the
same physics an installer checks against, with the system loss of
rules.PVGIS_SYSTEM_LOSS_PCT. The engine asks for 1 kWp over every year of the
radiation database and keeps the yearly totals: their spread is the year-to-
year range the report shows. Nothing hourly is kept or simulated.

Requests are keyed by the location snapped to rules.PVGIS_GRID_DEG, the tilt
and azimuth in whole degrees and the loss; one cached file answers every later
request in the same cell (docs/specs/14-solution-configurator.md, "缓存按 0.05° 网格").
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import rules


class YieldUnavailable(RuntimeError):
    """PVGIS could not be reached or answered without a usable series."""


@dataclass(frozen=True)
class YieldProfile:
    latitude: float
    longitude: float
    tilt_deg: int
    azimuth_deg: int
    loss_pct: float
    radiation_db: str
    annual_kwh_per_kwp: dict[int, float]
    monthly_kwh_per_kwp: list[float]

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["annual_kwh_per_kwp"] = {
            str(k): v for k, v in self.annual_kwh_per_kwp.items()
        }
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> YieldProfile:
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"],
            tilt_deg=data["tilt_deg"],
            azimuth_deg=data["azimuth_deg"],
            loss_pct=data["loss_pct"],
            radiation_db=data["radiation_db"],
            annual_kwh_per_kwp={
                int(k): float(v) for k, v in data["annual_kwh_per_kwp"].items()
            },
            monthly_kwh_per_kwp=[float(v) for v in data["monthly_kwh_per_kwp"]],
        )


Fetch = Callable[[float, float, int, int, float], tuple[Any, dict[str, Any]]]


def _pvgis_fetch(
    latitude: float, longitude: float, tilt: int, azimuth: int, loss: float
) -> tuple[Any, dict[str, Any]]:
    from pvlib.iotools import get_pvgis_hourly

    try:
        data, meta = get_pvgis_hourly(
            latitude,
            longitude,
            surface_tilt=tilt,
            # pvlib's convention (north 0, south 180); pvlib converts for PVGIS.
            surface_azimuth=azimuth,
            pvcalculation=True,
            peakpower=1,
            loss=loss,
            components=False,
            timeout=rules.PVGIS_TIMEOUT_S.value,
        )
    except Exception as error:  # requests and PVGIS errors alike
        raise YieldUnavailable(str(error)) from error
    return data, meta


def snap(value: float) -> float:
    step = rules.PVGIS_GRID_DEG.value
    return round(round(value / step) * step, 4)


def profile_from_series(
    data: Any,
    meta: dict[str, Any],
    latitude: float,
    longitude: float,
    tilt: int,
    azimuth: int,
) -> YieldProfile:
    """Yearly and mean monthly kWh per kWp from PVGIS hourly power (W per kWp)."""
    power = data["P"]
    if power.empty:
        raise YieldUnavailable("PVGIS returned an empty series")
    hours = power.index
    yearly = (power.groupby(hours.year).sum() / 1000).round(1)
    monthly_totals = power.groupby([hours.year, hours.month]).sum() / 1000
    monthly = monthly_totals.groupby(level=1).mean().round(1)
    meteo = meta.get("inputs", {}).get("meteo_data", {})
    return YieldProfile(
        latitude=latitude,
        longitude=longitude,
        tilt_deg=tilt,
        azimuth_deg=azimuth,
        loss_pct=rules.PVGIS_SYSTEM_LOSS_PCT.value,
        radiation_db=str(meteo.get("radiation_db", "PVGIS")),
        annual_kwh_per_kwp={int(year): float(kwh) for year, kwh in yearly.items()},
        monthly_kwh_per_kwp=[float(monthly.get(month, 0.0)) for month in range(1, 13)],
    )


class Pvgis:
    """Yearly yield per kWp for a location and roof plane, from cache or PVGIS."""

    def __init__(self, cache_dir: Path, fetch: Fetch | None = None) -> None:
        self._cache_dir = cache_dir
        self._fetch = fetch

    def _path(self, latitude: float, longitude: float, tilt: int, azimuth: int) -> Path:
        loss = rules.PVGIS_SYSTEM_LOSS_PCT.value
        name = f"{latitude:.2f}_{longitude:.2f}_t{tilt}_a{azimuth}_l{loss:g}.json"
        return self._cache_dir / name

    def per_kwp(
        self, latitude: float, longitude: float, tilt_deg: float, azimuth_deg: float
    ) -> YieldProfile:
        lat, lon = snap(latitude), snap(longitude)
        tilt, azimuth = round(tilt_deg), round(azimuth_deg) % 360
        path = self._path(lat, lon, tilt, azimuth)
        if path.exists():
            return YieldProfile.from_json(json.loads(path.read_text()))
        data, meta = (self._fetch or _pvgis_fetch)(
            lat, lon, tilt, azimuth, rules.PVGIS_SYSTEM_LOSS_PCT.value
        )
        profile = profile_from_series(data, meta, lat, lon, tilt, azimuth)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile.to_json(), indent="\t") + "\n")
        return profile
