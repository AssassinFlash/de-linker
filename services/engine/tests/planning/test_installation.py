"""Physical route semantics, owned preview and frozen report share one fixture."""

from __future__ import annotations

import copy
import csv
import io
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import InvalidInput, ProductEvidenceChanged
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_takeoff import product_basis, route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import ReportInputsChanged, report_sources
from linker_engine.planning.worker import Worker
from linker_engine.products import Products
from linker_engine.publication import Publication

from .test_energy_kernel import TOLERANCE
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_equipment import inputs
from .test_geometry import fixture
from .test_private_http import TOKEN, headers


def test_physical_lengths_unknowns_and_owned_frozen_exports(
    engine, workspace, owner, request, monkeypatch
):
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")

    def current(self):
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    sources = ProductSources(lambda: shared)
    basis = sources.equipment_basis()
    inverter = next(p for p in basis["products"] if p["id"] == 4107)
    geometry = fixture()
    for key in (
        "roofs",
        "arrays",
        "obstacles",
        "keepouts",
        "module_specs",
        "layout_rules",
    ):
        geometry[key] = []

    def point(e, n, h):
        return {"east_m": e, "north_m": n, "height_m": h}

    start, end = point(0, 0, 1), point(6, 8, 5)
    plan = {
        "schema_version": 1,
        "geometry_sha256": digest(encode(geometry)),
        "instances": [
            {
                "id": alias,
                "name": alias,
                "product_id": 4107,
                "product_revision": inverter["product_revision"],
                "source_id": "survey",
                "ports": [
                    {"id": "terminal", "name": "Recorded terminal", "position": p}
                ],
            }
            for alias, p in (("inverter_a", start), ("inverter_b", end))
        ],
        "circuits": [
            {
                "id": "ac",
                "name": "Recorded connection",
                "kind": "ac",
                "start": {"instance_id": "inverter_a", "port_id": "terminal"},
                "end": {"instance_id": "inverter_b", "port_id": "terminal"},
            }
        ],
        "routes": [
            {
                "id": "path",
                "name": "Horizontal and vertical route",
                "source_id": "survey",
                "points": [dict(start), point(3, 4, 1), point(3, 4, 5), dict(end)],
                "extra_length_m": 2,
                "extra_length_note": "Synthetic explicit 2 m allowance",
            }
        ],
        "cable_runs": [
            {
                "id": key,
                "name": name,
                "circuit_id": "ac",
                "route_id": "path",
                "construction": construction,
            }
            for key, name, construction in (
                ("multi", "Five-core cable", "multicore_cable"),
                ("plus", "Independent conductor A", "single_conductor"),
                ("minus", "Independent conductor B", "single_conductor"),
            )
        ],
    }
    saved = {**inputs(feed, 3), "geometry": geometry, "installation": plan}
    selected = product_basis(InstallationInputs.read(plan), basis)
    assert [p["product_id"] for p in selected["publication"]["products"]] == [4107]
    output = route_takeoff(saved, basis)
    assert len(output["instances"]) == 2 and output["qualified"] is False
    assert [
        (c["plan_length_m"], c["route_length_m"], c["quantity"])
        for c in output["cables"]
    ] == [(10, 14, 16)] * 3
    assert len(output["sources"]) == 1
    # Distinct missing facts never become guessed quantities. Combined missing
    # source + denied export also exercises the independent permission boundary.
    for field, value, reason in (
        ("geometry_sha256", None, "layout_confirmation_required"),
        ("height", None, "height_missing"),
        ("endpoint", 999, "route_endpoints_differ"),
        ("extra_length_note", None, "extra_length_unconfirmed"),
        ("source_id", "absent", "source_missing"),
    ):
        draft = copy.deepcopy(saved)
        if field == "height":
            draft["installation"]["routes"][0]["points"][1]["height_m"] = value
        elif field == "endpoint":
            draft["installation"]["routes"][0]["points"][0]["east_m"] = value
        elif field == "geometry_sha256":
            draft["installation"][field] = value
        else:
            draft["installation"]["routes"][0][field] = value
        rows = route_takeoff(draft, basis)["cables"]
        assert all(c["quantity"] is None and reason in c["reasons"] for c in rows), (
            field,
            rows,
        )
    unsafe = copy.deepcopy(saved)
    unsafe["installation"]["routes"][0]["source_id"] = "absent"
    unsafe["geometry"]["sources"][0]["permissions"]["export"] = "prohibited"
    assert {"source_missing", "source_export_unconfirmed"} <= set(
        route_takeoff(unsafe, basis)["cables"][0]["reasons"]
    )
    false_fact = copy.deepcopy(plan)
    false_fact["instances"][0]["rated_kw"] = 10
    with pytest.raises(InvalidInput):
        InstallationInputs.read(false_fact)
    stale = copy.deepcopy(plan)
    stale["instances"][0]["product_revision"] = "a" * 64
    with pytest.raises(ProductEvidenceChanged):
        product_basis(InstallationInputs.read(stale), basis)

    project = workspace.create(
        owner, "Physical routing fixture", saved, key="route-project"
    )
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, sources), max_attempts=1
    )
    reports = ReportService(workspace, ReportKernel(workspace, sources), max_attempts=1)
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    registry = service_registry(energy, None, None, equipment, None, reports)
    worker = Worker(
        Jobs(workspace),
        "routes",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    checked = equipment.evaluate(owner, project.id, 1, key="one-inverter-assessment")
    assert worker.run_once() and workspace.run(owner, checked.id).state == "succeeded"
    legacy_options = {
        "locale": "en",
        "energy_run_id": None,
        "pv_run_id": None,
        "equipment_run_id": None,
        "logo": None,
    }
    assert ReportOptions.read(legacy_options).intent() == {
        "kind": "planning_report_v1",
        "options_sha256": digest(encode(legacy_options)),
    }
    mixed = ReportOptions.read(
        {**legacy_options, "equipment_run_id": checked.id, "include_installation": True}
    )
    with pytest.raises(ReportInputsChanged):
        report_sources(workspace, sources, owner, project, mixed)
    unsafe_project = replace(project, inputs=unsafe)
    with pytest.raises(InvalidInput, match="export permission"):
        report_sources(
            workspace,
            sources,
            owner,
            unsafe_project,
            ReportOptions.read({**legacy_options, "include_installation": True}),
        )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        equipment=equipment,
        reports=reports,
        product_provider=lambda: shared,
    )
    with TestClient(app) as client:
        body = {
            "schema_version": 1,
            "project_id": project.id,
            "geometry": geometry,
            "installation": plan,
            "bind_geometry": True,
        }
        assert client.post("/installation/review", json=body).status_code == 401
        assert (
            client.post("/installation/review", json=body, headers=headers()).json()[
                "cables"
            ][0]["quantity"]
            == 16
        )
        foreign = {**headers(), "X-Linker-Planner-Principal-Subject": "wordpress:18"}
        assert (
            client.post("/installation/review", json=body, headers=foreign).status_code
            == 404
        )
        for locale in ("en", "de"):
            options = {**legacy_options, "locale": locale, "include_installation": True}
            accepted = client.post(
                "/runs/report",
                json={
                    "schema_version": 1,
                    "project_id": project.id,
                    "expected_revision": 1,
                    "key": "routes-" + locale,
                    "options": options,
                },
                headers=headers(),
            )
            assert accepted.status_code == 200, accepted.text
            assert worker.run_once()
            run = workspace.run(owner, accepted.json()["id"])
            assert run.state == "succeeded", run.error
            result = run.result
            assert not any(s["id"] == "basis" for s in result["report"]["sections"])
            materials = workspace.blobs.object(result["materials_sha256"])
            assert (
                materials["kind"] == "project_materials_v3"
                and len(materials["lines"]) == 3
            )
            assert {r["handling"] for r in materials["lines"]} == {
                "installation_requirement"
            }
            assert all(r["quantity"] == 16 for r in materials["lines"])
            export = result["prepared_attachments"]["bill_of_materials_csv"]
            csv_bytes = Assets(workspace).content(owner, project.id, export["id"])
            rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
            assert len(rows) == 4 and all(
                float(r[2]) == 16 and r[7] == result["materials_sha256"]
                for r in rows[1:]
            )
            pdf = Assets(workspace).content(
                owner, project.id, result["prepared_asset"]["id"]
            )
            shown = "\n".join(
                page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages
            )
            assert all(
                v in shown
                for v in ("Five-core cable", "16 m", "inverter_a", "inverter_b")
            )
            assert (
                "Installation routing" in shown
                if locale == "en"
                else "Leitungswege der Installation" in shown
            )
