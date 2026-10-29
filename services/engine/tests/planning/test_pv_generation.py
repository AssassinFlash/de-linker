"""Independent analytic checks across the actual geometry-to-converter seam."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from linker_engine.planning.canonical import Object, decode_object, digest, encode
from linker_engine.planning.errors import (
    InvalidInput,
    NumericalFailure,
    VersionUnavailable,
)
from linker_engine.planning.interval import Interval
from linker_engine.planning.model_numbers import derived_witness_number
from linker_engine.planning.pv_arrays import generation_arrays
from linker_engine.planning.pv_dc_profile import from_generation, prepared_dc_profile
from linker_engine.planning.pv_generation import generate_pv
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.pv_physics import (
    ArrayPower,
    PvModelDomainExceeded,
    array_power,
    conversion_power,
)
from linker_engine.planning.pv_profile_preparation import PROFILE_PURPOSE
from linker_engine.planning.pv_weather import WeatherPoint, WeatherSeries
from linker_engine.planning.series_source import SeriesSource
from linker_engine.planning.workspace import Workspace

ROOT = Path(__file__).resolve().parents[4]
NOTE = (
    "Synthetic analytic scenario; no surveyed, manufacturer, shading or country release"
)


def geometry() -> dict[str, Any]:
    value = json.loads((ROOT / "fixtures/planning/geometry-flat.json").read_bytes())
    value["coordinate_system"].update(
        north_reference="user_declared",
        north_source_id="survey",
        anchor={
            "latitude_deg": 52.52,
            "longitude_deg": 13.405,
            "source_id": "survey",
            "datum": "EPSG:4326",
        },
    )
    return cast(dict[str, Any], value)


def parameter_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "model": "uniform_unshaded_pvlib_reference_v1",
        "pvlib_version": "0.16.1",
        "temporal_policy": "representative_pv_output_over_declared_intervals_v1",
        "shading_policy": "explicit_unshaded_reference",
        "source_note": NOTE,
        "modules": [
            {
                "module_spec_id": "module",
                "gamma_pdc_per_c": -0.004,
                "source": {
                    "kind": "user_declared",
                    "note": NOTE,
                    "document_sha256": None,
                    "url": None,
                    "page": None,
                },
            }
        ],
        "arrays": [
            {
                "array_id": "array",
                "transposition": "isotropic",
                "albedo": 0.2,
                "thermal": {
                    "model": "sapm_cell",
                    "a": -1000,
                    "b": 0,
                    "delta_t_c": 0,
                    "source_note": NOTE,
                },
                "beam_iam_model": "ashrae",
                "beam_iam_b": 0,
                "sky_diffuse_iam_factor": 1,
                "ground_diffuse_iam_factor": 1,
                "spectral_factor": 1,
                "soiling_factor": 1,
                "dc_wiring_factor": 1,
                "dc_mismatch_factor": 1,
                "source_note": NOTE,
            }
        ],
        "converters": [
            {
                "id": "converter",
                "array_ids": ["array"],
                "model": "pvwatts",
                "input_assumption": "independent_mppt_array_mpp_sum",
                "reference_dc_power_w": 10000,
                "eta_nominal": 0.96,
                "eta_reference": 0.9637,
                "source_note": NOTE,
            }
        ],
    }


def parameters() -> PvGenerationParameters:
    return PvGenerationParameters.read(parameter_document())


def weather(
    *,
    ghi: float = 800,
    dni: float = 0,
    dhi: float = 800,
    temp: float = 45,
    hour: int = 12,
) -> WeatherSeries:
    date = datetime(2020, 6, 21, hour, tzinfo=UTC)
    return WeatherSeries(
        52.52,
        13.405,
        37,
        (
            WeatherPoint(
                Interval(date, date + timedelta(hours=1)),
                date,
                date,
                ghi,
                dni,
                dhi,
                temp,
                0,
                101325,
            ),
        ),
        SeriesSource("a" * 64, "synthetic", "UTC", 3600, encode({"basis": NOTE})),
    )


def test_actual_included_geometry_count_and_composed_normal() -> None:
    value, par, meteo = geometry(), parameters(), weather()
    array = generation_arrays(value, meteo, par)[0]
    assert array.module_ids == (
        "array:0:0",
        "array:0:1",
        "array:0:2",
        "array:1:0",
        "array:1:1",
    )
    assert array.stc_power_w == 2500
    assert array.tilt_deg == array.azimuth_deg == 0
    assert array.azimuth_basis == "horizontal_orientation_invariant"
    value["roofs"][0]["v_axis_enu"] = [0, math.sqrt(3) / 2, 0.5]
    value["arrays"][0]["mount_tilt_deg"] = 30
    array = generation_arrays(value, meteo, par)[0]
    assert array.tilt_deg == pytest.approx(60, rel=0, abs=1e-12)
    assert array.azimuth_deg == 180


def test_horizontal_poa_components_have_independent_analytic_expectation() -> None:
    meteo, par = weather(ghi=500, dni=800, dhi=100), parameters()
    array = generation_arrays(geometry(), meteo, par)[0]
    result = array_power(
        array,
        par.arrays[0],
        par.modules[0],
        meteo,
        {
            "apparent_zenith_deg": np.array([60.0]),
            "azimuth_deg": np.array([180.0]),
            "dni_extra_w_m2": np.array([1366.1]),
        },
    ).witness
    poa = cast(Object, result["poa_components_w_m2"])
    assert poa["poa_direct"] == pytest.approx([400], rel=2e-9)
    assert poa["poa_sky_diffuse"] == [100]
    assert poa["poa_ground_diffuse"] == [0]
    assert poa["poa_global"] == pytest.approx([500], rel=2e-9)


def test_pvwatts_dc_uses_actual_count_and_temperature_coefficient_once() -> None:
    value = geometry()
    value["module_specs"][0]["stc_power_w"] = 400
    value["arrays"][0].update(rows=2, columns=5, excluded_slots=[])
    result = generate_pv(value, weather(), parameters(), max_array_steps=1)
    array = cast(list[Object], result.witness()["arrays"])[0]
    # 10×400W ×800/1000 ×(1−.004×(45−25)) =2944W, not 4kW.
    assert array["stc_power_w"] == 4000
    assert array["cell_temperature_c"] == [45]
    assert array["dc_available_w"] == pytest.approx([2944], rel=2e-9)
    assert result.profile.reconstructed_means is True
    assert result.profile.measurement == "pv_available_ac"
    assert (
        result.profile.transformations[0].document()["energy_preservation_claim"]
        is False
    )


def test_documented_sapm_cell_example_and_loss_product() -> None:
    doc = parameter_document()
    doc["arrays"][0]["thermal"].update(a=-3.47, b=-0.0594, delta_t_c=3)
    doc["arrays"][0].update(dc_wiring_factor=0.98, dc_mismatch_factor=0.97)
    result = generate_pv(
        geometry(),
        weather(ghi=1000, dhi=1000, temp=10),
        PvGenerationParameters.read(doc),
        max_array_steps=1,
    )
    array = cast(list[Object], result.witness()["arrays"])[0]
    assert array["cell_temperature_c"] == pytest.approx([44.11703066106086], rel=2e-9)
    before, after = (
        cast(list[float], array[name])[0]
        for name in ("dc_mpp_before_wiring_mismatch_w", "dc_available_w")
    )
    assert after == pytest.approx(before * 0.9506, rel=5e-8)
    assert array["dc_declared_factor_reduction_w"] == pytest.approx(
        [before - after], rel=5e-8
    )


def test_witness_spelling_does_not_change_the_loss_ledger() -> None:
    from linker_engine.planning.pv_physics import array_power, sun

    doc = parameter_document()
    doc["arrays"][0]["thermal"].update(a=-3.47, b=-0.0594, delta_t_c=3)
    doc["arrays"][0].update(dc_wiring_factor=0.98, dc_mismatch_factor=0.97)
    roof = geometry()
    meteo = weather(ghi=1000, dhi=1000, temp=10)
    parsed = PvGenerationParameters.read(doc)

    # array_power's witness already carries the platform-stable spelling,
    # so the ledger relations hold to the documented spelling bound, and
    # generate_pv stores exactly those spelled members unchanged (the
    # document pass is a fixed point on them).
    arrays = generation_arrays(roof, meteo, parsed)
    solar = sun(meteo)
    power = array_power(arrays[0], parsed.arrays[0], parsed.modules[0], meteo, solar)
    stage = power.witness
    spelled_before = cast(list[float], stage["dc_mpp_before_wiring_mismatch_w"])[0]
    spelled_after = cast(list[float], stage["dc_available_w"])[0]
    assert spelled_after == pytest.approx(spelled_before * 0.9506, rel=5e-8)
    assert spelled_before - spelled_after == pytest.approx(
        spelled_before * (1 - 0.98 * 0.97), rel=5e-8
    )

    result = generate_pv(roof, meteo, parsed, max_array_steps=1)
    repeat = generate_pv(roof, meteo, parsed, max_array_steps=1)
    assert result.witness_json == repeat.witness_json
    array = cast(list[Object], result.witness()["arrays"])[0]
    assert array["dc_mpp_before_wiring_mismatch_w"] == [spelled_before]
    assert array["dc_available_w"] == [spelled_after]
    # The reduction is spelled from the exact difference of the exact
    # vectors, not the difference of the spelled operands; it stays within
    # the documented bound of that difference.
    assert array["dc_declared_factor_reduction_w"] == pytest.approx(
        [spelled_before - spelled_after], rel=5e-8
    )


def test_physics_vectors_stay_bit_identical_when_witness_spelling_is_destroyed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import Iterable

    import linker_engine.planning.pv_physics as pv_physics
    from linker_engine.planning.pv_physics import sun

    meteo = weather(ghi=800, dni=600, dhi=200, temp=20)
    par = parameters()
    roof = geometry()
    solar = sun(meteo)
    built = generation_arrays(roof, meteo, par)
    array = built[0]
    group = par.converters[0]
    assert array.id == group.array_ids[0]
    baseline_power = array_power(array, par.arrays[0], par.modules[0], meteo, solar)
    baseline_ac, baseline_report = conversion_power(
        group, {array.id: baseline_power}, 1
    )
    baseline = generate_pv(roof, meteo, par, max_array_steps=1)

    def zeros(items: Iterable[float]) -> list[float]:
        return [0.0 for _ in items]

    monkeypatch.setattr(pv_physics, "derived_witness_numbers", zeros)
    damaged_solar = sun(meteo)
    for key in (
        "apparent_zenith_deg",
        "azimuth_deg",
        "delta_t_seconds",
        "dni_extra_w_m2",
    ):
        assert np.array_equal(damaged_solar[key], solar[key])
        assert not np.array_equal(damaged_solar[key], np.zeros_like(damaged_solar[key]))

    from pvlib import irradiance as pvlib_irradiance

    seen: dict[str, np.ndarray] = {}
    real_poa = pvlib_irradiance.get_total_irradiance

    def capture(*args: object, **kwargs: object) -> object:
        zenith, azimuth = args[2], args[3]
        assert isinstance(zenith, np.ndarray)
        assert isinstance(azimuth, np.ndarray)
        seen["zenith"] = zenith.astype(np.float64, copy=True)
        seen["azimuth"] = azimuth.astype(np.float64, copy=True)
        return real_poa(*args, **kwargs)

    monkeypatch.setattr(pvlib_irradiance, "get_total_irradiance", capture)
    damaged_power = array_power(
        array, par.arrays[0], par.modules[0], meteo, damaged_solar
    )
    assert np.array_equal(seen["zenith"], solar["apparent_zenith_deg"])
    assert np.array_equal(seen["azimuth"], solar["azimuth_deg"])
    assert np.array_equal(damaged_power.dc_w, baseline_power.dc_w)
    assert damaged_power.dc_w.tolist() != [0.0]
    assert damaged_power.witness["dc_available_w"] == [0.0]
    damaged_ac, damaged_report = conversion_power(group, {array.id: damaged_power}, 1)
    assert np.array_equal(damaged_ac, baseline_ac)
    assert damaged_report["available_ac_w"] == baseline_report["available_ac_w"]
    assert damaged_report["dc_available_w"] == baseline_report["dc_available_w"]
    assert damaged_report["unclipped_model_ac_w"] == [0.0]
    damaged = generate_pv(roof, meteo, par, max_array_steps=1)
    assert damaged.profile.values_kw == baseline.profile.values_kw
    assert damaged.profile.total_kwh == baseline.profile.total_kwh
    assert damaged.witness()["energy_kwh"] == derived_witness_number(
        baseline.profile.total_kwh
    )
    assert damaged.witness()["available_ac_w"] == baseline.witness()["available_ac_w"]
    assert (
        tuple(
            value / 1000
            for value in cast(list[float], baseline.witness()["available_ac_w"])
        )
        == baseline.profile.values_kw
    )
    converter = cast(list[Object], baseline.witness()["converters"])[0]
    assert converter["dc_available_w"] == baseline_report["dc_available_w"]
    solar_geometry = cast(Object, damaged.witness()["solar_geometry"])
    assert solar_geometry["apparent_zenith_deg"] == [0.0]
    assert baseline.witness()["available_ac_w"] != [0.0]


def test_shared_conversion_caps_combined_dc_and_keeps_a_loss_witness() -> None:
    group = (
        parameters()
        .converters[0]
        .model_copy(
            update={
                "reference_dc_power_w": 1000.0,
                "array_ids": ["first", "second"],
            }
        )
    )
    outputs = {name: ArrayPower(np.array([1000.0]), {}) for name in group.array_ids}
    ac, report = conversion_power(group, outputs, 1)
    assert ac.tolist() == [
        960
    ]  # One shared converter, not two independent960W outputs.
    assert report["dc_available_w"] == [2000]
    assert cast(list[float], report["clipped_ac_potential_w"])[0] > 0
    reduced = cast(list[float], report["conversion_model_reduction_w"])[0]
    clipped = cast(list[float], report["clipped_ac_potential_w"])[0]
    assert 2000 == pytest.approx(960 + reduced + clipped, rel=0, abs=1e-9)
    single = group.model_copy(update={"array_ids": ["first"]})
    assert conversion_power(single, outputs, 1)[0].tolist() == [960]


def test_dc_projection_reads_unclipped_stage_with_the_same_pinned_time_policy(
    workspace: Workspace,
) -> None:
    raw_hash = workspace.blobs.put(b"owned synthetic DC-stage weather fixture")
    meteo = weather()
    meteo = replace(
        meteo,
        source=SeriesSource(
            raw_hash, "synthetic", "UTC", 3600, encode({"basis": NOTE})
        ),
    )
    document = parameter_document()
    document["converters"][0]["reference_dc_power_w"] = 1000
    roof = geometry()
    result = generate_pv(
        roof, meteo, PvGenerationParameters.read(document), max_array_steps=10
    )
    direct = from_generation(result, "converter")
    metadata: Object = {
        "schema": 1,
        "profile_type": PROFILE_PURPOSE,
        "retention": "permanent",
        "geometry_sha256": digest(encode(roof)),
        "dependencies": {
            "pv_model_inputs": workspace.blobs.put(result.inputs_json),
            "pv_model_witness": workspace.blobs.put(result.witness_json),
        },
    }
    retained = prepared_dc_profile(workspace.blobs, raw_hash, metadata, "converter")
    assert retained.document() == direct.document()
    assert direct.values_kw[0] > result.profile.values_kw[0]
    assert result.profile.values_kw[0] == pytest.approx(0.96)
    assert direct.transformations == result.profile.transformations
    assert direct.document()["value_semantics"] == "reconstructed_interval_average"
    assert direct.source.document()["details"] == retained.source.document()["details"]


@pytest.mark.parametrize("model", ["isotropic", "haydavies", "perez", "perez-driesse"])
@pytest.mark.parametrize("hour", [0, 12])
def test_explicit_transposition_and_dark_conditions_remain_finite(
    model: str, hour: int
) -> None:
    doc = parameter_document()
    doc["arrays"][0]["transposition"] = model
    dark = weather(ghi=0, dni=0, dhi=0, temp=10, hour=hour)
    result = generate_pv(
        geometry(), dark, PvGenerationParameters.read(doc), max_array_steps=1
    )
    assert result.profile.values_kw == (0,)
    assert result.witness()["equipment_release"] == {"status": "not_assessed"}
    assert result.witness()["near_shading_assessment"] == {
        "status": "not_assessed",
        "policy": "explicit_unshaded_reference",
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda g: g["coordinate_system"].update(anchor=None),
        lambda g: g["coordinate_system"].update(
            north_reference="unreferenced", north_source_id=None
        ),
        lambda g: g["coordinate_system"]["anchor"].update(latitude_deg=51),
        lambda g: g["arrays"][0].update(origin_uv=[-10, 0]),
        lambda g: g["arrays"][0].update(
            excluded_slots=["0:0", "0:1", "0:2", "1:0", "1:1", "1:2"]
        ),
    ],
)
def test_missing_or_conflicting_geometry_never_yields_a_profile(change: Any) -> None:
    value = geometry()
    change(value)
    with pytest.raises(InvalidInput):
        generate_pv(value, weather(), parameters(), max_array_steps=1)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["converters"][0].update(array_ids=["array", "array"]),
        lambda p: p["converters"][0].update(array_ids=["other"]),
        lambda p: p["arrays"].append(copy.deepcopy(p["arrays"][0])),
        lambda p: p["modules"][0].update(module_spec_id="other"),
        lambda p: p["arrays"][0].pop("albedo"),
        lambda p: p["arrays"][0].update(soiling_factor="1"),
        lambda p: p["arrays"][0].update(beam_iam_b=True),
    ],
)
def test_parameters_are_complete_and_bound_to_actual_inputs(change: Any) -> None:
    doc = parameter_document()
    change(doc)
    with pytest.raises(InvalidInput):
        generate_pv(
            geometry(), weather(), PvGenerationParameters.read(doc), max_array_steps=1
        )


def test_nonphysical_dc_is_a_method_error_not_repaired_to_zero() -> None:
    doc = parameter_document()
    doc["modules"][0]["gamma_pdc_per_c"] = -1
    with pytest.raises(PvModelDomainExceeded):
        generate_pv(
            geometry(),
            weather(temp=100),
            PvGenerationParameters.read(doc),
            max_array_steps=1,
        )


def test_nonzero_irradiance_with_undefined_perez_output_is_not_filled_with_zero() -> (
    None
):
    doc = parameter_document()
    doc["arrays"][0]["transposition"] = "perez"
    with pytest.raises(NumericalFailure, match="poa_sky_diffuse"):
        generate_pv(
            geometry(),
            weather(ghi=1, dni=0, dhi=0),
            PvGenerationParameters.read(doc),
            max_array_steps=1,
        )


def test_source_versions_and_frozen_inputs_are_reproducible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value, par = geometry(), parameters()
    result = generate_pv(value, weather(), par, max_array_steps=1)
    inputs_before, witness_before = result.inputs_json, result.witness_json
    value["arrays"][0]["columns"] = 100
    par.arrays.clear()
    assert result.inputs_json == inputs_before and result.witness_json == witness_before
    assert result.profile.source.raw_sha256 == digest(result.inputs_json)
    assert decode_object(result.inputs_json)["kind"] == par.model
    monkeypatch.setattr("pvlib.__version__", "unavailable")
    with pytest.raises(VersionUnavailable):
        generate_pv(geometry(), weather(), parameters(), max_array_steps=1)


@pytest.mark.parametrize("limit", [0, True])
def test_resource_policy_is_not_an_implicit_success(limit: int) -> None:
    with pytest.raises(InvalidInput):
        generate_pv(geometry(), weather(), parameters(), max_array_steps=limit)


def test_weather_does_not_coerce_missing_negative_or_nonphysical_values() -> None:
    for kwargs in (
        {"ghi": -1},
        {"dhi": float("nan")},
        {"dni": True},
        {"temp": -274},
        {"dni": 10**1000},
    ):
        with pytest.raises(InvalidInput):
            weather(**kwargs)
