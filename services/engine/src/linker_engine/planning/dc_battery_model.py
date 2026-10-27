"""One selected battery port and one shared bridge, with explicit DC stages.

Topology and equations: NUMERICAL-MODELS.md §12. Fixed efficiencies describe
this pinned scenario; neither maximum/Euro efficiency nor fault/peak current
can supply these parameters. No unused port contributes to the selected port.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import ClassVar

from .battery_model import nonnegative
from .canonical import Object, decode_object, encode
from .errors import InvalidInput, MethodDomainExceeded


def efficiency(value: float, name: str) -> None:
    nonnegative(value, name)
    if not 0 < value <= 1:
        raise InvalidInput(f"{name} must be in (0, 1]")


@dataclass(frozen=True)
class DcPort:
    id: str
    operating_min_v: float
    operating_max_v: float
    charge_power_limit_kw: float | None
    discharge_power_limit_kw: float | None
    charge_current_a: float
    discharge_current_a: float

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise InvalidInput("an explicitly selected DC port is required")
        for name, value in asdict(self).items():
            if name != "id" and value is not None:
                nonnegative(value, name)
        if not 0 < self.operating_min_v <= self.operating_max_v:
            raise InvalidInput(
                "an ordered positive operating-voltage range is required"
            )


@dataclass(frozen=True)
class SharedBridge:
    forward_ac_kw: float
    forward_dc_kw: float | None
    eta_forward: float
    reverse_supported: bool | None
    reverse_ac_kw: float | None
    reverse_dc_kw: float | None
    eta_reverse: float | None

    def __post_init__(self) -> None:
        nonnegative(self.forward_ac_kw, "forward AC limit")
        if self.forward_dc_kw is not None:
            nonnegative(self.forward_dc_kw, "forward DC limit")
        efficiency(self.eta_forward, "forward efficiency")
        if (
            self.reverse_supported is not None
            and type(self.reverse_supported) is not bool
        ):
            raise InvalidInput(
                "explicit true/false/unknown reverse capability required"
            )
        if self.reverse_supported is True:
            if self.reverse_ac_kw is None or self.eta_reverse is None:
                raise InvalidInput(
                    "supported reverse conversion needs its own limits and efficiency"
                )
            nonnegative(self.reverse_ac_kw, "reverse AC limit")
            if self.reverse_dc_kw is not None:
                nonnegative(self.reverse_dc_kw, "reverse DC limit")
            efficiency(self.eta_reverse, "reverse efficiency")
        elif any(
            value is not None
            for value in (self.reverse_ac_kw, self.reverse_dc_kw, self.eta_reverse)
        ):
            raise InvalidInput(
                "unknown/unsupported reverse conversion cannot carry assumed parameters"
            )

    @property
    def forward_limit_dc_kw(self) -> float:
        converted_limit = self.forward_ac_kw / self.eta_forward
        return (
            converted_limit
            if self.forward_dc_kw is None
            else min(self.forward_dc_kw, converted_limit)
        )


@dataclass(frozen=True)
class DcBatteryModel:
    usable_window_kwh: float
    battery: DcPort
    selected_port: DcPort
    pv_input_dc_kw: float | None
    dc_dc_charge_bus_kw: float | None
    dc_dc_discharge_bus_kw: float | None
    eta_bus_to_battery: float
    eta_battery_to_bus: float
    eta_store_charge: float
    eta_store_discharge: float
    internal_aux_kw: float
    standing_loss_rate_per_hour: float
    connected_bridge: SharedBridge
    outage_bridge: SharedBridge | None
    parameters_source_sha256: str
    version: ClassVar[str] = "constant_window_shared_dc_bus_v1"

    def __post_init__(self) -> None:
        for name in (
            "usable_window_kwh",
            "pv_input_dc_kw",
            "dc_dc_charge_bus_kw",
            "dc_dc_discharge_bus_kw",
            "internal_aux_kw",
            "standing_loss_rate_per_hour",
        ):
            value = getattr(self, name)
            if value is not None:
                nonnegative(value, name)
        for name in (
            "eta_bus_to_battery",
            "eta_battery_to_bus",
            "eta_store_charge",
            "eta_store_discharge",
        ):
            efficiency(getattr(self, name), name)
        if not (
            self.selected_port.operating_min_v
            <= self.battery.operating_min_v
            <= self.battery.operating_max_v
            <= self.selected_port.operating_max_v
        ):
            raise InvalidInput(
                "selected port must support the battery's complete declared voltage range"
            )
        if not isinstance(self.parameters_source_sha256, str) or not re.fullmatch(
            r"[a-f0-9]{64}", self.parameters_source_sha256
        ):
            raise InvalidInput("pinned DC scenario parameters required")
        if not all(
            math.isfinite(value)
            for value in (self.charge_terminal_kw, self.discharge_terminal_kw)
        ):
            raise InvalidInput("DC port capability exceeds finite numerical domain")

    @property
    def charge_terminal_kw(self) -> float:
        # P=VI, using the battery's voltage floor, conservatively intersects
        # one battery and ONE selected port; 1000 W per kW is an SI conversion.
        limits = [
            self.battery.operating_min_v
            * min(self.battery.charge_current_a, self.selected_port.charge_current_a)
            / 1000
        ]
        limits.extend(
            value
            for value in (
                self.battery.charge_power_limit_kw,
                self.selected_port.charge_power_limit_kw,
            )
            if value is not None
        )
        if self.dc_dc_charge_bus_kw is not None:
            limits.append(self.dc_dc_charge_bus_kw * self.eta_bus_to_battery)
        return min(limits)

    @property
    def discharge_terminal_kw(self) -> float:
        limits = [
            self.battery.operating_min_v
            * min(
                self.battery.discharge_current_a, self.selected_port.discharge_current_a
            )
            / 1000
        ]
        limits.extend(
            value
            for value in (
                self.battery.discharge_power_limit_kw,
                self.selected_port.discharge_power_limit_kw,
            )
            if value is not None
        )
        if self.dc_dc_discharge_bus_kw is not None:
            limits.append(self.dc_dc_discharge_bus_kw / self.eta_battery_to_bus)
        return min(limits)

    def bridge(self, mode: str) -> SharedBridge:
        if mode == "connected":
            return self.connected_bridge
        if mode == "outage" and self.outage_bridge is not None:
            return self.outage_bridge
        raise MethodDomainExceeded(
            "shared DC scenario has no bridge for this operating mode"
        )

    def document(self) -> Object:
        return {
            **decode_object(encode(asdict(self))),
            "version": self.version,
            "charge_terminal_kw": self.charge_terminal_kw,
            "discharge_terminal_kw": self.discharge_terminal_kw,
            "power_bound_method": "voltage_floor_current_cap_one_selected_port_v1",
            "pv_boundary": "available_dc_at_bus_before_shared_inverter",
            "command_boundary": "battery_dc_terminal",
            "internal_loss_order": "standing_loss_then_internal_aux_before_dc_flows",
            "source_accounting": "proportional_mixing_v1",
            "battery_export": "excluded_from_this_model",
            "priority": "dc_aux_then_ac_load_then_ac_aux_then_storage_then_pv_export",
        }
