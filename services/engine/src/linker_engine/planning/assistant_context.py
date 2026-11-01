"""Read owned saved inputs and selected immutable results without running work.

This is a bounded presentation of the same records the workbench displays.
It never grants current product permission or substitutes a new calculation.
"""

from __future__ import annotations

from typing import cast

from .assistant_calculation_sources import calculation_sources
from .brief import PlanningBrief
from .canonical import Json, Object, digest, encode
from .certificate_information import report_source_with_information
from .direct_beam_read import KIND as DIRECT_BEAM_KIND
from .direct_beam_read import direct_beam_bundle, direct_beam_facts
from .equipment_candidate_store import EquipmentCandidateStore
from .errors import InvalidInput
from .geometric_pv_inputs import KIND as GEOMETRIC_PV_KIND
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .geometric_pv_profile import prepared_profile as geometric_pv_profile
from .geometric_pv_profile import reference_bundle as geometric_pv_bundle
from .installation_report import installation_sections
from .project_materials import (
    material_name,
    material_quantity,
    material_reference,
    material_scope,
    project_materials,
)
from .pvgis_reference_inputs import PvgisReferenceInputs
from .pvgis_reference_profile import (
    PROFILE_PURPOSE,
    prepared_reference_profile,
    reference_bundle,
)
from .records import Actor, Run
from .report_copy import check_label, text
from .report_model import build_report
from .report_numbers import number, percent
from .workspace import Workspace

# Assistant context resource policies, not numerical/engineering limits.
MAX_ROWS = 256
MAX_TEXT_BYTES = 64 * 1024
_RATIOS = frozenset(
    {
        "solar_autarky",
        "pv_input_self_use",
        "pv_onsite_available_share",
        "solar_load_share_of_requested_demand",
    }
)
_ENERGY = frozenset(
    {
        "single_ac_energy_replay_v1",
        "shared_dc_energy_replay_v1",
        "plant_ac_energy_replay_v1",
        "plant_shared_dc_energy_replay_v1",
    }
)
_MATERIAL_HANDLING = frozenset(
    {
        "customer_supplied_required",
        "installation_requirement",
        "manufacturer_included",
        "pv_reference",
        "site_engineering_required",
        "woo_product",
    }
)


def _summary(value: Json) -> Json:
    """Keep aggregate metadata; interval/event arrays stay in the workbench."""
    if isinstance(value, list):
        return {
            "recorded_entries": len(value),
            "detail_scope": "not_in_assistant_summary",
        }
    if isinstance(value, dict):
        return {key: _summary(item) for key, item in value.items()}
    return value


def _rows(value: Json, locale: str, prefix: str = "") -> list[Json]:
    """Preserve producer field names and units; do not derive new metrics."""
    result: list[Json] = []
    if not isinstance(value, dict):
        return result
    for key, item in value.items():
        label = f"{prefix}.{key}" if prefix else key
        if key in _RATIOS and isinstance(item, dict):
            ratio = item.get("value")
            if isinstance(ratio, (int, float)) and not isinstance(ratio, bool):
                # Same ratio-to-percent presentation as report_model.build_report.
                result.append({"label": label, "value": percent(ratio * 100, locale)})
            else:
                result.append(
                    {
                        "label": label,
                        "value": None,
                        "undefined_reason": item.get("undefined_reason"),
                    }
                )
        elif isinstance(item, dict):
            result.extend(_rows(item, locale, label))
        elif isinstance(item, list):
            for index, child in enumerate(item):
                if isinstance(child, dict):
                    result.extend(_rows(child, locale, f"{label}[{index}]"))
                elif isinstance(child, (str, int, float, bool)) or child is None:
                    result.append({"label": f"{label}[{index}]", "value": child})
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            # Units are explicit in the existing producer's metric field names.
            unit = (
                "kWh"
                if key == "kwh" or key.endswith("_kwh")
                else "kW"
                if key.endswith("_kw")
                else "kWp"
                if key.endswith("_kwp")
                else ""
            )
            result.append({"label": label, "value": number(item, locale, unit)})
        else:
            if not isinstance(item, str) or not item.startswith(
                ("http://", "https://")
            ):
                result.append({"label": label, "value": item})
    return result


