"""One validated original and its direct official-source transport receipt."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .canonical import Object
from .pv_source import PvSource
from .storage import Blobs
from .weather_fetch_plan import WeatherFetchPlan


@dataclass(frozen=True)
class WeatherDownload:
    source: PvSource
    transport_json: bytes

    def retain_evidence(self, blobs: Blobs) -> Object:
        return {
            "schema_version": 1,
            "kind": "official_jrc_weather_transport_evidence_v1",
            "dependencies": {"transport_receipt": blobs.put(self.transport_json)},
        }


class WeatherDownloader(Protocol):
    def close(self) -> None: ...

    def download(
        self,
        plan: WeatherFetchPlan,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> WeatherDownload: ...
