"""Full-axis geometric PV with an explicitly uniform module response.

The retained direct-only request attenuates beam irradiance and leaves sky and
ground diffuse unobstructed. The Perez component request scales isotropic sky,
circumsolar, a positive horizon term and ground by sampled visible fractions.
A negative Perez horizon correction is retained unchanged. Neither request is
a bypass-diode, string I–V or real MPPT model.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace
from typing import cast

import numpy as np
import pvlib

from .canonical import Json, Object, decode_object, digest, encode
from .direct_beam_geometry import build_scene
from .direct_beam_index import DirectBeamIndex
from .direct_beam_visibility import VisibilityBudget, visibility_row
from .errors import InvalidInput, NumericalFailure, VersionUnavailable
from .geometric_pv_diffuse import diffuse_sample_upper_bound, module_diffuse_visibility
from .geometric_pv_inputs import (
    MODEL_ROLES,
    MODEL_V2,
    SHADING_STATUS,
    GeometricPvInputs,
    GeometricPvLimits,
)
from .geometry import sin_cos_degrees
from .power_series import PowerSeries
from .pv_arrays import generation_arrays
from .pv_generation import PvGeneration
from .pv_physics import (
    ArrayPower,
    DiffuseFractions,
    array_power,
    checked,
    conversion_power,
    sun,
    values,
)
from .pv_reconstruction import PvReconstruction
from .pv_weather import WeatherSeries
from .series_source import SeriesSource


def generate_geometric_pv(
    geometry: Json,
    weather: WeatherSeries,
    request: GeometricPvInputs,
    limits: GeometricPvLimits,
    *,
    max_weather_rows: int,
    checkpoint: Callable[[], None] = lambda: None,
) -> PvGeneration:
    """Every retained weather row is used; no selected-row interpolation.

    Direct fractions attenuate beam POA before the declared mean-module thermal
    and uniform PVWatts response. The retained policy leaves sky and ground
    unobstructed. The Perez policy scales isotropic sky, circumsolar, a positive
    horizon term and ground by visible fractions. A negative horizon correction
    stays unchanged. This is not a bypass-diode, string I–V or real MPPT
    performance model.
    """
    geometry = decode_object(encode(geometry))
    request = GeometricPvInputs.read(request.model_dump(mode="json"))
    limits = GeometricPvLimits.read(limits.model_dump(mode="json"))
    parameters = request.parameters
    if pvlib.__version__ != parameters.pvlib_version:
        raise VersionUnavailable("the pinned geometric PV library is unavailable")
    # `electrical_policy` declares that every module runs at its own MPP and the
    # results are summed. Inter-module mismatch loss exists only because a
    # series string cannot hold every module at its own MPP, so the declared
    # array mismatch factor would contradict that policy. Refuse rather than
    # silently apply a derate the policy says is not modelled.
    misdeclared = [
        item.array_id for item in parameters.arrays if item.dc_mismatch_factor != 1
    ]
    if misdeclared:
        raise InvalidInput(
            "geometric PV independent-module MPP policy requires a unit DC mismatch factor: "
            + ", ".join(sorted(misdeclared))
        )
    arrays = generation_arrays(geometry, weather, parameters)
    scene = build_scene(geometry)
    size = len(weather.points)
    if size > max_weather_rows or len(scene.receivers) * size > limits.max_module_steps:
        raise InvalidInput("geometric PV full-axis module-step policy exceeded")
    receiver_ids = [receiver.id for receiver in scene.receivers]
    if set(receiver_ids) != {module for array in arrays for module in array.module_ids}:
        raise InvalidInput("geometric PV receivers differ from included modules")
    diffuse = request.model == MODEL_V2
    upper_samples = (
        len(receiver_ids)
        * size
        * (
            request.sampling.coarse_cells_per_edge**2
            + request.sampling.fine_cells_per_edge**2
        )
    )
    if diffuse:
        upper_samples += diffuse_sample_upper_bound(
            len(receiver_ids), request.sampling.fine_cells_per_edge
        )
    if upper_samples > limits.max_samples:
        raise InvalidInput("geometric PV requested sampling exceeds work policy")
    budget = VisibilityBudget(limits.visibility_ray_limits())
    index = DirectBeamIndex.from_scene(scene, leaf_size=limits.index_leaf_size)
    checkpoint()
    static_diffuse = {}
    if diffuse:
        for receiver in scene.receivers:
            checkpoint()
            static_diffuse[receiver.id] = module_diffuse_visibility(
                scene, receiver, request.sampling, budget, index
            )
    solar = sun(weather)
    fractions = {identifier: np.zeros(size) for identifier in receiver_ids}
    visible: dict[str, list[Json]] = {identifier: [] for identifier in receiver_ids}
    statuses: dict[str, list[Json]] = {identifier: [] for identifier in receiver_ids}
    deltas: dict[str, list[Json]] = {identifier: [] for identifier in receiver_ids}
    for ordinal in range(size):
        checkpoint()
        sz, cz = sin_cos_degrees(float(solar["apparent_zenith_deg"][ordinal]))
        sa, ca = sin_cos_degrees(float(solar["azimuth_deg"][ordinal]))
        row = visibility_row(
            scene, (sz * sa, sz * ca, cz), request.sampling, budget, index=index
        )
        modules = row["modules"]
        assert isinstance(modules, list)
        for raw in modules:
            assert isinstance(raw, dict)
            identifier = str(raw["module_id"])
            status = str(raw["status"])
            fine = raw["fine"]
            fraction = fine["visible_fraction"] if isinstance(fine, dict) else None
            # Night/back-facing has zero direct POA, but no defined geometric
            # fraction. Retain null and status separately from the factor used
            # in the direct-irradiance equation.
            fractions[identifier][ordinal] = (
                float(cast(float, fraction)) if fraction is not None else 0
            )
            visible[identifier].append(fraction)
            statuses[identifier].append(status)
            deltas[identifier].append(raw["observed_absolute_delta"])
    inputs_json = encode(
        {
            "schema_version": 1,
            "kind": request.model,
            "geometry": geometry,
            "weather": weather.document(),
            "parameters": request.model_dump(mode="json"),
            "limits": limits.model_dump(mode="json"),
        }
    )
    input_hash = digest(inputs_json)
    module_parameters = {p.module_spec_id: p for p in parameters.modules}
    array_parameters = {p.array_id: p for p in parameters.arrays}
    outputs: dict[str, ArrayPower] = {}
    module_witnesses: list[Json] = []
    try:
        with np.errstate(over="raise", invalid="raise"):
            for array in arrays:
                module_outputs = []
                for identifier in array.module_ids:
                    checkpoint()
                    module = replace(
                        array,
                        module_ids=(identifier,),
                        stc_power_w=array.stc_power_w / len(array.module_ids),
                    )
                    visibility = static_diffuse.get(identifier)
                    output = array_power(
                        module,
                        array_parameters[array.id],
                        module_parameters[array.module_spec_id],
                        weather,
                        solar,
                        direct_beam_fraction=fractions[identifier],
                        diffuse_fractions=(
                            None
                            if visibility is None
                            else DiffuseFractions(
                                visibility.isotropic,
                                visibility.horizon,
                                visibility.ground,
                            )
                        ),
                    )
                    module_outputs.append(output.dc_w)
                    module_witnesses.append(
                        {
                            **output.witness,
                            "module_id": identifier,
                            "geometric_visible_fraction": visible[identifier],
                            "geometric_status": statuses[identifier],
                            "observed_grid_delta": deltas[identifier],
                            **(
                                {}
                                if visibility is None
                                else {
                                    "accepted_directions": cast(
                                        Object, visibility.accepted_directions
                                    ),
                                    "blocked_samples": visibility.blocked_samples,
                                }
                            ),
                        }
                    )
                dc = checked(
                    np.add.reduce(module_outputs),
                    size,
                    "array module DC sum",
                    nonnegative=True,
                )
                outputs[array.id] = ArrayPower(
                    dc, {**array.document(), "dc_available_w": values(dc)}
                )
            converters = [
                conversion_power(group, outputs, size)
                for group in parameters.converters
            ]
            total = checked(
                np.add.reduce([item[0] for item in converters]),
                size,
                "geometric reference available AC",
                nonnegative=True,
            )
    except (FloatingPointError, OverflowError) as error:
        raise NumericalFailure(
            "geometric PV scenario exceeds numeric domain"
        ) from error
    checkpoint()
    axis: Object = {
        "intervals": [
            {
                "start_utc": p.interval.start.isoformat(),
                "end_utc": p.interval.end.isoformat(),
            }
            for p in weather.points
        ]
    }
    transformation = PvReconstruction(
        input_hash,
        digest(encode(axis)),
        weather.source.native_max_interval_seconds,
        max(p.interval.hours * 3600 for p in weather.points),
    )
    details: Object = {
        "model": request.model,
        "model_role": MODEL_ROLES[request.model],
        "input_bundle_sha256": input_hash,
        "geometry_sha256": digest(encode(geometry)),
        "parameters_sha256": digest(encode(request.model_dump(mode="json"))),
        "weather_document_sha256": digest(encode(weather.document())),
        "weather_original_sha256": weather.source.raw_sha256,
        "weather_source": weather.source.document(),
        "temporal_policy": transformation.document(),
        "diffuse_policy": request.diffuse_policy,
        "thermal_policy": request.thermal_policy,
        "electrical_policy": request.electrical_policy,
        "electrical_policy_scope": {
            "module_mpp": "independent_per_module",
            "dc_wiring_factor": "applied_per_module",
            "dc_mismatch_factor": "unit_required_not_applied",
        },
        "output_boundary": "scenario_ac_potential_before_site_export_and_storage_control",
        "sampling": request.sampling.model_dump(mode="json"),
        "work": {
            "module_steps": len(receiver_ids) * size,
            "sample_upper_bound": upper_samples,
            "sample_count": budget.samples,
            "ray_face_checks": budget.ray_face_checks,
            "bounds_checks": budget.bounds_checks,
        },
        "limits": limits.model_dump(mode="json"),
        "not_assessed": [
            *([] if diffuse else ["occluded_sky_and_ground_diffuse_irradiance"]),
            "cell_substring_bypass_diode_and_string_iv_response",
            "actual_mppt_and_manufacturer_operating_performance",
            "equipment_and_country_release",
            "complete_shading_accuracy_or_sampling_error_bound",
        ],
    }
    profile = PowerSeries(
        tuple(point.interval for point in weather.points),
        tuple(float(value / 1000) for value in total),
        "pv_available_ac",
        SeriesSource(
            input_hash,
            "modelled",
            "UTC",
            weather.source.native_max_interval_seconds,
            encode(details),
        ),
        (transformation,),
    )
    if not math.isfinite(profile.total_kwh):
        raise NumericalFailure("geometric PV scenario integrated energy is nonfinite")
    return PvGeneration(
        profile,
        inputs_json,
        encode(
            {
                "schema_version": 1,
                "kind": request.model,
                "inputs": details,
                "solar_geometry": {key: values(value) for key, value in solar.items()},
                "arrays": [outputs[array.id].witness for array in arrays],
                "modules": module_witnesses,
                "converters": [item[1] for item in converters],
                "available_ac_w": values(total),
                "energy_kwh": profile.total_kwh,
                "equipment_release": {"status": "not_assessed"},
                "country_assessment": {"status": "not_assessed"},
                "near_shading_assessment": {"status": SHADING_STATUS[request.model]},
            }
        ),
    )
