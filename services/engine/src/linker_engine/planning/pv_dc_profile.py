"""A typed DC projection of existing immutable PV producer artifacts.

The same representative-output interval assignment is retained. These values
are never recovered from clipped AC, and remain an unshaded reference scenario
with the producer's unresolved MPPT/equipment/shading limitations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .canonical import Object, decode_object, digest, encode
from .errors import EvidenceMissing, InvalidInput, NumericalFailure, VersionUnavailable
from .interval import Interval
from .power_series import PowerSeries, check_intervals
from .pv_profile_artifacts import model_dependencies, prepared_profile
from .pv_reconstruction import PvReconstruction
from .series_source import SeriesSource
from .series_transform import SeriesTransform
from .storage import Blobs

if TYPE_CHECKING:
    from .pv_generation import PvGeneration


@dataclass(frozen=True)
class DcPvProfile:
    intervals: tuple[Interval, ...]
    values_kw: tuple[float, ...]
    source: SeriesSource
    transformations: tuple[PvReconstruction | SeriesTransform, ...]
    converter_id: str
    array_ids: tuple[str, ...]
    model_inputs_sha256: str
    model_witness_sha256: str
    measurement: ClassVar[str] = "pv_available_dc"
    stage: ClassVar[str] = (
        "array_mpp_sum_after_declared_dc_factors_before_reference_ac_conversion"
    )

    def __post_init__(self) -> None:
        check_intervals(self.intervals)
        if len(self.intervals) != len(self.values_kw) or any(
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
            for value in self.values_kw
        ):
            raise InvalidInput(
                "one finite nonnegative DC value per declared interval required"
            )

    @property
    def total_kwh(self) -> float:
        try:
            total = math.fsum(
                power * interval.hours
                for power, interval in zip(self.values_kw, self.intervals, strict=True)
            )
        except (OverflowError, ValueError) as error:
            raise NumericalFailure(
                "integrated PV DC energy exceeds finite domain"
            ) from error
        if not math.isfinite(total):
            raise NumericalFailure("integrated PV DC energy exceeds finite domain")
        return total

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

    def document(self) -> Object:
        return {
            "schema": 1,
            "measurement": self.measurement,
            "stage": self.stage,
            "unit": "kW",
            "value_semantics": "reconstructed_interval_average",
            "intervals": [
                {"start_utc": item.start.isoformat(), "end_utc": item.end.isoformat()}
                for item in self.intervals
            ],
            "values": list(self.values_kw),
            "energy_kwh": self.total_kwh,
            "source": self.source.document(),
            "converter_id": self.converter_id,
            "array_ids": list(self.array_ids),
            "model_inputs_sha256": self.model_inputs_sha256,
            "model_witness_sha256": self.model_witness_sha256,
            "transformations": [item.document() for item in self.transformations],
        }


def project_dc(
    ac: PowerSeries,
    inputs: Object,
    witness: Object,
    witness_sha256: str,
    converter_id: str,
) -> DcPvProfile:
    parameters = inputs.get("parameters")
    groups = parameters.get("converters") if isinstance(parameters, dict) else None
    converters = witness.get("converters")
    if not isinstance(groups, list) or not isinstance(converters, list):
        raise EvidenceMissing(
            "pv_dc_stage: selected converter has no retained DC output"
        )
    group = [
        item
        for item in groups
        if isinstance(item, dict) and item.get("id") == converter_id
    ]
    retained = [
        item
        for item in converters
        if isinstance(item, dict) and item.get("id") == converter_id
    ]
    if len(group) != 1 or len(retained) != 1:
        raise EvidenceMissing(
            "pv_dc_stage: exactly one explicitly selected converter required"
        )
    row = retained[0]
    array_ids, values = row.get("array_ids"), row.get("dc_available_w")
    if (
        not isinstance(array_ids, list)
        or not array_ids
        or any(not isinstance(item, str) for item in array_ids)
        or array_ids != group[0].get("array_ids")
        or row.get("input_assumption") != group[0].get("input_assumption")
    ):
        raise VersionUnavailable("retained DC arrays differ from the pinned converter")
    if not isinstance(values, list) or len(values) != len(ac.intervals):
        raise EvidenceMissing("pv_dc_stage: complete finite DC output required")
    powers: list[float] = []
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise EvidenceMissing("pv_dc_stage: finite nonnegative DC output required")
        # SI conversion only; reference AC conversion and its clipping are
        # deliberately absent from this DC branch.
        powers.append(float(value) / 1000)
    details = decode_object(ac.source.details_json)
    details.update(
        {
            "output_boundary": DcPvProfile.stage,
            "converter_id": converter_id,
            "array_ids": array_ids,
            "model_witness_sha256": witness_sha256,
            "ac_conversion_applied": False,
        }
    )
    return DcPvProfile(
        ac.intervals,
        tuple(powers),
        SeriesSource(
            ac.source.raw_sha256,
            ac.source.origin,
            ac.source.timezone,
            ac.source.native_max_interval_seconds,
            encode(details),
        ),
        tuple(
            item for item in ac.transformations if isinstance(item, PvReconstruction)
        ),
        converter_id,
        tuple(str(item) for item in array_ids),
        ac.source.raw_sha256,
        witness_sha256,
    )


def from_generation(result: PvGeneration, converter_id: str) -> DcPvProfile:
    return project_dc(
        result.profile,
        decode_object(result.inputs_json),
        result.witness(),
        digest(result.witness_json),
        converter_id,
    )


def prepared_dc_profile(
    blobs: Blobs, raw_sha256: str, metadata: Object, converter_id: str
) -> DcPvProfile:
    # Reuse the existing hash/geometry/source/axis/temporal cross-binding. This
    # reads retained outputs; it does not rerun pvlib or require a new library.
    ac = prepared_profile(blobs, raw_sha256, metadata)
    dependencies = model_dependencies(metadata)
    return project_dc(
        ac,
        blobs.object(dependencies["pv_model_inputs"]),
        blobs.object(dependencies["pv_model_witness"]),
        dependencies["pv_model_witness"],
        converter_id,
    )
