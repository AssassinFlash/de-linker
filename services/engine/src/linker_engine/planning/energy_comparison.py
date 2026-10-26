"""Compare original owned results; never simulate or renew product authority.

Common AC metrics can compare the two supported coupling models. PV utilization
and generation keep their original AC/DC boundaries. Deltas require matching
external conditions and a satisfied scenario on each side, not a product release.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from .canonical import Json, Object, digest, encode
from .dc_plant_inputs import DcPlantEnergyInputs
from .energy_inputs import EnergyInputs
from .errors import InvalidInput, NotFound, VersionUnavailable
from .plant_energy_inputs import PlantEnergyInputs
from .records import Actor, Run
from .workspace import Workspace

MODEL = "frozen_energy_comparison_v1"
KINDS = {
    "single_ac_energy_replay_v1",
    "shared_dc_energy_replay_v1",
    "plant_ac_energy_replay_v1",
    "plant_shared_dc_energy_replay_v1",
}
# Admission/read/presentation modules do not calculate these frozen results.
# All other source files, dependencies and interpreter bindings stay included;
# adding an unknown module cannot silently exempt it from the comparison.
_NON_NUMERICAL = {
    "energy_comparison.py",
    "comparison_report.py",
    "http_app.py",
    "http_documents.py",
    "http_views.py",
    "http_index.py",
    "http_replay.py",
    "report_copy.py",
    "report_inputs.py",
    "report_kernel.py",
    "report_model.py",
    "report_pv_components.py",
    "report_sources.py",
}


@dataclass(frozen=True)
class EnergyComparisonSide:
    run: Run
    result: Object
    inputs: Object
    scenario: EnergyInputs | PlantEnergyInputs | DcPlantEnergyInputs

    @property
    def dc(self) -> bool:
        return self.scenario.coupling == "shared_dc"

    @property
    def joint(self) -> bool:
        return isinstance(self.scenario, (PlantEnergyInputs, DcPlantEnergyInputs))

    def inventory_key(self) -> Json:
        if isinstance(self.scenario, (PlantEnergyInputs, DcPlantEnergyInputs)):
            return {
                u.unit_id: u.initial_inventory.energy().document()
                for u in self.scenario.units
            }
        return self.scenario.initial_inventory.energy().document()

    def terminal_key(self) -> Json:
        if isinstance(self.scenario, (PlantEnergyInputs, DcPlantEnergyInputs)):
            return {u.unit_id: u.terminal_min_kwh for u in self.scenario.units}
        return self.scenario.terminal_min_kwh

    def temperature_key(self) -> Json:
        if self.joint:
            sources = _object(self.result.get("parameter_sources"))
            pool = _object(sources.get("pool"))
            return {
                str(u["unit_id"]): _object(
                    _object(pool.get(str(u["parameter_sha256"]))).get("loss_scenario")
                ).get("battery_temperature_c")
                for u in cast(list[Object], sources["units"])
            }
        if self.dc:
            return _object(
                _object(self.result.get("prepared_dc_parameters")).get("loss_scenario")
            ).get("battery_temperature_c")
        return None

    def capacity_key(self) -> Json:
        def basis(proof: Object) -> Json:
            assumption = _object(proof.get("source_facts")).get(
                "capacity_window_assumption"
            )
            return assumption if isinstance(assumption, dict) else None

        if self.joint:
            sources = _object(self.result.get("parameter_sources"))
            pool = _object(sources.get("pool"))
            return {
                str(unit["unit_id"]): basis(
                    _object(pool.get(str(unit["parameter_sha256"])))
                )
                for unit in cast(list[Object], sources["units"])
            }
        return (
            basis(_object(self.result.get("prepared_dc_parameters")))
            if self.dc
            else None
        )

    @property
    def metrics(self) -> Object:
        return cast(Object, self.result["metrics"])

    @property
    def pinned(self) -> Object:
        return cast(Object, self.result["pinned_assets"])

    def storage_unit_references(self) -> list[Json]:
        if not isinstance(self.scenario, (PlantEnergyInputs, DcPlantEnergyInputs)):
            return []
        plant = _object(_object(self.result.get("equipment_binding")).get("plant"))
        names = {
            str(u["id"]): str(u["name"]) for u in cast(list[Object], plant["units"])
        }
        return [
            {
                "unit_id": u.unit_id,
                "name": names[u.unit_id],
                "starting_energy_kwh": u.initial_inventory.energy().total,
                "starting_inventory": u.initial_inventory.energy().document(),
                "reserve_kwh": u.reserve_kwh,
                "terminal_min_kwh": u.terminal_min_kwh,
            }
            for u in self.scenario.units
        ]

    def reference(self) -> Object:
        source_note: Json
        if self.joint:
            sources = _object(self.result.get("parameter_sources"))
            notes = [
                _object(u.get("provenance")).get("label")
                for u in cast(list[Object], sources["units"])
            ]
            if any(not isinstance(n, str) or not n for n in notes):
                raise VersionUnavailable(
                    "retained per-unit storage assumptions required"
                )
            source_note = " · ".join(dict.fromkeys(cast(list[str], notes)))
        else:
            metadata = _object(self.result.get("battery_parameter_provenance"))
            source_note = _object(metadata.get("provenance")).get("label")
            if not isinstance(source_note, str):
                raise VersionUnavailable("retained storage assumption label required")
        brief = self.inputs.get("brief")
        site = brief.get("site") if isinstance(brief, dict) else None
        binding = self.result.get("equipment_binding")
        assessment = binding.get("assessment") if isinstance(binding, dict) else None
        selection = binding.get("selection", {}) if isinstance(binding, dict) else {}
        selected = (
            assessment.get("selected_products", [])
            if isinstance(assessment, dict)
            else []
        )
        return {
            "run_id": self.run.id,
            "revision": self.run.revision,
            "manifest_sha256": self.run.manifest_sha256,
            "result_sha256": self.run.result_sha256,
            "input_sha256": self.result["input_sha256"],
            "runtime_sha256": self.result["runtime_sha256"],
            "coupling": self.scenario.coupling,
            "scenario_constraint_status": self.result["scenario_constraint_status"],
            "equipment_status": assessment.get("overall_status")
            if isinstance(assessment, dict)
            else None,
            "equipment_models": [
                " ".join(str(p.get(k, "")) for k in ("brand", "model")).strip()
                for p in cast(list[Object], selected)
            ],
            "usable_window_kwh": math.fsum(
                float(cast(float, u["usable_window_kwh"]))
                for u in cast(list[Object], self.metrics["units"])
            )
            if self.joint
            else _object(self.result.get("model"))["usable_window_kwh"],
            "modules_per_stack": selection.get("modules_per_stack")
            if isinstance(selection, dict)
            else None,
            "parallel_stacks": selection.get("parallel_stacks")
            if isinstance(selection, dict)
            else None,
            "source_note": source_note,
            **({"storage_units": self.storage_unit_references()} if self.joint else {}),
            "site": site,
            "operating_periods": _schedule(self, times_only=False),
            "starting_energy_kwh": math.fsum(
                u.initial_inventory.energy().total for u in self.scenario.units
            )
            if isinstance(self.scenario, (PlantEnergyInputs, DcPlantEnergyInputs))
            else self.scenario.initial_inventory.energy().total,
            "terminal_min_kwh": None
            if self.joint
            else cast(EnergyInputs, self.scenario).terminal_min_kwh,
        }


def comparison_side(
    workspace: Workspace, actor: Actor, project_id: str, run_id: str
) -> EnergyComparisonSide:
    run = workspace.run(actor, run_id)
    if run.project_id != project_id:
        raise NotFound("comparison result not found in this project")
    result = run.result
    if (
        run.state != "succeeded"
        or not isinstance(result, dict)
        or result.get("kind") not in KINDS
    ):
        raise InvalidInput("comparison requires two completed energy calculations")
    if (
        result.get("project_id") != project_id
        or result.get("revision") != run.revision
        or result.get("manifest_sha256") != run.manifest_sha256
        or result.get("input_sha256") != run.manifest.get("input_sha256")
        or digest(encode(result)) != run.result_sha256
    ):
        raise VersionUnavailable(
            "comparison result identity differs from its saved run"
        )
    inputs = workspace.pinned_inputs(run.manifest)
    scenario: EnergyInputs | PlantEnergyInputs | DcPlantEnergyInputs = (
        DcPlantEnergyInputs.from_project(inputs)
        if result["kind"] == "plant_shared_dc_energy_replay_v1"
        else PlantEnergyInputs.from_project(inputs)
        if result["kind"] == "plant_ac_energy_replay_v1"
        else EnergyInputs.from_project(inputs)
    )
    if (result["kind"] == "shared_dc_energy_replay_v1") != (
        scenario.coupling == "shared_dc"
    ):
        raise VersionUnavailable("comparison coupling differs from its saved result")
    context = _object(run.manifest.get("context"))
    models = _object(context.get("models"))
    expected_battery = (
        "distinct_woo_shared_dc_ports_v1"
        if isinstance(scenario, DcPlantEnergyInputs)
        else "distinct_woo_battery_only_ac_equivalents_v1"
        if isinstance(scenario, PlantEnergyInputs)
        else "constant_window_shared_dc_bus_v1"
        if scenario.coupling == "shared_dc"
        else "constant_window_single_ac_bus_v1"
    )
    if (
        models.get("replay") != result["kind"]
        or models.get("battery") != expected_battery
        or _object(result.get("model")).get("version") != expected_battery
        or result.get("runtime_sha256") != context.get("code_sha256")
    ):
        raise VersionUnavailable("saved comparison model is unsupported or mismatched")
    return EnergyComparisonSide(run, result, inputs, scenario)


def _object(value: Json | None) -> Object:
    if not isinstance(value, dict):
        raise VersionUnavailable("comparison source document is unavailable")
    return value


def numerical_key(workspace: Workspace, side: EnergyComparisonSide) -> str:
    bundle = workspace.blobs.object(str(side.pinned["runtime_bundle"]))
    files = bundle.get("files")
    if not isinstance(files, list):
        raise VersionUnavailable("retained calculation source inventory required")
    source: list[Json] = []
    for raw in files:
        item = _object(raw)
        path, sha = item.get("path"), item.get("sha256")
        if not isinstance(path, str) or not isinstance(sha, str):
            raise VersionUnavailable("retained calculation source binding required")
        if (
            path.startswith("src/linker_engine/planning/")
            and path.removeprefix("src/linker_engine/planning/") in _NON_NUMERICAL
        ):
            continue
        source.append({"path": path, "sha256": sha})
    parameters = _object(_object(side.run.manifest.get("context")).get("parameters"))
    return digest(
        encode(
            {
                **{k: v for k, v in bundle.items() if k != "files"},
                "files": source,
                "policy": "retained_source_except_presentation_rpc_v1",
                "parameters": {
                    k: v
                    for k, v in parameters.items()
                    if k not in {"kind", "max_intervals"}
                },
            }
        )
    )


def _profile_key(side: EnergyComparisonSide, role: str) -> Json:
    return {
        key: side.pinned.get(f"{role}.{key}") for key in ("raw", "metadata", "timezone")
    }


def _weather_key(workspace: Workspace, side: EnergyComparisonSide) -> Json:
    if isinstance(side.scenario, DcPlantEnergyInputs):
        weather: Object = {}
        opaque = False
        for role in ("pv_reference", "pv_available_ac"):
            if role + ".metadata" not in side.pinned:
                continue
            metadata = workspace.blobs.object(str(side.pinned[role + ".metadata"]))
            dependencies = metadata.get("dependencies")
            if metadata.get(
                "profile_type"
            ) == "pvlib_reference_profile_v1" and isinstance(dependencies, dict):
                model = workspace.blobs.object(str(dependencies["pv_model_inputs"]))
                weather[role] = {
                    "retained_weather_sha256": digest(encode(model["weather"]))
                }
            else:
                weather[role] = _profile_key(side, role)
                opaque = True
        return {
            "plant_weather_sources": weather,
            **({"opaque": True} if opaque else {}),
        }
    role = "pv_available_dc" if side.dc else "pv_available_ac"
    metadata = workspace.blobs.object(str(side.pinned[f"{role}.metadata"]))
    dependencies = metadata.get("dependencies")
    if metadata.get("profile_type") == "pvlib_reference_profile_v1" and isinstance(
        dependencies, dict
    ):
        model = workspace.blobs.object(str(dependencies["pv_model_inputs"]))
        return {"retained_weather_sha256": digest(encode(model["weather"]))}
    # Identical original profile bytes/interpretation provide a common input
    # even for measured CSVs. Different opaque profiles prove no common climate.
    return {"profile": _profile_key(side, role), "opaque": True}


def _schedule(side: EnergyComparisonSide, *, times_only: bool) -> Json:
    rows: list[Json] = []
    for period in side.scenario.schedule:
        row = period.model_dump(mode="json")
        for key in ("start_utc", "end_utc"):
            row[key] = datetime.fromisoformat(row[key]).astimezone(UTC).isoformat()
        rows.append(
            {
                k: v
                for k, v in row.items()
                if not times_only or k in ("start_utc", "end_utc")
            }
        )
    return rows


def _operation_key(side: EnergyComparisonSide) -> Json:
    periods = _schedule(side, times_only=False)
    if isinstance(side.scenario, (PlantEnergyInputs, DcPlantEnergyInputs)):
        return {
            "periods": periods,
            "unit_reserves_kwh": {
                u.unit_id: u.reserve_kwh for u in side.scenario.units
            },
            **(
                {
                    "unit_dc_operation": {
                        u.unit_id: {
                            "aux_dc_kw": u.aux_dc_kw,
                            "allow_ac_charge": u.allow_ac_charge,
                        }
                        for u in side.scenario.units
                    }
                }
                if isinstance(side.scenario, DcPlantEnergyInputs)
                else {}
            ),
        }
    return periods


def _resolution(side: EnergyComparisonSide) -> Json:
    periods = _object(side.result.get("profile_interpretation")).get(
        "operating_periods"
    )
    if not isinstance(periods, list):
        raise VersionUnavailable("saved comparison time interpretation unavailable")
    return [
        {
            ("pv" if role in {"pv_available_ac", "pv_available_dc"} else role): {
                key: profile.get(key)
                for key in ("effective_max_interval_seconds", "reconstructed_means")
            }
            for role, profile in _object(_object(period).get("profiles")).items()
            if isinstance(profile, dict)
        }
        for period in periods
    ]


def compare_energy_runs(
    workspace: Workspace,
    actor: Actor,
    project_id: str,
    baseline_id: str,
    candidate_id: str,
) -> Object:
    workspace.get(actor, project_id)
    if baseline_id == candidate_id:
        raise InvalidInput("choose two different saved calculations")
    a = comparison_side(workspace, actor, project_id, baseline_id)
    b = comparison_side(workspace, actor, project_id, candidate_id)
    checks: list[Json] = []

    def check(identity: str, left: Json, right: Json, *, known: bool = True) -> None:
        checks.append(
            {
                "id": identity,
                "status": "unavailable"
                if not known
                else "matched"
                if left == right
                else "different",
            }
        )

    briefs = [side.inputs.get("brief") for side in (a, b)]
    sites = [brief.get("site") if isinstance(brief, dict) else None for brief in briefs]
    check(
        "site",
        *[
            {
                k: site.get(k)
                for k in ("country_code", "latitude", "longitude", "timezone")
            }
            if isinstance(site, dict)
            else None
            for site in sites
        ],
        known=all(
            isinstance(site, dict)
            and site.get("country_code") is not None
            and site.get("timezone") is not None
            for site in sites
        ),
    )
    check("periods", _schedule(a, times_only=True), _schedule(b, times_only=True))
    check(
        "demand_sources",
        *[
            {
                role: _profile_key(side, role)
                for role in ("gross_load", "critical_load", "aux_ac")
            }
            for side in (a, b)
        ],
    )
    weather_a, weather_b = _weather_key(workspace, a), _weather_key(workspace, b)
    weather_known = weather_a == weather_b or (
        "opaque" not in _object(weather_a) and "opaque" not in _object(weather_b)
    )
    check("pv_weather", weather_a, weather_b, known=weather_known)
    check("time_resolution", _resolution(a), _resolution(b))
    check(
        "operating_requirements",
        _operation_key(a),
        _operation_key(b),
    )
    check(
        "starting_inventory",
        a.inventory_key(),
        b.inventory_key(),
    )
    check("terminal_requirement", a.terminal_key(), b.terminal_key())
    check(
        "load_scope",
        a.metrics.get("load_measurement_scope"),
        b.metrics.get("load_measurement_scope"),
    )
    methods = [numerical_key(workspace, side) for side in (a, b)]
    check("calculation_method", *methods)
    check(
        "scenario_constraints",
        a.result.get("scenario_constraint_status") == "satisfied",
        b.result.get("scenario_constraint_status") == "satisfied",
        known=a.result.get("scenario_constraint_status")
        == b.result.get("scenario_constraint_status")
        == "satisfied",
    )
    check("battery_temperature", a.temperature_key(), b.temperature_key())
    aligned = all(_object(item)["status"] == "matched" for item in checks)
    rows: list[Json] = []

    def metric(
        identity: str,
        field_a: str,
        field_b: str,
        *,
        boundary_a: str = "ac",
        boundary_b: str = "ac",
        ratio: bool = False,
    ) -> None:
        left, right = a.metrics.get(field_a), b.metrics.get(field_b)
        reasons: list[Json] = [None, None]
        if ratio:
            reasons = [
                _object(value).get("undefined_reason") for value in (left, right)
            ]
            left, right = (_object(value).get("value") for value in (left, right))
        if identity == "stored_final":
            left, right = (
                math.fsum(
                    cast(float, _object(value)[key])
                    for key in ("pv_kwh", "grid_kwh", "initial_unknown_kwh")
                )
                for value in (left, right)
            )
        for value in (left, right):
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(cast(float, value))
            ):
                raise VersionUnavailable("finite saved comparison metric required")
        same_definition = boundary_a == boundary_b
        reason = (
            "undefined_metric"
            if left is None or right is None
            else "measurement_boundaries_differ"
            if not same_definition
            else "conditions_differ"
            if not aligned
            else None
        )
        delta = (
            (cast(float, right) - cast(float, left)) * (100 if ratio else 1)
            if reason is None
            else None
        )
        if delta is not None and not math.isfinite(delta):
            raise VersionUnavailable("comparison difference exceeds finite domain")
        rows.append(
            {
                "id": identity,
                "unit": "%" if ratio else "kWh",
                "delta_unit": "pp" if ratio else "kWh",
                "baseline": left,
                "candidate": right,
                "baseline_boundary": boundary_a,
                "candidate_boundary": boundary_b,
                "baseline_undefined_reason": reasons[0],
                "candidate_undefined_reason": reasons[1],
                "delta": delta,
                "delta_reason": reason,
            }
        )

    for identity, key in (
        ("load_demand", "load_demand_kwh"),
        ("solar_supply", "solar_load_kwh"),
        ("grid_import", "grid_import_kwh"),
        ("unserved_load", "unserved_load_kwh"),
    ):
        metric(identity, key, key)
    metric(
        "pv_export",
        "pv_export_ac_kwh" if a.dc else "pv_export_kwh",
        "pv_export_ac_kwh" if b.dc else "pv_export_kwh",
    )
    metric(
        "stored_final",
        "stored_final",
        "stored_final",
        boundary_a="storage",
        boundary_b="storage",
    )
    metric(
        "pv_generation",
        "pv_generated_dc_kwh" if a.dc else "pv_generated_ac_kwh",
        "pv_generated_dc_kwh" if b.dc else "pv_generated_ac_kwh",
        boundary_a="dc" if a.dc else "ac",
        boundary_b="dc" if b.dc else "ac",
    )
    metric("solar_share", "solar_autarky", "solar_autarky", ratio=True)
    metric(
        "pv_use",
        "pv_input_self_use",
        "pv_input_self_use",
        ratio=True,
        boundary_a="dc" if a.dc else "ac",
        boundary_b="dc" if b.dc else "ac",
    )
    differences: list[Json] = [
        {"id": identity, "changed": left != right}
        for identity, left, right in (
            ("storage_parameters", a.result["model"], b.result["model"]),
            (
                "equipment_selection",
                a.inputs.get("equipment_plant")
                if a.joint
                else a.inputs.get("equipment_selection"),
                b.inputs.get("equipment_plant")
                if b.joint
                else b.inputs.get("equipment_selection"),
            ),
            (
                "pv_design",
                [
                    a.inputs.get("geometry"),
                    a.inputs.get("pv_generation"),
                    [
                        {"unit_id": u.unit_id, "pv_converter_id": u.pv_converter_id}
                        for u in a.scenario.units
                    ]
                    if isinstance(a.scenario, DcPlantEnergyInputs)
                    else None,
                ],
                [
                    b.inputs.get("geometry"),
                    b.inputs.get("pv_generation"),
                    [
                        {"unit_id": u.unit_id, "pv_converter_id": u.pv_converter_id}
                        for u in b.scenario.units
                    ]
                    if isinstance(b.scenario, DcPlantEnergyInputs)
                    else None,
                ],
            ),
            (
                "dc_auxiliary",
                {u.unit_id: u.aux_dc_kw for u in a.scenario.units}
                if isinstance(a.scenario, DcPlantEnergyInputs)
                else None
                if a.joint
                else cast(EnergyInputs, a.scenario).aux_dc_kw,
                {u.unit_id: u.aux_dc_kw for u in b.scenario.units}
                if isinstance(b.scenario, DcPlantEnergyInputs)
                else None
                if b.joint
                else cast(EnergyInputs, b.scenario).aux_dc_kw,
            ),
            ("capacity_basis", a.capacity_key(), b.capacity_key()),
        )
    ]
    return {
        "schema_version": 1,
        "model": MODEL,
        "project_id": project_id,
        "baseline": {**a.reference(), "numerical_basis_sha256": methods[0]},
        "candidate": {**b.reference(), "numerical_basis_sha256": methods[1]},
        "conditions_aligned": aligned,
        "conditions": checks,
        "differences": differences,
        "metrics": rows,
        "equipment_release": "not_established",
        "country_release": "not_assessed",
    }
