"""Resolve owned report sources once, without recomputing their calculations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from .assets import Asset, Assets
from .canonical import Json, Object
from .certificate_evidence import certificate_documents
from .dc_energy_kernel import DcEnergyKernel
from .dc_plant_inputs import DcPlantEnergyInputs
from .dc_plant_kernel import DcPlantEnergyKernel
from .direct_beam_read import KIND as DIRECT_BEAM_KIND
from .direct_beam_read import direct_beam_bundle
from .energy_comparison import compare_energy_runs, comparison_side
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_condition_inputs import validate_condition_inputs
from .equipment_inputs import EquipmentSelection
from .equipment_kernel import EquipmentKernel
from .equipment_plant import EquipmentPlant, assert_plant_exclusivity
from .errors import InvalidInput, ProductEvidenceChanged, VersionUnavailable
from .frozen_documents import FrozenDocuments
from .geometric_pv_inputs import KIND as GEOMETRIC_PV_KIND
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .geometric_pv_report import geometric_pv_reference
from .geometry import read_geometry
from .geometry_documents import GeometryDocument
from .installation_inputs import InstallationInputs
from .installation_takeoff import product_basis, route_takeoff
from .plant_energy_inputs import PlantEnergyInputs
from .plant_energy_kernel import PlantEnergyKernel
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .pv_preparation import PvReferenceKernel
from .pv_profile_preparation import PROFILE_PURPOSE as PVLIB_PURPOSE
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


def renew_module_permission(previous: Object, current: Object) -> Object:
    """Renew permission only when every frozen module fact and citation matches."""
    if previous.get("schema_version") != 1 or not isinstance(
        previous.get("module"), dict
    ):
        raise VersionUnavailable("frozen Woo module proof is missing")
    if previous["module"] != current.get("module"):
        raise ProductEvidenceChanged("the frozen Woo module facts have changed")
    return current


def report_sources(
    workspace: Workspace,
    products: ProductSources,
    actor: Actor,
    project: Project,
    options: ReportOptions,
) -> Object:
    sources: list[Json] = []
    bases: dict[str, Json] = {}
    labels: list[str] = []
    roof_references: dict[str, Object] = {}
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
        if run.result.get("kind") != kind:
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
                "runtime_sha256": run.result["runtime_sha256"],
            }
        )
        return run

    assessment: Object | None = None
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
    candidate = None if comparison_only else project.inputs.get("equipment_candidate")
    if isinstance(candidate, dict):
        if options.equipment_run_id not in (None, candidate.get("run_id")):
            raise InvalidInput(
                "report equipment differs from the adopted project candidate"
            )
        # Validate the historical choice here; the common report boundary
        # confirms current permission for every distinct proof once below.
        check_equipment_candidate(
            workspace, actor, project.id, project.inputs, previous=project.inputs
        )
        run = workspace.run(actor, cast(str, candidate["run_id"]))
        assert run.result is not None
        equipment_source_run = run
        equipment_source_inputs = workspace.pinned_inputs(run.manifest)
        detail = EquipmentCandidateStore(workspace).read(
            actor, run.id, cast(str, candidate["candidate_id"])
        )
        assessment = cast(Object, detail["assessment"])
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
                "runtime_sha256": run.result["runtime_sha256"],
            }
        )
        pinned = cast(Object, run.result["pinned_assets"])
        bases["equipment"] = pinned["woo.equipment_inputs"]
    elif options.equipment_run_id is not None:
        run = owned(options.equipment_run_id, EquipmentKernel.kind, ())
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
        pinned = cast(Object, run.result["pinned_assets"])
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
            elif asset.purpose == ROOF_AC_PURPOSE:
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
        roof_ac = (
            selected_run.result is not None
            and selected_run.result.get("kind") == PvgisRoofReferenceKernel.kind
        )
        geometric = (
            selected_run.result is not None
            and selected_run.result.get("kind") == GEOMETRIC_PV_KIND
        )
        run = owned(
            options.pv_run_id,
            GEOMETRIC_PV_KIND
            if geometric
            else PvgisRoofReferenceKernel.kind
            if roof_ac
            else PvReferenceKernel.kind,
            ("geometry", "geometric_pv_preparation", "weather_acquisition")
            if geometric
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
                asset.purpose != ROOF_AC_PURPOSE
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
                elif asset.purpose == ROOF_AC_PURPOSE:
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
        has_wiring = any(
            project.inputs.get(key) is not None
            for key in ("pv_string_plan", "pv_plant_string_plan")
        )
        has_result = isinstance(assessment.get("pv_electrical"), dict)
        if has_wiring and not has_result:
            raise ReportInputsChanged(
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
                raise InvalidInput(
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
        if (
            not plan.cable_runs
            and "pv_string_links" not in plan.model_fields_set
            and project.inputs.get("pv_plant_string_plan") is None
        ):
            raise InvalidInput(
                "select at least one physical cable for the routing report"
            )
        basis = product_basis(plan, products.equipment_basis(include_cables=True))
        installation = route_takeoff(project.inputs, basis)
        geometry = GeometryDocument.read(project.inputs.get("geometry"))
        instance_sources = {instance.source_id for instance in plan.instances}
        if any(
            s.id in instance_sources and s.permissions.export != "permitted"
            for s in geometry.sources
        ):
            raise InvalidInput(
                "installation instance source export permission is unconfirmed"
            )
        if any(
            "source_export_unconfirmed" in cast(list[str], cable["reasons"])
            for cable in cast(list[Object], installation["cables"])
        ):
            raise InvalidInput("installation source export permission is unconfirmed")
        bases["installation"] = workspace.blobs.put_object(basis)
        if isinstance(assessment, dict):
            counts: dict[int, int] = {}
            for instance in plan.instances:
                if instance.product_id is not None:
                    counts[instance.product_id] = counts.get(instance.product_id, 0) + 1
            checked = {
                p["product_id"]: p.get("quantity")
                for p in cast(list[Object], assessment["provisional_bill_of_materials"])
            }
            if any(
                type(checked.get(pid)) is not int or quantity > cast(int, checked[pid])
                for pid, quantity in counts.items()
            ):
                raise ReportInputsChanged(
                    "installation instances exceed the selected equipment assessment scope"
                )

    if not sources and installation is None:
        raise InvalidInput("select at least one completed analysis for the report")
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
    historical_bases = {
        name: sha for name, sha in bases.items() if name.startswith("energy.")
    }
    if historical_bases:
        current_module = (
            workspace.blobs.object(cast(str, bases["pv"]))
            if "pv" in bases
            else products.module_basis()
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
        ):

            def grid_context(values: Object) -> tuple[bool, Json, Json]:
                brief = values.get("brief")
                site = brief.get("site") if isinstance(brief, dict) else None
                return (
                    "grid_connection" in values,
                    values.get("grid_connection"),
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
                    else {}
                ),
            }
    source: Object = {
        "schema_version": 1,
        "project_id": project.id,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "title": project.title,
        "brief": None if comparison_only else project.inputs.get("brief"),
        "equipment_selection": project.inputs.get("equipment_selection"),
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
            if "equipment_plant" in project.inputs
            else {}
        ),
        "candidate": candidate,
        "equipment": assessment,
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
    for sha, require_reference in distinct.items():
        products.confirm_basis(
            workspace.blobs.object(sha), require_reference=require_reference
        )
