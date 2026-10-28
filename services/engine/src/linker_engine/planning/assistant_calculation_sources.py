"""Small, language-independent facts from the selected immutable report source."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from .canonical import Json, Object
from .errors import InvalidInput
from .records import Run
from .workspace import Workspace


def _object(value: Json) -> Object:
    return value if isinstance(value, dict) else {}


def _period(value: Object) -> Object | None:
    values = [value.get(key) for key in ("start_utc", "end_utc")]
    if all(item is None for item in values):
        return None
    try:
        instants = [datetime.fromisoformat(cast(str, item)) for item in values]
        if any(item.tzinfo is None for item in instants) or instants[0] >= instants[1]:
            raise ValueError
    except (TypeError, ValueError) as error:
        raise InvalidInput("the saved calculation period is invalid") from error
    return {
        key: instant.astimezone(UTC).isoformat()
        for key, instant in zip(("start_utc", "end_utc"), instants, strict=True)
    }


def _timezone(source: Object) -> Json:
    value = _object(_object(source.get("brief")).get("site")).get("timezone")
    return value if isinstance(value, str) else None


def calculation_sources(workspace: Workspace, run: Run) -> Object | None:
    """No live inputs, source acquisition, calculation, localization or blob writes."""
    result = run.result
    if not result or result.get("kind") != "planning_report_v1":
        return None
    sha = _object(result.get("dependencies")).get("report_source")
    if not isinstance(sha, str):
        return None  # Older stored reports may have no retained source bundle.
    source = workspace.blobs.object(sha)
    if (
        source.get("project_id") != run.project_id
        or source.get("revision") != run.revision
        or source.get("input_sha256") != run.manifest.get("input_sha256")
    ):
        raise InvalidInput("saved report source differs from selected result")
    groups: list[Json] = []
    timezone = _timezone(source)
    comparison = _object(source.get("comparison"))
    for key, tmy in (
        ("pvlib_references", True),
        ("geometric_pv_references", True),
        ("pvgis_roof_ac_references", False),
    ):
        references = source.get(key, [])
        if not isinstance(references, list):
            raise InvalidInput("saved calculation sources are invalid")
        for raw in references:
            if not isinstance(raw, dict):
                raise InvalidInput("saved calculation sources are invalid")
            reference = _object(raw)
            weather = (
                _object(_object(reference.get("weather_source")).get("details"))
                if key == "geometric_pv_references"
                else _object(reference.get("weather"))
            )
            request = _object(weather.get("request"))
            interpretation = _object(weather.get("interpretation"))
            typical_year = tmy and any(
                key in weather for key in ("request", "interpretation")
            )
            parameters = _object(reference.get("parameters"))
            used = reference.get("used_by", [])
            if not isinstance(used, list):
                raise InvalidInput("saved calculation source scope is invalid")
            converter = reference.get("converter_id")
            scope = (
                "whole_reference"
                if converter is None
                else "selected_dc_group"
                if isinstance(converter, str) and converter
                else None
            )
            uses: list[tuple[str, str | None, str | None]] = []
            for item in used:
                role = _object(item).get("comparison_role", "selected")
                if not isinstance(role, str) or role not in (
                    "selected",
                    "baseline",
                    "candidate",
                ):
                    raise InvalidInput("saved calculation source scope is invalid")
                binding = _object(item).get("binding")
                # PlantEnergyKernel.profile_bindings gives pv_reference the DC quantity.
                quantity = (
                    {
                        "pv_available_ac": "pv_available_ac",
                        "pv_available_dc": "pv_available_dc",
                        "pv_reference": "pv_available_dc",
                    }.get(binding)
                    if isinstance(binding, str)
                    else None
                )
                usage = (role, quantity, scope)
                if usage not in uses:
                    uses.append(usage)
            if not uses:
                uses.append(("selected", None, scope))
            for role, quantity, source_scope in uses:
                if role not in ("selected", "baseline", "candidate"):
                    raise InvalidInput("saved calculation source scope is invalid")
                groups.append(
                    {
                        "kind": "pv",
                        "role": role,
                        "input_quantity": quantity,
                        "source_scope": source_scope,
                        "timezone": timezone
                        if role == "selected"
                        else _object(_object(comparison.get(role)).get("site")).get(
                            "timezone"
                        ),
                        "radiation_database": weather.get("radiation_database")
                        if tmy
                        else parameters.get("radiation_database"),
                        "meteorological_database": weather.get("meteo_database")
                        if tmy
                        else None,
                        **(
                            {
                                "weather_selection_period": {
                                    "start_year": request["start_year"],
                                    "end_year": request["end_year"],
                                }
                                if "start_year" in request and "end_year" in request
                                else None,
                                "synthetic_calculation_year": interpretation.get(
                                    "synthetic_energy_year"
                                ),
                            }
                            if typical_year
                            else {}
                        ),
                        "periods_utc": [
                            _period(
                                _object(
                                    reference.get(
                                        "profile_summary", reference.get("summary")
                                    )
                                )
                            )
                        ],
                    }
                )
    if not groups and isinstance(source.get("pv"), dict):
        groups.append(
            {
                "kind": "pv",
                "role": "selected",
                "input_quantity": None,
                "source_scope": None,
                "timezone": timezone,
                "periods_utc": [
                    _period(_object(_object(source["pv"]).get("profile_summary")))
                ],
            }
        )
    scenario = _object(source.get("energy_scenario"))
    schedule = scenario.get("schedule")
    if isinstance(source.get("energy"), dict):
        groups.append(
            {
                "kind": "energy",
                "role": "selected",
                "timezone": timezone,
                "periods_utc": [_period(_object(item)) for item in schedule]
                if isinstance(schedule, list)
                else [],
            }
        )
    for role in ("baseline", "candidate"):
        side = _object(comparison.get(role))
        if not side:
            continue
        periods = side.get("operating_periods")
        groups.append(
            {
                "kind": "energy",
                "role": role,
                "timezone": _object(side.get("site")).get("timezone"),
                "periods_utc": [_period(_object(item)) for item in periods]
                if isinstance(periods, list)
                else [],
            }
        )
    return {"schema_version": 1, "groups": groups} if groups else None
