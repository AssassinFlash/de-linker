"""Actual cited module fit with independent forward-string reference cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from conftest import SHIPPED_COMPATIBILITY, publication_feed
from pvlib import pvsystem
from scipy.optimize import minimize_scalar

from linker_engine.planning.canonical import Object
from linker_engine.planning.equipment_facts import compile_facts
from linker_engine.planning.pv_iv_model import derive_iv_model, model_point
from linker_engine.planning.pv_series_operating import series_operating_point


def test_fitted_module_series_conditions_follow_the_common_current() -> None:
    raw = json.loads((Path(__file__).parents[1] / "fixtures/feed.json").read_text())
    feed = publication_feed(raw, json.loads(SHIPPED_COMPATIBILITY.read_text()))
    facts = compile_facts(feed["overlay"][0])
    model = derive_iv_model(cast(Object, facts))
    assert model["status"] == "available"
    params = cast(dict[str, Any], model["parameters"])
    first = (np.array([1000.0, 1000.0, 0.0]), np.array([25.0, 25.0, 25.0]))
    second = (np.array([1000.0, 300.0, 800.0]), np.array([25.0, 25.0, 25.0]))
    actual = series_operating_point([first, second], params, (1.0, 1000.0), 100.0)
    reference = model_point(cast(Object, params), 1000, 25)
    assert actual.dc_w[0] == pytest.approx(2 * cast(float, reference["p_mp"]), rel=1e-8)
    assert actual.voltage_v[0] == pytest.approx(
        2 * cast(float, reference["v_mp"]), rel=1e-7
    )
    assert actual.current_a[0] == pytest.approx(reference["i_mp"], rel=1e-7)
    assert actual.dc_w[2] == 0
    one = [pvsystem.calcparams_desoto(g, 25, **params) for g in (1000.0, 300.0)]
    high = min(float(pvsystem.i_from_v(0, *p, method="lambertw")) for p in one)

    def watts(i: float) -> float:
        return i * sum(float(pvsystem.v_from_i(i, *p, method="lambertw")) for p in one)

    independently = minimize_scalar(
        lambda i: -watts(i), bounds=(0.0, high), method="bounded"
    )
    assert independently.success
    assert actual.dc_w[1] == pytest.approx(-independently.fun, rel=1e-8)
    independent_sum = sum(
        cast(float, model_point(cast(Object, params), g, 25)["p_mp"])
        for g in (1000.0, 300.0)
    )
    assert 0 < actual.dc_w[1] < independent_sum
    capped = series_operating_point([first, second], params, (1.0, 1000.0), 2.0)
    assert capped.current_a[0] <= 2
    assert capped.dc_w[0] < actual.dc_w[0]
    outside = series_operating_point([first, second], params, (200.0, 1000.0), 100.0)
    assert outside.dc_w[0] == 0


def test_real_roof_irradiance_flows_through_the_selected_woo_string() -> None:
    from linker_engine.planning.geometric_pv_generation import generate_geometric_pv
    from linker_engine.planning.geometric_pv_inputs import (
        ELECTRICAL_V3,
        MODEL_V3,
        POLICY_V2,
        GeometricPvInputs,
        GeometricPvLimits,
    )
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.woo_module import module_template

    from .test_geometric_pv import perez_parameters
    from .test_pv_generation import geometry, weather

    raw = json.loads((Path(__file__).parents[1] / "fixtures/feed.json").read_text())
    feed = publication_feed(raw, json.loads(SHIPPED_COMPATIBILITY.read_text()))
    reference = feed["overlay"][0]
    template = module_template(reference)
    geo = geometry()
    geo["module_specs"] = [{**template["specification"], "id": "module"}]
    geo["arrays"][0].update(rows=1, columns=6, excluded_slots=[])
    ids = [p.id for p in panel_poses(read_geometry(geo)) if p.included]
    inverter = next(item for item in feed["products"] if item["id"] == 4107)
    selection = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "battery_product_id": None,
        "modules_per_stack": None,
        "parallel_stacks": None,
        "accessory_product_ids": [],
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": 2.76,
        "required_usable_kwh": None,
        "required_discharge_ac_kw": None,
        "product_revisions": {"4107": inverter["product_revision"]},
    }
    wiring = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "minimum_ambient_c": None,
        "temperature_source": None,
        "strings": [{"id": "s1", "mppt": 1, "input": 1, "module_ids": ids}],
    }
    par = perez_parameters()
    par["modules"] = [{**template["parameters"], "module_spec_id": "module"}]
    par["converters"][0]["input_assumption"] = (
        "one_string_per_tracker_independent_mpp_sum"
    )
    request = GeometricPvInputs.read(
        {
            "schema_version": 1,
            "model": MODEL_V3,
            "weather_asset_id": "a" * 32,
            "sampling": {"coarse_cells_per_edge": 1, "fine_cells_per_edge": 2},
            "diffuse_policy": POLICY_V2,
            "thermal_policy": "sapm_from_module_mean_poa_v1",
            "electrical_policy": ELECTRICAL_V3,
            "parameters": par,
        }
    )
    basis = {
        "products": feed["products"],
        "pv_module_inputs": {"module": template, "electrical_product": reference},
    }
    limits = GeometricPvLimits(
        max_module_steps=10,
        max_samples=1000,
        max_ray_face_checks=100000,
        max_bounds_checks=100000,
        index_leaf_size=2,
    )
    result = generate_geometric_pv(
        geo,
        weather(),
        request,
        limits,
        max_weather_rows=10,
        electrical_inputs={"equipment_selection": selection, "pv_string_plan": wiring},
        electrical_basis=basis,
    )
    witness = result.witness()
    assert witness["kind"] == MODEL_V3
    string = cast(list[dict[str, Any]], witness["strings"])[0]
    assert string["module_ids"] == ids
    assert 180 <= string["voltage_v"][0] <= 900
    assert string["dc_available_w"][0] > 0
    assert result.profile.values_kw[0] > 0
    assert (
        "cell_substring_bypass_diode_and_reverse_breakdown"
        in witness["inputs"]["not_assessed"]
    )
