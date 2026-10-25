"""Trusted owned command adapter; browsers do not choose runtime or dependencies."""

from __future__ import annotations

from .canonical import Object
from .energy_inputs import EnergyInputs
from .energy_kernel import EnergyKernel
from .errors import EvidenceMissing
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
    ) -> None:
        self.workspace = workspace
        self.kernel = kernel
        self.max_attempts = max_attempts
        self.dc_kernel = dc_kernel

    @property
    def kernels(self) -> tuple[EnergyKernel, ...]:
        return (
            (self.kernel,) if self.dc_kernel is None else (self.kernel, self.dc_kernel)
        )

    def kernel_for(self, inputs: Object) -> EnergyKernel:
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
