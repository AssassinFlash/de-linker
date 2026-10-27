"""Mode-specific import/export/reserve conditions resolved before dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .battery_model import nonnegative
from .errors import InvalidInput


@dataclass(frozen=True)
class OperatingLimits:
    mode: Literal["connected", "outage"]
    reserve_kwh: float
    import_cap_kw: float | None
    export_cap_kw: float | None
    pv_enabled: bool
    allow_grid_charge: bool

    def __post_init__(self) -> None:
        if self.mode not in ("connected", "outage"):
            raise InvalidInput("connected/outage mode required")
        if (
            type(self.pv_enabled) is not bool
            or type(self.allow_grid_charge) is not bool
        ):
            raise InvalidInput("explicit mode capabilities required")
        nonnegative(self.reserve_kwh, "reserve")
        for name, value in (
            ("import cap", self.import_cap_kw),
            ("export cap", self.export_cap_kw),
        ):
            if value is not None:
                nonnegative(value, name)
        if self.mode == "outage" and self.allow_grid_charge:
            raise InvalidInput("grid charging cannot be enabled during an outage")

    def import_limit(self, demand_kw: float) -> float:
        if self.mode == "outage":
            return 0.0
        return (
            demand_kw
            if self.import_cap_kw is None
            else min(demand_kw, self.import_cap_kw)
        )

    def export_limit(self, surplus_kw: float) -> float:
        if self.mode == "outage":
            return 0.0
        return (
            surplus_kw
            if self.export_cap_kw is None
            else min(surplus_kw, self.export_cap_kw)
        )
