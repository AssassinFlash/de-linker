"""Real complete retained-weather worker, profile, energy and report consumers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, cast

import pytest
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_calculation_sources import calculation_sources
from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import (
    EvidenceMissing,
    InvalidInput,
    NotFound,
    ProductEvidenceChanged,
    ProjectInputContractRequired,
    VersionUnavailable,
)
from linker_engine.planning.execution_registry import (
    ExecutionRegistry,
    service_registry,
)
from linker_engine.planning.frozen_documents import FrozenDocuments
from linker_engine.planning.geometric_pv_inputs import (
    MODEL_V1,
    MODEL_V2,
    GeometricPvLimits,
)
from linker_engine.planning.geometric_pv_job import GeometricPvKernel
from linker_engine.planning.geometric_pv_profile import (
    prepared_profile,
    reference_bundle,
)
from linker_engine.planning.geometric_pv_report import geometric_pv_reference
from linker_engine.planning.geometric_pv_service import GeometricPvService
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.http_views import asset_view, project_view, run_view
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.profile_assets import profile_dependencies
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.profile_preview import ProfilePreview
from linker_engine.planning.profile_selections import check_profile_selections
from linker_engine.planning.project_input_contracts import (
    DIRECT_BEAM_INPUT_CONTRACT,
    GEOMETRIC_PV_INPUT_CONTRACT,
)
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_pv_components import pv_components
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.publication import Publication

from .test_energy_kernel import BATTERY, TOLERANCE
from .test_energy_kernel import PROVENANCE as SYNTHETIC
from .test_geometric_pv import perez_parameters, perez_request, scenario
from .test_private_http import TOKEN, headers
from .test_pv_generation import geometry, parameter_document
from .test_pv_profile import LIMITS, PROVENANCE
from .test_pvgis_tmy import capture, interpretation, raw
from .test_pvgis_tmy import request as weather_request


def test_owned_complete_weather_to_profile_two_hour_energy_report_and_frozen_read(
    workspace: Workspace,
    owner: Actor,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    withdrawn = False

    def current(publication: Publication) -> dict[str, Any]:
        value = publication_manifest(publication.feed)
        for row in value["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            value["products"] = [
                row
                for row in value["products"]
                if row.get("engineering_role") != "reference_pv_module"
            ]
        return value

    monkeypatch.setattr(Publication, "read", current)
    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    template = products.module_basis()["module"]
    assert isinstance(template, dict)
    geo, par = geometry(), parameter_document()
    specification = template["specification"]
    assert isinstance(specification, dict)
    geo["module_specs"] = [{**specification, "id": "module"}]
    geo["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    parameter = template["parameters"]
    assert isinstance(parameter, dict)
    par["modules"] = [{**parameter, "module_spec_id": "module"}]
    project = workspace.create(
        owner,
        "Actual weather / synthetic one-module geometric scenario",
        {"geometry": geo},
        key="create",
    )
    source = WeatherImport(Assets(workspace), LIMITS).tmy(
        owner,
        project.id,
        PvSource(
            raw(), weather_request(), capture(), interpretation(), encode(PROVENANCE)
        ),
        key="weather",
    )
    options = scenario(par).model_copy(update={"weather_asset_id": source.id})
    project = workspace.revise(
        owner,
        project.id,
        1,
        {**project.inputs, "geometric_pv_preparation": options.model_dump(mode="json")},
        key="parameters",
        input_contract=GEOMETRIC_PV_INPUT_CONTRACT,
    )
    # Full8760 source / one synthetic module / explicit1+2 grids:43800
    # worst-case samples. These limits are this diagnostic's work policy.
    kernel = GeometricPvKernel(
        workspace,
        LIMITS,
        GeometricPvLimits(
            max_module_steps=9000,
            max_samples=45000,
            max_ray_face_checks=1_000_000,
            max_bounds_checks=1_000_000,
            index_leaf_size=2,
        ),
        products=products,
    )
    service = GeometricPvService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    reports = ReportService(
        workspace, ReportKernel(workspace, products), max_attempts=1
    )
    registry = service_registry(energy, None, reports=reports, geometric_pv=service)
    worker = Worker(
        Jobs(workspace),
        "geometric-full-source",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
        routing=registry.routing(1),
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 2, 32),
        product_provider=client.app.state.planning_product_provider,
        geometric_pv=service,
        reports=reports,
    )
    with pytest.raises(NotFound):
        service.evaluate(Actor("user", "foreign"), project.id, 2, key="foreign")
    with TestClient(app) as http:
        command = {
            "schema_version": 1,
            "project_id": project.id,
            "expected_revision": 2,
            "key": "full-geometric",
        }
        reply = http.post("/runs/geometric-pv", json=command, headers=headers(owner))
        assert reply.status_code == 200, reply.text
        run_id = reply.json()["id"]
        assert worker.run_once()
        run = workspace.run(owner, run_id)
        assert run.state == "succeeded", run.error
        assert run.result is not None
        result = run.result
        asset = Assets(workspace).get(
            owner, project.id, str(cast(Object, result["prepared_asset"])["id"])
        )
        profile = prepared_profile(
            workspace.blobs, asset.content_sha256, asset.metadata
        )
        assert len(profile.intervals) == 8760
        assert profile.intervals[0].start.isoformat() == "2023-01-01T00:00:00+00:00"
        assert profile.intervals[-1].end.isoformat() == "2024-01-01T00:00:00+00:00"
        assert cast(Object, asset.metadata["weather"])["interval_count"] == 8760
        # profile_summary carries the exact-model total. The separately stored
        # energy is platform-stable spelled, so comparison uses its bound.
        assert math.isclose(
            float(cast(float, cast(Object, result["profile_summary"])["energy_kwh"])),
            profile.total_kwh,
            rel_tol=2e-9,
            abs_tol=1e-12,
        )
        assert (
            http.post(
                "/operations/replay/runs/geometric-pv",
                json=command,
                headers=headers(owner),
            ).json()["result"]["id"]
            == run_id
        )
    # A read and downstream workers consume the original complete output.
    # A second call to the numerical producer would be a product defect.
    import linker_engine.planning.geometric_pv_job as job

    def no_recompute(*args: Any, **kwargs: Any) -> None:
        pytest.fail("frozen profile/report tried to rerun PV generation")

    monkeypatch.setattr(job, "generate_geometric_pv", no_recompute)
    preview = ProfilePreview(Assets(workspace)).page(
        owner, project.id, asset.id, offset=3995, page_size=2
    )

    # One report reads the same retained artifacts for the profile, the rows and
    # the component list. A shared reader must reach the store once per artifact
    # even though each consumer re-verifies the manifest.
    class CountingBlobs:
        def __init__(self, blobs: Any) -> None:
            self.blobs = blobs
            self.reads: list[str] = []

        def read(self, sha256: str) -> bytes:
            self.reads.append(sha256)
            return cast(bytes, self.blobs.read(sha256))

        def object(self, sha256: str) -> Object:
            raise AssertionError("the shared reader verifies through read")

    store = CountingBlobs(workspace.blobs)
    shared = FrozenDocuments(store)  # type: ignore[arg-type]
    geometric_pv_reference(
        workspace.blobs, asset.content_sha256, asset.metadata, shared
    )
    prepared_profile(workspace.blobs, asset.content_sha256, asset.metadata, shared)
    bundle = reference_bundle(
        workspace.blobs, asset.content_sha256, asset.metadata, shared
    )
    pv_components(
        workspace.blobs,
        asset.content_sha256,
        asset.metadata,
        documents=shared,
        geometric_bundle=bundle,
    )
    dependencies = cast(Object, asset.metadata["dependencies"])
    assert sorted(store.reads) == sorted(
        [asset.content_sha256, *cast(list[str], list(dependencies.values()))]
    )
    with pytest.raises(EvidenceMissing):
        profile_dependencies(asset, "pv_available_dc", project.inputs, workspace.blobs)
    changed = {**project.inputs, "geometry": {}}
    with pytest.raises(InvalidInput):
        profile_dependencies(asset, "pv_available_ac", changed, workspace.blobs)
    with pytest.raises(ProjectInputContractRequired):
        workspace.revise(
            owner,
            project.id,
            2,
            {"geometry": geo},
            key="old-editor",
            input_contract=DIRECT_BEAM_INPUT_CONTRACT,
        )
    tampered = {
        **asset.metadata,
        "interpretation": {
            **cast(Object, asset.metadata["interpretation"]),
            "interval_count": 2,
        },
    }
    with pytest.raises(VersionUnavailable, match="summary"):
        prepared_profile(workspace.blobs, asset.content_sha256, tampered)
    before_project = project_view(project)
    assets = Assets(workspace)
    imported = {}
    for role, power in (("gross_load", 2), ("aux_ac", 0)):
        data = f"time,power\n2023-06-16T11:00:00Z,{power}\n2023-06-16T12:00:00Z,{power}\n".encode()
        imported[role] = (
            ProfileImport(assets)
            .csv(
                owner,
                project.id,
                data,
                CsvMapping(
                    "time",
                    "power",
                    cast(Measurement, role),
                    "interval_average_kw",
                    "start",
                    "UTC",
                    "synthetic",
                    3600,
                    ",",
                    ".",
                ),
                SYNTHETIC,
                key=role,
            )
            .id
        )
    battery = assets.add(
        owner,
        project.id,
        encode(
            {**BATTERY, "usable_window_kwh": 0, "charge_ac_kw": 0, "discharge_ac_kw": 0}
        ),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": SYNTHETIC},
        key="battery",
    )
    project = workspace.revise(
        owner,
        project.id,
        2,
        {
            **project.inputs,
            "profile_selections": {
                "schema_version": 1,
                "selected": {"pv_available_ac": asset.id},
            },
            "energy_replay": {
                "schema_version": 1,
                "gross_load_asset_id": imported["gross_load"],
                "aux_ac_asset_id": imported["aux_ac"],
                "critical_load_asset_id": None,
                "pv_available_asset_id": asset.id,
                "battery_parameters_asset_id": battery.id,
                "initial_inventory": {
                    "pv_kwh": 0,
                    "grid_kwh": 0,
                    "initial_unknown_kwh": 0,
                    "basis": "synthetic_fixture",
                    "source_note": "No battery",
                },
                "schedule": [
                    {
                        "start_utc": "2023-06-16T11:00:00Z",
                        "end_utc": "2023-06-16T13:00:00Z",
                        "mode": "connected",
                        "reserve_kwh": 0,
                        "import_cap_kw": None,
                        "export_cap_kw": None,
                        "pv_enabled": True,
                        "allow_grid_charge": False,
                    }
                ],
                "controller": "self_consumption_with_reserve_v1",
                "terminal_min_kwh": 0,
            },
        },
        key="adopt-and-scenario",
        input_contract=GEOMETRIC_PV_INPUT_CONTRACT,
    )
    check_profile_selections(assets, owner, project.id, project.inputs)
    energy_run = energy.evaluate(owner, project.id, 3, key="energy")
    assert worker.run_once()
    energy_result = workspace.run(owner, energy_run.id)
    assert energy_result.state == "succeeded", energy_result.error
    assert energy_result.result is not None
    metrics = cast(Object, energy_result.result["metrics"])
    selected_pv = sum(profile.values_kw[3995:3997])
    assert metrics["gross_load_kwh"] == 4
    assert metrics["solar_load_kwh"] == pytest.approx(selected_pv, abs=1e-7)
    assert metrics["grid_import_kwh"] == pytest.approx(4 - selected_pv, abs=1e-7)
    report = reports.evaluate(
        owner,
        project.id,
        3,
        ReportOptions(
            locale="de",
            pv_run_id=run.id,
            energy_run_id=energy_result.id,
            equipment_run_id=None,
            logo=None,
        ),
        key="report",
    )
    assert worker.run_once()
    report_run = workspace.run(owner, report.id)
    assert report_run.state == "succeeded", report_run.error
    assert report_run.result is not None
    sections = cast(list[Object], cast(Object, report_run.result["report"])["sections"])
    assert any(
        str(section["id"]).startswith("geometric-pv-reference-") for section in sections
    )
    for selected in (run, report_run):
        context = assistant_context(
            workspace, owner, project.id, selected.revision, [selected.id], "en"
        )
        assert "uniform" in str(context)
        assert "latitude_deg" not in str(context) and weather_request().url not in str(
            context
        )
        assert "SARAH3" in str(context)
    groups = cast(
        list[Object], cast(Object, calculation_sources(workspace, report_run))["groups"]
    )
    pv_source = next(group for group in groups if group["kind"] == "pv")
    energy_source = next(group for group in groups if group["kind"] == "energy")
    assert pv_source["radiation_database"] == "PVGIS-SARAH3"
    assert pv_source["synthetic_calculation_year"] == 2023
    assert (
        cast(list[Object], pv_source["periods_utc"])[0]["start_utc"]
        == "2023-01-01T00:00:00+00:00"
    )
    assert (
        cast(list[Object], energy_source["periods_utc"])[0]["start_utc"]
        == "2023-06-16T11:00:00+00:00"
    )
    withdrawn = True
    assert service.evaluate(owner, project.id, 2, key="full-geometric").id == run.id
    with pytest.raises(ProductEvidenceChanged):
        service.evaluate(owner, project.id, 3, key="new-withdrawn")
    withdrawn = False
    # Native seam for browser readers: actual completed objects and hashes;
    # no provider originals, runtime bytes or live site/customer claim.
    # Every key of the committed browser fixture is produced here, so the
    # fixture can be regenerated from this test instead of being hand-edited.
    seam = {
        "project": before_project,
        "run": run_view(run),
        "weather_asset": asset_view(source),
        "profile_asset": asset_view(asset),
        "profile_preview": preview,
        "profile_preview_initial": ProfilePreview(Assets(workspace)).page(
            owner, project.id, asset.id, offset=0, page_size=2
        ),
        "report_run": run_view(report_run),
        "run_assistant": assistant_context(
            workspace, owner, project.id, run.revision, [run.id], "en"
        ),
        "report_run_assistant": assistant_context(
            workspace, owner, project.id, report_run.revision, [report_run.id], "en"
        ),
        "calculation_sources": calculation_sources(workspace, report_run),
        "source_note": "Actual retained complete weather; synthetic one-module layout and declared scenario; native task/asset/report, not site/equipment approval",
    }
    out = tmp_path / "geometric-pv-native-seam.json"
    out.write_text(json.dumps(seam, ensure_ascii=False, indent=2) + "\n")
    print(f"GEOMETRIC_NATIVE_SEAM={out}")


def test_new_manifest_freezes_the_requested_generation_model(
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sha = workspace.blobs.put(b"{}")

    class Source:
        content_sha256 = sha
        metadata_sha256 = sha

    monkeypatch.setattr(
        "linker_engine.planning.geometric_pv_job.selected_source",
        lambda *_args: Source(),
    )
    kernel = GeometricPvKernel(
        workspace,
        LIMITS,
        GeometricPvLimits(
            max_module_steps=10,
            max_samples=100,
            max_ray_face_checks=1000,
            max_bounds_checks=1000,
            index_leaf_size=2,
        ),
        products=ProductSources(lambda: cast(Any, object())),
    )
    monkeypatch.setattr(
        kernel.products, "pv_basis", lambda _inputs: {"module": "frozen"}
    )
    service = GeometricPvService(workspace, kernel, max_attempts=1)
    registry = ExecutionRegistry(kernel)
    routing = registry.routing(1)
    assert kernel.execution_key_for(MODEL_V1) in routing.execution_keys
    assert kernel.execution_key_for(MODEL_V2) in routing.execution_keys
    assert registry._by_key[kernel.execution_key_for(MODEL_V2)] is kernel

    def enqueue(model_request: object, key: str) -> Object:
        document = cast(Object, cast(Any, model_request).model_dump(mode="json"))
        model = cast(str, document["model"])
        project = workspace.create(
            owner,
            key,
            {"geometric_pv_preparation": document, "geometry": geometry()},
            key=key,
            input_contract=GEOMETRIC_PV_INPUT_CONTRACT,
        )
        run = service.evaluate(owner, project.id, 1, key=key)
        models = cast(Object, cast(Object, run.manifest["context"])["models"])
        assert models["generation"] == model
        with workspace.database.read() as connection:
            route = cast(
                Any,
                connection.execute(
                    "SELECT evaluation_routes.execution_sha256 FROM evaluation_routes "
                    "JOIN jobs ON jobs.id=evaluation_routes.job_id WHERE jobs.run_id=?",
                    (run.id,),
                ).fetchone(),
            )
        assert route is not None
        assert route["execution_sha256"] == kernel.execution_key_for(model)
        return run.manifest

    retained = enqueue(scenario(parameter_document()), "freeze-v1")
    current = enqueue(perez_request(perez_parameters()), "freeze-v2")
    retained_models = cast(Object, cast(Object, retained["context"])["models"])
    current_models = cast(Object, cast(Object, current["context"])["models"])
    assert retained_models["generation"] == MODEL_V1
    assert current_models["generation"] == MODEL_V2
    assert kernel.execution_key_for(MODEL_V1) != kernel.execution_key_for(MODEL_V2)
