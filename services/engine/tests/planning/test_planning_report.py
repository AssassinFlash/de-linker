"""One owned report path; old numerical fixtures and source studies are reused."""

from __future__ import annotations

import io
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.engine import Engine
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import NotFound, ProductEvidenceChanged
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.guest_claims import GuestClaims
from linker_engine.planning.handoffs import Handoffs
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.records import Actor
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import renew_module_permission
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .test_energy_kernel import TOLERANCE
from .test_equipment import (
    feed as equipment_feed,  # noqa: F401 -- Shared cited fixture, registered under this name.
)
from .test_equipment import inputs
from .test_private_http import TOKEN, headers


def test_owned_report_publishes_one_pdf_and_retains_history_after_withdrawal(
    request: pytest.FixtureRequest,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = Actor("guest", "report:guest")

    def caller_headers():
        return {
            **headers(),
            "X-Linker-Planner-Principal-Kind": owner.kind,
            "X-Linker-Planner-Principal-Subject": owner.subject,
        }

    old_proof = {"schema_version": 1, "module": {"frozen_fact": "same"}}
    current_proof = {**old_proof, "publication": {"revision": "renewed"}}
    assert renew_module_permission(old_proof, current_proof) == current_proof
    with pytest.raises(ProductEvidenceChanged):
        renew_module_permission(
            old_proof, {**current_proof, "module": {"frozen_fact": "changed"}}
        )
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    offline = False
    withdrawn = False

    def current(self):
        if offline:
            raise PublicationUnavailable("fixture authority offline")
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            manifest["products"] = [
                p for p in manifest["products"] if p["product_id"] != 2090
            ]
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    sources = ProductSources(lambda: shared)
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, sources), max_attempts=1
    )
    original_compute = EquipmentKernel.compute

    def historical_bom(self, *args):
        output = original_compute(self, *args)
        for line in output["assessment"]["provisional_bill_of_materials"]:
            for field in ("brand", "model", "sku"):
                line.pop(field, None)
        return output

    monkeypatch.setattr(EquipmentKernel, "compute", historical_bom)
    reports = ReportService(workspace, ReportKernel(workspace, sources), max_attempts=1)
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    registry = service_registry(energy, None, None, equipment, None, reports)
    worker = Worker(
        Jobs(workspace),
        "report-fixture",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    project = workspace.create(
        owner, "Frozen project report", inputs(feed, 3), key="report-project"
    )
    checked = equipment.evaluate(owner, project.id, 1, key="equipment-source")
    assert worker.run_once() and workspace.run(owner, checked.id).state == "succeeded"
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        equipment=equipment,
        reports=reports,
        product_provider=lambda: shared,
    )
    command = {
        "schema_version": 1,
        "project_id": project.id,
        "expected_revision": 1,
        "key": "first-report",
        "options": {
            "locale": "en",
            "energy_run_id": None,
            "pv_run_id": None,
            "equipment_run_id": checked.id,
            "logo": None,
        },
    }
    with TestClient(app) as client:
        assert client.post("/runs/report", json=command).status_code == 401
        accepted = client.post("/runs/report", json=command, headers=caller_headers())
        assert accepted.status_code == 200, accepted.text
        assert worker.run_once()
        run = workspace.run(owner, accepted.json()["id"])
        assert run.state == "succeeded", run.error
        result = run.result
        assert result is not None
        assert result["report_sha256"] == digest(encode(result["report"]))
        asset = result["prepared_asset"]
        pdf = Assets(workspace).content(owner, project.id, asset["id"])
        text = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages
        )
        assert "Frozen project report" in text and "13.5" in text
        assert "Provisional bill of materials" in text and "HTW Berlin" not in text
        assert "H2-10K-T3" in text and "BU2" in text
        transfer_command = {
            "schema_version": 1,
            "project_id": project.id,
            "report_run_id": run.id,
            "expected_revision": 1,
            "key": "report-handoff",
        }
        prepared = client.post(
            "/handoffs/prepare", json=transfer_command, headers=caller_headers()
        )
        assert prepared.status_code == 200, prepared.text
        handoff = prepared.json()
        assert handoff["snapshot_sha256"] == digest(encode(handoff["snapshot"]))
        assert {
            (item["product_id"], item["quantity"])
            for item in handoff["snapshot"]["items"]
        } == {(4107, 1), (2090, 3), (2092, 1)}
        assert (
            client.post(
                "/handoffs/prepare",
                json={**transfer_command, "key": "another-preview"},
                headers=caller_headers(),
            ).json()["id"]
            == handoff["id"]
        )
        assert (
            client.post(
                "/handoffs/prepare",
                json={**transfer_command, "items": []},
                headers=caller_headers(),
            ).status_code
            == 422
        )
        with pytest.raises(NotFound):
            Handoffs(workspace).read(Actor("user", "other:account"), handoff["id"])
        guest = owner
        owner = Actor("user", "report:account")
        GuestClaims(workspace).claim(guest, owner, key="native-login")
        assert (
            client.post(
                "/handoffs/prepare", json=transfer_command, headers=caller_headers()
            ).json()["id"]
            == handoff["id"]
        )
        with pytest.raises(NotFound):
            Handoffs(workspace).read(guest, handoff["id"])
        before_assets = workspace.database.read()
        with before_assets as connection:
            count = connection.execute(
                "select count(*) from project_assets"
            ).fetchone()[0]
        offline = True
        replay = client.post("/runs/report", json=command, headers=caller_headers())
        assert replay.status_code == 200 and replay.json()["id"] == run.id
        assert Assets(workspace).content(owner, project.id, asset["id"]) == pdf
        offline = False
        original = __import__(
            "linker_engine.planning.report_kernel", fromlist=["render"]
        ).render

        def withdraw_during_render(*args, **kwargs):
            nonlocal withdrawn
            output = original(*args, **kwargs)
            withdrawn = True
            return output

        monkeypatch.setattr(
            "linker_engine.planning.report_kernel.render", withdraw_during_render
        )
        second = client.post(
            "/runs/report",
            json={**command, "key": "second-report"},
            headers=caller_headers(),
        )
        assert second.status_code == 200, second.text
        assert worker.run_once()
        failed = workspace.run(owner, second.json()["id"])
        assert (
            failed.state == "failed"
            and failed.error["code"] == "product_evidence_changed"
        )
        with workspace.database.read() as connection:
            assert (
                connection.execute("select count(*) from project_assets").fetchone()[0]
                == count
            )
        assert Assets(workspace).content(owner, project.id, asset["id"]) == pdf
