"""Record modelled point output assigned to declared intervals, without new data."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar

from .canonical import Object
from .errors import InvalidInput


@dataclass(frozen=True)
class PvReconstruction:
    input_document_sha256: str
    target_axis_sha256: str
    input_max_interval_seconds: float
    output_max_interval_seconds: float
    method: ClassVar[str] = "representative_pv_output_over_declared_intervals_v1"
    exact_interval_copy: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if any(
            not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in (
                self.input_document_sha256,
                self.target_axis_sha256,
            )
        ) or any(
            type(value) not in (float, int) or not math.isfinite(value) or value <= 0
            for value in (
                self.input_max_interval_seconds,
                self.output_max_interval_seconds,
            )
        ):
            raise InvalidInput(
                "PV reconstruction requires exact input/axis and resolution"
            )

    def document(self) -> Object:
        return {
            "method": self.method,
            "input_document_sha256": self.input_document_sha256,
            "target_axis_sha256": self.target_axis_sha256,
            "input_max_interval_seconds": self.input_max_interval_seconds,
            "output_max_interval_seconds": self.output_max_interval_seconds,
            "exact_interval_copy": False,
            "native_value_semantics": "weather_records_with_separate_irradiance_instants",
            "output_value_semantics": "reconstructed_interval_average",
            "interval_assignment_basis": "explicit_model_policy_not_observed_interval_power",
            "energy_preservation_claim": False,
        }