def _report_materials(workspace: Workspace, run: Run, result: Object) -> Json | None:
    """Expose one verified materials projection without duplicating its rows."""
    materials_sha = result.get("materials_sha256")
    if materials_sha is None:
        return None  # Reports frozen before the materials model retain their rows.
    if (
        not isinstance(materials_sha, str)
        or len(materials_sha) != 64
        or any(character not in "0123456789abcdef" for character in materials_sha)
    ):
        raise InvalidInput("saved report materials identity is invalid")
    dependencies = result.get("dependencies")
    if (
        not isinstance(dependencies, dict)
        or dependencies.get("materials_model") != materials_sha
    ):
        raise InvalidInput("saved report materials dependency differs")
    manifest_context = run.manifest.get("context")
    models = (
        manifest_context.get("models") if isinstance(manifest_context, dict) else None
    )
    model = models.get("materials") if isinstance(models, dict) else None
    if not isinstance(model, str) or not model:
        raise InvalidInput("saved report materials model is missing")
    pinned = (
        manifest_context.get("assets") if isinstance(manifest_context, dict) else None
    )
    if (
        not isinstance(pinned, dict)
        or not isinstance(pinned.get("report.source"), str)
        or dependencies.get("report_source") != pinned["report.source"]
    ):
        raise InvalidInput("saved materials differ from the frozen report source")
    source = report_source_with_information(workspace.blobs, dependencies)
    source_dependencies = source.get("dependencies")
    if (
        source.get("project_id") != run.project_id
        or source.get("revision") != run.revision
        or source.get("input_sha256") != run.manifest.get("input_sha256")
        or not isinstance(source_dependencies, dict)
        or source_dependencies.get("materials_model") != materials_sha
    ):
        raise InvalidInput("saved report materials source differs from selected result")
    stored = source.get("materials")
    frozen = workspace.blobs.object(materials_sha)
    if (
        not isinstance(stored, dict)
        or stored != frozen
        or type(frozen.get("schema_version")) is not int
        or frozen.get("schema_version") != 3
        or frozen.get("kind") != model
        or frozen.get("installation_status") != "not_assessed"
        or frozen.get("project_id") != run.project_id
        or frozen.get("revision") != run.revision
        or frozen.get("input_sha256") != run.manifest.get("input_sha256")
    ):
        raise InvalidInput("saved report materials projection is inconsistent")
    raw_lines = frozen.get("lines")
    if not isinstance(raw_lines, list):
        raise InvalidInput("saved report materials lines are missing")
    handling_counts: dict[str, int] = {}
    unresolved = 0
    for line in raw_lines:
        if not isinstance(line, dict):
            raise InvalidInput("saved report materials line is invalid")
        raw_handling = line.get("handling")
        if (
            not isinstance(line.get("id"), str)
            or not isinstance(raw_handling, str)
            or raw_handling not in _MATERIAL_HANDLING
        ):
            raise InvalidInput("saved report materials line is invalid")
        quantity = line.get("quantity")
        if quantity is not None:
            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or quantity < 0
            ):
                raise InvalidInput("saved report materials quantity is invalid")
        handling = raw_handling
        handling_counts[handling] = handling_counts.get(handling, 0) + 1
        if quantity is None:
            unresolved += 1
    return {
        "status": "verified",
        "sha256": materials_sha,
        "model": model,
        "line_count": len(raw_lines),
        "unresolved_quantity_count": unresolved,
        "handling_counts": dict(sorted(handling_counts.items())),
        "scope": "provisional_not_complete_bos",
    }


def _string_link_projection(link: Object, private: str) -> Object:
    """v2 unit bindings are owner identifiers, not engineering scope text."""
    return (
        {
            **link,
            "unit_id": private if link["unit_id"] is not None else None,
            "inverter_instance_id": private
            if link.get("inverter_instance_id") is not None
            else None,
        }
        if "unit_id" in link
        else link
    )


def _materials_projection(source: Object, private: str) -> Object:
    """Apply the same boundary after either pinned or historical BOM loading."""
    materials = source.get("materials")
    if not isinstance(materials, dict):
        materials = project_materials(source)
    plan = source.get("installation")
    method = plan.get("method") if isinstance(plan, dict) else None
    lines: list[Json] = []
    for index, line in enumerate(cast(list[Object], materials["lines"]), 1):
        safe = {key: value for key, value in line.items() if key != "unit_name"}
        lines.append(safe)
        if line.get("handling") != "installation_requirement":
            continue
        if line.get("basis") == method:
            safe["label"] = {
                lang: f"{text('installation_conductor', lang)} {index}"
                for lang in ("en", "de")
            }
        origin = line.get("source")
        link = origin.get("link") if isinstance(origin, dict) else None
        if isinstance(origin, dict) and isinstance(link, dict):
            safe["source"] = {**origin, "link": _string_link_projection(link, private)}
    return {**materials, "lines": lines}


