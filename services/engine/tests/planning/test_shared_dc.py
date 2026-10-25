"""Distinct shared-DC acceptance; no annual or existing AC replay repetition."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from linker_engine.planning.dc_battery_model import DcBatteryModel, DcPort, SharedBridge
from linker_engine.planning.dc_frame import DcFrame
from linker_engine.planning.dispatch_frame import Command
from linker_engine.planning.energy_origins import EnergyOrigins
from linker_engine.planning.errors import EvidenceMissing
from linker_engine.planning.interval import Interval
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.operating_limits import OperatingLimits
from linker_engine.planning.shared_dc_checks import verify
from linker_engine.planning.shared_dc_dispatch import replay, self_consumption, step

TOLERANCE = Tolerance(1e-8, 1e-8, 1e-10)
EMPTY = EnergyOrigins(0, 0, 0)


def model() -> DcBatteryModel:
    return DcBatteryModel(
        usable_window_kwh=20,
        battery=DcPort("synthetic-stack", 200, 400, 20, 20, 100, 100),
        selected_port=DcPort("synthetic-selected-port", 180, 500, 20, 20, 100, 100),
        pv_input_dc_kw=30,
        dc_dc_charge_bus_kw=20,
        dc_dc_discharge_bus_kw=20,
        eta_bus_to_battery=1,
        eta_battery_to_bus=1,
        eta_store_charge=1,
        eta_store_discharge=1,
        internal_aux_kw=0,
        standing_loss_rate_per_hour=0,
        connected_bridge=SharedBridge(10, 20, 1, False, None, None, None),
        outage_bridge=None,
        parameters_source_sha256="a" * 64,
    )


def frame(
    pv: float, load: float, *, hour: int = 0, grid_charge: bool = False
) -> DcFrame:
    start = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=hour)
    return DcFrame(
        Interval(start, start + timedelta(hours=1)),
        load,
        pv,
        0,
        0,
        OperatingLimits("connected", 0, None, 0, True, grid_charge),
        "gross_load",
    )


def test_pv_charges_before_clipping_and_retains_one_continuous_solar_inventory() -> (
    None
):
    physical = model()
    flows = replay(
        (frame(12, 10), frame(0, 2, hour=1)),
        physical,
        EMPTY,
        self_consumption,
        checkpoint=lambda: None,
    )
    first, last = flows
    assert (
        first.inverter_forward_ac_kw,
        first.pv_charge_bus_dc_kw,
        first.pv_curtailed_dc_kw,
    ) == (10, 2, 0)
    assert first.after == EnergyOrigins(2, 0, 0)
    assert last.before == first.after and last.after == EMPTY
    assert last.discharged_to_load_ac == EnergyOrigins(2, 0, 0)
    assert verify(flows, physical, TOLERANCE, initial=EMPTY, terminal_min_kwh=0).passed
    exported_instead_of_served = replace(
        first,
        frame=replace(
            first.frame, limits=replace(first.frame.limits, export_cap_kw=None)
        ),
        pv_to_load_ac_kw=0,
        export_ac_kw=10,
        unserved_load_ac_kw=10,
    )
    invalid = verify(
        (exported_instead_of_served,),
        physical,
        TOLERANCE,
        initial=EMPTY,
        terminal_min_kwh=None,
    )
    assert any(
        check.code == "load_before_pv_export" and not check.passed
        for check in invalid.checks
    )


def test_battery_request_uses_only_shared_headroom_and_does_not_discard_inventory() -> (
    None
):
    physical = model()
    initial = EnergyOrigins(0, 0, 5)
    flow = step(frame(8, 10), physical, initial, Command(0, 5))
    assert (
        flow.inverter_forward_ac_kw,
        flow.discharge_terminal_dc_kw,
        flow.discharge_command_unmet_dc_kw,
    ) == (10, 2, 3)
    assert flow.after == EnergyOrigins(0, 0, 3)
    assert flow.discharged_to_load_ac == EnergyOrigins(0, 0, 2)
    assert verify(
        (flow,), physical, TOLERANCE, initial=initial, terminal_min_kwh=None
    ).passed
    corrupted = replace(flow, inverter_forward_ac_kw=13)
    checked = verify(
        (corrupted,), physical, TOLERANCE, initial=initial, terminal_min_kwh=None
    )
    assert not checked.passed
    assert any(
        check.code == "shared_forward_ac_cap" and not check.passed
        for check in checked.checks
    )
    oversized = EnergyOrigins(0, 0, 21)
    entered_from_larger_window = step(
        frame(0, 1), replace(physical, usable_window_kwh=21), oversized, Command(0, 1)
    )
    invalid = verify(
        (entered_from_larger_window,),
        physical,
        TOLERANCE,
        initial=oversized,
        terminal_min_kwh=None,
    )
    assert any(
        check.code == "usable_window" and not check.passed for check in invalid.checks
    )
    tiny_frame = frame(0, 10)
    tiny_frame = replace(
        tiny_frame,
        interval=Interval(
            tiny_frame.interval.start,
            tiny_frame.interval.start + timedelta(microseconds=1),
        ),
    )
    one = EnergyOrigins(0, 0, 1)
    real_tiny = step(tiny_frame, physical, one, Command(0, 10))
    assert verify(
        (real_tiny,), physical, TOLERANCE, initial=one, terminal_min_kwh=None
    ).passed
    counterfeit = replace(real_tiny, before=EMPTY, after=EMPTY)
    invalid = verify(
        (counterfeit,), physical, TOLERANCE, initial=EMPTY, terminal_min_kwh=None
    )
    assert any(
        check.code == "inventory_discharge_power" and not check.passed
        for check in invalid.checks
    )


def test_reverse_support_and_each_loss_stage_are_explicit_and_applied_once() -> None:
    physical = model()
    request = frame(0, 0, grid_charge=True)
    refused = step(request, physical, EMPTY, Command(9, 0))
    assert (
        refused.charge_terminal_dc_kw == 0 and refused.charge_command_unmet_dc_kw == 9
    )
    pv_load_first = step(frame(5, 5, grid_charge=True), physical, EMPTY, Command(5, 0))
    assert pv_load_first.pv_to_load_ac_kw == 5
    assert pv_load_first.charge_terminal_dc_kw == 0 and pv_load_first.import_ac_kw == 0
    assert verify(
        (pv_load_first,), physical, TOLERANCE, initial=EMPTY, terminal_min_kwh=None
    ).passed
    unknown = replace(
        physical, connected_bridge=SharedBridge(10, 20, 1, None, None, None, None)
    )
    with pytest.raises(EvidenceMissing, match="reverse_conversion"):
        step(request, unknown, EMPTY, Command(9, 0))
    physical = replace(
        physical,
        connected_bridge=SharedBridge(10, 20, 0.8, True, 10, 9, 0.9),
        eta_bus_to_battery=0.8,
        eta_battery_to_bus=0.75,
        eta_store_charge=0.9,
        eta_store_discharge=0.8,
    )
    charged = step(request, physical, EMPTY, Command(9, 0))
    # AC10 -> bus9 -> terminal7.2 -> internal6.48. Neither maximum
    # efficiency nor AC energy is silently reused as battery-terminal energy.
    assert charged.import_ac_kw == pytest.approx(10)
    assert charged.grid_charge_bus_dc_kw == pytest.approx(9)
    assert charged.after.grid_kwh == pytest.approx(6.48)
    discharged = step(frame(0, 10, hour=1), physical, charged.after, Command(0, 20))
    assert discharged.discharged_to_load_ac.grid_kwh == pytest.approx(
        6.48 * 0.8 * 0.75 * 0.8
    )
    assert discharged.discharged_to_load_ac.pv_kwh == 0
    assert verify(
        (charged, discharged), physical, TOLERANCE, initial=EMPTY, terminal_min_kwh=None
    ).passed


def test_only_selected_port_intersects_battery_current_at_voltage_floor() -> None:
    physical = model()
    # A second port is not part of this graph. Selecting one 50A port with
    # a 30A battery gives200V*30A=6kW, never2*50A or nominal/max-voltage power.
    physical = replace(
        physical,
        battery=replace(physical.battery, charge_current_a=30, discharge_current_a=30),
        selected_port=replace(
            physical.selected_port, charge_current_a=50, discharge_current_a=50
        ),
    )
    assert physical.charge_terminal_kw == 6 and physical.discharge_terminal_kw == 6
    request = replace(frame(0, 20), aux_dc_kw=1)
    initial = EnergyOrigins(10, 5, 5)
    flow = step(request, physical, initial, Command(0, 10))
    assert flow.discharge_terminal_dc_kw == pytest.approx(6)
    assert flow.battery_to_aux_dc_kw == pytest.approx(1)
    assert flow.battery_to_inverter_dc_kw == pytest.approx(5)
    assert flow.after.total == pytest.approx(14)
    assert verify(
        (flow,), physical, TOLERANCE, initial=initial, terminal_min_kwh=None
    ).passed
