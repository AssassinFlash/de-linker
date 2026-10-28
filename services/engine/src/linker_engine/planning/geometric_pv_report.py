"""Readable frozen direct-only PV scenario, without numerical reproduction."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .geometric_pv_profile import prepared_profile, reference_bundle
from .pv_profile_artifacts import _object
from .report_copy import text
from .report_pv_components import pv_components
from .report_pvlib import pvlib_sections
from .storage import Blobs


def _number(value: Json, locale: str) -> str:
    # Reuse this section's six-significant-digit energy display for coefficients
    # and geometry. Frozen source JSON and numerical witnesses keep full precision.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    shown = str(value) if isinstance(value, int) else f"{value:.6g}"
    return shown.replace(".", ",") if locale == "de" else shown


def geometric_pv_reference(blobs: Blobs, raw_sha256: str, metadata: Object) -> Object:
    profile = prepared_profile(blobs, raw_sha256, metadata)
    bundle = reference_bundle(blobs, raw_sha256, metadata)
    inputs, witness = _object(bundle["inputs"]), _object(bundle["witness"])
    details = _object(witness["inputs"])
    geometry = _object(inputs["geometry"])
    placements = {
        str(_object(item)["id"]): _object(item)
        for item in cast(list[Json], geometry["arrays"])
    }
    return {
        "model": witness["kind"],
        "geometry": inputs["geometry"],
        "parameters": inputs["parameters"],
        "model_facts": {
            key: details[key]
            for key in (
                "model_role",
                "diffuse_policy",
                "thermal_policy",
                "electrical_policy",
                "sampling",
                "work",
                "limits",
                "not_assessed",
                "temporal_policy",
            )
        },
        "summary": {
            "start_utc": profile.intervals[0].start.isoformat(),
            "end_utc": profile.intervals[-1].end.isoformat(),
            "interval_count": len(profile.intervals),
            "energy_kwh": profile.total_kwh,
            "native_max_interval_seconds": profile.source.native_max_interval_seconds,
            "reconstructed_means": profile.reconstructed_means,
            "output_boundary": "pv_available_ac",
        },
        "weather_source": _object(inputs["weather"])["source"],
        "weather_metadata": bundle["weather_metadata"],
        "arrays": [
            {
                **{
                    key: _object(array)[key]
                    for key in (
                        "id",
                        "module_spec_id",
                        "module_count",
                        "stc_power_w",
                        "normal_enu",
                        "tilt_deg",
                        "azimuth_north_clockwise_deg",
                        "azimuth_basis",
                    )
                },
                "mounting_note": placements[str(_object(array)["id"])].get(
                    "mounting_note"
                ),
                "lower_edge_clearance_m": placements[str(_object(array)["id"])].get(
                    "lower_edge_clearance_m"
                ),
            }
            for array in cast(list[Json], witness["arrays"])
        ],
        "converters": [
            {key: _object(item)[key] for key in ("id", "model_ac_cap_w")}
            for item in cast(list[Json], witness["converters"])
        ],
        "pv_components": pv_components(blobs, raw_sha256, metadata),
        "dependencies": bundle["dependencies"],
    }


def _parameter_rows(reference: Object, locale: str) -> list[ReportRow]:
    """Reuse the established readable coefficients without its unshaded label."""
    if not all(key in reference for key in ("arrays", "converters", "pv_components")):
        return []  # Historical report sources retain their original shape.
    parameters = _object(_object(reference["parameters"])["parameters"])
    projection: Object = {
        "parameters": parameters,
        "profile_summary": reference["summary"],
        "weather": _object(reference["weather_source"])["details"],
        **{
            key: reference[key]
            for key in ("arrays", "converters", "pv_components", "used_by")
        },
        "dependencies": {},
    }
    # The geometric section already names its own model, output, period, source
    # range and usage. Keep the mature coefficient/source rows, not a second
    # reference identity or the unshaded scope paragraphs.
    repeated = {
        text(key, locale)
        for key in (
            "pvlib_model",
            "pvlib_weather_period",
            "pvgis_radiation_database",
            "pvlib_meteo_database",
            "pvlib_synthetic_year",
            "period",
            "intervals",
            "pvgis_ac_energy",
            "pvgis_source_run",
            "comparison_baseline",
            "comparison_candidate",
        )
    }
    return [
        row.model_copy(update={"label": text("geometric_pv_original_note", locale)})
        if row.label == text("pvlib_note", locale)
        else row
        for row in pvlib_sections(
            {"pvlib_references": [projection]},
            locale,
            format_number=lambda value: _number(value, locale),
        )[0].rows
        if row.label not in repeated
    ]


def geometric_pv_sections(references: list[Json], locale: str) -> list[ReportSection]:
    result = []
    for index, raw in enumerate(references):
        reference = _object(raw)
        summary, facts = (
            _object(reference["summary"]),
            _object(reference["model_facts"]),
        )
        metadata = _object(reference["weather_metadata"])
        request, interpretation = (
            _object(metadata["weather_request"]),
            _object(metadata["weather_interpretation"]),
        )
        sampling = _object(facts["sampling"])
        parameters = _object(_object(reference["parameters"])["parameters"])
        rows = [
            ReportRow(
                label=text("geometric_pv_model", locale),
                value=f"{reference['model']} / pvlib {parameters['pvlib_version']}",
            ),
            ReportRow(
                label=text("geometric_pv_period", locale),
                value=f"{summary['start_utc']} – {summary['end_utc']}",
            ),
            ReportRow(
                label=text("geometric_pv_rows", locale),
                value=str(summary["interval_count"]),
            ),
            ReportRow(
                label=text("geometric_pv_energy", locale),
                value=_number(summary["energy_kwh"], locale) + " kWh",
            ),
            ReportRow(
                label=text("geometric_pv_sampling", locale),
                value=f"{sampling['coarse_cells_per_edge']} / {sampling['fine_cells_per_edge']}",
            ),
            ReportRow(
                label=text("geometric_pv_weather", locale),
                value=f"{request['start_year']}–{request['end_year']} / {request['expected_radiation_database']} / {request['expected_meteo_database']}",
            ),
            ReportRow(
                label=text("geometric_pv_year", locale),
                value=str(interpretation["synthetic_energy_year"]),
            ),
        ]
        rows.extend(_parameter_rows(reference, locale))
        rows.extend(
            ReportRow(label=name + " SHA-256", value=str(sha))
            for name, sha in _object(reference["dependencies"]).items()
        )
        rows.extend(
            ReportRow(
                label=text("geometric_pv_used_by", locale),
                value=f"{_object(usage)['run_id']} / {_object(usage)['revision']}",
            )
            for usage in cast(list[Json], reference["used_by"])
        )
        result.append(
            ReportSection(
                id=f"geometric-pv-reference-{index}",
                title=text("geometric_pv_title", locale),
                paragraphs=[
                    text("geometric_pv_scope", locale),
                    text("geometric_pv_axes", locale),
                    *(
                        [text("geometric_pv_notes_scope", locale)]
                        if "arrays" in reference
                        else []
                    ),
                ],
                rows=rows,
            )
        )
    return result
