"""Versioned native DC parameter snapshot; device facts are server-derived Woo data.

Only loss/auxiliary assumptions are scenario inputs. Product voltage, current,
power, energy and selected-port capability are never customer-supplied fields.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .canonical import Object
from .dc_battery_model import DcBatteryModel, DcPort, SharedBridge
from .energy_inputs import (
    Document,
    Identifier,
    Nonnegative,
    PositiveEfficiency,
    SchemaVersion,
)

type Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class DcLossScenario(Document):
    schema_version: SchemaVersion
    model: Literal["constant_window_shared_dc_bus_v1"]
    parameter_basis: Literal["explicit_loss_scenario_with_woo_equipment"]
    battery_port_id: Identifier
    eta_bus_to_battery: PositiveEfficiency
    eta_battery_to_bus: PositiveEfficiency
    eta_store_charge: PositiveEfficiency
    eta_store_discharge: PositiveEfficiency
    eta_inverter_forward: PositiveEfficiency
    eta_inverter_reverse: PositiveEfficiency | None
    internal_aux_kw: Nonnegative
    standing_loss_rate_per_hour: Nonnegative
    source_note: Identifier


class DcPortDocument(Document):
    id: Identifier
    operating_min_v: Nonnegative
    operating_max_v: Nonnegative
    charge_power_limit_kw: Nonnegative | None
    discharge_power_limit_kw: Nonnegative | None
    charge_current_a: Nonnegative
    discharge_current_a: Nonnegative

    def port(self) -> DcPort:
        return DcPort(**self.model_dump())


class SharedBridgeDocument(Document):
    forward_ac_kw: Nonnegative
    forward_dc_kw: Nonnegative | None
    eta_forward: PositiveEfficiency
    reverse_supported: bool | None
    reverse_ac_kw: Nonnegative | None
    reverse_dc_kw: Nonnegative | None
    eta_reverse: PositiveEfficiency | None

    def bridge(self) -> SharedBridge:
        return SharedBridge(**self.model_dump())


class DcPreparedParameters(Document):
    schema_version: SchemaVersion
    model: Literal["constant_window_shared_dc_bus_v1"]
    parameter_basis: Literal["woo_selected_equipment_with_explicit_loss_scenario"]
    loss_scenario: DcLossScenario
    selection_sha256: Hash
    product_revisions: dict[str, Hash]
    source_facts: Object
    usable_window_kwh: Nonnegative
    battery: DcPortDocument
    selected_port: DcPortDocument
    pv_input_dc_kw: Nonnegative | None
    dc_dc_charge_bus_kw: Nonnegative | None
    dc_dc_discharge_bus_kw: Nonnegative | None
    connected_bridge: SharedBridgeDocument
    outage_bridge: SharedBridgeDocument | None

    @model_validator(mode="after")
    def validate_graph(self) -> DcPreparedParameters:
        self.battery_model("0" * 64)
        if self.selected_port.id != self.loss_scenario.battery_port_id:
            raise ValueError(
                "prepared DC port differs from the explicitly selected port"
            )
        return self

    def battery_model(self, source_sha256: str) -> DcBatteryModel:
        assumptions = self.loss_scenario
        return DcBatteryModel(
            self.usable_window_kwh,
            self.battery.port(),
            self.selected_port.port(),
            self.pv_input_dc_kw,
            self.dc_dc_charge_bus_kw,
            self.dc_dc_discharge_bus_kw,
            assumptions.eta_bus_to_battery,
            assumptions.eta_battery_to_bus,
            assumptions.eta_store_charge,
            assumptions.eta_store_discharge,
            assumptions.internal_aux_kw,
            assumptions.standing_loss_rate_per_hour,
            self.connected_bridge.bridge(),
            self.outage_bridge.bridge() if self.outage_bridge else None,
            source_sha256,
        )
