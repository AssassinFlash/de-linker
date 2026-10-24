"""Trusted original-weather intake; no browser capture or provider URL claims."""

from __future__ import annotations

from .assets import Asset, Assets
from .canonical import Object, digest
from .pv_parameters import PvGenerationLimits
from .pv_source import PvSource
from .records import Actor

WEATHER_PURPOSE = "pvgis_tmy_weather_v1"


class WeatherImport:
    def __init__(self, assets: Assets, limits: PvGenerationLimits) -> None:
        self.assets, self.limits = assets, limits

    def tmy(
        self, actor: Actor, project_id: str, source: PvSource, *, key: str
    ) -> Asset:
        self.assets.check_write(actor, project_id)
        logical: Object = {
            "schema": 1,
            "source_type": WEATHER_PURPOSE,
            "retention": "permanent",
            **source.metadata(),
        }
        previous = self.assets.receipt(
            actor,
            project_id,
            key,
            {
                "content_sha256": digest(source.content),
                "media_type": "application/json",
                "purpose": WEATHER_PURPOSE,
                "metadata": logical,
            },
        )
        if previous is not None:
            return previous
        weather = source.weather(self.limits)
        return self.assets.add(
            actor,
            project_id,
            source.content,
            "application/json",
            WEATHER_PURPOSE,
            {
                **logical,
                "limits": {**self.limits.model_dump(mode="json")},
                "weather": {
                    "latitude_deg": weather.latitude_deg,
                    "longitude_deg": weather.longitude_deg,
                    "altitude_m": weather.altitude_m,
                    "interval_count": len(weather.points),
                    "source": weather.source.document(),
                },
            },
            key=key,
            logical_metadata=logical,
        )
