"""The existing equipment command boundary with a finite-search executor."""

from __future__ import annotations

from .asset_publication import AssetResult
from .assets import Asset
from .canonical import Json, Object
from .comparison_pv import ComparisonPv, comparison_horizon, shared_dc
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_demand import pin_demand_profiles, replay_demand
from .equipment_kernel import EquipmentKernel
from .equipment_requirements import DeclaredEquipmentRequirements, EquipmentRequirements
from .equipment_search import search_equipment
from .equipment_search_limits import EquipmentSearchLimits
from .errors import InvalidInput
from .existing_system import unverified_retained_inverter
from .numerical_tolerance import Tolerance
from .plant_search_plan import PlantSearchPlan
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .profile_demand_bounds import evaluate_bounds, pin_profiles, requested
from .profile_selections import ProfileSelections
from .pvgis_reference_kernel import PvgisRoofReferenceKernel
from .records import Actor, Context, Lease
from .worker import Control
from .workspace import Workspace


class EquipmentSearchKernel(EquipmentKernel):
    kind = "search_woo_equipment_v1"
    models = {"task": kind, "search": "finite_woo_single_and_declared_plant_v2"}

    def __init__(
        self,
        workspace: Workspace,
        products: ProductSources,
        limits: EquipmentSearchLimits,
        *,
        tolerance: Tolerance | None = None,
        max_intervals: int | None = None,
        pvgis_reference: PvgisRoofReferenceKernel | None = None,
    ) -> None:
        super().__init__(workspace, products)
        self.limits = limits
        self.tolerance, self.max_intervals = tolerance, max_intervals
        self.pv = (
            ComparisonPv(workspace, products, pvgis_reference)
            if pvgis_reference
            else None
        )

    def comparison_declarations(self, inputs: Object) -> Object:
        return self.pv.declarations(inputs) if self.pv is not None else inputs

    def parameters(self) -> Object:
        return {
            **super().parameters(),
            "work_budget": self.limits.work_budget,
            **(
                {"pvgis_execution_keys": list(self.pv.reference.execution_keys())}
                if self.pv
                else {}
            ),
            **(
                {
                    "demand_interval_budget": self.limits.demand_interval_budget,
                    "max_intervals": self.max_intervals,
                    "tolerance": self.tolerance.document() if self.tolerance else None,
                }
                if self.max_intervals is not None
                else {}
            ),
        }

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        retained = unverified_retained_inverter(inputs)
        pv_pinned, pending_pv = (
            self.pv.context(actor, project_id, inputs) if self.pv else ({}, False)
        )
        pinned = dict(pv_pinned)
        if retained is not None:
            declared_demand(inputs)
            if baseline_requested(inputs):
                pinned.update(
                    self.pin_baseline(
                        actor,
                        project_id,
                        inputs,
                        baseline_only=True,
                        skip_pv=pending_pv or bool(pv_pinned),
                    )
                )
            return Context(
                self.runtime.sha256,
                dict(self.models),
                {"runtime_bundle": self.runtime.sha256, **pinned},
                self.parameters(),
            )
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            PlantSearchPlan.from_inputs(inputs)
        else:
            EquipmentRequirements.from_inputs(inputs)
        if "equipment_demand" in inputs:
            if (
                self.tolerance is None
                or self.max_intervals is None
                or self.limits.demand_interval_budget is None
            ):
                raise InvalidInput(
                    "equipment demand replay budget is not configured",
                    fields=("equipment_demand",),
                )
            pinned.update(
                pin_demand_profiles(
                    self.workspace,
                    self.products,
                    actor,
                    project_id,
                    inputs,
                    pending_pv=pending_pv,
                )
            )
        elif requested(inputs):
            pinned.update(
                self.pin_baseline(
                    actor, project_id, inputs, skip_pv=pending_pv or bool(pv_pinned)
                )
            )
        basis = self.products.equipment_basis()
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "woo.equipment_inputs": self.workspace.blobs.put_object(basis),
                **pinned,
            },
            self.parameters(),
        )

    def pin_baseline(
        self,
        actor: Actor,
        project_id: str,
        inputs: Object,
        *,
        baseline_only: bool = False,
        skip_pv: bool = False,
    ) -> dict[str, str]:
        if self.max_intervals is None:
            raise InvalidInput("profile demand interval limit is not configured")
        return pin_profiles(
            self.workspace,
            self.products,
            actor,
            project_id,
            inputs,
            baseline_only=baseline_only,
            skip_pv=skip_pv,
        )

    def prepare_inputs(
        self,
        lease: Lease,
        control: Control,
        manifest: Object,
        inputs: Object,
        pinned: Object,
    ) -> tuple[Object, AssetResult | None]:
        prepared = None
        if self.pv is not None and "pvgis_reference.plan" in pinned:
            prepared = self.pv.reference.prepare(
                lease, control, manifest, inputs, pinned
            )
            publication = prepared.asset
            asset = Asset(
                publication.id,
                publication.project_id,
                publication.content_sha256,
                publication.media_type,
                publication.purpose,
                publication.metadata_sha256,
                self.workspace.blobs.object(publication.metadata_sha256),
            )
            self.products.check_profile(asset.metadata)
            pinned.update(
                profile_dependencies(
                    asset, "pv_available_ac", inputs, self.workspace.blobs
                )
            )
            raw = inputs.get("profile_selections")
            selected = ProfileSelections.read(raw).selected if raw is not None else {}
            inputs = {
                **inputs,
                "profile_selections": {
                    "schema_version": 1,
                    "selected": {
                        **{str(role): identity for role, identity in selected.items()},
                        "pv_available_ac": asset.id,
                    },
                },
            }
        metadata = pinned.get("pv_available_ac.metadata")
        if (
            self.pv is not None
            and "gross_load.raw" in pinned
            and isinstance(metadata, str)
        ):
            inputs = comparison_horizon(inputs, self.workspace.blobs.object(metadata))
        return inputs, prepared

    def requires_woo_basis(self, inputs: Object) -> bool:
        return unverified_retained_inverter(inputs) is None

    def compute(
        self, inputs: Object, basis: Object, control: Control, *, pinned: Object
    ) -> Object:
        retained = unverified_retained_inverter(inputs)
        if retained is not None:
            partial: Object = {
                "existing_system": retained.model_dump(mode="json"),
                **declared_demand(inputs),
            }
            if "gross_load.raw" in pinned:
                assert self.max_intervals is not None
                profile_output: Object = {}
                evaluate_bounds(
                    self.workspace,
                    self.products,
                    inputs,
                    None,
                    pinned,
                    profile_output,
                    control,
                    max_intervals=self.max_intervals,
                    work_budget=0,
                    tolerance=None,
                )
                partial["profile_baseline"] = profile_output["demand"]
            return {"retained_inverter": partial}
        search = search_equipment
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            from .plant_search import search_plant

            search = search_plant
        result = search(
            inputs,
            basis,
            self.limits,
            EquipmentCandidateStore(self.workspace),
            control.checkpoint,
            constrain_models="resolved_inputs" in pinned,
        )
        if "equipment_demand" in inputs:
            assert (
                self.tolerance is not None
                and self.max_intervals is not None
                and self.limits.demand_interval_budget is not None
            )
            replay_demand(
                self.workspace,
                self.products,
                inputs,
                basis,
                pinned,
                result,
                control,
                tolerance=self.tolerance,
                max_intervals=self.max_intervals,
                work_budget=self.limits.demand_interval_budget,
            )
        elif requested(inputs) and "gross_load.raw" in pinned:
            assert self.max_intervals is not None
            evaluate_bounds(
                self.workspace,
                self.products,
                inputs,
                basis,
                pinned,
                result,
                control,
                max_intervals=self.max_intervals,
                work_budget=(
                    self.limits.demand_interval_budget
                    or self.max_intervals * self.limits.work_budget
                ),
                tolerance=self.tolerance,
            )
        output: Object = {"search": result}
        if shared_dc(inputs):
            output["pv_capacity_basis"] = "declared_hardware"
        return output


