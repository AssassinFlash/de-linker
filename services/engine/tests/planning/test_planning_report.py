"""One owned report path; old numerical fixtures and source studies are reused."""

from __future__ import annotations

import copy
import csv
import io
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine import pdf
from linker_engine.engine import Engine
from linker_engine.models import Report
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import _result_rows, assistant_context
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.certificate_evidence import CertificateEvidence
from linker_engine.planning.certificate_report import certificate_sections
from linker_engine.planning.certificate_sources import inspect_report_certificates
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.dc_energy_kernel import DcEnergyKernel
from linker_engine.planning.energy_inputs import EnergyInputs
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_conditions import review_device_conditions
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import (
    EvidenceMissing,
    InvalidInput,
    NotFound,
    ProductEvidenceChanged,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.frozen_profiles import frozen_profile
from linker_engine.planning.guest_claims import GuestClaims
from linker_engine.planning.handoffs import Handoffs
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.profile_assets import profile_dependencies
from linker_engine.planning.profile_import import ProfileImport
from linker_engine.planning.profile_preview import ProfilePreview
from linker_engine.planning.profile_selections import check_profile_selections
from linker_engine.planning.project_materials import materials_csv
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.pv_preparation import PvReferenceKernel
from linker_engine.planning.pv_reconstruction import PvReconstruction
from linker_engine.planning.pvgis_reference_artifacts import prepare_reference_asset
from linker_engine.planning.pvgis_reference_download import ReferenceCapture
from linker_engine.planning.pvgis_reference_geometry import reference_plan
from linker_engine.planning.pvgis_reference_kernel import PvgisRoofReferenceKernel
from linker_engine.planning.pvgis_response import PvgisCapture
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_copy import text
from linker_engine.planning.report_inputs import ComparisonSelection, ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_model import build_report
from linker_engine.planning.report_pvlib import pvlib_sections
from linker_engine.planning.report_sources import (
    ReportInputsChanged,
    renew_module_permission,
    report_sources,
)
from linker_engine.planning.worker import Control, Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable
from linker_engine.texts import t

from .conftest import FixtureObject, json_object, mapping_role
from .test_certificate_evidence import (
    certificate_pdf,
    condition_project,
    evidence,
    inspected_fixture,
)
from .test_energy_kernel import BATTERY, PROVENANCE, TOLERANCE, create_scenario
from .test_equipment import (
    feed as equipment_feed,  # noqa: F401 -- Shared cited fixture, registered under this name.
)
from .test_equipment import inputs
from .test_private_http import TOKEN, headers
from .test_pv_generation import geometry, parameter_document, weather
from .test_pvgis_roof_reference import limits as reference_limits
from .test_pvgis_roof_reference import prepared_reference_fixture


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
    # The wire accepts these full-length private entries. A single token and
    # a spaced note both need lossless continuation across PDF pages.
    long_model = "GW-" + "W" * 4093
    long_note = "W " * 2047 + "<&"
    declared = inputs["equipment_condition_inputs"]["devices"][0]
    declared.update(declared_model=long_model, source_note=long_note)
    source["condition_review"] = review_device_conditions(inputs, source)
    long_sections = certificate_sections(source, "en")
    device_section = next(s for s in long_sections if s.id == "certificate-device-0")
    assert {row.value for row in device_section.rows} >= {long_model, long_note}
    document = pdf.render(
        Report(
            title="Synthetic long device entries",
            subtitle="Lossless page continuation",
            generated_at="2026-10-27T00:00:00Z",
            locale="en",
            sections=long_sections,
        )
    )
    reader = PdfReader(io.BytesIO(document))
    # Page furniture must not interrupt a field continued onto another page.
    written = "".join(
        "".join(line.split())
        for number, page in enumerate(reader.pages, start=1)
        for line in page.extract_text().splitlines()
        if line not in {str(number), t("pdf.footer", "en"), t("pdf.credits", "en")}
    )
    assert long_model in written
    assert long_note.replace(" ", "") in written
    assert len(reader.pages) > 1


def test_roof_ac_reference_consumption_and_frozen_report_keep_actual_model_scope(
    client: TestClient,
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def current(publication: Publication) -> FixtureObject:
        value = publication_manifest(publication.feed)
        for product in value["products"]:
            product["ready"]["engineering"] = True
        return value

    monkeypatch.setattr(Publication, "read", current)
    assert isinstance(client.app, FastAPI)
    products = ProductSources(client.app.state.planning_product_provider)
    roof, asset = prepared_reference_fixture(workspace, owner, products)
    assets = Assets(workspace)
    profile = frozen_profile(
        workspace.blobs, asset.content_sha256, asset.metadata_sha256, None
    )
    assert profile.measurement == "pv_available_ac"
    preview = ProfilePreview(assets).page(
        owner, roof.id, asset.id, offset=0, page_size=1
    )
    assert preview["measurement"] == "pv_available_ac"
    assert len(json_object(preview)["rows"]) == 1
    assert len(profile.intervals) == 8784  # Complete leap calendar year 2020.
    choices: FixtureObject = {
        "schema_version": 1,
        "selected": {"pv_available_ac": asset.id},
    }
    check_profile_selections(assets, owner, roof.id, {"profile_selections": choices})
    with pytest.raises(InvalidInput):
        check_profile_selections(
            assets,
            owner,
            roof.id,
            {"profile_selections": {**choices, "selected": {"pv_reference": asset.id}}},
        )
    with pytest.raises(EvidenceMissing, match="pv_dc_stage"):
        profile_dependencies(asset, "pv_available_dc", roof.inputs, workspace.blobs)
    stale = copy.deepcopy(json_object(roof.inputs))
    stale["pvgis_reference"]["system_loss_percent"] = 15
    with pytest.raises(InvalidInput, match="saved roof or model choices"):
        profile_dependencies(asset, "pv_available_ac", stale, workspace.blobs)

    # A saved producer result selects this exact owned artifact. Producer
    # execution/transport are covered by the shared multi-array fixture.
    pv_run = workspace.evaluate(owner, roof.id, 1, context, key="pv", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(
        lease,
        {
            "kind": PvgisRoofReferenceKernel.kind,
            "runtime_sha256": context.code_sha256,
            "pinned_assets": {},
            "profile_summary": asset.metadata["interpretation"],
            "equipment_release": {"status": "not_assessed"},
            "country_assessment": {"status": "not_assessed"},
            "near_shading_assessment": {"status": "not_assessed"},
            "prepared_asset": {
                "id": asset.id,
                "project_id": roof.id,
                "purpose": asset.purpose,
                "content_sha256": asset.content_sha256,
                "metadata_sha256": asset.metadata_sha256,
                "metadata": asset.metadata,
            },
        },
    )
    explicit = report_sources(
        workspace,
        products,
        owner,
        roof,
        ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=pv_run.id,
            equipment_run_id=None,
            logo=None,
        ),
    )
    assert len(json_object(explicit)["pvgis_roof_ac_references"]) == 1
    for locale in ("en", "de"):
        context_view = json_object(
            assistant_context(workspace, owner, roof.id, 1, [pv_run.id], locale)
        )
        rows = {r["label"]: r["value"] for r in context_view["runs"][0]["rows"]}
        assert rows["reference_model_choices.year"] == "2020"
        assert rows["reference_model_choices.radiation_database"] == "PVGIS-ERA5"
        assert rows["reference_model_choices.pv_technology"] == "crystSi"
        assert rows["reference_model_choices.mounting_place"] == "free"
        assert rows["reference_model_choices.system_loss_percent"] == "14"
        assert rows["reference_model_choices.use_terrain_horizon"] is True
        assert rows["included_modules[0].quantity"] == "20"

    # Only two operating hours are replayed. The retained annual source is
    # read as supplied; no weather/PV model or annual physics is rerun here.
    source_ids: dict[str, str] = {}
    for role, power in (("gross_load", 2), ("aux_ac", 0)):
        source_ids[role] = (
            ProfileImport(assets)
            .csv(
                owner,
                roof.id,
                f"time,power\n2020-01-01T00:00:00Z,{power}\n2020-01-01T01:00:00Z,{power}\n".encode(),
                CsvMapping(
                    "time",
                    "power",
                    mapping_role(role),
                    "interval_average_kw",
                    "start",
                    "UTC",
                    "synthetic",
                    3600,
                    ",",
                    ".",
                ),
                PROVENANCE,
                key=role,
            )
            .id
        )
    battery = assets.add(
        owner,
        roof.id,
        encode(BATTERY),
        "application/json",
        "battery_parameters_v1",
        {"retention": "permanent", "provenance": PROVENANCE},
        key="battery",
    )
    values = json_object(roof.inputs)
    values["profile_selections"] = choices
    values["energy_replay"] = {
        "schema_version": 1,
        "gross_load_asset_id": source_ids["gross_load"],
        "critical_load_asset_id": None,
        "pv_available_asset_id": asset.id,
        "aux_ac_asset_id": source_ids["aux_ac"],
        "battery_parameters_asset_id": battery.id,
        "initial_inventory": {
            "pv_kwh": 0,
            "grid_kwh": 0,
            "initial_unknown_kwh": 0,
            "basis": "synthetic_fixture",
            "source_note": "Synthetic empty starting storage",
        },
        "schedule": [
            {
                "start_utc": "2020-01-01T00:00:00Z",
                "end_utc": "2020-01-01T02:00:00Z",
                "mode": "connected",
                "reserve_kwh": 0,
                "import_cap_kw": None,
                "export_cap_kw": 0,
                "pv_enabled": True,
                "allow_grid_charge": False,
            }
        ],
        "controller": "self_consumption_with_reserve_v1",
        "terminal_min_kwh": 0,
    }
    project = workspace.revise(owner, roof.id, 1, values, key="adopt-ac")
    energy_kernel = EnergyKernel(
        workspace, TOLERANCE, max_intervals=4, products=products
    )
    energy_run = EnergyService(workspace, energy_kernel, max_attempts=1).evaluate(
        owner, project.id, project.revision, key="energy"
    )
    energy_worker = Worker(
        jobs,
        "energy-reference",
        {"evaluate": energy_kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert energy_worker.run_once()
    assert workspace.run(owner, energy_run.id).state == "succeeded"
    options = ReportOptions(
        locale="en",
        energy_run_id=energy_run.id,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    reports = ReportService(
        workspace, ReportKernel(workspace, products), max_attempts=1
    )
    report_run = reports.evaluate(
        owner, project.id, project.revision, options, key="report"
    )
    pinned_source = json_object(report_run.manifest["context"])["assets"][
        "report.source"
    ]
    frozen = workspace.blobs.object(pinned_source)
    reference = json_object(frozen)["pvgis_roof_ac_references"][0]
    assert reference["parameters"] == values["pvgis_reference"]
    assert reference["used_by"] == [
        {"run_id": energy_run.id, "revision": 2, "binding": "pv_available_ac"}
    ]
    components = json_object(frozen)["pv_components"]
    assert components["status"] == "available"
    assert sum(c["quantity"] for c in components["components"]) == 20
    assert (
        components["components"][0]["model"]
        == values["geometry"]["module_specs"][0]["model"]
    )
    for locale, title, mounting in (
        ("en", "PVGIS roof AC reference", "Free-standing (free)"),
        ("de", "PVGIS-Referenz der AC-PV-Erzeugung", "Freistehend (free)"),
    ):
        model = build_report({**frozen, "locale": locale})
        section = next(s for s in model.sections if s.id == "pvgis-roof-reference-0")
        assert section.title == title
        displayed = {r.value for r in section.rows}
        assert {"2020", "PVGIS-ERA5", "crystSi", "14 %", mounting}.issubset(displayed)
        assert all(s.id != "pv" for s in model.sections)
        assert "source_note" not in values["pvgis_reference"]
        assert all(
            r.label != text("pvgis_reference_note", locale)
            for s in model.sections
            if s.id == "pvgis-roof-reference-0"
            for r in s.rows
        )
    changed = copy.deepcopy(values)
    changed["pvgis_reference"]["source_note"] = "Later project assumption"
    project = workspace.revise(owner, project.id, 2, changed, key="change-assumption")
    with pytest.raises(ReportInputsChanged):
        report_sources(workspace, products, owner, project, options)
    # Already admitted reports use their frozen assumption and original module
    # proof even if the current editable project has moved on.
    report_worker = Worker(
        jobs,
        "report-reference",
        {"evaluate": reports.kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert report_worker.run_once()
    completed = workspace.run(owner, report_run.id)
    assert completed.state == "succeeded", completed.error
    assert workspace.blobs.object(pinned_source) == frozen
    pdf_asset = json_object(completed.result)["prepared_asset"]
    reader = PdfReader(io.BytesIO(workspace.blobs.read(pdf_asset["content_sha256"])))
    written = "\n".join(page.extract_text() for page in reader.pages)
    assert "PVGIS roof AC reference" in written
    assert "Later project assumption" not in written

    # Reuse the completed two-hour result: changing a source note and an array
    # name changes its source identity without changing any numerical input.
    # The candidate original bytes/HTTP receipts are the retained first ones.
    candidate_values = copy.deepcopy(changed)
    candidate_values["geometry"]["arrays"][0]["name"] = "Candidate roof name"
    candidate_values["pvgis_reference"]["source_note"] = "Candidate frozen assumption"
    basis = json_object(asset.metadata["woo_module_inputs"])
    plan = reference_plan(
        candidate_values, workspace.blobs.put_object(basis), reference_limits(), 20_000
    )
    original = workspace.blobs.object(asset.content_sha256)
    captures = [
        ReferenceCapture(
            workspace.blobs.read(a["original_sha256"]),
            PvgisCapture.read(workspace.blobs.object(a["capture_sha256"])),
        )
        for a in json_object(original)["arrays"]
    ]
    publication, _ = prepare_reference_asset(
        workspace.blobs, project.id, 4, candidate_values, basis, plan, captures
    )
    candidate_asset = assets.add(
        owner,
        project.id,
        workspace.blobs.read(publication.content_sha256),
        publication.media_type,
        publication.purpose,
        workspace.blobs.object(publication.metadata_sha256),
        key="candidate-reference",
    )
    candidate_values["profile_selections"]["selected"]["pv_available_ac"] = (
        candidate_asset.id
    )
    candidate_values["energy_replay"]["pv_available_asset_id"] = candidate_asset.id
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        candidate_values,
        key="candidate-reference-inputs",
    )
    candidate_context = energy_kernel.context(owner, project.id, project.inputs)
    candidate_run = workspace.evaluate(
        owner,
        project.id,
        project.revision,
        candidate_context,
        key="candidate-result",
        max_attempts=1,
    )
    candidate_result = copy.deepcopy(
        json_object(workspace.run(owner, energy_run.id).result)
    )
    candidate_result.update(
        revision=project.revision,
        input_sha256=project.input_sha256,
        manifest_sha256=candidate_run.manifest_sha256,
        pinned_assets=candidate_context.assets,
    )
    lease = jobs.claim("comparison-fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(lease, candidate_result)
    candidate_reference = replace(
        workspace.run(owner, candidate_run.id),
        result={
            **json_object(workspace.run(owner, pv_run.id).result),
            "profile_summary": candidate_asset.metadata["interpretation"],
            "prepared_asset": {
                "id": candidate_asset.id,
                "project_id": project.id,
                "purpose": candidate_asset.purpose,
                "content_sha256": candidate_asset.content_sha256,
                "metadata_sha256": candidate_asset.metadata_sha256,
                "metadata": candidate_asset.metadata,
            },
        },
    )
    for locale in ("en", "de"):
        private_projection = _result_rows(workspace, candidate_reference, locale)
        assert "Candidate frozen assumption" not in str(private_projection)
        assert "PVGIS-ERA5" in str(private_projection)
    current_values = copy.deepcopy(candidate_values)
    current_values["pvgis_reference"]["source_note"] = (
        "Current unsimulated third assumption"
    )
    project = workspace.revise(
        owner, project.id, project.revision, current_values, key="third-assumption"
    )
    comparison_source = report_sources(
        workspace,
        products,
        owner,
        project,
        ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=None,
            logo=None,
            comparison=ComparisonSelection(
                baseline_run_id=energy_run.id, candidate_run_id=candidate_run.id
            ),
        ),
    )
    references = json_object(comparison_source)["pvgis_roof_ac_references"]
    assert len(references) == 2
    assert [r["parameters"].get("source_note") for r in references] == [
        None,
        "Candidate frozen assumption",
    ]
    assert [r["used_by"][0]["comparison_role"] for r in references] == [
        "baseline",
        "candidate",
    ]
    assert [r["used_by"][0]["run_id"] for r in references] == [
        energy_run.id,
        candidate_run.id,
    ]
    assert references[0]["geometry_sha256"] != references[1]["geometry_sha256"]
    assert all(
        sum(c["quantity"] for c in r["pv_components"]["components"]) == 20
        for r in references
    )
    assert comparison_source["pv_components"] is None  # Alternatives are never summed.
    for locale in ("en", "de"):
        compared = build_report({**comparison_source, "locale": locale})
        reference_sections = [
            s for s in compared.sections if s.id.startswith("pvgis-roof-reference-")
        ]
        assert len(reference_sections) == 2
        assert any(
            r.value == "Candidate frozen assumption"
            for s in reference_sections
            for r in s.rows
        )
        assert all(
            s.table is not None and s.table.rows[0][0] == "20"
            for s in reference_sections
        )
        assert (
            "Current unsimulated third assumption"
            not in encode(compared.model_dump(mode="json")).decode()
        )
        assert any(s.id == "comparison-values" for s in compared.sections)


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
    assert "pvgis_roof_ac_references" not in source
    assert "inspect_certificate_declarations" not in source
    assert "condition_review" not in json_object(source["certificates"])
    assert len(certificate_sections(json_object(source["certificates"]), "en")) == 1

    # A small, explicitly synthetic retained output exercises report projection,
    # not physical generation. No provider/model/energy calculation is invoked.
    roof = create_scenario(workspace, owner)
    geo, parameters = geometry(), parameter_document()
    geo["arrays"].append(
        {
            **geo["arrays"][0],
            "id": "other_array",
            "rows": 1,
            "columns": 1,
            "excluded_slots": [],
            "origin_uv": [15, 15],
        }
    )
    parameters["arrays"].append(
        {**copy.deepcopy(parameters["arrays"][0]), "array_id": "other_array"}
    )
    parameters["converters"].append(
        {
            **parameters["converters"][0],
            "id": "other_converter",
            "array_ids": ["other_array"],
        }
    )
    module_source = {
        **geo["module_specs"][0]["source"],
        "kind": "datasheet",
        "document_sha256": "c" * 64,
        "url": "https://de-linker.com/wp-content/uploads/synthetic-report-module.pdf",
        "page": 1,
        "woo": {
            "product_id": 999,
            "product_revision": "b" * 64,
            "reference_input_id": "synthetic_report_module",
        },
    }
    geo["module_specs"][0]["source"] = module_source
    parameters["modules"][0]["source"] = module_source
    module_proof = {
        "schema_version": 1,
        "module": {
            "specification": geo["module_specs"][0],
            "parameters": parameters["modules"][0],
        },
    }
    monkeypatch.setattr(products, "module_basis", lambda: module_proof)
    originals = workspace.blobs.put(
        b"Synthetic retained report weather, not provider data"
    )
    details = {
        "request": {"start_year": 2014, "end_year": 2023, "use_terrain_horizon": False},
        "capture": {
            "requested_url": "https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=52.52&lon=13.405&startyear=2014&endyear=2023&usehorizon=0&outputformat=json",
            "received_at_utc": "2026-10-28T00:00:00Z",
        },
        "interpretation": {"synthetic_energy_year": 2023},
        "radiation_database": "PVGIS-SARAH3",
        "meteo_database": "ERA5",
        "irradiance_time_offset_hours": 0.1805,
        "irradiance_offset_microseconds": 649800000,
        "months_selected": [{"month": 1, "year": 2014}],
        "solar_date_basis": "original_selected_year_plus_reported_irradiance_offset",
        "native_radiation_semantics": "sarah_instantaneous",
    }

    def retained(note: str, key: str) -> tuple[Any, Any]:
        par = copy.deepcopy(parameters)
        par["source_note"] = note
        typed = PvGenerationParameters.read(par).model_dump(mode="json")
        meteo = json_object(weather().document())
        meteo["source"].update(raw_sha256=originals, details=details)
        model_input = {
            "schema_version": 1,
            "kind": par["model"],
            "geometry": geo,
            "parameters": typed,
            "weather": meteo,
        }
        input_sha = workspace.blobs.put_object(model_input)
        axis: FixtureObject = {
            "intervals": [
                {"start_utc": p["start_utc"], "end_utc": p["end_utc"]}
                for p in meteo["points"]
            ]
        }
        # Retain only the identities actually included in the geometry.
        from linker_engine.planning.geometry import panel_poses, read_geometry

        poses = [p for p in panel_poses(read_geometry(geo)) if p.included]
        witness = {
            "schema_version": 1,
            "kind": par["model"],
            "available_ac_w": [1000],
            "energy_kwh": 1.0,
            "inputs": {
                "model": par["model"],
                "input_bundle_sha256": input_sha,
                "geometry_sha256": digest(encode(geo)),
                "parameters_sha256": digest(encode(typed)),
                "weather_document_sha256": digest(encode(meteo)),
                "weather_original_sha256": originals,
                "weather_source": meteo["source"],
                "temporal_policy": PvReconstruction(
                    input_sha, digest(encode(axis)), 3600, 3600.0
                ).document(),
            },
            "arrays": [
                {
                    "id": array_id,
                    "module_spec_id": "module",
                    "module_ids": [p.id for p in poses if p.array_id == array_id],
                    "module_count": sum(p.array_id == array_id for p in poses),
                    "stc_power_w": sum(
                        p.stc_power_w for p in poses if p.array_id == array_id
                    ),
                    "normal_enu": [0, 0, 1],
                    "tilt_deg": 0,
                    "azimuth_north_clockwise_deg": 0,
                    "azimuth_basis": "horizontal_orientation_invariant",
                }
                for array_id in ("array", "other_array")
            ],
            "converters": [
                {
                    "id": name,
                    "model_ac_cap_w": 9600,
                    "array_ids": arrays,
                    "input_assumption": "independent_mppt_array_mpp_sum",
                    "dc_available_w": [power],
                }
                for name, arrays, power in (
                    ("converter", ["array"], 1500),
                    ("other_converter", ["other_array"], 2500),
                )
            ],
        }
        metadata = {
            "schema": 1,
            "profile_type": "pvlib_reference_profile_v1",
            "retention": "permanent",
            "provenance": PROVENANCE,
            "derived_from_revision": roof.revision + 1,
            "geometry_sha256": digest(encode(geo)),
            "parameters_sha256": digest(encode(par)),
            "woo_module_inputs": module_proof,
            **{
                "weather_" + k: details[k]
                for k in ("request", "capture", "interpretation")
            },
            "dependencies": {
                "pv_model_inputs": input_sha,
                "pv_model_witness": workspace.blobs.put_object(witness),
            },
            "interpretation": {
                "energy_kwh": 1.0,
                "interval_count": 1,
                "start_utc": meteo["points"][0]["start_utc"],
                "end_utc": meteo["points"][0]["end_utc"],
            },
        }
        asset = Assets(workspace).add(
            owner,
            roof.id,
            workspace.blobs.read(originals),
            "application/json",
            "pvlib_reference_profile_v1",
            cast(Object, metadata),
            key=key,
        )
        values = json_object({**roof.inputs, "geometry": geo, "pv_generation": par})
        values["energy_replay"] = {
            **values["energy_replay"],
            "pv_available_asset_id": asset.id,
        }
        saved = workspace.revise(
            owner,
            roof.id,
            workspace.get(owner, roof.id).revision,
            values,
            key=key + "-inputs",
        )
        return saved, asset

    first, asset = retained("PRIVATE frozen first assumption", "retained-first")

    def completed(project: Any, result: dict[str, Any], key: str) -> Any:
        run = workspace.evaluate(
            owner, project.id, project.revision, context, key=key, max_attempts=1
        )
        lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
        assert lease is not None
        jobs.complete(
            lease,
            {
                **result,
                "runtime_sha256": context.code_sha256,
                "input_sha256": project.input_sha256,
            },
        )
        return workspace.run(owner, run.id)

    pv_run = completed(
        first,
        {
            "kind": PvReferenceKernel.kind,
            "pinned_assets": {},
            "profile_summary": asset.metadata["interpretation"],
            "prepared_asset": {
                "id": asset.id,
                "content_sha256": asset.content_sha256,
                "metadata_sha256": asset.metadata_sha256,
                "metadata": asset.metadata,
            },
        },
        "pvlib-source",
    )
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=pv_run.id,
        equipment_run_id=None,
        logo=None,
    )
    permission_checks: list[Object] = []

    def confirm_once(basis: Object, *, require_reference: bool = True) -> None:
        permission_checks.append(basis)

    monkeypatch.setattr(products, "confirm_basis", confirm_once)
    explicit = report_sources(workspace, products, owner, first, options)
    assert len(json_object(explicit)["pvlib_references"]) == 1
    assert len(permission_checks) == 1
    assert permission_checks[0] == module_proof
    with monkeypatch.context() as denied:

        def withdrawn(*args: Any, **kwargs: Any) -> None:
            raise ProductEvidenceChanged("current Woo permission changed")

        denied.setattr(products, "confirm_basis", withdrawn)
        with pytest.raises(ProductEvidenceChanged):
            report_sources(workspace, products, owner, first, options)
    for dependency in json_object(explicit)["dependencies"].values():
        workspace.blobs.read(dependency)
    pinned: dict[str, str] = {}
    for role, identity in EnergyInputs.from_project(first.inputs).profiles().items():
        pinned.update(
            profile_dependencies(
                Assets(workspace).get(owner, first.id, identity),
                role,
                first.inputs,
                workspace.blobs,
            )
        )
    energy_run = completed(
        first,
        {"kind": EnergyKernel.kind, "pinned_assets": pinned},
        "frozen-energy-source",
    )
    energy_source = report_sources(
        workspace,
        products,
        owner,
        first,
        options.model_copy(update={"pv_run_id": None, "energy_run_id": energy_run.id}),
    )
    assert (
        json_object(energy_source)["pvlib_references"][0]["used_by"][0]["run_id"]
        == energy_run.id
    )
    second, candidate_asset = retained(
        "PRIVATE frozen candidate assumption", "retained-candidate"
    )
    candidate_pinned = {
        **pinned,
        **profile_dependencies(
            candidate_asset, "pv_available_ac", second.inputs, workspace.blobs
        ),
    }
    candidate = completed(
        second,
        {"kind": EnergyKernel.kind, "pinned_assets": candidate_pinned},
        "frozen-energy-candidate",
    )
    import importlib

    source_module = importlib.import_module("linker_engine.planning.report_sources")
    monkeypatch.setattr(source_module, "compare_energy_runs", lambda *a: {})
    sides = {
        r.id: SimpleNamespace(
            run=r,
            result=r.result,
            pinned=r.result["pinned_assets"],
            inputs=p.inputs,
            scenario=EnergyInputs.from_project(p.inputs),
        )
        for r, p in ((energy_run, first), (candidate, second))
    }
    monkeypatch.setattr(source_module, "comparison_side", lambda *a: sides[a[-1]])
    comparison = report_sources(
        workspace,
        products,
        owner,
        second,
        options.model_copy(
            update={
                "pv_run_id": None,
                "comparison": ComparisonSelection(
                    baseline_run_id=energy_run.id, candidate_run_id=candidate.id
                ),
            }
        ),
    )
    references = json_object(comparison)["pvlib_references"]
    assert [r["parameters"]["source_note"] for r in references] == [
        "PRIVATE frozen first assumption",
        "PRIVATE frozen candidate assumption",
    ]
    assert [r["used_by"][0]["comparison_role"] for r in references] == [
        "baseline",
        "candidate",
    ]
    for locale in ("en", "de"):
        sections = pvlib_sections(comparison, locale)
        assert [s.id for s in sections] == ["pvlib-reference-0", "pvlib-reference-1"]
        shown = str([s.model_dump() for s in sections])
        assert "2014–2023" in shown and "0.1805" in shown and "0.9637" in shown
        assert "PRIVATE frozen first assumption" in shown and originals in shown

    # The same immutable source has two DC groups. A report's selected group
    # must follow its own frozen scenario, even when metadata hashes coincide.
    dc_runs = []
    dc_projects = []
    for converter_id in ("converter", "other_converter"):
        values = copy.deepcopy(json_object(first.inputs))
        values["energy_replay"].update(
            coupling="shared_dc", pv_converter_id=converter_id, aux_dc_kw=0
        )
        dc_project = workspace.revise(
            owner,
            first.id,
            workspace.get(owner, first.id).revision,
            values,
            key="dc-" + converter_id,
        )
        dc_pinned = {}
        for role, identity in (
            EnergyInputs.from_project(dc_project.inputs).profiles().items()
        ):
            dc_pinned.update(
                profile_dependencies(
                    Assets(workspace).get(owner, first.id, identity),
                    role,
                    dc_project.inputs,
                    workspace.blobs,
                )
            )
        dc_run = completed(
            dc_project,
            {"kind": DcEnergyKernel.kind, "pinned_assets": dc_pinned},
            "dc-source-" + converter_id,
        )
        dc_runs.append(dc_run)
        dc_projects.append(dc_project)
    selected_dc = report_sources(
        workspace,
        products,
        owner,
        dc_projects[0],
        options.model_copy(update={"pv_run_id": None, "energy_run_id": dc_runs[0].id}),
    )
    selected = json_object(selected_dc)["pvlib_references"][0]
    assert selected["converter_id"] == "converter"
    assert selected["profile_summary"]["measurement"] == "pv_available_dc"
    assert selected["profile_summary"]["energy_kwh"] == 1.5
    assert selected["used_by"][0]["converter_id"] == "converter"
    assert [a["id"] for a in selected["arrays"]] == ["array"]
    assert [c["id"] for c in selected["parameters"]["converters"]] == ["converter"]
    assert selected["pv_components"]["components"][0]["array_ids"] == ["array"]
    for locale in ("en", "de"):
        section = pvlib_sections(selected_dc, locale)[0]
        assert any(
            r.label == text("pvlib_dc_energy", locale) and r.value == "1.5 kWh"
            for r in section.rows
        )
        assert "other_converter" not in str(section.model_dump())
        assert "other_array" not in str(section.model_dump())
    both = report_sources(
        workspace,
        products,
        owner,
        dc_projects[0],
        options.model_copy(update={"energy_run_id": dc_runs[0].id}),
    )
    assert [r.get("converter_id") for r in json_object(both)["pvlib_references"]] == [
        "converter",
        None,
    ]
    full = json_object(both)["pvlib_references"][1]
    assert len(full["arrays"]) == len(full["parameters"]["converters"]) == 2
    assert full["profile_summary"]["energy_kwh"] == 1.0
    sides.update(
        {
            r.id: SimpleNamespace(
                run=r,
                result=r.result,
                pinned=r.result["pinned_assets"],
                inputs=p.inputs,
                scenario=EnergyInputs.from_project(p.inputs),
            )
            for r, p in zip(dc_runs, dc_projects, strict=True)
        }
    )
    grouped_comparison = report_sources(
        workspace,
        products,
        owner,
        dc_projects[1],
        options.model_copy(
            update={
                "pv_run_id": None,
                "comparison": ComparisonSelection(
                    baseline_run_id=dc_runs[0].id, candidate_run_id=dc_runs[1].id
                ),
            }
        ),
    )
    grouped = json_object(grouped_comparison)["pvlib_references"]
    assert (
        len(grouped) == 2
        and grouped[0]["metadata_sha256"] == grouped[1]["metadata_sha256"]
    )
    assert [r["converter_id"] for r in grouped] == ["converter", "other_converter"]
    assert [r["profile_summary"]["energy_kwh"] for r in grouped] == [1.5, 2.5]
    assert [r["used_by"][0]["comparison_role"] for r in grouped] == [
        "baseline",
        "candidate",
    ]

    # Deferring live permission checks never admits an asset with no Woo proof.
    missing = Assets(workspace).add(
        owner,
        first.id,
        workspace.blobs.read(originals),
        "application/json",
        asset.purpose,
        {k: v for k, v in asset.metadata.items() if k != "woo_module_inputs"},
        key="retained-missing-proof",
    )
    missing_inputs = copy.deepcopy(json_object(first.inputs))
    missing_inputs["energy_replay"]["pv_available_asset_id"] = missing.id
    missing_project = workspace.revise(
        owner,
        first.id,
        workspace.get(owner, first.id).revision,
        missing_inputs,
        key="missing-proof-inputs",
    )
    missing_run = completed(
        missing_project,
        {
            "kind": EnergyKernel.kind,
            "pinned_assets": {
                **pinned,
                **profile_dependencies(
                    missing, "pv_available_ac", missing_project.inputs, workspace.blobs
                ),
            },
        },
        "missing-proof-energy",
    )
    with pytest.raises(InvalidInput, match="current Woo-maintained module"):
        report_sources(
            workspace,
            products,
            owner,
            missing_project,
            options.model_copy(
                update={"pv_run_id": None, "energy_run_id": missing_run.id}
            ),
        )


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
    # Reuse valid two-hour profile inputs; no energy calculation is needed.
    project = create_scenario(workspace, owner)
    project = workspace.revise(
        owner,
        project.id,
        project.revision,
        {**project.inputs, **values},
        key="subset",
    )
    scenario = EnergyInputs.read(project.inputs["energy_replay"])
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
                revision=project.revision,
                manifest_sha256="c" * 64,
                result_sha256="d" * 64,
            ),
            result={
                "kind": "synthetic_saved_comparison",
                "input_sha256": "e" * 64,
                "runtime_sha256": context.code_sha256,
            },
            pinned={},
            inputs=project.inputs,
            scenario=scenario,
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
