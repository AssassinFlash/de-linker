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
from linker_engine.planning.certificate_evidence import CertificateEvidence
from linker_engine.planning.certificate_report import certificate_sections
from linker_engine.planning.certificate_sources import inspect_report_certificates
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_conditions import review_device_conditions
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
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import (
    ReportInputsChanged,
    renew_module_permission,
    report_sources,
)
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .conftest import FixtureObject, json_object
from .test_certificate_evidence import (
    certificate_pdf,
    condition_project,
    evidence,
    inspected_fixture,
)
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
    project_inputs = inputs(feed, 3)
    project_inputs["equipment_condition_inputs"] = {
        "schema_version": 1,
        "devices": [
            {
                "selection_ref": {"kind": "single", "role": "inverter"},
                "product_id": 4107,
                "product_revision": project_inputs["equipment_selection"][
                    "product_revisions"
                ]["4107"],
                "declared_model": "Fixture-1",
                "declared_firmware": "010101",
                "source_note": "Synthetic proposed device detail for this project.",
            }
        ],
    }
    project = workspace.create(
        owner, "Frozen project report", project_inputs, key="report-project"
    )
    checked = equipment.evaluate(owner, project.id, 1, key="equipment-source")
    assert worker.run_once() and workspace.run(owner, checked.id).state == "succeeded"
    equipment_certificates = CertificateEvidence(workspace).read(owner, checked.id)
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
        assert "Project device details" in text
        assert "Model listed on this page" in text and "Firmware text matches" in text
        assert "Model text differs" in text and "identity needs clarification" in text
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
        report_source_sha = result["dependencies"]["report_source"]
        recorded_source = json_object(workspace.blobs.object(report_source_sha))
        assert (
            recorded_source["equipment_condition_inputs"]
            == project_inputs["equipment_condition_inputs"]
        )
        assert recorded_source["inspect_certificate_declarations"] is True
        assert recorded_source["certificate_context"] == {
            "run_id": checked.id,
            "revision": 1,
            "kind": EquipmentKernel.kind,
        }
        device_section = next(
            section
            for section in result["report"]["sections"]
            if section["id"] == "certificate-device-conditions"
        )
        assert {row["value"] for row in device_section["rows"]} == {checked.id, "1"}
        assert (
            CertificateEvidence(workspace).read(owner, run.id)["condition_review"]
            == equipment_certificates["condition_review"]
            == inspection["evidence"]["condition_review"]
            == recorded_source["certificates"]["condition_review"]
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
        changed_inputs = copy.deepcopy(project_inputs)
        changed_inputs["equipment_condition_inputs"]["devices"][0][
            "declared_firmware"
        ] = "10101"
        changed = workspace.revise(
            owner, project.id, 1, changed_inputs, key="later-device-details"
        )
        with pytest.raises(ReportInputsChanged):
            report_sources(
                workspace,
                sources,
                owner,
                changed,
                ReportOptions(
                    locale="en",
                    energy_run_id=None,
                    pv_run_id=None,
                    equipment_run_id=checked.id,
                    logo=None,
                ),
            )
        assert workspace.blobs.object(report_source_sha) == recorded_source
        assert Assets(workspace).content(owner, project.id, asset["id"]) == pdf


def test_device_report_keeps_each_documents_result_and_unanswered_device(
    workspace: Workspace,
) -> None:
    source = json_object(inspected_fixture(workspace))
    original = source["documents"][0]
    another = {
        **original,
        "document_id": "doc-other",
        "document_revision": "c" * 64,
        "title": "Second recorded certificate",
        "product_ids": [1],
        "blob_sha256": workspace.blobs.put(
            certificate_pdf(models="Other-9", firmware="010102")
        ),
    }
    source["documents"].append(another)
    inspect_report_certificates({"certificates": source}, workspace.blobs, lambda: None)
    inputs = json_object(condition_project())
    inputs["equipment_condition_inputs"]["devices"][0]["declared_firmware"] = "010102"
    legacy_sections = certificate_sections(source, "en")
    source["condition_review"] = review_device_conditions(inputs, source)
    frozen_sha = digest(encode(source))
    for locale, listed, absent, conflict, matched, unresolved in (
        (
            "en",
            "Model listed on this page",
            "Model not listed on this page",
            "Firmware text differs",
            "Firmware text matches",
            "Firmware comparison unresolved",
        ),
        (
            "de",
            "Modell auf dieser Seite aufgeführt",
            "Modell auf dieser Seite nicht aufgeführt",
            "Firmwareangabe weicht ab",
            "Firmwareangabe stimmt überein",
            "Firmwareabgleich offen",
        ),
    ):
        sections = {
            section.id: section
            for section in certificate_sections(
                source,
                locale,
                {"run_id": "a" * 32, "revision": 4, "candidate_id": "saved-choice"},
            )
        }
        assert {
            row.value for row in sections["certificate-device-conditions"].rows
        } == {
            "a" * 32,
            "4",
            "saved-choice",
        }
        first = sections["certificate-device-0-document-0"]
        second = sections["certificate-device-0-document-1"]
        assert {row.value for row in first.rows} >= {
            listed,
            conflict,
            "010101",
            "010102",
        }
        assert {row.value for row in second.rows} >= {
            absent,
            matched,
            "Other-9",
            "010102",
        }
        assert any("164" in row.value for row in first.rows)
        for document, section in ((original, first), (another, second)):
            assert {row.value for row in section.rows} >= {
                document["document_id"],
                document["document_revision"],
                document["blob_sha256"],
            }
            assert all(
                "linker_document_sha256=" + document["blob_sha256"] in row.href
                for row in section.rows
                if row.href
            )
        unanswered = sections["certificate-device-1-document-0"]
        assert unresolved in {row.value for row in unanswered.rows}
        assert len(sections["certificate-device-open-checks"].rows) == 10
    assert certificate_sections(source, "en")[0] == legacy_sections[0]
    assert (
        digest(encode(source)) == frozen_sha
    )  # Presentation never rewrites its input.


def test_absent_device_inputs_keep_legacy_report_source_shape(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_inputs = json_object(condition_project())
    project_inputs.pop("equipment_condition_inputs")
    basis, assessment = evidence()
    proof = workspace.blobs.put_object(basis)
    context = replace(context, assets={**context.assets, "woo.equipment_inputs": proof})
    project = workspace.create(
        owner, "Legacy report shape", project_inputs, key="legacy"
    )
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": EquipmentKernel.kind,
            "assessment": assessment,
            "pinned_assets": {key: sha for key, sha in context.assets.items()},
            "runtime_sha256": context.code_sha256,
        },
    )
    products = ProductSources(
        lambda: pytest.fail("this fixture uses the frozen source")
    )
    monkeypatch.setattr(products, "confirm_basis", lambda *args, **kwargs: None)
    source = report_sources(
        workspace,
        products,
        owner,
        project,
        ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=run.id,
            logo=None,
        ),
    )
    assert "equipment_condition_inputs" not in source
    assert "certificate_context" not in source
    assert "inspect_certificate_declarations" not in source
    assert "condition_review" not in json_object(source["certificates"])
    assert len(certificate_sections(json_object(source["certificates"]), "en")) == 1


