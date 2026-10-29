"""Actual browser preparation output passes the native saved-source boundary."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

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
from linker_engine.planning.runtime_snapshot import RuntimeSnapshot
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from . import export_preparation_fixture
from .test_energy_kernel import TOLERANCE
from .test_private_http import TOKEN, headers
from .test_pv_profile import LIMITS, PROVENANCE
from .test_pvgis_tmy import capture, interpretation, raw, request

APP = Path(__file__).resolve().parents[4] / "apps" / "planner"


def preparation_fixture() -> dict[str, Any]:
    name = f"preparation-flow-{sys.platform}-{platform.machine()}.json"
    return cast(dict[str, Any], json.loads((APP / "tests/fixtures" / name).read_text()))


HOST_DERIVED_FIXTURE_PATHS = frozenset(
    {
        ("geometric_pv", "profile_asset", "content_sha256"),
        ("geometric_pv", "profile_asset", "metadata", "dependencies", "model.witness"),
        ("geometric_pv", "profile_asset", "metadata_sha256"),
        ("geometric_pv", "profile_preview", "content_sha256"),
        ("geometric_pv", "profile_preview", "metadata_sha256"),
        ("geometric_pv", "profile_preview_initial", "content_sha256"),
        ("geometric_pv", "profile_preview_initial", "metadata_sha256"),
        (
            "geometric_pv",
            "report_run",
            "manifest",
            "context",
            "assets",
            "report.source",
        ),
        ("geometric_pv", "report_run", "manifest_sha256"),
        (
            "geometric_pv",
            "report_run",
            "result",
            "dependencies",
            "prepared_asset_content",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "dependencies",
            "prepared_asset_metadata",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "dependencies",
            "prepared_attachment.bill_of_materials_csv.metadata",
        ),
        ("geometric_pv", "report_run", "result", "dependencies", "report_model"),
        ("geometric_pv", "report_run", "result", "dependencies", "report_source"),
        ("geometric_pv", "report_run", "result", "manifest_sha256"),
        ("geometric_pv", "report_run", "result", "pinned_assets", "report.source"),
        ("geometric_pv", "report_run", "result", "prepared_asset", "content_sha256"),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_asset",
            "metadata",
            "dependencies",
            "report_model",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_asset",
            "metadata",
            "dependencies",
            "report_source",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_asset",
            "metadata",
            "report_model_sha256",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_asset",
            "metadata_sha256",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_attachments",
            "bill_of_materials_csv",
            "metadata",
            "dependencies",
            "report_model",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_attachments",
            "bill_of_materials_csv",
            "metadata",
            "dependencies",
            "report_source",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "prepared_attachments",
            "bill_of_materials_csv",
            "metadata_sha256",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "report",
            "sections",
            1,
            "rows",
            35,
            "value",
        ),
        ("geometric_pv", "report_run", "result", "report_sha256"),
        (
            "geometric_pv",
            "report_run",
            "result",
            "source_runs",
            0,
            "manifest_sha256",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "source_runs",
            0,
            "result_sha256",
        ),
        (
            "geometric_pv",
            "report_run",
            "result",
            "source_runs",
            1,
            "result_sha256",
        ),
        ("geometric_pv", "report_run", "result_sha256"),
        ("geometric_pv", "report_run_assistant", "runs", 0, "manifest_sha256"),
        ("geometric_pv", "report_run_assistant", "runs", 0, "result_sha256"),
        ("geometric_pv", "report_run_assistant", "runs", 0, "rows", 34, "value"),
        ("geometric_pv", "run", "result", "dependencies", "model.witness"),
        (
            "geometric_pv",
            "run",
            "result",
            "dependencies",
            "prepared_asset_content",
        ),
        (
            "geometric_pv",
            "run",
            "result",
            "dependencies",
            "prepared_asset_metadata",
        ),
        (
            "geometric_pv",
            "run",
            "result",
            "prepared_asset",
            "content_sha256",
        ),
        (
            "geometric_pv",
            "run",
            "result",
            "prepared_asset",
            "metadata",
            "dependencies",
            "model.witness",
        ),
        (
            "geometric_pv",
            "run",
            "result",
            "prepared_asset",
            "metadata_sha256",
        ),
        ("geometric_pv", "run", "result_sha256"),
        ("geometric_pv", "run_assistant", "runs", 0, "result_sha256"),
        ("pv_run", "result", "dependencies", "prepared_asset_metadata"),
        ("pv_run", "result", "dependencies", "pv_model_witness"),
        (
            "pv_run",
            "result",
            "prepared_asset",
            "metadata",
            "dependencies",
            "pv_model_witness",
        ),
        ("pv_run", "result", "prepared_asset", "metadata_sha256"),
        ("pv_run", "result_sha256"),
    }
)


def host_invariant_view(node: Any, path: tuple[str | int, ...] = ()) -> Any:
    """Replace only the fixture paths proven to depend on exact host arithmetic."""
    if path in HOST_DERIVED_FIXTURE_PATHS:
        return "<host-derived>"
    if isinstance(node, dict):
        return {
            key: host_invariant_view(value, (*path, key)) for key, value in node.items()
        }
    if isinstance(node, list):
        return [
            host_invariant_view(value, (*path, index))
            for index, value in enumerate(node)
        ]
    return node


def test_replacing_selected_weather_can_be_saved_after_browser_preparation(
    workspace: Workspace, owner: Actor
) -> None:
    fixture = preparation_fixture()
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
    fixture = preparation_fixture()
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
import { fromPercent } from './src/domain/decimal.ts';
let text = ''; for await (const chunk of process.stdin) text += chunk;
const inputs = JSON.parse(text), setup = readSolarSetup(inputs);
// Same displayed-% to model-fraction boundary as the actual module form.
const pv = {...setup.pv, modules: setup.pv.modules.map(module => ({...module,
    gamma_pdc_per_c: fromPercent(-0.29)}))};
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


def test_preparation_fixture_export_reproduces_the_committed_fixture() -> None:
    """The committed browser fixture matches this host on every stable field.

    Same-host repeated exports are byte-identical. Across hosts, only the paths
    proven to depend on exact AC/DC arithmetic are masked; source/input identity
    and every other field remain exact. That identity is not this machine's live
    snapshot.
    """
    committed = preparation_fixture()
    produced = export_preparation_fixture.capture()
    assert set(produced) == set(committed) == set(EXPECTED_FIXTURE_KEYS)
    assert host_invariant_view(produced) == host_invariant_view(committed)
    pinned = export_preparation_fixture.fixture_runtime_snapshot()
    live = RuntimeSnapshot.capture()
    assert pinned.sha256 != live.sha256
    weather_run = cast(Object, produced["weather_run"])
    manifest = cast(Object, weather_run["manifest"])
    context = cast(Object, manifest["context"])
    assert context["code_sha256"] == pinned.sha256
    # The browser package owns this file's whitespace: it formats its own JSON
    # with Prettier, which may expand a short array or break a long string.
    # Whatever that formatting did, it changed no saved value, so re-reading
    # the committed bytes must yield exactly the document the exporter produced.
    assert json.loads(export_preparation_fixture.rendered()) == produced


def test_preparation_platform_manifest_names_each_export() -> None:
    """Each host baseline is a complete document with the recorded canonical hash."""
    manifest_path = APP / "tests/fixtures/preparation-flow-platforms.json"
    manifest = json.loads(manifest_path.read_text())
    baselines = cast(dict[str, Object], manifest["baselines"])
    for host, baseline in baselines.items():
        fixture = json.loads(
            (manifest_path.parent / cast(str, baseline["fixture"])).read_text()
        )
        canonical = json.dumps(fixture, sort_keys=True, ensure_ascii=False).encode()
        assert (
            hashlib.sha256(canonical).hexdigest()
            == baseline["canonical_sorted_json_sha256"]
        ), host


# Every top-level key the browser fixture carries, produced by the exporter.
EXPECTED_FIXTURE_KEYS = frozenset(
    {
        "schema_version",
        "provider_responses",
        "weather_run",
        "pv_run",
        "weather_project",
        "pv_project",
        "weather_status",
        "pvgis_reference_run",
        "pvgis_reference_project",
        "direct_beam",
        "geometric_pv",
    }
)
