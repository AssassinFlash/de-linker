"""Read-only, offline counterexamples against the audited engine source.

Run from the research worktree with the project's existing engine venv Python.
Only writes the requested JSON result in this research folder.
Synthetic cases establish invariants/counterexamples, not site or field accuracy.
"""
from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/engine/src"))

from linker_engine import commercial, eligibility, htw, report, residential, stacking, strings, units
from linker_engine.compatibility import Compatibility
from linker_engine.engine import Engine
from linker_engine.models import CommercialInput, ResidentialInput
from linker_engine.products import Products
from linker_engine.pvgis import YieldProfile
from linker_engine.roof.citygml import RoofPlane, plane_of, read_buildings
from linker_engine.roof.packing import pack

FIXTURES = ROOT / "services/engine/tests/fixtures"
products = Products.load(FIXTURES / "feed.json")
compatibility = Compatibility.load(ROOT / "plugins/linker-commerce/data/compatibility.json")
module = products.module


class FixedYield:
    def __init__(self, kwh_per_kwp: float) -> None:
        self.kwh_per_kwp = kwh_per_kwp

    def per_kwp(self, latitude: float, longitude: float, tilt: float, azimuth: float) -> YieldProfile:
        return YieldProfile(latitude, longitude, round(tilt), round(azimuth), 14, "synthetic audit fixture", {2022: self.kwh_per_kwp, 2023: self.kwh_per_kwp}, [self.kwh_per_kwp / 12] * 12)


engine = Engine(products, compatibility, FixedYield(1024))  # type: ignore[arg-type]
out: dict[str, object] = {
    "baseline": "123aea571e80b5b1ba756816914ba86408866ba5",
    "method": "offline probes; shipped compatibility plus repository fixture feed; synthetic boundary inputs; no network or production",
    "module": {k: getattr(module, k) for k in ("model", "pmax_w", "length_m", "width_m")},
}

# A genuine geometry check: a 30-degree plane's 3D Newell area agrees
# with plan area / cos(tilt), with north/east axes unambiguously defined.
inclined = plane_of([(0, 0, 0), (10, 0, 0), (10, 8.660254037844386, 5), (0, 8.660254037844386, 5), (0, 0, 0)])
assert inclined is not None
assert (inclined.tilt_deg, inclined.azimuth_deg, inclined.area_m2) == (30.0, 180.0, 100.0)
out["newell_planar_geometry_control"] = dataclasses.asdict(inclined)

# CityGML interior rings are negative space. The current parser emits every
# posList as another roof face, so it counts the hole as additional roof.
xml = b'''<core:CityModel xmlns:core="http://www.opengis.net/citygml/2.0" xmlns:bldg="http://www.opengis.net/citygml/building/2.0" xmlns:gml="http://www.opengis.net/gml">
 <core:cityObjectMember><bldg:Building gml:id="audit-hole"><bldg:boundedBy><bldg:RoofSurface>
 <bldg:lod2MultiSurface><gml:MultiSurface><gml:surfaceMember><gml:Polygon>
 <gml:exterior><gml:LinearRing><gml:posList>0 0 0 10 0 0 10 10 0 0 10 0 0 0 0</gml:posList></gml:LinearRing></gml:exterior>
 <gml:interior><gml:LinearRing><gml:posList>3 3 0 3 7 0 7 7 0 7 3 0 3 3 0</gml:posList></gml:LinearRing></gml:interior>
 </gml:Polygon></gml:surfaceMember></gml:MultiSurface></bldg:lod2MultiSurface>
 </bldg:RoofSurface></bldg:boundedBy></bldg:Building></core:cityObjectMember></core:CityModel>'''
building = next(read_buildings(io.BytesIO(xml)))
packed_hole = [pack(p, module) for p in building.planes]
out["citygml_hole"] = {
    "expected_faces": 1, "expected_net_roof_m2": 84,
    "actual_faces": len(building.planes),
    "actual_sum_roof_m2": sum(p.area_m2 for p in building.planes),
    "actual_modules_by_face": [len(p.modules) for p in packed_hole],
    "interior_hole_preserved": False,
}
assert len(building.planes) == 2 and sum(p.area_m2 for p in building.planes) == 116

