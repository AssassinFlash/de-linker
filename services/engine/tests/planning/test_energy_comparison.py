"""One short original-result comparison, ownership and frozen report path.

Reuses the existing two-hour analytic sources; no annual/PV simulation or new
manufacturer dataset. The third result changes the reserve requirement to
exercise the actual misleading-delta refusal.
"""

from __future__ import annotations

import copy
import io
from typing import Never

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_brief import incomplete_brief
from .test_energy_kernel import BATTERY, PROVENANCE, TOLERANCE, create_scenario
from .test_private_http import TOKEN, headers


@pytest.mark.parametrize(
    "fixture_name", ["plant-energy-run.json", "dc-plant-energy-run.json"]
)
def test_joint_comparison_report_keeps_list_periods_and_named_final_requirements(
    fixture_name: str,
) -> None:
    """Read the retained native fixture; do not replay its physical calculation."""
    import json
    from pathlib import Path

    from linker_engine.planning.comparison_report import comparison_sections
    from linker_engine.planning.dc_plant_inputs import DcPlantEnergyInputs
    from linker_engine.planning.energy_comparison import EnergyComparisonSide
    from linker_engine.planning.plant_energy_inputs import PlantEnergyInputs
    from linker_engine.planning.records import Run
    from linker_engine.planning.report_model import number

    fixture = json.loads(
        (
            Path(__file__).resolve().parents[4]
            / "apps/planner/tests/fixtures"
            / fixture_name
        ).read_text()
    )
    run = Run(**fixture["run"])
    scenario = (
        DcPlantEnergyInputs if fixture_name.startswith("dc-") else PlantEnergyInputs
    ).from_project(fixture["project"]["inputs"])
    # A presentation-only declared final requirement distinguishes it from None.
    scenario = scenario.model_copy(
        update={
            "units": [
                scenario.units[0].model_copy(update={"terminal_min_kwh": 2}),
                *scenario.units[1:],
            ]
        }
    )
    side = EnergyComparisonSide(
        run, json_object(run.result), fixture["project"]["inputs"], scenario
    )
    reference = json_object(side.reference())
    assert isinstance(reference["operating_periods"], list)
    sections = comparison_sections(
        {
            "baseline": reference,
            "candidate": reference,
            "conditions_aligned": False,
            "metrics": [],
            "conditions": [],
            "differences": [],
        },
        "en",
        number,
    )
    assert any(
        row.label.endswith("Minimum final stored energy") and row.value == "2 kWh"
        for row in sections[1].rows
    )


