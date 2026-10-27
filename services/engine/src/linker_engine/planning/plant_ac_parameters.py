"""Reduce a Woo-derived battery-only DC path to its equivalent AC envelope.

This algebra is valid only when no PV shares the converter's DC bus. It
preserves the selected port/bank and all directional conversion losses; it
does not turn operating current or nominal power into a continuous rating.
The parent DC preparation retains every source, condition and limitation.
"""

from __future__ import annotations

from .battery_model import BatteryModel
from .dc_energy_parameters import DcPreparedParameters
from .errors import EvidenceMissing
from .plant_energy_model import StorageUnit


def storage_unit(
    unit_id: str, parameters: DcPreparedParameters, source_sha256: str
) -> StorageUnit:
    model = parameters.battery_model(source_sha256)

    def equivalent(mode: str) -> BatteryModel:
        bridge = model.bridge(mode)
        if bridge.reverse_supported is None:
            raise EvidenceMissing(
                "plant_ac_reverse_capability:" + unit_id,
                constraint_id="plant_ac_reverse_capability",
            )
        discharge = (
            min(
                model.discharge_terminal_kw * model.eta_battery_to_bus,
                bridge.forward_limit_dc_kw,
            )
            * bridge.eta_forward
        )
        if bridge.reverse_supported:
            assert bridge.eta_reverse is not None and bridge.reverse_ac_kw is not None
            reverse_dc = bridge.reverse_ac_kw * bridge.eta_reverse
            if bridge.reverse_dc_kw is not None:
                reverse_dc = min(reverse_dc, bridge.reverse_dc_kw)
            charge = (
                min(model.charge_terminal_kw / model.eta_bus_to_battery, reverse_dc)
                / bridge.eta_reverse
            )
            eta_c = (
                bridge.eta_reverse * model.eta_bus_to_battery * model.eta_store_charge
            )
        else:
            # An explicitly absent edge transfers zero energy. Identity here
            # is its inactive algebraic coefficient, not a device efficiency.
            charge, eta_c = 0.0, 1.0
        return BatteryModel(
            model.usable_window_kwh,
            charge,
            discharge,
            eta_c,
            model.eta_store_discharge * model.eta_battery_to_bus * bridge.eta_forward,
            model.internal_aux_kw,
            model.standing_loss_rate_per_hour,
            source_sha256,
        )

    return StorageUnit(
        unit_id,
        equivalent("connected"),
        equivalent("outage")
        if parameters.outage_bridge is not None
        and parameters.outage_bridge.reverse_supported is not None
        else None,
    )
