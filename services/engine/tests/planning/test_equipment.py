"""Current Woo fixture -> typed quantities -> one real durable qualification.

The source numbers/documents reuse the existing engineering fixture and shipped
pair contract. Synthetic publication identities are never runtime product data.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import (
    FIXTURES,
    SHIPPED_COMPATIBILITY,
    publication_feed,
    publication_manifest,
)
from fastapi.testclient import TestClient

from linker_engine.engine import Engine
from linker_engine.planning.canonical import Object
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_facts import compile_product
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import VersionUnavailable
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.records import Actor
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .test_energy_kernel import TOLERANCE
from .test_private_http import TOKEN, headers


@pytest.fixture
def feed() -> dict:
    raw = json.loads((FIXTURES / "feed.json").read_text())
    # The source study identifies these five module-count columns. This
    # explicit synthetic maintenance field exercises the producer contract;
    # native Woo needs its own source-backed labels before qualification.
    controller = next(p for p in raw["products"] if p["id"] == 2092)
    controller["figures"]["system_operating_voltage_range_v"]["columns"] = [
        {"modules_per_stack": count} for count in (1, 2, 3, 4, 5)
    ]
    battery = next(p for p in raw["products"] if p["id"] == 2090)
    battery["figures"]["sales_unit_kind"] = {
        "value": "battery_module",
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["module_energy_kwh_usable"]["citation"]
        ),
    }
    return publication_feed(
        raw,
        json.loads(SHIPPED_COMPATIBILITY.read_text()),
    )


def inputs(feed: dict, count: int) -> Object:
    ids = [4107, 2090, 2092]
    return {
        "equipment_selection": {
            "schema_version": 1,
            "inverter_product_id": 4107,
            "battery_product_id": 2090,
            "modules_per_stack": count,
            "parallel_stacks": 1,
            "accessory_product_ids": [2092],
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 10,
            "required_discharge_ac_kw": 5,
            "product_revisions": {
                str(p["id"]): p["product_revision"]
                for p in feed["products"]
                if p["id"] in ids
            },
        }
    }


def test_cited_quantities_keep_apparent_power_conditions_and_table_columns(
    feed: dict,
) -> None:
    row = copy.deepcopy(next(p for p in feed["products"] if p["id"] == 1946))
    original = row["figures"]["backup_power_kw"]
    original["unit"] = "kVA"
    original["qualifier"] = {"en": "With the specified transfer equipment."}
    compiled = compile_product(row)
    figure = compiled["facts"]["backup_power_kw"]
    assert figure["quantity"] == "apparent_power" and figure["unit"] == "kVA"
    assert (
        figure["status"] == "conditional"
        and figure["source"]["page"] == original["citation"]["page"]
    )
    assert "ac_power_kw" not in compiled and "nominal_kwh" not in compiled
    controller = compile_product(next(p for p in feed["products"] if p["id"] == 2092))
    ranges = controller["facts"]["system_operating_voltage_range_v"]
    assert ranges["shape"] == "ordered_values" and len(ranges["value"]) == 5
    assert "max_fault_current_a" not in controller["facts"]


@pytest.mark.parametrize(
    ("count", "voltage_status"), [(1, "violated"), (2, "unresolved"), (3, "satisfied")]
)
def test_stack_window_is_not_a_flattened_range_or_a_fault_current_power(
    feed: dict, count: int, voltage_status: str
) -> None:
    result = assess_equipment(
        inputs(feed, count),
        {"products": feed["products"], "compatibility": feed["compatibility"]},
    )
    checks = {item["id"]: item for item in result["checks"]}
    assert checks["battery_voltage"]["status"] == voltage_status
    assert checks["continuous_battery_ac_output"]["status"] == "unresolved"
    assert checks["battery_sales_unit"]["status"] == "satisfied"
    assert checks["usable_energy"]["status"] == (
        "satisfied" if count == 3 else "unresolved"
    )
    assert result["country_assessment"]["status"] == "unresolved"
    if count == 3:
        unlabeled = copy.deepcopy(feed)
        del next(p for p in unlabeled["products"] if p["id"] == 2092)["figures"][
            "system_operating_voltage_range_v"
        ]["columns"]
        unproven = assess_equipment(
            inputs(feed, count),
            {
                "products": unlabeled["products"],
                "compatibility": unlabeled["compatibility"],
            },
        )
        assert (
            next(c for c in unproven["checks"] if c["id"] == "battery_voltage")[
                "status"
            ]
            == "unresolved"
        )
        unknown_unit = copy.deepcopy(feed)
        del next(p for p in unknown_unit["products"] if p["id"] == 2090)["figures"][
            "sales_unit_kind"
        ]
        unresolved = assess_equipment(
            inputs(feed, 3),
            {
                "products": unknown_unit["products"],
                "compatibility": unknown_unit["compatibility"],
            },
        )
        assert not any(
            line["product_id"] == 2090
            for line in unresolved["provisional_bill_of_materials"]
        )
        scalar = copy.deepcopy(feed)
        table = next(p for p in scalar["products"] if p["id"] == 2092)["figures"][
            "system_operating_voltage_range_v"
        ]
        table["value"] = "268.8~345.6"
        no_count = inputs(feed, 3)
        no_count["equipment_selection"]["modules_per_stack"] = None
        unresolved = assess_equipment(
            no_count,
            {"products": scalar["products"], "compatibility": scalar["compatibility"]},
        )
        assert (
            next(c for c in unresolved["checks"] if c["id"] == "battery_voltage")[
                "status"
            ]
            == "unresolved"
        )


def test_native_command_worker_receipt_and_inflight_withdrawal_use_one_frozen_pool(
    feed: dict,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = Publication(feed)
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=publication,
        version="fixture",
    )
    source = ProductSources(lambda: shared)
    withdrawn, offline = False, False

    def current(self: Publication) -> dict:
        if offline:
            raise PublicationUnavailable("fixture source offline")
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            manifest["products"] = [
                p for p in manifest["products"] if p["product_id"] != 2090
            ]
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    with pytest.raises(VersionUnavailable):
        source.equipment_basis()
    feed["figure_projection_version"] = 2
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment=equipment,
        product_provider=lambda: shared,
    )
    registry = service_registry(energy, None, None, equipment)
    worker = Worker(
        Jobs(workspace),
        "equipment-only-path",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    with TestClient(app) as client:
        created = client.post(
            "/projects/create",
            json={
                "schema_version": 1,
                "title": "Cited equipment fixture",
                "inputs": inputs(feed, 3),
                "key": "equipment-project",
            },
            headers=headers(),
        )
        assert created.status_code == 200, created.text
        pid = created.json()["id"]
        command = {
            "schema_version": 1,
            "project_id": pid,
            "expected_revision": 1,
            "key": "equipment-first",
        }
        assert client.post("/runs/equipment", json=command).status_code == 401
        accepted = client.post("/runs/equipment", json=command, headers=headers())
        assert accepted.status_code == 200, accepted.text
        first = accepted.json()["id"]
        assert worker.run_once()
        completed = workspace.run(owner, first)
        assert completed.state == "succeeded" and completed.result is not None
        proof = completed.result["pinned_assets"]["woo.equipment_inputs"]
        assert workspace.blobs.object(proof)["figure_projection_version"] == 2
        offline = True
        replayed = client.post("/runs/equipment", json=command, headers=headers())
        assert replayed.status_code == 200 and replayed.json()["id"] == first
        offline = False
        second_inputs = {**inputs(feed, 3), "project_note": "second qualification"}
        workspace.revise(owner, pid, 1, second_inputs, key="second-input")
        second = client.post(
            "/runs/equipment",
            json={**command, "expected_revision": 2, "key": "equipment-second"},
            headers=headers(),
        )
        assert second.status_code == 200, second.text
        original = assess_equipment

        def withdraw_after_assessment(*args):
            nonlocal withdrawn
            result = original(*args)
            withdrawn = True
            return result

        monkeypatch.setattr(
            "linker_engine.planning.equipment_kernel.assess_equipment",
            withdraw_after_assessment,
        )
        assert worker.run_once()
        refused = workspace.run(owner, second.json()["id"])
        assert refused.state == "failed" and refused.result is None
        assert refused.error["code"] == "product_evidence_changed"
        assert workspace.run(owner, first).result == completed.result
