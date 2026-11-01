"""One electrical chain: sourced core identity, independent sums, frozen consumers."""

from __future__ import annotations

import copy
import csv
import io
import json
import math
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
from linker_engine.planning.errors import (
    ProductEvidenceChanged,
    ProjectInputContractRequired,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    ELECTRICAL_INPUT_CONTRACT,
    PLANT_PV_INPUT_CONTRACT,
    require_input_contract,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_energy_kernel import TOLERANCE
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_geometry import fixture
from .test_private_http import TOKEN, headers


def cable_reference(
    pid: int, section: float, resistance: float, *, ac: bool = False, cores: int = 1
) -> FixtureObject:
    """Synthetic Woo/PDF binding around independently checked parameter values.

    DC values are the official Nexans 20°C maximum Rdc in CAPABILITY-MAP §10.
    AC values are explicit analytic fixtures, never claims about those cables.
    """
    sha = digest(f"synthetic-cable-{pid}".encode())
    document: FixtureObject = {
        "document_id": sha,
        "document_revision": sha,
        "blob_sha256": sha,
        "product_ids": [pid],
        "url": f"https://de-linker.com/wp-content/uploads/fixture-{pid}.pdf",
        "title": "Synthetic cable evidence",
        "type": "datasheet",
        "lang": "en",
    }
    source: FixtureObject = {
        key: document[key]
        for key in ("document_id", "document_revision", "blob_sha256", "url")
    }
    source.update(
        product_id=pid,
        page=1,
        quote="Synthetic retained binding, not a published product or manufacturer approval.",
    )
    row: FixtureObject = {
        "id": f"fixture_cable_{pid}",
        "kind": "cable",
        "canonical_product_id": pid,
        "brand": "Synthetic",
        "model": f"Cable {section} mm² / {cores} cores",
        "figures": {},
        "documents": [document],
        "cable_facts": {
            "schema_version": 1,
            "construction": "single_conductor" if cores == 1 else "multicore_cable",
            "core_count": cores,
            "cross_section_mm2": section,
            "conductor_material": "Tinned copper",
            "insulation": "Cross-linked rubber",
            "source": source,
            "parameter_sets": [
                {
                    "id": "ac_50_20" if ac else "dc_20",
                    "current_kind": "ac" if ac else "dc",
                    "temperature_c": 20,
                    "frequency_hz": 50 if ac else None,
                    "arrangement": "fixture_trefoil" if ac else None,
                    "resistance_ohm_per_km": resistance,
                    "reactance_ohm_per_km": 0.08 if ac else None,
                    "resistance_basis": "nominal" if ac else "maximum",
                    "source": source,
                }
            ],
        },
    }
    row["product_revision"] = digest(encode(row))
    row["reference_revision"] = row["product_revision"]
    return row


def circuit_fixture(
    *, ac: bool = False, three_phase: bool = False
) -> tuple[FixtureObject, FixtureObject]:
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
    point_a = {"east_m": 0, "north_m": 0, "height_m": 0}
    point_b = {"east_m": 10, "north_m": 0, "height_m": 0}
    refs = [
        cable_reference(9101, 4, 0.2 if ac else 5.09, ac=ac),
        cable_reference(9102, 6, 0.2 if ac else 3.39, ac=ac),
    ]
    condition = {
        "id": "steady",
        "name": "Declared design condition",
        "method": "ac_balanced_three_phase"
        if three_phase
        else "ac_two_wire"
        if ac
        else "dc_resistive",
        "current_a": 20,
        "reference_voltage_v": 400 if three_phase else 230 if ac else 600,
        "direction": "start_to_end",
        "conductor_temperature_c": 20,
        "frequency_hz": 50 if ac else None,
        "power_factor": 0.8 if ac else None,
        "reactive_direction": "lagging" if ac else None,
        "balanced": True if three_phase else None,
        "sinusoidal": True,
        "arrangement": "fixture_trefoil" if ac else None,
        "source_note": "Synthetic project load declaration",
        "voltage_limit": None,
    }
    roles = (
        ["l1", "l2", "l3"]
        if three_phase
        else ["line", "neutral"]
        if ac
        else ["dc_positive", "dc_negative"]
    )
    plan: FixtureObject = {
        "schema_version": 1,
        "geometry_sha256": digest(encode(geometry)),
        "instances": [
            {
                "id": key,
                "name": key,
                "product_id": None,
                "product_revision": None,
                "source_id": "survey",
                "ports": [
                    {"id": "terminal", "name": "Declared terminal", "position": point}
                ],
            }
            for key, point in (("source", point_a), ("load", point_b))
        ],
        "circuits": [
            {
                "id": "circuit",
                "name": "Declared connection",
                "kind": "ac" if ac else "pv_dc",
                "start": {"instance_id": "source", "port_id": "terminal"},
                "end": {"instance_id": "load", "port_id": "terminal"},
                "operating_conditions": [condition],
            }
        ],
        "routes": [
            {
                "id": f"route_{index}",
                "name": f"Measured route {index}",
                "source_id": "survey",
                "points": [point_a, point_b],
                "extra_length_m": 20,
                "extra_length_note": "Synthetic measured allowance",
            }
            for index in range(len(roles))
        ],
        "cable_runs": [
            {
                "id": f"run_{index}",
                "name": role,
                "circuit_id": "circuit",
                "route_id": f"route_{index}",
                "construction": "single_conductor",
                "core_roles": [role],
                "conductor": {
                    "cross_section_mm2": refs[min(index, 1)]["cable_facts"][
                        "cross_section_mm2"
                    ],
                    "source_note": "Selected Woo reference",
                    "cable_reference": {
                        "product_id": refs[min(index, 1)]["canonical_product_id"],
                        "product_revision": refs[min(index, 1)]["product_revision"],
                    },
                },
            }
            for index, role in enumerate(roles)
        ],
    }
    basis: FixtureObject = {
        "products": [],
        "cable_references": refs,
        "publication": {"products": [], "documents": [], "reference_inputs": []},
    }
    return {"geometry": geometry, "installation": plan}, basis


def condition_result(inputs: FixtureObject, basis: FixtureObject) -> FixtureObject:
    return json_object(
        json_object(route_takeoff(inputs, basis))["electrical"]["circuits"][0][
            "conditions"
        ][0]
    )


def test_asymmetric_dc_maximum_resistance_direction_limits_and_contract() -> None:
    inputs, basis = circuit_fixture()
    row = condition_result(inputs, basis)
    # Independent Nexans 4mm² positive + 6mm² negative at 30 m each (§10.3).
    assert row["status"] == "calculated" and row[
        "loop_resistance_ohm"
    ] == pytest.approx(0.2544)
    assert row["voltage_drop_v"] == pytest.approx(5.088)
    assert row["voltage_drop_percent"] == pytest.approx(0.848)
    assert row["conductor_loss_w"] == pytest.approx(101.76)
    assert row["end_minus_start_voltage_v"] == pytest.approx(-5.088)
    assert (
        row["resistance_basis"] == "maximum"
        and row["value_basis"] == "resistance_upper_bound"
    )
    assert row["limit"]["status"] == "not_declared" and not row["qualified"]
    condition = inputs["installation"]["circuits"][0]["operating_conditions"][0]
    condition.update(
        direction="end_to_start",
        voltage_limit={
            "maximum_percent": 0.8,
            "source_note": "Declared project limit only",
        },
    )
    reverse = condition_result(inputs, basis)
    assert reverse["end_minus_start_voltage_v"] == pytest.approx(5.088)
    assert reverse["conductor_loss_w"] == row["conductor_loss_w"]
    assert reverse["limit"]["status"] == "exceeds_declared_limit"
    # Two genuinely different physical lengths are summed once, without ×2.
    inputs["installation"]["routes"][1]["extra_length_m"] = 30
    unequal = condition_result(inputs, basis)
    assert unequal["loop_resistance_ohm"] == pytest.approx(0.2883)
    assert unequal["voltage_drop_v"] == pytest.approx(5.766)
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(inputs, {}, PLANT_PV_INPUT_CONTRACT)
    require_input_contract(inputs, {}, ELECTRICAL_INPUT_CONTRACT)


@pytest.mark.parametrize(
    ("three_phase", "expected_drop", "expected_loss"),
    [(False, 0.2496, 4.8), (True, math.sqrt(3) * 0.1248, 7.2)],
)
def test_ac_formula_and_active_core_count(
    three_phase: bool, expected_drop: float, expected_loss: float
) -> None:
    inputs, basis = circuit_fixture(ac=True, three_phase=three_phase)
    row = condition_result(inputs, basis)
    assert row["status"] == "calculated"
    assert row["voltage_drop_v"] == pytest.approx(expected_drop)
    assert row["conductor_loss_w"] == pytest.approx(expected_loss)
    condition = inputs["installation"]["circuits"][0]["operating_conditions"][0]
    condition["reactive_direction"] = "leading"
    assert condition_result(inputs, basis)["voltage_drop_v"] < expected_drop
    # One five-core purchase is three phase conductors plus non-current N/PE.
    if three_phase:
        reference = cable_reference(9103, 6, 0.2, ac=True, cores=5)
        basis["cable_references"].append(reference)
        run = inputs["installation"]["cable_runs"][0]
        run.update(
            construction="multicore_cable",
            core_roles=["l1", "l2", "l3", "neutral", "pe"],
            conductor={
                "cross_section_mm2": 6,
                "source_note": "Synthetic selection",
                "cable_reference": {
                    "product_id": 9103,
                    "product_revision": reference["product_revision"],
                },
            },
        )
        inputs["installation"]["cable_runs"] = [run]
        output = json_object(route_takeoff(inputs, basis))
        assert output["cables"][0]["quantity"] == 30
        result = output["electrical"]["circuits"][0]["conditions"][0]
        assert len(result["segments"]) == 3 and result[
            "conductor_loss_w"
        ] == pytest.approx(7.2)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("temperature", "cable_conditions_mismatch"),
        ("revision", "cable_reference_unavailable"),
        ("section", "cable_specification_mismatch"),
        ("roles", "core_roles_missing"),
        ("parallel", "parallel_or_branched_cores_not_supported"),
        ("route", "route_quantity_unconfirmed"),
        ("ambiguous", "cable_parameter_set_ambiguous"),
    ],
)
def test_evidence_and_current_path_fail_explicitly(mutation: str, reason: str) -> None:
    inputs, basis = circuit_fixture()
    plan = inputs["installation"]
    if mutation == "temperature":
        plan["circuits"][0]["operating_conditions"][0]["conductor_temperature_c"] = 70
    elif mutation == "revision":
        plan["cable_runs"][0]["conductor"]["cable_reference"]["product_revision"] = (
            "a" * 64
        )
    elif mutation == "section":
        plan["cable_runs"][0]["conductor"]["cross_section_mm2"] = 99
    elif mutation == "roles":
        plan["cable_runs"][0].pop("core_roles")
    elif mutation == "parallel":
        duplicate = copy.deepcopy(plan["cable_runs"][0])
        duplicate["id"] = "parallel"
        plan["cable_runs"].append(duplicate)
    elif mutation == "route":
        plan["routes"][0]["extra_length_m"] = None
    else:
        duplicate = copy.deepcopy(
            basis["cable_references"][0]["cable_facts"]["parameter_sets"][0]
        )
        duplicate["id"] = "duplicate"
        basis["cable_references"][0]["cable_facts"]["parameter_sets"].append(duplicate)
    row = condition_result(inputs, basis)
    assert row["status"] != "calculated" and reason in row["reasons"]
    assert all(
        row[key] is None
        for key in ("voltage_drop_v", "conductor_loss_w", "loop_resistance_ohm")
    )


