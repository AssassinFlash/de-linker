"""Resolve owned report sources once, without recomputing their calculations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from .assets import Assets
from .canonical import Json, Object
from .dc_energy_kernel import DcEnergyKernel
from .dc_plant_inputs import DcPlantEnergyInputs
from .dc_plant_kernel import DcPlantEnergyKernel
from .energy_comparison import compare_energy_runs, comparison_side
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_inputs import EquipmentSelection
from .equipment_kernel import EquipmentKernel
from .equipment_plant import EquipmentPlant, assert_plant_exclusivity
from .errors import InvalidInput, ProductEvidenceChanged, VersionUnavailable
from .installation_inputs import InstallationInputs
from .installation_takeoff import product_basis, route_takeoff
from .plant_energy_inputs import PlantEnergyInputs
from .plant_energy_kernel import PlantEnergyKernel
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .pv_preparation import PvReferenceKernel
from .records import Actor, Project, Run
from .report_inputs import ReportOptions
from .report_pv_components import pv_components, saved_roof_components
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
    comparison_only = (
        not options.include_installation
        and options.comparison is not None
        and all(
            identity is None
            for identity in (
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
        if isinstance(assessment.get("pv_electrical"), dict) and any(
            previous.get(field) != project.inputs.get(field)
            for field in ("geometry", "pv_string_plan")
        ):
            raise ReportInputsChanged(
                "report PV strings differ from the saved roof or wiring plan"
            )
        if isinstance(assessment.get("pv_electrical"), dict):
            from .geometry import read_geometry

            if any(
                s.permissions.export != "permitted"
                for s in read_geometry(project.inputs.get("geometry")).sources
            ):
                raise InvalidInput(
                    "PV wiring reports require export permission for the roof sources"
                )
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
                    )
                module_basis = metadata.get("woo_module_inputs")
                if isinstance(module_basis, dict):
                    bases[f"energy.{name}"] = workspace.blobs.put_object(module_basis)

    pv: Object | None = None
    if options.pv_run_id is not None:
        run = owned(
            options.pv_run_id,
            PvReferenceKernel.kind,
            ("geometry", "pv_generation", "pv_preparation", "weather_acquisition"),
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
        bases["pv"] = workspace.blobs.put_object(products.pv_basis(project.inputs))
        # An explicitly selected complete PV result defines the report scope.
        # Without it, the energy profile's actual AC/DC group defines the list.
        prepared_pv = cast(Object, pv["prepared_asset"])
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

    installation: Object | None = None
    if options.include_installation:
        plan = InstallationInputs.read(project.inputs.get("installation"))
        if not plan.cable_runs:
            raise InvalidInput(
                "select at least one physical cable for the routing report"
            )
        basis = product_basis(plan, products.equipment_basis())
        installation = route_takeoff(project.inputs, basis)
        from .geometry_documents import GeometryDocument

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
    source: Object = {
        "schema_version": 1,
        "project_id": project.id,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "title": project.title,
        "brief": None if comparison_only else project.inputs.get("brief"),
        "equipment_selection": project.inputs.get("equipment_selection"),
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
        "source_runs": sources,
        "woo_bases": bases,
        "historical_woo_bases": historical_bases,
        "generated_at": datetime.fromtimestamp(workspace.clock(), UTC).isoformat(),
        "locale": options.locale,
        "source_labels": list(dict.fromkeys(labels)),
        "dependencies": dependencies,
    }
    if comparison is not None:
        source["comparison"] = comparison
        dependencies["energy_comparison"] = workspace.blobs.put_object(comparison)
    if installation is not None:
        dependencies["installation_model"] = workspace.blobs.put_object(installation)
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
