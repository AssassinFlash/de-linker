"""Cited compound single-diode fit: Batzelis initialization, De Soto refinement.

All physical inputs come from Woo. No electrical cell-series count is inferred.
Published methods/API behavior and applicability: NUMERICAL-MODELS.md §14.
"""

from __future__ import annotations

import math
import re
import sys
from typing import Any, cast

import numpy as np
import pvlib
from pvlib.ivtools.sdm import fit_desoto, fit_desoto_batzelis
from scipy.constants import physical_constants

from .canonical import Object, digest, encode

METHOD = "woo_batzelis_seeded_desoto_v1"
# Documented De Soto crystalline-Si assumptions, not product properties:
# pvlib.pvsystem.calcparams_desoto, pinned 0.16.1; numerical-models §14.
EG_REF, DEG_DT = 1.121, -0.0002677
# MINPACK's conventional sqrt(machine epsilon): numerical precision only.
ROOT_RTOL = math.sqrt(sys.float_info.epsilon)


def cited_scalar(facts: Object, key: str, quantity: str) -> float | None:
    fact = facts.get(key)
    if (
        isinstance(fact, dict)
        and fact.get("status") == "typed"
        and fact.get("shape") == "scalar"
        and fact.get("quantity") == quantity
        and isinstance(fact.get("value"), (int, float))
    ):
        return float(cast(float, fact["value"]))
    return None


def model_point(parameters: Object, irradiance: float, cell_c: float) -> Object:
    with np.errstate(all="raise"):
        translated = pvlib.pvsystem.calcparams_desoto(
            irradiance, cell_c, **cast(dict[str, Any], parameters)
        )
        curve = pvlib.pvsystem.singlediode(*translated, method="lambertw")
    values = {
        key: float(curve[key]) for key in ("v_oc", "i_sc", "v_mp", "i_mp", "p_mp")
    }
    if (
        not all(math.isfinite(v) and v > 0 for v in values.values())
        or values["v_mp"] >= values["v_oc"]
        or values["i_mp"] >= values["i_sc"]
    ):
        raise ValueError("the fitted I-V curve is not physically admissible")
    return dict(values)


