"""Pinned pvlib calculations with explicit inputs and a stage-by-stage witness.

Equations, coefficients and interfaces: NUMERICAL-MODELS.md §4.2 and the pinned
pvlib primary source fingerprints in 2026-10-24-pv-generation. No library
parameter default is used to claim a site or manufacturer fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pvlib import (
    atmosphere,
    iam,
    inverter,
    irradiance,
    pvsystem,
    solarposition,
    spa,
    temperature,
)

from .canonical import Json, Object
from .errors import InvalidInput, NumericalFailure
from .pv_arrays import GenerationArray
from .pv_parameters import PvArrayParameters, PvConversionParameters, PvModuleParameters
from .pv_weather import WeatherSeries

type Vector = NDArray[np.float64]


class PvModelDomainExceeded(InvalidInput):
    """The requested scenario makes this empirical model nonphysical."""

    code = "method_domain_exceeded"


def checked(
    value: object, size: int, name: str, *, nonnegative: bool = False
) -> Vector:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise NumericalFailure("nonfinite or mismatched PV " + name)
    if nonnegative and np.any(result < 0):
        raise PvModelDomainExceeded("negative PV " + name)
    return result


def values(vector: Vector) -> list[Json]:
    return cast(list[Json], vector.tolist())


def weather_values(weather: WeatherSeries, field: str) -> Vector:
    return np.asarray(
        [getattr(point, field) for point in weather.points], dtype=np.float64
    )


def sun(weather: WeatherSeries) -> dict[str, Vector]:
    size = len(weather.points)
    try:
        dates = pd.DatetimeIndex([point.irradiance_at_utc for point in weather.points])
        delta_t = checked(
            spa.calculate_deltat(dates.year, dates.month), size, "delta-T"
        )
        position = solarposition.get_solarposition(
            dates,
            weather.latitude_deg,
            weather.longitude_deg,
            altitude=weather.altitude_m,
            pressure=weather_values(weather, "pressure_pa"),
            temperature=weather_values(weather, "air_temp_2m_c"),
            method="nrel_numpy",
            delta_t=delta_t,
            atmos_refract=0.5667,
            numthreads=1,
        )
        # The same year/month delta-T calculation used by SPA's None route,
        # expanded here so the actual values are pinned in the witness.
        zenith = checked(position["apparent_zenith"], size, "solar zenith")
        return {
            "apparent_zenith_deg": zenith,
            "azimuth_deg": checked(position["azimuth"], size, "solar azimuth"),
            "delta_t_seconds": delta_t,
            "dni_extra_w_m2": checked(
                irradiance.get_extra_radiation(
                    dates,
                    solar_constant=1366.1,
                    method="spencer",
                    epoch_year=2014,
                ),
                size,
                "extraterrestrial DNI",
                nonnegative=True,
            ),
        }
    except (ValueError, OverflowError) as error:
        raise InvalidInput(
            "weather solar dates cannot be evaluated by the pinned model"
        ) from error


@dataclass(frozen=True)
class ArrayPower:
    dc_w: Vector
    witness: Object


def array_power(
    array: GenerationArray,
    parameter: PvArrayParameters,
    module: PvModuleParameters,
    weather: WeatherSeries,
    solar: dict[str, Vector],
) -> ArrayPower:
    size = len(weather.points)
    zenith, azimuth = solar["apparent_zenith_deg"], solar["azimuth_deg"]
    # Perez takes relative, not pressure-corrected, airmass. Nighttime NaN in
    # this intermediate is part of pvlib's documented horizon handling; no
    # output NaN is accepted or repaired here.
    airmass = atmosphere.get_relative_airmass(zenith, model="kastenyoung1989")
    dni, ghi, dhi = (
        weather_values(weather, key)
        for key in (
            "dni_w_m2",
            "ghi_w_m2",
            "dhi_w_m2",
        )
    )
    # With no incident irradiance every POA component is exactly zero. Perez's
    # clearness ratio (DHI+DNI)/DHI is undefined for that valid zero case even
    # while the sun is above the horizon. Resolve the physical zero BEFORE
    # calling the model; never fill arbitrary NaN output with zero.
    lit = (dni != 0) | (ghi != 0) | (dhi != 0)
    components = {
        key: np.zeros(size)
        for key in (
            "poa_direct",
            "poa_sky_diffuse",
            "poa_ground_diffuse",
            "poa_global",
        )
    }
    if np.any(lit):
        poa = irradiance.get_total_irradiance(
            array.tilt_deg,
            array.azimuth_deg,
            zenith[lit],
            azimuth[lit],
            dni[lit],
            ghi[lit],
            dhi[lit],
            dni_extra=solar["dni_extra_w_m2"][lit],
            airmass=airmass[lit],
            albedo=parameter.albedo,
            surface_type=None,
            model=parameter.transposition,
            model_perez="allsitescomposite1990",
        )
        for key in components:
            components[key][lit] = checked(
                poa[key], int(np.count_nonzero(lit)), key, nonnegative=True
            )
    incidence = checked(
        irradiance.aoi(
            array.tilt_deg,
            array.azimuth_deg,
            zenith,
            azimuth,
        ),
        size,
        "incidence angle",
    )
    beam_iam = checked(
        iam.ashrae(incidence, b=parameter.beam_iam_b),
        size,
        "beam IAM",
        nonnegative=True,
    )
    effective = checked(
        (
            components["poa_direct"] * beam_iam
            + components["poa_sky_diffuse"] * parameter.sky_diffuse_iam_factor
            + components["poa_ground_diffuse"] * parameter.ground_diffuse_iam_factor
        )
        * parameter.spectral_factor
        * parameter.soiling_factor,
        size,
        "effective irradiance",
        nonnegative=True,
    )
    thermal = parameter.thermal
    cell = checked(
        temperature.sapm_cell(
            components["poa_global"],
            weather_values(weather, "air_temp_2m_c"),
            weather_values(weather, "wind_10m_m_s"),
            thermal.a,
            thermal.b,
            thermal.delta_t_c,
            irrad_ref=1000.0,
        ),
        size,
        "cell temperature",
    )
    dc = checked(
        pvsystem.pvwatts_dc(
            effective,
            cell,
            array.stc_power_w,
            module.gamma_pdc_per_c,
            temp_ref=25.0,
            k=None,
            cap_adjustment=False,
        ),
        size,
        "DC power",
        nonnegative=True,
    )
    delivered = checked(
        dc * parameter.dc_wiring_factor * parameter.dc_mismatch_factor,
        size,
        "DC after declared factors",
        nonnegative=True,
    )
    return ArrayPower(
        delivered,
        {
            **array.document(),
            "transposition": parameter.transposition,
            "zero_irradiance_intervals": int(np.count_nonzero(~lit)),
            "poa_components_w_m2": {
                key: values(value) for key, value in components.items()
            },
            "incidence_deg": values(incidence),
            "beam_iam_factor": values(beam_iam),
            "effective_irradiance_w_m2": values(effective),
            "cell_temperature_c": values(cell),
            "dc_mpp_before_wiring_mismatch_w": values(dc),
            "dc_available_w": values(delivered),
            "dc_declared_factor_reduction_w": values(dc - delivered),
        },
    )


def conversion_power(
    parameter: PvConversionParameters,
    arrays: dict[str, ArrayPower],
    size: int,
) -> tuple[Vector, Object]:
    inputs = [arrays[array_id].dc_w for array_id in parameter.array_ids]
    dc = checked(np.add.reduce(inputs), size, "combined converter DC", nonnegative=True)
    reference = parameter.reference_dc_power_w
    # The unclipped witness is the pinned PVWatts equation (§4.2), including
    # its zero/start-up branch. Its AC output is independently checked against
    # the library, not used as a substitute conversion implementation.
    raw = (parameter.eta_nominal / parameter.eta_reference) * (
        -0.0162 * dc * dc / reference - 0.0059 * reference + 0.9858 * dc
    )
    if np.any((dc > reference) & (raw < 0)):
        raise PvModelDomainExceeded(
            "PVWatts conversion curve outside positive-efficiency domain"
        )
    unclipped = checked(
        np.maximum(raw, 0), size, "unclipped model AC", nonnegative=True
    )
    if np.any(unclipped > dc):
        raise PvModelDomainExceeded("PVWatts parameters imply conversion energy gain")
    cap = parameter.eta_nominal * reference
    ac = checked(
        inverter.pvwatts_multi(
            inputs,
            reference,
            eta_inv_nom=parameter.eta_nominal,
            eta_inv_ref=parameter.eta_reference,
        ),
        size,
        "converter AC",
        nonnegative=True,
    )
    expected = np.minimum(unclipped, cap)
    # Floating-point model-witness check only; not an engineering margin.
    if not np.allclose(ac, expected, rtol=1e-12, atol=1e-9):
        raise NumericalFailure("PVWatts library and conversion witness disagree")
    return ac, {
        "id": parameter.id,
        "array_ids": list(parameter.array_ids),
        "input_assumption": parameter.input_assumption,
        "reference_dc_power_w": reference,
        "model_ac_cap_w": cap,
        "dc_available_w": values(dc),
        "unclipped_model_ac_w": values(unclipped),
        "conversion_model_reduction_w": values(dc - unclipped),
        "clipped_ac_potential_w": values(np.maximum(unclipped - cap, 0)),
        "available_ac_w": values(ac),
    }
