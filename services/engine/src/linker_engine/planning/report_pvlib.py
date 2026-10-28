"""Readable projection of retained pvlib inputs and output, without calculation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Json, Object
from .errors import VersionUnavailable
from .pv_dc_profile import project_dc
from .pv_profile_artifacts import model_dependencies, prepared_profile
from .report_copy import text
from .report_numbers import significant, span
from .report_pv_arrays import array_identities, placements_of
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
    source_fields = ("request", "capture", "interpretation")
    tmy = (
        any(
            field in details or "weather_" + field in metadata
            for field in source_fields
        )
        or details.get("adapter") == "pvgis_5_3_tmy_explicit_two_axes_v1"
    )
    capture_dependencies: Object = {}
    if tmy:
        for field in source_fields:
            if not isinstance(details.get(field), dict) or details[
                field
            ] != metadata.get("weather_" + field):
                raise VersionUnavailable("the frozen PV weather provenance differs")
        capture_dependencies["weather_capture"] = blobs.put_object(
            _object(details["capture"])
        )
    parameters = _object(inputs["parameters"])
    geometry = _object(inputs["geometry"])
    # Native retained references can use synthetic/non-TMY weather and omit
    # optional summary metadata. Their verified axis/output remain reportable;
    # no official request, capture or typical-year facts are invented for them.
    summary = dict(_object(metadata.get("interpretation", {})))
    for field, instant in {
        "start_utc": ac.intervals[0].start,
        "end_utc": ac.intervals[-1].end,
    }.items():
        if field not in summary:
            summary[field] = instant.isoformat()
        else:
            value = summary[field]
            try:
                if (
                    not isinstance(value, str)
                    or datetime.fromisoformat(value) != instant
                ):
                    raise ValueError
            except ValueError as error:
                raise VersionUnavailable(
                    "the frozen PV summary axis differs"
                ) from error
    for field, value in {
        "interval_count": len(ac.intervals),
        "energy_kwh": witness["energy_kwh"],
        "measurement": "pv_available_ac",
    }.items():
        if field in summary and (
            isinstance(summary[field], bool) or summary[field] != value
        ):
            raise VersionUnavailable("the frozen PV summary differs from its output")
        summary.setdefault(field, value)
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
    return {
        "parameters": parameters,
        "profile_summary": summary,
        **({"converter_id": converter_id} if converter_id is not None else {}),
        "weather": details,
        "arrays": array_identities(
            cast(list[Json], witness["arrays"]),
            placements_of(geometry),
            selected=selected,
        ),
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
            **capture_dependencies,
            "geometry": blobs.put_object(geometry),
        },
    }


@dataclass(frozen=True)
class PvReferenceParts:
    """The parts one PV coefficient/source section reads, named explicitly.

    Both the unshaded and the geometric reference store these same facts under
    slightly different nesting. Each caller states them once here, so the row
    builder never has to be handed a fabricated reference document.
    """

    parameters: Object
    weather: Object
    profile_summary: Object
    # Reports saved before component identities were retained keep their own
    # rows. Absence is a historical shape, not a corrupt reference.
    components: Object | None
    arrays: list[Object]
    converters: list[Object]
    used_by: list[Object]
    dependencies: Object
    converter_id: str | None = None

    @classmethod
    def of(cls, reference: Object) -> PvReferenceParts:
        """Read the canonical saved-reference shape."""
        converter = reference.get("converter_id")
        saved = reference.get("pv_components")
        return cls(
            parameters=_object(reference["parameters"]),
            weather=_object(reference["weather"]),
            profile_summary=_object(reference["profile_summary"]),
            components=_object(saved) if isinstance(saved, dict) else None,
            arrays=cast(list[Object], reference["arrays"]),
            converters=cast(list[Object], reference["converters"]),
            used_by=cast(list[Object], reference["used_by"]),
            dependencies=_object(reference["dependencies"]),
            converter_id=converter if isinstance(converter, str) else None,
        )


def pvlib_rows(
    parts: PvReferenceParts,
    locale: str,
    *,
    skip: frozenset[str] = frozenset(),
    note_key: str = "pvlib_note",
) -> list[ReportRow]:
    """Rows for one saved reference, minus the copy keys its caller owns.

    A section that already names the model, period, databases or usage passes
    those keys in `skip`, instead of comparing its own translated labels after
    the fact: an edited translation cannot silently re-add a row.
    """
    parameters = parts.parameters
    weather = parts.weather
    tmy = isinstance(weather.get("capture"), dict)
    summary = parts.profile_summary
    # Reports saved before component identities were retained keep their own
    # rows: no capacity claim is invented for a reference that recorded none.
    components = parts.components
    dc_group = parts.converter_id is not None

    # One display format for the whole report, from the caller's locale. A raw
    # float repr such as 9315.200808684325 kWh beside the same report's
    # 9,315.201 kWh is a formatting drift, not precision a reader can act on.
    def number(value: Json) -> str:
        return significant(value, locale)

    def one(key: str, value: Json, href: str | None = None) -> ReportRow | None:
        if key in skip:
            return None
        label = text(note_key, locale) if key == "pvlib_note" else text(key, locale)
        return ReportRow(label=label, value=str(value), href=href)

    def many(items: Iterable[tuple[str, Json]]) -> list[ReportRow | None]:
        return [one(key, value) for key, value in items]

    def add(target: list[ReportRow | None], row: ReportRow | None) -> None:
        target.append(row)

    rows: list[ReportRow | None] = [
        one(
            "pvlib_model",
            f"{parameters['model']} / pvlib {parameters['pvlib_version']}",
        )
    ]
    if tmy:
        request = _object(weather["request"])
        capture = _object(weather["capture"])
        interpretation = _object(weather["interpretation"])
        rows.extend(
            many(
                [
                    (
                        "pvlib_weather_period",
                        f"{request['start_year']}–{request['end_year']}",
                    ),
                    ("pvgis_radiation_database", weather["radiation_database"]),
                    ("pvlib_meteo_database", weather["meteo_database"]),
                    (
                        "pvgis_terrain_horizon",
                        text(
                            "pvgis_horizon_included"
                            if request["use_terrain_horizon"]
                            else "pvgis_horizon_omitted",
                            locale,
                        ),
                    ),
                    (
                        "pvlib_synthetic_year",
                        interpretation["synthetic_energy_year"],
                    ),
                ]
            )
        )
    rows.extend(
        many(
            [
                ("period", span(summary["start_utc"], summary["end_utc"], locale)),
                ("intervals", summary["interval_count"]),
                (
                    "pvlib_dc_energy" if dc_group else "pvgis_ac_energy",
                    f"{number(summary['energy_kwh'])} kWh",
                ),
            ]
        )
    )
    if tmy:
        rows.extend(
            many(
                [
                    (
                        "pvlib_offset",
                        f"{number(weather['irradiance_time_offset_hours'])} h / {number(weather['irradiance_offset_microseconds'])} µs",
                    ),
                    (
                        "pvlib_selected_months",
                        "; ".join(
                            f"{_object(m)['month']}: {_object(m)['year']}"
                            for m in cast(list[Json], weather["months_selected"])
                        ),
                    ),
                ]
            )
        )
    add(rows, one("pvlib_temporal", parameters["temporal_policy"]))
    if tmy:
        rows.extend(
            many(
                [
                    ("pvlib_solar_dates", weather["solar_date_basis"]),
                    (
                        "pvlib_radiation_semantics",
                        weather["native_radiation_semantics"],
                    ),
                ]
            )
        )
        if "pvlib_original_request" not in skip:
            # The provider URL is both the shown value and its own link.
            url = str(capture["requested_url"])
            rows.append(
                ReportRow(
                    label=text("pvlib_original_request", locale), value=url, href=url
                )
            )
        add(rows, one("pvlib_capture_time", capture["received_at_utc"]))
    else:
        rows.extend(
            many(
                [
                    ("pvlib_original_request", text("not_defined", locale)),
                    ("pvlib_capture_time", text("not_defined", locale)),
                ]
            )
        )
    # A reference that recorded no component list predates component
    # retention. Its other rows stay exactly as saved, and no capacity is
    # invented from a current layout for it.
    if components is not None:
        rows.append(
            one(
                "pv_components_capacity",
                f"{number(components['nameplate_kwp'])} kWp",
            )
        )
    rows.append(one("pvlib_note", parameters["source_note"]))
    if dc_group:
        add(rows, one("pvlib_selected_dc_group", parts.converter_id))
    for use in parts.used_by:
        key = (
            "comparison_" + str(use["comparison_role"])
            if "comparison_role" in use
            else "pvgis_source_run"
        )
        add(
            rows,
            one(key, f"{use['run_id']} / {use['revision']} / {use['binding']}"),
        )
    for component in cast(
        list[Object], components.get("components", []) if components else []
    ):
        citation = _object(component["source"])
        add(
            rows,
            one(
                "pvlib_module",
                f"{number(component['quantity'])} × {component['model']} / {number(component['stc_power_w'])} W; {citation.get('document_sha256')} / p. {citation.get('page')}",
            ),
        )
    modules = {
        str(_object(m)["module_spec_id"]): _object(m)
        for m in cast(list[Json], parameters["modules"])
    }
    array_parameters = {
        str(_object(a)["array_id"]): _object(a)
        for a in cast(list[Json], parameters["arrays"])
    }
    for array in parts.arrays:
        parameter = array_parameters[str(array["id"])]
        thermal = _object(parameter["thermal"])
        normal = (
            "["
            + "; ".join(
                number(value) for value in cast(list[Json], array["normal_enu"])
            )
            + "]"
        )
        rows.extend(
            many(
                [
                    ("pvlib_array", array["id"]),
                    (
                        "pvlib_array_geometry",
                        f"{number(array['module_count'])} / {number(array['stc_power_w'])} W / {number(array['tilt_deg'])}° / {number(array['azimuth_north_clockwise_deg'])}° / {normal}",
                    ),
                    (
                        "pvlib_clearance",
                        f"{number(array.get('lower_edge_clearance_m'))} m",
                    ),
                    (
                        "pvlib_gamma",
                        f"{number(modules[str(array['module_spec_id'])]['gamma_pdc_per_c'])} / °C",
                    ),
                    (
                        "pvlib_transposition",
                        f"{parameter['transposition']} / {number(parameter['albedo'])}",
                    ),
                    (
                        "pvlib_iam",
                        f"{parameter['beam_iam_model']} / {number(parameter['beam_iam_b'])} / {number(parameter['sky_diffuse_iam_factor'])} / {number(parameter['ground_diffuse_iam_factor'])}",
                    ),
                    (
                        "pvlib_retention",
                        f"{number(parameter['spectral_factor'])} / {number(parameter['soiling_factor'])} / {number(parameter['dc_wiring_factor'])} / {number(parameter['dc_mismatch_factor'])}",
                    ),
                    (
                        "pvlib_thermal",
                        f"{thermal['model']}; a={number(thermal['a'])}; b={number(thermal['b'])} s/m; delta T={number(thermal['delta_t_c'])} °C",
                    ),
                    ("pvlib_note", parameter["source_note"]),
                    ("pvlib_note", thermal["source_note"]),
                ]
            )
        )
        if array.get("mounting_note"):
            add(rows, one("pvlib_note", array["mounting_note"]))
    converters = {str(c["id"]): c for c in parts.converters}
    for converter in cast(list[Object], parameters["converters"]):
        rows.extend(
            many(
                [
                    (
                        "pvlib_converter",
                        f"{converter['id']} / {converter['array_ids']}",
                    ),
                    (
                        "pvlib_conversion",
                        f"{converter['model']} / {converter['input_assumption']}",
                    ),
                    (
                        "pvlib_conversion_power",
                        f"{number(converter['reference_dc_power_w'])} W / {number(converters[str(converter['id'])]['model_ac_cap_w'])} W",
                    ),
                    (
                        "pvlib_conversion_eta",
                        f"{number(converter['eta_nominal'])} / {number(converter['eta_reference'])}",
                    ),
                    ("pvlib_note", converter["source_note"]),
                ]
            )
        )
    for name, sha in parts.dependencies.items():
        add(rows, one("pvlib_evidence", f"{name}: {sha}"))
    # `skip` names copy keys only; evidence, module, array and converter rows
    # always belong to the section that owns the reference.
    return [row for row in rows if row is not None]


def pvlib_sections(source: Object, locale: str) -> list[ReportSection]:
    references = source.get("pvlib_references")
    if not isinstance(references, list):
        return []  # Historical report bundles keep their original shape.
    sections = []
    for index, value in enumerate(references):
        reference = _object(value)
        weather = _object(reference["weather"])
        tmy = isinstance(weather.get("capture"), dict)
        dc_group = isinstance(reference.get("converter_id"), str)
        sections.append(
            ReportSection(
                id=f"pvlib-reference-{index}",
                title=text("pvlib_reference", locale),
                paragraphs=[
                    text(
                        ("pvlib_dc_scope" if dc_group else "pvlib_reference_scope")
                        if tmy
                        else "pv_scope",
                        locale,
                    ),
                    text("pvlib_thermal_scope", locale),
                    *(
                        [text("pv_components_dc_scope", locale)]
                        if dc_group and not tmy
                        else []
                    ),
                ],
                rows=pvlib_rows(PvReferenceParts.of(reference), locale),
            )
        )
    return sections
