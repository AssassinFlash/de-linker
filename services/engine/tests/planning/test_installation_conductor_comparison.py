"""Physical conductor choices compare only with the selected current source."""

from __future__ import annotations

import copy
from typing import cast

import pytest

from linker_engine.engine import Engine
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.project_input_contracts import (
    CONDUCTOR_MANUFACTURER_INPUT_CONTRACT,
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_installation_terminals import sample


def bound(
    pid: int, fact_id: str, kind: str, section: float
) -> tuple[FixtureObject, FixtureObject]:
    inputs, basis = sample(pid)
    plan = inputs["installation"]
    circuit, run, instance = (
        plan["circuits"][0],
        plan["cable_runs"][0],
        plan["instances"][0],
    )
    circuit["kind"] = kind
    circuit.pop("communication_use", None)
    run["construction"] = "single_conductor"
    run["conductor"] = {
        "cross_section_mm2": section,
        "source_note": "Private conductor note",
    }
    fact = next(
        item
        for item in basis["products"][0]["installation_facts"]["items"]
        if item["id"] == fact_id
    )
    run["manufacturer_comparison"] = {
        "instance_id": instance["id"],
        "product_id": pid,
        "product_revision": instance["product_revision"],
        "fact_id": fact_id,
        "document_id": fact["source"]["document_id"],
        "document_revision": fact["source"]["document_revision"],
        "conditions_confirmed": True,
        "confirmation_context": {
            "circuit": {k: circuit[k] for k in ("id", "kind", "start", "end")},
            "construction": run["construction"],
            "conductor": {**run["conductor"], "cable_reference": None},
            "core_roles": [],
        },
    }
    return inputs, basis


@pytest.mark.parametrize(
    ("pid", "fact", "kind", "section", "status", "page"),
    [
        (1946, "ac-conductor", "ac", 50, "within_recommendation", 155),
        (1946, "ac-conductor", "ac", 71, "outside_recommendation", 155),
        (
            1947,
            "protective-earth-conductor",
            "protective_earth",
            25,
            "within_recommendation",
            153,
        ),
        (
            1958,
            "battery-cluster-conductor",
            "battery_dc",
            50,
            "within_recommendation",
            50,
        ),
    ],
)
def test_current_manufacturer_instruction_for_actual_run(
    pid: int, fact: str, kind: str, section: float, status: str, page: int
) -> None:
    inputs, basis = bound(pid, fact, kind, section)
    review = json_object(route_takeoff(inputs, basis))
    result = review["cables"][0]["manufacturer_comparison"]
    assert result["status"] == status and result["qualified"] is False
    assert result["fact"]["source"]["page"] == page and review["qualified"] is False


def test_confirmation_source_and_product_changes_never_pass() -> None:
    inputs, basis = bound(1946, "ac-conductor", "ac", 50)
    changed = copy.deepcopy(inputs)
    changed["installation"]["cable_runs"][0]["conductor"]["cross_section_mm2"] = 70
    assert (
        json_object(route_takeoff(changed, basis))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "conditions_changed"
    )
    changed = copy.deepcopy(inputs)
    changed["installation"]["cable_runs"][0]["manufacturer_comparison"][
        "conditions_confirmed"
    ] = False
    assert (
        json_object(route_takeoff(changed, basis))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "conditions_not_confirmed"
    )
    changed = copy.deepcopy(basis)
    changed["products"][0]["installation_facts"]["items"] = [
        f
        for f in changed["products"][0]["installation_facts"]["items"]
        if f["id"] != "ac-conductor"
    ]
    assert (
        json_object(route_takeoff(inputs, changed))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "fact_unavailable"
    )
    changed = copy.deepcopy(basis)
    changed["products"][0]["documents"][0]["document_revision"] = "f" * 64
    assert (
        json_object(route_takeoff(inputs, changed))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "document_unavailable"
    )
    changed = copy.deepcopy(basis)
    fact = next(
        f
        for f in changed["products"][0]["installation_facts"]["items"]
        if f["id"] == "ac-conductor"
    )
    fact["conditions"] = [{"en": "only when applicable", "de": "nur sofern zutreffend"}]
    assert (
        json_object(route_takeoff(inputs, changed))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "conditions_not_assessed"
    )
    changed = copy.deepcopy(basis)
    changed["products"][0]["product_revision"] = "b" * 64
    assert (
        json_object(route_takeoff(inputs, changed))["cables"][0][
            "manufacturer_comparison"
        ]["status"]
        == "product_unavailable"
    )


def test_legacy_project_and_old_writer_protection() -> None:
    inputs, _ = bound(1946, "ac-conductor", "ac", 50)
    legacy = copy.deepcopy(inputs)
    legacy["installation"]["cable_runs"][0].pop("manufacturer_comparison")
    document = json_object(
        InstallationInputs.read(legacy["installation"]).project_document()
    )
    assert "manufacturer_comparison" not in document["cable_runs"][0]
    for before, after in ((legacy, inputs), (inputs, inputs), (inputs, legacy)):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(
                cast(Object, before), cast(Object, after), SUPPORTED_INPUT_CONTRACTS[-2]
            )
    require_input_contract(
        cast(Object, legacy),
        cast(Object, inputs),
        CONDUCTOR_MANUFACTURER_INPUT_CONTRACT,
    )


def test_frozen_report_pdf_csv_and_assistant_projection() -> None:
    import io

    from pypdf import PdfReader

    from linker_engine import pdf
    from linker_engine.planning.assistant_context import _report_source_projection
    from linker_engine.planning.project_materials import (
        materials_csv,
        project_materials,
    )
    from linker_engine.planning.report_model import build_report

    from .test_project_materials import _source_data

    inputs, basis = bound(1946, "ac-conductor", "ac", 50)
    source = _source_data()
    source.update(
        installation=json_object(route_takeoff(inputs, basis)),
        title="Fixture",
        locale="en",
    )
    source["materials"] = project_materials(cast(Object, source))
    for locale in ("en", "de"):
        source["locale"] = locale
        rendered = " ".join(
            " ".join(page.extract_text().split())
            for page in PdfReader(
                io.BytesIO(pdf.render(build_report(cast(Object, source))))
            ).pages
        )
        exported = materials_csv(
            cast(Object, source["materials"]), "0" * 64, locale
        ).decode("utf-8-sig")
        projection = str(_report_source_projection(cast(Object, source), locale))
        assert "50 mm²" in rendered and "p. 155" in rendered
        assert "within_recommendation" in exported and "155" in exported
        assert "within_recommendation" in projection and "155" in projection
        assert "Private conductor note" not in projection


def test_native_woo_save_review_worker_and_retained_outputs(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace
    from types import SimpleNamespace

    from conftest import publication_manifest
    from fastapi.testclient import TestClient

    from linker_engine.planning.energy_kernel import EnergyKernel
    from linker_engine.planning.energy_service import EnergyService
    from linker_engine.planning.execution_registry import service_registry
    from linker_engine.planning.http_app import HttpLimits, create_private_app
    from linker_engine.planning.jobs import Jobs
    from linker_engine.planning.product_sources import ProductProvider, ProductSources
    from linker_engine.planning.report_kernel import ReportKernel, ReportService
    from linker_engine.planning.worker import Worker
    from linker_engine.products import Products
    from linker_engine.publication import Publication

    from .test_energy_kernel import TOLERANCE
    from .test_installation_terminals import real_projection
    from .test_private_http import TOKEN, headers

    feed = copy.deepcopy(request.getfixturevalue("equipment_feed"))
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    product = next(p for p in feed["products"] if p["id"] == 1956)
    document = product["documents"][0]
    facts = real_projection(1956)["installation_facts"]
    for fact in facts["items"]:
        fact["source"].update(
            product_id=1956,
            document_id=document["document_id"],
            document_revision=document["document_revision"],
            blob_sha256=document["blob_sha256"],
            url=document["url"],
        )
    product["installation_facts"] = facts
    manifest = publication_manifest(feed)
    for row in manifest["products"]:
        row["ready"]["engineering"] = True
    publication = Publication(feed)
    monkeypatch.setattr(publication, "read", lambda: manifest)
    shared = cast(
        ProductProvider,
        SimpleNamespace(
            engine=replace(engine, products=Products.from_feed(feed)),
            publication=publication,
            version="synthetic-loaded-generation",
        ),
    )
    sources = ProductSources(lambda: shared)
    inputs, _ = bound(1956, "battery-cluster-conductor", "battery_dc", 50)
    for device in inputs["installation"]["instances"]:
        device["product_revision"] = product["product_revision"]
    binding = inputs["installation"]["cable_runs"][0]["manufacturer_comparison"]
    binding.update(
        product_revision=product["product_revision"],
        document_id=document["document_id"],
        document_revision=document["document_revision"],
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    reports = ReportService(workspace, ReportKernel(workspace, sources), max_attempts=1)
    registry = service_registry(energy, None, None, None, None, reports)
    worker = Worker(
        Jobs(workspace),
        "conductor-report",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        product_provider=lambda: shared,
        reports=reports,
    )
    with TestClient(app) as client:
        created = client.post(
            "/projects/create",
            json={
                "schema_version": 1,
                "title": "Synthetic conductor comparison",
                "inputs": inputs,
                "key": "conductor-project",
                "input_contract": CONDUCTOR_MANUFACTURER_INPUT_CONTRACT,
            },
            headers=headers(owner),
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]
        reviewed = client.post(
            "/installation/review",
            json={
                "schema_version": 1,
                "project_id": project_id,
                "expected_revision": 1,
                "geometry": inputs["geometry"],
                "installation": inputs["installation"],
                "bind_geometry": False,
            },
            headers=headers(owner),
        )
        assert reviewed.status_code == 200, reviewed.text
        assert (
            reviewed.json()["cables"][0]["manufacturer_comparison"]["status"]
            == "within_recommendation"
        )
        for locale in ("en", "de"):
            options = {
                "locale": locale,
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
                "include_installation": True,
            }
            queued = client.post(
                "/runs/report",
                json={
                    "schema_version": 1,
                    "project_id": project_id,
                    "expected_revision": 1,
                    "key": "conductor-report-" + locale,
                    "options": options,
                },
                headers=headers(owner),
            )
            assert queued.status_code == 200, queued.text
            assert worker.run_once()
            completed = client.post(
                "/runs/read",
                json={"schema_version": 1, "run_id": queued.json()["id"]},
                headers=headers(owner),
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["state"] == "succeeded", completed.json()
            result = json_object(completed.json()["result"])
            assert result["revision"] == 1
            frozen = json_object(
                workspace.blobs.object(result["dependencies"]["report_source"])
            )
            assert (
                frozen["installation"]["cables"][0]["manufacturer_comparison"]["status"]
                == "within_recommendation"
            )

            def content(asset_id: str) -> bytes:
                response = client.post(
                    "/assets/content",
                    json={
                        "schema_version": 1,
                        "project_id": project_id,
                        "asset_id": asset_id,
                    },
                    headers=headers(owner),
                )
                assert response.status_code == 200, response.text
                return response.content

            pdf_bytes = content(result["prepared_asset"]["id"])
            csv_bytes = content(
                result["prepared_attachments"]["bill_of_materials_csv"]["id"]
            )
            import io

            from pypdf import PdfReader

            words = " ".join(
                " ".join(page.extract_text().split())
                for page in PdfReader(io.BytesIO(pdf_bytes)).pages
            )
            assert "50 mm²" in words and "p. 50" in words
            assert b"within_recommendation" in csv_bytes
            assistant = client.post(
                "/projects/assistant",
                json={
                    "schema_version": 1,
                    "project_id": project_id,
                    "revision": 1,
                    "run_ids": [queued.json()["id"]],
                    "locale": locale,
                },
                headers=headers(owner),
            )
            assert assistant.status_code == 200, assistant.text
            assistant_text = str(assistant.json())
            assert "50 mm²" in assistant_text and "p. 50" in assistant_text
            assert "Private conductor note" not in assistant_text
