"""Owned acquisition admission; requests queue work without calling a provider."""

from .errors import InvalidInput
from .records import Actor, Run
from .weather_journal import WeatherJournal
from .weather_kernel import WeatherKernel
from .workspace import Workspace


class WeatherService:
    def __init__(
        self, workspace: Workspace, kernel: WeatherKernel, *, max_attempts: int
    ) -> None:
        if kernel.workspace is not workspace:
            raise InvalidInput("weather acquisition must share project authority")
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts
        self.journal = WeatherJournal(workspace)

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
