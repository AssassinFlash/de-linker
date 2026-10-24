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
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.records import Actor
from linker_engine.planning.weather_import import WeatherImport
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
