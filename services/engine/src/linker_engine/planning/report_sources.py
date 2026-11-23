"""Resolve owned report sources once, without recomputing their calculations."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

from .assets import Asset, Assets
from .canonical import Json, Object
from .certificate_evidence import certificate_documents
from .comparison_pv import is_known, roof_power
from .dc_energy_kernel import DcEnergyKernel
from .dc_plant_inputs import DcPlantEnergyInputs
from .dc_plant_kernel import DcPlantEnergyKernel
from .direct_beam_read import KIND as DIRECT_BEAM_KIND
from .direct_beam_read import direct_beam_bundle
from .energy_comparison import compare_energy_runs, comparison_side
from .energy_inputs import EnergyInputs, storage_only_project
from .energy_kernel import EnergyKernel
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_condition_inputs import validate_condition_inputs
from .equipment_declarations import (
    comparison_model_preferences,
    normalize_discovery_inputs,
    restore_comparison_models,
)
from .equipment_inputs import EquipmentSelection
from .equipment_kernel import EquipmentKernel
from .equipment_plant import EquipmentPlant, assert_plant_exclusivity
from .equipment_search_kernel import EquipmentSearchKernel
from .errors import (
    InvalidInput,
    ProductEvidenceChanged,
    ReportSourceExportRequired,
    VersionUnavailable,
)
from .existing_system import require_retained_inverter, unverified_retained_inverter
from .frozen_documents import FrozenDocuments
from .geometric_pv_inputs import KIND as GEOMETRIC_PV_KIND
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .geometric_pv_report import geometric_pv_reference
from .geometry import read_geometry
from .geometry_documents import GeometryDocument
from .installation_inputs import InstallationInputs
from .installation_takeoff import product_basis, route_takeoff
from .partial_equipment import partial_equipment
from .plant_energy_inputs import PlantEnergyInputs
from .plant_energy_kernel import PlantEnergyKernel
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .profile_demand_bounds import MODEL as PROFILE_BOUNDS_MODEL
from .profile_demand_bounds import peak_targets, periods
from .profile_selections import ProfileSelections
from .pv_preparation import PvReferenceKernel
from .pv_profile_preparation import PROFILE_PURPOSE as PVLIB_PURPOSE
from .pvgis_known_inputs import PROFILE_PURPOSE as KNOWN_AC_PURPOSE
from .pvgis_reference_kernel import PvgisRoofReferenceKernel
from .pvgis_reference_profile import PROFILE_PURPOSE as ROOF_AC_PURPOSE
from .pvgis_reference_profile import prepared_reference_profile, reference_bundle
from .records import Actor, Project, Run
from .report_inputs import ReportOptions
from .report_pv_components import pv_components, saved_roof_components
from .report_pvlib import pvlib_reference
from .workspace import Workspace


class ReportInputsChanged(InvalidInput):
    code = "report_inputs_changed"


class ReportWiringCheckRequired(ReportInputsChanged):
    code = "report_wiring_check_required"


def renew_module_permission(previous: Object, current: Object) -> Object:
    """Renew permission only when every frozen module fact and citation matches."""
    if previous.get("kind") == "project_panel_parameters" and current == previous:
        return previous
    if previous.get("schema_version") != 1 or not isinstance(
        previous.get("module"), dict
    ):
        raise VersionUnavailable("frozen Woo module proof is missing")
    if previous["module"] != current.get("module"):
        raise ProductEvidenceChanged("the frozen Woo module facts have changed")
    return current


def _declared_panels(inputs: Object, components: Object | None) -> Object | None:
    if (
        isinstance(components, dict) and components.get("status") == "available"
    ) or storage_only_project(inputs):
        return None
    setup = inputs.get("pvgis_reference_setup", inputs.get("pvgis_reference"))
    details = inputs.get("known_panel_details")
    if not is_known(setup) or not isinstance(details, dict):
        return None
    count, power = details.get("count"), details.get("power_w")
    if count is not None and (type(count) is not int or count <= 0):
        raise InvalidInput("the declared panel count must be a positive whole number")
    if power is not None and (
        type(power) not in (int, float) or cast(float, power) <= 0
    ):
        raise InvalidInput("the declared panel power must be positive")
    return (
        {"count": count, "stc_power_w": power}
        if count is not None or power is not None
        else None
    )


def report_sources(
    workspace: Workspace,
    products: ProductSources,
    actor: Actor,
    project: Project,
    options: ReportOptions,
) -> Object:
    declared_inputs = project.inputs
    if options.energy_run_id is not None:
        energy_run = workspace.run(actor, options.energy_run_id)
        if energy_run.project_id != project.id:
            raise InvalidInput("report analysis must belong to this project")
        context = energy_run.manifest.get("context")
        pinned = context.get("assets") if isinstance(context, dict) else None
        if isinstance(pinned, dict) and "resolved_inputs" in pinned:
            authored = workspace.get(
                actor, project.id, revision=energy_run.revision
            ).inputs
            authored_brief = authored.get("brief")
            current_brief = project.inputs.get("brief")
            authored_scope = (
                authored_brief.get("system_scope")
                if isinstance(authored_brief, dict)
                else None
            )
            current_scope = (
                current_brief.get("system_scope")
                if isinstance(current_brief, dict)
                else None
            )
            if authored_scope != current_scope or any(
                authored.get(field) != project.inputs.get(field)
                for field in (
                    "energy_scenario",
                    "energy_plant_setup",
                    "profile_selections",
                    "equipment_setup",
                    "equipment_selection",
                    "equipment_plant_setup",
                    "equipment_plant",
                )
            ):
                raise ReportInputsChanged(
                    "report energy declarations differ from the selected calculation"
                )
            resolved = workspace.pinned_inputs(energy_run.manifest)
            project = replace(
                project,
                inputs={
                    **project.inputs,
                    **{
                        field: resolved[field]
                        for field in (
                            "energy_replay",
                            "energy_plant",
                            "equipment_selection",
                            "equipment_plant",
                        )
                        if field in resolved
                    },
                },
            )
    retained_comparison: Object | None = None
    if options.equipment_run_id is not None:
        checked = workspace.run(actor, options.equipment_run_id)
        if checked.project_id != project.id:
            raise InvalidInput("report equipment check must belong to this project")
        if checked.result is not None and isinstance(
            checked.result.get("retained_inverter"), dict
        ):
            if (
                checked.manifest["input_sha256"] != project.input_sha256
                or unverified_retained_inverter(declared_inputs) is None
            ):
                raise ReportInputsChanged(
                    "the retained-inverter comparison differs from the saved project"
                )
            retained_comparison = cast(Object, checked.result["retained_inverter"])
        context = checked.manifest.get("context")
        pinned = context.get("assets") if isinstance(context, dict) else None
        if (
            retained_comparison is None
            and isinstance(pinned, dict)
            and "resolved_inputs" in pinned
        ):
            authored = workspace.get(
                actor, project.id, revision=checked.revision
            ).inputs
            authored_brief = authored.get("brief")
            current_brief = declared_inputs.get("brief")
            authored_scope = (
                authored_brief.get("system_scope")
                if isinstance(authored_brief, dict)
                else None
            )
            current_scope = (
                current_brief.get("system_scope")
                if isinstance(current_brief, dict)
                else None
            )
            if authored_scope != current_scope or any(
                authored.get(field) != declared_inputs.get(field)
                for field in (
                    "equipment_setup",
                    "equipment_selection",
                    "equipment_plant_setup",
                    "equipment_plant",
                )
            ):
                raise ReportInputsChanged(
                    "report hardware declarations differ from the selected check"
                )
            resolved = workspace.pinned_inputs(checked.manifest)
            project = replace(
                project,
                inputs={
                    **project.inputs,
                    **{
                        field: resolved[field]
                        for field in ("equipment_selection", "equipment_plant")
                        if field in resolved
                    },
                },
            )
    sources: list[Json] = []
    bases: dict[str, Json] = {}
    labels: list[str] = []
    roof_references: dict[str, Object] = {}
    known_references: dict[str, Object] = {}
    pvlib_references: dict[tuple[str, str | None], Object] = {}
    geometric_pv_references: dict[str, Object] = {}
    # One request resolves the same retained witness for the selected PV
    # reference, the energy profiles and the component list. Sharing the
    # reader keeps that to one verified parse per document.
    documents = FrozenDocuments(workspace.blobs)

    def require_profile_proof(asset: Asset) -> None:
        if not isinstance(asset.metadata.get("woo_module_inputs"), dict):
            raise InvalidInput(
                "prepare a PV profile from the current Woo-maintained module"
            )

    def geometric_reference(
        asset: Asset, run: Run, binding: str, *, comparison_role: str | None = None
    ) -> None:
        require_profile_proof(asset)
        reference = geometric_pv_references.setdefault(
            asset.metadata_sha256,
            {
                **geometric_pv_reference(
                    workspace.blobs,
                    asset.content_sha256,
                    asset.metadata,
                    documents,
                ),
                "asset_id": asset.id,
                "content_sha256": asset.content_sha256,
                "metadata_sha256": asset.metadata_sha256,
                "used_by": [],
            },
        )
        cast(list[Json], reference["used_by"]).append(
            {
                "run_id": run.id,
                "revision": run.revision,
                "binding": binding,
                **({"comparison_role": comparison_role} if comparison_role else {}),
            }
        )

    def weather_reference(
        asset: Asset,
        run: Run,
        binding: str,
        *,
        comparison_role: str | None = None,
        converter_id: str | None = None,
    ) -> None:
        require_profile_proof(asset)
        scope = (asset.metadata_sha256, converter_id)
        if scope not in pvlib_references:
            pvlib_references[scope] = {
                **pvlib_reference(
                    workspace.blobs,
                    asset.content_sha256,
                    asset.metadata,
                    converter_id=converter_id,
                ),
                "asset_id": asset.id,
                "content_sha256": asset.content_sha256,
                "metadata_sha256": asset.metadata_sha256,
                "used_by": [],
            }
        cast(list[Json], pvlib_references[scope]["used_by"]).append(
            {
                "run_id": run.id,
                "revision": run.revision,
                "binding": binding,
                **({"converter_id": converter_id} if converter_id is not None else {}),
                **({"comparison_role": comparison_role} if comparison_role else {}),
            }
        )

    def roof_reference(
        asset: Asset, run: Run, binding: str, *, comparison_role: str | None = None
    ) -> None:
        if asset.purpose == KNOWN_AC_PURPOSE:
            prepared_reference_profile(
                workspace.blobs, asset.content_sha256, asset.metadata, documents
            )
            bundle = reference_bundle(
                workspace.blobs, asset.content_sha256, asset.metadata, documents
            )
            reference = known_references.setdefault(
                asset.metadata_sha256,
                {
                    "asset_id": asset.id,
                    "content_sha256": asset.content_sha256,
                    "metadata_sha256": asset.metadata_sha256,
                    "parameters": bundle["parameters"],
                    "site": bundle["site"],
                    "profile_summary": asset.metadata["interpretation"],
                    "arrays": cast(Object, bundle["manifest"])["arrays"],
                    "dependencies": asset.metadata["dependencies"],
                    "basis": "customer_declared",
                    "used_by": [],
                },
            )
            cast(list[Json], reference["used_by"]).append(
                {
                    "run_id": run.id,
                    "revision": run.revision,
                    "binding": binding,
                    **({"comparison_role": comparison_role} if comparison_role else {}),
                }
            )
            return
        require_profile_proof(asset)
        # Read the retained output and its original proof, never a current
        # product snapshot or a second provider/model calculation. The report's
        # own reader is reused, so the manifest and children of this reference
        # are verified once for every section that reads it.
        prepared_reference_profile(
            workspace.blobs, asset.content_sha256, asset.metadata, documents
        )
        bundle = reference_bundle(
            workspace.blobs, asset.content_sha256, asset.metadata, documents
        )
        reference = roof_references.setdefault(
            asset.metadata_sha256,
            {
                "asset_id": asset.id,
                "content_sha256": asset.content_sha256,
                "metadata_sha256": asset.metadata_sha256,
                "parameters": bundle["parameters"],
                "profile_summary": asset.metadata["interpretation"],
                "arrays": cast(Object, bundle["manifest"])["arrays"],
                "geometry_sha256": asset.metadata["geometry_sha256"],
                "woo_module_inputs": bundle["woo_module_inputs"],
                "dependencies": asset.metadata["dependencies"],
                "pv_components": pv_components(
                    workspace.blobs,
                    asset.content_sha256,
                    asset.metadata,
                    documents=documents,
                ),
                "used_by": [],
            },
        )
        cast(list[Json], reference["used_by"]).append(
            {
                "run_id": run.id,
                "revision": run.revision,
                "binding": binding,
                **({"comparison_role": comparison_role} if comparison_role else {}),
            }
        )

    def provenance(metadata: Object) -> None:
        source = metadata.get("provenance")
        if isinstance(source, dict) and isinstance(source.get("label"), str):
            labels.append(cast(str, source["label"]))

    def _runtime_sha(run: Run) -> Json:
        if run.result is not None and "runtime_sha256" in run.result:
            return run.result["runtime_sha256"]
        context = run.manifest.get("context")
        return context.get("code_sha256") if isinstance(context, dict) else None

    def _pinned_assets(run: Run) -> Object:
        if run.result is not None and isinstance(run.result.get("pinned_assets"), dict):
            return cast(Object, run.result["pinned_assets"])
        context = run.manifest.get("context")
        assets = context.get("assets") if isinstance(context, dict) else None
        return assets if isinstance(assets, dict) else {}

    def owned(run_id: str, kind: str, fields: tuple[str, ...]) -> Run:
        run = workspace.run(actor, run_id)
        if (
            run.project_id != project.id
            or run.state != "succeeded"
            or run.result is None
        ):
            raise InvalidInput(
                "report analysis must be completed and belong to this project"
            )
        actual_kind = run.result.get("kind")
        if (
            actual_kind is None
            and kind == EquipmentKernel.kind
            and isinstance(run.result.get("assessment"), dict)
        ):
            actual_kind = EquipmentKernel.kind
        if actual_kind != kind:
            raise InvalidInput("report analysis has a different task kind")
        previous = workspace.pinned_inputs(run.manifest)
        if any(previous.get(field) != project.inputs.get(field) for field in fields):
            raise ReportInputsChanged(
                "report analysis does not match the saved project inputs"
            )
        sources.append(
            {
                "run_id": run.id,
                "revision": run.revision,
                "kind": kind,
                "manifest_sha256": run.manifest_sha256,
                "result_sha256": run.result_sha256,
                "input_sha256": run.manifest["input_sha256"],
                "runtime_sha256": _runtime_sha(run),
            }
        )
        return run

    assessment: Object | None = None
    peak_comparison: Object | None = None
    self_use_comparison: Object | None = None
    frozen_certificates: Object | None = None
    equipment_source_run: Run | None = None
    equipment_source_inputs: Object | None = None
    comparison_only = (
        not options.include_installation
        and options.comparison is not None
        and all(
            identity is None
            for identity in (
                options.direct_beam_run_id,
                options.energy_run_id,
                options.pv_run_id,
                options.equipment_run_id,
            )
        )
    )
    assert_plant_exclusivity(project.inputs)
    candidate = (
        None
        if comparison_only or retained_comparison is not None
        else project.inputs.get("equipment_candidate")
    )
    has_wiring = any(
        project.inputs.get(key) is not None
        for key in ("pv_string_plan", "pv_plant_string_plan")
    )
    if isinstance(candidate, dict) or (
        options.equipment_run_id is not None and retained_comparison is None
    ):
        require_retained_inverter(project.inputs, selection=True)
    use_wiring_check = False
    if isinstance(candidate, dict):
        separate_equipment = options.equipment_run_id not in (
            None,
            candidate.get("run_id"),
        )
        if separate_equipment and not has_wiring:
            raise InvalidInput(
                "report equipment differs from the adopted project candidate"
            )
        use_wiring_check = separate_equipment
        # Validate the historical choice here; the common report boundary
        # confirms current permission for every distinct proof once below.
        check_equipment_candidate(
            workspace, actor, project.id, project.inputs, previous=project.inputs
        )
        run = workspace.run(actor, cast(str, candidate["run_id"]))
        assert run.result is not None
        searched = normalize_discovery_inputs(workspace.pinned_inputs(run.manifest))
        current = restore_comparison_models(
            normalize_discovery_inputs(declared_inputs), searched
        )
        previous_brief, current_brief = searched.get("brief"), current.get("brief")
        if use_wiring_check and searched.get("geometry") != current.get("geometry"):
            prepared = run.result.get("prepared_asset")
            if (
                isinstance(prepared, dict)
                and prepared.get("purpose") == ROOF_AC_PURPOSE
            ):
                raise ReportInputsChanged(
                    "report roof differs from the comparison PV reference"
                )
            context = cast(Object, run.manifest["context"])
            if (
                run.result.get("pv_capacity_basis") != "declared_hardware"
                and "resolved_inputs" in _pinned_assets(run)
                and "pvgis_execution_keys" in cast(Object, context["parameters"])
                and isinstance(previous_brief, dict)
                and previous_brief.get("system_scope") in ("new_pv_storage", "pv_only")
                and not is_known(
                    searched.get(
                        "pvgis_reference_setup", searched.get("pvgis_reference")
                    )
                )
                and roof_power(searched) != roof_power(current)
            ):
                raise ReportInputsChanged(
                    "report roof capacity differs from the equipment comparison"
                )
        if (
            any(
                (
                    previous_brief.get(field)
                    if isinstance(previous_brief, dict)
                    else None
                )
                != (
                    current_brief.get(field)
                    if isinstance(current_brief, dict)
                    else None
                )
                for field in ("system_scope", "project_use", "site")
            )
            or any(
                searched.get(field) != current.get(field)
                for field in (
                    "backup_demand",
                    "existing_system",
                    "energy_scenario",
                    "energy_plant_setup",
                    "profile_selections",
                    "equipment_demand",
                    "pvgis_reference_setup",
                    "pvgis_reference",
                    *(("geometry",) if not use_wiring_check else ()),
                    "pv_generation",
                    "pv_preparation",
                    "geometric_pv_preparation",
                )
            )
            or comparison_model_preferences(searched)
            != comparison_model_preferences(current)
        ):
            raise ReportInputsChanged(
                "report demand differs from the selected candidate"
            )
        equipment_source_run = run
        equipment_source_inputs = workspace.pinned_inputs(run.manifest)
        detail = EquipmentCandidateStore(workspace).read(
            actor, run.id, cast(str, candidate["candidate_id"])
        )
        assessment = cast(Object, detail["assessment"])
        search = cast(Object, run.result["search"])
        summary = search.get("demand")
        if isinstance(summary, dict) and summary.get("model") == PROFILE_BOUNDS_MODEL:
            selected_option = next(
                item
                for item in cast(list[Object], search["candidates"])
                if item["id"] == candidate["candidate_id"]
            )
            bounds = cast(Object, selected_option["demand"])
            baseline = cast(Object, summary["baseline"])
            if summary.get("controller") == "self_consumption_with_reserve_v1":
                self_use_comparison = {
                    "horizon_start_utc": summary["horizon_start_utc"],
                    "horizon_end_utc": summary["horizon_end_utc"],
                    "baseline": baseline,
                    "upper_kwh": bounds["additional_pv_use_upper_kwh"],
                }
            elif summary.get("controller") == "peak_shaving_with_reserve_v1":
                # Older comparisons may have only a scalar, or null for varying caps.
                targets = summary
                if (
                    targets.get("peak_target_kw") is None
                    and "peak_target_periods" not in targets
                ):
                    targets = peak_targets(periods(equipment_source_inputs))
                peak_comparison = {
                    "target_kw": targets.get("peak_target_kw"),
                    "target_periods": targets.get("peak_target_periods", []),
                    "baseline_kw": baseline["peak_grid_import_kw"],
                    "lower_bound_kw": bounds["peak_import_lower_bound_kw"],
                    "status": bounds["status"],
                }
        sources.append(
            {
                "run_id": run.id,
                "revision": run.revision,
                "kind": run.result["kind"],
                "candidate_id": candidate["candidate_id"],
                "assessment_sha256": candidate["assessment_sha256"],
                "manifest_sha256": run.manifest_sha256,
                "result_sha256": run.result_sha256,
                "input_sha256": run.manifest["input_sha256"],
                "runtime_sha256": _runtime_sha(run),
            }
        )
        pinned = _pinned_assets(run)
        if "pv_available_ac.raw" in pinned:
            profiles = ProfileSelections.read(
                project.inputs.get("profile_selections")
            ).selected
            asset = Assets(workspace).get(
                actor, project.id, profiles["pv_available_ac"]
            )
            try:
                bindings = profile_dependencies(
                    asset, "pv_available_ac", project.inputs, workspace.blobs
                )
            except InvalidInput as error:
                raise ReportInputsChanged(
                    "report candidate PV source differs from the saved project"
                ) from error
            if any(pinned.get(name) != sha for name, sha in bindings.items()):
                raise ReportInputsChanged(
                    "report candidate PV source dependencies have changed"
                )
        bases["comparison_equipment.adopted" if use_wiring_check else "equipment"] = (
            pinned["woo.equipment_inputs"]
        )
    if retained_comparison is not None and options.equipment_run_id is not None:
        run = owned(options.equipment_run_id, EquipmentSearchKernel.kind, ())
        for role in ("gross_load", "pv_available_ac"):
            name = f"{role}.metadata"
            sha = _pinned_assets(run).get(name)
            if isinstance(sha, str):
                metadata = workspace.blobs.object(sha)
                provenance(metadata)
                module_basis = metadata.get("woo_module_inputs")
                if isinstance(module_basis, dict):
                    bases[f"energy.{name}"] = workspace.blobs.put_object(module_basis)
                equipment_basis = metadata.get("woo_equipment_inputs")
                if isinstance(equipment_basis, dict):
                    bases["energy_equipment"] = workspace.blobs.put_object(
                        equipment_basis
                    )
    elif options.equipment_run_id is not None and (
        not isinstance(candidate, dict) or use_wiring_check
    ):
        run = owned(options.equipment_run_id, EquipmentKernel.kind, ("backup_demand",))
        previous = workspace.pinned_inputs(run.manifest)
        equipment_source_run = run
        equipment_source_inputs = previous
        if "equipment_plant" in previous or "equipment_plant" in project.inputs:
            matches = EquipmentPlant.from_inputs(
                previous
            ) == EquipmentPlant.from_inputs(project.inputs)
        else:
            matches = EquipmentSelection.read(
                previous.get("equipment_selection")
            ) == EquipmentSelection.read(project.inputs.get("equipment_selection"))
        if not matches:
            raise InvalidInput(
                "report equipment does not match the saved project selection"
            )
        assert run.result is not None
        assessment = cast(Object, run.result["assessment"])
        recorded_certificates = run.result.get("certificates")
        if isinstance(recorded_certificates, dict):
            frozen_certificates = recorded_certificates
        pinned = _pinned_assets(run)
        bases["equipment"] = pinned["woo.equipment_inputs"]

    component_list: Object | None = None
    energy: Object | None = None
    if options.energy_run_id is not None:
        joint = "energy_plant" in project.inputs
        raw_plant = project.inputs.get("energy_plant")
        joint_dc = (
            isinstance(raw_plant, dict)
            and raw_plant.get("coupling") == "plant_shared_dc"
        )
        scenario: EnergyInputs | PlantEnergyInputs | DcPlantEnergyInputs = (
            DcPlantEnergyInputs.from_project(project.inputs)
            if joint_dc
            else PlantEnergyInputs.from_project(project.inputs)
            if joint
            else EnergyInputs.from_project(project.inputs)
        )
        run = owned(
            options.energy_run_id,
            DcPlantEnergyKernel.kind
            if joint_dc
            else PlantEnergyKernel.kind
            if joint
            else DcEnergyKernel.kind
            if scenario.coupling == "shared_dc"
            else EnergyKernel.kind,
            ("energy_plant", "equipment_plant") if joint else ("energy_replay",),
        )
        energy = run.result
        assert energy is not None
        binding = energy.get("equipment_binding")
        if isinstance(binding, dict):
            if joint:
                if EquipmentPlant.read(
                    binding.get("plant")
                ) != EquipmentPlant.from_inputs(project.inputs):
                    raise ReportInputsChanged(
                        "report energy result belongs to another prepared plant"
                    )
            elif EquipmentSelection.read(
                binding.get("selection")
            ) != EquipmentSelection.read(project.inputs.get("equipment_selection")):
                raise ReportInputsChanged(
                    "report energy result belongs to a different equipment selection"
                )
        pinned_energy = cast(Object, energy["pinned_assets"])
        if isinstance(binding, dict):
            bases["energy_equipment"] = pinned_energy["woo.equipment_inputs"]
            if assessment is None:
                bound_assessment = binding.get("assessment")
                if not isinstance(bound_assessment, dict):
                    raise VersionUnavailable(
                        "the energy equipment assessment is missing"
                    )
                # The selected run already froze these quantities and its Woo
                # proof. Do not require another equipment calculation or read
                # a newer product snapshot to fill the report and handoff.
                assessment = bound_assessment
                bases["equipment"] = pinned_energy["woo.equipment_inputs"]
                equipment_source_run = run
                equipment_source_inputs = workspace.pinned_inputs(run.manifest)
        energy_profiles = (
            PlantEnergyKernel.profile_bindings(scenario)
            if isinstance(scenario, (PlantEnergyInputs, DcPlantEnergyInputs))
            else {
                role: (role, asset_id) for role, asset_id in scenario.profiles().items()
            }
        )
        for role, (measurement, asset_id) in energy_profiles.items():
            asset = Assets(workspace).get(actor, project.id, asset_id)
            try:
                profile_bindings = profile_dependencies(
                    asset, measurement, project.inputs, workspace.blobs, binding=role
                )
            except InvalidInput as error:
                raise ReportInputsChanged(
                    "report energy source does not match the saved project inputs"
                ) from error
            if any(
                pinned_energy.get(name) != sha for name, sha in profile_bindings.items()
            ):
                raise ReportInputsChanged(
                    "report energy source dependencies have changed"
                )
            if asset.purpose == GEOMETRIC_PV_PURPOSE:
                geometric_reference(asset, run, role)
            elif asset.purpose in (ROOF_AC_PURPOSE, KNOWN_AC_PURPOSE):
                roof_reference(asset, run, role)
                component_list = pv_components(
                    workspace.blobs,
                    asset.content_sha256,
                    asset.metadata,
                    documents=documents,
                )
            elif asset.purpose == PVLIB_PURPOSE:
                weather_reference(
                    asset,
                    run,
                    role,
                    converter_id=scenario.pv_converter_id
                    if measurement == "pv_available_dc"
                    and isinstance(scenario, EnergyInputs)
                    else None,
                )
        for name, sha in cast(Object, energy["pinned_assets"]).items():
            if name.endswith(".metadata") and isinstance(sha, str):
                metadata = workspace.blobs.object(sha)
                provenance(metadata)
                if name in {
                    "pv_available_ac.metadata",
                    "pv_available_dc.metadata",
                    "pv_reference.metadata",
                }:
                    raw_sha = pinned_energy.get(name.replace(".metadata", ".raw"))
                    if not isinstance(raw_sha, str):
                        raise VersionUnavailable(
                            "the saved PV profile raw source is missing"
                        )
                    component_list = pv_components(
                        workspace.blobs,
                        raw_sha,
                        metadata,
                        converter_id=scenario.pv_converter_id
                        if name == "pv_available_dc.metadata"
                        and isinstance(scenario, EnergyInputs)
                        else None,
                        documents=documents,
                    )
                module_basis = metadata.get("woo_module_inputs")
                if isinstance(module_basis, dict):
                    bases[f"energy.{name}"] = workspace.blobs.put_object(module_basis)

    pv: Object | None = None
    if options.pv_run_id is not None:
        selected_run = workspace.run(actor, options.pv_run_id)
        result = selected_run.result or {}
        prepared = result.get("prepared_asset")
        purpose = prepared.get("purpose") if isinstance(prepared, dict) else None
        pv_choice = project.inputs.get("equipment_candidate")
        comparison_pv = (
            result.get("kind") == EquipmentSearchKernel.kind
            and isinstance(pv_choice, dict)
            and pv_choice.get("run_id") == selected_run.id
            and purpose in (ROOF_AC_PURPOSE, KNOWN_AC_PURPOSE)
        )
        roof_ac = result.get("kind") == PvgisRoofReferenceKernel.kind or comparison_pv
        geometric = (
            selected_run.result is not None
            and selected_run.result.get("kind") == GEOMETRIC_PV_KIND
        )
        series_iv = (
            geometric
            and selected_run.result is not None
            and selected_run.result.get("model")
            == "opaque_perez_series_iv_forward_reference_v1"
        )
        run = owned(
            options.pv_run_id,
            GEOMETRIC_PV_KIND
            if geometric
            else EquipmentSearchKernel.kind
            if comparison_pv
            else PvgisRoofReferenceKernel.kind
            if roof_ac
            else PvReferenceKernel.kind,
            (
                "geometry",
                "geometric_pv_preparation",
                "weather_acquisition",
                *(
                    (
                        "equipment_selection",
                        "pv_string_plan",
                        "equipment_plant",
                        "pv_plant_string_plan",
                    )
                    if series_iv
                    else ()
                ),
            )
            if geometric
            else ("pvgis_reference",)
            if roof_ac and purpose == KNOWN_AC_PURPOSE
            else ("geometry", "pvgis_reference")
            if roof_ac
            else ("geometry", "pv_generation", "pv_preparation", "weather_acquisition"),
        )
        pv = run.result
        assert pv is not None
        if energy is not None and cast(Object, pv["prepared_asset"])["id"] != (
            scenario.pv_reference_asset_id
            if isinstance(scenario, DcPlantEnergyInputs)
            else scenario.pv_available_asset_id
        ):
            raise ReportInputsChanged(
                "report PV and energy results use different generation profiles"
            )
        for name, sha in cast(Object, pv["pinned_assets"]).items():
            if name.endswith(".metadata") and isinstance(sha, str):
                provenance(workspace.blobs.object(sha))
        # An explicitly selected complete PV result defines the report scope.
        # Without it, the energy profile's actual AC/DC group defines the list.
        prepared_pv = cast(Object, pv["prepared_asset"])
        if geometric:
            asset = Assets(workspace).get(actor, project.id, str(prepared_pv["id"]))
            if (
                asset.purpose != GEOMETRIC_PV_PURPOSE
                or asset.content_sha256 != prepared_pv.get("content_sha256")
                or asset.metadata_sha256 != prepared_pv.get("metadata_sha256")
                or asset.metadata != prepared_pv.get("metadata")
            ):
                raise VersionUnavailable(
                    "the saved geometric PV reference asset differs"
                )
            profile_dependencies(
                asset, "pv_available_ac", project.inputs, workspace.blobs
            )
            geometric_reference(asset, run, "pv_available_ac")
            bases["pv"] = workspace.blobs.put_object(
                cast(Object, asset.metadata["woo_module_inputs"])
            )
        elif roof_ac:
            asset = Assets(workspace).get(actor, project.id, str(prepared_pv["id"]))
            if (
                asset.purpose not in (ROOF_AC_PURPOSE, KNOWN_AC_PURPOSE)
                or asset.content_sha256 != prepared_pv.get("content_sha256")
                or asset.metadata_sha256 != prepared_pv.get("metadata_sha256")
                or asset.metadata != prepared_pv.get("metadata")
            ):
                raise VersionUnavailable("the saved roof AC reference asset differs")
            profile_dependencies(
                asset, "pv_available_ac", project.inputs, workspace.blobs
            )
            provenance(asset.metadata)
            roof_reference(asset, run, "pv_available_ac")
            if asset.purpose == ROOF_AC_PURPOSE:
                bases["pv"] = workspace.blobs.put_object(
                    cast(Object, asset.metadata["woo_module_inputs"])
                )
        else:
            asset = Assets(workspace).get(actor, project.id, str(prepared_pv["id"]))
            if (
                asset.purpose != PVLIB_PURPOSE
                or asset.content_sha256 != prepared_pv.get("content_sha256")
                or asset.metadata_sha256 != prepared_pv.get("metadata_sha256")
                or asset.metadata != prepared_pv.get("metadata")
            ):
                raise VersionUnavailable("the saved weather-based PV asset differs")
            weather_reference(asset, run, "pv_available_ac")
            bases["pv"] = workspace.blobs.put_object(
                cast(Object, asset.metadata["woo_module_inputs"])
            )
        component_list = pv_components(
            workspace.blobs,
            cast(str, prepared_pv["content_sha256"]),
            cast(Object, prepared_pv["metadata"]),
        )

    comparison: Object | None = None
    if options.comparison is not None:
        comparison = compare_energy_runs(
            workspace,
            actor,
            project.id,
            options.comparison.baseline_run_id,
            options.comparison.candidate_run_id,
        )
        for index, identity in enumerate(
            (options.comparison.baseline_run_id, options.comparison.candidate_run_id)
        ):
            side = comparison_side(workspace, actor, project.id, identity)
            sources.append(
                {
                    "run_id": side.run.id,
                    "revision": side.run.revision,
                    "kind": side.result["kind"],
                    "manifest_sha256": side.run.manifest_sha256,
                    "result_sha256": side.run.result_sha256,
                    "input_sha256": side.result["input_sha256"],
                    "runtime_sha256": side.result["runtime_sha256"],
                }
            )
            if isinstance(side.result.get("equipment_binding"), dict):
                bases[f"comparison_equipment.{index}"] = side.pinned[
                    "woo.equipment_inputs"
                ]
            for name, sha in side.pinned.items():
                if name.endswith(".metadata") and isinstance(sha, str):
                    metadata = workspace.blobs.object(sha)
                    provenance(metadata)
                    module_basis = metadata.get("woo_module_inputs")
                    if isinstance(module_basis, dict):
                        bases[f"energy.comparison.{index}.{name}"] = (
                            workspace.blobs.put_object(module_basis)
                        )
            comparison_profiles = (
                PlantEnergyKernel.profile_bindings(side.scenario)
                if isinstance(side.scenario, (PlantEnergyInputs, DcPlantEnergyInputs))
                else {
                    role: (role, asset_id)
                    for role, asset_id in side.scenario.profiles().items()
                }
            )
            for role, (measurement, asset_id) in comparison_profiles.items():
                asset = Assets(workspace).get(actor, project.id, asset_id)
                if asset.purpose not in (
                    ROOF_AC_PURPOSE,
                    KNOWN_AC_PURPOSE,
                    PVLIB_PURPOSE,
                    GEOMETRIC_PV_PURPOSE,
                ):
                    continue
                # Comparisons retain each original side's roof and choices;
                # the current editable project may describe a third scenario.
                bindings = profile_dependencies(
                    asset, measurement, side.inputs, workspace.blobs, binding=role
                )
                if any(side.pinned.get(name) != sha for name, sha in bindings.items()):
                    raise VersionUnavailable("comparison PV source bindings differ")
                if asset.purpose == GEOMETRIC_PV_PURPOSE:
                    geometric_reference(
                        asset,
                        side.run,
                        role,
                        comparison_role="baseline" if index == 0 else "candidate",
                    )
                elif asset.purpose in (ROOF_AC_PURPOSE, KNOWN_AC_PURPOSE):
                    roof_reference(
                        asset,
                        side.run,
                        role,
                        comparison_role="baseline" if index == 0 else "candidate",
                    )
                else:
                    weather_reference(
                        asset,
                        side.run,
                        role,
                        comparison_role="baseline" if index == 0 else "candidate",
                        converter_id=side.scenario.pv_converter_id
                        if measurement == "pv_available_dc"
                        and isinstance(side.scenario, EnergyInputs)
                        else None,
                    )

    direct_beam: Object | None = None
    if options.direct_beam_run_id is not None:
        run = owned(
            options.direct_beam_run_id,
            DIRECT_BEAM_KIND,
            ("geometry", "direct_beam_visibility"),
        )
        direct_beam = {
            **direct_beam_bundle(workspace, run),
            "run_id": run.id,
            "revision": run.revision,
            "result_sha256": run.result_sha256,
            "manifest_sha256": run.manifest_sha256,
        }
        bases["direct_beam"] = cast(Object, direct_beam["dependencies"])[
            "woo.module_inputs"
        ]
        if component_list is None:
            component_list = saved_roof_components(
                direct_beam["geometry"],
                cast(Object, direct_beam["woo_module_inputs"]),
                workspace.blobs,
                run.revision,
            )

    # Both adopted-candidate and direct-run paths must have evaluated the saved
    # wiring. An equipment-only candidate cannot silently omit new PV work.
    if assessment is not None and equipment_source_inputs is not None:
        has_result = isinstance(assessment.get("pv_electrical"), dict)
        if has_wiring and not has_result:
            raise ReportWiringCheckRequired(
                "report equipment has not assessed the saved PV wiring plan"
            )
        if has_result:
            fields: tuple[str, ...] = (
                "geometry",
                "pv_string_plan",
                "pv_plant_string_plan",
            )

            if any(
                equipment_source_inputs.get(field) != project.inputs.get(field)
                for field in fields
            ):
                raise ReportInputsChanged(
                    "report PV strings differ from the saved roof, wiring or physical instances"
                )
            if any(
                source.permissions.export != "permitted"
                for source in read_geometry(project.inputs.get("geometry")).sources
            ):
                raise ReportSourceExportRequired(
                    "PV wiring reports require export permission for the roof sources"
                )
            if project.inputs.get("pv_plant_string_plan") is not None:
                from .pv_string_inputs import (
                    PvPlantStringPlan,
                    plant_instance_projection,
                    plant_instance_statuses,
                )

                if plant_instance_projection(
                    equipment_source_inputs
                ) != plant_instance_projection(project.inputs):
                    raise ReportInputsChanged(
                        "report PV inverter instance identities changed"
                    )
                statuses = plant_instance_statuses(
                    project.inputs, PvPlantStringPlan.from_inputs(project.inputs)
                )
                if any(
                    status not in {"declared", "not_recorded"}
                    for status in statuses.values()
                ):
                    raise ReportInputsChanged(
                        "report PV inverter instance identity requires correction"
                    )

    installation: Object | None = None
    if options.include_installation:
        plan = InstallationInputs.read(project.inputs.get("installation"))
        from .installation_conductor_comparison import has_conductor_comparison
        from .installation_terminals import has_terminal_feature

        ports = {
            (device.id, port.id): port
            for device in plan.instances
            for port in device.ports
        }
        has_terminal_circuit = has_terminal_feature(plan) and any(
            circuit.kind == "control"
            and "communication_use" in circuit.model_fields_set
            or any(
                ports[(endpoint.instance_id, endpoint.port_id)].terminal_binding
                is not None
                for endpoint in (circuit.start, circuit.end)
            )
            for circuit in plan.circuits
        )
        if (
            not plan.cable_runs
            and "pv_string_links" not in plan.model_fields_set
            and project.inputs.get("pv_plant_string_plan") is None
            and not has_terminal_circuit
            and not plan.materials
        ):
            raise InvalidInput(
                "select at least one physical cable for the routing report"
            )

        basis = product_basis(
            plan,
            products.equipment_basis(include_cables=True),
            allow_stale=has_terminal_feature(plan) or has_conductor_comparison(plan),
        )
        installation = route_takeoff(project.inputs, basis)
        geometry = GeometryDocument.read(project.inputs.get("geometry"))
        mounting_sources = {
            source_id
            for item in plan.materials
            if item.mounting_quantity_basis is not None
            for source_id in (
                item.mounting_quantity_basis.array.source_id,
                item.mounting_quantity_basis.roof.source_id,
            )
        }
        exportable_sources = {
            s.id for s in geometry.sources if s.permissions.export == "permitted"
        }
        if not mounting_sources.issubset(exportable_sources):
            raise ReportSourceExportRequired(
                "mounting layout source export permission is unconfirmed"
            )
        instance_sources = {instance.source_id for instance in plan.instances}
        if any(
            s.id in instance_sources and s.permissions.export != "permitted"
            for s in geometry.sources
        ):
            raise ReportSourceExportRequired(
                "installation instance source export permission is unconfirmed"
            )
        if any(
            "source_export_unconfirmed" in cast(list[str], cable["reasons"])
            for cable in cast(list[Object], installation["cables"])
        ):
            raise ReportSourceExportRequired(
                "installation source export permission is unconfirmed"
            )
        bases["installation"] = workspace.blobs.put_object(basis)
        if isinstance(assessment, dict):
            counts: dict[tuple[int, str], int] = {}
            for instance in plan.instances:
                if instance.product_id is not None:
                    assert instance.product_revision is not None
                    product_identity = (instance.product_id, instance.product_revision)
                    counts[product_identity] = counts.get(product_identity, 0) + 1
            selected = cast(list[Object], assessment["selected_products"])
            bom = cast(list[Object], assessment["provisional_bill_of_materials"])
            if any(
                len(
                    products_for_id := [
                        p for p in selected if p.get("product_id") == pid
                    ]
                )
                != 1
                or products_for_id[0].get("product_revision") != revision
                or len(lines := [p for p in bom if p.get("product_id") == pid]) != 1
                or type(lines[0].get("quantity")) is not int
                or quantity > cast(int, lines[0]["quantity"])
                for (pid, revision), quantity in counts.items()
            ):
                raise ReportInputsChanged(
                    "installation instances differ from the selected equipment assessment scope"
                )

    customer_selection = (
        partial_equipment(project.inputs, products)
        if assessment is None and not comparison_only and retained_comparison is None
        else None
    )
    if customer_selection:
        bases["customer_equipment"] = workspace.blobs.put_object(customer_selection[1])
    brief = project.inputs.get("brief")
    if (
        not sources
        and not customer_selection
        and installation is None
        and not (isinstance(brief, dict) and brief.get("system_scope"))
    ):
        raise InvalidInput(
            "choose a project direction or a completed analysis for the report"
        )
    if isinstance(assessment, dict) and isinstance(
        assessment.get("pv_electrical"), dict
    ):
        equipment_basis = workspace.blobs.object(cast(str, bases["equipment"]))
        electrical_proof = equipment_basis.get("pv_module_inputs")
        if not isinstance(electrical_proof, dict):
            raise VersionUnavailable(
                "the wiring report has no frozen PV reference proof"
            )
        # Handoffs aggregate the top-level Woo bases. Keep the reference
        # separately addressable so later withdrawal checks retain it too.
        bases["equipment_pv"] = workspace.blobs.put_object(electrical_proof)
        if component_list is None:
            component_list = saved_roof_components(
                project.inputs.get("geometry"),
                electrical_proof,
                workspace.blobs,
                project.revision,
            )
    layout = project.inputs.get("geometry")
    if (
        component_list is None
        and isinstance(candidate, dict)
        and comparison is None
        and not storage_only_project(project.inputs)
        and not is_known(
            project.inputs.get(
                "pvgis_reference_setup", project.inputs.get("pvgis_reference")
            )
        )
        and isinstance(layout, dict)
        and layout.get("arrays")
    ):
        component_list = saved_roof_components(
            layout,
            lambda: products.roof_basis(project.inputs),
            workspace.blobs,
            project.revision,
        )
        component_dependencies = component_list.get("dependencies")
        if (
            isinstance(component_dependencies, dict)
            and "woo_module" in component_dependencies
        ):
            bases["equipment_pv"] = component_dependencies["woo_module"]
    historical_bases = {
        name: sha for name, sha in bases.items() if name.startswith("energy.")
    }
    if historical_bases:
        current_module = (
            workspace.blobs.object(cast(str, bases["pv"]))
            if "pv" in bases
            else products.roof_basis(project.inputs)
        )
        for name, sha in historical_bases.items():
            current = renew_module_permission(
                workspace.blobs.object(cast(str, sha)), current_module
            )
            bases[name] = workspace.blobs.put_object(current)
    dependencies: Object = {f"woo.{name}": sha for name, sha in bases.items()}
    dependencies.update(
        {f"historical_woo.{name}": sha for name, sha in historical_bases.items()}
    )
    for index, item in enumerate(cast(list[Object], sources)):
        dependencies[f"run.{index}.manifest"] = item["manifest_sha256"]
        dependencies[f"run.{index}.result"] = item["result_sha256"]
    if component_list is not None and component_list.get("status") == "available":
        for name, sha in cast(Object, component_list["dependencies"]).items():
            dependencies[f"pv_components.{name}"] = sha
    for index, reference in enumerate(known_references.values()):
        dependencies[f"pvgis_known.{index}.manifest"] = reference["content_sha256"]
        dependencies[f"pvgis_known.{index}.metadata"] = reference["metadata_sha256"]
        for name, sha in cast(Object, reference["dependencies"]).items():
            dependencies[f"pvgis_known.{index}.{name}"] = sha
    for index, reference in enumerate(roof_references.values()):
        dependencies[f"pvgis_reference.{index}.manifest"] = reference["content_sha256"]
        dependencies[f"pvgis_reference.{index}.metadata"] = reference["metadata_sha256"]
        for name, sha in cast(Object, reference["dependencies"]).items():
            dependencies[f"pvgis_reference.{index}.{name}"] = sha
    for index, reference in enumerate(pvlib_references.values()):
        dependencies[f"pvlib_reference.{index}.metadata"] = reference["metadata_sha256"]
        for name, sha in cast(Object, reference["dependencies"]).items():
            dependencies[f"pvlib_reference.{index}.{name}"] = sha
    for index, reference in enumerate(geometric_pv_references.values()):
        dependencies[f"geometric_pv_reference.{index}.manifest"] = reference[
            "content_sha256"
        ]
        dependencies[f"geometric_pv_reference.{index}.metadata"] = reference[
            "metadata_sha256"
        ]
        for name, sha in cast(Object, reference["dependencies"]).items():
            dependencies[f"geometric_pv_reference.{index}.{name}"] = sha
    if direct_beam is not None:
        for name, sha in cast(Object, direct_beam["dependencies"]).items():
            dependencies[f"direct_beam.{name}"] = sha
    condition_inputs: Object | None = None
    certificate_context: Object | None = None
    if assessment is not None and "equipment" in bases:
        if equipment_source_run is None or equipment_source_inputs is None:
            raise VersionUnavailable("the equipment source calculation is missing")
        if (
            "grid_connection" in equipment_source_inputs
            or "grid_connection" in project.inputs
            or "country_rule_inputs" in equipment_source_inputs
            or "country_rule_inputs" in project.inputs
        ):

            def grid_context(values: Object) -> tuple[bool, Json, bool, Json, Json]:
                from .country_rules import CountryRuleInputs
                from .grid_connection import GridConnection

                brief = values.get("brief")
                site = brief.get("site") if isinstance(brief, dict) else None
                raw_grid = values.get("grid_connection")
                raw_rules = values.get("country_rule_inputs")
                if isinstance(raw_grid, dict):
                    try:
                        raw_grid = GridConnection.read(raw_grid).model_dump(mode="json")
                    except InvalidInput:
                        pass
                if isinstance(raw_rules, dict):
                    try:
                        raw_rules = CountryRuleInputs.read(raw_rules).model_dump(
                            mode="json"
                        )
                    except InvalidInput:
                        pass
                return (
                    "grid_connection" in values,
                    raw_grid,
                    "country_rule_inputs" in values,
                    raw_rules,
                    site.get("country_code") if isinstance(site, dict) else None,
                )

            # The declarations and country scope belong to the selected
            # assessment/search/energy source, not the report's editable site.
            # No new field on either side preserves the legacy projection.
            if grid_context(equipment_source_inputs) != grid_context(project.inputs):
                raise ReportInputsChanged(
                    "report grid entries or country differ from the selected result; check the selection again"
                )
        condition_key = "equipment_condition_inputs"
        if (
            condition_key in equipment_source_inputs,
            equipment_source_inputs.get(condition_key),
        ) != (condition_key in project.inputs, project.inputs.get(condition_key)):
            raise ReportInputsChanged(
                "report device entries differ from the selected result; prepare and check the selection again"
            )
        if condition_key in equipment_source_inputs:
            validate_condition_inputs(equipment_source_inputs, require_prepared=True)
            condition_inputs = cast(Object, equipment_source_inputs[condition_key])
            certificate_context = {
                "run_id": equipment_source_run.id,
                "revision": equipment_source_run.revision,
                "kind": cast(Object, equipment_source_run.result)["kind"],
                **(
                    {"candidate_id": candidate["candidate_id"]}
                    if isinstance(candidate, dict)
                    and equipment_source_run.id == candidate["run_id"]
                    else {}
                ),
            }
    declared_panels = (
        None if comparison_only else _declared_panels(declared_inputs, component_list)
    )
    source: Object = {
        "schema_version": 1,
        **(
            {"declared_pv_panels": declared_panels}
            if declared_panels is not None
            else {}
        ),
        "project_id": project.id,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "title": project.title,
        "brief": None if comparison_only else project.inputs.get("brief"),
        **(
            {"inquiry_quantities": project.inputs["inquiry_quantities"]}
            if not comparison_only and "inquiry_quantities" in project.inputs
            else {}
        ),
        **(
            {"existing_system": project.inputs["existing_system"]}
            if not comparison_only and "existing_system" in project.inputs
            else {}
        ),
        "equipment_selection": (
            project.inputs.get("equipment_selection")
            if retained_comparison is None
            else None
        ),
        **(
            {
                "equipment_condition_inputs": condition_inputs,
                "certificate_context": certificate_context,
            }
            if condition_inputs is not None
            else {}
        ),
        **(
            {"equipment_plant": project.inputs["equipment_plant"]}
            if retained_comparison is None and "equipment_plant" in project.inputs
            else {}
        ),
        **(
            {"retained_inverter": retained_comparison}
            if retained_comparison is not None
            else {}
        ),
        "candidate": candidate,
        **({"peak_comparison": peak_comparison} if peak_comparison is not None else {}),
        **(
            {"self_use_comparison": self_use_comparison}
            if self_use_comparison is not None
            else {}
        ),
        "equipment": assessment,
        **(
            {"customer_equipment": cast(list[Json], customer_selection[0])}
            if customer_selection
            else {}
        ),
        "installation": installation,
        "energy": energy,
        "energy_scenario": scenario.model_dump(mode="json")
        if energy is not None
        else None,
        "energy_equipment": energy.get("equipment_binding") if energy else None,
        "pv_components": component_list,
        "pv": pv,
        **({"direct_beam": direct_beam} if direct_beam is not None else {}),
        **(
            {"pvgis_known_ac_references": list(known_references.values())}
            if known_references
            else {}
        ),
        **(
            {"pvgis_roof_ac_references": list(roof_references.values())}
            if roof_references
            else {}
        ),
        **(
            {"pvlib_references": list(pvlib_references.values())}
            if pvlib_references
            else {}
        ),
        **(
            {"geometric_pv_references": list(geometric_pv_references.values())}
            if geometric_pv_references
            else {}
        ),
        "source_runs": sources,
        "woo_bases": bases,
        "historical_woo_bases": historical_bases,
        "generated_at": datetime.fromtimestamp(workspace.clock(), UTC).isoformat(),
        "locale": options.locale,
        "source_labels": list(dict.fromkeys(labels)),
        "dependencies": dependencies,
    }
    if assessment is not None and "equipment" in bases:
        certificates = certificate_documents(
            workspace.blobs.object(cast(str, bases["equipment"])), assessment
        )
        if frozen_certificates is not None:
            associated = {
                key: value
                for key, value in frozen_certificates.items()
                if key not in {"inspections", "condition_review"}
            }
            if associated != certificates:
                raise VersionUnavailable(
                    "recorded certificate review differs from frozen equipment sources"
                )
            certificates = frozen_certificates
        source["certificates"] = certificates
    if options.inspect_certificate_declarations or condition_inputs is not None:
        if "certificates" not in source:
            raise InvalidInput("certificate inspection requires selected equipment")
        source["inspect_certificate_declarations"] = True
    if comparison is not None:
        source["comparison"] = comparison
        dependencies["energy_comparison"] = workspace.blobs.put_object(comparison)
    if installation is not None:
        dependencies["installation_model"] = workspace.blobs.put_object(installation)
    # All owned artifacts above remain frozen source facts. Confirm each
    # distinct Woo proof once here, before admission can publish a run. An
    # eager check per profile/consumer would repeat the same live publication
    # reads; the durable worker independently confirms before and after use.
    confirm_report_sources(workspace, products, source)
    return source


def confirm_report_sources(
    workspace: Workspace, products: ProductSources, source: Object
) -> None:
    bases = source.get("woo_bases")
    if not isinstance(bases, dict):
        raise VersionUnavailable("report source permission proofs are missing")
    distinct: dict[str, bool] = {}
    for name, sha in bases.items():
        if not isinstance(sha, str):
            raise VersionUnavailable("report source permission proof is invalid")
        distinct[sha] = distinct.get(sha, False) or (
            not name.startswith("comparison_equipment.")
            and name
            not in {
                "equipment",
                "energy_equipment",
                "installation",
            }
        )
    products.confirm_bases(
        [
            (workspace.blobs.object(sha), require_reference)
            for sha, require_reference in distinct.items()
        ]
    )