def test_report_subset_omits_unrelated_unprepared_device_entries(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reuse valid private device entries, but leave their selection unprepared.
    # A comparison-only report must not acquire an unrelated equipment scope.
    values = json_object(condition_project())
    setup = values.pop("equipment_selection")
    setup.pop("product_revisions")
    values["equipment_setup"] = setup
    project = workspace.create(owner, "Comparison only", values, key="subset")
    module = __import__(
        "linker_engine.planning.report_sources", fromlist=["report_sources"]
    )
    monkeypatch.setattr(module, "compare_energy_runs", lambda *args: {"fixture": True})
    monkeypatch.setattr(
        module,
        "comparison_side",
        lambda _workspace, _actor, _project, identity: SimpleNamespace(
            run=SimpleNamespace(
                id=identity,
                revision=1,
                manifest_sha256="c" * 64,
                result_sha256="d" * 64,
            ),
            result={
                "kind": "synthetic_saved_comparison",
                "input_sha256": "e" * 64,
                "runtime_sha256": context.code_sha256,
            },
            pinned={},
        ),
    )
    source = report_sources(
        workspace,
        ProductSources(
            lambda: pytest.fail("no equipment source belongs to this report")
        ),
        owner,
        project,
        ReportOptions.read(
            {
                "locale": "en",
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
                "comparison": {
                    "baseline_run_id": "a" * 32,
                    "candidate_run_id": "b" * 32,
                },
            }
        ),
    )
    assert source["equipment"] is None
    assert all(
        key not in source
        for key in (
            "equipment_condition_inputs",
            "certificate_context",
            "certificates",
            "inspect_certificate_declarations",
        )
    )
