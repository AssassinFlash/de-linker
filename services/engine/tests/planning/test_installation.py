"""Physical route semantics, owned preview and frozen report share one fixture."""

from __future__ import annotations

import copy
import csv
import io
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.engine import Engine
from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import _result_rows
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import InvalidInput, ProductEvidenceChanged
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_report import installation_sections
from linker_engine.planning.installation_takeoff import product_basis, route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import INPUT_CONTRACT
from linker_engine.planning.project_materials import material_scope, project_materials
from linker_engine.planning.records import Actor
from linker_engine.planning.report_copy import text
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import ReportInputsChanged, report_sources
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_energy_kernel import TOLERANCE
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_equipment import inputs
from .test_geometry import fixture
from .test_private_http import TOKEN, headers


def test_physical_lengths_unknowns_and_owned_frozen_exports(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")

    def current(self: Publication) -> FixtureObject:
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
    basis = json_object(sources.equipment_basis())
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

    def point(e: float, n: float, h: float) -> dict[str, float]:
        return {"east_m": e, "north_m": n, "height_m": h}

    start, end = point(0, 0, 1), point(6, 8, 5)
    plan: FixtureObject = {
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
    selected = json_object(product_basis(InstallationInputs.read(plan), basis))
    assert [p["product_id"] for p in selected["publication"]["products"]] == [4107]
    output = json_object(route_takeoff(saved, basis))
    assert len(output["instances"]) == 2 and output["qualified"] is False
    assert [
        (c["plan_length_m"], c["route_length_m"], c["quantity"])
        for c in output["cables"]
    ] == [(10, 14, 16)] * 3
    assert len(output["sources"]) == 1
    # Optional linking must leave historical prepared bytes and hashes intact.
    # An undeclared conductor is not invented into the frozen bytes either.
    assert output["prepared_inputs"] == json_object(
        InstallationInputs.read(plan).project_document()
    )
    assert output["input_sha256"] == digest(encode(output["prepared_inputs"]))
    assert "pv_string_links" not in output["prepared_inputs"]
    assert all("conductor" not in c for c in output["prepared_inputs"]["cable_runs"])
    assert "pv_string_reconciliation" not in output
    assert all(
        c["conductor"] is None and c["specification"] == "open"
        for c in output["cables"]
    )

    # An omitted conductor and an explicit null describe the same physical run,
    # so both drop the key: one project cannot freeze into two input hashes.
    explicit_null = copy.deepcopy(saved)
    for run in explicit_null["installation"]["cable_runs"]:
        run["conductor"] = None
    assert (
        json_object(route_takeoff(explicit_null, basis))["input_sha256"]
        == (output["input_sha256"])
    )
    assert (
        json_object(route_takeoff(explicit_null, basis))["prepared_inputs"]
        == output["prepared_inputs"]
    )

    linked = copy.deepcopy(saved)
    linked["installation"]["circuits"][0]["kind"] = "pv_dc"
    linked["installation"]["instances"][1].update(
        product_id=None, product_revision=None
    )
    # These are saved project declarations, not an electrical assessment of
    # module assignments or the manufacturer's physical terminal map.
    linked["pv_string_plan"] = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "minimum_ambient_c": None,
        "temperature_source": None,
        "strings": [
            {"id": key, "mppt": index, "input": 1, "module_ids": [f"declared_{index}"]}
            for index, key in enumerate(("private_string_a", "private_string_b"), 1)
        ],
    }
    linked["installation"]["pv_string_links"] = [
        {"string_id": "private_string_a", "circuit_id": "ac"}
    ]
    linked_review = json_object(route_takeoff(linked, basis))
    reconciliation = linked_review["pv_string_reconciliation"]
    assert reconciliation["pv_string_plan_sha256"] == digest(
        encode(linked["pv_string_plan"])
    )
    assert reconciliation["installation_input_sha256"] == linked_review["input_sha256"]
    assert reconciliation["qualified"] is False
    assert [(r["string_id"], r["status"]) for r in reconciliation["rows"]] == [
        ("private_string_a", "linked"),
        ("private_string_b", "unlinked"),
    ]
    assert [c["quantity"] for c in reconciliation["rows"][0]["cable_runs"]] == [16] * 3
    # No run declares a cross-section, so the linkage is not yet a closed BOM:
    # the identities and lengths are recorded and the specification stays open.
    assert reconciliation["rows"][0]["closure"] == {
        "conductor": "unconfirmed",
        "quantity": "confirmed",
        "recorded": False,
        "approval": "not_assessed",
    }
    declared = copy.deepcopy(linked)
    for cable in declared["installation"]["cable_runs"]:
        cable["conductor"] = {
            "cross_section_mm2": 6,
            "source_note": "Synthetic project declaration for this fixture",
        }
    declared_review = json_object(route_takeoff(declared, basis))
    declared_rows = declared_review["pv_string_reconciliation"]["rows"]
    assert declared_rows[0]["closure"] == {
        "conductor": "declared",
        "quantity": "confirmed",
        "recorded": True,
        "approval": "not_assessed",
    }
    # An unlinked string stays open even when every run is fully specified.
    assert declared_rows[1]["closure"]["recorded"] is False
    assert [c["conductor"]["cross_section_mm2"] for c in declared_review["cables"]] == [
        6
    ] * 3
    # One specification per physical run; a differing section is a real conflict
    # rather than a silent choice of one value.
    conflicting = copy.deepcopy(declared)
    conflicting["installation"]["cable_runs"][1]["conductor"]["cross_section_mm2"] = 10
    assert (
        json_object(route_takeoff(conflicting, basis))["pv_string_reconciliation"][
            "rows"
        ][0]["closure"]["conductor"]
        == "conflicting"
    )
    # A run left undeclared keeps the circuit open and is never filled in.
    partial = copy.deepcopy(declared)
    partial["installation"]["cable_runs"][2].pop("conductor")
    partial_review = json_object(route_takeoff(partial, basis))
    assert partial_review["pv_string_reconciliation"]["rows"][0]["closure"] == {
        "conductor": "unconfirmed",
        "quantity": "confirmed",
        "recorded": False,
        "approval": "not_assessed",
    }
    assert [c["specification"] for c in partial_review["cables"]] == [
        "declared",
        "declared",
        "open",
    ]
    # Declared conductor bytes are frozen input, so the hash covers them.
    assert declared_review["prepared_inputs"]["cable_runs"][0]["conductor"] == {
        "cross_section_mm2": 6,
        "source_note": "Synthetic project declaration for this fixture",
    }
    assert declared_review["input_sha256"] == digest(
        encode(declared_review["prepared_inputs"])
    )
    renamed = copy.deepcopy(linked)
    renamed["pv_string_plan"]["strings"].reverse()
    renamed["installation"]["circuits"][0]["name"] = "Renamed circuit"
    assert {
        r["string_id"]: r["status"]
        for r in json_object(route_takeoff(renamed, basis))["pv_string_reconciliation"][
            "rows"
        ]
    } == {"private_string_a": "linked", "private_string_b": "unlinked"}
    for missing in ("string", "circuit"):
        stale_link = copy.deepcopy(linked)
        if missing == "string":
            stale_link["pv_string_plan"]["strings"].pop(0)
        else:
            stale_link["installation"]["pv_string_links"][0]["circuit_id"] = (
                "removed_circuit"
            )
        stale_review = json_object(route_takeoff(stale_link, basis))
        assert (
            stale_review["prepared_inputs"]["pv_string_links"]
            == stale_link["installation"]["pv_string_links"]
        )
        assert (
            next(
                r
                for r in stale_review["pv_string_reconciliation"]["rows"]
                if r["string_id"] == "private_string_a"
            )["status"]
            == "stale_" + missing
        )
    competing = copy.deepcopy(linked["installation"])
    competing["pv_string_links"].append(
        {"string_id": "private_string_b", "circuit_id": "ac"}
    )
    with pytest.raises(InvalidInput):
        InstallationInputs.read(competing)
    wrong_kind = copy.deepcopy(linked)
    wrong_kind["installation"]["circuits"][0]["kind"] = "ac"
    assert (
        json_object(route_takeoff(wrong_kind, basis))["pv_string_reconciliation"][
            "rows"
        ][0]["status"]
        == "wrong_circuit_kind"
    )
    ambiguous_endpoint = copy.deepcopy(linked)
    ambiguous_endpoint["installation"]["instances"][1].update(
        product_id=4107, product_revision=inverter["product_revision"]
    )
    assert (
        json_object(route_takeoff(ambiguous_endpoint, basis))[
            "pv_string_reconciliation"
        ]["rows"][0]["status"]
        == "inverter_endpoint_unresolved"
    )
    unlinked = copy.deepcopy(linked)
    unlinked["installation"]["pv_string_links"] = []
    assert all(
        r["status"] == "unlinked"
        for r in json_object(route_takeoff(unlinked, basis))[
            "pv_string_reconciliation"
        ]["rows"]
    )
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
        rows = json_object(route_takeoff(draft, basis))["cables"]
        assert all(c["quantity"] is None and reason in c["reasons"] for c in rows), (
            field,
            rows,
        )
    unsafe = copy.deepcopy(saved)
    unsafe["installation"]["routes"][0]["source_id"] = "absent"
    unsafe["geometry"]["sources"][0]["permissions"]["export"] = "prohibited"
    assert {"source_missing", "source_export_unconfirmed"} <= set(
        json_object(route_takeoff(unsafe, basis))["cables"][0]["reasons"]
    )
    false_fact = copy.deepcopy(plan)
    false_fact["instances"][0]["rated_kw"] = 10
    with pytest.raises(InvalidInput):
        InstallationInputs.read(false_fact)
    stale = copy.deepcopy(plan)
    stale["instances"][0]["product_revision"] = "a" * 64
    with pytest.raises(ProductEvidenceChanged):
        json_object(product_basis(InstallationInputs.read(stale), basis))

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
    legacy_project = project
    project = workspace.revise(
        owner,
        project.id,
        1,
        linked,
        key="save-declared-links",
        input_contract=INPUT_CONTRACT,
    )
    no_cables = copy.deepcopy(unlinked)
    no_cables["installation"]["cable_runs"] = []
    legacy_options: FixtureObject = {
        "locale": "en",
        "energy_run_id": None,
        "pv_run_id": None,
        "equipment_run_id": None,
        "logo": None,
    }
    assert json_object(ReportOptions.read(legacy_options).intent()) == {
        "kind": "planning_report_v1",
        "options_sha256": digest(encode(legacy_options)),
    }
    # Explicit [] can produce an unresolved, source-bound report without a
    # fabricated cable. This exercises the changed report admission branch.
    unresolved_source = json_object(
        report_sources(
            workspace,
            sources,
            owner,
            replace(project, inputs=no_cables),
            ReportOptions.read({**legacy_options, "include_installation": True}),
        )
    )
    assert all(
        r["quantity"] is None
        for r in json_object(project_materials(unresolved_source))["lines"]
    )
    assert (
        len(unresolved_source["installation"]["pv_string_reconciliation"]["rows"]) == 2
    )
    # A circuit with no recorded run is the fourth closure state; every state
    # must resolve to its own copy in both locales rather than raise.
    blank_rows = unresolved_source["installation"]["pv_string_reconciliation"]["rows"]
    assert {row["closure"]["conductor"] for row in blank_rows} == {"not_recorded"}
    for locale in ("en", "de"):
        rendered = installation_sections(unresolved_source, locale)
        links = next(s for s in rendered if s.id == "installation-pv-string-links")
        assert links.table is not None
        assert all(row[5] for row in links.table.rows)
        assert any(
            text("installation_conductor_not_recorded", locale) == row[5]
            for row in links.table.rows
        )
        # A report saved before the closure existed keeps its rows and says the
        # closure was not recorded, instead of raising or inventing one.
        historical = copy.deepcopy(unresolved_source)
        for row in historical["installation"]["pv_string_reconciliation"]["rows"]:
            row.pop("closure")
        legacy_rendered = installation_sections(historical, locale)
        legacy_links = next(
            s for s in legacy_rendered if s.id == "installation-pv-string-links"
        )
        assert legacy_links.table is not None
        assert all(
            row[6] == text("installation_closure_not_recorded", locale)
            for row in legacy_links.table.rows
        )
        assert all(
            row[5] == text("installation_conductor_not_recorded", locale)
            for row in legacy_links.table.rows
        )
    mixed = ReportOptions.read(
        {**legacy_options, "equipment_run_id": checked.id, "include_installation": True}
    )
    with pytest.raises(ReportInputsChanged):
        json_object(report_sources(workspace, sources, owner, legacy_project, mixed))
    unsafe_project = replace(project, inputs=unsafe)
    with pytest.raises(InvalidInput, match="export permission") as rejected:
        json_object(
            report_sources(
                workspace,
                sources,
                owner,
                unsafe_project,
                ReportOptions.read({**legacy_options, "include_installation": True}),
            )
        )
    assert rejected.value.code == "report_source_export_required"
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
        legacy_review = client.post(
            "/installation/review", json=body, headers=headers()
        ).json()
        assert legacy_review["cables"][0]["quantity"] == 16
        assert "project_revision" not in legacy_review
        linked_body = {**body, "installation": linked["installation"]}
        stale_response = client.post(
            "/installation/review",
            json={**linked_body, "expected_revision": 1},
            headers=headers(),
        )
        assert stale_response.status_code == 409
        assert stale_response.json()["error"]["code"] == "conflict"
        owned_review = client.post(
            "/installation/review",
            json={**linked_body, "expected_revision": project.revision},
            headers=headers(),
        ).json()
        assert owned_review["project_revision"] == project.revision
        assert owned_review["pv_string_reconciliation"][
            "pv_string_plan_sha256"
        ] == digest(encode(linked["pv_string_plan"]))
        assert owned_review["pv_string_reconciliation"]["rows"][0]["status"] == "linked"
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
                    "expected_revision": project.revision,
                    "key": "routes-" + locale,
                    "options": options,
                },
                headers=headers(),
            )
            assert accepted.status_code == 200, accepted.text
            assert worker.run_once()
            run = workspace.run(owner, accepted.json()["id"])
            assert run.state == "succeeded", run.error
            result = json_object(run.result)
            assert not any(s["id"] == "basis" for s in result["report"]["sections"])
            materials = json_object(workspace.blobs.object(result["materials_sha256"]))
            assert (
                materials["kind"] == "project_materials_v3"
                and len(materials["lines"]) == 5
            )
            assert {r["handling"] for r in materials["lines"]} == {
                "installation_requirement"
            }
            assert all(r["quantity"] == 16 for r in materials["lines"][:3])
            assert all(r["quantity"] is None for r in materials["lines"][3:])
            export = result["prepared_attachments"]["bill_of_materials_csv"]
            csv_bytes = Assets(workspace).content(owner, project.id, export["id"])
            rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
            assert len(rows) == 6 and all(
                float(r[2]) == 16 and r[7] == result["materials_sha256"]
                for r in rows[1:4]
            )
            link_source = json.loads(rows[4][6])["source"]
            assert (
                rows[4][2] == ""
                and link_source["link"]["string_id"] == "private_string_a"
            )
            assert link_source["pv_string_plan_sha256"] == digest(
                encode(linked["pv_string_plan"])
            )
            section = next(
                s
                for s in result["report"]["sections"]
                if s["id"] == "installation-pv-string-links"
            )
            assert section["table"]["rows"][1][3] == text(
                "installation_string_link_unlinked", locale
            )
            for assistant_locale in ("en", "de"):
                safe = encode(_result_rows(workspace, run, assistant_locale))
                assert b"private_string_" not in safe
                assert (
                    text(
                        "installation_string_unresolved_count", assistant_locale
                    ).encode()
                    in safe
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
        # The declared cross-section reaches every consumer of one frozen
        # revision: routing table, BOM scope, CSV provenance and the PDF.
        declared_project = workspace.revise(
            owner,
            project.id,
            project.revision,
            declared,
            key="save-declared-conductors",
            input_contract=INPUT_CONTRACT,
        )
        accepted = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": declared_project.revision,
                "key": "declared-conductors",
                "options": {**legacy_options, "include_installation": True},
            },
            headers=headers(),
        )
        assert accepted.status_code == 200, accepted.text
        assert worker.run_once()
        declared_run = workspace.run(owner, accepted.json()["id"])
        assert declared_run.state == "succeeded", declared_run.error
        declared_result = json_object(declared_run.result)
        routing = next(
            s
            for s in declared_result["report"]["sections"]
            if s["id"] == "installation-routing"
        )
        assert [row[4] for row in routing["table"]["rows"]] == ["6 mm²"] * 3
        declared_materials = json_object(
            workspace.blobs.object(declared_result["materials_sha256"])
        )
        cable_lines = [
            line
            for line in declared_materials["lines"]
            if line["handling"] == "installation_requirement"
            and line.get("quantity") is not None
        ]
        assert [
            line["source"]["conductor"]["cross_section_mm2"] for line in cable_lines
        ] == [6] * 3
        assert text("material_installation_declared", "en") in material_scope(
            cable_lines[0], "en"
        )
        declared_csv = Assets(workspace).content(
            owner,
            project.id,
            declared_result["prepared_attachments"]["bill_of_materials_csv"]["id"],
        )
        declared_rows = list(csv.reader(io.StringIO(declared_csv.decode("utf-8-sig"))))
        provenance = json.loads(declared_rows[1][6])["source"]
        assert provenance["conductor"]["cross_section_mm2"] == 6
        assert declared_rows[1][5] == text("material_installation_declared", "en")
        declared_pdf = Assets(workspace).content(
            owner, project.id, declared_result["prepared_asset"]["id"]
        )
        declared_shown = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(declared_pdf)).pages
        )
        assert "6 mm²" in declared_shown
