"""Convert verified PVGIS output to a named AC-scenario input exactly once."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from .canonical import Json, Object, digest, encode
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput
from .interval import Interval
from .power_series import PowerSeries
from .pvgis_response import PvgisSeries
from .sample_reconstruction import SampleReconstruction
from .series_source import SeriesSource
from .series_transform import SeriesTransform


class PvgisInterpretation(Document):
    schema_version: SchemaVersion
    temporal_policy: Literal[
        "era5_centered_hourly_means_v1",
        "sample_value_over_containing_utc_hour_v1",
    ]
    output_role: Literal["pv_available_ac"]
    system_power_policy: Literal["provider_system_output_no_second_loss_chain"]

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}


def pvgis_profile(
    native: PvgisSeries, interpretation: PvgisInterpretation
) -> PowerSeries:
    transformations: tuple[SeriesTransform | SampleReconstruction, ...]
    if native.value_semantics == "centered_hourly_mean":
        if interpretation.temporal_policy != "era5_centered_hourly_means_v1":
            raise InvalidInput("ERA5 requires its centered-hour mean interpretation")
        intervals = tuple(
            Interval(
                item.timestamp - timedelta(minutes=30),
                item.timestamp + timedelta(minutes=30),
            )
            for item in native.hours
        )
        transformations = ()
    else:
        if interpretation.temporal_policy != SampleReconstruction.method:
            raise InvalidInput(
                "SARAH instantaneous values require explicit reconstruction"
            )
        intervals = tuple(
            Interval(
                item.timestamp.replace(minute=0),
                item.timestamp.replace(minute=0) + timedelta(hours=1),
            )
            for item in native.hours
        )
        axis: list[Json] = [
            {"start_utc": item.start.isoformat(), "end_utc": item.end.isoformat()}
            for item in intervals
        ]
        transformations = (
            SampleReconstruction(
                digest(encode(native.source_document())), digest(encode(axis))
            ),
        )
    details = {
        **native.source_document(),
        "interpretation": interpretation.document(),
        "unit_conversion": "W / 1000 = kW; system losses already included",
    }
    source = SeriesSource(native.raw_sha256, "modelled", "UTC", 3600, encode(details))
    # JRC P is final modelled system power, normally AC, inclusive of the
    # explicit loss. No new module/inverter efficiency or percentage is applied.
    return PowerSeries(
        intervals,
        tuple(item.power_w / 1000 for item in native.hours),
        "pv_available_ac",
        source,
        transformations,
    )
