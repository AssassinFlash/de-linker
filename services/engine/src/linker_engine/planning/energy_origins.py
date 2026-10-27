"""Proportional-mixing energy accounts, all values in internal kWh.

This is a declared accounting convention, not identification of electrons.
Initial energy of unknown origin can never be relabelled as solar production.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .canonical import Object
from .errors import InvalidInput


@dataclass(frozen=True)
class EnergyOrigins:
    pv_kwh: float
    grid_kwh: float
    initial_unknown_kwh: float

    def __post_init__(self) -> None:
        if any(
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
            for value in (self.pv_kwh, self.grid_kwh, self.initial_unknown_kwh)
        ):
            raise InvalidInput("finite nonnegative source energy required")
        try:
            total = math.fsum((self.pv_kwh, self.grid_kwh, self.initial_unknown_kwh))
        except OverflowError as error:
            raise InvalidInput(
                "source inventory exceeds finite energy domain"
            ) from error
        if not math.isfinite(total):
            raise InvalidInput("source inventory exceeds finite energy domain")

    @property
    def total(self) -> float:
        return math.fsum((self.pv_kwh, self.grid_kwh, self.initial_unknown_kwh))

    def scaled(self, fraction: float) -> EnergyOrigins:
        if not math.isfinite(fraction) or fraction < 0:
            raise InvalidInput("nonnegative source allocation required")
        return EnergyOrigins(
            self.pv_kwh * fraction,
            self.grid_kwh * fraction,
            self.initial_unknown_kwh * fraction,
        )

    def plus(self, other: EnergyOrigins) -> EnergyOrigins:
        return EnergyOrigins(
            self.pv_kwh + other.pv_kwh,
            self.grid_kwh + other.grid_kwh,
            self.initial_unknown_kwh + other.initial_unknown_kwh,
        )

    def withdraw(self, requested_kwh: float) -> tuple[EnergyOrigins, EnergyOrigins]:
        if not math.isfinite(requested_kwh) or requested_kwh < 0:
            raise InvalidInput("finite nonnegative internal withdrawal required")
        # Saturate BEFORE delivery. The delivered amount is derived from this
        # actual withdrawal; there is no post-hoc E clamp hiding missing supply.
        fraction = min(requested_kwh / self.total, 1.0) if self.total else 0.0
        return self.scaled(1.0 - fraction), self.scaled(fraction)

    def document(self) -> Object:
        return {
            "pv_kwh": self.pv_kwh,
            "grid_kwh": self.grid_kwh,
            "initial_unknown_kwh": self.initial_unknown_kwh,
        }