def test_saved_comparison_keeps_original_conditions_and_publishes_report(
    workspace: Workspace, owner: Actor
) -> None:
    p = create_scenario(workspace, owner)
    brief = incomplete_brief()
    brief["site"].update(
        country_code="FR",
        timezone="Europe/Paris",
        location_label="Original comparison site A",
    )
    p = workspace.revise(
        owner, p.id, p.revision, {**p.inputs, "brief": brief}, key="comparison-site"
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )

    def no_product_lookup() -> Never:
        raise AssertionError("isolated numeric comparison must not invent a Woo source")

    reports = ReportService(
        workspace,
        ReportKernel(workspace, ProductSources(no_product_lookup)),
        max_attempts=1,
    )
    registry = service_registry(energy, None, None, None, None, reports)
    worker = Worker(
        Jobs(workspace),
        "comparison-worker",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    baseline = energy.evaluate(owner, p.id, p.revision, key="comparison-baseline")
    assert worker.run_once()
    battery = Assets(workspace).add(
        owner,
        p.id,
        encode({**BATTERY, "eta_charge": 0.8, "eta_discharge": 0.8}),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": PROVENANCE},
        key="comparison-storage",
    )
    inputs = json_object(copy.deepcopy(p.inputs))
    inputs["energy_replay"]["battery_parameters_asset_id"] = battery.id
    p = workspace.revise(owner, p.id, p.revision, inputs, key="comparison-design")
    candidate = energy.evaluate(owner, p.id, p.revision, key="comparison-candidate")
    assert worker.run_once()
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        reports=reports,
        product_provider=no_product_lookup,
    )
    auth = {
        **headers(),
        "X-Linker-Planner-Principal-Kind": owner.kind,
        "X-Linker-Planner-Principal-Subject": owner.subject,
    }
    command = {
        "schema_version": 1,
        "project_id": p.id,
        "baseline_run_id": baseline.id,
        "candidate_run_id": candidate.id,
    }
    with TestClient(app) as client:
        assert client.post("/runs/compare", json=command).status_code == 401
        response = client.post("/runs/compare", json=command, headers=auth)
        assert response.status_code == 200, response.text
        comparison = response.json()
        assert comparison["conditions_aligned"] is True
        rows = {row["id"]: row for row in comparison["metrics"]}
        assert rows["grid_import"]["delta"] == pytest.approx(0.34)
        assert rows["stored_final"]["baseline"] == pytest.approx(0)
        assert comparison["differences"][0] == {
            "id": "storage_parameters",
            "changed": True,
        }
        assert (
            client.post(
                "/runs/compare",
                json={**command, "candidate_run_id": baseline.id},
                headers=auth,
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/runs/compare",
                json=command,
                headers={**auth, "X-Linker-Planner-Principal-Subject": "other-owner"},
            ).status_code
            == 404
        )
        # The stored requirement conflict remains a readable original result;
        # it cannot generate a claimed performance delta.
        different = json_object(copy.deepcopy(p.inputs))
        different["energy_replay"]["schedule"][0]["reserve_kwh"] = 1
        different["brief"]["site"]["location_label"] = "Current head-only site B"
        p = workspace.revise(
            owner, p.id, p.revision, different, key="comparison-requirements"
        )
        conflict = energy.evaluate(owner, p.id, p.revision, key="comparison-conflict")
        assert worker.run_once()
        blocked = client.post(
            "/runs/compare",
            json={**command, "candidate_run_id": conflict.id},
            headers=auth,
        )
        assert blocked.status_code == 200, blocked.text
        assert blocked.json()["conditions_aligned"] is False
        assert all(row["delta"] is None for row in blocked.json()["metrics"])
        options: FixtureObject = {
            "locale": "en",
            "energy_run_id": None,
            "pv_run_id": None,
            "equipment_run_id": None,
            "logo": None,
        }
        # Absent and explicit-empty additive options preserve old receipts.
        assert json_object(ReportOptions.read(options).intent())[
            "options_sha256"
        ] == digest(encode(options))
        assert json_object(
            ReportOptions.read({**options, "comparison": None}).intent()
        ) == json_object(ReportOptions.read(options).intent())
        accepted = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": p.id,
                "expected_revision": p.revision,
                "key": "comparison-report",
                "options": {
                    **options,
                    "comparison": {
                        "baseline_run_id": baseline.id,
                        "candidate_run_id": candidate.id,
                    },
                },
            },
            headers=auth,
        )
        assert accepted.status_code == 200, accepted.text
        assert worker.run_once()
        report = workspace.run(owner, accepted.json()["id"])
        assert report.state == "succeeded", report.error
        source = json_object(
            workspace.blobs.object(
                json_object(report.result)["pinned_assets"]["report.source"]
            )
        )
        assert source["comparison"] == comparison
        assert source["energy"] is None and source["candidate"] is None
        assert source["brief"] is None
        assert (
            comparison["baseline"]["site"]["location_label"]
            == comparison["candidate"]["site"]["location_label"]
            == "Original comparison site A"
        )
        pdf = Assets(workspace).content(
            owner, p.id, json_object(report.result)["prepared_asset"]["id"]
        )
        text = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages
        )
        assert "Saved calculation comparison" in text and "0.34 kWh" in text
        assert (
            "Original comparison site A" in text
            and "Current head-only site B" not in text
        )
        assert (
            workspace.run(owner, baseline.id).result_sha256
            == comparison["baseline"]["result_sha256"]
        )
