"""Actual browser preparation output passes the native saved-source boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.pv_preparation import (
    PvPreparationService,
    PvReferenceKernel,
)
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .test_energy_kernel import TOLERANCE
from .test_private_http import TOKEN, headers
from .test_pv_profile import LIMITS, PROVENANCE
from .test_pvgis_tmy import capture, interpretation, raw, request

APP = Path(__file__).resolve().parents[4] / "apps" / "planner"


def test_replacing_selected_weather_can_be_saved_after_browser_preparation(
    workspace: Workspace, owner: Actor
) -> None:
    fixture = json.loads((APP / "tests/fixtures/preparation-flow.json").read_text())
    original = fixture["weather_project"]["inputs"]
    project = workspace.create(
        owner, "Synthetic browser save fixture", original, key="new"
    )
    assets = Assets(workspace)
    source = WeatherImport(assets, LIMITS).tmy(
        owner,
        project.id,
        PvSource(raw(), request(), capture(), interpretation(), encode(PROVENANCE)),
        key="original-weather",
    )
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **original,
            "pv_preparation": {"schema_version": 1, "weather_asset_id": source.id},
            "unrelated": "preserved",
        },
        key="select-original",
    )
    prepared = cast(
        Object,
        json.loads(
            subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "--eval",
                    """
import { readSolarSetup, solarInputs, prepareWeatherInputs } from './src/domain/solarSetup.ts';
let text = ''; for await (const chunk of process.stdin) text += chunk;
const inputs = JSON.parse(text), setup = readSolarSetup(inputs);
const changed = solarInputs(inputs, {...setup, weather: {...setup.weather,
  request: {...setup.weather.request, use_terrain_horizon: true}}});
process.stdout.write(JSON.stringify(prepareWeatherInputs(changed)));
""",
                ],
                input=json.dumps(project.inputs),
                text=True,
                capture_output=True,
                check=True,
                cwd=APP,
                timeout=10,
            ).stdout
        ),
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
        max_attempts=2,
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(16777216, 8388608, 100, 32),
    )
    with TestClient(app) as client:
        saved = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "replacement-weather",
                "inputs": prepared,
            },
            headers=headers(owner),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == project.revision + 1
        assert "pv_preparation" not in saved.json()["inputs"]
        assert saved.json()["inputs"]["unrelated"] == "preserved"
        assert assets.get(owner, project.id, source.id) == source
        assert workspace.get(owner, project.id, revision=project.revision) == project

        # The native binding remains strict; reattaching A to request B is refused.
        refused = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision + 1,
                "key": "mismatched-old-selection",
                "inputs": {
                    **prepared,
                    "pv_preparation": project.inputs["pv_preparation"],
                },
            },
            headers=headers(owner),
        )
        assert refused.status_code == 422
        assert workspace.get(owner, project.id).revision == project.revision + 1


def test_browser_pv_preparation_saves_and_executes_the_frozen_model(
    workspace: Workspace, owner: Actor
) -> None:
    fixture = json.loads((APP / "tests/fixtures/preparation-flow.json").read_text())
    original = cast(Object, fixture["pv_project"]["inputs"])
    original.pop("pv_preparation")
    original["unrelated"] = "preserved"
    project = workspace.create(
        owner, "Synthetic browser PV fixture", original, key="pv"
    )
    assets = Assets(workspace)
    source = WeatherImport(assets, LIMITS).tmy(
        owner,
        project.id,
        PvSource(raw(), request(), capture(), interpretation(), encode(PROVENANCE)),
        key="original-weather",
    )
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **original,
            "pv_preparation": {"schema_version": 1, "weather_asset_id": source.id},
        },
        key="select-weather",
    )
    prepared = cast(
        Object,
        json.loads(
            subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "--eval",
                    """
import { readSolarSetup, solarInputs, preparePvInputs, checkPvWeather } from './src/domain/solarSetup.ts';
let text = ''; for await (const chunk of process.stdin) text += chunk;
const inputs = JSON.parse(text), setup = readSolarSetup(inputs);
// Same displayed-% to model-fraction boundary as the actual module form.
const pv = {...setup.pv, modules: setup.pv.modules.map(module => ({...module,
    gamma_pdc_per_c: -0.29 / 100}))};
const prepared = preparePvInputs(solarInputs(inputs, {...setup, pv}));
checkPvWeather(prepared);
process.stdout.write(JSON.stringify(prepared));
""",
                ],
                input=json.dumps(project.inputs),
                text=True,
                capture_output=True,
                check=True,
                cwd=APP,
                timeout=10,
            ).stdout
        ),
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
        max_attempts=2,
    )
    pv = PvPreparationService(
        workspace, PvReferenceKernel(workspace, LIMITS), max_attempts=2
    )
    registry = ExecutionRegistry(energy.kernel, pv.kernel)
    with TestClient(
        create_private_app(
            workspace,
            energy,
            credential=lambda: TOKEN,
            limits=HttpLimits(16777216, 8388608, 100, 32),
            pv=pv,
        )
    ) as client:
        saved = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "prepared-pv",
                "inputs": prepared,
            },
            headers=headers(owner),
        )
        assert saved.status_code == 200, saved.text
        revision = saved.json()["revision"]
        assert revision == project.revision + 1
        assert saved.json()["inputs"]["unrelated"] == "preserved"
        assert (
            saved.json()["inputs"]["pv_generation"]["modules"][0]["gamma_pdc_per_c"]
            == -0.0029
        )
        command: Object = {
            "schema_version": 1,
            "project_id": project.id,
            "expected_revision": revision,
            "key": "browser-pv",
        }
        queued = client.post("/runs/pv", json=command, headers=headers(owner))
        assert queued.status_code == 200, queued.text
        run_id = queued.json()["id"]
        assert queued.json()["state"] == "queued"
        assert queued.json()["revision"] == revision
        assert (
            client.post(
                "/runs/pv",
                json={**command, "pv_generation": {}},
                headers=headers(owner),
            ).status_code
            == 422
        )
        assert Worker(
            Jobs(workspace),
            "browser-pv",
            {"evaluate": registry},
            lease_seconds=30,
            heartbeat_seconds=1,
            retry_seconds=1,
            routing=registry.routing(8),
        ).run_once()
        completed = client.post(
            "/runs/read",
            json={"schema_version": 1, "run_id": run_id},
            headers=headers(owner),
        )
        assert completed.status_code == 200
        result = completed.json()
        assert result["state"] == "succeeded", result
        assert result["result"]["revision"] == revision
        assert result["result"]["profile_summary"]["interval_count"] == 8760
        assert result["result"]["profile_summary"]["energy_kwh"] > 0
        assert result["result"]["equipment_release"]["status"] == "not_assessed"
        assert assets.get(owner, project.id, source.id) == source
        assert workspace.get(owner, project.id, revision=project.revision) == project
        retry = client.post("/runs/pv", json=command, headers=headers(owner))
        assert retry.status_code == 200 and retry.json()["id"] == run_id
