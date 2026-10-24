"""Export actual worker/publication views for native consumer regression fixtures.

Uses the retained real TMY and explicit synthetic model/roof with a simulated
provider adapter. Never connects to a live service, account, or project store.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from linker_engine.planning.canonical import Object
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_views import project_view, run_view
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_status import weather_status
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_pv_profile import LIMITS, project_with_roof
from .test_weather_kernel import services, source_inputs, valid_adapter, worker


def capture() -> Object:
    with TemporaryDirectory(prefix="p548-preparation-fixture-") as directory:
        workspace = Workspace(Path(directory), clock=Clock())
        owner = Actor("user", "native-preparation-synthetic-fixture")
        project = project_with_roof(workspace, owner)
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            {**project.inputs, **source_inputs()},
            key="weather-inputs",
        )
        adapter = valid_adapter()
        weather, energy = services(workspace, adapter)
        pv = PvPreparationService(
            workspace, PvReferenceKernel(workspace, LIMITS), max_attempts=2
        )
        registry = service_registry(energy, pv, weather)
        weather_run = weather.evaluate(
            owner, project.id, project.revision, key="acquire"
        )
        assert worker(workspace, registry).run_once()
        completed = workspace.run(owner, weather_run.id)
        assert completed.result is not None
        asset = completed.result["prepared_asset"]
        assert isinstance(asset, dict) and isinstance(asset["id"], str)
        selected = workspace.revise(
            owner,
            project.id,
            project.revision,
            {
                **project.inputs,
                "pv_preparation": {
                    "schema_version": 1,
                    "weather_asset_id": asset["id"],
                },
            },
            key="select-weather",
        )
        pv_run = pv.evaluate(owner, project.id, selected.revision, key="prepare-pv")
        assert worker(workspace, registry).run_once()
        finished = workspace.run(owner, pv_run.id)
        assert completed.state == finished.state == "succeeded"
        assert len(adapter.calls) == 5
        return {
            "schema_version": 1,
            "provider_responses": "simulated; no external request",
            "weather_run": run_view(completed),
            "pv_run": run_view(finished),
            "weather_project": project_view(project),
            "pv_project": project_view(selected),
            "weather_status": weather_status(workspace, owner, weather_run.id),
        }


if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parents[4]
        / "apps/planner/tests/fixtures/preparation-flow.json"
    )
    target.write_text(json.dumps(capture(), ensure_ascii=False, indent=2) + "\n")
    print(target)