def _report_source_projection(source: Object, locale: str) -> Object:
    """Keep frozen engineering facts; project labels/notes remain owner-only.

    Redact native source fields before reusing the report presenter. This keeps
    the same numerical labels, source evidence and scope in either language,
    without parsing localized prose or changing the stored report/PDF/CSV.
    """
    projected = {**source, "locale": locale}
    raw_plan = source.get("installation")
    private = (
        "Im eigenen Bericht erfasst" if locale == "de" else "Recorded in owned report"
    )
    if not isinstance(raw_plan, dict):
        projected["materials"] = _materials_projection(projected, private)
        return projected
    # Copy only edited branches. Unrelated saved profiles and evidence are read
    # as-is, and no persistent blob or source object is changed.
    plan = {**raw_plan, "sources": []}
    projected["installation"] = plan
    plan["instances"] = [
        {
            **device,
            "name": f"{text('installation_instance', locale)} {index}",
            "ports": [
                {**port, "name": f"{text('installation_ports', locale)} {port_index}"}
                for port_index, port in enumerate(
                    cast(list[Object], device["ports"]), 1
                )
            ],
        }
        for index, device in enumerate(cast(list[Object], raw_plan["instances"]), 1)
    ]
    plan["cables"] = [
        {
            **cable,
            "name": f"{text('installation_conductor', locale)} {index}",
            "circuit_name": private,
            "route_name": private,
            "extra_length_note": private
            if cable.get("extra_length_note") is not None
            else None,
        }
        for index, cable in enumerate(cast(list[Object], raw_plan["cables"]), 1)
    ]
    reconciliation = raw_plan.get("pv_string_reconciliation")
    if isinstance(reconciliation, dict):
        plan["pv_string_reconciliation"] = {
            **reconciliation,
            "rows": [
                _string_link_projection(row, private)
                for row in cast(list[Object], reconciliation["rows"])
            ],
        }
    electrical = raw_plan.get("electrical")
    if isinstance(electrical, dict):
        circuits: list[Json] = []
        plan["electrical"] = {**electrical, "circuits": circuits}
        for index, circuit in enumerate(cast(list[Object], electrical["circuits"]), 1):
            conditions: list[Json] = []
            circuits.append(
                {
                    **circuit,
                    "name": f"{'Stromkreis' if locale == 'de' else 'Circuit'} {index}",
                    "conditions": conditions,
                }
            )
            for condition_index, result in enumerate(
                cast(list[Object], circuit["conditions"]), 1
            ):
                condition = cast(Object, result["condition"])
                limit = cast(Object, result["limit"])
                declared = limit.get("declared")
                conditions.append(
                    {
                        **result,
                        "name": f"{'Betriebsfall' if locale == 'de' else 'Condition'} {condition_index}",
                        "condition": {
                            **condition,
                            "source_note": private,
                            "arrangement": private
                            if condition.get("arrangement") is not None
                            else None,
                        },
                        "limit": {
                            **limit,
                            "declared": {**declared, "source_note": private}
                            if isinstance(declared, dict)
                            else declared,
                        },
                        "segments": [
                            {
                                **segment,
                                "run_id": f"{text('installation_conductor', locale)} {segment_index}",
                            }
                            for segment_index, segment in enumerate(
                                cast(list[Object], result["segments"]), 1
                            )
                        ],
                    }
                )
    projected["materials"] = _materials_projection(projected, private)
    return projected


