"""Independent beam/diffuse/thermal ledger and real owned full-source adapter."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import replace
from typing import Any, cast

import numpy as np
import pytest

from linker_engine.planning.canonical import Object, decode_object
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geometric_pv_generation import generate_geometric_pv
from linker_engine.planning.geometric_pv_inputs import (
    MODEL,
    GeometricPvInputs,
    GeometricPvLimits,
)
from linker_engine.planning.geometric_pv_report import geometric_pv_reference
from linker_engine.planning.pv_arrays import generation_arrays
from linker_engine.planning.pv_generation import generate_pv
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.pv_physics import array_power

from .test_pv_generation import geometry, parameter_document, weather


def test_partial_beam_factor_precedes_mean_module_thermal_and_dc_response() -> None:
    geo, par = geometry(), parameter_document()
    geo["module_specs"][0]["stc_power_w"] = 1000
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    par["arrays"][0]["thermal"].update(a=-3.47, b=0, delta_t_c=3)
    parameters = PvGenerationParameters.read(par)
    meteo = weather(ghi=500, dni=800, dhi=100, temp=25)
    array = generation_arrays(geo, meteo, parameters)[0]
    output = array_power(
        array,
        parameters.arrays[0],
        parameters.modules[0],
        meteo,
        {
            "apparent_zenith_deg": np.array([60.0]),
            "azimuth_deg": np.array([180.0]),
            "dni_extra_w_m2": np.array([1366.1]),
        },
        direct_beam_fraction=np.array([0.5]),
    )
    # Horizontal beam=800*cos60=400, then geometric0.5 =>200. The100
    # diffuse component is not multiplied by0.5. Temperature responds to300.
    expected_temperature = 25 + 300 * math.exp(-3.47) + 0.3 * 3
    expected_dc = 1000 * 0.3 * (1 - 0.004 * (expected_temperature - 25))
    poa = cast(Object, output.witness["poa_components_w_m2"])
    assert poa["poa_direct"] == pytest.approx([200], abs=1e-10)
    assert poa["poa_sky_diffuse"] == [100]
    assert poa["poa_global"] == pytest.approx([300], abs=1e-10)
    assert output.witness["cell_temperature_c"] == pytest.approx(
        [expected_temperature], abs=1e-10
    )
    assert output.dc_w.tolist() == pytest.approx([expected_dc], abs=1e-10)


def test_geometric_direction_and_profile_stay_unspelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import Iterable

    import linker_engine.planning.geometric_pv_generation as geometric_pv
    import linker_engine.planning.pv_physics as pv_physics
    from linker_engine.planning.direct_beam_visibility import visibility_row
    from linker_engine.planning.geometry import sin_cos_degrees
    from linker_engine.planning.pv_physics import sun

    geo, par = geometry(), parameter_document()
    geo["module_specs"][0].update(length_m=1, width_m=1, stc_power_w=1000)
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    meteo = weather(dni=600, dhi=100, ghi=800, temp=25)
    request = scenario(par)
    limits = policy()
    recorded: list[float] = []
    directions: list[tuple[float, float, float]] = []

    def spy(degrees: float) -> tuple[float, float]:
        recorded.append(degrees)
        return sin_cos_degrees(degrees)

    def capture_row(*args: object, **kwargs: object) -> object:
        direction = args[1]
        assert isinstance(direction, tuple)
        x, y, z = (float(part) for part in direction)
        directions.append((x, y, z))
        return cast(Any, visibility_row)(*args, **kwargs)

    monkeypatch.setattr(geometric_pv, "sin_cos_degrees", spy)
    monkeypatch.setattr(geometric_pv, "visibility_row", capture_row)
    baseline = generate_geometric_pv(geo, meteo, request, limits, max_weather_rows=10)
    solar = sun(meteo)
    assert recorded[:2] == [
        float(solar["apparent_zenith_deg"][0]),
        float(solar["azimuth_deg"][0]),
    ]
    zenith, azimuth = recorded[0], recorded[1]
    sz, cz = sin_cos_degrees(zenith)
    sa, ca = sin_cos_degrees(azimuth)
    baseline_direction = (sz * sa, sz * ca, cz)
    assert directions == [baseline_direction]

    def zeros(items: Iterable[float]) -> list[float]:
        return [0.0 for _ in items]

    monkeypatch.setattr(pv_physics, "derived_witness_numbers", zeros)
    recorded.clear()
    directions.clear()
    damaged = generate_geometric_pv(geo, meteo, request, limits, max_weather_rows=10)
    assert recorded[:2] == [zenith, azimuth]
    sz, cz = sin_cos_degrees(recorded[0])
    sa, ca = sin_cos_degrees(recorded[1])
    assert directions == [(sz * sa, sz * ca, cz)] == [baseline_direction]
    assert damaged.profile.values_kw == baseline.profile.values_kw
    assert damaged.profile.total_kwh == baseline.profile.total_kwh
    assert damaged.witness()["energy_kwh"] == baseline.profile.total_kwh
    assert damaged.witness()["available_ac_w"] == baseline.witness()["available_ac_w"]
    solar_geometry = cast(Object, damaged.witness()["solar_geometry"])
    assert solar_geometry["apparent_zenith_deg"] == [0.0]
    assert baseline.witness()["available_ac_w"] != [0.0]


def scenario(parameters: dict[str, Any]) -> GeometricPvInputs:
    return GeometricPvInputs.read(
        {
            "schema_version": 1,
            "model": MODEL,
            "weather_asset_id": "a" * 32,
            "sampling": {"coarse_cells_per_edge": 1, "fine_cells_per_edge": 2},
            "diffuse_policy": "retain_unobstructed_sky_and_ground_components_v1",
            "thermal_policy": "sapm_from_module_mean_poa_v1",
            "electrical_policy": "uniform_module_pvwatts_independent_mpp_sum_v1",
            "parameters": parameters,
        }
    )


def policy() -> GeometricPvLimits:
    # Tiny explicit work envelope for the independent one-module fixture;
    # neither a production capacity nor a physical resolution recommendation.
    return GeometricPvLimits(
        max_module_steps=10,
        max_samples=100,
        max_ray_face_checks=10000,
        max_bounds_checks=10000,
        index_leaf_size=2,
    )


def test_opaque_canopy_removes_only_beam_and_preserves_declared_diffuse_and_uniform_response() -> (
    None
):
    geo, par = geometry(), parameter_document()
    geo["module_specs"][0].update(length_m=1, width_m=1, stc_power_w=1000)
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    meteo = weather(dni=600, dhi=100, ghi=800, temp=25)
    request = scenario(par)
    clear = generate_geometric_pv(geo, meteo, request, policy(), max_weather_rows=10)
    baseline = generate_pv(geo, meteo, request.parameters, max_array_steps=10)
    assert clear.profile.values_kw == baseline.profile.values_kw
    canopy = deepcopy(geo["roofs"][0])
    canopy.update(
        id="canopy",
        origin_enu=[0, 0, 10],
        boundary_uv=[[-100, -100], [100, -100], [100, 100], [-100, 100]],
    )
    shaded = deepcopy(geo)
    shaded["roofs"].append(canopy)
    result = generate_geometric_pv(
        shaded, meteo, request, policy(), max_weather_rows=10
    )
    witness = result.witness()
    module = cast(list[Object], witness["modules"])[0]
    components = cast(Object, module["poa_components_w_m2"])
    assert module["geometric_visible_fraction"] == [0]
    assert components["poa_direct"] == [0]
    assert components["poa_sky_diffuse"] == [100]
    assert components["poa_ground_diffuse"] == [0]
    assert module["cell_temperature_c"] == [25]
    # Pdc = 1000W × (100W/m² / 1000W/m²), with zero thermal/DC losses.
    assert module["dc_available_w"] == [100]
    converter = par["converters"][0]
    p0 = converter["reference_dc_power_w"]
    expected_ac = (converter["eta_nominal"] / converter["eta_reference"]) * (
        -0.0162 * 100**2 / p0 - 0.0059 * p0 + 0.9858 * 100
    )
    assert result.profile.values_kw == pytest.approx((expected_ac / 1000,))
    assert result.profile.total_kwh == pytest.approx(expected_ac / 1000)
    details = cast(Object, witness["inputs"])
    assert (
        details["model"] == MODEL
        and details["model_role"] != "unshaded_reference_scenario"
    )
    assert cast(Object, details["work"])["module_steps"] == 1
    assert "cell_substring_bypass_diode_and_string_iv_response" in cast(
        list[str], details["not_assessed"]
    )
    # The task preserves every source axis; geometric budget exhaustion is a
    # refusal, never an interpolated/partially successful power profile.
    twice = replace(
        meteo,
        points=(
            meteo.points[0],
            replace(
                meteo.points[0],
                interval=replace(
                    meteo.points[0].interval,
                    start=meteo.points[0].interval.end,
                    end=meteo.points[0].interval.end
                    + (meteo.points[0].interval.end - meteo.points[0].interval.start),
                ),
            ),
        ),
    )
    with pytest.raises(InvalidInput, match="module-step"):
        generate_geometric_pv(
            shaded,
            twice,
            request,
            policy().model_copy(update={"max_module_steps": 1}),
            max_weather_rows=10,
        )
    with pytest.raises(InvalidInput, match="sampling"):
        generate_geometric_pv(
            shaded,
            meteo,
            request,
            policy().model_copy(update={"max_samples": 4}),
            max_weather_rows=10,
        )


def test_declared_independent_module_mpp_policy_refuses_a_mismatch_derate() -> None:
    geo, par = geometry(), parameter_document()
    geo["module_specs"][0].update(length_m=1, width_m=1, stc_power_w=1000)
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    par["arrays"][0]["dc_mismatch_factor"] = 0.97
    request = scenario(par)
    meteo = weather(dni=600, dhi=100, ghi=800, temp=25)
    # A string-level mismatch loss presupposes modules that cannot each hold
    # their own MPP, which is the opposite of the declared policy.
    with pytest.raises(InvalidInput, match="unit DC mismatch factor"):
        generate_geometric_pv(geo, meteo, request, policy(), max_weather_rows=10)
    # The same document stays valid for the unshaded reference, whose declared
    # policy is the array-level independent-MPPT sum.
    assert generate_pv(geo, meteo, request.parameters, max_array_steps=10)


def test_witness_states_which_electrical_stages_the_policy_applies() -> None:
    geo, par = geometry(), parameter_document()
    geo["module_specs"][0].update(length_m=1, width_m=1, stc_power_w=1000)
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    par["arrays"][0]["dc_wiring_factor"] = 0.98
    request = scenario(par)
    result = generate_geometric_pv(
        geo,
        weather(dni=600, dhi=100, ghi=800, temp=25),
        request,
        policy(),
        max_weather_rows=10,
    )
    scope = cast(
        Object, cast(Object, result.witness()["inputs"])["electrical_policy_scope"]
    )
    assert scope == {
        "module_mpp": "independent_per_module",
        "dc_wiring_factor": "applied_per_module",
        "dc_mismatch_factor": "unit_required_not_applied",
    }


def test_old_witness_marks_electrical_scope_not_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A witness saved before the scope existed can still feed a new report.

    The recorded policy name stays. The missing stage breakdown is marked not
    recorded; the current independent-module interpretation is not filled in.
    """
    import linker_engine.planning.geometric_pv_report as geometric_report

    geo, par = geometry(), parameter_document()
    geo["module_specs"][0].update(length_m=1, width_m=1, stc_power_w=1000)
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    generated = generate_geometric_pv(
        geo,
        weather(dni=600, dhi=100, ghi=800, temp=25),
        scenario(par),
        policy(),
        max_weather_rows=10,
    )
    current = generated.witness()
    recorded_inputs = cast(Object, current["inputs"])
    assert recorded_inputs["electrical_policy_scope"] == {
        "module_mpp": "independent_per_module",
        "dc_wiring_factor": "applied_per_module",
        "dc_mismatch_factor": "unit_required_not_applied",
    }
    old = {
        **current,
        "inputs": {
            key: value
            for key, value in recorded_inputs.items()
            if key != "electrical_policy_scope"
        },
    }
    holder: dict[str, Object] = {"witness": old}
    inputs = decode_object(generated.inputs_json)

    def bundle(*_args: Any, **_kwargs: Any) -> Object:
        return {
            "inputs": inputs,
            "witness": holder["witness"],
            "weather_metadata": {},
            "dependencies": {},
        }

    monkeypatch.setattr(geometric_report, "reference_bundle", bundle)
    monkeypatch.setattr(
        geometric_report,
        "prepared_profile",
        lambda *_args, **_kwargs: generated.profile,
    )
    monkeypatch.setattr(
        geometric_report,
        "pv_components",
        lambda *_args, **_kwargs: {"components": [], "nameplate_kwp": 1},
    )
    produced = geometric_pv_reference(cast(Any, object()), "a" * 64, {})
    facts = cast(Object, produced["model_facts"])
    assert facts["electrical_policy"] == recorded_inputs["electrical_policy"]
    assert facts["electrical_policy_scope"] == {"status": "not_recorded"}
    assert "independent_per_module" not in facts["electrical_policy_scope"]
    assert "applied_per_module" not in facts["electrical_policy_scope"]
    assert "unit_required_not_applied" not in facts["electrical_policy_scope"]
    holder["witness"] = current
    kept = geometric_pv_reference(cast(Any, object()), "a" * 64, {})
    assert (
        cast(Object, kept["model_facts"])["electrical_policy_scope"]
        == (recorded_inputs["electrical_policy_scope"])
    )


def test_ray_budget_carries_no_selected_row_policy() -> None:
    limits = policy()
    # The diagnostic executor caps how many source rows may be selected. This
    # model always uses every retained row, so it declares only ray budgets.
    assert not hasattr(limits, "visibility_limits")
    rays = limits.visibility_ray_limits()
    assert (rays.max_samples, rays.max_ray_face_checks, rays.max_bounds_checks) == (
        limits.max_samples,
        limits.max_ray_face_checks,
        limits.max_bounds_checks,
    )
    assert not hasattr(rays, "max_selected_rows")
