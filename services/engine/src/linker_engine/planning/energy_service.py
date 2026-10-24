"""Trusted owned command adapter; browsers do not choose runtime or dependencies."""

from __future__ import annotations

from .energy_kernel import EnergyKernel
from .records import Actor, Run
from .workspace import Workspace


class EnergyService:
    def __init__(
        self, workspace: Workspace, kernel: EnergyKernel, *, max_attempts: int
    ) -> None:
        self.workspace = workspace
        self.kernel = kernel
        self.max_attempts = max_attempts

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        context = self.kernel.context(actor, project_id, project.inputs)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            context,
            key=key,
            max_attempts=self.max_attempts,
            intent={"kind": self.kernel.kind},
        )
