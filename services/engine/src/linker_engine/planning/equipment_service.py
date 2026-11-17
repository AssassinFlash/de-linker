"""Owned durable command for one proposed equipment configuration."""

from __future__ import annotations

from typing import Literal

from .assets import Assets
from .canonical import Object
from .direct_beam_weather import check_direct_beam
from .equipment_candidate_choice import (
    EquipmentCandidateChoice,
    check_equipment_candidate,
)
from .equipment_declarations import (
    compile_discovery_inputs,
    compile_equipment_inputs,
    normalize_discovery_inputs,
    restore_comparison_models,
)
from .equipment_kernel import EquipmentKernel
from .errors import InvalidInput
from .geometric_pv_job import check_geometric_pv
from .geometry_import_selections import check_geometry_imports
from .profile_selections import check_profile_selections
from .pv_preparation import check_pv_preparation
from .records import Actor, Context, Project, Run
from .workspace import Workspace


class EquipmentService:
    def __init__(
        self, workspace: Workspace, kernel: EquipmentKernel, *, max_attempts: int
    ) -> None:
        if workspace is not kernel.workspace:
            raise InvalidInput("equipment qualification must share project authority")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

    def find(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        *,
        key: str,
        input_contract: str | None = None,
    ) -> tuple[Project, Run]:
        return self._admit_current(
            actor,
            project_id,
            expected_revision,
            inputs,
            operation="find-equipment",
            key=key,
            input_contract=input_contract,
        )

    def check(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        *,
        key: str,
        input_contract: str | None = None,
    ) -> tuple[Project, Run]:
        return self._admit_current(
            actor,
            project_id,
            expected_revision,
            inputs,
            operation="check-equipment",
            key=key,
            input_contract=input_contract,
        )

    def _admit_current(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        *,
        operation: Literal["find-equipment", "check-equipment"],
        key: str,
        input_contract: str | None,
    ) -> tuple[Project, Run]:
        authored = normalize_discovery_inputs(inputs)

        def resolve() -> Context:
            discovery = authored
            if operation == "find-equipment" and "equipment_candidate" in authored:
                choice = EquipmentCandidateChoice.read(authored["equipment_candidate"])
                run = self.workspace.run(actor, choice.run_id)
                if run.project_id != project_id:
                    raise InvalidInput("candidate must belong to this project")
                discovery = restore_comparison_models(
                    authored, self.workspace.pinned_inputs(run.manifest)
                )
            execution = (
                compile_discovery_inputs(discovery)
                if operation == "find-equipment"
                else compile_equipment_inputs(authored, self.kernel.products)
            )
            if operation == "check-equipment" and not {
                "equipment_selection",
                "equipment_plant",
            }.intersection(execution):
                raise InvalidInput(
                    "select equipment to check",
                    fields=("equipment_setup.inverter_product_id",),
                )
            previous = self.workspace.get(
                actor, project_id, revision=expected_revision
            ).inputs
            assets = Assets(self.workspace)
            for check in (
                check_profile_selections,
                check_geometry_imports,
                check_pv_preparation,
                check_direct_beam,
                check_geometric_pv,
            ):
                check(assets, actor, project_id, execution)
            check_equipment_candidate(
                self.workspace,
                actor,
                project_id,
                execution,
                products=self.kernel.products,
                previous=previous,
            )
            self.kernel.products.check_project(execution, previous)
            context = self.kernel.context(actor, project_id, execution)
            resolved = self.workspace.blobs.put_object(
                {
                    "schema_version": 1,
                    "source_input_sha256": self.workspace.input_hash(authored),
                    "inputs": execution,
                }
            )
            return Context(
                context.code_sha256,
                context.models,
                {**context.assets, "resolved_inputs": resolved},
                context.parameters,
            )

        return self.workspace.evaluate_inputs(
            actor,
            project_id,
            expected_revision,
            authored,
            resolve,
            operation=operation,
            key=key,
            max_attempts=self.max_attempts,
            input_contract=input_contract,
        )

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            self.kernel.context(actor, project_id, project.inputs),
            key=key,
            max_attempts=self.max_attempts,
            intent={"kind": self.kernel.kind},
        )
