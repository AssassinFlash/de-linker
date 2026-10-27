"""Trusted original-weather intake; no browser capture or provider URL claims."""

from __future__ import annotations

from .assets import Asset, Assets
from .canonical import Object, digest
from .pv_parameters import PvGenerationLimits
from .pv_source import PvSource
from .records import Actor
from .weather_metadata import WEATHER_PURPOSE as WEATHER_PURPOSE
from .weather_metadata import weather_details, weather_identity


class WeatherImport:
    def __init__(self, assets: Assets, limits: PvGenerationLimits) -> None:
        self.assets, self.limits = assets, limits

    def tmy(
        self, actor: Actor, project_id: str, source: PvSource, *, key: str
    ) -> Asset:
        self.assets.check_write(actor, project_id)
        logical: Object = weather_identity(source)
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
        details = weather_details(
            source,
            max_bytes=self.limits.max_weather_bytes,
            max_rows=self.limits.max_weather_rows,
        )
        return self.assets.add(
            actor,
            project_id,
            source.content,
            "application/json",
            WEATHER_PURPOSE,
            {
                **logical,
                "limits": {**self.limits.model_dump(mode="json")},
                "weather": details,
            },
            key=key,
            logical_metadata=logical,
        )
