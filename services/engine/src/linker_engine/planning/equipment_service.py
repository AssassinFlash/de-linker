"""Owned durable command for one proposed equipment configuration."""

from __future__ import annotations

from .equipment_kernel import EquipmentKernel
from .errors import InvalidInput
from .records import Actor, Run
from .workspace import Workspace


class EquipmentService:
    def __init__(
        self, workspace: Workspace, kernel: EquipmentKernel, *, max_attempts: int
    ) -> None:
        if workspace is not kernel.workspace:
            raise InvalidInput("equipment qualification must share project authority")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

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
