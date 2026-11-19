"""One managed multi-array reference and its source/permission boundaries."""

from __future__ import annotations

import copy
import io
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
import requests
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests.adapters import BaseAdapter
from urllib3.response import HTTPResponse

from linker_engine.engine import Engine
from linker_engine.planning.assets import Asset, Assets
from linker_engine.planning.canonical import decode_object, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import (
    InvalidInput,
    LeaseLost,
)
from linker_engine.planning.execution_registry import ExecutionRegistry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.pvgis_reference_artifacts import prepare_reference_asset
from linker_engine.planning.pvgis_reference_download import ReferenceCapture
from linker_engine.planning.pvgis_reference_geometry import (
    _canonical_derived_angle,
    reference_plan,
)
from linker_engine.planning.pvgis_reference_http import PvgisReferenceHttp
from linker_engine.planning.pvgis_reference_inputs import PvgisReferenceInputs
from linker_engine.planning.pvgis_reference_journal import PvgisReferenceJournal
from linker_engine.planning.pvgis_reference_kernel import PvgisRoofReferenceKernel
from linker_engine.planning.pvgis_reference_profile import (
    prepared_reference_profile,
    reference_bundle,
    reference_dependencies,
)
from linker_engine.planning.pvgis_reference_service import PvgisRoofReferenceService
from linker_engine.planning.pvgis_reference_transport import PvgisReferenceTransport
from linker_engine.planning.pvgis_request import PvgisRequest
from linker_engine.planning.pvgis_response import PvgisCapture
from linker_engine.planning.records import Actor, Project
from linker_engine.planning.weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
)
from linker_engine.planning.weather_fetch_plan import WeatherFetchLimits
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.publication import Publication

from .conftest import Clock, FixtureObject, json_object
from .panel_fixture import panel_basis, panel_parameters
from .test_energy_kernel import TOLERANCE
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_equipment import prepared_dc_fixture_source
from .test_official_weather import Reply
from .test_private_http import TOKEN, headers
from .test_pv_generation import geometry
from .test_pvgis import raw
from .test_pvgis import request as sample_request
from .test_weather_deadline import SLOW_BODY


def limits() -> WeatherFetchLimits:
    # Isolated operational test budgets, not provider or engineering limits.
    return WeatherFetchLimits(
        max_response_bytes=8_000_000,
        max_metadata_bytes=100_000,
        max_weather_rows=9000,
        connect_timeout_seconds=5,
        read_timeout_seconds=20,
        max_elapsed_seconds=60,
    )


def settings() -> FixtureObject:
    return {
        "schema_version": 1,
        "model": "pvgis_5_3_roof_ac_reference_v1",
        "radiation_database": "PVGIS-ERA5",
        "year": 2020,
        "pv_technology": "crystSi",
        "mounting_place": "free",
        "system_loss_percent": 14,
        "use_terrain_horizon": True,
    }