def test_leading_ac_maximum_resistance_cannot_claim_absolute_limit() -> None:
    inputs, basis = circuit_fixture(ac=True)
    condition = inputs["installation"]["circuits"][0]["operating_conditions"][0]
    condition.update(
        reactive_direction="leading",
        voltage_limit={"maximum_percent": 0.04, "source_note": "Project limit"},
    )
    # A large Rmax cancels part of the negative reactive term. Lower actual R
    # may increase the rise magnitude, despite this result lying inside 0.04%.
    condition["power_factor"] = 0.1
    for reference in basis["cable_references"]:
        reference["cable_facts"]["parameter_sets"][0]["resistance_basis"] = "maximum"
    row = condition_result(inputs, basis)
    assert row["status"] == "calculated" and row["voltage_drop_v"] < 0
    assert abs(row["voltage_drop_percent"]) < 0.04
    assert row["limit"]["status"] == "not_evaluated"
    assert row["limit"]["reason"] == ("resistance_upper_bound_not_absolute_drop_bound")
    assert row["reasons"] == [] and row["conductor_loss_w"] == pytest.approx(4.8)
    condition["reactive_direction"] = "lagging"
    assert condition_result(inputs, basis)["limit"]["status"] != "not_evaluated"
    condition["reactive_direction"] = "leading"
    condition["current_a"] = 0
    assert condition_result(inputs, basis)["limit"]["status"] == "within_declared_limit"


