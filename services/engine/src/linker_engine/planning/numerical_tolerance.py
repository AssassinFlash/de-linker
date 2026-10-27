"""Explicit floating-point settings; independent of physical safety margins."""

from __future__ import annotations

from dataclasses import dataclass

from .battery_model import nonnegative
from .canonical import Object


@dataclass(frozen=True)
class Tolerance:
    absolute_kwh: float
    absolute_kw: float
    relative: float

    def __post_init__(self) -> None:
        nonnegative(self.absolute_kwh, "energy tolerance")
        nonnegative(self.absolute_kw, "power tolerance")
        nonnegative(self.relative, "relative tolerance")

    def document(self) -> Object:
        return {
            "absolute_kwh": self.absolute_kwh,
            "absolute_kw": self.absolute_kw,
            "relative": self.relative,
            "role": "floating_point_arithmetic_not_engineering_margin",
        }
