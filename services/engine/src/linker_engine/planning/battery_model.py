"""A named single-AC-bus, constant-window battery model with explicit losses.

Parameters come from a pinned capability/scenario asset. This model alone does
not validate a product, mode, shared DC ports, temperature/SOC-dependent limits,
black start, phase behaviour or the controller's ability to execute a policy.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar

from .canonical import Object
from .errors import InvalidInput


def nonnegative(value: float, name: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise InvalidInput(f"{name} must be finite and nonnegative")


@dataclass(frozen=True)
class BatteryModel:
    usable_window_kwh: float
    charge_ac_kw: float
    discharge_ac_kw: float
    eta_charge: float
    eta_discharge: float
    internal_aux_kw: float
    standing_loss_rate_per_hour: float
    parameters_source_sha256: str
    version: ClassVar[str] = "constant_window_single_ac_bus_v1"

    def __post_init__(self) -> None:
        for name in (
            "usable_window_kwh",
            "charge_ac_kw",
            "discharge_ac_kw",
            "internal_aux_kw",
            "standing_loss_rate_per_hour",
        ):
            nonnegative(getattr(self, name), name)
        for name in ("eta_charge", "eta_discharge"):
            value = getattr(self, name)
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 < value <= 1
            ):
                raise InvalidInput(f"{name} must be in (0, 1]")
        if not re.fullmatch(r"[a-f0-9]{64}", self.parameters_source_sha256):
            raise InvalidInput("pinned battery/scenario parameters required")

    def document(self) -> Object:
        return {
            "version": self.version,
            "usable_window_kwh": self.usable_window_kwh,
            "charge_ac_kw": self.charge_ac_kw,
            "discharge_ac_kw": self.discharge_ac_kw,
            "eta_charge": self.eta_charge,
            "eta_discharge": self.eta_discharge,
            "internal_aux_kw": self.internal_aux_kw,
            "standing_loss_rate_per_hour": self.standing_loss_rate_per_hour,
            "parameters_source_sha256": self.parameters_source_sha256,
            "internal_loss_order": "standing_loss_then_internal_aux_before_ac_flows",
            "source_accounting": "proportional_mixing_v1",
            "battery_export": "excluded_from_this_model",
        }