# The roof has a fixed integer module count; string routing must not invent
# extra panels merely to meet a minimum voltage. Find real fixture products
# and counts for which the actual current implementation does so.
increases = []
for inverter in products.in_class("inverters"):
    if inverter.application != "home":
        continue
    for roof_count in range(1, 41):
        kwp = roof_count * module.pmax_w / 1000
        if inverter.pv_input_kw is None or inverter.pv_input_kw < kwp:
            continue
        result = strings.layout(inverter, [kwp], module)
        if result.layout and result.layout.module_count > roof_count:
            increases.append({"inverter": inverter.model, "roof_count": roof_count, "roof_kwp": kwp, "string_count": result.layout.module_count, "string_kwp": result.layout.array_kwp, "groups": [dataclasses.asdict(g) for g in result.layout.strings]})
out["string_layout_roof_count_increases"] = increases[:8]
assert increases

# Full residential consumer proof for the first such eligible input: yield
# continues to use roof kWp while the BOM consumes the altered string count.
full_mismatches = []
for roof_count in range(1, 41):
    kwp = roof_count * module.pmax_w / 1000
    req = ResidentialInput(plz="80538", annual_kwh=4000, pv_kwp=kwp, planes=[{"kwp": kwp, "tilt_deg": 35, "azimuth_deg": 180}], roof_source="drawn", phase=3)
    design = residential.design(engine, req)
    if design.selected and design.selected.strings and design.selected.strings.module_count > roof_count:
        full_mismatches.append({"input_roof_count": roof_count, "input_kwp": kwp, "selected_inverter": design.selected.inverter.model, "string_count": design.selected.strings.module_count, "string_kwp": design.selected.strings.array_kwp, "yield_planes_kwp": sum(p.kwp for p in design.yield_.planes), "yield_mean_kwh": design.yield_.kwh_year_mean, "bom_module_quantities": [line.quantity for line in design.selected.lines if line.role == "pv_module"]})
out["full_residential_roof_to_bom_increases"] = full_mismatches
assert full_mismatches

# An 8-hour continuous peak is bisected by midnight. The cap cannot recharge
# the battery during that event, regardless of charging strategy or efficiency.
load = [0.0] * (96 * 7)
load[3 * 96 - 16:3 * 96 + 16] = [20.0] * 32
shaved = commercial.shave(load, 10)
lower_bound = 8 * (20 - 10) / 0.94
out["cross_midnight_peak"] = {"event_hours": 8, "peak_kw": 20, "cap_kw": 10, "engine": dataclasses.asdict(shaved), "physical_usable_energy_lower_bound_kwh": lower_bound, "undersizing_factor": lower_bound / shaved.energy_kwh}
assert shaved.energy_kwh < lower_bound / 1.99

# Daily room equals the AC discharge need, yet is less than required battery
# replenishment even if charging is lossless; the warning still says zero.
tight_load = ([20.0] * 4 + [0.0] * 4 + [10.0] * 88) * 7
tight = commercial.shave(tight_load, 10)
out["recharge_energy_balance"] = {"engine": dataclasses.asdict(tight), "daily_ac_discharge_need_kwh": 10, "daily_grid_headroom_kwh": 10, "battery_energy_drawn_at_engine_eta_kwh": 10 / 0.94, "minimum_charge_energy_if_lossless_kwh": 10 / 0.94}
assert tight.short_days == 0

# CSV takes the last numeric cell, never verifies timestamps or intervals.
hourly = "timestamp;load_kW\n" + "\n".join(f"2026-01-{1 + i // 24:02d}T{i % 24:02d}:00:00;20" for i in range(672))
parsed = commercial.parse_load_profile(hourly, "kW")
with_counter = "timestamp;load_kW;row_id\n" + "\n".join(f"same-timestamp;20;{i + 1}" for i in range(672))
counter = commercial.parse_load_profile(with_counter, "kW")
out["csv_time_and_column_semantics"] = {"hourly_samples": 672, "true_days_in_hourly_fixture": 28, "engine_days": commercial.summary(parsed).days, "accepted_repeated_timestamps_with_extra_numeric_column": True, "true_load_peak_kw": 20, "extra_column_engine_peak_kw": max(counter), "extra_column_first_values": counter[:5]}

# Supplying PV and an explicit self-consumption goal changes nothing in the
# exact same CSV sized branch: the input is accepted but not consumed.
def commercial_request(**changes: object) -> CommercialInput:
    values = {"plz": "80538", "grid_connection_kva": 135, "annual_kwh": 400000, "goals": ["peak_shaving"], "target_peak_kw": 10, "load_profile_csv": "\n".join(map(str, load))}
    values.update(changes)
    return CommercialInput.model_validate(values)

