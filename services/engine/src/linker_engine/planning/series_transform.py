"""A transformation identity and its loss of temporal information."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar

from .canonical import Object
from .errors import InvalidInput


@dataclass(frozen=True)
class SeriesTransform:
    input_document_sha256: str
    target_axis_sha256: str
    input_max_interval_seconds: float
    output_max_interval_seconds: float
    exact_interval_copy: bool
    method: ClassVar[str] = "energy_preserving_overlap_of_interval_means"

    def __post_init__(self) -> None:
        for sha256 in (self.input_document_sha256, self.target_axis_sha256):
            if not re.fullmatch(r"[a-f0-9]{64}", sha256):
                raise InvalidInput("transformation input and target hashes required")
        if (
            any(
                not math.isfinite(value) or value <= 0
                for value in (
                    self.input_max_interval_seconds,
                    self.output_max_interval_seconds,
                )
            )
            or type(self.exact_interval_copy) is not bool
        ):
            raise InvalidInput("transformation resolution/copy semantics required")

    def document(self) -> Object:
        return {
            "method": self.method,
            "input_document_sha256": self.input_document_sha256,
            "target_axis_sha256": self.target_axis_sha256,
            "input_max_interval_seconds": self.input_max_interval_seconds,
            "output_max_interval_seconds": self.output_max_interval_seconds,
            "exact_interval_copy": self.exact_interval_copy,
        }
