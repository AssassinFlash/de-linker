"""An explicit estimate from point samples, not energy-preserving resampling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from .canonical import Object
from .errors import InvalidInput


@dataclass(frozen=True)
class SampleReconstruction:
    input_document_sha256: str
    target_axis_sha256: str
    # This named model assigns one hourly observation to its containing UTC
    # hour. JRC describes an hourly-average assumption but does not define
    # this interval assignment mathematically; this is our declared policy.
    method: ClassVar[str] = "sample_value_over_containing_utc_hour_v1"
    input_max_interval_seconds: ClassVar[float] = 3600
    output_max_interval_seconds: ClassVar[float] = 3600
    exact_interval_copy: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if any(
            not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in (self.input_document_sha256, self.target_axis_sha256)
        ):
            raise InvalidInput("sample reconstruction input/axis hashes required")

    def document(self) -> Object:
        return {
            "method": self.method,
            "input_document_sha256": self.input_document_sha256,
            "target_axis_sha256": self.target_axis_sha256,
            "input_max_interval_seconds": self.input_max_interval_seconds,
            "output_max_interval_seconds": self.output_max_interval_seconds,
            "exact_interval_copy": False,
            "native_value_semantics": "instantaneous_sample",
            "output_value_semantics": "reconstructed_interval_average",
            "interval_assignment_basis": "explicit_model_policy_not_provider_interval_definition",
            "energy_preservation_claim": False,
        }
