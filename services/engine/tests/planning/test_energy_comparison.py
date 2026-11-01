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


def test_geometric_weather_identity_follows_verified_frozen_inputs(
    workspace: Workspace,
    owner: Actor,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Before/after roof and wiring changes retain one actual weather source."""
    from dataclasses import replace
    from types import SimpleNamespace
    from typing import Any, cast

    from conftest import publication_manifest
    from fastapi import FastAPI

    from linker_engine.planning.canonical import Object
    from linker_engine.planning.energy_comparison import (
        EnergyComparisonSide,
        _weather_key,
    )
    from linker_engine.planning.errors import VersionUnavailable
    from linker_engine.planning.frozen_documents import FrozenDocuments
    from linker_engine.planning.geometric_pv_generation import generate_geometric_pv
    from linker_engine.planning.geometric_pv_inputs import (
        ELECTRICAL_V3,
        MODEL_ROLES,
        MODEL_V3,
        PROFILE_PURPOSE,
        GeometricPvInputs,
    )
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.pv_weather import WeatherSeries
    from linker_engine.publication import Publication

    from .test_equipment import inputs as equipment_inputs
    from .test_geometric_pv import perez_parameters, perez_request, wide_policy
    from .test_pv_generation import geometry, weather

    def current(publication: Publication) -> dict[str, Any]:
        value = publication_manifest(publication.feed)
        for row in value["products"]:
            row["ready"]["engineering"] = True
        return value

    monkeypatch.setattr(Publication, "read", current)
    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    provider = client.app.state.planning_product_provider()
    feed = provider.publication.feed
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    basis = products.electrical_module_basis()
    equipment = products.equipment_basis()
    equipment["pv_module_inputs"] = basis
    template = cast(dict[str, Any], basis["module"])
    geo = geometry()
    geo["module_specs"] = [{**template["specification"], "id": "module"}]
    geo["arrays"][0].update(rows=1, columns=6, excluded_slots=[], origin_uv=[10, 10])
    ids = [pose.id for pose in panel_poses(read_geometry(geo)) if pose.included]
    selection = equipment_inputs(feed, 3)["equipment_selection"]
    selection["pv_dc_kw"] = 2.76
    wiring = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "minimum_ambient_c": None,
        "temperature_source": None,
        "strings": [{"id": "s1", "mppt": 1, "input": 1, "module_ids": ids}],
    }
    project_inputs = {
        "equipment_selection": selection,
        "pv_string_plan": wiring,
        "equipment_plant": None,
        "pv_plant_string_plan": None,
    }
    parameters = perez_parameters()
    parameters["modules"] = [{**template["parameters"], "module_spec_id": "module"}]
    original = perez_request(parameters)
    series_parameters = copy.deepcopy(parameters)
    series_parameters["converters"][0]["input_assumption"] = (
        "one_string_per_tracker_independent_mpp_sum"
    )
    series = GeometricPvInputs.read(
        {
            **original.model_dump(mode="json"),
            "model": MODEL_V3,
            "electrical_policy": ELECTRICAL_V3,
            "parameters": series_parameters,
        }
    )
    meteo = weather(dni=600, dhi=200, ghi=700, temp=25)
    raw_weather = workspace.blobs.put(b"declared one-hour weather source")
    meteo = replace(meteo, source=replace(meteo.source, raw_sha256=raw_weather))
    metadata_sha = workspace.blobs.put_object({})
    basis_sha = workspace.blobs.put_object(basis)
    equipment_sha = workspace.blobs.put_object(equipment)

    def side(raw: str, metadata: Object) -> EnergyComparisonSide:
        return cast(
            EnergyComparisonSide,
            SimpleNamespace(
                scenario=None,
                dc=False,
                pinned={
                    "pv_available_ac.raw": raw,
                    "pv_available_ac.metadata": workspace.blobs.put_object(metadata),
                },
            ),
        )

    def frozen(
        layout: dict[str, Any],
        request: GeometricPvInputs,
        climate: WeatherSeries,
        electrical: dict[str, Any],
    ) -> EnergyComparisonSide:
        is_series = request.model == MODEL_V3
        result = generate_geometric_pv(
            layout,
            climate,
            request,
            wide_policy(),
            max_weather_rows=10,
            electrical_inputs=electrical if is_series else None,
            electrical_basis=equipment if is_series else None,
        )
        dependencies: Object = {
            "model.inputs": workspace.blobs.put(result.inputs_json),
            "model.witness": workspace.blobs.put(result.witness_json),
            "weather.raw": climate.source.raw_sha256,
            "weather.metadata": metadata_sha,
            "woo.module_inputs": basis_sha,
            "project.parameters": workspace.blobs.put_object(
                request.model_dump(mode="json")
            ),
            **({"woo.equipment_inputs": equipment_sha} if is_series else {}),
        }
        manifest = workspace.blobs.put_object(
            {"schema_version": 1, "kind": request.model, "dependencies": dependencies}
        )
        metadata: Object = {
            "schema": 1,
            "profile_type": PROFILE_PURPOSE,
            "retention": "permanent",
            "provenance": PROVENANCE,
            "interpretation": {
                "start_utc": result.profile.intervals[0].start.isoformat(),
                "end_utc": result.profile.intervals[-1].end.isoformat(),
                "interval_count": len(result.profile.intervals),
                "energy_kwh": result.profile.total_kwh,
                "measurement": "pv_available_ac",
                "origin": "modelled",
                "native_max_interval_seconds": climate.source.native_max_interval_seconds,
                "reconstructed_means": True,
                "model_role": MODEL_ROLES[request.model],
            },
            "weather": {
                "interval_count": len(climate.points),
                "start_utc": climate.points[0].interval.start.isoformat(),
                "end_utc": climate.points[-1].interval.end.isoformat(),
                "weather_document_sha256": digest(encode(climate.document())),
            },
            "dependencies": dependencies,
            "parameters_sha256": dependencies["project.parameters"],
            "geometry_sha256": digest(encode(layout)),
            "woo_module_inputs": basis,
            **({"woo_equipment_inputs": equipment} if is_series else {}),
        }
        return side(manifest, metadata)

    # The first pair uses identical roof and weather, but different electrical models.
    baseline = frozen(geo, original, meteo, project_inputs)
    candidate = frozen(geo, series, meteo, project_inputs)
    shaded = copy.deepcopy(geo)
    shaded["obstacles"] = [
        {
            "id": "wall",
            "name": "South wall",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[0, 8], [20, 8], [20, 9], [0, 9]],
            "extrusion_axis_enu": [0, 0, 1],
            "height_m": 8,
        }
    ]
    changed_wiring = copy.deepcopy(project_inputs)
    changed_wiring["pv_string_plan"]["strings"][0]["module_ids"] = list(reversed(ids))
    revised = frozen(shaded, series, meteo, changed_wiring)
    other_raw = workspace.blobs.put(b"a different one-hour weather source")
    other_climate = weather(dni=500, dhi=200, ghi=650, temp=25)
    other_climate = replace(
        other_climate, source=replace(other_climate.source, raw_sha256=other_raw)
    )
    other = frozen(geo, series, other_climate, project_inputs)
    documents = FrozenDocuments(workspace.blobs)
    identity = json_object(_weather_key(workspace, baseline, documents))
    assert (
        baseline.pinned["pv_available_ac.raw"]
        != candidate.pinned["pv_available_ac.raw"]
    )
    assert (
        candidate.pinned["pv_available_ac.raw"] != revised.pinned["pv_available_ac.raw"]
    )
    assert identity == _weather_key(workspace, candidate, documents)
    assert identity == _weather_key(workspace, revised, documents)
    assert identity != _weather_key(workspace, other, documents)
    assert "opaque" not in identity and "opaque" not in json_object(
        _weather_key(workspace, other, documents)
    )

    # Force the same bounded path used by an annual oversized witness. The
    # comparison only needs its verified weather identity, not module arrays.
    projected = FrozenDocuments(workspace.blobs, max_bytes=1)
    projection_calls: list[str] = []
    project_witness = projected.geometric_witness

    def observe_projection(blobs: Any, sha: str) -> Object:
        projection_calls.append(sha)
        return project_witness(blobs, sha)

    monkeypatch.setattr(projected, "geometric_witness", observe_projection)
    assert identity == _weather_key(workspace, candidate, projected)
    assert identity == _weather_key(workspace, revised, projected)
    assert identity != _weather_key(workspace, other, projected)
    assert len(projection_calls) == 3

    # The real comparison consumer must expose deltas only for matching weather.
    from linker_engine.planning.energy_comparison import compare_energy_runs
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.project_input_contracts import (
        ENGINEERING_V10_INPUT_CONTRACT,
    )

    from .test_energy_kernel import mapping

    project = create_scenario(workspace, owner)
    brief = incomplete_brief()
    brief["site"].update(country_code="DE", timezone="Europe/Berlin")
    assets = Assets(workspace)
    load = ProfileImport(assets).csv(
        owner,
        project.id,
        b"time,power\n2020-06-21T12:00:00Z,2\n",
        mapping("gross_load"),
        PROVENANCE,
        key="comparison-hour-load",
    )
    aux = ProfileImport(assets).csv(
        owner,
        project.id,
        b"time,power\n2020-06-21T12:00:00Z,0\n",
        mapping("aux_ac"),
        PROVENANCE,
        key="comparison-hour-aux",
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=products),
        max_attempts=1,
    )
    worker = Worker(
        Jobs(workspace),
        "geometric-weather-comparison",
        {"evaluate": energy.kernel},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
    )

    def energy_run(
        profile: EnergyComparisonSide,
        layout: dict[str, Any],
        request: GeometricPvInputs,
        electrical: dict[str, Any],
        key: str,
    ) -> str:
        nonlocal project
        raw = str(profile.pinned["pv_available_ac.raw"])
        meta = workspace.blobs.object(str(profile.pinned["pv_available_ac.metadata"]))
        asset = assets.add(
            owner,
            project.id,
            workspace.blobs.read(raw),
            "application/json",
            PROFILE_PURPOSE,
            meta,
            key="profile-" + key,
        )
        values = json_object(copy.deepcopy(project.inputs))
        values.update(
            brief=brief,
            geometry=layout,
            geometric_pv_preparation=request.model_dump(mode="json"),
            equipment_selection=electrical["equipment_selection"],
            pv_string_plan=electrical["pv_string_plan"],
        )
        replay = values["energy_replay"]
        replay["gross_load_asset_id"] = load.id
        replay["aux_ac_asset_id"] = aux.id
        replay["pv_available_asset_id"] = asset.id
        replay["schedule"][0]["start_utc"] = "2020-06-21T12:00:00Z"
        replay["schedule"][0]["end_utc"] = "2020-06-21T13:00:00Z"
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            values,
            key="inputs-" + key,
            input_contract=ENGINEERING_V10_INPUT_CONTRACT,
        )
        queued = energy.evaluate(
            owner, project.id, project.revision, key="energy-" + key
        )
        assert worker.run_once()
        completed = workspace.run(owner, queued.id)
        assert completed.state == "succeeded", completed.error
        return completed.id

    before = energy_run(baseline, geo, original, project_inputs, "before")
    after = energy_run(candidate, geo, series, project_inputs, "after")
    changed = energy_run(revised, shaded, series, changed_wiring, "shaded")
    different = energy_run(other, geo, series, project_inputs, "weather")
    for baseline_id, candidate_id in ((before, after), (after, changed)):
        comparison = json_object(
            compare_energy_runs(workspace, owner, project.id, baseline_id, candidate_id)
        )
        checks = {row["id"]: row["status"] for row in comparison["conditions"]}
        assert checks["pv_weather"] == "matched"
        assert comparison["conditions_aligned"] is True
        assert any(row["delta"] is not None for row in comparison["metrics"])
    comparison = json_object(
        compare_energy_runs(workspace, owner, project.id, before, different)
    )
    checks = {row["id"]: row["status"] for row in comparison["conditions"]}
    assert checks["pv_weather"] == "different"
    assert comparison["conditions_aligned"] is False
    assert all(row["delta"] is None for row in comparison["metrics"])

    # The pre-existing pvlib weather format uses the same canonical identity.
    pvlib_inputs = workspace.blobs.put_object({"weather": meteo.document()})
    pvlib = side(
        workspace.blobs.put(b"pvlib profile"),
        {
            "profile_type": "pvlib_reference_profile_v1",
            "dependencies": {"pv_model_inputs": pvlib_inputs},
        },
    )
    assert identity == _weather_key(workspace, pvlib, documents)

    # Unknown profiles remain conservative, and a broken geometric proof fails closed.
    opaque_a = side(
        workspace.blobs.put(b"old profile A"), {"profile_type": "csv_profile_v1"}
    )
    opaque_b = side(
        workspace.blobs.put(b"old profile B"), {"profile_type": "csv_profile_v1"}
    )
    assert json_object(_weather_key(workspace, opaque_a, documents))["opaque"] is True
    assert _weather_key(workspace, opaque_a, documents) != _weather_key(
        workspace, opaque_b, documents
    )
    broken = workspace.blobs.object(str(candidate.pinned["pv_available_ac.metadata"]))
    broken["geometry_sha256"] = "0" * 64
    with pytest.raises(VersionUnavailable, match="differs from frozen sources"):
        _weather_key(
            workspace,
            side(str(candidate.pinned["pv_available_ac.raw"]), broken),
            documents,
        )