class Captures:
    def __init__(self, *, transient_second: bool = False) -> None:
        self.requests: list[PvgisRequest] = []
        self.deadlines: list[float] = []
        self.byte_limits: list[int] = []
        self.transient_second, self.closed = transient_second, False

    def close(self) -> None:
        self.closed = True

    def download(
        self,
        request: PvgisRequest,
        limits: WeatherFetchLimits,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> ReferenceCapture:
        guard()
        self.requests.append(request)
        self.deadlines.append(deadline)
        self.byte_limits.append(limits.max_response_bytes)
        if self.transient_second and len(self.requests) == 2:
            raise WeatherProviderUnavailable("synthetic transient second-array failure")
        # Reuse the retained JRC response structure. The changed input echoes
        # and linear P scaling are explicitly synthetic transport fixtures.
        document = json_object(decode_object(raw()))
        inputs = document["inputs"]
        inputs["location"].update(
            latitude=request.latitude_deg, longitude=request.longitude_deg
        )
        inputs["meteo_data"].update(
            radiation_db=request.radiation_database,
            year_min=request.start_year,
            year_max=request.end_year,
            use_horizon=request.use_terrain_horizon,
        )
        inputs["pv_module"].update(
            technology="c-Si",
            peak_power=request.peak_power_kwp,
            system_loss=request.system_loss_percent,
        )
        fixed = inputs["mounting_system"]["fixed"]
        fixed["slope"]["value"] = request.tilt_deg
        fixed["azimuth"]["value"] = request.azimuth_north_clockwise_deg - 180
        for row in document["outputs"]["hourly"]:
            row["P"] *= request.peak_power_kwp
        return ReferenceCapture(
            encode(document),
            PvgisCapture(
                schema_version=1,
                requested_url=request.url,
                loaded_url=request.url,
                status=200,
                content_type="application/json",
                received_at_utc="2026-10-28T00:00:00Z",
                capture_basis="official_jrc_https_get_original_v1",
                source_identifiers={"provider": "EC_JRC_PVGIS", "api_version": "5.3"},
            ),
        )


def fixture_inputs() -> FixtureObject:
    layout = geometry()
    layout["module_specs"] = [{**panel_parameters()["specification"], "id": "module"}]
    first = layout["arrays"][0]
    first.update(rows=2, columns=5, excluded_slots=[], mount_tilt_deg=10)
    second = copy.deepcopy(first)
    second.update(
        id="other", name="Second synthetic array", origin_uv=[10, 2], mount_tilt_deg=30
    )
    layout["arrays"].append(second)
    return {"geometry": layout, "pvgis_reference": settings()}


def prepared_reference_fixture(
    workspace: Workspace,
    owner: Actor,
    products: ProductSources,
    *,
    export_permission: str = "permitted",
) -> tuple[Project, Asset]:
    """Reuse the exact producer artifact for consumer tests, without a PV replay."""
    basis = panel_basis()
    values = fixture_inputs()
    values["geometry"]["sources"][0]["permissions"]["export"] = export_permission
    project = workspace.create(
        owner, "Synthetic reference consumer", values, key="reference-consumer"
    )
    plan = reference_plan(values, workspace.blobs.put_object(basis), limits(), 20_000)
    source = Captures()
    captures = [
        source.download(
            a.request, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
        for a in plan.arrays
    ]
    publication, _ = prepare_reference_asset(
        workspace.blobs, project.id, 1, values, basis, plan, captures
    )
    asset = Assets(workspace).add(
        owner,
        project.id,
        workspace.blobs.read(publication.content_sha256),
        publication.media_type,
        publication.purpose,
        workspace.blobs.object(publication.metadata_sha256),
        key="reference-source",
    )
    return project, asset


def test_known_pv_without_geometry_uses_site_and_publishes_consumable_ac_reference(
    client: TestClient,
    workspace: Workspace,
    owner: Actor,
    engine: Engine,
    equipment_feed: FixtureObject,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from linker_engine.planning.equipment_search_kernel import EquipmentSearchKernel
    from linker_engine.planning.equipment_search_limits import EquipmentSearchLimits
    from linker_engine.planning.equipment_service import EquipmentService
    from linker_engine.planning.frozen_profiles import frozen_profile
    from linker_engine.planning.profile_assets import profile_dependencies
    from linker_engine.planning.profile_selections import check_profile_selections

    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    values: FixtureObject = {
        "brief": {
            "schema_version": 1,
            "project_use": "residential",
            "system_scope": "storage_addition",
            "site": {
                "country_code": "NL",
                "location_label": "Declared existing PV site",
                "latitude": 52.12567,
                "longitude": 5.12567,
                "coordinate_basis": "user_entered",
                "timezone": "Europe/Amsterdam",
            },
            "annual_load": {"kwh": None, "basis": None, "source_note": ""},
            "project_note": "",
        },
        "pvgis_reference": {
            **settings(),
            "model": "pvgis_5_3_known_ac_reference_v1",
            "source_note": "Commissioning report for location and system losses",
            "arrays": [
                {
                    "id": "existing",
                    "peak_power_kwp": 6.4,
                    "tilt_deg": 31.25,
                    "azimuth_north_clockwise_deg": 172.5,
                    "source_note": "Existing PV commissioning report",
                }
            ],
        },
    }
    source = Captures()
    kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: source,
    )
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    _, search_products, _, _, _, _ = prepared_dc_fixture_source(
        equipment_feed, engine, monkeypatch
    )
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace,
            search_products,
            EquipmentSearchLimits(work_budget=5000),
            tolerance=TOLERANCE,
            max_intervals=9000,
        ),
        max_attempts=1,
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 100_000, 10, 32),
        product_provider=client.app.state.planning_product_provider,
        pvgis_reference=PvgisRoofReferenceService(workspace, kernel, max_attempts=1),
        equipment_search=search,
    )
    with TestClient(app) as admission:
        create_body: FixtureObject = {
            "schema_version": 1,
            "title": "Known PV without drawing",
            "inputs": values,
            "key": "known-pv",
            "input_contract": "known_pv_ac_reference_v1",
        }
        invalid = copy.deepcopy(create_body)
        invalid["inputs"]["pvgis_reference"]["arrays"][0]["peak_power_kwp"] = 0
        rejected = admission.post(
            "/projects/create", json=invalid, headers=headers(owner)
        )
        assert rejected.status_code == 422, rejected.text
        blank_source = copy.deepcopy(create_body)
        blank_source["inputs"]["pvgis_reference"]["source_note"] = " \t "
        rejected_blank = admission.post(
            "/projects/create", json=blank_source, headers=headers(owner)
        )
        assert rejected_blank.status_code == 422, rejected_blank.text
        created = admission.post(
            "/projects/create", json=create_body, headers=headers(owner)
        )
        assert created.status_code == 200, created.text
        project = workspace.get(owner, created.json()["id"])
        assert project.inputs == values
        stale_writer = admission.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": 1,
                "inputs": {"brief": values["brief"]},
                "key": "stale-writer",
            },
            headers=headers(owner),
        )
        assert stale_writer.status_code == 422, stale_writer.text
        assert stale_writer.json()["error"]["code"] == "project_input_contract_required"
        command = {
            "schema_version": 1,
            "project_id": project.id,
            "expected_revision": 1,
            "key": "known-reference",
        }
        admitted = admission.post(
            "/runs/pvgis-reference", json=command, headers=headers(owner)
        )
        assert admitted.status_code == 200, admitted.text
        assert (
            admission.post(
                "/runs/pvgis-reference", json=command, headers=headers(owner)
            ).json()
            == admitted.json()
        )
        replayed = admission.post(
            "/operations/replay/runs/pvgis-reference",
            json=command,
            headers=headers(owner),
        )
        assert replayed.json()["result"] == admitted.json()
    assert not source.requests
    registry = ExecutionRegistry(kernel)
    worker = Worker(
        Jobs(workspace),
        "known-reference",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once()
    finished = workspace.run(owner, admitted.json()["id"])
    assert finished.state == "succeeded", finished.error
    result = json_object(finished.result)
    asset = Assets(workspace).get(owner, project.id, result["prepared_asset"]["id"])
    assert asset.purpose == "pvgis_known_ac_reference_profile_v1"
    assert (
        "geometry_sha256" not in asset.metadata
        and "woo_module_inputs" not in asset.metadata
    )
    assert asset.metadata["basis"] == "customer_declared"
    assert [
        (
            r.latitude_deg,
            r.longitude_deg,
            r.peak_power_kwp,
            r.tilt_deg,
            r.azimuth_north_clockwise_deg,
        )
        for r in source.requests
    ] == [(52.12567, 5.12567, 6.4, 31.25, 172.5)]
    adopted = {
        **values,
        "profile_selections": {
            "schema_version": 1,
            "selected": {"pv_available_ac": asset.id},
        },
    }
    check_profile_selections(Assets(workspace), owner, project.id, adopted)
    pinned = profile_dependencies(asset, "pv_available_ac", adopted, workspace.blobs)
    profile = frozen_profile(
        workspace.blobs,
        pinned["pv_available_ac.raw"],
        pinned["pv_available_ac.metadata"],
        None,
    )
    assert profile.total_kwh == pytest.approx(946.43692 * 6.4, abs=1e-8)
    assert len(profile.intervals) == 8784
    changed = copy.deepcopy(adopted)
    changed["brief"]["site"]["latitude"] = 51.0
    with pytest.raises(InvalidInput):
        profile_dependencies(asset, "pv_available_ac", changed, workspace.blobs)
    assert "geometry" not in workspace.get(owner, project.id).inputs
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.project_input_contracts import KNOWN_PV_INPUT_CONTRACT

    from .test_energy_kernel import PROVENANCE, mapping

    assets = Assets(workspace)
    load = ProfileImport(assets).csv(
        owner,
        project.id,
        b"time,power\n2020-01-01T00:00:00Z,2\n2020-01-01T01:00:00Z,2\n",
        mapping("gross_load"),
        PROVENANCE,
        key="known-load",
    )
    scenario_path = (
        Path(__file__).resolve().parents[4]
        / "apps/planner/tests/fixtures/energy-scenario.json"
    )
    scenario = json_object(decode_object(scenario_path.read_bytes()))
    scenario["aux_ac_kw"] = 0
    scenario["schedule"][0].update(
        start_utc="2020-01-01T00:00:00Z", end_utc="2020-01-01T02:00:00Z"
    )
    energy_inputs = {
        **adopted,
        "profile_selections": {
            "schema_version": 1,
            "selected": {"gross_load": load.id, "pv_available_ac": asset.id},
        },
        "energy_scenario": scenario,
    }
    with TestClient(app) as admission:
        calculation = admission.post(
            "/runs/calculate",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "input_contract": KNOWN_PV_INPUT_CONTRACT,
                "inputs": energy_inputs,
                "key": "known-energy",
            },
            headers=headers(owner),
        )
        assert calculation.status_code == 200, calculation.text
    energy_receipt = calculation.json()
    replay_project = workspace.get(owner, project.id)
    assert (
        energy_receipt["project"]["inputs"]["profile_selections"]
        == energy_inputs["profile_selections"]
    )
    energy_registry = ExecutionRegistry(energy.kernel)
    replay_worker = Worker(
        Jobs(workspace),
        "known-energy",
        {"evaluate": energy_registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=energy_registry.routing(8),
    )
    assert replay_worker.run_once()
    replayed_energy = workspace.run(owner, energy_receipt["run"]["id"])
    assert replayed_energy.state == "succeeded", replayed_energy.error
    declarations = {
        **adopted,
        "profile_selections": {
            "schema_version": 1,
            "selected": {"gross_load": load.id, "pv_available_ac": asset.id},
        },
        "equipment_setup": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": None,
            "required_usable_kwh": None,
            "required_discharge_ac_kw": None,
        },
        "energy_scenario": {
            "controller": "self_consumption_with_reserve_v1",
            "battery": None,
            "schedule": scenario["schedule"],
        },
    }
    search_registry = ExecutionRegistry(search.kernel)
    search_worker = Worker(
        Jobs(workspace),
        "known-compare",
        {"evaluate": search_registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=search_registry.routing(8),
    )
    with TestClient(app) as admission:
        comparison = admission.post(
            "/runs/find-equipment",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": replay_project.revision,
                "input_contract": KNOWN_PV_INPUT_CONTRACT,
                "inputs": declarations,
                "key": "known-compare",
            },
            headers=headers(owner),
        )
        assert comparison.status_code == 200, comparison.text
        receipt = comparison.json()
        assert (
            receipt["project"]["inputs"]["profile_selections"]
            == declarations["profile_selections"]
        )
        assert search_worker.run_once()
        run = admission.post(
            "/runs/read",
            json={"schema_version": 1, "run_id": receipt["run"]["id"]},
            headers=headers(owner),
        ).json()
        assert run["state"] == "succeeded", run
        comparison_result = run["result"]["search"]
        assert comparison_result["candidates"]
        assert comparison_result["demand"]["baseline"]["load_kwh"] == 4
        assert (
            run["manifest"]["context"]["assets"]["pv_available_ac.raw"]
            == asset.content_sha256
        )

    from linker_engine.planning.report_inputs import ReportOptions
    from linker_engine.planning.report_model import build_report
    from linker_engine.planning.report_sources import report_sources

    options = ReportOptions(
        locale="en",
        pv_run_id=finished.id,
        energy_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    report_source = report_sources(workspace, products, owner, project, options)
    note_inputs = json_object(copy.deepcopy(project.inputs))
    note_inputs["brief"]["project_note"] = "Customer updated a project note"
    note_inputs["brief"]["annual_load"]["kwh"] = 12000
    note_project = workspace.revise(
        owner,
        project.id,
        receipt["project"]["revision"],
        note_inputs,
        key="known-unrelated-brief",
        input_contract=KNOWN_PV_INPUT_CONTRACT,
    )
    assert report_sources(workspace, products, owner, note_project, options)[
        "pvgis_known_ac_references"
    ]
    energy_options = options.model_copy(update={"energy_run_id": replayed_energy.id})
    energy_report_source = report_sources(
        workspace, products, owner, replay_project, energy_options
    )
    assert energy_report_source["pvgis_known_ac_references"]
    for locale in ("en", "de"):
        model = build_report({**report_source, "locale": locale})
        section = next(s for s in model.sections if s.id == "pvgis-known-reference-0")
        assert any("6.4" in row.value or "6,4" in row.value for row in section.rows)
        assert any("31.25" in row.value or "31,25" in row.value for row in section.rows)
        assert any("Commissioning report" in row.value for row in section.rows)
        assert all(
            s.table is None or not s.table.rows
            for s in model.sections
            if s.id == "pv-components"
        )


@pytest.mark.parametrize("mode", ["known-site", "imported-roof", "capacity-only"])
def test_comparison_prepares_pv_and_finishes_after_the_client_disconnects(
    client: TestClient,
    workspace: Workspace,
    owner: Actor,
    engine: Engine,
    equipment_feed: FixtureObject,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    from linker_engine.planning.equipment_search_kernel import EquipmentSearchKernel
    from linker_engine.planning.equipment_search_limits import EquipmentSearchLimits
    from linker_engine.planning.equipment_service import EquipmentService
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.project_input_contracts import KNOWN_PV_INPUT_CONTRACT
    from linker_engine.planning.report_inputs import ReportOptions
    from linker_engine.planning.report_sources import (
        ReportInputsChanged,
        report_sources,
    )

    from .test_energy_kernel import PROVENANCE, mapping

    known = mode != "imported-roof"
    _, products, _, _, _, _ = prepared_dc_fixture_source(
        equipment_feed, engine, monkeypatch
    )
    source = Captures()
    pv = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: source,
    )
    search = EquipmentSearchKernel(
        workspace,
        products,
        EquipmentSearchLimits(work_budget=5000),
        tolerance=TOLERANCE,
        max_intervals=9000,
        pvgis_reference=pv,
    )
    assert isinstance(client.app, FastAPI)
    app = create_private_app(
        workspace,
        EnergyService(
            workspace,
            EnergyKernel(workspace, TOLERANCE, max_intervals=9000),
            max_attempts=1,
        ),
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 100_000, 10, 32),
        product_provider=client.app.state.planning_product_provider,
        equipment_search=EquipmentService(workspace, search, max_attempts=2),
        pvgis_reference=PvgisRoofReferenceService(workspace, pv, max_attempts=2),
    )
    values = (
        fixture_inputs()
        if not known
        else {
            "pvgis_reference": {
                **settings(),
                "model": "pvgis_5_3_known_ac_reference_v1",
                "source_note": "Installer's original model settings",
                "arrays": [
                    {
                        "id": "existing",
                        "peak_power_kwp": 6.4,
                        "tilt_deg": 31.25,
                        "azimuth_north_clockwise_deg": 172.5,
                        "source_note": "Existing module list",
                    }
                ],
            },
        }
    )
    # Use an excluded third roof array to verify that roof power and requests use placed modules only.
    if not known:
        excluded = copy.deepcopy(values["geometry"]["arrays"][0])
        excluded.update(
            id="excluded",
            excluded_slots=[f"{r}:{c}" for r in range(2) for c in range(5)],
        )
        values["geometry"]["arrays"].append(excluded)
    values["brief"] = {
        "schema_version": 1,
        "project_use": "residential",
        "system_scope": "new_pv_storage",
        "site": {
            "country_code": "NL",
            "location_label": "Installer site",
            "latitude": 52.12567,
            "longitude": 5.12567,
            "coordinate_basis": "user_entered",
            "timezone": "Europe/Amsterdam",
        },
        "annual_load": {"kwh": None, "basis": None, "source_note": ""},
        "project_note": "",
    }
    with TestClient(app) as browser:
        create = browser.post(
            "/projects/create",
            json={
                "schema_version": 1,
                "title": "New comparison",
                "inputs": {},
                "key": "compare-project",
            },
            headers=headers(owner),
        )
        assert create.status_code == 200, create.text
        project_id = create.json()["id"]
        load = ProfileImport(Assets(workspace)).csv(
            owner,
            project_id,
            b"time,power\n2020-06-01T12:00:00Z,2\n2020-06-01T13:00:00Z,2\n",
            mapping("gross_load"),
            PROVENANCE,
            key="compare-load",
        )
        values.update(
            profile_selections={
                "schema_version": 1,
                "selected": {"gross_load": load.id},
            },
            equipment_setup={
                "schema_version": 1,
                "grid_phase": 3,
                "operating_mode": "grid_connected",
                "pv_dc_kw": 9.0,
            },
            energy_scenario={
                "controller": "self_consumption_with_reserve_v1",
                "battery": None,
                "schedule": [
                    {
                        "mode": "connected",
                        "pv_enabled": True,
                        "start_utc": "2020-06-01T12:00:00Z",
                        "end_utc": "2020-06-01T14:00:00Z",
                    }
                ],
            },
        )
        if mode == "capacity-only":
            declared = values.pop("pvgis_reference")
            declared["arrays"][0].update(peak_power_kwp=10, tilt_deg=None)
            values["pvgis_reference_setup"] = declared
            values["brief"]["system_scope"] = "pv_only"
            values["equipment_setup"]["pv_dc_kw"] = None
            values["geometry"] = fixture_inputs()["geometry"]
            del values["profile_selections"]
        command = {
            "schema_version": 1,
            "project_id": project_id,
            "expected_revision": 1,
            "input_contract": KNOWN_PV_INPUT_CONTRACT,
            "inputs": values,
            "key": "compare-pv",
        }
        reply = browser.post(
            "/runs/find-equipment", json=command, headers=headers(owner)
        )
        assert reply.status_code == 200, reply.text
        receipt = reply.json()
        run_id = receipt["run"]["id"]
        assert receipt["run"]["state"] == "queued"
        assert receipt["project"]["revision"] == 2
        if mode == "capacity-only":
            registry = ExecutionRegistry(search, pv)
            worker = Worker(
                Jobs(workspace),
                "capacity-only",
                {"evaluate": registry},
                lease_seconds=30,
                heartbeat_seconds=1,
                retry_seconds=1,
                routing=registry.routing(8),
            )
            assert worker.run_once()
            result = browser.post(
                "/runs/read",
                json={"schema_version": 1, "run_id": run_id},
                headers=headers(owner),
            ).json()
            assert result["state"] == "succeeded", result
            assert "prepared_asset" not in result["result"]
            candidates = result["result"]["search"]["candidates"]
            assert candidates
            assert {row["selection"]["pv_dc_kw"] for row in candidates} == {10}
            assert not source.requests
            selected = candidates[0]
            adopted = workspace.revise(
                owner,
                project_id,
                2,
                {
                    **values,
                    "equipment_selection": selected["selection"],
                    "equipment_candidate": {
                        "run_id": run_id,
                        "candidate_id": selected["id"],
                        "assessment_sha256": selected["assessment_sha256"],
                    },
                },
                key="adopt-capacity-only",
                input_contract=KNOWN_PV_INPUT_CONTRACT,
            )
            options = ReportOptions(
                locale="en",
                energy_run_id=None,
                pv_run_id=None,
                equipment_run_id=None,
                logo=None,
            )
            assert (
                report_sources(workspace, products, owner, adopted, options)[
                    "pv_components"
                ]
                is None
            )
            return
        assert (
            "pv_available_ac"
            not in receipt["project"]["inputs"]["profile_selections"]["selected"]
        )
        edited = copy.deepcopy(values)
        edited["brief"]["site"]["latitude"] = 51.5
        revision = browser.post(
            "/projects/revise",
            json={
                **command,
                "expected_revision": 2,
                "inputs": edited,
                "key": "edit-while-queued",
            },
            headers=headers(owner),
        )
        assert revision.status_code == 200, revision.text
    assert not source.requests
    registry = ExecutionRegistry(search, pv)
    worker = Worker(
        Jobs(workspace),
        "compare-pv",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once()
    with TestClient(app) as reopened:
        replay = reopened.post(
            "/operations/replay/runs/find-equipment",
            json=command,
            headers=headers(owner),
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["result"]["project"] == receipt["project"]
        assert replay.json()["result"]["run"]["id"] == run_id
        request = {"schema_version": 1, "run_id": run_id}
        result = reopened.post(
            "/runs/read", json=request, headers=headers(owner)
        ).json()
        assert result["state"] == "succeeded", result
        assert result["revision"] == 2
        assert result["is_current"] is False
        assert receipt["project"]["inputs"]["equipment_setup"]["pv_dc_kw"] == 9.0
        frozen = reopened.post(
            "/runs/inputs",
            json={**request, "project_id": project_id},
            headers=headers(owner),
        )
        assert frozen.status_code == 200, frozen.text
        expected_power = (
            6.4
            if known
            else values["geometry"]["module_specs"][0]["stc_power_w"] * 20 / 1000
        )
        assert frozen.json()["inputs"]["equipment_requirements"][
            "pv_dc_kw"
        ] == pytest.approx(expected_power)
        assert result["result"]["search"]["demand"]["baseline"]["load_kwh"] == 4
        assert result["result"]["search"]["demand"]["baseline"]["pv_available_kwh"] > 0
        prepared = result["result"]["prepared_asset"]
        assert prepared["purpose"] == (
            "pvgis_known_ac_reference_profile_v1"
            if known
            else "pvgis_roof_ac_reference_profile_v1"
        )
        asset = reopened.post(
            "/assets/read",
            json={
                "schema_version": 1,
                "project_id": project_id,
                "asset_id": prepared["id"],
            },
            headers=headers(owner),
        )
        assert asset.status_code == 200, asset.text
        assert asset.json()["content_sha256"] == prepared["content_sha256"]
        assert (
            reopened.post(
                "/runs/read",
                json=request,
                headers=headers(Actor("user", "another-owner")),
            ).status_code
            == 404
        )
    candidate = result["result"]["search"]["candidates"][0]
    adopted = workspace.revise(
        owner,
        project_id,
        3,
        {
            **values,
            "equipment_selection": candidate["selection"],
            "equipment_candidate": {
                "run_id": run_id,
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        },
        key="adopt-pv-comparison",
        input_contract=KNOWN_PV_INPUT_CONTRACT,
    )
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=run_id,
        equipment_run_id=None,
        logo=None,
    )
    report = report_sources(workspace, products, owner, adopted, options)
    references = json_object(report)[
        "pvgis_known_ac_references" if known else "pvgis_roof_ac_references"
    ]
    assert references[0]["asset_id"] == prepared["id"]
    assert references[0]["used_by"][0]["run_id"] == run_id
    changed = json_object(copy.deepcopy(adopted.inputs))
    if known:
        changed["brief"]["site"]["latitude"] = 51.5
    else:
        changed["geometry"]["arrays"][0]["excluded_slots"] = ["0:0"]
    stale = workspace.revise(
        owner,
        project_id,
        adopted.revision,
        changed,
        key="edit-adopted-pv",
        input_contract=KNOWN_PV_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged):
        report_sources(workspace, products, owner, stale, options)
    if known:
        assert [(r.latitude_deg, r.peak_power_kwp) for r in source.requests] == [
            (52.12567, 6.4)
        ]
    else:
        module_watts = values["geometry"]["module_specs"][0]["stc_power_w"]
        assert [r.peak_power_kwp for r in source.requests] == [module_watts / 100] * 2


def test_managed_reference_freezes_both_arrays_and_refuses_stale_or_partial_use(
    client: TestClient,
    workspace: Workspace,
    owner: Actor,
    clock: Clock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    withdrawn = False

    def current(publication: Publication) -> FixtureObject:
        value = publication_manifest(publication.feed)
        for product in value["products"]:
            product["ready"]["engineering"] = True
        if withdrawn:
            value["products"] = [
                p
                for p in value["products"]
                if p.get("engineering_role") != "reference_pv_module"
            ]
        return value

    monkeypatch.setattr(Publication, "read", current)
    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    basis = panel_basis()
    values = fixture_inputs()
    assert "source_note" not in values["pvgis_reference"]
    assert PvgisReferenceInputs.read(values["pvgis_reference"]).source_note is None
    for optional_note in (None, "", " \t\n"):
        variant = {**values["pvgis_reference"], "source_note": optional_note}
        assert PvgisReferenceInputs.read(variant).source_note is None
    assert (
        PvgisReferenceInputs.read(
            {**values["pvgis_reference"], "source_note": " note \t"}
        ).source_note
        == " note \t"
    )
    layout = values["geometry"]
    source = Captures()
    kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: source,
    )
    project = workspace.create(
        owner, "Synthetic multi-array reference", values, key="roof"
    )
    plan = reference_plan(values, workspace.blobs.put_object(basis), limits(), 20_000)
    assert sum(a.module_count for a in plan.arrays) == 20
    expected_kwp = 20 * layout["module_specs"][0]["stc_power_w"] / 1000
    assert sum(a.request.peak_power_kwp for a in plan.arrays) == expected_kwp
    # The actual ENU atan2 conversion of the second mount produces
    # 29.999999999999996; JRC echoes the equivalent requested slope as 30.
    assert [a.request.tilt_deg for a in plan.arrays] == [10, 30]
    # Two binary steps away from 30 is beyond the canonicalization allowance.
    assert _canonical_derived_angle(30.000000000000007) == 30.000000000000007
    tampered = copy.deepcopy(values)
    tampered["geometry"]["module_specs"][0]["stc_power_w"] += 1
    assert kernel.context(tampered) != kernel.context(values)
    service = PvgisRoofReferenceService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 100_000, 10, 32),
        product_provider=client.app.state.planning_product_provider,
        pvgis_reference=service,
    )
    body = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": project.revision,
        "key": "reference",
    }
    with TestClient(app) as admission:
        version = admission.post(
            "/version", json={"schema_version": 1}, headers=headers(owner)
        )
        assert version.status_code == 200
        assert version.json()["models"]["pvgis_roof_reference"] == kernel.kind
        admitted = admission.post(
            "/runs/pvgis-reference", json=body, headers=headers(owner)
        )
        assert admitted.status_code == 200, admitted.text
        assert (
            admission.post(
                "/runs/pvgis-reference", json=body, headers=headers(owner)
            ).json()
            == admitted.json()
        )
        replay = admission.post(
            "/operations/replay/runs/pvgis-reference", json=body, headers=headers(owner)
        )
        assert replay.status_code == 200
        assert replay.json()["schema_version"] == 1
        assert replay.json()["status"] == "replayed"
        assert replay.json()["result"] == admitted.json()
        foreign = admission.post(
            "/runs/pvgis-reference",
            json=body,
            headers=headers(Actor("user", "wordpress:18")),
        )
        assert foreign.status_code == 404
    run = workspace.run(owner, admitted.json()["id"])
    assert source.requests == []  # HTTP admission has not called a provider.
    registry = ExecutionRegistry(kernel)
    worker = Worker(
        Jobs(workspace),
        "reference",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once()
    finished = workspace.run(owner, run.id)
    assert finished.state == "succeeded", finished.error
    result = json_object(finished.result)
    asset = Assets(workspace).get(owner, project.id, result["prepared_asset"]["id"])
    profile = prepared_reference_profile(
        workspace.blobs, asset.content_sha256, asset.metadata
    )
    assert profile.total_kwh == pytest.approx(946.43692 * expected_kwp, abs=1e-8)
    assert len(profile.intervals) == 8784 and profile.measurement == "pv_available_ac"
    assert profile.reconstructed_means is False and source.closed
    bundle = json_object(
        reference_bundle(workspace.blobs, asset.content_sha256, asset.metadata)
    )
    assert len(bundle["manifest"]["arrays"]) == 2
    assert bundle["parameters"] == values["pvgis_reference"]
    assert len(reference_dependencies(asset, values, workspace.blobs)) == 9
    for changed in ["geometry", "pvgis_reference"]:
        altered = copy.deepcopy(values)
        if changed == "geometry":
            altered[changed]["arrays"][0]["excluded_slots"] = ["0:0"]
        else:
            altered[changed]["year"] = 2021
        with pytest.raises(InvalidInput):
            reference_dependencies(asset, altered, workspace.blobs)
    bad = Captures(transient_second=True)
    bad_kernel = PvgisRoofReferenceKernel(
        workspace,
        products,
        limits(),
        max_array_steps=20_000,
        transport_factory=lambda: bad,
    )
    bad_run = PvgisRoofReferenceService(workspace, bad_kernel, max_attempts=2).evaluate(
        owner, project.id, 1, key="bad"
    )
    bad_registry = ExecutionRegistry(bad_kernel)
    bad_worker = Worker(
        Jobs(workspace),
        "bad",
        {"evaluate": bad_registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=bad_registry.routing(8),
    )
    assert bad_worker.run_once()
    assert workspace.run(owner, bad_run.id).state == "retry_wait"
    assert workspace.run(owner, bad_run.id).result is None
    with workspace.database.read() as db:
        journal_sha = db.execute(
            "SELECT output_sha256 FROM jobs WHERE run_id=?", (bad_run.id,)
        ).fetchone()[0]
        assert (
            db.execute(
                "SELECT COUNT(*) FROM project_assets WHERE project_id=?", (project.id,)
            ).fetchone()[0]
            == 1
        )
    retained = json_object(workspace.blobs.object(journal_sha))
    assert list(retained["arrays"]) == ["0"]
    assert retained["arrays"]["0"]["validated"] is True
    first_raw = retained["arrays"]["0"]["raw_sha256"]
    first_capture = retained["arrays"]["0"]["capture_sha256"]
    used = len(workspace.blobs.read(first_raw))
    assert retained["consumed_bytes"] == used
    assert bad.byte_limits == [
        limits().max_response_bytes,
        limits().max_response_bytes - used,
    ]
    clock.advance(1)
    assert bad_worker.run_once()
    resumed = workspace.run(owner, bad_run.id)
    assert resumed.state == "succeeded", resumed.error
    resumed_asset = json_object(json_object(resumed.result)["prepared_asset"])
    resumed_metadata = resumed_asset["metadata"]
    acquisition = resumed_metadata["acquisition"]
    assert [r.tilt_deg for r in bad.requests] == [10, 30, 30]
    assert bad.deadlines == [retained["deadline_at"]] * 3
    assert bad.byte_limits[2] == limits().max_response_bytes - used
    assert acquisition["started_at"] == retained["started_at"]
    assert acquisition["deadline_at"] == retained["deadline_at"]
    assert acquisition["arrays"]["0"]["raw_sha256"] == first_raw
    assert acquisition["arrays"]["0"]["capture_sha256"] == first_capture
    assert acquisition["consumed_bytes"] == sum(
        len(workspace.blobs.read(row["raw_sha256"]))
        for row in acquisition["arrays"].values()
    )
    assert (
        resumed_metadata["interpretation"]["energy_kwh"]
        == json_object(asset.metadata["interpretation"])["energy_kwh"]
    )
    # One two-byte rejected response proves quarantine/fencing, without a
    # further annual replay or provider request.
    rejected = service.evaluate(owner, project.id, 1, key="invalid-original")
    lease = Jobs(workspace).claim(
        "quarantine", kinds=("evaluate",), lease_seconds=30, routing=registry.routing(8)
    )
    assert lease is not None and lease.run_id == rejected.id
    journal = PvgisReferenceJournal(workspace, lease, plan)
    journal.begin()
    invalid_original = ReferenceCapture(
        b"{}", PvgisCapture.read(workspace.blobs.object(first_capture))
    )
    journal.retain(0, invalid_original)
    with pytest.raises(WeatherResponseInvalid):
        journal.validate(0, invalid_original)
    quarantined = json_object(journal.current())
    assert quarantined["arrays"]["0"]["validated"] is False
    assert quarantined["arrays"]["0"]["failure"] == "response_validation_failed"
    assert workspace.blobs.read(quarantined["arrays"]["0"]["raw_sha256"]) == b"{}"
    with pytest.raises(WeatherResponseInvalid):
        journal.captured(0)
    assert workspace.run(owner, rejected.id).result is None
    Jobs(workspace).fail(
        lease,
        {"code": "weather_response_invalid", "retryable": False},
        retry_after=None,
    )
    with pytest.raises(LeaseLost):
        journal.retain(0, invalid_original)
    withdrawn = True
    products.check_profile(asset.metadata)
    assert (
        prepared_reference_profile(
            workspace.blobs, asset.content_sha256, asset.metadata
        ).total_kwh
        == profile.total_kwh
    )


class ReferenceAdapter(BaseAdapter):
    def __init__(self, reply: Reply) -> None:
        self.reply = reply

    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        assert request.url and "/api/v5_3/seriescalc?" in request.url
        assert request.method == "GET" and stream is True and verify is not False
        assert (
            "Authorization" not in request.headers and "Cookie" not in request.headers
        )
        response = requests.Response()
        response.status_code = self.reply.status
        response.url = self.reply.loaded_url or request.url
        response.headers.update(self.reply.headers)
        response.raw = HTTPResponse(
            body=io.BytesIO(self.reply.body), preload_content=False
        )
        return response

    def close(self) -> None:
        pass


def test_official_reference_transfer_retains_bytes_and_refuses_redirects() -> None:
    req = sample_request()
    transfer = PvgisReferenceHttp(ReferenceAdapter(Reply(200, raw())))
    captured = transfer.download(
        req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
    )
    assert captured.content == raw()
    wire = (
        encode({"schema_version": 1, "capture": captured.capture.document()})
        + b"\n"
        + captured.content
    )
    assert PvgisReferenceTransport._result(req, limits(), wire).content == raw()
    with pytest.raises(WeatherProviderRejected):
        PvgisReferenceHttp(ReferenceAdapter(Reply(302, b"redirect"))).download(
            req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
    with pytest.raises(WeatherResponseInvalid):
        PvgisReferenceHttp(
            ReferenceAdapter(
                Reply(200, raw(), loaded_url="https://foreign.invalid/seriescalc")
            )
        ).download(req, limits(), deadline=60, clock=lambda: 0, guard=lambda: None)
    transfer.close()


def test_reference_supervision_cancels_and_reaps_only_its_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def observe(command: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        assert not any(
            k in kwargs["env"] for k in ["APIFY_TOKEN", "GENIE_SERVICE_TOKEN"]
        )
        child: subprocess.Popen[bytes] = original(
            [sys.executable, "-c", SLOW_BODY], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe)
    start = time.monotonic()

    def guard() -> None:
        if time.monotonic() - start > 0.10:
            raise LeaseLost("synthetic revoked owner")

    with pytest.raises(LeaseLost):
        PvgisReferenceTransport().download(
            sample_request(),
            limits(),
            deadline=time.time() + 5,
            clock=time.time,
            guard=guard,
        )
    assert len(children) == 1 and children[0].returncode is not None