ci_base = commercial.design(engine, commercial_request(), "audit")
ci_pv = commercial.design(engine, commercial_request(goals=["peak_shaving", "self_consumption"], pv_kwp=1000), "audit")
out["commercial_joint_pv_path"] = {"base": ci_base.model_dump(), "with_self_consumption_and_1000kwp": ci_pv.model_dump(), "identical_entire_result": ci_base == ci_pv}
assert ci_base == ci_pv

# Hardware capability cannot exceed the battery's own documented limit.
# The source is the repository fixture field, not a newly fetched PDF.
hardware = commercial.systems(engine, 75, 60, "en")
out["commercial_battery_power_ignored"] = {
    "requested_kw": 75,
    "requested_kwh": 60,
    "first_system": hardware[0].model_dump(),
    "battery_power_figure": dataclasses.asdict(products.by_id[1954].figures["max_charge_discharge_power_kw"]),
    "source_caveat": "fixture reproduces the data consumer; original hosted PDF not re-fetched in this probe",
}
assert hardware[0].power_kw == 80 and hardware[0].battery.id == 1954

# The all-in-one's initial power count passes as a single unit; then increasing
# units to reach energy silently bypasses the initial parallel-release gate.
cabinet = products.by_id[6321]
cabinet_parallel = compatibility.requirements(cabinet.model, "parallel_controller")
expanded = commercial.systems(engine, 100, 600, "en")
out["commercial_cabinet_parallel_gate_bypassed"] = {
    "requested_kw": 100, "requested_kwh": 600,
    "parallel_contract_count": len(cabinet_parallel),
    "systems": [s.model_dump() for s in expanded],
}
assert not cabinet_parallel and expanded[0].inverter_units == 3

# Show the independent roof-dependent yield and roof-independent HTW metrics
# in one full response. This is a data-flow proof, not PVGIS accuracy testing.
req = ResidentialInput(plz="80538", annual_kwh=4000, pv_kwp=5.52, phase=3)
low = residential.design(Engine(products, compatibility, FixedYield(400)), req)  # type: ignore[arg-type]
high = residential.design(Engine(products, compatibility, FixedYield(1400)), req)  # type: ignore[arg-type]
out["pvgis_htw_disconnection"] = {"low_yield_kwh": low.yield_.kwh_year_mean, "high_yield_kwh": high.yield_.kwh_year_mean, "low_metrics": low.metrics.model_dump() if low.metrics else None, "high_metrics": high.metrics.model_dump() if high.metrics else None, "identical_metrics": low.metrics == high.metrics, "lossless_autarky_upper_bound_low_yield": low.yield_.kwh_year_mean / req.annual_kwh}
assert low.metrics and low.metrics == high.metrics
assert low.metrics.autarky_range.low > low.yield_.kwh_year_mean / req.annual_kwh

# Positive controls: source-independent dimensional arithmetic, exact table
# node lookup, explicit unknown gates, and overlapping release strictness.
use = htw.consumption(4000, False, False)
upper = htw.size(10, use, 0)
assert upper.low_kwh == upper.high_kwh == min(1.5 * 10, 1.5 * 4) == 6
assert not htw.size(1.5, htw.consumption(5000, False, False), 0).recommended
assert units.kilo("10000", "W") == 10 and units.kwh("5000", "Wh") == 5
assert units.kilo("10000", "unrecognized") is None
assert eligibility.phase(dataclasses.replace(products.by_id[4107], phase=None), 3).passed is None
assert compatibility.pair("nonexistent", "nonexistent").verdict == "unknown"
assert compatibility.pair("H2-10K-T3", "B2-5.0-HV1").verdict == "not_released"
table = htw._table("tabelleAutarkie.json")
assert htw.lookup(table, table[0][17], table[17][0]) == table[17][17]
out["positive_method_controls"] = {
    "storage_10kwp_4000kwh_upper_kwh": upper.high_kwh,
    "small_pv_rejected_for_cycling": True,
    "w_to_kw_and_wh_to_kwh": True,
    "unrecognized_unit_stays_unknown": True,
    "unknown_phase_stays_unknown": True,
    "unknown_pair_stays_unknown": True,
    "narrow_rejection_overrides_family_release": True,
    "exact_htw_table_node_preserved": True,
}

