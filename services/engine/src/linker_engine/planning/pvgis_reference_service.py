"""HTTP admission queues the named reference; acquisition belongs to its worker."""

from .errors import InvalidInput
from .pvgis_reference_kernel import PvgisRoofReferenceKernel
from .records import Actor, Run
from .workspace import Workspace


class PvgisRoofReferenceService:
    def __init__(
        self,
        workspace: Workspace,
        kernel: PvgisRoofReferenceKernel,
        *,
        max_attempts: int,
    ) -> None:
        if workspace is not kernel.workspace:
            raise InvalidInput("roof reference must share project authority")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            self.kernel.context(project.inputs),
            key=key,
            max_attempts=self.max_attempts,
            intent={"kind": self.kernel.kind},
        )
