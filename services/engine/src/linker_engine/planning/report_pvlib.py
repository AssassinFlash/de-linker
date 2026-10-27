"""Readable projection of retained pvlib inputs and output, without calculation."""

from __future__ import annotations

from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .errors import VersionUnavailable
from .pv_dc_profile import project_dc
from .pv_profile_artifacts import model_dependencies, prepared_profile
from .report_copy import text
from .report_pv_components import pv_components
from .storage import Blobs


def _object(value: Json) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("the frozen PV reference document is incomplete")
    return value


def pvlib_reference(
    blobs: Blobs, raw_sha256: str, metadata: Object, *, converter_id: str | None = None
) -> Object:
    # This validates the retained axis/values and hash bindings. It neither
    # calls generate_pv nor reads current project geometry or model parameters.
    ac = prepared_profile(blobs, raw_sha256, metadata)
    dependencies = model_dependencies(metadata)
    inputs = blobs.object(dependencies["pv_model_inputs"])
    witness = blobs.object(dependencies["pv_model_witness"])
    weather = _object(_object(inputs["weather"])["source"])
    details = _object(weather["details"])
    for field in ("request", "capture", "interpretation"):
        if details.get(field) != metadata.get("weather_" + field):
            raise VersionUnavailable("the frozen PV weather provenance differs")
    capture = _object(details["capture"])
    capture_sha = blobs.put_object(capture)
    parameters = _object(inputs["parameters"])
    geometry = _object(inputs["geometry"])
    summary = _object(metadata["interpretation"])
    selected: set[str] | None = None
    if converter_id is not None:
        dc = project_dc(
            ac, inputs, witness, dependencies["pv_model_witness"], converter_id
        )
        selected = set(dc.array_ids)
        active = [
            a
            for a in cast(list[Object], parameters["arrays"])
            if a["array_id"] in selected
        ]
        module_ids = {
            a["module_spec_id"]
            for a in cast(list[Object], witness["arrays"])
            if a["id"] in selected
        }
        parameters = {
            **parameters,
            "arrays": cast(list[Json], active),
            "modules": [
                m
                for m in cast(list[Object], parameters["modules"])
                if m["module_spec_id"] in module_ids
            ],
            "converters": [
                c
                for c in cast(list[Object], parameters["converters"])
                if c["id"] == converter_id
            ],
        }
        summary = {
            **summary,
            "measurement": dc.measurement,
            "energy_kwh": dc.total_kwh,
        }
    arrays: list[Json] = []
    for value in cast(list[Json], witness["arrays"]):
        array = _object(value)
        if selected is not None and array["id"] not in selected:
            continue
        placement = next(
            _object(item)
            for item in cast(list[Json], geometry["arrays"])
            if _object(item)["id"] == array["id"]
        )
        arrays.append(
            {
                **{
                    key: array[key]
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
                "mounting_note": placement.get("mounting_note"),
                "lower_edge_clearance_m": placement.get("lower_edge_clearance_m"),
            }
        )
    return {
        "parameters": parameters,
        "profile_summary": summary,
        **({"converter_id": converter_id} if converter_id is not None else {}),
        "weather": details,
        "arrays": arrays,
        "converters": [
            {key: _object(item)[key] for key in ("id", "model_ac_cap_w")}
            for item in cast(list[Json], witness["converters"])
            if converter_id is None or _object(item)["id"] == converter_id
        ],
        "pv_components": pv_components(
            blobs, raw_sha256, metadata, converter_id=converter_id
        ),
        "dependencies": {
            **dependencies,
            "weather_original": raw_sha256,
            "weather_capture": capture_sha,
            "geometry": blobs.put_object(geometry),
        },
    }


def pvlib_sections(source: Object, locale: str) -> list[ReportSection]:
    references = source.get("pvlib_references")
    if not isinstance(references, list):
        return []  # Historical report bundles keep their original shape.

    def row(key: str, value: Json, href: str | None = None) -> ReportRow:
        return ReportRow(label=text(key, locale), value=str(value), href=href)

    sections = []
    for index, value in enumerate(references):
        reference = _object(value)
        parameters = _object(reference["parameters"])
        weather = _object(reference["weather"])
        request = _object(weather["request"])
        capture = _object(weather["capture"])
        interpretation = _object(weather["interpretation"])
        summary = _object(reference["profile_summary"])
        parts = _object(reference["pv_components"])
        dc_group = isinstance(reference.get("converter_id"), str)
        rows = [
            row(
                "pvlib_model",
                f"{parameters['model']} / pvlib {parameters['pvlib_version']}",
            ),
            row(
                "pvlib_weather_period", f"{request['start_year']}–{request['end_year']}"
            ),
            row("pvgis_radiation_database", weather["radiation_database"]),
            row("pvlib_meteo_database", weather["meteo_database"]),
            row(
                "pvgis_terrain_horizon",
                text(
                    "pvgis_horizon_included"
                    if request["use_terrain_horizon"]
                    else "pvgis_horizon_omitted",
                    locale,
                ),
            ),
            row("pvlib_synthetic_year", interpretation["synthetic_energy_year"]),
            row("period", f"{summary['start_utc']} – {summary['end_utc']}"),
            row("intervals", summary["interval_count"]),
            row(
                "pvlib_dc_energy" if dc_group else "pvgis_ac_energy",
                f"{summary['energy_kwh']} kWh",
            ),
            row(
                "pvlib_offset",
                f"{weather['irradiance_time_offset_hours']} h / {weather['irradiance_offset_microseconds']} µs",
            ),
            row(
                "pvlib_selected_months",
                "; ".join(
                    f"{_object(m)['month']}: {_object(m)['year']}"
                    for m in cast(list[Json], weather["months_selected"])
                ),
            ),
            row("pvlib_temporal", parameters["temporal_policy"]),
            row("pvlib_solar_dates", weather["solar_date_basis"]),
            row("pvlib_radiation_semantics", weather["native_radiation_semantics"]),
            row(
                "pvlib_original_request",
                str(capture["requested_url"]),
                str(capture["requested_url"]),
            ),
            row("pvlib_capture_time", capture["received_at_utc"]),
            row("pv_components_capacity", f"{parts['nameplate_kwp']} kWp"),
            row("pvlib_note", parameters["source_note"]),
        ]
        if dc_group:
            rows.append(row("pvlib_selected_dc_group", reference["converter_id"]))
        for use in cast(list[Object], reference["used_by"]):
            rows.append(
                row(
                    "comparison_" + str(use["comparison_role"])
                    if "comparison_role" in use
                    else "pvgis_source_run",
                    f"{use['run_id']} / {use['revision']} / {use['binding']}",
                )
            )
        for component in cast(list[Object], parts.get("components", [])):
            citation = _object(component["source"])
            rows.append(
                row(
                    "pvlib_module",
                    f"{component['quantity']} × {component['model']} / {component['stc_power_w']} W; {citation.get('document_sha256')} / p. {citation.get('page')}",
                )
            )
        modules = {
            str(_object(m)["module_spec_id"]): _object(m)
            for m in cast(list[Json], parameters["modules"])
        }
        array_parameters = {
            str(_object(a)["array_id"]): _object(a)
            for a in cast(list[Json], parameters["arrays"])
        }
        for array in cast(list[Object], reference["arrays"]):
            parameter = array_parameters[str(array["id"])]
            thermal = _object(parameter["thermal"])
            rows.extend(
                [
                    row("pvlib_array", array["id"]),
                    row(
                        "pvlib_array_geometry",
                        f"{array['module_count']} / {array['stc_power_w']} W / {array['tilt_deg']}° / {array['azimuth_north_clockwise_deg']}° / {array['normal_enu']}",
                    ),
                    row("pvlib_clearance", f"{array.get('lower_edge_clearance_m')} m"),
                    row(
                        "pvlib_gamma",
                        f"{modules[str(array['module_spec_id'])]['gamma_pdc_per_c']} / °C",
                    ),
                    row(
                        "pvlib_transposition",
                        f"{parameter['transposition']} / {parameter['albedo']}",
                    ),
                    row(
                        "pvlib_iam",
                        f"{parameter['beam_iam_model']} / {parameter['beam_iam_b']} / {parameter['sky_diffuse_iam_factor']} / {parameter['ground_diffuse_iam_factor']}",
                    ),
                    row(
                        "pvlib_retention",
                        f"{parameter['spectral_factor']} / {parameter['soiling_factor']} / {parameter['dc_wiring_factor']} / {parameter['dc_mismatch_factor']}",
                    ),
                    row(
                        "pvlib_thermal",
                        f"{thermal['model']}; a={thermal['a']}; b={thermal['b']} s/m; delta T={thermal['delta_t_c']} °C",
                    ),
                    row("pvlib_note", parameter["source_note"]),
                    row("pvlib_note", thermal["source_note"]),
                    *(
                        [row("pvlib_note", array["mounting_note"])]
                        if array.get("mounting_note")
                        else []
                    ),
                ]
            )
        converters = {
            str(_object(c)["id"]): _object(c)
            for c in cast(list[Json], reference["converters"])
        }
        for converter in cast(list[Object], parameters["converters"]):
            rows.extend(
                [
                    row(
                        "pvlib_converter",
                        f"{converter['id']} / {converter['array_ids']}",
                    ),
                    row(
                        "pvlib_conversion",
                        f"{converter['model']} / {converter['input_assumption']}",
                    ),
                    row(
                        "pvlib_conversion_power",
                        f"{converter['reference_dc_power_w']} W / {converters[str(converter['id'])]['model_ac_cap_w']} W",
                    ),
                    row(
                        "pvlib_conversion_eta",
                        f"{converter['eta_nominal']} / {converter['eta_reference']}",
                    ),
                    row("pvlib_note", converter["source_note"]),
                ]
            )
        for name, sha in _object(reference["dependencies"]).items():
            rows.append(row("pvlib_evidence", f"{name}: {sha}"))
        sections.append(
            ReportSection(
                id=f"pvlib-reference-{index}",
                title=text("pvlib_reference", locale),
                paragraphs=[
                    text(
                        "pvlib_dc_scope" if dc_group else "pvlib_reference_scope",
                        locale,
                    ),
                    text("pvlib_thermal_scope", locale),
                ],
                rows=rows,
            )
        )
    return sections
