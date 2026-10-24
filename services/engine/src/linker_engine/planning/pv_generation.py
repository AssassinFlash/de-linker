"""A complete pure geometry/weather → irradiance/DC/shared-AC reference model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

from .access import positive_integer
from .canonical import Json, Object, decode_object, digest, encode
from .errors import InvalidInput, NumericalFailure, VersionUnavailable
from .power_series import PowerSeries
from .pv_arrays import generation_arrays
from .pv_parameters import PvGenerationParameters
from .pv_physics import array_power, checked, conversion_power, sun, values
from .pv_reconstruction import PvReconstruction
from .pv_weather import WeatherSeries
from .series_source import SeriesSource


@dataclass(frozen=True)
class PvGeneration:
    profile: PowerSeries
    inputs_json: bytes
    witness_json: bytes

    def witness(self) -> Object:
        return decode_object(self.witness_json)


def generate_pv(
    geometry: Json,
    weather: WeatherSeries,
    parameters: PvGenerationParameters,
    *,
    max_array_steps: int,
) -> PvGeneration:
    """No network, mutable product feed, current time or implicit model change.

    Resource limits are explicit deployment policy. The returned reference
    scenario does not qualify equipment or assess the site's near shading.
    """
    positive_integer(max_array_steps, "PV array-step limit")
    if len(weather.points) > max_array_steps:
        raise InvalidInput("PV calculation exceeds array-step resource limit")
    # Take private canonical snapshots before using mutable caller JSON/lists.
    geometry_bytes = encode(geometry)
    parameters = PvGenerationParameters.read(parameters.model_dump(mode="json"))
    if pvlib.__version__ != parameters.pvlib_version:
        raise VersionUnavailable("the pinned PV model library is unavailable")
    geometry = decode_object(geometry_bytes)
    arrays = generation_arrays(geometry, weather, parameters)
    if len(arrays) * len(weather.points) > max_array_steps:
        raise InvalidInput("PV calculation exceeds array-step resource limit")
    modules = {item.module_spec_id: item for item in parameters.modules}
    array_parameters = {item.array_id: item for item in parameters.arrays}
    weather_document = weather.document()
    parameter_document: Object = {**parameters.model_dump(mode="json")}
    inputs_json = encode(
        {
            "schema_version": 1,
            "kind": parameters.model,
            "geometry": geometry,
            "weather": weather_document,
            "parameters": parameter_document,
        }
    )
    input_hash = digest(inputs_json)
    try:
        with np.errstate(over="raise", invalid="raise"):
            solar = sun(weather)
            outputs = {
                array.id: array_power(
                    array,
                    array_parameters[array.id],
                    modules[array.module_spec_id],
                    weather,
                    solar,
                )
                for array in arrays
            }
            converters = [
                conversion_power(group, outputs, len(weather.points))
                for group in parameters.converters
            ]
            total = checked(
                np.add.reduce([item[0] for item in converters]),
                len(weather.points),
                "total available AC",
                nonnegative=True,
            )
    except (FloatingPointError, OverflowError) as error:
        raise NumericalFailure("PV model exceeds numerical representation") from error
    axis: Object = {
        "intervals": [
            {
                "start_utc": p.interval.start.isoformat(),
                "end_utc": p.interval.end.isoformat(),
            }
            for p in weather.points
        ]
    }
    resolutions = [point.interval.hours * 3600 for point in weather.points]
    transformation = PvReconstruction(
        input_hash,
        digest(encode(axis)),
        weather.source.native_max_interval_seconds,
        max(resolutions),
    )
    details: Object = {
        "model": parameters.model,
        "model_role": "unshaded_reference_scenario",
        "input_bundle_sha256": input_hash,
        "geometry_sha256": digest(geometry_bytes),
        "weather_document_sha256": digest(encode(weather_document)),
        "weather_original_sha256": weather.source.raw_sha256,
        "parameters_sha256": digest(encode(parameter_document)),
        "libraries": {
            "pvlib": pvlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "weather_source": weather.source.document(),
        "temporal_policy": transformation.document(),
        "output_boundary": "scenario_ac_potential_before_site_export_and_storage_control",
        "model_conventions": {
            "solar_position": "nrel_numpy_spa",
            "delta_t": "spa_year_month",
            "atmospheric_refraction_deg": 0.5667,
            "extraterrestrial_radiation": "spencer",
            "solar_constant_w_m2": 1366.1,
            "relative_airmass": "kastenyoung1989",
            "perez_coefficients": "allsitescomposite1990",
            "sapm_reference_irradiance_w_m2": 1000.0,
            "pvwatts_dc_reference_temperature_c": 25.0,
            "pvwatts_optional_low_light_adjustment": False,
            "zero_irradiance_policy": "zero_ghi_dni_dhi_implies_zero_poa_before_clearness_model_v1",
        },
        "not_assessed": [
            "near_field_and_inter_row_shading",
            "bifacial_rear_irradiance",
            "partial_shading_and_string_electrical_mismatch",
            "real_mppt_and_port_limits",
            "manufacturer_efficiency_and_operating_envelope",
            "equipment_and_country_release",
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
    array_witnesses: list[Json] = [outputs[array.id].witness for array in arrays]
    converter_witnesses: list[Json] = [item[1] for item in converters]
    return PvGeneration(
        profile,
        inputs_json,
        encode(
            {
                "schema_version": 1,
                "kind": parameters.model,
                "inputs": details,
                "solar_geometry": {key: values(value) for key, value in solar.items()},
                "arrays": array_witnesses,
                "converters": converter_witnesses,
                "available_ac_w": values(total),
                "energy_kwh": profile.total_kwh,
                "equipment_release": {"status": "not_assessed"},
                "country_assessment": {"status": "not_assessed"},
                "near_shading_assessment": {
                    "status": "not_assessed",
                    "policy": parameters.shading_policy,
                },
            }
        ),
    )
