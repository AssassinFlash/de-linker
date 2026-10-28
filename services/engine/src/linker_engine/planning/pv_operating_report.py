"""Presentation of frozen operating points and their fitted model diagnostics."""

from __future__ import annotations

from typing import Any, cast

from linker_engine.models import ReportRow, ReportSection, ReportTable

from .canonical import Object
from .report_copy import text
from .report_numbers import number as display


def operating_sections(
    value: Object, strings: list[dict[str, Any]], locale: str
) -> list[ReportSection]:
    model, conditions = cast(Object, value["model"]), cast(Object, value["conditions"])
    points = cast(list[dict[str, Any]], value["points"])
    numbers = {s["id"]: i + 1 for i, s in enumerate(strings)}

    def row(key: str, value: Any, unit: str = "") -> ReportRow:
        # Significant-digit presentation retains small diode-current values;
        # it is not model precision or a physical uncertainty statement.
        return ReportRow(label=text(key, locale), value=display(value, locale, unit))

    sections = [
        ReportSection(
            id="pv-operating",
            title=text("pv_operating_title", locale),
            paragraphs=[
                text("pv_operating_scope", locale),
                str(
                    conditions.get("source_note")
                    or text("pv_operating_incomplete", locale)
                ),
            ],
            rows=[
                row("pv_effective_irradiance", conditions["irradiance_w_m2"], "W/m²"),
                row("pv_hot_cell", conditions["hot_cell_c"], "°C"),
                row("pv_cold_cell", conditions["cold_cell_c"], "°C"),
            ],
            table=ReportTable(
                columns=[
                    text("pv_string", locale),
                    text("pv_case", locale),
                    "Vmpp",
                    "Impp",
                    "Isc",
                ],
                rows=[
                    [
                        str(numbers[p["string_id"]]),
                        text("pv_" + p["case"] + "_case", locale),
                        display(p["v_mp_v"], locale, "V"),
                        display(p["i_mp_a"], locale, "A"),
                        display(p["i_sc_a"], locale, "A"),
                    ]
                    for p in points
                ],
            )
            if points
            else None,
        )
    ]
    if model["status"] != "available":
        sections[0].paragraphs.append(text("pv_iv_unavailable", locale))
        return sections
    parameters = cast(Object, model["parameters"])
    diagnostics = cast(Object, model["diagnostics"])
    data = cast(dict[str, dict[str, Any]], model["input_facts"])
    symbols = {
        "vmpp_v": "Vmpp (STC)",
        "impp_a": "Impp (STC)",
        "voc_v": "Voc (STC)",
        "isc_a": "Isc (STC)",
        "alpha_isc_pct_per_c": "αIsc",
        "beta_voc_pct_per_c": "βVoc",
        "cell_technology": text("pv_cell_technology", locale),
    }
    documents: dict[tuple[str, int], ReportRow] = {}
    for fact in data.values():
        source = fact.get("source")
        if isinstance(source, dict):
            url, page = source["url"], source["page"]
            documents[url, page] = ReportRow(
                label=text("source", locale)
                + " · "
                + text("page", locale)
                + f" {page}",
                value=str(url),
                href=url,
            )
    sections.append(
        ReportSection(
            id="pv-iv-model",
            title=text("pv_model_details", locale),
            paragraphs=[
                text("pv_model_scope", locale),
                "pvlib " + str(model["pvlib_version"]),
            ],
            rows=[
                *documents.values(),
                ReportRow(
                    label=text("pv_fitting_method", locale),
                    value="Batzelis",
                    href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto_batzelis.html",
                ),
                ReportRow(
                    label=text("pv_refinement_method", locale),
                    value="De Soto",
                    href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto.html",
                ),
                ReportRow(
                    label=text("pv_translation_method", locale),
                    value="De Soto",
                    href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.pvsystem.calcparams_desoto.html",
                ),
                ReportRow(
                    label=text("pv_model_identity", locale), value=str(model["sha256"])
                ),
            ],
            table=ReportTable(
                columns=[text("quantity", locale), text("pv_value", locale)],
                rows=[
                    [
                        symbols[key],
                        str(fact["raw_value"])
                        + (f" {fact['raw_unit']}" if fact.get("raw_unit") else ""),
                    ]
                    for key, fact in data.items()
                ],
            ),
        )
    )
    sections.append(
        ReportSection(
            id="pv-iv-parameters",
            title=text("pv_fitted_parameters", locale),
            rows=[
                ReportRow(label=label, value=display(parameters[key], locale, unit))
                for key, label, unit in (
                    ("a_ref", "a,ref", "V"),
                    ("I_L_ref", "IL,ref", "A"),
                    ("I_o_ref", "I0,ref", "A"),
                    ("R_s", "Rs", "Ω"),
                    ("R_sh_ref", "Rsh,ref", "Ω"),
                    ("alpha_sc", "αIsc", "A/K"),
                )
            ]
            + [
                row("pv_eg_assumption", parameters["EgRef"], "eV"),
                row("pv_deg_assumption", parameters["dEgdT"], "1/K"),
                row("pv_numerical_residual", model["numerical_residual_relative"]),
                row("pv_numerical_tolerance", model["numerical_tolerance_relative"]),
            ],
        )
    )
    gamma = diagnostics.get("gamma_pmax_per_c_declared")
    diagnostic_rows = [
        row(
            "pv_gamma_declared",
            cast(float, gamma) * 100 if gamma is not None else None,
            "%/°C",
        ),
        row(
            "pv_gamma_model",
            cast(float, diagnostics["gamma_pmax_per_c_model"]) * 100,
            "%/°C",
        ),
    ]
    noct = diagnostics.get("noct")
    if isinstance(noct, dict):
        diagnostic_rows.extend(
            [
                row("pv_noct_irradiance", noct["reference_irradiance_w_m2"], "W/m²"),
                ReportRow(
                    label=text("pv_noct_cell_interval", locale),
                    value=" – ".join(
                        display(t, locale, "°C")
                        for t in cast(list[float], noct["cell_c_interval"])
                    ),
                ),
                row("pv_noct_cell", noct["cell_c"], "°C"),
                row("pv_noct_declared_power", noct["declared_p_mp_w"], "W"),
                row(
                    "pv_noct_model_power",
                    cast(Object, noct["predicted_nominal"])["p_mp"],
                    "W",
                ),
                ReportRow(
                    label=text("pv_noct_model_limits", locale),
                    value=" / ".join(
                        display(v, locale, "W")
                        for v in cast(list[float], noct["p_mp_at_cell_limits_w"])
                    ),
                ),
            ]
        )
    sections.append(
        ReportSection(
            id="pv-iv-diagnostics",
            title=text("pv_datasheet_comparisons", locale),
            paragraphs=[text("pv_diagnostics_scope", locale)],
            rows=diagnostic_rows,
        )
    )
    return sections
