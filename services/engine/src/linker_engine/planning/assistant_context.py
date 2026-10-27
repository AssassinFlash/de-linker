"""Read owned saved inputs and selected immutable results without running work.

This is a bounded presentation of the same records the workbench displays.
It never grants current product permission or substitutes a new calculation.
"""

from __future__ import annotations

from typing import cast

from .brief import PlanningBrief
from .canonical import Json, Object, encode
from .certificate_information import report_source_with_information
from .equipment_candidate_store import EquipmentCandidateStore
from .errors import InvalidInput
from .records import Actor, Run
from .report_copy import text
from .report_model import build_report, number
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
                result.append(
                    {"label": label, "value": number(ratio * 100, locale, "%")}
                )
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


def _result_rows(workspace: Workspace, run: Run, locale: str) -> list[Json]:
    result = run.result
    if result is None:
        return []
    kind = result.get("kind")
    if not isinstance(kind, str):
        raise InvalidInput("saved result kind is missing")
    if kind == "planning_report_v1":
        report = result.get("report")
        if not isinstance(report, dict):
            raise InvalidInput("saved report model is missing")
        if report.get("locale") != locale:
            # Localize only presentation of its frozen source; no kernel, source
            # refresh, PDF, job, or persistent artifact is produced by this read.
            dependencies = cast(Object, result.get("dependencies", {}))
            sha = dependencies.get("report_source")
            if not isinstance(sha, str):
                raise InvalidInput("saved report source is missing")
            source = report_source_with_information(workspace.blobs, dependencies)
            if (
                source.get("project_id") != run.project_id
                or source.get("revision") != run.revision
                or source.get("input_sha256") != run.manifest.get("input_sha256")
            ):
                raise InvalidInput("saved report source differs from selected result")
            report = cast(
                Object,
                build_report({**source, "locale": locale}).model_dump(mode="json"),
            )
        rows: list[Json] = []
        for section in cast(list[Object], report.get("sections", [])):
            if section.get("id") == "site":
                continue  # Exact location labels and private project notes are unnecessary.
            title = str(section.get("title", ""))
            # Comparison-side paragraphs contain the customer's free source note.
            paragraphs = (
                []
                if section.get("id") in {"comparison-baseline", "comparison-candidate"}
                else section.get("paragraphs", [])
            )
            for paragraph in cast(list[str], paragraphs):
                rows.append({"label": title, "value": paragraph})
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
                # Original report text is history; current document access is separate.
                rows.append(
                    {"label": f"{title}: {row['label']}", "value": row["value"]}
                )
            table = section.get("table")
            if isinstance(table, dict):
                columns = cast(list[str], table["columns"])
                for cells in cast(list[list[str]], table["rows"]):
                    rows.append(
                        {
                            "label": title,
                            "value": dict(zip(columns, cells, strict=True)),
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
        return _rows(result.get("search"), locale)
    assessment = result.get("assessment")
    if isinstance(assessment, dict):
        # The assessment is a saved observation, not current recommendation permission.
        return _rows(assessment, locale)
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
                _rows(project.inputs[key], locale, key)
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
            rows = _rows(selected["assessment"], locale)
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
        runs.append(
            {
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
        )
        remaining -= min(max(0, remaining), len(rows))
        if omitted:
            result["truncated"] = True
    result["runs"] = runs
    if len(encode(result)) > MAX_TEXT_BYTES:
        # Keep explicit provenance/status and refuse an oversized source, not a partial fact.
        raise InvalidInput("assistant context exceeds its presentation budget")
    return result
