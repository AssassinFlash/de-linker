"""Resolve owned report sources once, without recomputing their calculations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from .assets import Assets
from .canonical import Json, Object
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .equipment_candidate_choice import check_equipment_candidate
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_inputs import EquipmentSelection
from .equipment_kernel import EquipmentKernel
from .errors import InvalidInput, VersionUnavailable
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .pv_preparation import PvReferenceKernel
from .records import Actor, Project, Run
from .report_inputs import ReportOptions
from .workspace import Workspace


class ReportInputsChanged(InvalidInput):
    code = "report_inputs_changed"


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
    candidate = project.inputs.get("equipment_candidate")
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
        if EquipmentSelection.read(
            previous.get("equipment_selection")
        ) != EquipmentSelection.read(project.inputs.get("equipment_selection")):
            raise InvalidInput(
                "report equipment does not match the saved project selection"
            )
        assert run.result is not None
        assessment = cast(Object, run.result["assessment"])
        pinned = cast(Object, run.result["pinned_assets"])
        bases["equipment"] = pinned["woo.equipment_inputs"]

    energy: Object | None = None
    if options.energy_run_id is not None:
        run = owned(options.energy_run_id, EnergyKernel.kind, ("energy_replay",))
        energy = run.result
        assert energy is not None
        scenario = EnergyInputs.from_project(project.inputs)
        pinned_energy = cast(Object, energy["pinned_assets"])
        for role, asset_id in scenario.profiles().items():
            asset = Assets(workspace).get(actor, project.id, asset_id)
            try:
                profile_bindings = profile_dependencies(
                    asset, role, project.inputs, workspace.blobs
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
        if (
            energy is not None
            and cast(Object, pv["prepared_asset"])["id"]
            != EnergyInputs.from_project(project.inputs).pv_available_asset_id
        ):
            raise ReportInputsChanged(
                "report PV and energy results use different generation profiles"
            )
        for name, sha in cast(Object, pv["pinned_assets"]).items():
            if name.endswith(".metadata") and isinstance(sha, str):
                provenance(workspace.blobs.object(sha))
        bases["pv"] = workspace.blobs.put_object(products.pv_basis(project.inputs))

    if not sources:
        raise InvalidInput("select at least one completed analysis for the report")
    dependencies: Object = {f"woo.{name}": sha for name, sha in bases.items()}
    for index, item in enumerate(cast(list[Object], sources)):
        dependencies[f"run.{index}.manifest"] = item["manifest_sha256"]
        dependencies[f"run.{index}.result"] = item["result_sha256"]
    source: Object = {
        "schema_version": 1,
        "project_id": project.id,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "title": project.title,
        "brief": project.inputs.get("brief"),
        "equipment_selection": project.inputs.get("equipment_selection"),
        "candidate": candidate,
        "equipment": assessment,
        "energy": energy,
        "pv": pv,
        "source_runs": sources,
        "woo_bases": bases,
        "generated_at": datetime.fromtimestamp(workspace.clock(), UTC).isoformat(),
        "locale": options.locale,
        "source_labels": list(dict.fromkeys(labels)),
        "dependencies": dependencies,
    }
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
        distinct[sha] = distinct.get(sha, False) or name != "equipment"
    for sha, require_reference in distinct.items():
        products.confirm_basis(
            workspace.blobs.object(sha), require_reference=require_reference
        )
