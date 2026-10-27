"""The existing equipment command boundary with a finite-search executor."""

from __future__ import annotations

from .canonical import Object
from .equipment_candidate_store import EquipmentCandidateStore
from .equipment_kernel import EquipmentKernel
from .equipment_requirements import EquipmentRequirements
from .equipment_search import search_equipment
from .equipment_search_limits import EquipmentSearchLimits
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
    ) -> None:
        super().__init__(workspace, products)
        self.limits = limits

    def parameters(self) -> Object:
        return {**super().parameters(), "work_budget": self.limits.work_budget}

    def context(self, actor: Actor, project_id: str, inputs: Object) -> Context:
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            PlantSearchPlan.from_inputs(inputs)
        else:
            EquipmentRequirements.from_inputs(inputs)
        basis = self.products.equipment_basis()
        return Context(
            self.runtime.sha256,
            dict(self.models),
            {
                "runtime_bundle": self.runtime.sha256,
                "woo.equipment_inputs": self.workspace.blobs.put_object(basis),
            },
            self.parameters(),
        )

    def compute(self, inputs: Object, basis: Object, control: Control) -> Object:
        search = search_equipment
        if "equipment_plant" in inputs or "equipment_plant_setup" in inputs:
            from .plant_search import search_plant

            search = search_plant
        return {
            "search": search(
                inputs,
                basis,
                self.limits,
                EquipmentCandidateStore(self.workspace),
                control.checkpoint,
            )
        }
