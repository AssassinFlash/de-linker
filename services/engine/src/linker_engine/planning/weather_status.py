"""Owned source status is readable even if fresh acquisition is disabled."""

from .canonical import Object
from .errors import NotFound
from .records import Actor
from .weather_journal import WeatherJournal
from .weather_kernel import WeatherKernel
from .workspace import Workspace


def weather_status(workspace: Workspace, actor: Actor, run_id: str) -> Object:
    run = workspace.run(actor, run_id)
    context = run.manifest.get("context")
    models = context.get("models") if isinstance(context, dict) else None
    if not isinstance(models, dict) or models.get("task") != WeatherKernel.kind:
        raise NotFound("weather task not found")
    return WeatherJournal(workspace).view(actor, run_id, allow_not_started=True)
