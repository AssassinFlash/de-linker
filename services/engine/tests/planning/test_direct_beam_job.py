"""One real durable adapter path; source parsing, not annual PV generation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import pytest
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from linker_engine.planning import direct_beam_job
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import assistant_context
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.direct_beam_inputs import DirectBeamLimits
from linker_engine.planning.direct_beam_job import DirectBeamKernel
from linker_engine.planning.direct_beam_service import DirectBeamService
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import (
    Conflict,
    EvaluationRevisionChanged,
    NotFound,
    ProductEvidenceChanged,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import DIRECT_BEAM_INPUT_CONTRACT
from linker_engine.planning.pv_parameters import PvGenerationLimits
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.pv_weather import WeatherSeries
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.weather_import import WeatherImport
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_energy_kernel import TOLERANCE
from .test_private_http import TOKEN, headers
from .test_pv_generation import geometry
from .test_pv_profile import LIMITS, PROVENANCE
from .test_pvgis_tmy import capture, interpretation, raw, request


def test_owned_frozen_weather_runs_only_in_worker_and_fails_closed_on_source_or_woo_change(
    workspace: Workspace,
    owner: Actor,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    withdrawn = False
    publication_reads = 0

    def current(publication: Publication) -> FixtureObject:
        nonlocal publication_reads
        publication_reads += 1
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
    template = cast(Object, json_object(products.module_basis())["module"])
    roof = geometry()
    identifier = roof["module_specs"][0]["id"]
    roof["module_specs"] = [
        {**cast(Object, template["specification"]), "id": identifier}
    ]
    project = workspace.create(
        owner, "Synthetic owned direct-beam fixture", {"geometry": roof}, key="roof"
    )
    assets = Assets(workspace)
    source = WeatherImport(assets, LIMITS).tmy(
        owner,
        project.id,
        PvSource(raw(), request(), capture(), interpretation(), encode(PROVENANCE)),
        key="weather",
    )
    inputs: Object = {
        **project.inputs,
        "direct_beam_visibility": {
            "schema_version": 1,
            "weather_asset_id": source.id,
            "row_indices": [0, 12],
            "sampling": {"coarse_cells_per_edge": 1, "fine_cells_per_edge": 2},
        },
    }
    project = workspace.revise(
        owner,
        project.id,
        1,
        inputs,
        key="selection",
        input_contract=DIRECT_BEAM_INPUT_CONTRACT,
    )
    # Explicit tiny diagnostic resource policy, not an engineering recommendation.
    kernel = DirectBeamKernel(
        workspace,
        LIMITS,
        DirectBeamLimits(
            max_selected_rows=2,
            max_samples=10000,
            max_ray_face_checks=100000,
            max_bounds_checks=100000,
            index_leaf_size=4,
        ),
        products=products,
    )
    service = DirectBeamService(workspace, kernel, max_attempts=1)
    energy = EnergyService(
        workspace,
        EnergyKernel(workspace, TOLERANCE, max_intervals=9000, products=products),
        max_attempts=1,
    )
    reports = ReportService(
        workspace, ReportKernel(workspace, products), max_attempts=1
    )
    registry = service_registry(energy, None, reports=reports, direct_beam=service)
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 2, 16),
        product_provider=client.app.state.planning_product_provider,
        direct_beam=service,
        reports=reports,
    )
    worker = Worker(
        Jobs(workspace),
        "direct-beam-fixture",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
        routing=registry.routing(1),
    )
    with pytest.raises(NotFound):
        service.evaluate(Actor("user", "foreign"), project.id, 2, key="foreign-owner")
    other = workspace.create(
        owner,
        "Another owned project cannot borrow an asset",
        inputs,
        key="other-project",
        input_contract=DIRECT_BEAM_INPUT_CONTRACT,
    )
    with pytest.raises(NotFound):
        service.evaluate(owner, other.id, 1, key="foreign-source")

    # The row picker navigates only owned retained originals, with a bounded
    # page and separate synthetic interval / original solar-position axes.
    with TestClient(app) as navigation:
        indexed = navigation.post(
            "/weather/assets",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "offset": 0,
                "page_size": 2,
            },
            headers=headers(owner),
        )
        assert (
            indexed.status_code == 200
            and indexed.json()["assets"][0]["asset_id"] == source.id
        )
        page_body = {
            "schema_version": 1,
            "project_id": project.id,
            "asset_id": source.id,
            "offset": 0,
            "page_size": 2,
        }
        preview = navigation.post(
            "/weather/preview", json=page_body, headers=headers(owner)
        )
        assert preview.status_code == 200, preview.text
        page = preview.json()
        assert (
            page["content_sha256"] == source.content_sha256
            and page["metadata_sha256"] == source.metadata_sha256
        )
        assert [row["source_row_index"] for row in page["rows"]] == [0, 1]
        assert page["next_offset"] == 2
        assert page["source"]["start_year"] == request().start_year
        assert page["synthetic_year"] == interpretation().synthetic_energy_year
        assert (
            navigation.post(
                "/weather/preview",
                json={**page_body, "page_size": 3},
                headers=headers(owner),
            ).status_code
            == 422
        )
        assert (
            navigation.post(
                "/weather/preview",
                json=page_body,
                headers=headers(Actor("user", "foreign")),
            ).status_code
            == 404
        )
        assert (
            navigation.post(
                "/weather/preview",
                json={**page_body, "project_id": other.id},
                headers=headers(owner),
            ).status_code
            == 404
        )

    parses = 0
    parse_weather = PvSource.weather

    def counted_weather(value: PvSource, limits: PvGenerationLimits) -> WeatherSeries:
        nonlocal parses
        parses += 1
        return parse_weather(value, limits)

    monkeypatch.setattr(PvSource, "weather", counted_weather)
    body = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": 2,
        "key": "visibility",
    }
    with TestClient(app) as admission:
        version = admission.post(
            "/version", json={"schema_version": 1}, headers=headers(owner)
        )
        assert version.status_code == 200
        assert version.json()["execution_key"] == registry.execution_key()
        assert version.json()["models"]["direct_beam_visibility"] == kernel.kind
        assert version.json()["limits"][
            "direct_beam_visibility"
        ] == kernel.limits.model_dump(mode="json")
        admitted = admission.post(
            "/runs/direct-beam", json=body, headers=headers(owner)
        )
        assert admitted.status_code == 200, admitted.text
        assert (
            admission.post(
                "/runs/direct-beam", json=body, headers=headers(owner)
            ).json()
            == admitted.json()
        )
        replay = admission.post(
            "/operations/replay/runs/direct-beam", json=body, headers=headers(owner)
        )
        assert replay.status_code == 200 and replay.json()["status"] == "replayed"
        assert replay.json()["result"] == admitted.json()
        invalid = deepcopy(inputs)
        cast(Object, invalid["direct_beam_visibility"])["row_indices"] = [2, 0]
        refused_rows = admission.post(
            "/projects/revise",
            json={
                **body,
                "key": "invalid-rows",
                "inputs": invalid,
                "input_contract": DIRECT_BEAM_INPUT_CONTRACT,
            },
            headers=headers(owner),
        )
        assert refused_rows.status_code == 422
        assert refused_rows.json()["error"]["code"] == "invalid_input"
        assert workspace.get(owner, project.id).revision == 2
    run = workspace.run(owner, admitted.json()["id"])
    assert parses == 0  # Admission pins raw/meta, without rebuilding 8760 rows.
    assert worker.run_once()
    completed = workspace.run(owner, run.id)
    assert completed.state == "succeeded" and completed.result is not None
    result = completed.result
    witness = cast(Object, result["visibility"])
    dependencies = cast(Object, result["dependencies"])
    rows = cast(list[Object], witness["rows"])
    document = workspace.blobs.object(str(dependencies["weather.document"]))
    original = cast(list[Object], document["points"])
    assert [row["source_row_index"] for row in rows] == [0, 12]
    assert [row["irradiance_at_utc"] for row in rows] == [
        original[i]["irradiance_at_utc"] for i in (0, 12)
    ]
    assert cast(Object, witness["sources"])["weather_document_sha256"] == digest(
        encode(document)
    )
    assert result["result_scope"] == "geometric_witness_not_a_profile_or_power_loss"
    assert "prepared_asset" not in result and parses == 1
    with workspace.database.read() as db:
        assert db.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0] == 1

    assert {module["status"] for module in cast(list[Object], rows[0]["modules"])} == {
        "night"
    }
    assert any(
        module["status"] == "sampled"
        for module in cast(list[Object], rows[1]["modules"])
    )
    assert result["frozen_geometry"] == inputs["geometry"]
    assert page["weather_document_sha256"] == dependencies["weather.document"]
    assert {key: rows[0][key] for key in page["rows"][0]} == page["rows"][0]
    # The same witness is consumed through report admission and the registered
    # report worker, with no solar-position/weather/PV recomputation.
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
        direct_beam_run_id=run.id,
    )
    with TestClient(app) as consumption:
        assert (
            consumption.post(
                "/runs/read",
                json={"schema_version": 1, "run_id": run.id},
                headers=headers(owner),
            ).json()["result"]
            == result
        )
        report_reply = consumption.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": 2,
                "key": "geometric-report",
                "options": options.model_dump(mode="json"),
            },
            headers=headers(owner),
        )
        assert report_reply.status_code == 200, report_reply.text
    assert worker.run_once()
    report_run = workspace.run(owner, report_reply.json()["id"])
    assert report_run.state == "succeeded" and report_run.result is not None
    report_result = report_run.result
    sections = cast(Object, report_result["report"])["sections"]
    geometric = next(
        item for item in cast(list[Object], sections) if item["id"] == "direct-beam-0"
    )
    assert len(cast(list[object], cast(Object, geometric["table"])["rows"])) == 2
    assert "not power or energy losses" in str(geometric["paragraphs"])
    report_source = workspace.blobs.object(
        str(cast(Object, report_result["dependencies"])["report_source"])
    )
    assert cast(Object, report_source["direct_beam"])["witness"] == witness
    assert (
        cast(Object, report_source["dependencies"])["direct_beam.weather.raw"]
        == source.content_sha256
    )
    for selected in (completed, report_run):
        context = assistant_context(
            workspace, owner, project.id, 2, [selected.id], "de"
        )
        text = str(context)
        assert "geometric" in text or "geometrisch" in text.lower()
        assert request().url not in text and "latitude_deg" not in text
        assert "not_assessed" in text or "Freigabe" in text
    assert parses == 1
    # Adding the absent report option must preserve the exact legacy intent.
    legacy = {
        key: value
        for key, value in options.model_dump(mode="json").items()
        if key
        not in {
            "direct_beam_run_id",
            "comparison",
            "include_installation",
            "inspect_certificate_declarations",
        }
    }
    legacy_options = ReportOptions.read(legacy)
    assert legacy_options.intent() == {
        "kind": "planning_report_v1",
        "options_sha256": digest(encode(legacy)),
    }

    # An exact acknowledgment returns the same frozen witness before any new
    # source permission read. A new command still needs current Woo evidence.
    reads_before_replay = publication_reads
    withdrawn = True
    replayed = service.evaluate(owner, project.id, 2, key="visibility")
    assert replayed == completed and publication_reads == reads_before_replay
    assert parses == 1
    with pytest.raises(NotFound):
        service.evaluate(Actor("user", "foreign"), project.id, 2, key="visibility")
    with pytest.raises(Conflict):
        service.evaluate(owner, project.id, 1, key="visibility")
    assert publication_reads == reads_before_replay
    with pytest.raises(ProductEvidenceChanged):
        service.evaluate(owner, project.id, 2, key="new-withdrawn-command")
    with pytest.raises(ProductEvidenceChanged):
        reports.kernel.context(owner, project.id, 2, options)
    assert publication_reads > reads_before_replay and parses == 1
    withdrawn = False

    # An owned row is insufficient if its retained original was corrupted.
    bad = service.evaluate(owner, project.id, 2, key="corrupt-source")
    path = workspace.blobs.directory / source.content_sha256[:2] / source.content_sha256
    retained = path.read_bytes()
    try:
        path.write_bytes(b"corrupt")
        assert worker.run_once()
        rejected = workspace.run(owner, bad.id)
        assert rejected.state == "failed" and rejected.result is None
        assert rejected.error == {"code": "version_unavailable", "retryable": False}
        assert parses == 1
    finally:
        path.write_bytes(retained)

    # Reuse the identical already-computed two-row witness. This isolates the
    # actual post-compute Woo permission race without recomputing geometry.
    permission_run = service.evaluate(owner, project.id, 2, key="permission-race")

    def withdraw_after_compute(*args: Any, **kwargs: Any) -> Object:
        nonlocal withdrawn
        withdrawn = True
        return deepcopy(witness)

    monkeypatch.setattr(direct_beam_job, "prepare_direct_beam", withdraw_after_compute)
    assert worker.run_once()
    refused = workspace.run(owner, permission_run.id)
    assert refused.state == "failed" and refused.result is None
    assert refused.error == {"code": "product_evidence_changed", "retryable": False}
    withdrawn = False

    # A save between the owned read and enqueue is rejected by the existing
    # transactional Workspace revision fence, never replaced with latest inputs.
    roof_basis = products.roof_basis

    def revise_during_intake(value: Object) -> Object:
        basis = roof_basis(value)
        workspace.revise(
            owner,
            project.id,
            2,
            {**inputs, "fixture_note": "edited"},
            key="race-edit",
            input_contract=DIRECT_BEAM_INPUT_CONTRACT,
        )
        return basis

    monkeypatch.setattr(products, "roof_basis", revise_during_intake)
    with pytest.raises(EvaluationRevisionChanged):
        service.evaluate(owner, project.id, 2, key="revision-race")
    historical = service.evaluate(owner, project.id, 2, key="visibility")
    assert historical.id == run.id and historical.revision == 2
    assert historical.result == completed.result and not historical.is_current
