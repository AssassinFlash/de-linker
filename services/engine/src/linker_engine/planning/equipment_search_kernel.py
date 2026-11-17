"""The existing equipment command boundary with a finite-search executor."""

from __future__ import annotations

from .canonical import Object
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_demand import pin_demand_profiles, replay_demand
from .equipment_kernel import EquipmentKernel
from .equipment_requirements import EquipmentRequirements
from .equipment_search import search_equipment
from .equipment_search_limits import EquipmentSearchLimits
from .errors import InvalidInput
from .numerical_tolerance import Tolerance
from .plant_search_plan import PlantSearchPlan
from .product_sources import ProductSources
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
                if self.limits.demand_interval_budget is not None
                else {}
            ),
        }

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            PlantSearchPlan.from_inputs(inputs)
        else:
            EquipmentRequirements.from_inputs(inputs)
        pinned = {}
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

    def compute(
        self, inputs: Object, basis: Object, control: Control, *, pinned: Object
    ) -> Object:
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
        return {"search": result}
