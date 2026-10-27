"""One owned report path; old numerical fixtures and source studies are reused."""

from __future__ import annotations

import copy
import csv
import io
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.engine import Engine
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import assistant_context
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
from linker_engine.planning.project_materials import materials_csv
from linker_engine.planning.records import Actor
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import renew_module_permission
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .conftest import FixtureObject, json_object
from .test_certificate_evidence import certificate_pdf
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

    def caller_headers() -> dict[str, str]:
        return {
            **headers(),
            "X-Linker-Planner-Principal-Kind": owner.kind,
            "X-Linker-Planner-Principal-Subject": owner.subject,
        }

    old_proof: FixtureObject = {"schema_version": 1, "module": {"frozen_fact": "same"}}
    current_proof: FixtureObject = {**old_proof, "publication": {"revision": "renewed"}}
    assert (
        json_object(renew_module_permission(old_proof, current_proof)) == current_proof
    )
    with pytest.raises(ProductEvidenceChanged):
        json_object(
            renew_module_permission(
                old_proof, {**current_proof, "module": {"frozen_fact": "changed"}}
            )
        )
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    certificate_bytes = certificate_pdf()
    certificate_sha = workspace.blobs.put(certificate_bytes)
    next(p for p in feed["products"] if p["id"] == 4107)["documents"].append(
        {
            "document_id": "doc-" + digest(b"synthetic-certificate"),
            "document_revision": digest(b"synthetic-certificate-revision"),
            "blob_sha256": certificate_sha,
            "url": "https://de-linker.com/wp-content/uploads/fixture-certificate.pdf",
            "title": "Synthetic certificate declarations",
            "type": "certificate",
            "lang": "en",
            "product_ids": [4107],
            "role": "primary",
            "aliases": [],
            "citation_aliases": [],
        }
    )
    # Synthetic quantities exercise the Woo projection, not a real packing list.
    for pid, quantity, role, name in (
        (4107, 1, "meter", "Fixture supplied meter"),
        (2090, 2, "other", "Fixture supplied connector"),
    ):
        product = next(p for p in feed["products"] if p["id"] == pid)
        doc = product["documents"][0]
        product["package_contents"] = {
            "status": "documented",
            "items": [
                {
                    "id": f"fixture-{pid}",
                    "label": {"en": name, "de": name},
                    "quantity": quantity,
                    "unit": "piece",
                    "role": role,
                    "source": {
                        **{
                            key: doc[key]
                            for key in (
                                "document_id",
                                "document_revision",
                                "blob_sha256",
                                "url",
                            )
                        },
                        "product_id": pid,
                        "page": 1,
                    },
                }
            ],
        }
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    offline = False
    withdrawn = False

    def current(self: Publication) -> FixtureObject:
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

    def historical_bom(
        self: EquipmentKernel,
        inputs: FixtureObject,
        basis: FixtureObject,
        control: Control,
    ) -> FixtureObject:
        output = json_object(original_compute(self, inputs, basis, control))
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
            "inspect_certificate_declarations": True,
        },
    }
    with TestClient(app) as client:
        assert client.post("/runs/report", json=command).status_code == 401
        accepted = client.post("/runs/report", json=command, headers=caller_headers())
        assert accepted.status_code == 200, accepted.text
        assert worker.run_once()
        run = workspace.run(owner, accepted.json()["id"])
        assert run.state == "succeeded", run.error
        result = json_object(run.result)
        assert result is not None
        assert result["report_sha256"] == digest(encode(result["report"]))
        asset = result["prepared_asset"]
        materials = json_object(workspace.blobs.object(result["materials_sha256"]))
        assert (
            materials
            == json_object(
                workspace.blobs.object(result["pinned_assets"]["report.source"])
            )["materials"]
        )
        csv_asset = result["prepared_attachments"]["bill_of_materials_csv"]
        original_csv = Assets(workspace).content(owner, project.id, csv_asset["id"])
        csv_rows = list(csv.reader(io.StringIO(original_csv.decode("utf-8-sig"))))
        assert {row[2] for row in csv_rows[1:]} >= {"1", "3"}
        assert all(row[7] == result["materials_sha256"] for row in csv_rows[1:])
        assert {row[3] for row in csv_rows[1:]} >= {"SAJ H2-10K-T3", "SAJ BU2-5.0-HV1"}
        supplied = [
            line
            for line in materials["lines"]
            if line["handling"] == "manufacturer_included"
        ]
        assert {
            (line["parent_product_id"], line["quantity"], line["unit"])
            for line in supplied
        } == {(4107, 1, "piece"), (2090, 6, "piece")}
        assert all(row[9] == "pc" for row in csv_rows[1:])
        from linker_engine.planning.project_materials import material_quantity

        assert (
            material_quantity({"quantity": 0.00001, "unit": "m"}, "en") == "0.00001 m"
        )
        assert material_quantity({"quantity": 1234.5, "unit": "m"}, "de") == "1.234,5 m"
        unsafe = copy.deepcopy(materials)
        unsafe["lines"][0]["brand"], unsafe["lines"][0]["model"] = "", " =1+1"
        german_csv = list(
            csv.reader(
                io.StringIO(
                    materials_csv(unsafe, result["materials_sha256"], "de").decode(
                        "utf-8-sig"
                    )
                )
            )
        )
        assert german_csv[0][2] == "Menge" and german_csv[1][3].startswith("'")
        pdf = Assets(workspace).content(owner, project.id, asset["id"])
        text = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages
        )
        assert "Frozen project report" in text and "13.5" in text
        assert "Provisional bill of materials" in text and "HTW Berlin" not in text
        assert "H2-10K-T3" in text and "BU2" in text
        assert "010101" in text and "164" in text
        inspection = json_object(
            workspace.blobs.object(result["dependencies"]["certificate_inspection"])
        )
        assert (
            inspection["dependencies"][
                "certificate.doc-" + digest(b"synthetic-certificate") + ".raw"
            ]
            == certificate_sha
        )
        assert (
            result["dependencies"]["report_source"]
            == inspection["report_source_sha256"]
            == result["pinned_assets"]["report.source"]
        )
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
        assert handoff["snapshot"]["materials_sha256"] == result["materials_sha256"]
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
        german_context = json_object(
            assistant_context(workspace, owner, project.id, 1, [run.id], "de")
        )
        assert any(
            "Firmware" in row["label"] and row["value"] == "010101"
            for row in german_context["runs"][0]["rows"]
        )
        assert any(
            "164" in str(row["value"]) for row in german_context["runs"][0]["rows"]
        )
        replay = client.post("/runs/report", json=command, headers=caller_headers())
        assert replay.status_code == 200 and replay.json()["id"] == run.id
        assert Assets(workspace).content(owner, project.id, asset["id"]) == pdf
        assert (
            Assets(workspace).content(owner, project.id, csv_asset["id"])
            == original_csv
        )
        offline = False
        original = __import__(
            "linker_engine.planning.report_kernel", fromlist=["render"]
        ).render

        def withdraw_during_render(*args: Any, **kwargs: Any) -> bytes:
            nonlocal withdrawn
            output = original(*args, **kwargs)
            assert isinstance(output, bytes)
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
            and json_object(failed.error)["code"] == "product_evidence_changed"
        )
        with workspace.database.read() as connection:
            assert (
                connection.execute("select count(*) from project_assets").fetchone()[0]
                == count
            )
        assert Assets(workspace).content(owner, project.id, asset["id"]) == pdf
        assert (
            Assets(workspace).content(owner, project.id, csv_asset["id"])
            == original_csv
        )
        with pytest.raises(NotFound):
            Assets(workspace).content(guest, project.id, csv_asset["id"])
