"""Trusted owned command adapter; browsers do not choose runtime or dependencies."""

from __future__ import annotations

from .canonical import Object
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .errors import EvidenceMissing, InvalidInput
from .plant_energy_kernel import PlantEnergyKernel
from .records import Actor, Run
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
    ) -> None:
        self.workspace = workspace
        self.kernel = kernel
        self.max_attempts = max_attempts
        self.dc_kernel = dc_kernel
        self.plant_kernel = plant_kernel

    @property
    def kernels(self) -> tuple[EnergyKernel | PlantEnergyKernel, ...]:
        return (
            self.kernel,
            *((self.dc_kernel,) if self.dc_kernel is not None else ()),
            *((self.plant_kernel,) if self.plant_kernel is not None else ()),
        )

    def kernel_for(self, inputs: Object) -> EnergyKernel | PlantEnergyKernel:
        if {"equipment_plant", "equipment_plant_setup"}.intersection(inputs):
            if self.plant_kernel is None:
                raise EvidenceMissing(
                    "plant_energy_executor: no registered joint executor"
                )
            if "energy_plant" not in inputs:
                raise EvidenceMissing(
                    "plant_energy_scenario: prepare every named storage unit and common connection"
                )
            return self.plant_kernel
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