@pytest.mark.parametrize("role", ["pe", "unused", "neutral"])
def test_non_current_cores_validate_identity_without_resistance(role: str) -> None:
    balanced = role == "neutral"
    inputs, basis = circuit_fixture(ac=balanced, three_phase=balanced)
    reference = cable_reference(9103, 6, 3.39, cores=5)
    reference["cable_facts"]["parameter_sets"] = []
    basis["cable_references"].append(reference)
    run = copy.deepcopy(inputs["installation"]["cable_runs"][0])
    run.update(
        id="non_current",
        construction="multicore_cable",
        core_roles=[role],
        conductor={
            "cross_section_mm2": 6,
            "source_note": "Synthetic non-current core selection",
            "cable_reference": {
                "product_id": 9103,
                "product_revision": reference["product_revision"],
            },
        },
    )
    inputs["installation"]["cable_runs"].append(run)
    # Five physical cores cannot be hidden behind one declared non-current role.
    invalid = condition_result(inputs, basis)
    assert invalid["status"] == "data_insufficient"
    assert "cable_specification_mismatch" in invalid["reasons"]
    assert invalid["voltage_drop_v"] is None
    run["core_roles"] = [role] + ["unused"] * 4
    complete = condition_result(inputs, basis)
    assert complete["status"] == "calculated" and complete["reasons"] == []
    assert all(row["run_id"] != run["id"] for row in complete["segments"])
    # No impedance parameters were provided for this zero-current cable, but
    # the selected product identity must remain current nonetheless.
    run["conductor"]["cable_reference"]["product_revision"] = "a" * 64
    stale = condition_result(inputs, basis)
    assert stale["status"] == "data_insufficient"
    assert "cable_reference_unavailable" in stale["reasons"]


