"""The existing equipment command boundary with a finite-search executor."""

from __future__ import annotations

from .canonical import Json, Object
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
from .profile_demand_bounds import evaluate_bounds, pin_profiles, requested
from .records import Actor, Context
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
    ) -> None:
        super().__init__(workspace, products)
        self.limits = limits
        self.tolerance, self.max_intervals = tolerance, max_intervals

    def parameters(self) -> Object:
        return {
            **super().parameters(),
            "work_budget": self.limits.work_budget,
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
        pinned: dict[str, str] = {}
        if retained is not None:
            declared_demand(inputs)
            if baseline_requested(inputs):
                pinned = self.pin_baseline(
                    actor, project_id, inputs, baseline_only=True
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
            pinned = pin_demand_profiles(
                self.workspace, self.products, actor, project_id, inputs
            )
        elif requested(inputs):
            pinned = self.pin_baseline(actor, project_id, inputs)
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
        )

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
        elif requested(inputs):
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
        return {"search": result}


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
