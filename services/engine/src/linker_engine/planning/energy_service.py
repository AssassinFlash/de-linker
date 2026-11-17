"""Trusted owned command adapter; browsers do not choose runtime or dependencies."""

from __future__ import annotations

from .canonical import Object
from .direct_beam_weather import check_direct_beam
from .energy_declarations import EnergyDeclarations, normalize_authored_inputs
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .equipment_candidate_choice import check_equipment_candidate
from .errors import EvidenceMissing, InvalidInput
from .geometric_pv_job import check_geometric_pv
from .geometry_import_selections import check_geometry_imports
from .plant_energy_kernel import PlantEnergyKernel
from .pv_preparation import check_pv_preparation
from .records import Actor, Context, Project, Run
from .workspace import Workspace


class EnergyService:
    def __init__(
        self,
        workspace: Workspace,
        kernel: EnergyKernel,
        *,
        max_attempts: int,
        dc_kernel: EnergyKernel | None = None,
        plant_kernel: PlantEnergyKernel | None = None,
        plant_dc_kernel: PlantEnergyKernel | None = None,
    ) -> None:
        self.workspace = workspace
        self.kernel = kernel
        self.max_attempts = max_attempts
        self.dc_kernel = dc_kernel
        self.plant_kernel = plant_kernel
        self.plant_dc_kernel = plant_dc_kernel

    @property
    def kernels(self) -> tuple[EnergyKernel | PlantEnergyKernel, ...]:
        return (
            self.kernel,
            *((self.dc_kernel,) if self.dc_kernel is not None else ()),
            *((self.plant_kernel,) if self.plant_kernel is not None else ()),
            *((self.plant_dc_kernel,) if self.plant_dc_kernel is not None else ()),
        )

    def kernel_for(self, inputs: Object) -> EnergyKernel | PlantEnergyKernel:
        if {"equipment_plant", "equipment_plant_setup"}.intersection(inputs):
            scenario = inputs.get("energy_plant")
            dc = (
                isinstance(scenario, dict)
                and scenario.get("coupling") == "plant_shared_dc"
            )
            kernel = self.plant_dc_kernel if dc else self.plant_kernel
            if kernel is None:
                raise EvidenceMissing(
                    "plant_energy_executor: no registered joint executor"
                )
            if "energy_plant" not in inputs:
                raise EvidenceMissing(
                    "plant_energy_scenario: prepare every named storage unit and common connection"
                )
            return kernel
        if "energy_plant" in inputs:
            raise InvalidInput("joint energy requires a prepared equipment plant")
        if EnergyInputs.from_project(inputs).coupling == "independent_ac":
            return self.kernel
        if self.dc_kernel is None:
            raise EvidenceMissing(
                "shared_dc_executor: this runtime has no registered DC executor"
            )
        return self.dc_kernel

    def kind_for(self, actor: Actor, project_id: str, revision: int) -> str:
        return self.kernel_for(
            self.workspace.get(actor, project_id, revision=revision).inputs
        ).kind

    def calculate(
        self,
        actor: Actor,
        project_id: str,
        expected_revision: int,
        inputs: Object,
        *,
        key: str,
        input_contract: str | None = None,
    ) -> tuple[Project, Run]:
        authored = normalize_authored_inputs(inputs)
        declarations = EnergyDeclarations(
            self.workspace, actor, project_id, authored, self.kernel.products
        )

        def resolve() -> Context:
            previous = self.workspace.get(
                actor, project_id, revision=expected_revision
            ).inputs
            execution = declarations.compile()
            for check in (
                check_geometry_imports,
                check_pv_preparation,
                check_direct_beam,
                check_geometric_pv,
            ):
                check(declarations.assets, actor, project_id, execution)
            check_equipment_candidate(
                self.workspace,
                actor,
                project_id,
                execution,
                products=self.kernel.products,
                previous=previous,
            )
            if self.kernel.products is not None:
                self.kernel.products.check_project(execution, previous)
            kernel = self.kernel_for(execution)
            context = kernel.context(
                actor, project_id, execution, assets=declarations.assets
            )
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
            operation="calculate",
            publish=declarations.publish,
            key=key,
            input_contract=input_contract,
            max_attempts=self.max_attempts,
        )

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        kernel = self.kernel_for(project.inputs)
        context = kernel.context(actor, project_id, project.inputs)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            context,
            key=key,
            max_attempts=self.max_attempts,
            intent={"kind": kernel.kind},
        )
