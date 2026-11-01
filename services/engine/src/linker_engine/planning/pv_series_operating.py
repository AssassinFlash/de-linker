"""Forward-quadrant module I-V response for one declared series string.

This is a conditional, uniform-per-module scenario. It does not represent
substring irradiance, bypass conduction, reverse breakdown, real MPPT dynamics,
or equipment release. The module fit and equations are described in the
existing numerical-models research (§14); v_from_i is pvlib's public Lambert-W
single-diode equation. No electrical cell count is inferred.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from pvlib import pvsystem

from .canonical import Object
from .errors import InvalidInput, NumericalFailure

type Vector = NDArray[np.float64]

# Shrink a monotone bracket through the representable binary64 precision.
_ITERATIONS = math.ceil(
    math.log(np.finfo(np.float64).eps) / math.log((math.sqrt(5) - 1) / 2)
)


@dataclass(frozen=True)
class StringOperatingSeries:
    dc_w: Vector
    voltage_v: Vector
    current_a: Vector


def series_operating_point(
    module_conditions: list[tuple[Vector, Vector]],
    fitted_parameters: Object,
    voltage_window_v: tuple[float, float],
    maximum_current_a: float,
) -> StringOperatingSeries:
    """Solve one string over each common time step, within a cited MPPT window.

    All series modules share a current. Each fitted whole-module curve is used
    only from short circuit to open circuit; it is not extended into reverse
    voltage. The maximum power inside this forward-only domain and the stated
    voltage/current range is an idealized operating scenario, not manufacturer
    performance. Zero irradiance in any module leaves no forward-only string
    operating point. Every component array uses the same time axis.
    """
    if not module_conditions:
        raise InvalidInput("a series string needs at least one assigned module")
    size = len(module_conditions[0][0])
    low_v, high_v = voltage_window_v
    if (
        size == 0
        or not math.isfinite(low_v)
        or not math.isfinite(high_v)
        or not math.isfinite(maximum_current_a)
        or low_v < 0
        or high_v <= low_v
        or maximum_current_a <= 0
    ):
        raise InvalidInput("valid string operating bounds and time axis required")
    lit = np.ones(size, dtype=bool)
    for irradiance, cell_c in module_conditions:
        if (
            irradiance.shape != (size,)
            or cell_c.shape != (size,)
            or not np.all(np.isfinite(irradiance))
            or not np.all(np.isfinite(cell_c))
            or np.any(irradiance < 0)
            or np.any(cell_c <= -273.15)
        ):
            raise InvalidInput(
                "module conditions must share a finite physical time axis"
            )
        lit &= irradiance > 0
    power = np.zeros(size)
    voltage = np.zeros(size)
    current = np.zeros(size)
    if not np.any(lit):
        return StringOperatingSeries(power, voltage, current)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            curves = [
                pvsystem.calcparams_desoto(
                    g[lit], t[lit], **cast(dict[str, Any], fitted_parameters)
                )
                for g, t in module_conditions
            ]
            short = [
                np.asarray(
                    pvsystem.i_from_v(0, *curve, method="lambertw"), dtype=np.float64
                )
                for curve in curves
            ]
            if any(
                not np.all(np.isfinite(value)) or np.any(value <= 0) for value in short
            ):
                raise NumericalFailure("nonphysical module short-circuit current")
            upper = np.minimum.reduce(short)
            upper = np.minimum(upper, maximum_current_a)

            def string_voltage(amperes: Vector) -> Vector:
                parts = [
                    np.asarray(
                        pvsystem.v_from_i(amperes, *curve, method="lambertw"),
                        dtype=np.float64,
                    )
                    for curve in curves
                ]
                value = np.add.reduce(parts)
                if not np.all(np.isfinite(value)):
                    raise NumericalFailure("nonfinite series string voltage")
                return cast(Vector, value)

            zeros = np.zeros_like(upper)
            voc = string_voltage(zeros)
            at_upper = string_voltage(upper)
            # At no forward point can the string reach the stated MPPT window.
            available = (voc >= low_v) & (at_upper <= high_v)

            def current_for_voltage(target: float) -> Vector:
                a, b = zeros.copy(), upper.copy()
                for _ in range(_ITERATIONS):
                    mid = (a + b) / 2
                    above = string_voltage(mid) > target
                    a, b = np.where(above, mid, a), np.where(above, b, mid)
                return cast(Vector, (a + b) / 2)

            lo = np.where(voc > high_v, current_for_voltage(high_v), zeros)
            hi = np.where(at_upper < low_v, current_for_voltage(low_v), upper)
            available &= lo <= hi
            ratio = (math.sqrt(5) - 1) / 2
            a, b = lo.copy(), hi.copy()
            for _ in range(_ITERATIONS):
                x1 = b - ratio * (b - a)
                x2 = a + ratio * (b - a)
                left = x1 * string_voltage(x1)
                right = x2 * string_voltage(x2)
                choose_right = left < right
                a, b = np.where(choose_right, x1, a), np.where(choose_right, b, x2)
            selected = (a + b) / 2
            selected_v = string_voltage(selected)
            current[lit] = np.where(available, selected, 0)
            voltage[lit] = np.where(available, selected_v, 0)
            power[lit] = current[lit] * voltage[lit]
    except (FloatingPointError, OverflowError, ValueError) as error:
        raise NumericalFailure(
            "series I-V scenario outside numerical domain"
        ) from error
    if not np.all(np.isfinite(power)) or np.any(power < 0):
        raise NumericalFailure("nonphysical series I-V power")
    return StringOperatingSeries(power, voltage, current)
