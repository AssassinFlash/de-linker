"""Interval-average kW with an explicit physical measurement boundary."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from .canonical import Json, Object
from .errors import InvalidInput
from .interval import Interval
from .sample_reconstruction import SampleReconstruction
from .series_source import SeriesSource
from .series_transform import SeriesTransform

type Measurement = Literal[
    "gross_load",
    "critical_load",
    "net_import",
    "pv_available_ac",
    "pv_generation_ac",
    "aux_ac",
]
MEASUREMENTS = (
    "gross_load",
    "critical_load",
    "net_import",
    "pv_available_ac",
    "pv_generation_ac",
    "aux_ac",
)


def check_intervals(intervals: tuple[Interval, ...]) -> None:
    if not intervals:
        raise InvalidInput("time series must contain at least one interval")
    for previous, current in zip(intervals, intervals[1:], strict=False):
        if current.start < previous.end:
            raise InvalidInput("intervals must be ordered and must not overlap")


@dataclass(frozen=True)
class PowerSeries:
    intervals: tuple[Interval, ...]
    values_kw: tuple[float, ...]
    measurement: Measurement
    source: SeriesSource
    transformations: tuple[SeriesTransform | SampleReconstruction, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "intervals", tuple(self.intervals))
        object.__setattr__(self, "transformations", tuple(self.transformations))
        check_intervals(self.intervals)
        if self.measurement not in MEASUREMENTS:
            raise InvalidInput("measurement boundary must be explicit")
        if len(self.values_kw) != len(self.intervals):
            raise InvalidInput("every interval requires one average power value")
        if any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or (self.measurement != "net_import" and value < 0)
            for value in self.values_kw
        ):
            raise InvalidInput(
                "finite power and a valid sign at this boundary required"
            )
        object.__setattr__(
            self, "values_kw", tuple(float(value) for value in self.values_kw)
        )

    @property
    def effective_max_interval_seconds(self) -> float:
        return max(
            [
                self.source.native_max_interval_seconds,
                *(
                    max(
                        item.input_max_interval_seconds,
                        item.output_max_interval_seconds,
                    )
                    for item in self.transformations
                ),
            ]
        )

    @property
    def reconstructed_means(self) -> bool:
        return any(not item.exact_interval_copy for item in self.transformations)

    @property
    def total_kwh(self) -> float:
        total = math.fsum(
            power * interval.hours
            for power, interval in zip(self.values_kw, self.intervals, strict=True)
        )
        if not math.isfinite(total):
            raise InvalidInput("integrated energy is not finite")
        return total

    def document(self) -> Object:
        intervals: list[Json] = [
            {
                "start_utc": interval.start.isoformat(),
                "end_utc": interval.end.isoformat(),
            }
            for interval in self.intervals
        ]
        return {
            "schema": 1,
            "measurement": self.measurement,
            "unit": "kW",
            "value_semantics": "interval_average",
            "intervals": intervals,
            "values": list(self.values_kw),
            "source": self.source.document(),
            "effective_max_interval_seconds": self.effective_max_interval_seconds,
            "reconstructed_means": self.reconstructed_means,
            "transformations": [item.document() for item in self.transformations],
        }