def baseline_requested(inputs: Object) -> bool:
    profiles = inputs.get("profile_selections")
    selected = profiles.get("selected") if isinstance(profiles, dict) else None
    return requested(inputs) and isinstance(selected, dict) and "gross_load" in selected


def declared_demand(inputs: Object) -> Object:
    def read(
        raw: Json, path: str, connection: DeclaredEquipmentRequirements | None = None
    ) -> DeclaredEquipmentRequirements:
        setup = raw if isinstance(raw, dict) else {}
        return DeclaredEquipmentRequirements.effective(
            {**setup, "schema_version": 1},
            inputs=inputs,
            path=path,
            connection=connection,
        )

    plant = inputs.get("equipment_plant_setup")
    if not isinstance(plant, dict):
        demand = read(inputs.get("equipment_setup"), "equipment_setup")
        return {"requirements": demand.model_dump(mode="json")}
    common = read(plant.get("requirements"), "equipment_plant_setup.requirements")
    units: list[Json] = []
    raw_units = plant.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise InvalidInput("declare the named plant systems")
    for index, unit in enumerate(raw_units):
        declared = unit.get("inputs") if isinstance(unit, dict) else None
        if (
            not isinstance(unit, dict)
            or not isinstance(declared, dict)
            or not isinstance(unit.get("id"), str)
            or not isinstance(unit.get("name"), str)
        ):
            raise InvalidInput("declare each plant system identity and demand")
        demand = read(
            declared.get("equipment_setup"),
            f"equipment_plant_setup.units[{index}].inputs.equipment_setup",
            common,
        )
        units.append(
            {
                "id": unit["id"],
                "name": unit["name"],
                "requirements": demand.model_dump(mode="json"),
            }
        )
    return {"requirements": common.model_dump(mode="json"), "units": units}