# Capacity-only backup selection can accept an outage load twice the
# chosen inverter's AC rating: this proves the stated scope of the gate.
backup_req = ResidentialInput(plz="80538", annual_kwh=4000, pv_kwp=5.52, phase=3, backup="needed", backup_load_kw=10, backup_hours=0.5)
backup = residential.design(engine, backup_req)
assert backup.selected and backup.selected.battery
selected_inv = products.by_id[backup.selected.inverter.id]
out["backup_power_not_an_eligibility_gate"] = {
    "requested_backup_kw": 10,
    "requested_backup_hours": 0.5,
    "reserve_kwh": backup.sizing.reserve_kwh,
    "selected_inverter": selected_inv.model,
    "inverter_ac_power_kw": selected_inv.ac_power_kw,
    "available_backup_figure": dataclasses.asdict(selected_inv.figures["backup_power_kw"]) if "backup_power_kw" in selected_inv.figures else None,
    "selected_battery_kwh": backup.selected.battery.usable_kwh,
    "eligibility_rules": [r.model_dump() for r in backup.selected.inverter_rules],
}
assert selected_inv.ac_power_kw < 10

# Fault injection preserves release evidence but removes the required BC2
# from the product feed. The design remains selected; its BOM drops BC2.
missing_products = dataclasses.replace(products, products=tuple(p for p in products.products if p.model != "BC2-HV1"))
missing_engine = Engine(missing_products, compatibility, FixedYield(1024))  # type: ignore[arg-type]
missing_req = ResidentialInput(plz="80538", annual_kwh=4000, pv_kwp=5.52, phase=3, inverter_id=4107, battery_id=2090)
missing_design = residential.design(missing_engine, missing_req)
assert missing_design.selected and missing_design.selected.battery
out["required_accessory_missing_feed_fault_injection"] = {
    "injected_change": "removed BC2-HV1 product from fixture feed; unchanged shipped release requires that accessory",
    "selected_inverter": missing_design.selected.inverter.model,
    "selected_battery": missing_design.selected.battery.product.model,
    "release": missing_design.selected.battery.release.model_dump(),
    "actual_bom_models": [line.product.model for line in missing_design.selected.lines if line.product],
    "design_still_selected": True,
}
assert "BC2-HV1" not in out["required_accessory_missing_feed_fault_injection"]["actual_bom_models"]

# Fault injection proves these physical fields currently have no consumer in
# stacking. It does not allege an actual field pair is invalid: voltage ports
# and any converter architecture must be understood before comparing ranges.
inv = products.by_id[4107]
bat = products.by_id[2090]
pair = compatibility.pair(inv.model, bat.model)
initial_configs = stacking.configurations(inv, bat, pair)
fig = next(iter(bat.figures.values()))
bad_bat = dataclasses.replace(bat, figures={**bat.figures, "system_operating_voltage_range_v": dataclasses.replace(fig, value="2000 ~ 2500", unit="V"), "max_discharge_current_a": dataclasses.replace(fig, value="0.01", unit="A")})
after_configs = stacking.configurations(inv, bad_bat, pair)
out["battery_electrical_constraints_fault_injection"] = {
    "injected_change": "battery operating voltage 2000–2500V and maximum discharge current 0.01A; unchanged release/quantity data",
    "original_quantities_energy": [(c.quantity, c.usable_kwh) for c in initial_configs],
    "mutated_quantities_energy": [(c.quantity, c.usable_kwh) for c in after_configs],
    "unchanged": [(c.quantity, c.usable_kwh) for c in initial_configs] == [(c.quantity, c.usable_kwh) for c in after_configs],
    "scope": "data-consumer dependency proof; not a real product voltage failure",
}
assert out["battery_electrical_constraints_fault_injection"]["unchanged"]

# Final report drops roof packing assumptions and geometry. The request has
# only source enum and angle/kWp; the report cannot recreate the chosen roof.
roof_values = {**req.model_dump(), "planes": [{"kwp": 5.52, "tilt_deg": 35, "azimuth_deg": 180}], "roof_source": "drawn"}
roof_req = ResidentialInput.model_validate(roof_values)
roof_design = residential.design(engine, roof_req)
roof_report = report.residential(roof_design, "audit")
out["roof_report_provenance"] = {"roof_input_fields": list(roof_req.model_dump()), "roof_report": roof_report.model_dump(), "report_unverified_rule_ids": [rule.id for rule in report.UNVERIFIED], "roof_assumption_ids_omitted": sorted(report.ROOF_ASSUMPTIONS)}

target = Path(__file__).with_name("probe-results.json")
target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"result_file": str(target), "counterexample_groups": len(out) - 3, "full_bom_mismatches": full_mismatches[:3], "cross_midnight": out["cross_midnight_peak"], "joint_pv_identical": ci_base == ci_pv, "htw_invariant": low.metrics == high.metrics}, indent=2, ensure_ascii=False))
