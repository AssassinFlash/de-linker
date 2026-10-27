"""Original official bytes with a server-authored capture, never browser testimony."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .pvgis_request import PvgisRequest
from .pvgis_response import PvgisCapture
from .weather_fetch_plan import WeatherFetchLimits


@dataclass(frozen=True)
class ReferenceCapture:
    content: bytes
    capture: PvgisCapture


class ReferenceDownloader(Protocol):
    def download(
        self,
        request: PvgisRequest,
        limits: WeatherFetchLimits,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> ReferenceCapture: ...

    def close(self) -> None: ...