def _installation_report_projection(
    report: Object, source: Object, locale: str
) -> Object:
    """Reuse stored non-installation sections; re-present only redacted branches."""
    safe = _report_source_projection(source, locale)
    replacements = {
        section.id: cast(Object, section.model_dump(mode="json"))
        for section in installation_sections(safe, locale)
    }
    materials = safe.get("materials")
    if not isinstance(materials, dict):
        materials = project_materials(safe)
    sections: list[Json] = []
    for section in cast(list[Object], report.get("sections", [])):
        identifier = str(section.get("id", ""))
        if identifier in replacements:
            sections.append(replacements[identifier])
        elif identifier == "bom" and isinstance(section.get("table"), dict):
            table = cast(Object, section["table"])
            sections.append(
                {
                    **section,
                    "table": {
                        **table,
                        "rows": [
                            [
                                material_quantity(line, locale),
                                material_name(line, locale),
                                material_reference(line),
                                material_scope(line, locale),
                            ]
                            for line in cast(list[Object], materials["lines"])
                        ],
                    },
                }
            )
        else:
            sections.append(section)
    return {**report, "sections": sections}


def _equipment_report_labels(
    source: Object | None, locale: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Use frozen semantic identities, never private names in saved headings."""
    labels: dict[str, str] = {}
    scopes: dict[str, str] = {}
    if source is None:
        return labels, scopes
    plant = source.get("equipment_plant")
    if isinstance(plant, dict):
        units = cast(list[Object], plant.get("units", []))
        names: dict[str, str] = {}
        for unit in units:
            raw_name, identity = unit.get("name"), unit.get("id")
            if isinstance(raw_name, str) and raw_name and isinstance(identity, str):
                names[identity] = raw_name
        for index, unit_name in enumerate(names.values(), 1):
            scopes[unit_name] = f"{text('plant_unit', locale)} {index}"
        for index, group in enumerate(
            cast(list[Object], plant.get("parallel_groups", [])), 1
        ):
            ids = group.get("unit_ids")
            if isinstance(ids, list) and ids and all(str(uid) in names for uid in ids):
                group_name = ", ".join(names[str(uid)] for uid in ids)
                scopes[group_name] = f"{text('plant_group', locale)} {index}"
    assessment = source.get("equipment")
    if not isinstance(assessment, dict):
        return labels, scopes
    for index, system in enumerate(
        cast(list[Object], assessment.get("systems", [])), 1
    ):
        name = system.get("name")
        if isinstance(name, str) and name:
            scopes[name] = f"{text('plant_unit', locale)} {index}"
    for index, check in enumerate(cast(list[Object], assessment.get("checks", []))):
        semantic = str(check.get("semantic_id", check["id"]))
        identifier = (
            f"check-controller-network-{index}"
            if semantic == "plant_controller_network_count"
            else f"check-{index}"
        )
        labels[identifier] = check_label(semantic, locale)
        for key, label in (("unit_name", "plant_unit"), ("group_name", "plant_group")):
            name = check.get(key)
            if isinstance(name, str) and name:
                scopes.setdefault(name, text(label, locale))
    for requirement in cast(
        list[Object], assessment.get("installation_requirements", [])
    ):
        for key, label in (("unit_name", "plant_unit"), ("group_name", "plant_group")):
            name = requirement.get(key)
            if isinstance(name, str) and name:
                scopes.setdefault(name, text(label, locale))
    return labels, scopes


def _equipment_scope_text(
    value: str, scopes: dict[str, str], *, exact: bool = True
) -> str:
    """Replace only producer scope prefixes; engineering numbers stay untouched."""
    for name, label in sorted(scopes.items(), key=lambda item: -len(item[0])):
        if exact and value == name:
            return label
        if value.startswith(name + " · "):
            return (
                label
                + " · "
                + _equipment_scope_text(value[len(name) + 3 :], scopes, exact=exact)
            )
    return value


def _equipment_context(value: Json, *, system: bool = False) -> Json:
    """Display names are owner text; preserve native IDs and engineering values."""
    if isinstance(value, list):
        return [_equipment_context(item, system=system) for item in value]
    if isinstance(value, dict):
        return {
            key: _equipment_context(item, system=key in {"units", "systems"})
            for key, item in value.items()
            if key not in {"unit_name", "group_name"}
            and not (
                key == "project_facts"
                and value.get("model") == "declared_grid_connection_evidence_v1"
            )
            and not (system and key == "name")
        }
    return value


def _result_rows(workspace: Workspace, run: Run, locale: str) -> list[Json]:
    result = run.result
    if result is None:
        return []
    kind = result.get("kind")
    if not isinstance(kind, str):
        raise InvalidInput("saved result kind is missing")
    if kind == DIRECT_BEAM_KIND:
        return _rows(
            direct_beam_facts(
                cast(Object, direct_beam_bundle(workspace, run)["witness"])
            ),
            locale,
        )
    if kind == "planning_report_v1":
        report = result.get("report")
        if not isinstance(report, dict):
            raise InvalidInput("saved report model is missing")
        has_installation = any(
            str(section.get("id", "")).startswith("installation-")
            for section in cast(list[Object], report.get("sections", []))
        )
        dependencies = cast(Object, result.get("dependencies", {}))
        source: Object | None = None
        has_checks = any(
            str(section.get("id", "")).startswith("check-")
            for section in cast(list[Object], report.get("sections", []))
        )
        if isinstance(dependencies.get("report_source"), str) and (
            has_installation or has_checks or report.get("locale") != locale
        ):
            source = report_source_with_information(workspace.blobs, dependencies)
            if (
                source.get("project_id") != run.project_id
                or source.get("revision") != run.revision
                or source.get("input_sha256") != run.manifest.get("input_sha256")
            ):
                raise InvalidInput("saved report source differs from selected result")
        if report.get("locale") != locale or (has_installation and source is not None):
            # Localize only presentation of its frozen source; no kernel, source
            # refresh, PDF, job, or persistent artifact is produced by this read.
            sha = dependencies.get("report_source")
            if not isinstance(sha, str):
                raise InvalidInput("saved report source is missing")
            assert source is not None
            if report.get("locale") == locale:
                report = _installation_report_projection(report, source, locale)
            else:
                report = cast(
                    Object,
                    build_report(_report_source_projection(source, locale)).model_dump(
                        mode="json"
                    ),
                )
        elif has_installation:
            # Source-less historical reports remain readable. Their fixed
            # installation scope is safe, but unstructured project details
            # cannot be separated from private text without the native source.
            sections: list[Json] = []
            for section in cast(list[Object], report.get("sections", [])):
                if str(section.get("id", "")).startswith("installation-"):
                    sections.append(
                        {
                            **section,
                            "title": text("installation", locale),
                            "rows": section.get("rows", [])
                            if section.get("id") == "installation-pv-string-links"
                            else [],
                            "table": None,
                        }
                    )
                elif section.get("id") == "bom":
                    sections.append({**section, "table": None})
                else:
                    sections.append(section)
            report = {**report, "sections": sections}
        check_titles, scope_names = _equipment_report_labels(
            source
            if source is not None
            else workspace.pinned_inputs(run.manifest)
            if has_checks
            else None,
            locale,
        )
        rows: list[Json] = []
        for section in cast(list[Object], report.get("sections", [])):
            if section.get("id") in {"site", "grid-connection-declarations"}:
                continue  # Owner-entered addresses, references and notes stay in the report.
            title = str(section.get("title", ""))
            if str(section.get("id", "")).startswith("check-controller-network-"):
                # The saved owner heading contains the project’s free group name.
                title = check_label("plant_controller_network_count", locale)
            elif str(section.get("id", "")).startswith("check-"):
                # Older source-less reports remain readable without releasing
                # an unstructured customer-defined system/group heading.
                title = check_titles.get(str(section["id"]), text("equipment", locale))
            title = _equipment_scope_text(title, scope_names)
            # Comparison-side paragraphs contain the customer's free source note.
            paragraphs = (
                []
                if section.get("id") in {"comparison-baseline", "comparison-candidate"}
                or (source is None and has_checks and section.get("id") == "conditions")
                else section.get("paragraphs", [])
            )
            for paragraph in cast(list[str], paragraphs):
                rows.append(
                    {
                        "label": title,
                        "value": _equipment_scope_text(paragraph, scope_names),
                    }
                )
            for row in cast(list[Object], section.get("rows", [])):
                # The comparison also repeats site fields outside the site section.
                if row.get("label") == text("location", locale):
                    continue
                # Device source notes stay in the owned report like other private
                # project notes; they are not part of the assistant projection.
                if str(section.get("id", "")).startswith("certificate-device-") and (
                    row.get("label")
                    == text("certificate_condition_source_note", locale)
                ):
                    continue
                if str(section.get("id", "")).startswith("pvgis-roof-reference-") and (
                    row.get("label") == text("pvgis_reference_note", locale)
                ):
                    continue  # The owned report retains this free-form assumption.
                if str(section.get("id", "")).startswith(
                    ("pvlib-reference-", "geometric-pv-reference-")
                ) and (
                    row.get("label")
                    in {
                        text(key, locale)
                        for key in (
                            "pvlib_note",
                            "geometric_pv_original_note",
                            "pvlib_original_request",
                            "pvlib_array",
                            "pvlib_converter",
                            "pvlib_selected_dc_group",
                        )
                    }
                ):
                    # Notes, editable identifiers and the coordinate-bearing
                    # request remain in the owner's report, not assistant input.
                    continue
                # Original report text is history; current document access is separate.
                rows.append(
                    {
                        "label": f"{title}: "
                        + (
                            text("source", locale)
                            if source is None
                            and has_checks
                            and section.get("id") == "conditions"
                            else _equipment_scope_text(str(row["label"]), scope_names)
                        ),
                        "value": row["value"],
                    }
                )
            table = section.get("table")
            if section.get("id") == "installation-pv-string-links":
                # Keep the fixed scope/missing-plan explanation above, while
                # user-defined string/circuit/endpoint IDs stay owner-only.
                continue
            if isinstance(table, dict):
                if source is None and has_checks and section.get("id") == "bom":
                    continue  # Historical unstructured product labels can embed names.
                columns = cast(list[str], table["columns"])
                for cells in cast(list[list[str]], table["rows"]):
                    rows.append(
                        {
                            "label": title,
                            "value": {
                                column: text("plant_unit", locale)
                                if source is None
                                and has_checks
                                and column == text("plant_unit", locale)
                                else _equipment_scope_text(
                                    cell,
                                    scope_names,
                                    exact=column == text("plant_unit", locale),
                                )
                                for column, cell in zip(columns, cells, strict=True)
                            },
                        }
                    )
        return rows
    if kind in _ENERGY:
        return _rows(result.get("metrics"), locale) + _rows(
            {
                key: _summary(result.get(key))
                for key in (
                    "profile_interpretation",
                    "country_assessment",
                    "equipment_release",
                    "scenario_constraint_status",
                    "verification",
                    "model",
                    "battery_parameter_provenance",
                )
            },
            locale,
        )
    if kind == GEOMETRIC_PV_KIND:
        asset = cast(Object, result.get("prepared_asset", {}))
        metadata = cast(Object, asset.get("metadata", {}))
        inputs = workspace.pinned_inputs(run.manifest)
        if (
            asset.get("project_id") != run.project_id
            or asset.get("purpose") != GEOMETRIC_PV_PURPOSE
            or metadata.get("derived_from_revision") != run.revision
            or metadata.get("geometry_sha256") != digest(encode(inputs.get("geometry")))
            or metadata.get("parameters_sha256")
            != digest(encode(inputs.get("geometric_pv_preparation")))
            or result.get("profile_summary") != metadata.get("interpretation")
            or workspace.blobs.object(str(asset.get("metadata_sha256"))) != metadata
        ):
            raise InvalidInput("saved geometric PV reference differs from its source")
        raw_sha = str(asset.get("content_sha256"))
        geometric_pv_profile(workspace.blobs, raw_sha, metadata)
        bundle = geometric_pv_bundle(workspace.blobs, raw_sha, metadata)
        model_inputs = cast(Object, bundle["inputs"])
        witness = cast(Object, bundle["witness"])
        weather = cast(Object, model_inputs["weather"])
        weather_source = cast(Object, weather["source"])
        weather_details = cast(Object, weather_source["details"])
        request = cast(Object, weather_details["request"])
        interpretation = cast(Object, weather_details["interpretation"])
        geometry = cast(Object, model_inputs["geometry"])
        specifications = {
            str(item["id"]): item
            for item in cast(list[Object], geometry["module_specs"])
        }
        counts: dict[str, int] = {}
        for array in cast(list[Object], witness["arrays"]):
            identity = str(array["module_spec_id"])
            counts[identity] = counts.get(identity, 0) + cast(
                int, array["module_count"]
            )
        return _rows(
            {
                "profile_summary": result["profile_summary"],
                "model": result["model"],
                "scope": result["scope"],
                "weather_reference": {
                    "selection_start_year": request["start_year"],
                    "selection_end_year": request["end_year"],
                    "radiation_database": request["expected_radiation_database"],
                    "meteo_database": request["expected_meteo_database"],
                    "synthetic_energy_year": interpretation["synthetic_energy_year"],
                    "irradiance_time_offset_hours": weather_details[
                        "irradiance_time_offset_hours"
                    ],
                    "months_selected": weather_details["months_selected"],
                },
                "included_modules": [
                    {
                        "model": specifications[identity]["model"],
                        "quantity": count,
                        "module_power_w": number(
                            specifications[identity]["stc_power_w"], locale, "W"
                        ),
                    }
                    for identity, count in counts.items()
                ],
                **{
                    key: result[key]
                    for key in (
                        "country_assessment",
                        "equipment_release",
                        "near_shading_assessment",
                    )
                },
            },
            locale,
        )
    if kind == "prepare_pvgis_roof_ac_reference_v1":
        asset = cast(Object, result.get("prepared_asset", {}))
        metadata = cast(Object, asset.get("metadata", {}))
        inputs = workspace.pinned_inputs(run.manifest)
        if (
            asset.get("project_id") != run.project_id
            or asset.get("purpose") != PROFILE_PURPOSE
            or metadata.get("derived_from_revision") != run.revision
            or metadata.get("geometry_sha256") != digest(encode(inputs.get("geometry")))
            or metadata.get("parameters_sha256")
            != digest(encode(inputs.get("pvgis_reference")))
            or result.get("profile_summary") != metadata.get("interpretation")
            or workspace.blobs.object(str(asset.get("metadata_sha256"))) != metadata
        ):
            raise InvalidInput("saved roof reference differs from its source")
        raw_sha = str(asset.get("content_sha256"))
        prepared_reference_profile(workspace.blobs, raw_sha, metadata)
        bundle = reference_bundle(workspace.blobs, raw_sha, metadata)
        parameters = PvgisReferenceInputs.read(bundle["parameters"])
        geometry, plan = cast(Object, bundle["geometry"]), cast(Object, bundle["plan"])
        arrays = cast(list[Object], plan["arrays"])
        modules: list[Json] = []
        for module in cast(list[Object], geometry["module_specs"]):
            count = sum(
                cast(int, a["module_count"])
                for a in arrays
                if a["module_spec_id"] == module["id"]
            )
            if not count:
                continue
            source = cast(Object, module["source"])
            modules.append(
                {
                    "model": module["model"],
                    "quantity": count,
                    "stc_power_w": module["stc_power_w"],
                    "woo": source.get("woo"),
                    "document_sha256": source.get("document_sha256"),
                    "page": source.get("page"),
                }
            )
        return _rows(
            {
                "profile_summary": result["profile_summary"],
                "reference_model_choices": {
                    **cast(
                        Object,
                        parameters.model_dump(mode="json", exclude={"source_note"}),
                    ),
                    "year": str(parameters.year),
                },
                "included_modules": modules,
                "source_dependencies": metadata["dependencies"],
                "country_assessment": result.get("country_assessment"),
                "equipment_release": result.get("equipment_release"),
                "near_shading_assessment": result.get("near_shading_assessment"),
            },
            locale,
        )
    if isinstance(result.get("profile_summary"), dict):
        return _rows(
            {
                key: result.get(key)
                for key in (
                    "profile_summary",
                    "verification",
                    "scope",
                    "warnings",
                    "model",
                    "included_modules",
                    "capacity_kwp",
                    "country_assessment",
                    "equipment_release",
                    "near_shading_assessment",
                )
            },
            locale,
        )
    if kind == "search_woo_equipment_v1":
        return _rows(_equipment_context(result.get("search")), locale)
    assessment = result.get("assessment")
    if isinstance(assessment, dict):
        # The assessment is a saved observation, not current recommendation permission.
        return _rows(_equipment_context(assessment), locale)
    return []


def assistant_context(
    workspace: Workspace,
    actor: Actor,
    project_id: str,
    revision: int,
    run_ids: list[str],
    locale: str,
    *,
    unsaved_changes: bool = False,
) -> Object:
    project = workspace.get(actor, project_id, revision=revision)
    current = workspace.get(actor, project_id)
    result: Object = {
        "schema_version": 1,
        "status": "unsaved_changes" if unsaved_changes else "available",
        "project": {
            "id": project.id,
            "title": project.title,
            "revision": project.revision,
            "current_revision": current.revision,
            "input_sha256": project.input_sha256,
        },
        "rows": [],
        "runs": [],
        "truncated": False,
        "adopted_equipment": None,
        "locale": locale,
        "authority": "owned_saved_inputs_and_immutable_analysis_snapshots",
        "current_product_permission": "not_granted_by_this_context",
    }
    if unsaved_changes:
        return result
    if len(run_ids) > 2 or len(set(run_ids)) != len(run_ids):
        raise InvalidInput("choose one result or the workbench's two-result comparison")
    brief = project.inputs.get("brief")
    if isinstance(brief, dict):
        typed = PlanningBrief.model_validate(brief)
        # Exact coordinates and free-form project notes are unnecessary for this read.
        data = typed.model_dump(mode="json")
        site = cast(Object, data["site"])
        data["site"] = {key: site.get(key) for key in ("country_code", "timezone")}
        data.pop("project_note", None)
        annual = cast(Object, data["annual_load"])
        annual.pop("source_note", None)
        result["rows"] = _rows(cast(Object, data), locale)
    for key in ("equipment_setup", "equipment_plant"):
        if isinstance(project.inputs.get(key), dict):
            cast(list[Json], result["rows"]).extend(
                _rows(_equipment_context(project.inputs[key]), locale, key)
            )
    project_rows = cast(list[Json], result["rows"])
    if len(project_rows) > MAX_ROWS:
        result["rows"], result["truncated"] = project_rows[:MAX_ROWS], True
    remaining = MAX_ROWS - len(cast(list[Json], result["rows"]))
    choice = project.inputs.get("equipment_candidate")
    if isinstance(choice, dict):
        run_id, candidate_id = choice.get("run_id"), choice.get("candidate_id")
        if isinstance(run_id, str) and isinstance(candidate_id, str):
            selected_run = workspace.run(actor, run_id)
            if selected_run.project_id != project.id:
                raise InvalidInput("adopted assessment belongs to another project")
            selected = EquipmentCandidateStore(workspace).read(
                actor, run_id, candidate_id
            )
            if selected["assessment_sha256"] != choice.get("assessment_sha256"):
                raise InvalidInput("adopted assessment binding differs")
            rows = _rows(_equipment_context(selected["assessment"]), locale)
            result["adopted_equipment"] = {
                "run_id": run_id,
                "candidate_id": candidate_id,
                "assessment_sha256": selected["assessment_sha256"],
                "rows": rows[:remaining],
            }
            result["truncated"] = result["truncated"] or len(rows) > remaining
            remaining -= min(remaining, len(rows))
    runs: list[Json] = []
    for run_id in run_ids:
        run = workspace.run(actor, run_id)
        if run.project_id != project.id:
            raise InvalidInput("selected result belongs to a different project")
        rows = _result_rows(workspace, run, locale) if run.state == "succeeded" else []
        omitted = len(rows) > remaining
        selected_run_view: dict[str, Json] = {
            "id": run.id,
            "revision": run.revision,
            "state": run.state,
            "matches_view_revision": run.revision == project.revision,
            "is_current": run.is_current,
            "manifest_sha256": run.manifest_sha256,
            "result_sha256": run.result_sha256,
            "kind": run.result.get("kind") if run.result else None,
            "scope": {
                key: run.result.get(key)
                for key in (
                    "country_assessment",
                    "equipment_release",
                    "scenario_constraint_status",
                    "near_shading_assessment",
                )
            }
            if run.result
            else {},
            "rows": rows[: max(0, remaining)],
            "truncated": omitted,
            "details_available": bool(rows),
        }
        if (
            run.state == "succeeded"
            and run.result
            and run.result.get("kind") == "planning_report_v1"
        ):
            selected_run_view["calculation_sources"] = calculation_sources(
                workspace, run
            )
            materials = _report_materials(workspace, run, run.result)
            if materials is not None:
                selected_run_view["materials"] = materials
        runs.append(selected_run_view)
        remaining -= min(max(0, remaining), len(rows))
        if omitted:
            result["truncated"] = True
    result["runs"] = runs
    if len(encode(result)) > MAX_TEXT_BYTES:
        # Keep explicit provenance/status and refuse an oversized source, not a partial fact.
        raise InvalidInput("assistant context exceeds its presentation budget")
    return result
