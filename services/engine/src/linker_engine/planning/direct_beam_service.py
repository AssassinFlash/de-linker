"""Owned geometric-witness admission; an exact receipt precedes fresh source reads."""

from . import commands
from .access import positive_integer, project_row
from .canonical import Object
from .direct_beam_job import DirectBeamKernel
from .errors import InvalidInput, VersionUnavailable
from .records import Actor, Run
from .workspace import Workspace


class DirectBeamService:
    def __init__(
        self, workspace: Workspace, kernel: DirectBeamKernel, *, max_attempts: int
    ) -> None:
        if kernel.workspace is not workspace:
            raise InvalidInput("direct-beam job must share project authority")
        positive_integer(max_attempts, "maximum attempts")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

    def evaluate(
        self, actor: Actor, project_id: str, expected_revision: int, *, key: str
    ) -> Run:
        positive_integer(expected_revision, "expected revision")
        intent: Object = {"kind": self.kernel.kind}
        command = commands.command_hash(
            {"expected_revision": expected_revision, "intent": intent}, key
        )
        with self.workspace.database.read() as connection:
            project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection,
                self.workspace.blobs,
                actor,
                f"evaluate:{project_id}",
                key,
                command,
            )
        if receipt is not None:
            # Acknowledging this frozen run is not a fresh product permission
            # or calculation. Native run ownership is checked again on read.
            run = self.workspace.run(actor, commands.receipt_string(receipt, "run_id"))
            if run.project_id != project_id or run.revision != expected_revision:
                raise VersionUnavailable("direct-beam receipt differs from its request")
            return run
        project = self.workspace.get(actor, project_id, revision=expected_revision)
        return self.workspace.evaluate(
            actor,
            project_id,
            expected_revision,
            self.kernel.context(actor, project_id, project.inputs),
            key=key,
            max_attempts=self.max_attempts,
            intent=intent,
        )