def test_native_woo_selection_review_frozen_report_pdf_csv_and_revocation(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, fixture_basis = circuit_fixture()
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    feed["overlay"].extend(fixture_basis["cable_references"])
    Products.from_feed(
        feed
    )  # The committed feed schema validates this exact projection.

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
            if row["product_id"] in {9101, 9102}:
                row.update(
                    engineering_role="reference_cable",
                    engineering_id=f"fixture_cable_{row['product_id']}",
                )
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    sources = ProductSources(lambda: shared)
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    reports = ReportService(workspace, ReportKernel(workspace, sources), max_attempts=1)
    registry = service_registry(energy, None, None, None, None, reports)
    worker = Worker(
        Jobs(workspace),
        "electrical",
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
        reports=reports,
        product_provider=lambda: shared,
    )
    with TestClient(app) as client:
        available = client.post(
            "/products/current", json={"schema_version": 1}, headers=headers()
        )
        assert available.status_code == 200, available.text
        assert {
            row["canonical_product_id"] for row in available.json()["cable_references"]
        } == {9101, 9102}
        assert not any(
            row["id"] in {9101, 9102} for row in available.json()["products"]
        )
        create: FixtureObject = {
            "schema_version": 1,
            "key": "electrical-project",
            "title": "Electrical fixture",
            "inputs": inputs,
            "input_contract": ELECTRICAL_INPUT_CONTRACT,
        }
        forged = copy.deepcopy(create)
        forged["key"] = "forged"
        forged["inputs"]["installation"]["cable_runs"][0]["conductor"][
            "cross_section_mm2"
        ] = 99
        assert (
            client.post("/projects/create", json=forged, headers=headers()).status_code
            == 422
        )
        created = client.post("/projects/create", json=create, headers=headers())
        assert created.status_code == 200, created.text
        project = created.json()
        reviewed = client.post(
            "/installation/review",
            json={
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": project["revision"],
                "geometry": inputs["geometry"],
                "installation": inputs["installation"],
                "bind_geometry": False,
            },
            headers=headers(),
        )
        assert reviewed.status_code == 200, reviewed.text
        frozen = reviewed.json()["electrical"]["circuits"][0]["conditions"][0]
        assert frozen["voltage_drop_v"] == pytest.approx(5.088)
        for locale in ("en", "de"):
            accepted = client.post(
                "/runs/report",
                json={
                    "schema_version": 1,
                    "project_id": project["id"],
                    "expected_revision": project["revision"],
                    "key": "electrical-report-" + locale,
                    "options": {
                        "locale": locale,
                        "energy_run_id": None,
                        "pv_run_id": None,
                        "equipment_run_id": None,
                        "logo": None,
                        "include_installation": True,
                    },
                },
                headers=headers(),
            )
            assert accepted.status_code == 200, accepted.text
            assert worker.run_once()
            run = workspace.run(owner, accepted.json()["id"])
            assert run.state == "succeeded", run.error
            result = json_object(run.result)
            materials = json_object(workspace.blobs.object(result["materials_sha256"]))
            assert [row["quantity"] for row in materials["lines"]] == [30, 30]
            for row in materials["lines"]:
                assert row["source"]["electrical"]["circuit"]["conditions"][0] == frozen
            csv_bytes = Assets(workspace).content(
                owner,
                project["id"],
                result["prepared_attachments"]["bill_of_materials_csv"]["id"],
            )
            csv_rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
            assert (
                json.loads(csv_rows[1][6])["source"]["electrical"]["circuit"][
                    "conditions"
                ][0]
                == frozen
            )
            table = next(
                section["table"]
                for section in result["report"]["sections"]
                if section["id"] == "installation-electrical"
            )
            assert any("5.088" in cell for row in table["rows"] for cell in row)
            pdf_bytes = Assets(workspace).content(
                owner, project["id"], result["prepared_asset"]["id"]
            )
            assert "5.088" in "\n".join(
                page.extract_text() for page in PdfReader(io.BytesIO(pdf_bytes)).pages
            )
        equipment_basis = sources.equipment_basis()
        assert "cable_references" not in equipment_basis
        basis = sources.equipment_basis(include_cables=True)
        # Revoke current original bytes independently of retained report bytes.
        manifest = current(shared.publication)
        manifest["documents"][-1]["blob_sha256"] = "a" * 64
        monkeypatch.setattr(Publication, "read", lambda self: manifest)
        with pytest.raises(ProductEvidenceChanged):
            sources.confirm_basis(basis, require_reference=False)
        sources.confirm_basis(equipment_basis, require_reference=False)
        assert len(json_object(sources.current())["cable_references"]) == 1
        assert (
            materials["lines"][0]["source"]["electrical"]["circuit"]["conditions"][0]
            == frozen
        )