def derive_iv_model(facts: Object) -> Object:
    keys = {
        "vmpp_v": "voltage",
        "impp_a": "current",
        "voc_v": "voltage",
        "isc_a": "current",
        "alpha_isc_pct_per_c": "temperature_coefficient",
        "beta_voc_pct_per_c": "temperature_coefficient",
    }
    used = {key: facts[key] for key in keys if key in facts}
    material = facts.get("cell_technology")
    if isinstance(material, dict):
        used["cell_technology"] = material
    result: Object = {
        "status": "unavailable",
        "method": METHOD,
        "pvlib_version": pvlib.__version__,
        "input_facts": used,
        "reason": "module_iv_inputs_missing",
    }
    if (
        not isinstance(material, dict)
        or material.get("source") is None
        or material.get("qualifier") not in (None, "", {}, [])
        or re.search(
            r"\b(?:mono-?crystalline|polycrystalline)\b",
            str(material.get("raw_value", "")),
            re.IGNORECASE,
        )
        is None
    ):
        result["reason"] = "crystalline_module_basis_missing"
        return result
    values = {key: cited_scalar(facts, key, quantity) for key, quantity in keys.items()}
    if any(value is None for value in values.values()):
        return result
    v = cast(dict[str, float], values)
    if not (0 < v["vmpp_v"] < v["voc_v"] and 0 < v["impp_a"] < v["isc_a"]):
        result["reason"] = "module_iv_points_inconsistent"
        return result
    alpha, beta = (
        v["isc_a"] * v["alpha_isc_pct_per_c"],
        v["voc_v"] * v["beta_voc_pct_per_c"],
    )
    try:
        with np.errstate(all="raise"):
            initial = fit_desoto_batzelis(
                v["vmpp_v"], v["impp_a"], v["voc_v"], v["isc_a"], alpha, beta
            )
            guess = {
                target: float(initial[source])
                for source, target in (
                    ("I_L_ref", "IL_0"),
                    ("I_o_ref", "Io_0"),
                    ("R_s", "Rs_0"),
                    ("R_sh_ref", "Rsh_0"),
                    ("a_ref", "a_0"),
                )
            }
            if (
                not all(math.isfinite(x) for x in guess.values())
                or guess["Rs_0"] < 0
                or any(guess[key] <= 0 for key in ("IL_0", "Io_0", "Rsh_0", "a_0"))
            ):
                raise ValueError("analytical initialization is not positive")
            k = physical_constants["Boltzmann constant in eV/K"][0]
            # Public fit_desoto evaluates defaults BEFORE overriding init_guess.
            # This well-scaled surrogate uses pvlib's 1.5*k*T seed formula;
            # ALL five seeds are then overridden. It is NEVER a product Ns.
            seed = max(1, round(guess["a_0"] / (1.5 * k * 298.15)))
            fitted, optimizer = fit_desoto(
                v["vmpp_v"],
                v["impp_a"],
                v["voc_v"],
                v["isc_a"],
                alpha,
                beta,
                cells_in_series=seed,
                EgRef=EG_REF,
                dEgdT=DEG_DT,
                init_guess=guess,
                root_kwargs={"options": {"xtol": ROOT_RTOL}},
            )
        parameters: Object = {key: float(value) for key, value in fitted.items()}
        numeric = cast(dict[str, float], parameters)
        residual = float(np.max(np.abs(optimizer.fun))) / v["isc_a"]
        if (
            not optimizer.success
            or not math.isfinite(residual)
            or residual > ROOT_RTOL
            or not all(math.isfinite(x) for x in numeric.values())
            or numeric["R_s"] < 0
            or any(
                numeric[key] <= 0 for key in ("a_ref", "I_L_ref", "I_o_ref", "R_sh_ref")
            )
        ):
            raise ValueError("the numerical fit is not admissible")
        # STC is the published reference condition, not a site default.
        stc = model_point(parameters, 1000, 25)
        for modeled, supplied in (
            ("v_oc", "voc_v"),
            ("i_sc", "isc_a"),
            ("v_mp", "vmpp_v"),
            ("i_mp", "impp_a"),
        ):
            if abs(cast(float, stc[modeled]) - v[supplied]) / v[supplied] > ROOT_RTOL:
                raise ValueError("the fitted curve does not reproduce its inputs")
        # Held-out diagnostics, never factory accuracy/qualification stamps.
        below, above = (
            model_point(parameters, 1000, 24),
            model_point(parameters, 1000, 26),
        )
        diagnostics: Object = {
            "stc": stc,
            "gamma_pmax_per_c_model": (
                cast(float, above["p_mp"]) - cast(float, below["p_mp"])
            )
            / (2 * cast(float, stc["p_mp"])),
            "gamma_pmax_per_c_declared": cited_scalar(
                facts, "gamma_pmax_pct_per_c", "temperature_coefficient"
            ),
            "gamma_derivative_step_c": 1,
        }
        noct = facts.get("noct_c")
        if (
            isinstance(noct, dict)
            and noct.get("source")
            and not noct.get("qualifier")
            and noct.get("quantity") == "temperature"
            and noct.get("unit") == "°C"
        ):
            match = re.fullmatch(
                r"([+-]?\d+(?:\.\d+)?) \(±(\d+(?:\.\d+)?)\)",
                str(noct.get("raw_value", "")),
            )
            if match:
                temp, spread = float(match[1]), float(match[2])
                power = cited_scalar(facts, "noct_pmax_w", "active_power")
                # NOCT reference irradiance 800 W/m²: maintained datasheet p2,
                # §13/14. Ambient20°C is not the module's NOCT cell temperature.
                diagnostics["noct"] = {
                    "reference_irradiance_w_m2": 800,
                    "cell_c": temp,
                    "cell_c_interval": [temp - spread, temp + spread],
                    "predicted_nominal": model_point(parameters, 800, temp),
                    "p_mp_at_cell_limits_w": [
                        model_point(parameters, 800, t)["p_mp"]
                        for t in (temp - spread, temp + spread)
                    ],
                    "declared_p_mp_w": power * 1000 if power is not None else None,
                    "temperature_fact": noct,
                    "power_fact": facts.get("noct_pmax_w"),
                }
        result.update(
            status="available",
            reason="derived_model_not_manufacturer_validation",
            parameters=parameters,
            diagnostics=diagnostics,
            numerical_residual_relative=residual,
            numerical_tolerance_relative=ROOT_RTOL,
            initialization={
                "kind": "numerical_only_all_five_seeds_overridden",
                "argument": seed,
            },
        )
        result["sha256"] = digest(encode(result))
        return result
    except (
        ValueError,
        RuntimeError,
        FloatingPointError,
        OverflowError,
        ZeroDivisionError,
    ):
        result["reason"] = "module_iv_fit_not_admissible"
        return result
