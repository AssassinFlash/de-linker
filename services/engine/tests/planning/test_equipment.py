"""Current Woo fixture -> typed quantities -> one real durable qualification.

The source numbers/documents reuse the existing engineering fixture and shipped
pair contract. Synthetic publication identities are never runtime product data.
"""

from __future__ import annotations

import copy
import io
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, cast

import pytest
from conftest import (
    FIXTURES,
    SHIPPED_COMPATIBILITY,
    publication_feed,
    publication_manifest,
)
from fastapi.testclient import TestClient
from pypdf import PdfReader

from linker_engine.engine import Engine
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.dc_energy_parameters import DcLossScenario
from linker_engine.planning.energy_equipment import assess_energy_equipment
from linker_engine.planning.energy_inputs import BatteryParameters
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_candidate_choice import check_equipment_candidate
from linker_engine.planning.equipment_candidate_store import EquipmentCandidateStore
from linker_engine.planning.equipment_declarations import compile_discovery_inputs
from linker_engine.planning.equipment_facts import compile_product
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_requirements import EquipmentRequirements
from linker_engine.planning.equipment_search import search_equipment
from linker_engine.planning.equipment_search_kernel import EquipmentSearchKernel
from linker_engine.planning.equipment_search_limits import EquipmentSearchLimits
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import (
    InvalidInput,
    ProductEvidenceChanged,
    ReportSourceExportRequired,
    VersionUnavailable,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.plant_search_plan import PlantSearchPlan
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_model import build_report
from linker_engine.planning.report_sources import ReportInputsChanged, report_sources
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .conftest import FixtureObject, json_object, mapping_role
from .panel_fixture import panel_basis, panel_parameters
from .test_brief import incomplete_brief
from .test_energy_kernel import BATTERY, TOLERANCE, create_scenario
from .test_energy_kernel import worker as energy_worker
from .test_private_http import TOKEN, USER, headers


@pytest.fixture
def feed() -> FixtureObject:
    raw = json.loads((FIXTURES / "scenario-feed-2026-10-09.json").read_text())
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


def inputs(feed: FixtureObject, count: int) -> FixtureObject:
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


def plant_inputs(feed: FixtureObject, *, coordinated: bool = False) -> FixtureObject:
    unit = inputs(feed, 3)["equipment_selection"]
    requirements = {
        k: v for k, v in unit.items() if k in EquipmentRequirements.model_fields
    }
    requirements["pv_dc_kw"] = 20
    controller = next(p for p in feed["products"] if p["id"] == 2409)
    return {
        "schema_version": 1,
        "requirements": requirements,
        "units": [
            {"id": "a", "name": "A", "selection": copy.deepcopy(unit)},
            {"id": "b", "name": "B", "selection": copy.deepcopy(unit)},
        ],
        "parallel_groups": [
            {
                "id": "ac",
                "unit_ids": ["a", "b"],
                "controller_product_id": 2409,
                "controller_revision": controller["product_revision"],
            }
        ]
        if coordinated
        else [],
    }


def test_cabinet_sales_unit_and_factory_count_share_cited_woo_basis(
    feed: FixtureObject,
) -> None:
    from linker_engine.planning.battery_assembly import battery_assembly
    from linker_engine.planning.equipment_inputs import EquipmentSelection

    basis = copy.deepcopy(feed)
    cabinet = next(p for p in basis["products"] if p["id"] == 1955)
    original = json_object(compile_product(cabinet))
    assert battery_assembly(original) is None
    # Explicit synthetic Woo maintenance entry, using the fixture's existing
    # whole-system source. It is not an independent runtime product registry.
    cabinet["figures"]["sales_unit_kind"] = {
        "value": "battery_system",
        "unit": None,
        "citation": copy.deepcopy(
            cabinet["figures"]["modules_per_stack_min"]["citation"]
        ),
    }
    assembly = battery_assembly(json_object(compile_product(cabinet)))
    assert assembly is not None and assembly["fixed_modules_per_stack"] == 11
    assert assembly["documents"] == [
        {"url": cabinet["figures"]["sales_unit_kind"]["citation"]["url"], "page": 2}
    ]
    selection = EquipmentSelection.read(
        {
            **inputs(feed, 3)["equipment_selection"],
            "inverter_product_id": 1946,
            "battery_product_id": 1955,
            "modules_per_stack": 11,
            "parallel_stacks": 1,
            "accessory_product_ids": [],
            "product_revisions": {
                str(p["id"]): p["product_revision"]
                for p in basis["products"]
                if p["id"] in [1946, 1955]
            },
        }
    )
    result = json_object(
        assess_equipment(
            {"equipment_selection": selection.model_dump(mode="json")}, basis
        )
    )
    assert [
        row["quantity"]
        for row in result["provisional_bill_of_materials"]
        if row["product_id"] == 1955
    ] == [1]
    cabinet["figures"]["modules_per_stack_max"]["qualifier"] = {"unassessed": True}
    conditional = battery_assembly(json_object(compile_product(cabinet)))
    assert conditional is not None and conditional["fixed_modules_per_stack"] is None
    del cabinet["figures"]["sales_unit_kind"]
    assert battery_assembly(json_object(compile_product(cabinet))) is None
    assert not any(
        row["product_id"] == 1955
        for row in json_object(
            assess_equipment(
                {"equipment_selection": selection.model_dump(mode="json")}, basis
            )
        )["provisional_bill_of_materials"]
    )


def test_batc_reviewed_delivery_follows_real_equipment_selection(
    feed: FixtureObject,
) -> None:
    from linker_engine.planning.battery_assembly import battery_assembly
    from linker_engine.planning.project_materials import project_materials

    path = Path(__file__).resolve().parents[4] / "tools/migrate/548-batc-delivery.json"
    plan = json.loads(path.read_text())["products"]
    basis = copy.deepcopy(feed)
    manual = "https://de-linker.com/wp-content/uploads/2026/09/GW_BAT-C-208-261kWh_User-Manual-EN.pdf"
    for pid, packs in ((1956, 4), (1957, 4), (1958, 5)):
        cabinet = next(product for product in basis["products"] if product["id"] == pid)
        # The model, linked manual and PACK evidence are the existing Woo fixture.
        # The additional sales-unit and delivery facts are this reviewed candidate.
        cabinet["figures"]["sales_unit_kind"] = {
            "value": "battery_system",
            "unit": None,
            "citation": {"url": manual, "page": 3},
        }
        cabinet["installation_facts"] = {
            "status": "documented",
            "items": plan[str(pid)]["items"],
        }
        assembly = battery_assembly(json_object(compile_product(cabinet)))
        assert assembly is not None and assembly["fixed_modules_per_stack"] == packs
        selected = {
            **inputs(basis, packs)["equipment_selection"],
            "inverter_product_id": 1946,
            "battery_product_id": pid,
            "modules_per_stack": packs,
            "parallel_stacks": 2,
            "accessory_product_ids": [],
            "product_revisions": {
                str(p["id"]): p["product_revision"]
                for p in basis["products"]
                if p["id"] in (1946, pid)
            },
        }
        assessed = json_object(
            assess_equipment({"equipment_selection": selected}, basis)
        )
        battery = next(
            row
            for row in assessed["provisional_bill_of_materials"]
            if row["product_id"] == pid
        )
        assert battery["quantity"] == 2 and battery["basis"] == "battery_system"
        materials = json_object(
            project_materials(
                {
                    "project_id": "synthetic",
                    "revision": 1,
                    "input_sha256": "0" * 64,
                    "woo_bases": {},
                    "equipment": assessed,
                }
            )
        )
        anchor = next(
            row
            for row in materials["lines"]
            if str(row["id"]).endswith(":expansion-bolt")
        )
        assert anchor["handling"] == "manufacturer_included" and anchor["quantity"] == 8


def test_multi_converter_plant_keeps_unit_ownership_and_source_revisions(
    feed: FixtureObject,
) -> None:
    from pydantic import ValidationError

    from linker_engine.planning.equipment_plant import EquipmentPlant
    from linker_engine.planning.plant_assessment import plant_products

    plant = plant_inputs(feed)
    unit = plant["units"][0]["selection"]
    parsed = EquipmentPlant.from_inputs({"equipment_plant": plant})
    assert len(parsed.units) == 2
    with pytest.raises(InvalidInput, match="single-converter"):
        EquipmentPlant.from_inputs(
            {"equipment_plant": plant, "equipment_selection": unit}
        )
    duplicate = copy.deepcopy(plant)
    duplicate["units"][1]["id"] = "a"
    with pytest.raises(ValidationError, match="unique"):
        EquipmentPlant.model_validate(duplicate)
    crossed = copy.deepcopy(plant)
    crossed["parallel_groups"] = [
        {
            "id": "g",
            "unit_ids": ["a", "b"],
            "controller_product_id": 2092,
            "controller_revision": unit["product_revisions"]["2092"],
        }
    ]
    with pytest.raises(ValidationError, match="shared controller"):
        EquipmentPlant.model_validate(crossed)
    changed = copy.deepcopy(plant)
    for u in changed["units"]:
        u["selection"]["product_revisions"]["4107"] = "0" * 64
    with pytest.raises(ProductEvidenceChanged):
        plant_products(EquipmentPlant.read(changed), {"products": feed["products"]})


@pytest.mark.parametrize(
    ("count", "change", "status"),
    [
        (10, "none", "satisfied"),
        (11, "none", "violated"),
        (2, "source", "unresolved"),
        (2, "qualifier", "unresolved"),
        (2, "rs485", "unresolved"),
        (2, "zero", "unresolved"),
    ],
)
def test_controller_network_limit_keeps_its_source_and_network_scope(
    feed: FixtureObject, count: int, change: str, status: str
) -> None:
    from linker_engine.planning.plant_assessment import assess_plant

    # The SEC numeric LAN field is explicitly maintained, not parsed from
    # the older RS485/LAN prose or the unrelated 15-port switch statement.
    controller = next(p for p in feed["products"] if p["id"] == 2409)
    controller["figures"]["max_lan_inverters"] = {
        "value": 10 if change != "zero" else 0,
        "unit": "units",
        "citation": copy.deepcopy(controller["figures"]["max_devices"]["citation"]),
    }
    basis = json_object(
        publication_feed(feed, json.loads(SHIPPED_COMPATIBILITY.read_text()))
    )
    controller = next(p for p in basis["products"] if p["id"] == 2409)
    fact = controller["figures"]["max_lan_inverters"]
    if change == "source":
        for doc in controller["documents"]:
            if doc["url"] == fact["citation"]["url"]:
                doc["product_ids"] = []
    if change == "qualifier":
        fact["qualifier"] = {"unresolved_condition": True}
    plant = plant_inputs(basis, coordinated=True)
    template = plant["units"][0]
    plant["units"] = [
        {**copy.deepcopy(template), "id": f"u{index}", "name": f"Unit {index}"}
        for index in range(count)
    ]
    group = plant["parallel_groups"][0]
    group["unit_ids"] = [unit["id"] for unit in plant["units"]]
    group["control_network"] = "rs485" if change == "rs485" else "lan"
    result = json_object(assess_plant({"equipment_plant": plant}, basis))
    check = next(
        c
        for c in result["checks"]
        if c.get("semantic_id") == "plant_controller_network_count"
    )
    assert check["status"] == status
    assert check["actual"] == count
    assert check["required"] == (10 if status != "unresolved" else None)
    assert check["facts"][0]["raw_value"] == (0 if change == "zero" else 10)
    assert all(
        c["status"] == "unresolved"
        for c in result["checks"]
        if c.get("semantic_id") == "plant_joint_operation"
    )


@pytest.mark.parametrize("locale", ["en", "de"])
def test_frozen_plant_phase_conflicts_identify_only_the_mismatching_hardware(
    feed: FixtureObject, locale: str
) -> None:
    from linker_engine.planning.plant_assessment import assess_plant

    plant = plant_inputs(feed)
    hardware, declaration_only = plant["units"]
    hardware["name"] = "Depot · East"
    declaration_only["name"] = "Office"
    single_phase = next(p for p in feed["products"] if p["id"] == 3577)
    hardware["selection"].update(
        inverter_product_id=3577,
        battery_product_id=None,
        modules_per_stack=None,
        parallel_stacks=None,
        accessory_product_ids=[],
        product_revisions={"3577": single_phase["product_revision"]},
    )
    declaration_only["selection"] = {**hardware["selection"], "grid_phase": 1}
    plant["units"].append({**copy.deepcopy(hardware), "id": "c", "name": "West"})
    assessment = json_object(
        assess_plant({"equipment_plant": plant}, json_object(feed))
    )
    assert [
        (check["semantic_id"], check["status"], check["actual"], check["required"])
        for check in assessment["checks"]
        if check.get("unit_name") == "Office"
        and check.get("semantic_id") in {"grid_phase", "plant_grid_phase"}
    ] == [("grid_phase", "satisfied", 1, 1), ("plant_grid_phase", "violated", 1, 3)]
    report = build_report(
        {
            "locale": locale,
            "title": "Depot",
            "project_id": "a" * 32,
            "revision": 3,
            "input_sha256": "1" * 64,
            "source_runs": [],
            "generated_at": "2026-11-18T00:00:00Z",
            "equipment": assessment,
        }
    ).model_dump(mode="json")
    assert report["phase_conflicts"] == [
        {"unit": "Depot · East", "actual": 1, "required": 3},
        {"unit": "West", "actual": 1, "required": 3},
    ]


@pytest.mark.parametrize("with_equipment_use", [False, True])
def test_multi_converter_native_job_freezes_plant_materials_and_report_lineage(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
    with_equipment_use: bool,
) -> None:
    from linker_engine.planning.plant_assessment import assess_plant
    from linker_engine.planning.project_materials import project_materials

    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    controller = next(p for p in feed["products"] if p["id"] == 2409)
    controller["figures"]["max_lan_inverters"] = {
        "value": 10,
        "unit": "units",
        "citation": copy.deepcopy(controller["figures"]["max_devices"]["citation"]),
    }
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="plant-fixture",
    )

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    sources = ProductSources(lambda: shared)
    controller = next(p for p in feed["products"] if p["id"] == 2409)
    plant = plant_inputs(feed, coordinated=True)
    plant["parallel_groups"][0]["control_network"] = "lan"
    setup = {
        "schema_version": 1,
        "requirements": copy.deepcopy(plant["requirements"]),
        "units": [
            {
                "id": u["id"],
                "name": u["name"],
                "inputs": {"equipment_selection": copy.deepcopy(u["selection"])},
            }
            for u in plant["units"]
        ],
        "parallel_groups": [
            {k: v for k, v in g.items() if k != "controller_revision"}
            for g in plant["parallel_groups"]
        ],
    }
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, sources), max_attempts=1
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, sources, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    registry = service_registry(energy, None, None, equipment, search)
    executor = Worker(
        Jobs(workspace),
        "plant-fixture",
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
        equipment=equipment,
        equipment_search=search,
        product_provider=lambda: shared,
    )
    with TestClient(app) as client:
        raw = client.post(
            "/projects/create",
            headers=headers(),
            json={
                "schema_version": 1,
                "title": "Editable plant",
                "inputs": {"equipment_plant_setup": setup},
                "key": "plant-raw",
            },
        )
        assert raw.status_code == 200, raw.text
        unprepared = client.post(
            "/runs/equipment",
            headers=headers(),
            json={
                "schema_version": 1,
                "project_id": raw.json()["id"],
                "expected_revision": 1,
                "key": "raw-check",
            },
        )
        assert unprepared.status_code == 422
        assert (
            unprepared.json()["error"]["code"] == "equipment_plant_requires_preparation"
        )
        mixed = client.post(
            "/projects/create",
            headers=headers(),
            json={
                "schema_version": 1,
                "title": "Mixed legacy input",
                "inputs": {
                    "equipment_plant_setup": setup,
                    "equipment_selection": plant["units"][0]["selection"],
                },
                "key": "plant-mixed",
            },
        )
        assert mixed.status_code == 422
        stale = copy.deepcopy(setup)
        stale["units"][0]["name"] = "Changed"
        for raw_setup in (stale, None):
            refused = client.post(
                "/projects/create",
                headers=headers(),
                json={
                    "schema_version": 1,
                    "title": "Stale prepared plant",
                    "inputs": {
                        "equipment_plant": plant,
                        "equipment_plant_setup": raw_setup,
                    },
                    "key": "plant-stale",
                },
            )
            assert refused.status_code == 422
            assert (
                refused.json()["error"]["code"]
                == "equipment_plant_requires_preparation"
            )
        response = client.post(
            "/projects/create",
            headers=headers(),
            json={
                "schema_version": 1,
                "title": "Synthetic two-converter plant",
                "inputs": {"equipment_plant": plant, "equipment_plant_setup": setup},
                "key": "plant-create",
            },
        )
        assert response.status_code == 200, response.text
        project = response.json()
        response = client.post(
            "/runs/equipment",
            headers=headers(),
            json={
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": 1,
                "key": "plant-check",
            },
        )
        assert response.status_code == 200, response.text
        run_id = response.json()["id"]
        assert executor.run_once()
        run = client.post(
            "/runs/read",
            headers=headers(),
            json={"schema_version": 1, "run_id": run_id},
        ).json()
        assert run["state"] == "succeeded", run["error"]
    actor = USER
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=run_id,
        logo=None,
    )
    with pytest.raises(InvalidInput):
        json_object(
            report_sources(
                workspace,
                sources,
                actor,
                replace(
                    workspace.get(actor, project["id"]),
                    inputs={"equipment_plant_setup": setup, "equipment_candidate": {}},
                ),
                options,
            )
        )
    source = json_object(
        report_sources(
            workspace, sources, actor, workspace.get(actor, project["id"]), options
        )
    )
    materials = json_object(project_materials(source))
    quantities = {
        row["product_id"]: row["quantity"]
        for row in materials["lines"]
        if row["handling"] == "woo_product"
    }
    assert quantities == {4107: 2, 2090: 6, 2092: 2, 2409: 1}
    assert (
        source["equipment_plant"] == plant
        and source["equipment"]["overall_status"] == "unresolved"
    )
    frozen_source = copy.deepcopy(source)
    network = next(
        check
        for check in source["equipment"]["checks"]
        if check.get("semantic_id") == "plant_controller_network_count"
    )
    assert (network["status"], network["actual"], network["required"]) == (
        "satisfied",
        2,
        10,
    )
    assert network["facts"][0]["source"]["figure_key"] == "max_lan_inverters"
    report = build_report(source)
    assert source == frozen_source
    network_section = next(
        s for s in report.sections if s.id.startswith("check-controller-network-")
    )
    assert any(r.value == "LAN" for r in network_section.rows)
    assert any(r.value == "LAN · 10" and r.href for r in network_section.rows)
    converter = next(s for s in report.sections if s.title == "A · Converter output")
    assert any(row.value.endswith(" kW") for row in converter.rows)
    accessory = next(s for s in report.sections if s.title == "A · Required accessory")
    accessory_model = next(p["model"] for p in feed["products"] if p["id"] == 2092)
    assert any(accessory_model in row.value for row in accessory.rows)
    assert not any(
        row.value == "2092" for section in report.sections for row in section.rows
    )
    conditions = next(s for s in report.sections if s.id == "conditions")
    assert any(p.startswith("A · ") for p in conditions.paragraphs) or any(
        row.label.startswith("A · ") for row in conditions.rows
    )
    assert any(
        s.title.endswith("Joint operation") and s.paragraphs for s in report.sections
    )
    wrong = copy.deepcopy(plant)
    wrong["requirements"]["pv_dc_kw"] = 21
    assessment = json_object(
        assess_plant({"equipment_plant": wrong}, json_object(sources.equipment_basis()))
    )
    assert any(
        c["id"] == "plant:allocation:pv_dc_kw" and c["status"] == "violated"
        for c in assessment["checks"]
    )
    # A deliberately synthetic source bound tests the group constraint. It
    # does not assert that these SAJ devices actually use a GoodWe controller.
    limited = copy.deepcopy(json_object(sources.equipment_basis()))
    limited["compatibility"]["requirements"].append(
        {
            "kind": "parallel_controller",
            "inverter": "^H2-10K-T3$",
            "inverter_product_id": 4107,
            "included": False,
            "phase": 3,
            "max_units": 1,
            "applicability": {
                "operating_mode": "grid_connected",
                "topology": "parallel_group",
            },
            "conditions": [],
            "accessories": [
                {
                    "product_id": 2409,
                    "model": "^SEC3000C$",
                    "quantity": 1,
                    "per": "system",
                }
            ],
            "documents": [{"url": controller["documents"][0]["url"]}],
        }
    )
    restricted = json_object(assess_plant({"equipment_plant": plant}, limited))
    assert any(
        c["id"].endswith(":parallel_count") and c["status"] == "violated"
        for c in restricted["checks"]
    )
    scoped_row = limited["compatibility"]["requirements"][-1]
    scoped_row["applicability"]["operating_mode"] = "backup"
    wrong_mode = json_object(assess_plant({"equipment_plant": plant}, limited))
    assert not any(
        c["id"].endswith(":parallel_count") and c["status"] != "unresolved"
        for c in wrong_mode["checks"]
    )
    del scoped_row["applicability"]
    legacy = json_object(assess_plant({"equipment_plant": plant}, limited))
    assert all(
        c["status"] == "unresolved"
        for c in legacy["checks"]
        if c["id"].endswith(":parallel_count")
    )
    workspace.revise(
        actor, project["id"], 1, {"equipment_plant": wrong}, key="change-plant-demand"
    )
    with pytest.raises(InvalidInput):
        json_object(
            report_sources(
                workspace, sources, actor, workspace.get(actor, project["id"]), options
            )
        )

    # The same private command/worker/store/report path can now search a whole
    # layout before any converter or battery has been manually chosen.
    from linker_engine.planning.plant_search_plan import PlantSearchPlan
    from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS

    raw_search = copy.deepcopy(setup)
    for unit in raw_search["units"]:
        raw_selection = unit["inputs"].pop("equipment_selection")
        raw_selection.pop("product_revisions")
        raw_selection.update(
            inverter_product_id=None,
            battery_product_id=None,
            modules_per_stack=None,
            parallel_stacks=None,
            accessory_product_ids=[],
        )
        unit["inputs"]["equipment_setup"] = raw_selection
    if with_equipment_use:
        first = raw_search["units"][0]["inputs"]["equipment_setup"]
        first.update(
            inverter_product_id=4107,
            battery_product_id=2090,
            modules_per_stack=3,
            parallel_stacks=1,
            equipment_use={"inverter": "retain", "battery": "retain"},
        )
        raw_search["units"][1]["inputs"] = {
            "equipment_selection": {
                **inputs(feed, 4)["equipment_selection"],
                "equipment_use": {"inverter": "new", "battery": "replace"},
            }
        }
    plan = {
        "schema_version": 1,
        "requirements": raw_search["requirements"],
        "units": [
            {
                "id": u["id"],
                "name": u["name"],
                "requirements": {
                    key: u["inputs"]
                    .get("equipment_setup", u["inputs"].get("equipment_selection"))
                    .get(key)
                    for key in EquipmentRequirements.model_fields
                },
            }
            for u in raw_search["units"]
        ],
        "parallel_groups": raw_search["parallel_groups"],
    }
    request_inputs: FixtureObject = {
        "equipment_plant_setup": raw_search,
        "equipment_plant_requirements": plan,
    }
    PlantSearchPlan.from_inputs(request_inputs)
    with TestClient(app) as client:
        updated = client.post(
            "/projects/revise",
            headers=headers(),
            json={
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": 2,
                "inputs": request_inputs,
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "prepare-plant-search",
            },
        )
        assert updated.status_code == 200, updated.text
        queued = client.post(
            "/runs/equipment-search",
            headers=headers(),
            json={
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": 3,
                "key": "search-plant-layout",
            },
        )
        assert queued.status_code == 200, queued.text
        assert executor.run_once()
        searched = workspace.run(actor, queued.json()["id"])
        assert searched.state == "succeeded", searched.error
        result = json_object(searched.result)["search"]
        assert (
            result["coverage"]["template"]
            == "declared_plant_one_external_assembly_per_converter"
        )
        assert result["coverage"]["identical_demand_cache_entries"] == (
            2 if with_equipment_use else 1
        )
        assert result["candidates"]
        if with_equipment_use:
            for row in result["candidates"]:
                first, second = (u["selection"] for u in row["plant"]["units"])
                assert first["equipment_use"] == {
                    "inverter": "retain",
                    "battery": "retain",
                }
                assert (
                    first["inverter_product_id"],
                    first["battery_product_id"],
                    first["modules_per_stack"],
                    first["parallel_stacks"],
                ) == (4107, 2090, 3, 1)
                assert second["equipment_use"] == {
                    "inverter": "new",
                    "battery": "replace",
                }
        candidate = result["candidates"][0]
        assert "selection" not in candidate
        detail = client.post(
            "/equipment/candidates/read",
            headers=headers(),
            json={
                "schema_version": 1,
                "run_id": searched.id,
                "candidate_id": candidate["id"],
            },
        )
        assert detail.status_code == 200, detail.text
        assessment = detail.json()["assessment"]
        assert len(assessment["systems"]) == 2
        assert all(
            "facts" in c
            for u in assessment["systems"]
            for c in u["assessment"]["checks"]
        )
        assert (
            next(
                r
                for r in assessment["provisional_bill_of_materials"]
                if r["product_id"] == 2409
            )["quantity"]
            == 1
        )
        compact = json_object(workspace.blobs.object(candidate["assessment_sha256"]))
        assert all(
            "facts" not in c
            for u in compact["systems"]
            for c in u["assessment"]["checks"]
        )
        chosen = candidate["plant"]
        adopted_setup = {
            "schema_version": 1,
            "requirements": chosen["requirements"],
            "units": [
                {
                    "id": u["id"],
                    "name": u["name"],
                    "inputs": {"equipment_selection": u["selection"]},
                }
                for u in chosen["units"]
            ],
            "parallel_groups": [
                {k: v for k, v in g.items() if k != "controller_revision"}
                for g in chosen["parallel_groups"]
            ],
        }
        choice = {
            "run_id": searched.id,
            "candidate_id": candidate["id"],
            "assessment_sha256": candidate["assessment_sha256"],
        }
        adopted = client.post(
            "/projects/revise",
            headers=headers(),
            json={
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": 3,
                "inputs": {
                    "equipment_plant_setup": adopted_setup,
                    "equipment_plant": chosen,
                    "equipment_candidate": choice,
                },
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "adopt-plant-search",
            },
        )
        assert adopted.status_code == 200, adopted.text
    selected_source = json_object(
        report_sources(
            workspace,
            sources,
            actor,
            workspace.get(actor, project["id"]),
            options.model_copy(update={"equipment_run_id": None}),
        )
    )
    bypass = copy.deepcopy(workspace.get(actor, project["id"]).inputs)
    bypass["pv_plant_string_plan"] = {
        "schema_version": 1,
        "units": [
            {
                "unit_id": chosen["units"][0]["id"],
                "inverter_instance_id": None,
                "plan": {
                    "schema_version": 1,
                    "inverter_product_id": chosen["units"][0]["selection"][
                        "inverter_product_id"
                    ],
                    "minimum_ambient_c": None,
                    "temperature_source": None,
                    "strings": [],
                },
            }
        ],
    }
    with pytest.raises(ReportInputsChanged, match="has not assessed") as missing_wiring:
        report_sources(
            workspace,
            sources,
            actor,
            replace(workspace.get(actor, project["id"]), inputs=bypass),
            options.model_copy(update={"equipment_run_id": None}),
        )
    assert missing_wiring.value.code == "report_wiring_check_required"
    assert selected_source["equipment"] == assessment
    assert selected_source["equipment_plant"] == chosen
    assert selected_source["source_runs"][0]["candidate_id"] == candidate["id"]
    frozen = EquipmentCandidateStore(workspace).read(
        actor, searched.id, candidate["id"]
    )
    assert frozen["assessment"] == assessment
    changed = copy.deepcopy(adopted.json()["inputs"])
    changed["equipment_plant"]["units"][0]["selection"]["required_usable_kwh"] += 1
    changed.pop("equipment_plant_setup")
    with pytest.raises(InvalidInput):
        check_equipment_candidate(
            workspace, actor, project["id"], changed, previous=changed
        )
    stale_plan = copy.deepcopy(request_inputs)
    stale_plan["equipment_plant_setup"]["units"][0]["name"] = "Changed search demand"
    with pytest.raises(InvalidInput):
        PlantSearchPlan.from_inputs(stale_plan)


def test_plant_packaging_only_covers_the_owning_units_included_items() -> None:
    from linker_engine.planning.project_materials import (
        material_name,
        project_materials,
    )

    # Synthetic packaging identities exercise scope, not a manufacturer's
    # real contents. B's unquantified included meter must survive A's package.
    source: FixtureObject = {
        "project_id": "synthetic",
        "revision": 1,
        "input_sha256": "0" * 64,
        "equipment": {
            "selected_products": [
                {
                    "product_id": 1,
                    "model": "A",
                    "package_contents": {
                        "status": "documented",
                        "items": [
                            {
                                "id": "meter",
                                "quantity": 1,
                                "unit": "piece",
                                "role": "meter",
                                "label": {
                                    "en": "Supplied meter",
                                    "de": "Mitgelieferter Zähler",
                                },
                                "source": {},
                            }
                        ],
                    },
                },
                {"product_id": 2, "model": "B"},
                {
                    "product_id": 3,
                    "model": "Central controller",
                    "package_contents": {
                        "status": "documented",
                        "items": [
                            {
                                "id": "central-meter",
                                "quantity": 1,
                                "unit": "piece",
                                "role": "meter",
                                "label": {
                                    "en": "Central meter",
                                    "de": "Zentraler Zähler",
                                },
                                "source": {},
                            }
                        ],
                    },
                },
            ],
            "provisional_bill_of_materials": [
                {
                    "product_id": 1,
                    "quantity": 1,
                    "basis": "selected_converter",
                    "unit_ids": ["a"],
                },
                {
                    "product_id": 2,
                    "quantity": 1,
                    "basis": "selected_converter",
                    "unit_ids": ["b"],
                },
                {
                    "product_id": 3,
                    "quantity": 1,
                    "basis": "selected_parallel_controller",
                    "group_ids": ["ac"],
                },
            ],
            "installation_requirements": [
                {"kind": "meter", "included": True, "unit_id": "a", "unit_name": "A"},
                {"kind": "meter", "included": True, "group_id": "ac"},
                {
                    "kind": "meter",
                    "included": True,
                    "unit_id": "b",
                    "unit_name": "B",
                    "documents": [{"url": "https://fixture.invalid/b.pdf"}],
                },
            ],
        },
    }
    material = json_object(project_materials(source))
    unknown = [
        r for r in material["lines"] if r.get("basis") == "manufacturer_included"
    ]
    assert len(unknown) == 1 and unknown[0]["quantity"] is None
    assert material_name(unknown[0], "en").startswith("B · ")
    assert unknown[0]["source"]["documents"] == [
        {"url": "https://fixture.invalid/b.pdf"}
    ]
    # Both actually supplied meters remain available; a documented central
    # meter only replaces the central unquantified statement, never B's gap.
    supplied = [r for r in material["lines"] if str(r["id"]).startswith("package:")]
    assert [(r["parent_product_id"], r["quantity"]) for r in supplied] == [
        (1, 1),
        (3, 1),
    ]


def prepared_dc_fixture_source(
    feed: FixtureObject,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    *,
    reverse_ac_kw: float | None = None,
) -> tuple[
    FixtureObject,
    ProductSources,
    SimpleNamespace,
    FixtureObject,
    FixtureObject,
    FixtureObject,
]:
    """Reuse one synthetic maintained-source fixture; no runtime product data.

    Extra reverse-conversion figures cite an explicitly synthetic fixture file.
    They test the native producer boundary and never claim manufacturer facts.
    """
    inverter = next(row for row in feed["products"] if row["id"] == 4107)
    battery = next(row for row in feed["products"] if row["id"] == 2090)

    def figure(
        product: FixtureObject,
        key: str,
        value: float | str | bool,
        unit: str,
        citation: FixtureObject,
    ) -> None:
        product["figures"][key] = {
            "value": value,
            "unit": unit,
            "citation": copy.deepcopy(citation),
        }

    inv_citation = inverter["figures"]["battery_voltage_range_v"]["citation"]
    battery_citation = battery["figures"]["module_energy_kwh_usable"]["citation"]
    for key in (
        "max_battery_charge_a",
        "max_battery_discharge_a",
    ):
        figure(inverter, key, 50, "A", inv_citation)
        inverter["figures"][key]["qualifier"] = {
            "quantity_kind": "maximum",
            "scope": "per_battery_port",
            "direction": "discharge" if "discharge" in key else "charge",
            "ports": ["BAT1", "BAT2"],
            "source_expression": "2*50 A",
        }
    figure(inverter, "n_battery_ports", 2, "units", inv_citation)
    figure(inverter, "ac_output_kw_nominal", 10000, "W", inv_citation)
    inverter["figures"]["ac_output_kw_nominal"]["qualifier"] = {
        "quantity_kind": "rated_active_power",
        "scope": "on_grid_ac_output",
    }
    for key in ("max_charge_current_a", "max_discharge_current_a"):
        figure(battery, key, 30, "A", battery_citation)
        battery["figures"][key]["qualifier"] = {
            "quantity_kind": "maximum",
            "scope": "series_stack",
            "direction": "discharge" if "discharge" in key else "charge",
            "module_count_min": 1,
            "module_count_max": 5,
            "operating_temperature_c": [-10 if "discharge" in key else 0, 50],
        }
    controller = next(row for row in feed["products"] if row["id"] == 2092)
    from linker_engine.planning.equipment_facts import numeric_value

    voltage = controller["figures"]["system_operating_voltage_range_v"]
    _, _, _, values = numeric_value(voltage["value"], voltage["unit"])
    assert isinstance(values, list)
    voltage["qualifier"] = {
        "quantity_kind": "operating_range",
        "scope": "battery_system",
        "module_count_basis": "columns",
    }
    voltage["columns"] = [
        {
            "module_count": i,
            "min": json_object(column)["value"][0],
            "max": json_object(column)["value"][1],
            "unit": "V",
        }
        for i, column in enumerate(values, 1)
    ]
    figure(
        battery,
        "rated_power_w",
        "3072 / 6144 / 9216 / 12288 / 15360",
        "W",
        battery_citation,
    )
    rated = battery["figures"]["rated_power_w"]
    rated["qualifier"] = {
        "quantity_kind": "rated",
        "scope": "battery_system",
        "module_count_basis": "columns",
        "battery_module": battery["model"],
        "control_module": controller["model"],
    }
    rated["columns"] = [
        {"module_count": i, "value": int(value.strip()), "unit": "W"}
        for i, value in enumerate(rated["value"].split("/"), 1)
    ]

    if reverse_ac_kw is not None:
        synthetic_citation = {
            "url": "https://de-linker.com/wp-content/uploads/fixtures/joint-ac-fixture-only.pdf",
            "page": 1,
        }
        figure(
            inverter,
            "battery_grid_charging_supported",
            "supported",
            "",
            synthetic_citation,
        )
        figure(
            inverter,
            "max_battery_charge_ac_power_kw",
            reverse_ac_kw,
            "kW",
            synthetic_citation,
        )
    feed = publication_feed(feed, feed["compatibility"])
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    loaded = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )

    def current(publication: Publication) -> FixtureObject:
        result = publication_manifest(publication.feed)
        for row in result["products"]:
            row["ready"]["engineering"] = True
        return result

    monkeypatch.setattr(Publication, "read", current)
    source = ProductSources(lambda: loaded)
    return feed, source, loaded, inverter, battery, controller


def dc_loss_fixture() -> DcLossScenario:
    """Shared explicit source-only assumptions, never a device-efficiency fact."""
    from linker_engine.planning.dc_energy_parameters import DcLossScenario

    return DcLossScenario.read(
        {
            "schema_version": 1,
            "model": "constant_window_shared_dc_bus_v1",
            "parameter_basis": "explicit_loss_scenario_with_woo_equipment",
            "battery_port_id": "BAT1",
            "battery_temperature_c": 20,
            "eta_bus_to_battery": 1,
            "eta_battery_to_bus": 1,
            "eta_store_charge": 1,
            "eta_store_discharge": 1,
            "eta_inverter_forward": 1,
            "eta_inverter_reverse": 1,
            "internal_aux_kw": 0,
            "standing_loss_rate_per_hour": 0,
            "source_note": "Synthetic source-bound input/terminal limits only",
        }
    )


@pytest.mark.parametrize(
    ("active_limit", "country", "expected"),
    [(None, "DE", 10), (6, "DE", 6), (None, "CL", None), (None, None, None)],
)
def test_reverse_input_ceiling_and_battery_terminal_power_keep_their_boundaries(
    feed: FixtureObject,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    active_limit: int | None,
    country: str | None,
    expected: int | None,
) -> None:
    """One source-preparation check; reuse fixtures without any energy replay."""
    from linker_engine.planning.dc_parameter_source import prepare_dc_parameters
    from linker_engine.planning.errors import EvidenceMissing

    feed, source, _, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch, reverse_ac_kw=6
    )
    basis = json_object(source.equipment_basis())
    inverter = next(p for p in basis["products"] if p["canonical_product_id"] == 4107)
    figures = inverter["figures"]
    capability = figures["battery_grid_charging_supported"]
    capability["qualifier"] = {
        "quantity_kind": "documented_operating_function",
        "scope": "grid_connected_battery_charging",
        "requires_local_grid_permission": True,
    }
    citation = copy.deepcopy(capability["citation"])
    if active_limit is None:
        figures.pop("max_battery_charge_ac_power_kw")
    figures["max_apparent_power_from_grid_kva"] = {
        "value": 10,
        "unit": "kVA",
        "citation": citation,
        "qualifier": {
            "quantity_kind": "maximum_apparent_power",
            "scope": "on_grid_ac_input",
            "excluded_countries": ["CL"],
        },
    }
    for direction, power in (("charge", 2), ("discharge", 3)):
        figures[f"max_battery_terminal_{direction}_power_kw"] = {
            "value": power,
            "unit": "kW",
            "citation": citation,
            "qualifier": {
                "quantity_kind": "maximum_active_power",
                "scope": "inverter_battery_terminals_total",
            },
        }
    assumptions = dc_loss_fixture()
    project_inputs = {
        **inputs(feed, 3),
        "brief": {"site": {"country_code": country}},
    }
    if expected is None:
        with pytest.raises(EvidenceMissing):
            prepare_dc_parameters(project_inputs, basis, assumptions)
        return
    prepared = prepare_dc_parameters(project_inputs, basis, assumptions)
    assert prepared.connected_bridge.reverse_ac_kw == expected
    # The maximum battery-terminal power is shared by PV and reversed AC;
    # it must not become a separate AC-to-DC bridge-output allowance.
    assert prepared.connected_bridge.reverse_dc_kw is None
    assert prepared.selected_port.charge_power_limit_kw == 2
    assert prepared.selected_port.discharge_power_limit_kw == 3
    assert prepared.battery_model("0" * 64).charge_terminal_kw == 2
    ceiling = json_object(prepared.source_facts)["reverse_ac_input_ceiling"]
    assert ceiling["role"] == "necessary_upper_bound_only"
    assert ceiling["apparent_power_limit_kva"] == 10
    assert ceiling["active_power_limit_kw"] == active_limit
    if active_limit is None:
        # A declared but unknown condition is not the absence of a condition.
        figures["max_apparent_power_from_grid_kva"]["qualifier"][
            "excluded_countries"
        ] = None
        with pytest.raises(EvidenceMissing):
            prepare_dc_parameters(project_inputs, basis, assumptions)


def test_reference_capacity_is_explicit_and_does_not_resolve_operating_conditions(
    feed: FixtureObject, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from linker_engine.planning.capacity_window import REFERENCE_CAPACITY
    from linker_engine.planning.dc_parameter_source import prepare_dc_parameters
    from linker_engine.planning.errors import EvidenceMissing

    feed, source, _, _, _, _ = prepared_dc_fixture_source(feed, engine, monkeypatch)
    basis = json_object(source.equipment_basis())
    battery = next(p for p in basis["products"] if p["canonical_product_id"] == 2090)
    fact = battery["figures"]["module_energy_kwh_usable"]
    fact["qualifier"] = {
        "quantity_kind": "rated_usable_energy",
        "scope": "battery_module",
        "rating_conditions": {
            "life_state": "beginning_of_life",
            "depth_of_discharge_pct": 100,
            "charge_rate_c": 0.2,
            "discharge_rate_c": 0.2,
            "test_temperature_c": [23, 27],
        },
        "configuration_dependent": True,
        "source_text": {
            "en": "Synthetic manufacturer reference conditions",
            "de": "Synthetische Hersteller-Prüfbedingungen",
        },
    }
    project_inputs = inputs(feed, 3)
    assumptions = dc_loss_fixture()
    assert "capacity_window_basis" not in assumptions.model_dump(mode="json")
    assert (
        assumptions.model_copy(update={"capacity_window_basis": None}).model_dump(
            mode="json"
        )["capacity_window_basis"]
        is None
    )
    with pytest.raises(EvidenceMissing):
        prepare_dc_parameters(project_inputs, basis, assumptions)
    chosen = assumptions.model_copy(
        update={"capacity_window_basis": REFERENCE_CAPACITY}
    )
    prepared = prepare_dc_parameters(project_inputs, basis, chosen)
    assert (
        prepared.usable_window_kwh == 13.5
    )  # 3 × 4.5 usable kWh; no second DOD reduction.
    recorded = json_object(prepared.source_facts)["capacity_window_assumption"]
    assert recorded["rating_conditions_status"] == "not_established"
    assert recorded["manufacturer_qualifier"] == fact["qualifier"]
    assert (
        recorded["internal_window_mapping"] == "published_usable_energy_as_model_window"
    )
    assert (
        json_object(prepared.source_facts)["usable_energy_derivation"]["status"]
        == "unresolved"
    )
    assert (
        "condition_match"
        not in json_object(prepared.source_facts)["2090.module_energy_kwh_usable"]
    )
    # Explicit model selection never interprets a new unknown source condition.
    fact["qualifier"]["unrecognized_operating_condition"] = "unknown"
    with pytest.raises(EvidenceMissing):
        prepare_dc_parameters(project_inputs, basis, chosen)


def test_shared_dc_native_asset_command_worker_and_stage_bound_trace(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One two-hour native route, with explicit synthetic Woo maintenance facts."""
    from datetime import timedelta

    from linker_engine.planning.assets import Assets
    from linker_engine.planning.canonical import digest, encode
    from linker_engine.planning.csv_mapping import CsvMapping
    from linker_engine.planning.dc_energy_kernel import DcEnergyKernel
    from linker_engine.planning.dc_energy_parameters import DcLossScenario
    from linker_engine.planning.errors import VersionUnavailable
    from linker_engine.planning.interval import Interval
    from linker_engine.planning.profile_import import ProfileImport
    from linker_engine.planning.pv_generation import generate_pv
    from linker_engine.planning.pv_parameters import PvGenerationParameters
    from linker_engine.planning.pv_profile_preparation import PROFILE_PURPOSE
    from linker_engine.planning.report_pv_components import (
        pv_components,
        saved_roof_components,
    )
    from linker_engine.planning.series_source import SeriesSource

    from .test_energy_kernel import PROVENANCE
    from .test_pv_generation import geometry, parameter_document, weather

    feed, source, loaded, inverter, battery, controller = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    layout = geometry()
    module_id = layout["module_specs"][0]["id"]
    module_basis = panel_parameters()
    layout["module_specs"] = [{**module_basis["specification"], "id": module_id}]
    parameter_data = parameter_document()
    parameter_data["modules"] = [
        {**module_basis["parameters"], "module_spec_id": module_id}
    ]
    # One additional valid source group distinguishes full-layout quantities
    # from the group actually consumed by the DC scenario, with no extra run.
    layout["arrays"].append(
        {
            **layout["arrays"][0],
            "id": "other-array",
            "name": "Other synthetic PV group",
            "origin_uv": [10, 10],
            "rows": 1,
            "columns": 1,
            "excluded_slots": [],
        }
    )
    parameter_data["arrays"].append(
        {**parameter_data["arrays"][0], "array_id": "other-array"}
    )
    parameter_data["converters"].append(
        {
            **parameter_data["converters"][0],
            "id": "other-group",
            "array_ids": ["other-array"],
        }
    )
    parameters = PvGenerationParameters.read(parameter_data)
    declared_parameters = parameters.model_dump(mode="json")
    declared_parameters["converters"][0]["reference_dc_power_w"] = int(
        declared_parameters["converters"][0]["reference_dc_power_w"]
    )
    project = workspace.create(
        owner,
        "Synthetic two-hour native DC fixture",
        {
            **inputs(feed, 3),
            "geometry": layout,
            "pv_generation": declared_parameters,
        },
        key="dc-project",
    )
    raw = encode({"fixture": "owned synthetic two-hour weather"})
    raw_hash = workspace.blobs.put(raw)
    meteo = weather()
    first = meteo.points[0]
    second = replace(
        first,
        interval=Interval(first.interval.end, first.interval.end + timedelta(hours=1)),
        irradiance_at_utc=first.irradiance_at_utc + timedelta(hours=1),
        source_label_utc=first.source_label_utc + timedelta(hours=1),
        ghi_w_m2=0,
        dni_w_m2=0,
        dhi_w_m2=0,
    )
    meteo = replace(
        meteo,
        points=(first, second),
        source=SeriesSource(raw_hash, "synthetic", "UTC", 3600, encode(PROVENANCE)),
    )
    generated = generate_pv(
        json_object(project.inputs)["geometry"], meteo, parameters, max_array_steps=10
    )
    metadata: FixtureObject = {
        "schema": 1,
        "profile_type": PROFILE_PURPOSE,
        "retention": "permanent",
        "provenance": PROVENANCE,
        "geometry_sha256": digest(encode(json_object(project.inputs)["geometry"])),
        "parameters_sha256": digest(
            encode(json_object(project.inputs)["pv_generation"])
        ),
        "woo_module_inputs": panel_basis(),
        "dependencies": {
            "pv_model_inputs": workspace.blobs.put(generated.inputs_json),
            "pv_model_witness": workspace.blobs.put(generated.witness_json),
        },
    }
    full_parts = json_object(pv_components(workspace.blobs, raw_hash, metadata))
    assert full_parts["components"][0]["quantity"] == 6
    for permission in ("unknown", "prohibited"):
        restricted = copy.deepcopy(layout)
        restricted["sources"][0]["permissions"]["export"] = permission
        restricted_result = generate_pv(
            restricted, meteo, parameters, max_array_steps=10
        )
        restricted_metadata = {
            **metadata,
            "geometry_sha256": digest(encode(restricted)),
            "dependencies": {
                "pv_model_inputs": workspace.blobs.put(restricted_result.inputs_json),
                "pv_model_witness": workspace.blobs.put(restricted_result.witness_json),
            },
        }
        with pytest.raises(ReportSourceExportRequired):
            pv_components(workspace.blobs, raw_hash, restricted_metadata)
    roof_parts = json_object(
        saved_roof_components(
            layout,
            panel_basis(),
            workspace.blobs,
            project.revision,
        )
    )
    assert roof_parts["components"] == full_parts["components"]
    assert roof_parts["scope"] == "saved_roof"
    group_parts = json_object(
        pv_components(
            workspace.blobs,
            raw_hash,
            metadata,
            converter_id=parameters.converters[0].id,
        )
    )
    assert group_parts["components"][0]["quantity"] == 5
    assert "array:1:2" not in group_parts["components"][0]["module_ids"]
    assert (
        json_object(pv_components(workspace.blobs, raw_hash, {}))["reason"]
        == "no_saved_layout"
    )
    without_proof = {k: v for k, v in metadata.items() if k != "woo_module_inputs"}
    assert (
        json_object(pv_components(workspace.blobs, raw_hash, without_proof))["reason"]
        == "no_woo_module_proof"
    )
    corrupted = json_object(generated.witness())
    corrupted["arrays"][0]["module_count"] += 1
    with pytest.raises(VersionUnavailable):
        json_object(
            pv_components(
                workspace.blobs,
                raw_hash,
                {
                    **metadata,
                    "dependencies": {
                        **metadata["dependencies"],
                        "pv_model_witness": workspace.blobs.put_object(corrupted),
                    },
                },
            )
        )
    pv = Assets(workspace).add(
        owner,
        project.id,
        raw,
        "application/json",
        PROFILE_PURPOSE,
        metadata,
        key="dc-pv",
    )
    profile_ids = {}
    for role, power in (("gross_load", 2), ("aux_ac", 0)):
        content = (
            "time,power\n"
            + "".join(
                f"{point.interval.start.isoformat()},{power}\n"
                for point in meteo.points
            )
        ).encode()
        profile_ids[role] = (
            ProfileImport(Assets(workspace))
            .csv(
                owner,
                project.id,
                content,
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
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    dc = DcEnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    service = EnergyService(workspace, ac, max_attempts=1, dc_kernel=dc)
    app = create_private_app(
        workspace,
        service,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 10, 32),
        product_provider=lambda: loaded,
    )
    scenario = DcLossScenario.read(
        {
            "schema_version": 1,
            "model": "constant_window_shared_dc_bus_v1",
            "parameter_basis": "explicit_loss_scenario_with_woo_equipment",
            "battery_port_id": "BAT1",
            "battery_temperature_c": 20,
            "eta_bus_to_battery": 1,
            "eta_battery_to_bus": 1,
            "eta_store_charge": 1,
            "eta_store_discharge": 1,
            "eta_inverter_forward": 1,
            "eta_inverter_reverse": None,
            "internal_aux_kw": 0,
            "standing_loss_rate_per_hour": 0,
            "source_note": "Synthetic analytic loss assumptions; not manufacturer performance",
        }
    )
    with TestClient(app) as client:
        body: FixtureObject = {
            "schema_version": 1,
            "project_id": project.id,
            "expected_revision": project.revision,
            "parameters": scenario.model_dump(mode="json"),
            "source_note": "Synthetic Woo-derived parameter integration",
            "key": "dc-battery",
        }
        unsupported = client.post(
            "/battery/scenario",
            json={
                **body,
                "key": "dc-unsupported-port",
                "parameters": {**body["parameters"], "battery_port_id": "battery-3"},
            },
            headers=headers(owner),
        )
        assert unsupported.status_code == 422
        assert unsupported.json() == {
            "error": {
                "code": "evidence_missing",
                "details": {
                    "product_id": 4107,
                    "fact_id": "battery_port_count",
                    "constraint_id": "selected_battery_port",
                },
            }
        }

        for temperature, reason in [
            (None, "battery_operating_temperature_required"),
            (-5, "battery_temperature_outside_condition"),
        ]:
            refused = client.post(
                "/battery/scenario",
                json={
                    **body,
                    "key": f"dc-temperature-{temperature}",
                    "parameters": {
                        **body["parameters"],
                        "battery_temperature_c": temperature,
                    },
                },
                headers=headers(owner),
            )
            assert refused.status_code == 422
            assert refused.json()["error"]["details"] == {
                "product_id": 2090,
                "fact_id": "max_charge_current_a",
                "constraint_id": reason,
            }
        prepared = client.post("/battery/scenario", json=body, headers=headers(owner))
        assert prepared.status_code == 200, prepared.text
        assert (
            client.post("/battery/scenario", json=body, headers=headers(owner)).json()
            == prepared.json()
        )
        asset = prepared.json()
        assert json_object(
            workspace.blobs.object(asset["content_sha256"])
        ) == scenario.model_dump(mode="json")
        project = workspace.revise(
            owner,
            project.id,
            project.revision,
            {
                **project.inputs,
                "energy_replay": {
                    "schema_version": 1,
                    "gross_load_asset_id": profile_ids["gross_load"],
                    "critical_load_asset_id": None,
                    "pv_available_asset_id": pv.id,
                    "aux_ac_asset_id": profile_ids["aux_ac"],
                    "battery_parameters_asset_id": asset["id"],
                    "initial_inventory": {
                        "pv_kwh": 0,
                        "grid_kwh": 0,
                        "initial_unknown_kwh": 0,
                        "basis": "synthetic_fixture",
                        "source_note": "Initially empty fixture",
                    },
                    "schedule": [
                        {
                            "start_utc": first.interval.start.isoformat(),
                            "end_utc": second.interval.end.isoformat(),
                            "mode": "connected",
                            "reserve_kwh": 0,
                            "import_cap_kw": None,
                            "export_cap_kw": 0,
                            "pv_enabled": True,
                            "allow_grid_charge": False,
                        }
                    ],
                    "controller": "self_consumption_with_reserve_v1",
                    "terminal_min_kwh": None,
                    "coupling": "shared_dc",
                    "pv_converter_id": "converter",
                    "aux_dc_kw": 0,
                },
            },
            key="dc-attach",
        )
        evaluated = client.post(
            "/runs/energy",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "expected_revision": project.revision,
                "key": "dc-run",
            },
            headers=headers(owner),
        )
        assert evaluated.status_code == 200, evaluated.text
    registry = service_registry(service, None)
    executor = Worker(
        Jobs(workspace),
        "dc-native",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert executor.run_once()
    saved = workspace.run(owner, evaluated.json()["id"])
    assert saved.state == "succeeded", saved.error
    assert json_object(saved.result)["kind"] == dc.kind
    assert json_object(saved.result)["model"]["usable_window_kwh"] == 13.5
    assert json_object(saved.result)["model"]["charge_terminal_kw"] == pytest.approx(
        8.064
    )
    assert json_object(saved.result)["metrics"]["load_demand_kwh"] == 4
    assert json_object(saved.result)["scenario_constraint_status"] == "satisfied"
    assert "pv_generated_ac_kwh" not in json_object(saved.result)["metrics"]
    assert (
        json_object(saved.result)["prepared_dc_parameters"]["product_revisions"]
        == json_object(project.inputs)["equipment_selection"]["product_revisions"]
    )
    from linker_engine.planning.dc_energy_parameters import DcPreparedParameters
    from linker_engine.planning.energy_equipment import assess_dc_energy_equipment
    from linker_engine.planning.trace_window import TraceWindow

    page = json_object(
        TraceWindow(workspace).page(owner, saved.id, offset=0, page_size=2)
    )
    assert page["measurement_boundaries"]["pv"] == "PV_DC_bus"
    assert page["measurement_boundaries"]["charge"] == "battery_DC_terminal"
    witness = json_object(
        workspace.blobs.object(metadata["dependencies"]["pv_model_witness"])
    )
    selected_pv = next(
        group
        for group in witness["converters"]
        if group["id"]
        == json_object(project.inputs)["energy_replay"]["pv_converter_id"]
    )
    assert page["rows"][0]["pv_kw"] == selected_pv["dc_available_w"][0] / 1000
    assert page["rows"][0]["pv_kw"] > selected_pv["available_ac_w"][0] / 1000
    # Reuse the saved physical model and source to check the hardware mode.
    # This does not replay physics or invent a backup rating for the fixture.
    outage_inputs = json_object(copy.deepcopy(project.inputs))
    outage_inputs["energy_replay"]["schedule"][0]["mode"] = "outage"
    outage_inputs["energy_replay"]["critical_load_asset_id"] = outage_inputs[
        "energy_replay"
    ]["gross_load_asset_id"]
    prepared_model = DcPreparedParameters.read(
        json_object(saved.result)["prepared_dc_parameters"]
    ).battery_model(
        json_object(saved.result)["pinned_assets"]["battery.dc_prepared_parameters"]
    )
    mismatch = json_object(
        assess_dc_energy_equipment(
            outage_inputs, json_object(source.equipment_basis()), prepared_model
        )
    )
    assert any(
        check["id"] == "scenario_operating_mode" and check["status"] == "violated"
        for check in mismatch["assessment"]["checks"]
    )
    for locale in ("en", "de"):
        frozen_report = json_object(
            report_sources(
                workspace,
                source,
                owner,
                project,
                ReportOptions(
                    locale=locale,
                    energy_run_id=saved.id,
                    pv_run_id=None,
                    equipment_run_id=None,
                    logo=None,
                ),
            )
        )
        report = build_report(
            {**frozen_report, "locale": locale, "generated_at": "2026-10-25T00:00:00Z"}
        )
        assert (
            frozen_report["equipment"]
            == json_object(saved.result)["equipment_binding"]["assessment"]
        )
        assert (
            frozen_report["woo_bases"]["equipment"]
            == frozen_report["woo_bases"]["energy_equipment"]
        )
        bom = next(section for section in report.sections if section.id == "bom")
        assert bom.table is not None
        assert (
            len(
                [
                    r
                    for r in bom.table.rows
                    if r[-1]
                    == (
                        "Selected equipment" if locale == "en" else "Ausgewählte Geräte"
                    )
                ]
            )
            == 3
        )
        panel_label = (
            "Generic 460 W PV module"
            if locale == "en"
            else "Generisches 460-W-PV-Modul"
        )
        assert not any(panel_label in row[1] for row in bom.table.rows)
        assert any(
            row[0] == ("3 pcs" if locale == "en" else "3 St.")
            and battery["model"] in row[1]
            for row in bom.table.rows
        )
        part_table = next(
            section for section in report.sections if section.id == "pv-components"
        ).table
        assert part_table is not None
        assert any(row[0] == "5" and panel_label in row[1] for row in part_table.rows)
        section = next(section for section in report.sections if section.id == "energy")
        dc_rows = [row for row in section.rows if "(DC)" in row.label]
        assert len(dc_rows) == 2 and all(row.value.endswith("kWh") for row in dc_rows)
        assert "DC" in section.paragraphs[0] and "AC" in section.paragraphs[0]
    facts = json_object(saved.result)["prepared_dc_parameters"]["source_facts"]
    assert (
        facts["4107.max_battery_charge_a"]["qualifier"]
        == inverter["figures"]["max_battery_charge_a"]["qualifier"]
    )
    assert facts["4107.max_battery_charge_a"]["status"] == "conditional"
    assert (
        facts["2090.max_charge_current_a"]["condition_match"]["battery_temperature_c"]
        == 20
    )
    assert facts["2090.rated_power_w"]["value"] == 9.216
    assert facts["2090.rated_power_w"]["selected_module_count"] == 3
    assert (
        json_object(saved.result)["prepared_dc_parameters"]["battery"][
            "charge_power_limit_kw"
        ]
        == 9.216
    )
    # A table declared in W cannot silently carry a mismatching duplicate cell.
    from linker_engine.planning.equipment_fact_resolution import (
        FactContext,
        resolve_fact,
    )
    from linker_engine.planning.equipment_inputs import EquipmentSelection

    bad = copy.deepcopy(json_object(compile_product(battery))["facts"]["rated_power_w"])
    bad["columns"][2]["unit"] = "Wp"
    context = FactContext(
        EquipmentSelection.read(json_object(project.inputs)["equipment_selection"]),
        {p["canonical_product_id"]: p for p in feed["products"]},
        20,
        "BAT1",
        2,
    )
    assert (
        resolve_fact(bad, context, "bank_rated_dc_power").issue
        == "column_value_unit_mismatch"
    )
    # Retained historical raw request bytes keep their original durable identity.
    from linker_engine.planning.http_asset_intake import HttpAssetIntake
    from linker_engine.planning.http_documents import BatteryScenario

    historic = json.loads(
        (
            Path(__file__).resolve().parents[4]
            / "apps/planner/tests/fixtures/dc-energy-run.json"
        ).read_text()
    )["run"]["result"]
    old = historic["prepared_dc_parameters"]["loss_scenario"]
    old_body = BatteryScenario.model_validate({**body, "parameters": old})
    assert (
        digest(HttpAssetIntake.battery_content(old_body))
        == historic["pinned_assets"]["battery.raw"]
    )
    from .test_energy_kernel import authored_from_execution

    authored = authored_from_execution(
        json_object(project.inputs), scenario.model_dump(mode="json")
    )
    selection = authored.pop("equipment_selection")
    authored["equipment_setup"] = {
        key: value for key, value in selection.items() if key != "product_revisions"
    }
    snapshot, calculated = service.calculate(
        owner,
        project.id,
        project.revision,
        authored,
        key="current-dc-declarations",
        input_contract="authored_energy_calculation_v1",
    )
    assert "energy_replay" not in snapshot.inputs
    assert "equipment_selection" not in snapshot.inputs
    assert executor.run_once()
    calculated = workspace.run(owner, calculated.id)
    assert calculated.state == "succeeded", calculated.error
    assert json_object(calculated.result)["metrics"]["load_demand_kwh"] == 4
    assert json_object(calculated.result)["model"]["usable_window_kwh"] == 13.5
    assert json_object(calculated.result)["kind"] == dc.kind
    from linker_engine.publication import PublicationUnavailable

    def unavailable_source() -> FixtureObject:
        raise PublicationUnavailable("fixture: Woo publication unavailable")

    monkeypatch.setattr(loaded.publication, "read", unavailable_source)
    retried_snapshot, retried_run = service.calculate(
        owner,
        project.id,
        project.revision,
        authored,
        key="current-dc-declarations",
        input_contract="authored_energy_calculation_v1",
    )
    assert retried_snapshot == snapshot and retried_run.id == calculated.id
    with pytest.raises(VersionUnavailable):
        service.calculate(
            owner,
            project.id,
            snapshot.revision,
            authored,
            key="unavailable-current-dc",
            input_contract="authored_energy_calculation_v1",
        )
    assert workspace.get(owner, project.id) == snapshot


def test_historic_product_panel_proof_is_retired() -> None:
    source = ProductSources(lambda: pytest.fail("no Woo read for a retired panel"))
    with pytest.raises(ProductEvidenceChanged):
        source.confirm_basis(
            {
                "schema_version": 1,
                "publication": {
                    "reference_inputs": [{"reference_input_id": "retired"}]
                },
            }
        )
    source.confirm_basis(panel_basis())


def test_cited_quantities_keep_apparent_power_conditions_and_table_columns(
    feed: FixtureObject,
) -> None:
    row = copy.deepcopy(next(p for p in feed["products"] if p["id"] == 1946))
    original = row["figures"]["backup_power_kw"]
    original["unit"] = "kVA"
    original["qualifier"] = {"en": "With the specified transfer equipment."}
    from linker_engine.planning.equipment_fact_resolution import (
        FactContext,
        resolve_fact,
    )
    from linker_engine.planning.equipment_inputs import EquipmentSelection

    battery = copy.deepcopy(next(p for p in feed["products"] if p["id"] == 2090))
    battery["figures"]["rated_power_w"] = {
        "value": 3072,
        "unit": "W",
        "citation": copy.deepcopy(
            battery["figures"]["module_energy_kwh_usable"]["citation"]
        ),
    }
    generic = json_object(compile_product(battery))["facts"]["rated_power_w"]
    context = FactContext(
        EquipmentSelection.read(inputs(feed, 3)["equipment_selection"]),
        {p["canonical_product_id"]: p for p in feed["products"]},
    )
    assert (
        resolve_fact(generic, context, "bank_rated_dc_power").issue
        == "system_power_basis_required"
    )

    compiled = json_object(compile_product(row))
    figure = compiled["facts"]["backup_power_kw"]
    assert figure["quantity"] == "apparent_power" and figure["unit"] == "kVA"
    assert (
        figure["status"] == "conditional"
        and figure["source"]["page"] == original["citation"]["page"]
    )
    assert "ac_power_kw" not in compiled and "nominal_kwh" not in compiled
    controller = json_object(
        compile_product(next(p for p in feed["products"] if p["id"] == 2092))
    )
    ranges = controller["facts"]["system_operating_voltage_range_v"]
    assert ranges["shape"] == "ordered_values" and len(ranges["value"]) == 5
    assert "max_fault_current_a" not in controller["facts"]


def test_energy_uses_its_simulated_window_instead_of_the_manual_sizing_target(
    feed: FixtureObject, workspace: Workspace, owner: Actor
) -> None:
    scenario = create_scenario(workspace, owner)
    proposed = {**scenario.inputs, **inputs(feed, 3)}
    basis = {"products": feed["products"], "compatibility": feed["compatibility"]}
    model = BatteryParameters.read(BATTERY).battery("a" * 64)
    binding = json_object(
        assess_energy_equipment(proposed, basis, replace(model, usable_window_kwh=15))
    )
    assessment = binding["assessment"]
    checks = {check["id"]: check for check in assessment["checks"]}
    # The original manual target is 10 kWh and would pass. The actual replay
    # window is 15 kWh, exceeding 3 x the source's 4.5 kWh usable module energy.
    assert proposed["equipment_selection"]["required_usable_kwh"] == 10
    assert checks["usable_energy"]["required"] == 15
    assert checks["usable_energy"]["actual"] == 13.5
    assert checks["usable_energy"]["status"] == "violated"
    assert checks["continuous_battery_ac_charge"]["status"] == "unresolved"
    assert assessment["overall_status"] == "violated"


def test_energy_freezes_woo_selection_and_keeps_mode_failure_separate_from_replay(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    loaded = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    withdrawn = False

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            manifest["products"] = [
                row for row in manifest["products"] if row["product_id"] != 2090
            ]
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    source = ProductSources(lambda: loaded)
    kernel = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    service = EnergyService(workspace, kernel, max_attempts=1)
    scenario = create_scenario(workspace, owner, outage=True)
    project = workspace.revise(
        owner,
        scenario.id,
        scenario.revision,
        {**scenario.inputs, **inputs(feed, 3)},
        key="energy-with-equipment",
    )
    run = service.evaluate(owner, project.id, project.revision, key="bound-energy")
    assert energy_worker(workspace, kernel).run_once()
    saved = workspace.run(owner, run.id)
    assert saved.state == "succeeded"
    result = json_object(saved.result)
    assert result is not None
    binding = result["equipment_binding"]
    assert binding["selection"] == json_object(project.inputs)["equipment_selection"]
    assert (
        json_object(
            workspace.blobs.object(result["pinned_assets"]["equipment.selection"])
        )
        == binding["selection"]
    )
    checks = {check["id"]: check for check in binding["assessment"]["checks"]}
    assert checks["scenario_operating_mode"]["status"] == "violated"
    assert checks["usable_energy"]["required"] == 5
    assert checks["usable_energy"]["actual"] == 13.5
    assert result["scenario_constraint_status"] == "satisfied"
    assert binding["assessment"]["overall_status"] == "violated"
    # An old completed snapshot remains historical; a new action cannot
    # acquire the withdrawn product's current permission through that result.
    withdrawn = True
    with pytest.raises(ProductEvidenceChanged):
        service.evaluate(owner, project.id, project.revision, key="after-withdrawal")
    assert workspace.run(owner, run.id).result == result
    withdrawn = False
    options = ReportOptions(
        locale="en",
        energy_run_id=run.id,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    report_source = json_object(
        report_sources(workspace, source, owner, project, options)
    )
    assert report_source["energy_equipment"] == binding
    assert (
        report_source["woo_bases"]["energy_equipment"]
        == result["pinned_assets"]["woo.equipment_inputs"]
    )
    for locale in ("en", "de"):
        displayed_source = copy.deepcopy(report_source)
        # The existing two-segment fixture spans the DST transition. These
        # equivalent offsets must be printed as actual UTC calculation periods.
        displayed_source["energy_scenario"]["schedule"][0].update(
            start_utc="2024-03-31T00:00:00+01:00",
            end_utc="2024-03-31T00:30:00+01:00",
        )
        displayed_source["energy_scenario"]["schedule"][1].update(
            start_utc="2024-03-31T00:30:00+01:00",
            end_utc="2024-03-31T03:00:00+02:00",
        )
        report = build_report({**displayed_source, "locale": locale})
        energy_section = next(s for s in report.sections if s.id == "energy")
        assert [r.value for r in energy_section.rows[:2]] == [
            "2024-03-30T23:00:00+00:00 – 2024-03-30T23:30:00+00:00",
            "2024-03-30T23:30:00+00:00 – 2024-03-31T01:00:00+00:00",
        ]
        assert all("UTC" in r.label for r in energy_section.rows[:2])
        # Historical report sources predate energy_scenario. Genie renders
        # those same sources in another language; do not read today's project
        # to invent a period or make the retained report unreadable.
        legacy_source = {**report_source, "locale": locale}
        legacy_source.pop("energy_scenario")
        legacy_energy = next(
            s for s in build_report(legacy_source).sections if s.id == "energy"
        )
        assert legacy_energy.rows[0].value == "—"
        assert legacy_energy.rows[1:] == energy_section.rows[2:]
        section = next(
            section for section in report.sections if section.id == "energy-equipment"
        )
        assert section.table is not None
        assert len(section.table.rows) == 6
        assert section.table.rows[0][2:] == [
            "13,5 kWh" if locale == "de" else "13.5 kWh",
            "5 kWh",
        ]
        assert section.rows[0].value in (
            "Requirements not met",
            "Anforderungen nicht erfüllt",
        )
        assert any("H2-10K-T3" in row.value for row in section.rows)
        assert any(row.href and "2" in row.label for row in section.rows)
    bad_voltage = json_object(
        assess_energy_equipment(
            {**project.inputs, **inputs(feed, 1)},
            json_object(
                workspace.blobs.object(result["pinned_assets"]["woo.equipment_inputs"])
            ),
            BatteryParameters.read(BATTERY).battery("a" * 64),
        )
    )
    report = build_report({**report_source, "energy_equipment": bad_voltage})
    section = next(
        section for section in report.sections if section.id == "energy-equipment"
    )
    assert section.rows[0].value == "Requirements not met"
    assert section.table is not None
    assert any(
        row[0] == "Battery voltage" and row[1] == "Requirements not met"
        for row in section.table.rows
    )
    changed = workspace.revise(
        owner,
        project.id,
        project.revision,
        {
            **project.inputs,
            "equipment_selection": {
                **json_object(project.inputs)["equipment_selection"],
                "modules_per_stack": 4,
            },
        },
        key="different-equipment-same-energy-input",
    )
    with pytest.raises(ReportInputsChanged):
        json_object(report_sources(workspace, source, owner, changed, options))


@pytest.mark.parametrize(
    ("count", "voltage_status"), [(1, "violated"), (2, "unresolved"), (3, "satisfied")]
)
def test_stack_window_is_not_a_flattened_range_or_a_fault_current_power(
    feed: FixtureObject, count: int, voltage_status: str
) -> None:
    result = json_object(
        assess_equipment(
            inputs(feed, count),
            {"products": feed["products"], "compatibility": feed["compatibility"]},
        )
    )
    checks = {item["id"]: item for item in result["checks"]}
    assert checks["battery_voltage"]["status"] == voltage_status
    assert checks["continuous_battery_ac_output"]["status"] == "satisfied"
    assert checks["battery_sales_unit"]["status"] == "satisfied"
    assert checks["parallel_stacks"]["status"] == "satisfied"
    assert checks["usable_energy"]["status"] == (
        "satisfied" if count == 3 else "unresolved"
    )
    assert result["country_assessment"]["status"] == "unresolved"
    if count == 3:
        unlabeled = copy.deepcopy(feed)
        del next(p for p in unlabeled["products"] if p["id"] == 2092)["figures"][
            "system_operating_voltage_range_v"
        ]["columns"]
        unproven = json_object(
            assess_equipment(
                inputs(feed, count),
                {
                    "products": unlabeled["products"],
                    "compatibility": unlabeled["compatibility"],
                },
            )
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
        unresolved = json_object(
            assess_equipment(
                inputs(feed, 3),
                {
                    "products": unknown_unit["products"],
                    "compatibility": unknown_unit["compatibility"],
                },
            )
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
        unresolved = json_object(
            assess_equipment(
                no_count,
                {
                    "products": scalar["products"],
                    "compatibility": scalar["compatibility"],
                },
            )
        )
        assert (
            next(c for c in unresolved["checks"] if c["id"] == "battery_voltage")[
                "status"
            ]
            == "unresolved"
        )


def test_native_command_worker_receipt_and_inflight_withdrawal_use_one_frozen_pool(
    feed: FixtureObject,
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

    def current(self: Publication) -> FixtureObject:
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
        json_object(source.equipment_basis())
    feed["figure_projection_version"] = 2
    with pytest.raises(VersionUnavailable):
        json_object(source.equipment_basis())
    feed["compatibility_origin"] = "woocommerce"
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
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
        equipment_search=search,
        product_provider=lambda: shared,
    )
    registry = service_registry(energy, None, None, equipment, search)
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
                "inputs": {
                    **inputs(feed, 3),
                    "equipment_requirements": {
                        "schema_version": 1,
                        "grid_phase": 3,
                        "operating_mode": "grid_connected",
                        "pv_dc_kw": 10,
                        "required_usable_kwh": 15,
                        "required_discharge_ac_kw": 5,
                    },
                },
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
        proof = json_object(completed.result)["pinned_assets"]["woo.equipment_inputs"]
        assert (
            json_object(workspace.blobs.object(proof))["figure_projection_version"] == 2
        )
        search_command = {**command, "key": "search-first"}
        found = client.post(
            "/runs/equipment-search", json=search_command, headers=headers()
        )
        assert found.status_code == 200, found.text
        assert worker.run_once()
        searched = workspace.run(owner, found.json()["id"])
        assert searched.state == "succeeded", searched.error
        candidate = json_object(searched.result)["search"]["candidates"][0]
        detail = client.post(
            "/equipment/candidates/read",
            json={
                "schema_version": 1,
                "run_id": searched.id,
                "candidate_id": candidate["id"],
            },
            headers=headers(),
        )
        assert (
            detail.status_code == 200
            and detail.json()["assessment_sha256"] == candidate["assessment_sha256"]
        )
        assert detail.json()["assessment"]["selected_products"]
        selected_inputs: FixtureObject = {
            # Native browser JSON writes whole-valued floats as integers.
            "equipment_selection": {
                **candidate["selection"],
                "pv_dc_kw": 10,
                "required_usable_kwh": 15,
                "required_discharge_ac_kw": 5,
            },
            "equipment_candidate": {
                "run_id": searched.id,
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        }
        check_equipment_candidate(
            workspace, owner, pid, selected_inputs, products=source
        )
        single_bypass = copy.deepcopy(selected_inputs)
        single_bypass["pv_string_plan"] = {
            "schema_version": 1,
            "inverter_product_id": candidate["selection"]["inverter_product_id"],
            "minimum_ambient_c": None,
            "temperature_source": None,
            "strings": [],
        }
        with pytest.raises(
            ReportInputsChanged, match="has not assessed"
        ) as missing_wiring:
            report_sources(
                workspace,
                source,
                owner,
                replace(workspace.get(owner, pid), inputs=single_bypass),
                ReportOptions(
                    locale="en",
                    energy_run_id=None,
                    pv_run_id=None,
                    equipment_run_id=None,
                    logo=None,
                ),
            )
        assert missing_wiring.value.code == "report_wiring_check_required"
        # A named check must be evaluated against the saved selection and wiring,
        # even when the search choice is still part of the saved project.
        direct = ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=completed.id,
            logo=None,
        )
        with pytest.raises(
            InvalidInput, match="saved project selection|has not assessed"
        ):
            report_sources(
                workspace,
                source,
                owner,
                replace(workspace.get(owner, pid), inputs=single_bypass),
                direct,
            )
        with pytest.raises(InvalidInput, match="differs from the adopted"):
            report_sources(
                workspace,
                source,
                owner,
                replace(workspace.get(owner, pid), inputs=selected_inputs),
                direct,
            )
        selected_inputs["equipment_candidate"]["assessment_sha256"] = "0" * 64
        with pytest.raises(InvalidInput):
            check_equipment_candidate(
                workspace, owner, pid, selected_inputs, products=source
            )
        selected_inputs["equipment_candidate"]["assessment_sha256"] = candidate[
            "assessment_sha256"
        ]
        withdrawn = True
        refused_adoption = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": 1,
                "inputs": selected_inputs,
                "key": "adopt-withdrawn-candidate",
            },
            headers=headers(),
        )
        assert refused_adoption.status_code == 409, refused_adoption.text
        assert workspace.get(owner, pid).revision == 1
        withdrawn = False
        offline = True
        replayed = client.post("/runs/equipment", json=command, headers=headers())
        assert replayed.status_code == 200 and replayed.json()["id"] == first
        historical_search = client.post(
            "/runs/equipment-search", json=search_command, headers=headers()
        )
        assert (
            historical_search.status_code == 200
            and historical_search.json()["id"] == searched.id
        )
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

        def withdraw_after_assessment(
            inputs: FixtureObject, basis: FixtureObject
        ) -> FixtureObject:
            nonlocal withdrawn
            result = json_object(original(inputs, basis))
            withdrawn = True
            return result

        monkeypatch.setattr(
            "linker_engine.planning.equipment_kernel.assess_equipment",
            withdraw_after_assessment,
        )
        assert worker.run_once()
        refused = workspace.run(owner, second.json()["id"])
        assert refused.state == "failed" and refused.result is None
        assert json_object(refused.error)["code"] == "product_evidence_changed"
        assert workspace.run(owner, first).result == completed.result

        # A customer may keep a previously adopted search result while adding
        # wiring. The matching, completed check must be usable in the report.
        from linker_engine.planning.geometry import panel_poses, read_geometry

        from .test_pv_generation import geometry

        withdrawn = False
        monkeypatch.setattr(
            "linker_engine.planning.equipment_kernel.assess_equipment", original
        )
        layout = geometry()
        module = panel_parameters(electrical=True)
        layout["module_specs"] = [{**module["specification"], "id": "module"}]
        layout["arrays"][0].update(rows=2, columns=6, excluded_slots=[])
        module_ids = [p.id for p in panel_poses(read_geometry(layout)) if p.included]
        assert len(module_ids) == 12
        wired_inputs = {
            **copy.deepcopy(selected_inputs),
            "geometry": layout,
            "pv_string_plan": {
                "schema_version": 1,
                "inverter_product_id": candidate["selection"]["inverter_product_id"],
                "minimum_ambient_c": -10,
                "temperature_source": "Synthetic design temperature",
                "strings": [
                    {"id": "s_a", "mppt": 1, "input": 1, "module_ids": module_ids[:6]},
                    {"id": "s_b", "mppt": 1, "input": 2, "module_ids": module_ids[6:]},
                ],
            },
        }
        revised = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": 2,
                "inputs": wired_inputs,
                "input_contract": "project_panel_parameters_v1",
                "key": "adopt-candidate-with-wiring",
            },
            headers=headers(),
        )
        assert revised.status_code == 200, revised.text
        wired = workspace.get(owner, pid)
        assert wired.revision == 3
        original_choice = copy.deepcopy(wired.inputs["equipment_candidate"])
        check = client.post(
            "/runs/equipment",
            json={**command, "expected_revision": 3, "key": "wired-equipment-check"},
            headers=headers(),
        )
        assert check.status_code == 200, check.text
        assert worker.run_once()
        wired_run = workspace.run(owner, check.json()["id"])
        assert wired_run.state == "succeeded", wired_run.error
        wiring = json_object(wired_run.result)["assessment"]["pv_electrical"]
        assert [row["id"] for row in wiring["strings"]] == ["s_a", "s_b"]
        with pytest.raises(ReportInputsChanged, match="report demand differs"):
            report_sources(
                workspace,
                source,
                owner,
                wired,
                direct.model_copy(update={"equipment_run_id": None}),
            )
        report = json_object(
            report_sources(
                workspace,
                source,
                owner,
                wired,
                direct.model_copy(update={"equipment_run_id": wired_run.id}),
            )
        )
        assert report["candidate"] == original_choice
        assert report["equipment"]["pv_electrical"] == wiring
        assert any(row["run_id"] == wired_run.id for row in report["source_runs"])
        assert (
            workspace.get(owner, pid).inputs["equipment_candidate"] == original_choice
        )


@pytest.mark.parametrize("plant", [False, True])
def test_current_equipment_check_freezes_unsaved_manual_hardware_and_pv_wiring_for_report(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    plant: bool,
) -> None:
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS

    from .test_private_http import Rig
    from .test_pv_generation import geometry

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    withdrawn = False

    def current(publication: Publication) -> FixtureObject:
        manifest = publication_manifest(publication.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            manifest["products"] = [
                p for p in manifest["products"] if p["product_id"] != 4107
            ]
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, equipment=equipment, reports=reports)
    worker = Worker(
        Jobs(workspace),
        "current-hardware-check",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment=equipment,
        reports=reports,
        product_provider=lambda: loaded,
    )
    layout = geometry()
    module = panel_parameters(electrical=True)
    layout["module_specs"] = [{**module["specification"], "id": "module"}]
    layout["arrays"][0].update(rows=2, columns=6, excluded_slots=[])
    module_ids = [p.id for p in panel_poses(read_geometry(layout)) if p.included]
    setup = inputs(feed, 3)["equipment_selection"]
    setup.pop("product_revisions")
    setup["pv_dc_kw"] = 5.52
    declared: FixtureObject = {
        "brief": {**incomplete_brief(), "system_scope": "new_pv_storage"},
        "equipment_setup": setup,
        "geometry": layout,
        "pv_string_plan": {
            "schema_version": 1,
            "inverter_product_id": 4107,
            "minimum_ambient_c": -10,
            "temperature_source": "Explicit synthetic design temperature",
            "strings": [
                {"id": "s_a", "mppt": 1, "input": 1, "module_ids": module_ids[:6]},
                {"id": "s_b", "mppt": 1, "input": 2, "module_ids": module_ids[6:]},
            ],
        },
    }
    if plant:
        plan = declared.pop("pv_string_plan")
        declared.pop("equipment_setup")
        declared["equipment_plant_setup"] = {
            "schema_version": 1,
            "requirements": {
                key: setup[key]
                for key in EquipmentRequirements.model_fields
                if key in setup
            },
            "units": [
                {
                    "id": uid,
                    "name": uid.upper(),
                    "inputs": {
                        "equipment_setup": {**setup, "pv_dc_kw": 2.76},
                    },
                }
                for uid in ("a", "b")
            ],
            "parallel_groups": [],
        }
        declared["pv_plant_string_plan"] = {
            "schema_version": 1,
            "units": [
                {
                    "unit_id": uid,
                    "inverter_instance_id": None,
                    "plan": {**plan, "strings": [plan["strings"][index]]},
                }
                for index, uid in enumerate(("a", "b"))
            ],
        }
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("current-manual-wiring")
        command = {
            "schema_version": 1,
            "project_id": pid,
            "expected_revision": 1,
            "inputs": declared,
            "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
            "key": "check-current-wiring",
        }
        if plant:
            malformed = copy.deepcopy(declared)
            malformed["equipment_plant_setup"]["parallel_groups"] = [
                {
                    "id": "shared",
                    "unit_ids": ["a", "b"],
                    "controller_product_id": None,
                    "comparison_controller_product_id": None,
                    "unknown_setting": True,
                }
            ]
            response = client.post(
                "/runs/check-equipment",
                json={**command, "inputs": malformed},
                headers=headers(owner),
            )
            assert response.status_code == 422, response.text
            assert response.json()["error"]["code"] == "invalid_input"
            assert not workspace.runs(owner, pid)
        invalid = copy.deepcopy(declared)
        invalid_setup = (
            invalid["equipment_plant_setup"]["units"][1]["inputs"]["equipment_setup"]
            if plant
            else invalid["equipment_setup"]
        )
        invalid_setup["inverter_product_id"] = None
        refused = client.post(
            "/runs/check-equipment",
            json={**command, "inputs": invalid},
            headers=headers(owner),
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["error"]["fields"] == [
            "equipment_plant_setup.units[1].inputs.equipment_setup.inverter_product_id"
            if plant
            else "equipment_setup.inverter_product_id"
        ]
        assert workspace.get(owner, pid).revision == 1
        assert workspace.runs(owner, pid) == []
        if not plant:
            empty = copy.deepcopy(declared)
            empty["equipment_selection"] = inputs(feed, 3)["equipment_selection"]
            empty["equipment_setup"].update(
                inverter_product_id=None,
                battery_product_id=None,
                modules_per_stack=None,
                parallel_stacks=None,
                accessory_product_ids=[],
            )
            missing = client.post(
                "/runs/check-equipment",
                json={**command, "inputs": empty},
                headers=headers(owner),
            )
            assert missing.status_code == 422, missing.text
            assert missing.json()["error"]["fields"] == [
                "equipment_setup.inverter_product_id"
            ]
            with workspace.database.transaction() as connection:
                connection.execute(
                    "CREATE TRIGGER fail_check_queue BEFORE INSERT ON jobs BEGIN SELECT RAISE(ABORT, 'queue unavailable'); END"
                )
            failed = client.post(
                "/runs/check-equipment", json=command, headers=headers(owner)
            )
            assert failed.status_code == 500
            assert workspace.get(owner, pid).revision == 1
            assert workspace.runs(owner, pid) == []
            assert rig.replay("/runs/check-equipment", command)["status"] == "absent"
            with workspace.database.transaction() as connection:
                connection.execute("DROP TRIGGER fail_check_queue")
        reply = rig.post("/runs/check-equipment", command)
        assert reply["project"]["revision"] == 2
        assert "equipment_selection" not in reply["project"]["inputs"]
        assert "energy_scenario" not in reply["project"]["inputs"]
        assert "profile_selections" not in reply["project"]["inputs"]
        assert rig.post("/runs/check-equipment", command) == reply
        assert rig.replay("/runs/check-equipment", command)["result"] == reply
        assert rig.replay("/runs/find-equipment", command)["status"] == "absent"
        assert worker.run_once()
        checked = workspace.run(owner, reply["run"]["id"])
        assert checked.state == "succeeded", checked.error
        frozen = json_object(workspace.pinned_inputs(checked.manifest))
        frozen_selection = (
            frozen["equipment_plant"]["units"][0]["selection"]
            if plant
            else frozen["equipment_selection"]
        )
        assert frozen_selection["product_revisions"]["4107"] == next(
            p["product_revision"]
            for p in feed["products"]
            if p["canonical_product_id"] == 4107
        )
        wiring = json_object(checked.result)["assessment"]["pv_electrical"]
        strings = (
            [s for unit in wiring["units"] for s in unit["assessment"]["strings"]]
            if plant
            else wiring["strings"]
        )
        assert [s["id"] for s in strings] == ["s_a", "s_b"]
        assert (
            next(c for c in wiring["checks"] if c["id"].endswith("pv_layout_coverage"))[
                "status"
            ]
            == "satisfied"
        )
        options = ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=checked.id,
            logo=None,
        )
        report_source = json_object(
            report_sources(workspace, source, owner, workspace.get(owner, pid), options)
        )
        assert report_source["equipment"]["pv_electrical"] == wiring
        reported = reports.evaluate(owner, pid, 2, options, key="manual-wiring-report")
        assert worker.run_once()
        completed = workspace.run(owner, reported.id)
        assert completed.state == "succeeded", completed.error
        pdf = json_object(completed.result)["prepared_asset"]["content_sha256"]
        assert workspace.blobs.read(pdf).startswith(b"%PDF-")
        pinned = json_object(checked.result)["pinned_assets"]
        assert "pv_module_inputs" in workspace.blobs.object(
            pinned["woo.equipment_inputs"]
        )
        withdrawn = True
        assert rig.post("/runs/check-equipment", command)["run"]["id"] == checked.id
        unavailable = client.post(
            "/runs/check-equipment",
            json={**command, "expected_revision": 2, "key": "after-withdrawal"},
            headers=headers(owner),
        )
        assert unavailable.status_code == 422, unavailable.text
        assert unavailable.json()["error"]["fields"] == [
            "equipment_plant_setup.units[0].inputs.equipment_setup.inverter_product_id"
            if plant
            else "equipment_setup.inverter_product_id"
        ]
        assert workspace.get(owner, pid).revision == 2
        assert len(workspace.runs(owner, pid)) == 2
        withdrawn = False
        changed_hardware = copy.deepcopy(reply["project"]["inputs"])
        changed_setup = (
            changed_hardware["equipment_plant_setup"]["units"][0]["inputs"][
                "equipment_setup"
            ]
            if plant
            else changed_hardware["equipment_setup"]
        )
        changed_setup["modules_per_stack"] = 4
        with pytest.raises(ReportInputsChanged, match="hardware declarations differ"):
            report_sources(
                workspace,
                source,
                owner,
                replace(workspace.get(owner, pid), inputs=changed_hardware),
                options,
            )
        changed_backup = copy.deepcopy(reply["project"]["inputs"])
        changed_backup["backup_demand"] = {
            "schema_version": 1,
            "load_kw": 3,
            "duration_hours": 4,
        }
        with pytest.raises(ReportInputsChanged):
            report_sources(
                workspace,
                source,
                owner,
                replace(workspace.get(owner, pid), inputs=changed_backup),
                options,
            )
        notes = copy.deepcopy(reply["project"]["inputs"])
        notes["brief"]["project_note"] = "Current customer note after qualification"
        noted = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": 2,
                "inputs": notes,
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "note-after-check",
            },
        )
        assert (
            json_object(
                report_sources(
                    workspace, source, owner, workspace.get(owner, pid), options
                )
            )["equipment"]["pv_electrical"]
            == wiring
        )
        rewired = copy.deepcopy(noted["inputs"])
        changed_plan = (
            rewired["pv_plant_string_plan"]["units"][0]["plan"]
            if plant
            else rewired["pv_string_plan"]
        )
        changed_plan["minimum_ambient_c"] = -20
        saved = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": noted["revision"],
                "inputs": rewired,
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "new-wiring-after-check",
            },
        )
        with pytest.raises(ReportInputsChanged, match="PV strings differ"):
            report_sources(workspace, source, owner, workspace.get(owner, pid), options)
        current_check = rig.post(
            "/runs/check-equipment",
            {
                **command,
                "inputs": saved["inputs"],
                "expected_revision": saved["revision"],
                "key": "check-updated-wiring",
            },
        )
        assert current_check["project"]["revision"] == saved["revision"]
        assert worker.run_once()
        updated_run = workspace.run(owner, current_check["run"]["id"])
        assert updated_run.state == "succeeded", updated_run.error
        updated_options = options.model_copy(
            update={"equipment_run_id": updated_run.id}
        )
        updated_source = json_object(
            report_sources(
                workspace, source, owner, workspace.get(owner, pid), updated_options
            )
        )
        assert updated_source["equipment"]["pv_electrical"] != wiring
        assert workspace.run(owner, checked.id).result == checked.result
        assert rig.post("/runs/check-equipment", command)["run"]["id"] == checked.id


@pytest.mark.parametrize(
    ("backup_output", "unit", "expected"),
    [
        (None, "kW", "unresolved"),
        (2, "kW", "violated"),
        (10, "kW", "satisfied"),
        (10, "kVA", "unresolved"),
    ],
)
def test_backup_load_and_hours_find_equipment_without_preparation(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    backup_output: float | None,
    unit: str,
    expected: str,
) -> None:
    from .test_private_http import Rig

    inverter = next(row for row in feed["products"] if row["id"] == 4107)
    if backup_output is not None:
        inverter["figures"]["backup_ac_active_power_kw"] = {
            "value": backup_output,
            "unit": unit,
            "citation": copy.deepcopy(
                inverter["figures"]["battery_voltage_range_v"]["citation"]
            ),
        }
    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    registry = service_registry(energy, None, equipment_search=search)
    worker = Worker(
        Jobs(workspace),
        "backup-demand-worker",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("backup-demand-project")
        declarations = {
            "backup_demand": {"schema_version": 1, "load_kw": 5, "duration_hours": 6},
            "equipment_setup": {"schema_version": 1, "grid_phase": 3},
        }
        command = {
            "project_id": pid,
            "expected_revision": 1,
            "inputs": declarations,
            "input_contract": "backup_demand_v1",
            "key": "compare-backup-systems",
        }
        reply = rig.post("/runs/find-equipment", command)
        assert reply["project"]["revision"] == 2
        assert reply["project"]["inputs"] == declarations
        assert rig.post("/runs/find-equipment", command) == reply
        assert rig.replay("/runs/find-equipment", command)["result"] == reply
        assert len(workspace.runs(owner, pid)) == 1
        assert worker.run_once()
        run = workspace.run(owner, reply["run"]["id"])
        assert run.state == "succeeded", run.error
        frozen = json_object(workspace.pinned_inputs(run.manifest))
        assert frozen["equipment_requirements"]["operating_mode"] == "backup"
        assert frozen["equipment_requirements"]["required_discharge_ac_kw"] == 5
        assert frozen["equipment_requirements"]["required_usable_kwh"] is None
        search_result = json_object(run.result)["search"]
        assert search_result["backup_demand"] == {
            **declarations["backup_demand"],
            "ac_load_energy_kwh": 30,
            "energy_basis": "ac_load_before_losses",
        }
        assert search_result["candidates"]
        assessed_batteries = 0
        for candidate in search_result["candidates"]:
            evidence = rig.post(
                "/equipment/candidates/read",
                {"run_id": run.id, "candidate_id": candidate["id"]},
            )["assessment"]
            checks = {row["id"]: row for row in evidence["checks"]}
            assert checks["backup_runtime"]["status"] in ("violated", "unresolved")
            assert (
                "starting_usable_energy_kwh"
                in checks["backup_runtime"]["missing_facts"]
            )
            assert (
                "documented_backup_discharge_losses"
                in checks["backup_runtime"]["missing_facts"]
            )
            if (
                candidate["selection"]["inverter_product_id"] == 4107
                and candidate["selection"]["battery_product_id"] is not None
            ):
                actual = checks["backup_runtime"]["actual"]
                assert actual["backup_active_output_kw"] == (
                    backup_output if unit == "kW" else None
                )
                if expected == "violated":
                    assert checks["backup_runtime"]["status"] == "violated"
                assert (
                    "battery_port_discharge_limits"
                    in checks["backup_runtime"]["missing_facts"]
                )
            assert evidence["provisional_bill_of_materials"]
            if candidate["selection"]["battery_product_id"] == 2090:
                assessed_batteries += 1
                energy = checks["usable_energy"]["actual"]
                if energy is not None and energy < 30:
                    assert checks["backup_runtime"]["status"] == "violated"
                assert checks["continuous_battery_ac_output"]["status"] != "satisfied"
        assert assessed_batteries > 0
        # Reading through a fresh workspace proves the run/receipt was durable.
        reopened = Workspace(workspace.blobs.directory.parent)
        assert reopened.run(owner, run.id).result == run.result
        assert workspace.get(owner, pid).revision == 2
        if backup_output is None:
            draft = rig.post(
                "/projects/create",
                {
                    "title": "Incomplete backup demand",
                    "inputs": {
                        "backup_demand": {
                            "schema_version": 1,
                            "load_kw": None,
                            "duration_hours": None,
                        },
                        "equipment_setup": {"schema_version": 1, "grid_phase": 3},
                    },
                    "input_contract": "backup_demand_v1",
                    "key": "backup-draft",
                },
            )
            incomplete_command = {
                **command,
                "schema_version": 1,
                "project_id": draft["id"],
                "inputs": draft["inputs"],
                "key": "incomplete-backup-compare",
            }
            incomplete = client.post(
                "/runs/find-equipment", json=incomplete_command, headers=headers(owner)
            )
            assert incomplete.status_code == 422
            assert incomplete.json()["error"]["fields"] == [
                "backup_demand.load_kw",
                "backup_demand.duration_hours",
            ]
            assert workspace.runs(owner, draft["id"]) == []
            assert (
                rig.replay("/runs/find-equipment", incomplete_command)["status"]
                == "absent"
            )
            assert workspace.get(owner, draft["id"]).revision == 1
            old_writer = client.post(
                "/projects/revise",
                json={
                    "schema_version": 1,
                    "project_id": draft["id"],
                    "expected_revision": 1,
                    "inputs": {},
                    "input_contract": "authored_equipment_discovery_v1",
                    "key": "old-backup-editor",
                },
                headers=headers(owner),
            )
            assert old_writer.status_code == 422
            assert (
                old_writer.json()["error"]["code"] == "project_input_contract_required"
            )


def test_plant_backup_and_preselected_models_reach_candidate_rpc(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .test_private_http import Rig

    inverter = next(row for row in feed["products"] if row["id"] == 4107)
    inverter["figures"]["backup_ac_active_power_kw"] = {
        "value": 4,
        "unit": "kW",
        "citation": copy.deepcopy(
            inverter["figures"]["battery_voltage_range_v"]["citation"]
        ),
    }
    battery = next(row for row in feed["products"] if row["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": 2,
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["modules_per_stack_max"]["citation"]
        ),
    }
    # Two separately cited synthetic battery options on the same converter.
    low_power = copy.deepcopy(battery)
    low_power.update(id=900001, sku="FIXTURE-BACKUP-ENERGY", model="BU2-5.0-HV5")
    citation = {
        "url": "https://de-linker.com/wp-content/uploads/fixtures/mixed-backup-fixture.pdf",
        "page": 1,
    }
    for key, value, unit in (
        ("module_energy_kwh_usable", 25, "kWh"),
        ("system_rated_dc_power_kw", 1, "kW"),
        ("stacks_parallel_max", 1, None),
    ):
        low_power["figures"][key] = {"value": value, "unit": unit, "citation": citation}
    feed["products"].append(low_power)
    _, source, loaded, _, _, _ = prepared_dc_fixture_source(feed, engine, monkeypatch)
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace,
            source,
            EquipmentSearchLimits(work_budget=1000),
        ),
        max_attempts=1,
    )
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(
        energy, None, equipment=equipment, equipment_search=search, reports=reports
    )
    worker = Worker(
        Jobs(workspace),
        "plant-backup-rpc",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment=equipment,
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)

        def run_equipment(
            label: str, authored: FixtureObject, path: str
        ) -> FixtureObject:
            pid = rig.create(label)
            result = rig.post(
                path,
                {
                    "project_id": pid,
                    "expected_revision": 1,
                    "inputs": authored,
                    "input_contract": "backup_demand_v1",
                    "key": "compare",
                },
            )
            assert worker.run_once()
            run = rig.post("/runs/read", {"run_id": result["run"]["id"]})
            assert run["state"] == "succeeded", run
            return run

        def find(label: str, authored: FixtureObject) -> tuple[str, FixtureObject]:
            run = run_equipment(label, authored, "/runs/find-equipment")
            return run["id"], run["result"]["search"]

        common = {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": None,
            "required_discharge_ac_kw": None,
        }
        selected = {
            **common,
            "inverter_product_id": 4107,
            "battery_product_id": 2090,
            "equipment_use": {"inverter": "replace", "battery": "new"},
        }
        _, single = find("explicit-models", {"equipment_setup": selected})
        assert single["candidates"]
        assert {
            (
                row["selection"]["inverter_product_id"],
                row["selection"]["battery_product_id"],
            )
            for row in single["candidates"]
        } == {(4107, 2090)}
        assert (
            len({row["selection"]["modules_per_stack"] for row in single["candidates"]})
            > 1
        )

        for n, load, duration, expected in (
            (2, 7, 6, "unresolved"),
            (2, 9, 2, "violated"),
            (6, 23, 3, "unresolved"),
            (12, 47, 10, "unresolved"),
        ):
            first_floor = None if load == 7 else 2
            authored: FixtureObject = {
                "backup_demand": {
                    "schema_version": 1,
                    "load_kw": load,
                    "duration_hours": duration,
                },
                "equipment_plant_setup": {
                    "schema_version": 1,
                    "requirements": {**common, "pv_dc_kw": n * 10},
                    "units": [
                        {
                            "id": f"u-{i}",
                            "name": f"Unit {i}",
                            "inputs": {
                                "equipment_setup": {
                                    **selected,
                                    "required_discharge_ac_kw": first_floor
                                    if i == 0
                                    else None,
                                },
                            },
                        }
                        for i in range(n)
                    ],
                    "parallel_groups": [],
                },
            }
            run_id, result = find(f"backup-plant-{n}-{load}", authored)
            assert result["backup_demand"]["load_kw"] == load
            candidates = result["candidates"]
            assert candidates, result["coverage"]
            candidate = next(
                (
                    c
                    for c in candidates
                    if c["status"] == expected
                    and (n != 12 or (c["usable_energy_kwh"] or 0) >= load * duration)
                ),
                None,
            )
            assert candidate is not None, result["coverage"]
            selections = [u["selection"] for u in candidate["plant"]["units"]]
            assert [x["required_discharge_ac_kw"] for x in selections] == [
                first_floor
            ] + [None] * (n - 1)
            assert {x["inverter_product_id"] for x in selections} == {4107}
            assert {x["battery_product_id"] for x in selections} == {2090}
            assert all(
                x["equipment_use"] == selected["equipment_use"] for x in selections
            )
            assessment = rig.post(
                "/equipment/candidates/read",
                {"run_id": run_id, "candidate_id": candidate["id"]},
            )["assessment"]
            checks = {row["id"]: row for row in assessment["checks"]}
            assert "unit:u-0:backup_runtime" not in checks
            check = checks["plant:backup_runtime"]
            assert check["status"] == expected
            assert check["required"]["ac_load_energy_kwh"] == load * duration
            assert check["actual"]["discharge_upper_bound_kw"] == n * 4
            assert (
                candidate["usable_energy_kwh"] == check["actual"]["usable_energy_kwh"]
            )
            if n == 2 and load == 7:
                plant = candidate["plant"]
                assert plant["requirements"]["required_discharge_ac_kw"] is None
                existing_run = rig.post("/runs/read", {"run_id": run_id})
                pid = existing_run["project_id"]
                saved = rig.post(
                    "/projects/revise",
                    {
                        "project_id": pid,
                        "expected_revision": existing_run["revision"],
                        "inputs": {
                            **authored,
                            "equipment_plant_setup": {
                                **authored["equipment_plant_setup"],
                                "requirements": {
                                    **authored["equipment_plant_setup"]["requirements"],
                                    "operating_mode": "backup",
                                },
                                "units": [
                                    {
                                        "id": u["id"],
                                        "name": u["name"],
                                        "inputs": {
                                            "equipment_setup": {
                                                k: v
                                                for k, v in u["selection"].items()
                                                if k != "product_revisions"
                                            }
                                        },
                                    }
                                    for u in plant["units"]
                                ],
                            },
                            "equipment_plant": plant,
                            "equipment_candidate": {
                                "run_id": run_id,
                                "candidate_id": candidate["id"],
                                "assessment_sha256": candidate["assessment_sha256"],
                            },
                        },
                        "input_contract": "backup_demand_v1",
                        "key": "adopt-backup-plant",
                    },
                )
                requested = rig.post(
                    "/runs/report",
                    {
                        "project_id": pid,
                        "expected_revision": saved["revision"],
                        "options": {
                            "locale": "en",
                            "energy_run_id": None,
                            "pv_run_id": None,
                            "equipment_run_id": None,
                            "logo": None,
                        },
                        "key": "report-backup-plant",
                    },
                )
                assert worker.run_once()
                completed = rig.post("/runs/read", {"run_id": requested["id"]})
                assert completed["state"] == "succeeded", completed
                result = completed["result"]
                report_source = json_object(
                    workspace.blobs.object(result["pinned_assets"]["report.source"])
                )
                assert report_source["equipment"] == assessment
                assert result["prepared_asset"]["media_type"] == "application/pdf"
                report = build_report(report_source)
                section = next(
                    s for s in report.sections if s.id == "plant-backup-runtime"
                )
                assert {row.label: row.value for row in section.rows}.items() >= {
                    "Backup load": "7 kW",
                    "Required duration": "6 h",
                    "Backup power upper bound": "8 kW",
                    "Backup load energy before losses": "42 kWh",
                }.items()
            if n == 12:
                assert check["actual"]["usable_energy_kwh"] >= load * duration

        grid_plant = copy.deepcopy(authored)
        grid_plant["backup_demand"].update(load_kw=21, duration_hours=1)
        grid_plant["equipment_plant_setup"]["requirements"]["pv_dc_kw"] = 20
        grid_units = grid_plant["equipment_plant_setup"]["units"][:2]
        grid_plant["equipment_plant_setup"]["units"] = grid_units
        for unit in grid_units:
            unit["inputs"]["equipment_setup"].update(
                modules_per_stack=4,
                parallel_stacks=1,
                accessory_product_ids=[2092],
                required_discharge_ac_kw=1,
            )
        checked = run_equipment(
            "grid-plant-backup", grid_plant, "/runs/check-equipment"
        )
        checks = {row["id"]: row for row in checked["result"]["assessment"]["checks"]}
        assert checks["unit:u-0:continuous_battery_ac_output"]["actual"] == 10
        backup = checks["plant:backup_runtime"]
        assert backup["actual"]["usable_energy_kwh"] == 36
        assert backup["actual"]["discharge_upper_bound_kw"] is None
        assert backup["status"] == "unresolved"

        companion = copy.deepcopy(grid_plant)
        companion["backup_demand"].update(load_kw=3, duration_hours=2)
        companion["equipment_plant_setup"]["units"][1]["inputs"] = {
            "equipment_setup": {**common, "inverter_product_id": 4107}
        }
        _, options = find("backup-with-solar-companion", companion)
        assert any(
            c["status"] == "unresolved"
            and c["plant"]["units"][0]["selection"]["battery_product_id"] == 2090
            and c["plant"]["units"][1]["selection"]["battery_product_id"] is None
            for c in options["candidates"]
        )

        mixed = copy.deepcopy(authored)
        mixed["backup_demand"].update(load_kw=35, duration_hours=20)
        for unit in mixed["equipment_plant_setup"]["units"]:
            unit["inputs"] = {
                "equipment_setup": {**common, "inverter_product_id": 4107}
            }
        run_id, options = find("backup-mixed-assemblies", mixed)
        assert options["completion"] == "budget_exhausted"
        candidate = next(
            (
                c
                for c in options["candidates"]
                if c["status"] == "unresolved" and (c["usable_energy_kwh"] or 0) >= 700
            ),
            None,
        )
        assert candidate is not None, options["coverage"]
        assert {
            u["selection"]["battery_product_id"] for u in candidate["plant"]["units"]
        } == {
            900001,
            2090,
        }
        assessment = rig.post(
            "/equipment/candidates/read",
            {"run_id": run_id, "candidate_id": candidate["id"]},
        )["assessment"]
        backup = next(
            c for c in assessment["checks"] if c["id"] == "plant:backup_runtime"
        )
        assert backup["actual"]["discharge_upper_bound_kw"] >= 35
        assert backup["status"] == "unresolved"


@pytest.mark.parametrize("retained_roof_export", [None, "permitted", "prohibited"])
def test_backup_candidate_reaches_report_and_bom_without_preparation(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    retained_roof_export: str | None,
) -> None:
    from .test_private_http import Rig, brief_inputs
    from .test_pvgis_roof_reference import fixture_inputs

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, equipment_search=search, reports=reports)
    worker = Worker(
        Jobs(workspace),
        "backup-report-worker",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("backup-report")
        authored: FixtureObject = {
            "backup_demand": {"schema_version": 1, "load_kw": 5, "duration_hours": 4},
            "equipment_setup": {"schema_version": 1, "grid_phase": 3},
        }
        if retained_roof_export is not None:
            authored.update(brief_inputs("Europe/Berlin"))
            authored["brief"]["system_scope"] = "storage_only"
            roof = fixture_inputs()["geometry"]
            roof["sources"][0]["permissions"]["export"] = retained_roof_export
            authored["geometry"] = roof
        found = rig.post(
            "/runs/find-equipment",
            {
                "project_id": pid,
                "expected_revision": 1,
                "inputs": authored,
                "input_contract": "backup_demand_v1",
                "key": "find-backup-report",
            },
        )
        assert worker.run_once()
        search_run = rig.post("/runs/read", {"run_id": found["run"]["id"]})
        assert search_run["state"] == "succeeded"
        candidate = next(
            row
            for row in search_run["result"]["search"]["candidates"]
            if row["selection"]["battery_product_id"] == 2090
            and row["selection"]["modules_per_stack"] == 5
        )
        detail = rig.post(
            "/equipment/candidates/read",
            {"run_id": search_run["id"], "candidate_id": candidate["id"]},
        )
        adoption = {
            **authored,
            "equipment_selection": candidate["selection"],
            "equipment_setup": {
                key: value
                for key, value in candidate["selection"].items()
                if key != "product_revisions"
            },
            "equipment_candidate": {
                "run_id": search_run["id"],
                "candidate_id": candidate["id"],
                "assessment_sha256": detail["assessment_sha256"],
            },
        }
        saved = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": found["project"]["revision"],
                "inputs": adoption,
                "input_contract": "backup_demand_v1",
                "key": "select-backup-report",
            },
        )
        report_command = {
            "project_id": pid,
            "expected_revision": saved["revision"],
            "options": {
                "locale": "en",
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
            },
            "key": "backup-candidate-report",
        }
        queued = rig.post("/runs/report", report_command)
        assert worker.run_once()
        completed = rig.post("/runs/read", {"run_id": queued["id"]})
        assert completed["state"] == "succeeded", completed
        result = completed["result"]
        report_source = json_object(
            workspace.blobs.object(result["pinned_assets"]["report.source"])
        )
        assert report_source["pv_components"] is None
        assert "equipment_pv" not in report_source["woo_bases"]
        assert report_source["equipment"] == detail["assessment"]
        assert any(
            row.get("candidate_id") == candidate["id"]
            and row["run_id"] == search_run["id"]
            for row in report_source["source_runs"]
        )
        runtime = next(
            row
            for row in report_source["equipment"]["checks"]
            if row["id"] == "backup_runtime"
        )
        assert runtime["required"]["ac_load_energy_kwh"] == 20
        assert runtime["status"] == "unresolved"
        for asset, media in (
            (result["prepared_asset"], "application/pdf"),
            (result["prepared_attachments"]["bill_of_materials_csv"], "text/csv"),
        ):
            response = client.post(
                "/assets/content",
                json={"schema_version": 1, "project_id": pid, "asset_id": asset["id"]},
                headers=headers(owner),
            )
            assert response.status_code == 200
            assert response.content
            if media == "application/pdf":
                assert response.content.startswith(b"%PDF")
            else:
                assert b"BU2" in response.content
        assert rig.post("/runs/report", report_command)["id"] == queued["id"]
        changed = copy.deepcopy(adoption)
        changed["backup_demand"]["duration_hours"] = 8
        changed_project = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": saved["revision"],
                "inputs": changed,
                "input_contract": "backup_demand_v1",
                "key": "changed-backup-duration",
            },
        )
        stale_report = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                **report_command,
                "expected_revision": changed_project["revision"],
                "key": "stale-backup-report",
            },
            headers=headers(owner),
        )
        assert stale_report.status_code == 422
        assert stale_report.json()["error"]["code"] == "report_inputs_changed"


@pytest.mark.parametrize(
    ("external_pv", "declared_module", "export"),
    [
        (False, False, "permitted"),
        (True, False, "permitted"),
        (True, True, "permitted"),
        (True, False, "prohibited"),
        (True, True, "unknown"),
    ],
)
def test_roof_layout_changes_refuse_a_new_report_and_keep_the_old_pdf(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    external_pv: bool,
    declared_module: bool,
    export: str,
) -> None:
    from linker_engine.planning.assets import Assets
    from linker_engine.planning.profile_import import ProfileImport

    from .test_energy_kernel import PROVENANCE, mapping
    from .test_private_http import Rig, authored_energy
    from .test_pvgis_roof_reference import prepared_reference_fixture

    _, source, loaded, _, _, _ = prepared_dc_fixture_source(feed, engine, monkeypatch)
    project, pv = prepared_reference_fixture(workspace, owner, source)
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000), max_intervals=10
        ),
        max_attempts=1,
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, equipment_search=search, reports=reports)
    worker = Worker(
        Jobs(workspace),
        "roof-report",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    with TestClient(app) as client:
        rig = Rig(workspace, ac, client)
        authored = {**project.inputs, **authored_energy(rig, project.id)}
        authored["geometry"]["sources"][0]["permissions"]["export"] = export
        if declared_module:
            from .test_declared_reference_end_to_end import _declared_roof

            authored["geometry"]["module_specs"] = _declared_roof()[0]["module_specs"]
        profiles = ProfileImport(Assets(workspace))
        load = profiles.csv(
            owner,
            project.id,
            b"time,power\n2020-01-01T00:00:00Z,2\n2020-01-01T01:00:00Z,2\n",
            mapping("gross_load"),
            PROVENANCE,
            key="roof-load",
        )
        if external_pv:
            pv = profiles.csv(
                owner,
                project.id,
                b"time,power\n2020-01-01T00:00:00Z,0\n2020-01-01T01:00:00Z,1\n",
                mapping("pv_available_ac"),
                PROVENANCE,
                key="external-pv",
            )
        authored["profile_selections"]["selected"] = {
            "gross_load": load.id,
            "pv_available_ac": pv.id,
        }
        scenario = authored["energy_scenario"]
        scenario["controller"] = "self_consumption_with_reserve_v1"
        scenario["schedule"][0].update(
            start_utc="2020-01-01T00:00:00Z", end_utc="2020-01-01T02:00:00Z"
        )
        authored["equipment_setup"] = {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 9.2,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        }
        command = {
            "project_id": project.id,
            "expected_revision": project.revision,
            "input_contract": "known_pv_ac_reference_v1",
        }
        found = rig.post(
            "/runs/find-equipment", {**command, "inputs": authored, "key": "find-roof"}
        )
        assert worker.run_once()
        run = rig.post("/runs/read", {"run_id": found["run"]["id"]})
        assert run["state"] == "succeeded", run
        assert (
            run["manifest"]["context"]["assets"]["pv_available_ac.raw"]
            == pv.content_sha256
        )
        candidate = run["result"]["search"]["candidates"][0]
        adopted = {
            **found["project"]["inputs"],
            "equipment_selection": candidate["selection"],
            "equipment_candidate": {
                "run_id": run["id"],
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        }
        saved = rig.post(
            "/projects/revise",
            {
                **command,
                "expected_revision": found["project"]["revision"],
                "inputs": adopted,
                "key": "adopt-roof",
            },
        )
        report_command = {
            "project_id": project.id,
            "options": {
                "locale": "en",
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
            },
        }
        if export != "permitted":
            refused = client.post(
                "/runs/report",
                json={
                    "schema_version": 1,
                    **report_command,
                    "expected_revision": saved["revision"],
                    "key": "restricted-roof-export",
                },
                headers=headers(owner),
            )
            assert refused.status_code == 422, refused.text
            assert refused.json()["error"]["code"] == "report_source_export_required"
            return
        report = rig.post(
            "/runs/report",
            {
                **report_command,
                "expected_revision": saved["revision"],
                "key": "roof-report",
            },
        )
        assert worker.run_once()
        finished = rig.post("/runs/read", {"run_id": report["id"]})
        assert finished["state"] == "succeeded", finished
        frozen_report = json_object(
            workspace.blobs.object(finished["result"]["pinned_assets"]["report.source"])
        )
        parts = frozen_report["pv_components"]
        assert parts["status"] == "available"
        assert parts["components"][0]["quantity"] == 20
        assert "equipment_pv" not in frozen_report["woo_bases"]
        changed = copy.deepcopy(adopted)
        changed["geometry"]["arrays"][0]["mount_tilt_deg"] = 12
        revised = rig.post(
            "/projects/revise",
            {
                **command,
                "expected_revision": saved["revision"],
                "inputs": changed,
                "key": "change-roof-tilt",
            },
        )
        stale = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                **report_command,
                "expected_revision": revised["revision"],
                "key": "stale-roof-report",
            },
            headers=headers(owner),
        )
        assert stale.status_code == 422, stale.text
        assert stale.json()["error"]["code"] == "report_inputs_changed"
        assert (
            rig.post("/runs/read", {"run_id": report["id"]})["result"]
            == finished["result"]
        )
        pdf = client.post(
            "/assets/content",
            json={
                "schema_version": 1,
                "project_id": project.id,
                "asset_id": finished["result"]["prepared_asset"]["id"],
            },
            headers=headers(owner),
        )
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_find_equipment_compiles_unsaved_demand_and_reaches_adoption_report(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .test_private_http import Rig, authored_energy

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000), max_intervals=10
        ),
        max_attempts=1,
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, equipment_search=search, reports=reports)
    worker = Worker(
        Jobs(workspace),
        "current-search-worker",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("current-search")
        declarations = authored_energy(rig, pid)
        declarations["equipment_setup"] = {
            "schema_version": 1,
            "inverter_product_id": None,
            "battery_product_id": None,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        }
        # Only application is authored in this legacy document. Its obsolete
        # shared fields must not replace the currently edited demand.
        declarations["equipment_requirements"] = {
            "schema_version": 1,
            "grid_phase": 1,
            "operating_mode": "backup",
            "pv_dc_kw": 1,
            "required_usable_kwh": 999,
            "required_discharge_ac_kw": 999,
            "application": "residential",
        }
        command = {
            "schema_version": 1,
            "project_id": pid,
            "expected_revision": 1,
            "inputs": declarations,
            "input_contract": "authored_equipment_discovery_v1",
            "key": "root-command",
        }
        declarations["equipment_setup"]["grid_phase"] = None
        invalid = client.post(
            "/runs/find-equipment", json=command, headers=headers(owner)
        )
        assert invalid.status_code == 422, invalid.text
        assert invalid.json()["error"]["fields"] == ["equipment_setup.grid_phase"]
        assert workspace.get(owner, pid).revision == 1
        declarations["equipment_setup"]["grid_phase"] = 3
        existing = {
            "schema_version": 1,
            "name": "West barn inverter",
            "inverter_power_kw": 7.5,
            "keep_inverter": True,
        }
        declarations["existing_system"] = existing
        command["input_contract"] = "existing_system_v1"
        minimal_project = rig.create("retain-name-and-power-only")
        minimal = rig.post(
            "/runs/find-equipment",
            {
                **command,
                "project_id": minimal_project,
                "key": "minimal-retention",
                "inputs": {"existing_system": existing},
            },
        )
        assert worker.run_once()
        minimal_run = workspace.run(owner, str(minimal["run"]["id"]))
        assert minimal_run.state == "succeeded", minimal_run.error
        minimal_demand = json_object(minimal_run.result)["retained_inverter"][
            "requirements"
        ]
        assert minimal_demand["grid_phase"] is None
        assert minimal_demand["operating_mode"] is None
        partial_project = rig.create("retain-unknown")
        partial_inputs = {
            **authored_energy(rig, partial_project),
            "equipment_setup": declarations["equipment_setup"],
            "existing_system": existing,
        }
        partial_inputs["energy_scenario"]["controller"] = (
            "self_consumption_with_reserve_v1"
        )
        partial_command = {
            **command,
            "project_id": partial_project,
            "inputs": partial_inputs,
        }
        partial = rig.post("/runs/find-equipment", partial_command)
        assert worker.run_once()
        run = workspace.run(owner, str(partial["run"]["id"]))
        assert run.state == "succeeded", run.error
        partial_result = json_object(run.result)
        assert "search" not in partial_result
        assert partial_result["retained_inverter"]["existing_system"] == existing
        assert (
            partial_result["retained_inverter"]["requirements"]["required_usable_kwh"]
            == 15
        )
        baseline = partial_result["retained_inverter"]["profile_baseline"]
        assert baseline["baseline"]["load_kwh"] == 4
        assert baseline["baseline"]["pv_available_kwh"] == 4
        assert baseline["baseline"]["direct_pv_use_kwh"] == 2
        assert baseline["baseline"]["grid_import_kwh"] == 2
        assert baseline["baseline"]["peak_grid_import_kw"] == 2
        missing_candidate = client.post(
            "/equipment/candidates/read",
            json={"schema_version": 1, "run_id": run.id, "candidate_id": "a" * 64},
            headers=headers(owner),
        )
        assert missing_candidate.status_code == 404, missing_candidate.text
        partial_report = rig.post(
            "/runs/report",
            {
                "project_id": partial_project,
                "expected_revision": partial["project"]["revision"],
                "options": {
                    "locale": "en",
                    "energy_run_id": None,
                    "pv_run_id": None,
                    "equipment_run_id": run.id,
                    "logo": None,
                },
                "key": "partial-report",
            },
        )
        assert worker.run_once()
        report_run = workspace.run(owner, str(partial_report["id"]))
        assert report_run.state == "succeeded", report_run.error
        sections = {
            section["id"]: section
            for section in json_object(report_run.result)["report"]["sections"]
        }
        assert "7.5 kW" in {row["value"] for row in sections["existing-system"]["rows"]}
        assert any(
            "model" in text for text in sections["existing-system"]["paragraphs"]
        )
        assert any(
            "West barn inverter" in row for row in sections["bom"]["table"]["rows"]
        )
        assert "4 kWh" in {
            row["value"] for row in sections["retained-energy-baseline"]["rows"]
        }
        assert any("Battery" in row for row in sections["bom"]["table"]["rows"])
        handoff = rig.post(
            "/handoffs/prepare",
            {
                "project_id": partial_project,
                "expected_revision": report_run.revision,
                "report_run_id": report_run.id,
                "key": "partial-handoff",
            },
        )
        assert handoff["snapshot"]["items"] == []
        assert handoff["snapshot"]["kind"] == "planning_report_only_v1"
        assert rig.post("/handoffs/read", {"handoff_id": handoff["id"]}) == handoff
        assert json_object(report_run.result)["has_report_only_handoff"] is True
        assert json_object(report_run.result)["has_draft_items"] is False
        declarations["existing_system"] = {**existing, "keep_inverter": False}
        with workspace.database.transaction() as connection:
            connection.execute(
                "CREATE TRIGGER fail_discovery_queue BEFORE INSERT ON jobs BEGIN SELECT RAISE(ABORT, 'queue unavailable'); END"
            )
        failed = client.post(
            "/runs/find-equipment", json=command, headers=headers(owner)
        )
        assert failed.status_code == 500
        assert workspace.get(owner, pid).revision == 1
        assert workspace.runs(owner, pid) == []
        assert rig.replay("/runs/find-equipment", command)["status"] == "absent"
        with workspace.database.transaction() as connection:
            connection.execute("DROP TRIGGER fail_discovery_queue")
        reply = rig.post("/runs/find-equipment", command)
        assert reply["project"]["revision"] == 2
        assert (
            reply["project"]["inputs"]["existing_system"]["name"]
            == "West barn inverter"
        )
        old_writer = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": 2,
                "inputs": {},
                "input_contract": "authored_equipment_discovery_v1",
                "key": "old-editor",
            },
            headers=headers(owner),
        )
        assert old_writer.status_code == 422
        assert old_writer.json()["error"]["code"] == "project_input_contract_required"
        assert "equipment_requirements" not in reply["project"]["inputs"]
        assert (
            reply["project"]["inputs"]["equipment_setup"]["application"]
            == "residential"
        )
        assert rig.post("/runs/find-equipment", command) == reply
        assert rig.replay("/runs/find-equipment", command)["result"] == reply
        assert rig.replay("/runs/calculate", command)["status"] == "absent"
        assert worker.run_once()
        found = workspace.run(owner, str(reply["run"]["id"]))
        assert found.state == "succeeded", found.error
        frozen = json_object(workspace.pinned_inputs(found.manifest))
        assert frozen["equipment_requirements"]["required_usable_kwh"] == 15
        assert frozen["equipment_requirements"]["grid_phase"] == 3
        assert frozen["equipment_requirements"]["application"] == "residential"
        candidate = next(
            c
            for c in json_object(found.result)["search"]["candidates"]
            if c["status"] == "satisfied"
        )
        selected = candidate["selection"]
        adoption = {
            **reply["project"]["inputs"],
            "equipment_selection": selected,
            "equipment_setup": {
                **{k: v for k, v in selected.items() if k != "product_revisions"},
                "application": reply["project"]["inputs"]["equipment_setup"][
                    "application"
                ],
            },
            "equipment_candidate": {
                "run_id": found.id,
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        }
        saved = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": 2,
                "inputs": adoption,
                "input_contract": "existing_system_v1",
                "key": "adopt-current-search",
            },
        )
        comparison = rig.post(
            "/runs/find-equipment",
            {
                **command,
                "expected_revision": saved["revision"],
                "inputs": saved["inputs"],
                "input_contract": "existing_system_v1",
                "key": "compare-after-legacy-adoption",
            },
        )
        assert (
            comparison["project"]["inputs"]["equipment_candidate"]
            == adoption["equipment_candidate"]
        )
        assert worker.run_once()
        compared = rig.post("/runs/read", {"run_id": comparison["run"]["id"]})
        assert compared["state"] == "succeeded", compared
        assert {row["id"] for row in compared["result"]["search"]["candidates"]} == {
            row["id"] for row in json_object(found.result)["search"]["candidates"]
        }
        saved = comparison["project"]
        report = rig.post(
            "/runs/report",
            {
                "project_id": pid,
                "expected_revision": saved["revision"],
                "options": {
                    "locale": "en",
                    "energy_run_id": None,
                    "pv_run_id": None,
                    "equipment_run_id": None,
                    "logo": None,
                },
                "key": "current-search-report",
            },
        )
        assert worker.run_once()
        completed = workspace.run(owner, str(report["id"]))
        assert completed.state == "succeeded", completed.error
        result = json_object(completed.result)
        assert result["prepared_asset"]["content_sha256"]
        section = next(
            section
            for section in result["report"]["sections"]
            if section["id"] == "existing-system"
        )
        assert {row["value"] for row in section["rows"]} == {
            "West barn inverter",
            "7.5 kW",
        }
        bom = next(
            section
            for section in result["report"]["sections"]
            if section["id"] == "bom"
        )
        assert any("West barn inverter" in row for row in bom["table"]["rows"])
        materials = json_object(
            workspace.blobs.object(result["pinned_assets"]["report.source"])
        )["materials"]
        assert (
            next(
                line for line in materials["lines"] if line["id"] == "existing-system"
            )["handling"]
            == "existing_system_declared"
        )
        calculated = rig.post(
            "/runs/calculate",
            {**command, "inputs": adoption, "expected_revision": saved["revision"]},
        )
        assert calculated["run"]["id"] != found.id
        assert rig.post("/runs/find-equipment", command)["run"]["id"] == found.id
        retention_edit = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": saved["revision"],
                "inputs": {**adoption, "existing_system": existing},
                "input_contract": "existing_system_v1",
                "key": "keep-existing-after-adoption",
            },
        )
        stale = client.post(
            "/runs/report",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": retention_edit["revision"],
                "options": {
                    "locale": "en",
                    "energy_run_id": None,
                    "pv_run_id": None,
                    "equipment_run_id": None,
                    "logo": None,
                },
                "key": "stale-retention-report",
            },
            headers=headers(owner),
        )
        assert stale.status_code == 422, stale.text
        assert stale.json()["error"]["fields"] == ["existing_system.keep_inverter"]


@pytest.mark.parametrize(
    ("fraction", "target", "interval_budget", "outage"),
    [
        (1.0, 0, 10000, False),
        (0.0, 0, 10000, False),
        (0.0, 4, 10000, False),
        (1.0, 0, 2, False),
        (1.0, 0, 10000, True),
    ],
)
def test_find_equipment_replays_frozen_candidate_demand_through_rpc(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    fraction: float,
    target: float,
    interval_budget: int,
    outage: bool,
) -> None:
    from .test_private_http import Rig, authored_energy

    battery = next(p for p in feed["products"] if p["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": "2",
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["module_energy_kwh_usable"]["citation"]
        ),
    }
    _, source, loaded, _, _, _ = prepared_dc_fixture_source(feed, engine, monkeypatch)
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace,
            source,
            EquipmentSearchLimits(
                work_budget=1000, demand_interval_budget=interval_budget
            ),
            tolerance=TOLERANCE,
            max_intervals=10,
        ),
        max_attempts=1,
    )
    registry = service_registry(energy, None, equipment_search=search)
    worker = Worker(
        Jobs(workspace),
        "demand-worker",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("demand-search")
        declarations = authored_energy(rig, pid)
        declarations["equipment_setup"] = {
            "schema_version": 1,
            "inverter_product_id": None,
            "battery_product_id": None,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 0,
            "required_usable_kwh": 0,
            "required_discharge_ac_kw": 0,
        }
        declarations["equipment_demand"] = {
            "schema_version": 1,
            "initial_usable_fraction": fraction,
            "source_note": "Customer declares fraction of each usable window",
            "max_unserved_load_kwh": target,
        }
        scenario = declarations["energy_scenario"]
        scenario["battery"]["usable_window_kwh"] = None
        scenario["controller"] = "peak_shaving_with_reserve_v1"
        scenario["schedule"][0].update(
            pv_enabled=False,
            import_policy="limited",
            import_cap_kw=0,
        )
        if outage:
            from linker_engine.planning.assets import Assets
            from linker_engine.planning.profile_import import ProfileImport

            from .test_energy_kernel import PROVENANCE, mapping

            critical = ProfileImport(Assets(workspace)).csv(
                owner,
                pid,
                b"time,power\n2024-03-30T23:00:00Z,2\n2024-03-31T00:00:00Z,2\n",
                mapping("critical_load"),
                PROVENANCE,
                key="critical-only",
            )
            selected = declarations["profile_selections"]["selected"]
            selected["critical_load"] = critical.id
            del selected["gross_load"]
            scenario["schedule"][0]["mode"] = "outage"
        command = {
            "schema_version": 1,
            "project_id": pid,
            "expected_revision": 1,
            "inputs": declarations,
            "input_contract": "authored_equipment_discovery_v1",
            "key": "candidate-demand",
        }
        reply = rig.post("/runs/find-equipment", command)
        # Later authored choices must not change the queued candidate replay.
        altered = copy.deepcopy(reply["project"]["inputs"])
        altered["energy_scenario"]["schedule"][0]["import_cap_kw"] = 999
        altered["equipment_demand"]["initial_usable_fraction"] = 0
        rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": 2,
                "inputs": altered,
                "input_contract": "authored_equipment_discovery_v1",
                "key": "later-demand-edit",
            },
        )
        assert worker.run_once()
        completed = workspace.run(owner, str(reply["run"]["id"]))
        assert completed.state == "succeeded", completed.error
        result = json_object(completed.result)
        demand = result["search"]["demand"]
        assert demand["model"] == "single_ac_equipment_demand_v1"
        assert demand["interval_count"] == 2
        candidates = result["search"]["candidates"]
        assert any(c["selection"]["parallel_stacks"] == 2 for c in candidates)
        for candidate in candidates:
            detail = rig.post(
                "/equipment/candidates/read",
                {
                    "schema_version": 1,
                    "run_id": completed.id,
                    "candidate_id": candidate["id"],
                },
            )
            assert detail["assessment"]["overall_status"] == candidate["status"]
        replayed = [c for c in candidates if c["demand"]["metrics"] is not None]
        assert replayed
        for candidate in replayed:
            outcome = candidate["demand"]
            assert outcome["metrics"]["load_demand_kwh"] == 4
            assert outcome["metrics"]["stored_initial"][
                "initial_unknown_kwh"
            ] == pytest.approx(candidate["usable_energy_kwh"] * fraction)
            assert outcome["metrics"]["solar_load_kwh"] == 0
            assert (
                outcome["equipment"]["performance_status"]
                == "not_established_by_scenario_envelope"
            )
        if fraction == 0:
            assert all(
                c["demand"]["metrics"]["unserved_load_kwh"] == 4 for c in replayed
            )
            assert all(
                c["demand"]["status"] == ("satisfied" if target == 4 else "violated")
                for c in replayed
            )
        else:
            assert any(c["demand"]["status"] == "satisfied" for c in replayed)
        assert demand["completion"] == (
            "budget_exhausted" if interval_budget == 2 else "complete"
        )
        distinct = {c["usable_energy_kwh"] for c in replayed}
        assert demand["work_used"] == len(distinct) * 2
        if interval_budget == 2:
            assert len(replayed) > 1
            assert len({c["selection"]["inverter_product_id"] for c in replayed}) > 1
            assert len(distinct) == 1
        for candidate in replayed:
            assert (
                candidate["demand"]["equipment"]["selection"] == candidate["selection"]
            )
        if interval_budget == 2:
            assert (
                sum(
                    c["demand"]["reason"] == "work_budget_exhausted" for c in candidates
                )
                > 0
            )
        assert any(
            c["usable_energy_kwh"] is None
            and c["demand"]["reason"] == "usable_energy_not_established"
            for c in candidates
        )
        pinned = result["pinned_assets"]
        assert all(
            ("critical_load." if outage else "gross_load.") + suffix in pinned
            for suffix in ("raw", "metadata", "timezone")
        )
        critical_missing = copy.deepcopy(altered)
        critical_missing["profile_selections"]["selected"].pop("critical_load", None)
        critical_missing["energy_scenario"]["schedule"][0]["mode"] = "outage"
        missing_reply = rig.client.post(
            "/runs/find-equipment",
            json={
                **command,
                "expected_revision": 3,
                "inputs": critical_missing,
                "key": "missing-critical",
            },
            headers=headers(owner),
        )
        assert missing_reply.status_code == 422, missing_reply.text
        assert workspace.get(owner, pid).revision == 3
        for invalid_demand in (
            {**altered["equipment_demand"], "initial_usable_fraction": 1.1},
            {
                key: value
                for key, value in altered["equipment_demand"].items()
                if key != "max_unserved_load_kwh"
            },
        ):
            invalid = rig.client.post(
                "/runs/find-equipment",
                json={
                    **command,
                    "expected_revision": 3,
                    "inputs": {**altered, "equipment_demand": invalid_demand},
                    "key": "invalid-demand",
                },
                headers=headers(owner),
            )
            assert invalid.status_code == 422, invalid.text
            expected_field = (
                "equipment_demand.initial_usable_fraction"
                if "max_unserved_load_kwh" in invalid_demand
                else "equipment_demand.max_unserved_load_kwh"
            )
            assert invalid.json()["error"]["fields"] == [expected_field]
            assert workspace.get(owner, pid).revision == 3
        assert rig.post("/runs/find-equipment", command)["run"]["id"] == completed.id
        if fraction == 1 and interval_budget == 10000 and not outage:
            impossible = copy.deepcopy(altered)
            impossible["energy_scenario"].update(
                terminal_policy="minimum", terminal_min_kwh=1000000
            )
            failed = rig.post(
                "/runs/find-equipment",
                {
                    **command,
                    "expected_revision": 3,
                    "inputs": impossible,
                    "key": "impossible-terminal",
                },
            )
            assert worker.run_once()
            failed_result = json_object(
                workspace.run(owner, str(failed["run"]["id"])).result
            )
            assessed = [
                c["demand"]
                for c in failed_result["search"]["candidates"]
                if c["demand"]["metrics"] is not None
            ]
            assert assessed and all(
                c["status"] == "violated" and c["reason"] == "scenario_not_feasible"
                for c in assessed
            )


def test_find_equipment_per_unit_application_reaches_candidate_adoption(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .test_private_http import Rig

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(energy, None, equipment_search=search, reports=reports)
    worker = Worker(
        Jobs(workspace),
        "unit-application-search",
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
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    setup = {
        key: value
        for key, value in inputs(feed, 3)["equipment_selection"].items()
        if key != "product_revisions"
    }
    authored: FixtureObject = {
        "brief": {**incomplete_brief(), "project_use": "residential"},
        "equipment_plant_setup": {
            "schema_version": 1,
            "requirements": {
                key: value
                for key, value in setup.items()
                if key in EquipmentRequirements.model_fields
            },
            "units": [
                {
                    "id": uid,
                    "name": uid.upper(),
                    "inputs": {
                        "equipment_setup": {
                            **setup,
                            **({"application": "residential"} if uid == "a" else {}),
                        }
                    },
                }
                for uid in ("a", "b")
            ],
            "parallel_groups": [
                {
                    "id": "shared",
                    "unit_ids": ["a", "b"],
                    "controller_product_id": 2409,
                    "control_network": "lan",
                    "controller_use": "retain",
                }
            ],
        },
    }
    authored["equipment_plant_setup"]["requirements"].update(
        pv_dc_kw=20, required_usable_kwh=20, required_discharge_ac_kw=10
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("unit-application")
        reply = rig.post(
            "/runs/find-equipment",
            {
                "project_id": pid,
                "expected_revision": 1,
                "inputs": authored,
                "input_contract": "authored_equipment_discovery_v1",
                "key": "unit-search",
            },
        )
        assert worker.run_once()
        run = workspace.run(owner, str(reply["run"]["id"]))
        assert run.state == "succeeded", run.error
        frozen = rig.post("/runs/inputs", {"project_id": pid, "run_id": run.id})[
            "inputs"
        ]
        assert (
            frozen["equipment_plant_requirements"]["units"][1]["requirements"][
                "application"
            ]
            == "residential"
        )
        candidates = json_object(run.result)["search"]["candidates"]
        assert candidates, run.result
        candidate = candidates[0]
        selected = candidate["plant"]
        assert selected["parallel_groups"][0]["controller_use"] == "retain"
        current = reply["project"]["inputs"]
        current["equipment_plant"] = selected
        for declaration, unit in zip(
            current["equipment_plant_setup"]["units"], selected["units"], strict=True
        ):
            declared_setup = declaration["inputs"]["equipment_setup"]
            declared_setup.update(
                {k: v for k, v in unit["selection"].items() if k != "product_revisions"}
            )
        current["equipment_candidate"] = {
            "run_id": run.id,
            "candidate_id": candidate["id"],
            "assessment_sha256": candidate["assessment_sha256"],
        }
        adopted = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": 2,
                "inputs": current,
                "input_contract": "authored_equipment_discovery_v1",
                "key": "adopt-unit-application",
            },
        )
        assert adopted["revision"] == 3
        options = ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=None,
            logo=None,
        )
        project = workspace.get(owner, pid)
        assert report_sources(workspace, source, owner, project, options)["candidate"]
        changed = copy.deepcopy(current)
        unit = changed["equipment_plant_setup"]["units"][0]["inputs"]["equipment_setup"]
        unit["comparison_models"] = {
            "inverter_product_id": None,
            "battery_product_id": None,
        }
        revised = rig.post(
            "/projects/revise",
            {
                "project_id": pid,
                "expected_revision": 3,
                "inputs": changed,
                "input_contract": "authored_equipment_discovery_v1",
                "key": "change-unit-model-preferences",
            },
        )
        assert revised["revision"] == 4
        with pytest.raises(ReportInputsChanged):
            report_sources(workspace, source, owner, workspace.get(owner, pid), options)


@pytest.mark.parametrize("shape", ["single", "plant", "legacy"])
@pytest.mark.parametrize("system_scope", ["new_pv_storage", "storage_only"])
def test_find_equipment_preserves_unknown_single_and_unit_sizing(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    shape: str,
    system_scope: str,
) -> None:
    from .test_private_http import Rig, brief_inputs

    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=10, products=source)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    app = create_private_app(
        workspace,
        EnergyService(workspace, ac, max_attempts=1),
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        product_provider=lambda: loaded,
    )
    setup: FixtureObject = {
        "schema_version": 1,
        "inverter_product_id": None,
        "battery_product_id": None,
        "modules_per_stack": None,
        "parallel_stacks": None,
        "accessory_product_ids": [],
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": None,
        "required_usable_kwh": None,
        "required_discharge_ac_kw": None,
    }
    authored = brief_inputs("Europe/Berlin")
    authored["brief"]["system_scope"] = system_scope
    if shape == "plant":
        authored["equipment_plant_setup"] = {
            "schema_version": 1,
            "requirements": {
                key: value
                for key, value in setup.items()
                if key in EquipmentRequirements.model_fields
            },
            "units": [
                {
                    "id": "a",
                    "name": "A",
                    "inputs": {
                        "equipment_setup": {
                            **setup,
                            "grid_phase": None,
                            "operating_mode": None,
                        },
                        "equipment_requirements": {"application": "residential"},
                    },
                }
            ],
            "parallel_groups": [],
        }
    elif shape == "legacy":
        authored["equipment_requirements"] = {
            key: value
            for key, value in setup.items()
            if key in EquipmentRequirements.model_fields
        }
        authored["equipment_requirements"]["application"] = "commercial"
    else:
        authored["equipment_setup"] = {**setup, "application": None}
        authored["equipment_requirements"] = {"application": "commercial"}
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        pid = rig.create("unknown-demand")
        response = rig.post(
            "/runs/find-equipment",
            {
                "project_id": pid,
                "expected_revision": 1,
                "inputs": authored,
                "input_contract": "authored_equipment_discovery_v1",
                "key": "unknown-search",
            },
        )
        run = workspace.run(owner, str(response["run"]["id"]))
        frozen = json_object(workspace.pinned_inputs(run.manifest))
        if shape == "plant":
            demand = frozen["equipment_plant_requirements"]["units"][0]["requirements"]
            assert (
                demand["grid_phase"] == 3
                and demand["operating_mode"] == "grid_connected"
            )
            assert demand["application"] == "residential"
            assert "equipment_plant_requirements" not in response["project"]["inputs"]
            unit_authored = response["project"]["inputs"]["equipment_plant_setup"][
                "units"
            ][0]["inputs"]
            assert unit_authored["equipment_setup"]["grid_phase"] is None
            assert "equipment_requirements" not in unit_authored
        else:
            demand = frozen["equipment_requirements"]
            assert "equipment_requirements" not in response["project"]["inputs"]
        assert demand["application"] == (
            "residential"
            if shape == "plant"
            else "commercial"
            if shape == "legacy"
            else None
        )
        assert demand["pv_dc_kw"] == (0 if system_scope == "storage_only" else None)
        assert demand["required_usable_kwh"] is None
        assert demand["required_discharge_ac_kw"] is None
        project_inputs = response["project"]["inputs"]
        saved_setup = (
            project_inputs["equipment_plant_setup"]["units"][0]["inputs"][
                "equipment_setup"
            ]
            if shape == "plant"
            else project_inputs["equipment_setup"]
        )
        assert saved_setup["pv_dc_kw"] is None
        assert saved_setup["required_usable_kwh"] is None
        assert saved_setup["required_discharge_ac_kw"] is None
        if shape == "plant":
            assert (
                project_inputs["equipment_plant_setup"]["requirements"]["pv_dc_kw"]
                is None
            )
            assert frozen["equipment_plant_setup"]["requirements"]["pv_dc_kw"] is None
            assert saved_setup["operating_mode"] is None


@pytest.mark.parametrize(
    ("source_kind", "equipment_use"),
    [
        ("equipment_selection", None),
        ("equipment_setup", {"inverter": "retain", "battery": "replace"}),
        ("equipment_selection", {"inverter": "new", "battery": "retain"}),
        ("equipment_setup", {"inverter": "replace", "battery": "new"}),
    ],
)
def test_report_from_an_adopted_candidate_needs_no_second_equipment_run(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    equipment_use: FixtureObject | None,
) -> None:
    """The one-screen quick start reaches its PDF, production walk 2026-11-11 §B.

    That screen adopts the chosen combination as the project's candidate and
    then asked for the report with the qualification run named as well. The
    report's own contract reads an adopted candidate as the project's single
    equipment source, so the extra run is refused and the customer got 422 with
    no PDF. This pins both halves: the screen's actual options produce a
    complete report source, and naming a second run stays refused.
    """
    from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS

    declared = inputs(feed, 4 if equipment_use is not None else 3)[
        "equipment_selection"
    ]
    declared["required_usable_kwh"] = 15
    if equipment_use is not None:
        declared["equipment_use"] = equipment_use
        feed["products"] = [
            p for p in feed["products"] if p["id"] in (4107, 2063, 2090, 2092)
        ]
    if source_kind == "equipment_setup":
        declared.pop("product_revisions")
    publication = Publication(feed)
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=publication,
        version="fixture",
    )
    source = ProductSources(lambda: shared)

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    feed["figure_projection_version"] = 2
    feed["compatibility_origin"] = "woocommerce"
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace, source, EquipmentSearchLimits(work_budget=1000)
        ),
        max_attempts=1,
    )
    app = create_private_app(
        workspace,
        EnergyService(
            workspace,
            EnergyKernel(workspace, TOLERANCE, max_intervals=10),
            max_attempts=1,
        ),
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment=equipment,
        equipment_search=search,
        product_provider=lambda: shared,
    )
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    registry = service_registry(
        EnergyService(
            workspace,
            EnergyKernel(workspace, TOLERANCE, max_intervals=10),
            max_attempts=1,
        ),
        None,
        None,
        equipment,
        search,
        reports,
    )
    worker = Worker(
        Jobs(workspace),
        "quickstart-report-path",
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
                "title": "Quick start commercial",
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "inputs": {
                    source_kind: declared,
                    "brief": {**incomplete_brief(), "system_scope": "new_pv_storage"},
                    "equipment_requirements": {
                        "schema_version": 1,
                        "grid_phase": 3,
                        "operating_mode": "grid_connected",
                        "pv_dc_kw": 10,
                        "required_usable_kwh": 15,
                        "required_discharge_ac_kw": 5,
                    },
                },
                "key": "quickstart-project",
            },
            headers=headers(),
        )
        assert created.status_code == 200, created.text
        pid = created.json()["id"]
        found = client.post(
            "/runs/equipment-search",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": 1,
                "key": "quickstart-search",
            },
            headers=headers(),
        )
        assert found.status_code == 200, found.text
        assert worker.run_once()
        searched = workspace.run(owner, found.json()["id"])
        assert searched.state == "succeeded", searched.error
        candidates = json_object(searched.result)["search"]["candidates"]
        assert candidates
        if equipment_use is not None:
            assert all(
                c["selection"].get("equipment_use") == equipment_use for c in candidates
            )
            if equipment_use["inverter"] == "retain":
                assert all(
                    c["selection"]["inverter_product_id"] == 4107 for c in candidates
                )
            else:
                assert {c["selection"]["inverter_product_id"] for c in candidates} == {
                    4107,
                    2063,
                }
            if equipment_use["battery"] == "retain":
                assert all(
                    (
                        c["selection"]["battery_product_id"],
                        c["selection"]["modules_per_stack"],
                        c["selection"]["parallel_stacks"],
                    )
                    == (2090, 4, 1)
                    for c in candidates
                )
            else:
                assert {c["selection"]["modules_per_stack"] for c in candidates} == {
                    2,
                    3,
                    4,
                    5,
                }
        candidate = next(row for row in candidates if row["status"] == "satisfied")
        adopted = {
            "equipment_selection": {
                **candidate["selection"],
                "pv_dc_kw": 10,
                "required_usable_kwh": 15,
                "required_discharge_ac_kw": 5,
            },
            "equipment_candidate": {
                "run_id": searched.id,
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        }
        revised = client.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": 1,
                "inputs": {**created.json()["inputs"], **adopted},
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "quickstart-adopt",
            },
            headers=headers(),
        )
        assert revised.status_code == 200, revised.text
        qualified = client.post(
            "/runs/equipment",
            json={
                "schema_version": 1,
                "project_id": pid,
                "expected_revision": revised.json()["revision"],
                "key": "quickstart-check",
            },
            headers=headers(),
        )
        assert qualified.status_code == 200, qualified.text
        assert worker.run_once()
        run = workspace.run(owner, qualified.json()["id"])
        assert run.state == "succeeded", run.error

        project = workspace.get(owner, pid)
        options = ReportOptions(
            locale="en",
            energy_run_id=None,
            pv_run_id=None,
            equipment_run_id=None,
            logo=None,
        )
        # The screen's own options: the candidate is the equipment source and
        # the report source is complete enough to render a PDF.
        report = json_object(report_sources(workspace, source, owner, project, options))
        assert report["candidate"] == adopted["equipment_candidate"]
        detail = EquipmentCandidateStore(workspace).read(
            owner, searched.id, str(candidate["id"])
        )
        assert report["equipment"] == detail["assessment"]
        assert [row["run_id"] for row in report["source_runs"]] == [searched.id]
        report_run = reports.evaluate(
            owner, pid, project.revision, options, key="quickstart-report"
        )
        assert worker.run_once()
        published = workspace.run(owner, report_run.id)
        assert published.state == "succeeded", published.error
        asset = json_object(published.result)["prepared_asset"]
        assert workspace.blobs.read(cast(str, asset["content_sha256"]))[:5] == b"%PDF-"

        # Naming the qualification run as well contradicts the adopted choice
        # and is what produced the 422; the refusal stays.
        with pytest.raises(InvalidInput, match="differs from the adopted"):
            report_sources(
                workspace,
                source,
                owner,
                project,
                options.model_copy(update={"equipment_run_id": run.id}),
            )


@pytest.mark.parametrize(
    "scope",
    ["pv_only", "new_pv_storage", "storage_addition", "storage_only", None, "absent"],
)
@pytest.mark.parametrize("lower_bound", [None, 0])
def test_search_storage_topology_follows_project_scope_not_sizing_sentinels(
    feed: FixtureObject,
    workspace: Workspace,
    scope: str | None,
    lower_bound: int | None,
) -> None:
    demand: FixtureObject = {
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": None,
            "required_usable_kwh": lower_bound,
            "required_discharge_ac_kw": lower_bound,
        }
    }
    if scope != "absent":
        demand["brief"] = {"system_scope": scope}
    result = json_object(
        search_equipment(
            demand,
            {
                "products": [
                    p for p in feed["products"] if p["id"] in (4107, 2090, 2092)
                ],
                "compatibility": feed["compatibility"],
            },
            EquipmentSearchLimits(work_budget=100),
            EquipmentCandidateStore(workspace),
            lambda: None,
        )
    )
    assert result["candidates"]
    batteries = {c["selection"]["battery_product_id"] for c in result["candidates"]}
    assert batteries == (
        {None}
        if scope == "pv_only"
        else {None, 2090}
        if scope in (None, "absent")
        else {2090}
    )
    if scope in (None, "absent"):
        assert result["coverage"]["gaps"]["storage_scope_not_declared"] > 0
    for candidate in result["candidates"]:
        checks = {
            c["id"]: c
            for c in json_object(
                workspace.blobs.object(candidate["assessment_sha256"])
            )["checks"]
        }
        if candidate["selection"]["battery_product_id"] is None:
            assert checks["battery"]["status"] == (
                "satisfied" if scope == "pv_only" else "unresolved"
            )


@pytest.mark.parametrize(
    ("scope", "with_battery", "expected"),
    [
        ("pv_only", True, "violated"),
        ("new_pv_storage", False, "violated"),
        ("storage_addition", False, "violated"),
        ("storage_only", False, "violated"),
        (None, False, "unresolved"),
        ("pv_only", False, "satisfied"),
    ],
)
def test_equipment_scope_assessment_does_not_treat_zero_as_customer_intent(
    feed: FixtureObject, scope: str | None, with_battery: bool, expected: str
) -> None:
    selected = inputs(feed, 3)["equipment_selection"]
    selected.update(required_usable_kwh=0, required_discharge_ac_kw=0)
    if not with_battery:
        selected.update(
            battery_product_id=None, modules_per_stack=None, parallel_stacks=None
        )
        selected["product_revisions"].pop("2090")
    result = json_object(
        assess_equipment(
            {"brief": {"system_scope": scope}, "equipment_selection": selected}, feed
        )
    )
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["battery_scope" if with_battery else "battery"]["status"] == expected


@pytest.mark.parametrize(
    ("change", "no_battery", "exclusion"),
    [
        ({"inverter_product_id": None}, False, None),
        ({"battery_product_id": None}, False, None),
        ({"modules_per_stack": None}, False, None),
        ({"modules_per_stack": True}, False, None),
        ({"parallel_stacks": 1.5}, False, None),
        ({"equipment_use": {"inverter": "new", "battery": "retain"}}, True, None),
        ({"equipment_use": {"inverter": "new", "battery": "replace"}}, True, None),
        (
            {
                "required_usable_kwh": 1,
                "equipment_use": {"inverter": "new", "battery": "new"},
            },
            True,
            None,
        ),
        (
            {
                "required_discharge_ac_kw": 1,
                "equipment_use": {"inverter": "new", "battery": "new"},
            },
            True,
            None,
        ),
        (
            {"modules_per_stack": 6},
            False,
            "retained_battery_configuration_outside_search_domain",
        ),
        (
            {"parallel_stacks": 2},
            False,
            "retained_battery_configuration_outside_search_domain",
        ),
        (
            {"inverter_product_id": 999999},
            False,
            "retained_equipment_not_in_search_domain",
        ),
        (
            {"battery_product_id": 999999},
            False,
            "retained_equipment_not_in_search_domain",
        ),
    ],
)
def test_search_refuses_missing_or_conflicting_retained_equipment(
    feed: FixtureObject,
    workspace: Workspace,
    change: FixtureObject,
    no_battery: bool,
    exclusion: str | None,
) -> None:
    declared = inputs(feed, 3)["equipment_selection"]
    declared.update(
        required_usable_kwh=0 if no_battery else None,
        required_discharge_ac_kw=0 if no_battery else None,
        equipment_use={"inverter": "retain", "battery": "retain"},
    )
    declared.update(change)
    demand = {
        "brief": {"system_scope": "pv_only" if no_battery else "new_pv_storage"},
        "equipment_setup": declared,
        "equipment_requirements": {
            key: declared[key]
            for key in EquipmentRequirements.model_fields
            if key in declared
        },
    }
    basis = {
        "products": [
            p for p in feed["products"] if p["id"] in (4107, 2063, 2090, 2092)
        ],
        "compatibility": feed["compatibility"],
    }
    store = EquipmentCandidateStore(workspace)
    if exclusion is None:
        with pytest.raises(InvalidInput):
            search_equipment(
                demand,
                basis,
                EquipmentSearchLimits(work_budget=100),
                store,
                lambda: None,
            )
    else:
        result = json_object(
            search_equipment(
                demand,
                basis,
                EquipmentSearchLimits(work_budget=100),
                store,
                lambda: None,
            )
        )
        assert result["candidates"] == []
        assert result["coverage"]["gaps"][exclusion] > 0
        assert any(
            row["reason"] == exclusion
            for row in result["coverage"]["excluded_products"]
        )


@pytest.mark.parametrize("inverter_use", ["new", "retain", "replace"])
def test_pv_only_search_keeps_inverter_intent_without_battery_fallback(
    feed: FixtureObject, workspace: Workspace, inverter_use: str
) -> None:
    declared = inputs(feed, 3)["equipment_selection"]
    declared.update(
        required_usable_kwh=0,
        required_discharge_ac_kw=0,
        equipment_use={"inverter": inverter_use, "battery": "new"},
    )
    result = json_object(
        search_equipment(
            {
                "brief": {"system_scope": "pv_only"},
                "equipment_selection": declared,
                "equipment_requirements": {
                    key: declared[key]
                    for key in EquipmentRequirements.model_fields
                    if key in declared
                },
            },
            {
                "products": [
                    p for p in feed["products"] if p["id"] in (4107, 2063, 2090, 2092)
                ],
                "compatibility": feed["compatibility"],
            },
            EquipmentSearchLimits(work_budget=100),
            EquipmentCandidateStore(workspace),
            lambda: None,
        )
    )
    assert result["candidates"]
    for candidate in result["candidates"]:
        selection = candidate["selection"]
        assert selection["equipment_use"] == {
            "inverter": inverter_use,
            "battery": "new",
        }
        assert selection["battery_product_id"] is None
        assert selection["modules_per_stack"] is None
        assert selection["parallel_stacks"] is None
        if inverter_use == "retain":
            assert selection["inverter_product_id"] == 4107


@pytest.mark.parametrize(
    ("usable_kwh", "discharge_kw"),
    [(None, None), (None, 5), (15, None), (0, None), (None, 0), (0, 0)],
)
def test_prepared_search_preserves_unknown_and_zero_storage_lower_bounds(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    usable_kwh: int | None,
    discharge_kw: int | None,
) -> None:
    from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS

    feed["products"] = [p for p in feed["products"] if p["id"] in (4107, 2090, 2092)]
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="nullable-demand-fixture",
    )

    def current(publication: Publication) -> FixtureObject:
        manifest = publication_manifest(publication.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace,
            ProductSources(lambda: shared),
            EquipmentSearchLimits(work_budget=100),
        ),
        max_attempts=1,
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 10, 32),
        equipment_search=search,
        product_provider=lambda: shared,
    )
    requirements: Object = {
        "schema_version": 1,
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": 10,
        "required_usable_kwh": usable_kwh,
        "required_discharge_ac_kw": discharge_kw,
    }
    with TestClient(app) as client:
        if usable_kwh is None and discharge_kw is None:
            for field in ("required_usable_kwh", "required_discharge_ac_kw"):
                for value in (-1, True, "5"):
                    invalid = client.post(
                        "/projects/create",
                        headers=headers(owner),
                        json={
                            "schema_version": 1,
                            "title": "Invalid sizing",
                            "inputs": {
                                "equipment_requirements": {**requirements, field: value}
                            },
                            "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                            "key": "invalid-demand",
                        },
                    )
                    assert invalid.status_code == 422, invalid.text
                    assert invalid.json()["error"]["code"] == "invalid_input"
            assert workspace.projects(owner) == []
        created = client.post(
            "/projects/create",
            headers=headers(owner),
            json={
                "schema_version": 1,
                "title": "Known connection, optional storage demand",
                "inputs": {
                    "brief": {**incomplete_brief(), "system_scope": "new_pv_storage"},
                    "equipment_setup": requirements,
                    "equipment_requirements": requirements,
                },
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
                "key": "nullable-demand",
            },
        )
        assert created.status_code == 200, created.text
    project = workspace.get(owner, created.json()["id"])
    run = search.evaluate(owner, project.id, project.revision, key="search")
    registry = service_registry(energy, None, None, None, search)
    worker = Worker(
        Jobs(workspace),
        "nullable-demand",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    assert worker.run_once()
    saved = workspace.run(owner, run.id)
    assert saved.state == "succeeded", saved.error
    result = json_object(saved.result)["search"]
    assert result["candidates"]
    for candidate in result["candidates"]:
        selection = candidate["selection"]
        assert selection["required_usable_kwh"] == usable_kwh
        assert selection["required_discharge_ac_kw"] == discharge_kw
        assert selection["battery_product_id"] == 2090
        checks = {
            c["id"]: c
            for c in json_object(
                workspace.blobs.object(candidate["assessment_sha256"])
            )["checks"]
        }
        if usable_kwh is None:
            assert checks["usable_energy"]["status"] == "unresolved"
            assert checks["usable_energy"]["required"] is None
        if usable_kwh is None or discharge_kw is None:
            assert candidate["status"] != "satisfied"
    if usable_kwh is None and discharge_kw is None:
        changed = workspace.revise(
            owner,
            project.id,
            project.revision,
            {
                **project.inputs,
                "equipment_setup": {**requirements, "required_usable_kwh": 0},
            },
            key="explicit-zero-after-unknown",
            input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
        )
        with pytest.raises(InvalidInput, match="need preparation"):
            search.evaluate(
                owner, changed.id, changed.revision, key="stale-preparation"
            )
        assert len(workspace.runs(owner, changed.id)) == 1


@pytest.mark.parametrize(
    ("usable_kwh", "discharge_kw"), [(None, None), (None, 5), (15, None)]
)
def test_unknown_sizing_preserves_supported_stacks_and_assessed_capacity(
    feed: FixtureObject,
    workspace: Workspace,
    usable_kwh: int | None,
    discharge_kw: int | None,
) -> None:
    battery = next(p for p in feed["products"] if p["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": 2,
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["modules_per_stack_max"]["citation"]
        ),
    }
    published = publication_feed(feed, feed["compatibility"])
    basis = {
        "products": [p for p in published["products"] if p["id"] in (4107, 2090, 2092)],
        "compatibility": published["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "new_pv_storage"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": None,
            "required_usable_kwh": usable_kwh,
            "required_discharge_ac_kw": discharge_kw,
        },
    }
    store = EquipmentCandidateStore(workspace)
    result = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
        )
    )
    assert result["completion"] == "exhausted_supported_domain"
    assert {
        (c["selection"]["parallel_stacks"], c["selection"]["modules_per_stack"])
        for c in result["candidates"]
    } == {(stacks, count) for stacks in (1, 2) for count in (2, 3, 4, 5)}
    assert result["qualified_count"] == 0
    for candidate in result["candidates"]:
        selection = candidate["selection"]
        checks = {
            c["id"]: c
            for c in json_object(
                workspace.blobs.object(candidate["assessment_sha256"])
            )["checks"]
        }
        assert candidate["usable_energy_kwh"] == checks["usable_energy"]["actual"]
        expected = (
            None
            if selection["modules_per_stack"] == 2
            else 4.5 * selection["modules_per_stack"] * selection["parallel_stacks"]
        )
        assert candidate["usable_energy_kwh"] == expected
        if discharge_kw is None:
            assert checks["continuous_battery_ac_output"]["status"] == "unresolved"
            assert checks["continuous_battery_ac_output"]["required"] is None

    partial = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=4), store, lambda: None
        )
    )
    assert partial["completion"] == "budget_exhausted"
    assert partial["work_used"] == partial["work_budget"] == 4
    assert {
        (c["selection"]["parallel_stacks"], c["selection"]["modules_per_stack"])
        for c in partial["candidates"]
    } == {(1, 2), (1, 3), (1, 4)}
    # Even without array size, the existing total ordering stays deterministic.
    repeated = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
        )
    )
    assert repeated["candidates"] == result["candidates"]
    if usable_kwh is None and discharge_kw is None:
        retained = json_object(
            search_equipment(
                {
                    **demand,
                    "equipment_setup": {
                        **demand["equipment_requirements"],
                        "inverter_product_id": 4107,
                        "battery_product_id": 2090,
                        "modules_per_stack": 3,
                        "parallel_stacks": 2,
                        "equipment_use": {"inverter": "retain", "battery": "retain"},
                    },
                },
                basis,
                EquipmentSearchLimits(work_budget=100),
                store,
                lambda: None,
            )
        )
        assert len(retained["candidates"]) == 1
        kept = retained["candidates"][0]
        assert (
            kept["selection"]["modules_per_stack"],
            kept["selection"]["parallel_stacks"],
        ) == (3, 2)
        assert kept["usable_energy_kwh"] == 27
        assert kept["status"] == "unresolved"
        # A known phase contradiction remains a violation despite unknown demand.
        wrong_phase = copy.deepcopy(demand)
        wrong_phase["equipment_requirements"]["grid_phase"] = 1
        contradicted = json_object(
            search_equipment(
                wrong_phase,
                basis,
                EquipmentSearchLimits(work_budget=100),
                store,
                lambda: None,
            )
        )
        assert all(c["status"] == "violated" for c in contradicted["candidates"])
        # Nominal energy alone must not be advertised as usable capacity.
        nominal_only = copy.deepcopy(basis)
        del next(p for p in nominal_only["products"] if p["id"] == 2090)["figures"][
            "module_energy_kwh_usable"
        ]
        unknown_capacity = json_object(
            search_equipment(
                demand,
                nominal_only,
                EquipmentSearchLimits(work_budget=100),
                store,
                lambda: None,
            )
        )
        assert all(
            c["usable_energy_kwh"] is None for c in unknown_capacity["candidates"]
        )


@pytest.mark.parametrize("scope", ["new_pv_storage", "pv_only", None])
def test_plant_search_keeps_unknown_allocations_and_joint_delivery_unresolved(
    feed: FixtureObject, workspace: Workspace, scope: str | None
) -> None:
    from linker_engine.planning.equipment_plant import EquipmentPlant
    from linker_engine.planning.plant_search import search_plant
    from linker_engine.planning.plant_search_plan import PlantSearchPlan

    requirements: FixtureObject = {
        "schema_version": 1,
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": None,
        "required_usable_kwh": None,
        "required_discharge_ac_kw": None,
    }
    plan: FixtureObject = {
        "schema_version": 1,
        "requirements": requirements,
        "units": [
            {"id": uid, "name": uid, "requirements": requirements} for uid in ("a", "b")
        ],
        "parallel_groups": [],
    }
    raw: FixtureObject = {
        **plan,
        "units": [
            {"id": uid, "name": uid, "inputs": {"equipment_setup": requirements}}
            for uid in ("a", "b")
        ],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": scope},
        "equipment_plant_requirements": plan,
        "equipment_plant_setup": raw,
    }
    result = json_object(
        search_plant(
            demand,
            {
                "products": [
                    p for p in feed["products"] if p["id"] in (4107, 2090, 2092)
                ],
                "compatibility": feed["compatibility"],
            },
            EquipmentSearchLimits(work_budget=100),
            EquipmentCandidateStore(workspace),
            lambda: None,
        )
    )
    assert result["completion"] == "exhausted_supported_domain"
    assert len(result["candidates"]) == (
        1 if scope == "pv_only" else 25 if scope is None else 16
    )
    assert {
        unit["selection"]["battery_product_id"]
        for candidate in result["candidates"]
        for unit in candidate["plant"]["units"]
    } == ({None} if scope == "pv_only" else {None, 2090} if scope is None else {2090})
    assert result["qualified_count"] == 0
    parsed = PlantSearchPlan.from_inputs(demand)
    for candidate in result["candidates"]:
        assert candidate["status"] == "unresolved"
        assert candidate["usable_energy_kwh"] is None
        assert parsed.matches_plant(EquipmentPlant.read(candidate["plant"]))
        checks = json_object(workspace.blobs.object(candidate["assessment_sha256"]))[
            "checks"
        ]
        joint = [c for c in checks if c["id"].startswith("plant:")]
        assert joint and all(c["status"] == "unresolved" for c in joint)
        assert all(c["required"] is None for c in joint)
    changed = copy.deepcopy(demand)
    changed["equipment_plant_setup"]["requirements"] = {
        **requirements,
        "required_usable_kwh": 0,
    }
    with pytest.raises(InvalidInput):
        PlantSearchPlan.from_inputs(changed)


def test_backup_plant_material_order_is_independent_of_system_ids(
    feed: FixtureObject, workspace: Workspace
) -> None:
    from linker_engine.planning.plant_search import search_plant

    battery = next(p for p in feed["products"] if p["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": 2,
        "unit": None,
        "citation": battery["figures"]["modules_per_stack_max"]["citation"],
    }
    stacked = publication_feed(feed, feed["compatibility"])
    basis = {
        "products": [p for p in stacked["products"] if p["id"] in (4107, 2090, 2092)],
        "compatibility": stacked["compatibility"],
    }
    requirements = {
        "schema_version": 1,
        "grid_phase": 3,
        "operating_mode": "backup",
        "pv_dc_kw": None,
        "required_usable_kwh": None,
        "required_discharge_ac_kw": None,
    }
    layouts = []
    for ids in (("north-a", "south-a"), ("north-b", "south-b")):
        authored: FixtureObject = {
            "brief": {"system_scope": "storage_only"},
            "backup_demand": {"schema_version": 1, "load_kw": 5, "duration_hours": 8},
            "equipment_plant_setup": {
                "schema_version": 1,
                "requirements": requirements,
                "units": [
                    {
                        "id": uid,
                        "name": name,
                        "inputs": {"equipment_setup": requirements},
                    }
                    for uid, name in zip(ids, ("North", "South"), strict=True)
                ],
                "parallel_groups": [],
            },
        }
        found = json_object(
            search_plant(
                compile_discovery_inputs(authored),
                basis,
                EquipmentSearchLimits(work_budget=300),
                EquipmentCandidateStore(workspace),
                lambda: None,
            )
        )
        layouts.append(
            [
                tuple(
                    (
                        u["selection"]["parallel_stacks"],
                        u["selection"]["modules_per_stack"],
                    )
                    for u in c["plant"]["units"]
                )
                for c in found["candidates"]
            ]
        )
    assert len(set(layouts[0])) == 64
    assert layouts[0][0] == ((1, 3), (2, 3))
    assert layouts[0] == layouts[1]


def test_search_enumerates_documented_counts_and_keeps_budget_exhaustion_visible(
    feed: FixtureObject, workspace: Workspace
) -> None:
    basis = {
        "products": [p for p in feed["products"] if p["id"] in [4107, 2090, 2092]],
        "compatibility": feed["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "new_pv_storage"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        },
    }
    store = EquipmentCandidateStore(workspace)
    with pytest.raises(InvalidInput):
        EquipmentRequirements.read(
            {**demand["equipment_requirements"], "grid_phase": True}
        )
    result = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
        )
    )
    assert result["completion"] == "exhausted_supported_domain"
    # Ranking orders satisfied candidates first (closest DC/AC ratio to the
    # band midpoint, then fewer unresolved checks, then product and assembly);
    # the emission order itself is the documented counts ascending.
    rows = result["candidates"]
    assert [
        (r["selection"]["parallel_stacks"], r["selection"]["modules_per_stack"])
        for r in rows
    ] == [(1, 4), (1, 5), (1, 3), (1, 2)]
    assert all(r["selection"]["accessory_product_ids"] == [2092] for r in rows)
    assert rows[0]["status"] == "satisfied" and rows[1]["status"] == "satisfied"
    assert rows[2]["status"] == "violated" and rows[3]["status"] == "unresolved"
    assert result["qualified_count"] == 2
    # The products list carries each battery's own energy figure so a reader can
    # state what a stack holds instead of how many modules it was built from.
    # Measured 2026-11-15 on production: the choice list read "Battery modules
    # per stack: 4" for four different stacks.
    battery_row = next(
        p for p in result["products"] if p["canonical_product_id"] == 2090
    )
    energy = battery_row["energy"]
    assert set(energy) & {"usable_kwh", "nominal_kwh", "module_energy_kwh_usable"}
    assert all(isinstance(v, (int, float)) and v > 0 for v in energy.values())
    compact = json_object(workspace.blobs.object(rows[0]["assessment_sha256"]))
    assert "facts" not in compact["selected_products"][0]
    assert all("facts" not in c for c in compact["checks"])
    limited = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=2), store, lambda: None
        )
    )
    assert (
        limited["completion"] == "budget_exhausted" and len(limited["candidates"]) == 1
    )

    ceiling_inputs = inputs(feed, 3)
    ceiling_inputs["equipment_selection"]["required_discharge_ac_kw"] = 50
    bounded = json_object(assess_equipment(ceiling_inputs, basis))
    check = next(c for c in bounded["checks"] if c["id"] == "grid_output_ceiling")
    assert (
        check["status"] == "violated"
        and check["actual"] == 11
        and check["required"] == 50
    )
    assert (
        check["facts"][0]["quantity"] == "apparent_power"
        and check["facts"][0]["unit"] == "kVA"
    )
    assert check["calculation"]["role"] == "necessary_upper_bound_only"
    assert (
        next(c for c in bounded["checks"] if c["id"] == "continuous_battery_ac_output")[
            "status"
        ]
        == "violated"
    )
    ceiling_inputs["equipment_selection"]["operating_mode"] = "backup"
    assert not any(
        c["id"] == "grid_output_ceiling"
        for c in json_object(assess_equipment(ceiling_inputs, basis))["checks"]
    )

    from linker_engine.planning.plant_search import search_plant

    unit_requirements = demand["equipment_requirements"]
    total = {
        **unit_requirements,
        "pv_dc_kw": 20,
        "required_usable_kwh": 30,
        "required_discharge_ac_kw": 10,
    }
    plan = {
        "schema_version": 1,
        "requirements": total,
        "units": [
            {"id": uid, "name": uid, "requirements": unit_requirements}
            for uid in ("a", "b")
        ],
        "parallel_groups": [],
    }
    raw = {
        "schema_version": 1,
        "requirements": total,
        "units": [
            {"id": uid, "name": uid, "inputs": {"equipment_setup": unit_requirements}}
            for uid in ("a", "b")
        ],
        "parallel_groups": [],
    }
    plant_demand: FixtureObject = {
        "brief": {"system_scope": "new_pv_storage"},
        "equipment_plant_requirements": plan,
        "equipment_plant_setup": raw,
    }
    whole = json_object(
        search_plant(
            plant_demand,
            basis,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    assert whole["completion"] == "exhausted_supported_domain"
    # Count2 remains unresolved on its source window, so it cannot be pruned
    # as a proven violation. Only the known failed count3 is excluded.
    assert {
        tuple(u["selection"]["modules_per_stack"] for u in c["plant"]["units"])
        for c in whole["candidates"]
    } == {(a, b) for a in (2, 4, 5) for b in (2, 4, 5)}
    assert len({c["id"] for c in whole["candidates"]}) == 9
    assert whole["coverage"]["identical_demand_cache_entries"] == 1
    partial = json_object(
        search_plant(
            plant_demand,
            basis,
            EquipmentSearchLimits(work_budget=8),
            store,
            lambda: None,
        )
    )
    assert partial["completion"] == "budget_exhausted"
    assert len(partial["candidates"]) == 1 and partial["work_used"] == 8
    # A large declared layout must pay for the expanded selection before a
    # result entry is created. This is an execution bound, not a device limit.
    large_plan: FixtureObject = copy.deepcopy(plan)
    large_raw: FixtureObject = copy.deepcopy(raw)
    large_plan["units"] = [
        {"id": f"u{i}", "name": f"U{i}", "requirements": unit_requirements}
        for i in range(300)
    ]
    large_raw["units"] = [
        {
            "id": f"u{i}",
            "name": f"U{i}",
            "inputs": {"equipment_setup": unit_requirements},
        }
        for i in range(300)
    ]
    weighted = json_object(
        search_plant(
            {
                "equipment_plant_requirements": large_plan,
                "equipment_plant_setup": large_raw,
            },
            basis,
            EquipmentSearchLimits(work_budget=400),
            store,
            lambda: None,
        )
    )
    assert weighted["completion"] == "budget_exhausted"
    assert weighted["candidates"] == [] and weighted["work_used"] <= 400


def test_search_enumerates_cited_parallel_stacks_and_keeps_missing_facts_visible(
    feed: FixtureObject, workspace: Workspace
) -> None:
    basis = {
        "products": [p for p in feed["products"] if p["id"] in [4107, 2090, 2092]],
        "compatibility": feed["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "new_pv_storage"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        },
    }
    store = EquipmentCandidateStore(workspace)

    # Without a cited stacks_parallel_max fact the battery stays single-stack;
    # the missing fact is a reported gap, never an invented parallel maximum.
    # Ranking orders satisfied combinations first (closest DC/AC ratio to the
    # band midpoint, then fewer unresolved checks, then product and assembly).
    single = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
        )
    )
    assert [
        (row["selection"]["parallel_stacks"], row["selection"]["modules_per_stack"])
        for row in single["candidates"]
    ] == [(1, 4), (1, 5), (1, 3), (1, 2)]
    assert single["coverage"]["gaps"]["stacks_parallel_max_missing"] == 1

    stacked = copy.deepcopy(feed)
    battery = next(p for p in stacked["products"] if p["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": "2",
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["modules_per_stack_max"]["citation"]
        ),
    }
    stacked = publication_feed(stacked, stacked["compatibility"])
    stacked_basis = {
        "products": [p for p in stacked["products"] if p["id"] in [4107, 2090, 2092]],
        "compatibility": stacked["compatibility"],
    }
    multi = json_object(
        search_equipment(
            demand,
            stacked_basis,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    # Stacks ascend in the outer loop, documented counts stay inner, so
    # single-stack coverage is spent first when the budget runs out. One
    # combination (inverter, battery, count) yields one candidate: the first
    # satisfying stack level, or the smallest one as its failing
    # representative - count 2 stays unresolved at every level and keeps its
    # single-stack representative; count 3 satisfies from two stacks on, so its
    # violated single-stack level is replaced; counts 4 and 5 already satisfy
    # single-stack. The result orders satisfied combinations first by fitness.
    assert [
        (row["selection"]["parallel_stacks"], row["selection"]["modules_per_stack"])
        for row in multi["candidates"]
    ] == [(1, 4), (1, 5), (2, 3), (1, 2)]
    assert len(
        {
            (
                row["selection"]["inverter_product_id"],
                row["selection"]["battery_product_id"],
                row["selection"]["modules_per_stack"],
            )
            for row in multi["candidates"]
        }
    ) == len(multi["candidates"])
    assert multi["completion"] == "exhausted_supported_domain"
    assert "stacks_parallel_max_missing" not in multi["coverage"]["gaps"]
    # The pair contract itself decides the accessory basis: BC2-HV1 is a
    # per-system component, so a second stack does not double its quantity.
    two_stack = json_object(
        workspace.blobs.object(
            next(
                row["assessment_sha256"]
                for row in multi["candidates"]
                if row["selection"]["parallel_stacks"] == 2
            )
        )
    )
    bc2 = next(
        line
        for line in two_stack["provisional_bill_of_materials"]
        if line["product_id"] == 2092
    )
    assert bc2["quantity"] == 1 and bc2["basis"] == "manufacturer_required_system"
    partial = json_object(
        search_equipment(
            demand,
            stacked_basis,
            EquipmentSearchLimits(work_budget=4),
            store,
            lambda: None,
        )
    )
    assert partial["completion"] == "budget_exhausted"
    assert [row["selection"]["parallel_stacks"] for row in partial["candidates"]] == [
        1,
        1,
        1,
    ]


@pytest.mark.parametrize("retain_inverter", [False, True])
def test_storage_search_uses_site_application_before_qualifying_products(
    feed: FixtureObject, workspace: Workspace, retain_inverter: bool
) -> None:
    brief = incomplete_brief()
    brief.update(project_use="residential", system_scope="storage_only")
    brief["site"].update(country_code="DE", location_label="Berlin")
    authored: FixtureObject = {
        "brief": brief,
        "backup_demand": {"schema_version": 1, "load_kw": 3, "duration_hours": 2},
        "equipment_setup": {
            "schema_version": 1,
            "inverter_product_id": None,
            "battery_product_id": None,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
            "equipment_use": None,
            "grid_phase": 3,
            "operating_mode": "backup",
            "pv_dc_kw": 0,
            "required_usable_kwh": None,
            "required_discharge_ac_kw": None,
        },
    }
    if retain_inverter:
        authored["equipment_setup"]["inverter_product_id"] = 1946
        authored["equipment_setup"]["equipment_use"] = {
            "inverter": "retain",
            "battery": "new",
        }
    product_ids = {1183, 1946, 2090, 2092, 1954}
    products = [
        copy.deepcopy(product)
        for product in feed["products"]
        if product["id"] in product_ids
    ]
    # This fixture covers application, not an installed battery assembly.
    # Reuse the published battery identity with a synthetic sales-unit witness.
    commercial_battery = next(product for product in products if product["id"] == 1954)
    commercial_battery["figures"]["sales_unit_kind"] = {
        "value": "battery_system",
        "unit": None,
        "citation": commercial_battery["figures"]["system_operating_voltage_range_v"][
            "citation"
        ],
    }
    basis = {
        "products": products,
        "compatibility": feed["compatibility"],
    }
    result = json_object(
        search_equipment(
            compile_discovery_inputs(authored),
            basis,
            EquipmentSearchLimits(work_budget=100),
            EquipmentCandidateStore(workspace),
            lambda: None,
        )
    )
    mismatch = {"product_id": 1946, "reason": "converter_application_mismatch"}
    assert (mismatch in result["coverage"]["excluded_products"]) is not retain_inverter
    assert {
        row["selection"]["inverter_product_id"] for row in result["candidates"]
    } == ({1946} if retain_inverter else {1183})
    assert "application" not in authored["equipment_setup"]


@pytest.mark.parametrize(
    ("site_use", "common_application", "expected_default"),
    [
        ("residential", {}, "residential"),
        ("commercial", {}, "commercial"),
        ("industrial", {}, None),
        (None, {}, None),
        ("residential", {"application": "commercial"}, "commercial"),
        pytest.param(
            "residential", {"application": None}, "residential", id="after-adoption"
        ),
    ],
)
def test_plant_search_uses_site_application_only_for_undeclared_systems(
    site_use: str | None, common_application: Object, expected_default: str | None
) -> None:
    brief = incomplete_brief()
    brief["project_use"] = site_use
    setup = {
        "schema_version": 1,
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": None,
        "required_usable_kwh": None,
        "required_discharge_ac_kw": None,
    }
    authored: FixtureObject = {
        "brief": brief,
        "equipment_plant_setup": {
            "schema_version": 1,
            "requirements": {**setup, **common_application},
            "units": [
                {
                    "id": uid,
                    "name": uid,
                    "inputs": {"equipment_setup": {**setup, **app}},
                }
                for uid, app in (
                    ("a", {}),
                    ("b", {"application": "commercial"}),
                    ("c", {"application": None}),
                )
            ],
            "parallel_groups": [],
        },
    }
    plan = PlantSearchPlan.from_inputs(compile_discovery_inputs(authored))
    assert plan.requirements.application == common_application.get("application")
    assert [unit.requirements.application for unit in plan.units] == [
        expected_default,
        "commercial",
        None,
    ]
    assert (
        "application"
        not in authored["equipment_plant_setup"]["units"][0]["inputs"][
            "equipment_setup"
        ]
    )


def test_residential_application_excludes_contradicting_converters_and_keeps_unknown_visible(
    feed: FixtureObject, workspace: Workspace
) -> None:
    """The manufacturer's own Woo application facet gates the candidate list.

    Production 2026-11-14: every GoodWe GW75K…GW125K is filed commercial, the
    SAJ H2/HS2/HS3 families are filed home. Only a contradicting named
    application excludes; an unknown filing stays visible.
    """
    basis = {
        "products": [
            p for p in feed["products"] if p["id"] in [4107, 1179, 2090, 2092]
        ],
        "compatibility": feed["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "pv_only"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 0,
            "required_discharge_ac_kw": 0,
            "application": "residential",
        },
    }
    store = EquipmentCandidateStore(workspace)
    residential = json_object(
        search_equipment(
            demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
        )
    )
    assert all(
        row["selection"]["inverter_product_id"] != 1179
        for row in residential["candidates"]
    )
    assert residential["coverage"]["gaps"]["converter_application_mismatch"] == 1
    assert {
        "product_id": 1179,
        "reason": "converter_application_mismatch",
    } in residential["coverage"]["excluded_products"]
    unrestricted = json_object(
        search_equipment(
            {
                "equipment_requirements": {
                    **demand["equipment_requirements"],
                    "application": None,
                }
            },
            basis,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    assert any(
        row["selection"]["inverter_product_id"] == 1179
        for row in unrestricted["candidates"]
    )
    # An unknown application filing is preserved, never silently excluded.
    unlabeled = copy.deepcopy(basis)
    unlabeled["products"] = copy.deepcopy(basis["products"])
    next(p for p in unlabeled["products"] if p["id"] == 1179)["application"] = "unknown"
    unknown = json_object(
        search_equipment(
            demand,
            unlabeled,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    assert any(
        row["selection"]["inverter_product_id"] == 1179 for row in unknown["candidates"]
    )
    assert "converter_application_mismatch" not in unknown["coverage"]["gaps"]
    commercial = json_object(
        search_equipment(
            {
                "equipment_requirements": {
                    **demand["equipment_requirements"],
                    "application": "commercial",
                }
            },
            basis,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    assert all(
        row["selection"]["inverter_product_id"] != 4107
        for row in commercial["candidates"]
    )
    assert any(
        row["selection"]["inverter_product_id"] == 1179
        for row in commercial["candidates"]
    )


@pytest.mark.parametrize(
    ("pv_kwp", "expected_status"),
    [(10, "satisfied"), (40, "satisfied"), (46, "violated")],
)
def test_pv_qualification_uses_the_selected_inverters_cited_limit(
    feed: FixtureObject, pv_kwp: float, expected_status: str
) -> None:
    """SAJ's 45 kWp input limit governs a 25 kW inverter, not another brand's ratio."""
    revisions = {
        str(p["id"]): p["product_revision"] for p in feed["products"] if p["id"] == 1179
    }
    selection: FixtureObject = {
        "equipment_selection": {
            "schema_version": 1,
            "inverter_product_id": 1179,
            "battery_product_id": None,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 0,
            "required_discharge_ac_kw": 0,
            "product_revisions": revisions,
        }
    }
    basis = {
        "products": [p for p in feed["products"] if p["id"] == 1179],
        "compatibility": feed["compatibility"],
    }
    selection["equipment_selection"]["pv_dc_kw"] = pv_kwp
    result = json_object(assess_equipment(selection, basis))
    assert (result["overall_status"] == "violated") == (expected_status == "violated")
    check = next(c for c in result["checks"] if c["id"] == "pv_dc_input")
    assert check["status"] == expected_status
    assert check["actual"] == 45
    assert check["required"] == pv_kwp
    assert all(c["id"] != "pv_dc_ac_ratio" for c in result["checks"])


def test_identical_combinations_collapse_to_one_candidate(
    feed: FixtureObject, workspace: Workspace
) -> None:
    """Parallel-stack levels of one documented combination yield one candidate.

    The production search listed the same inverter, battery and module count
    four times consecutively, differing only in the parallel-stack level.
    """
    basis_feed = copy.deepcopy(feed)
    battery = next(p for p in basis_feed["products"] if p["id"] == 2090)
    battery["figures"]["stacks_parallel_max"] = {
        "value": "4",
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["modules_per_stack_max"]["citation"]
        ),
    }
    stacked = publication_feed(basis_feed, basis_feed["compatibility"])
    basis = {
        "products": [p for p in stacked["products"] if p["id"] in [4107, 2090, 2092]],
        "compatibility": stacked["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "new_pv_storage"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        },
    }
    store = EquipmentCandidateStore(workspace)
    result = json_object(
        search_equipment(
            demand,
            basis,
            EquipmentSearchLimits(work_budget=100),
            store,
            lambda: None,
        )
    )
    combos = [
        (
            row["selection"]["inverter_product_id"],
            row["selection"]["battery_product_id"],
            row["selection"]["modules_per_stack"],
        )
        for row in result["candidates"]
    ]
    assert len(combos) == len(set(combos))
    # Counts 4 and 5 satisfy single-stack, so no larger stack level of those
    # combinations is emitted; count 3 emits its first satisfying stack level
    # (two stacks), replacing the violated single-stack level; count 2 stays
    # unresolved at every level and keeps its smallest representative.
    # Ranking orders the satisfied combinations first.
    assert [
        (row["selection"]["parallel_stacks"], row["selection"]["modules_per_stack"])
        for row in result["candidates"]
    ] == [(1, 4), (1, 5), (2, 3), (1, 2)]
    assert result["completion"] == "exhausted_supported_domain"


def test_search_does_not_prefer_an_uncited_dc_ac_ratio(
    feed: FixtureObject, workspace: Workspace
) -> None:
    """A smaller array does not disqualify or demote an otherwise valid inverter."""
    basis = {
        "products": [
            p for p in feed["products"] if p["id"] in [2063, 2064, 4107, 1179]
        ],
        "compatibility": feed["compatibility"],
    }
    demand: FixtureObject = {
        "brief": {"system_scope": "pv_only"},
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 0,
            "required_discharge_ac_kw": 0,
            "application": "residential",
        },
    }
    result = json_object(
        search_equipment(
            demand,
            basis,
            EquipmentSearchLimits(work_budget=100),
            EquipmentCandidateStore(workspace),
            lambda: None,
        )
    )
    assert result["ranking"] == "unresolved_then_product_and_module_count"
    assert all(row["status"] != "violated" for row in result["candidates"])
    assert [
        row["selection"]["inverter_product_id"] for row in result["candidates"]
    ] == [2063, 2064, 4107]


def test_column_limit_condition_binds_count_only_not_stack_count(
    feed: FixtureObject,
) -> None:
    basis = copy.deepcopy(feed)
    battery = next(p for p in basis["products"] if p["id"] == 2090)
    battery["figures"]["modules_per_stack_max"]["value"] = "6"
    battery["figures"]["stacks_parallel_max"] = {
        "value": "2",
        "unit": None,
        "citation": copy.deepcopy(
            battery["figures"]["modules_per_stack_max"]["citation"]
        ),
    }
    for pair in basis["compatibility"]["pairs"]:
        if any(
            accessory.get("model") == "^BC2-HV1$"
            for accessory in pair.get("accessories", [])
        ):
            # The manufacturer condition constrains one column's battery count;
            # stack legality is decided by the cited parallel_stacks fact. The
            # control module is ordered once per stack, as the contract states.
            pair.pop("modules", None)
            pair["accessories"] = [
                {**accessory, "per": "stack"} for accessory in pair["accessories"]
            ]
            pair["conditions"] = [
                {
                    "en": "The user manual limits one column to six batteries and names a battery expansion kit for higher capacity or a lower column (p. 79).",
                    "de": "Das Benutzerhandbuch begrenzt eine Säule auf sechs Batterien und nennt ein Batterie-Erweiterungsset für mehr Kapazität oder eine niedrigere Säule (S. 79).",
                }
            ]
    basis = publication_feed(basis, basis["compatibility"])
    revisions = {
        str(p["id"]): p["product_revision"]
        for p in basis["products"]
        if p["id"] in (4107, 2090, 2092)
    }

    def selection(count: int, stacks: int) -> FixtureObject:
        return {
            "equipment_selection": {
                "schema_version": 1,
                "inverter_product_id": 4107,
                "battery_product_id": 2090,
                "modules_per_stack": count,
                "parallel_stacks": stacks,
                "accessory_product_ids": [2092],
                "grid_phase": 3,
                "operating_mode": "grid_connected",
                "pv_dc_kw": 10,
                "required_usable_kwh": 10,
                "required_discharge_ac_kw": 5,
                "product_revisions": revisions,
            }
        }

    six_two = json_object(assess_equipment(selection(6, 2), basis))
    checks = {check["id"]: check for check in six_two["checks"]}
    assert checks["manufacturer_pair"]["status"] == "satisfied"
    assert checks["parallel_stacks"]["status"] == "satisfied"
    assert checks["modules_per_stack"]["status"] == "satisfied"
    bc2 = next(
        line
        for line in six_two["provisional_bill_of_materials"]
        if line["product_id"] == 2092
    )
    assert bc2["quantity"] == 2 and bc2["basis"] == "manufacturer_required_stack"
    seven_one = json_object(assess_equipment(selection(7, 1), basis))
    pair_check = next(
        check for check in seven_one["checks"] if check["id"] == "manufacturer_pair"
    )
    assert pair_check["status"] == "violated"


def test_roof_string_plan_uses_cited_woo_facts_and_keeps_design_gaps(
    feed: FixtureObject, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One wiring representative: series voltage, parallel current and stale IDs."""
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.pv_string_assessment import assess_pv_strings
    from linker_engine.planning.pv_string_inputs import PvStringPlan

    from .test_pv_generation import geometry

    proof = panel_basis()
    layout = geometry()
    layout["module_specs"] = [
        {**panel_parameters(electrical=True)["specification"], "id": "module"}
    ]
    layout["arrays"][0].update(rows=2, columns=6, excluded_slots=[])
    ids = [p.id for p in panel_poses(read_geometry(layout)) if p.included]
    assert len(ids) == 12
    value = inputs(feed, 3)
    value["geometry"] = layout
    value["equipment_selection"]["pv_dc_kw"] = 5.52
    value["pv_string_plan"] = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "minimum_ambient_c": -10,
        "temperature_source": "Explicit synthetic design temperature; not a site extreme claim",
        "strings": [
            {"id": "s_a", "mppt": 1, "input": 1, "module_ids": ids[:6]},
            {"id": "s_b", "mppt": 1, "input": 2, "module_ids": ids[6:]},
        ],
    }
    basis = {
        "products": feed["products"],
        "compatibility": engine.compatibility.snapshot(),
        "pv_module_inputs": proof,
    }
    result = json_object(assess_pv_strings(value, basis))
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["pv_cold_voc:s_a"]["actual"] == pytest.approx(6 * 53.8 * 1.084)
    assert checks["pv_stc_mppt:s_a"]["actual"] == pytest.approx(6 * 45.4)
    assert checks["pv_stc_current:1"]["actual"] == pytest.approx(2 * 10.14)
    assert checks["pv_stc_isc:1"]["actual"] == pytest.approx(2 * 10.81)
    assert checks["pv_layout_coverage"]["status"] == "satisfied"
    assert checks["pv_module_voltage:s_a"]["required"] == 1500
    assert checks["pv_parallel_count:1"]["status"] == "satisfied"
    assert checks["pv_input:s_a"]["status"] == "unresolved"
    assert checks["pv_operating_temperatures"]["status"] == "unresolved"
    assert checks["pv_design_current"]["status"] == "unresolved"
    # The cited standby interval is distinct from both the absolute cold-Voc
    # rating and the MPPT window; a single STC MPP never proves annual exposure.
    standby_basis = copy.deepcopy(basis)
    inverter = next(
        p for p in standby_basis["products"] if p["canonical_product_id"] == 4107
    )
    source = inverter["figures"]["max_pv_input_v"]["citation"]
    inverter["figures"]["pv_standby_input_voltage_v"] = {
        "value": "950 ~ 1000",
        "unit": "V",
        "citation": source,
    }
    standby_value = copy.deepcopy(value)
    standby_value["geometry"]["arrays"][0].update(rows=4, columns=6)
    standby_ids = [
        p.id
        for p in panel_poses(read_geometry(standby_value["geometry"]))
        if p.included
    ]
    standby_value["pv_string_plan"]["strings"] = [
        {"id": "s_a", "mppt": 1, "input": 1, "module_ids": standby_ids[:21]},
    ]
    standby_result = json_object(assess_pv_strings(standby_value, standby_basis))
    standby = standby_result["standby"]
    point = standby["points"][0]
    assert point["voltage_v"] == pytest.approx(21 * 45.4)
    assert standby["interval_v"] == [950, 1000]
    assert point["observation"] == "in_interval"
    cold = next(c for c in standby_result["checks"] if c["id"] == "pv_cold_voc:s_a")
    assert cold["actual"] != point["voltage_v"]
    assert standby["fact"]["source"]["page"] == source["page"]
    # Merely maintaining this source must not change qualification status.
    without_standby = json_object(assess_equipment(standby_value, basis))
    with_standby = json_object(assess_equipment(standby_value, standby_basis))
    assert without_standby["checks"] == with_standby["checks"]
    assert without_standby["equipment_status"] == with_standby["equipment_status"]
    for voltage, expected in (
        (949.9999, "949.9999 V"),
        (950.0001, "950.0001 V"),
        (950.0000000000001, "> 950 V"),
        (1000.0001, "1,000.0001 V"),
    ):
        comparison = copy.deepcopy(with_standby)
        comparison["pv_electrical"]["standby"]["points"][0]["voltage_v"] = voltage
        formatted = build_report(
            {
                "locale": "en",
                "title": "Display precision",
                "project_id": "a" * 32,
                "revision": 1,
                "input_sha256": "b" * 64,
                "generated_at": "2026-10-26T00:00:00+00:00",
                "source_runs": [],
                "equipment": comparison,
            }
        )
        section = next(s for s in formatted.sections if s.id == "pv-standby-0")
        assert section.table is not None and section.table.rows[0][2] == expected
    for locale in ("en", "de"):
        report = build_report(
            {
                "locale": locale,
                "title": "Standby fixture",
                "project_id": "a" * 32,
                "revision": 1,
                "input_sha256": "b" * 64,
                "generated_at": "2026-10-26T00:00:00+00:00",
                "source_runs": [],
                "equipment": json_object(
                    assess_equipment(standby_value, standby_basis)
                ),
            }
        )
        section = next(s for s in report.sections if "standby" in s.title.lower())
        assert "950" in " ".join(row.value for row in section.rows)
        assert len(section.paragraphs) == 1 and "MPP" in section.paragraphs[0]
        assert any(row.href for row in section.rows)
    standby_value["pv_string_plan"]["strings"][0]["module_ids"] = standby_ids[:20]
    below = json_object(assess_pv_strings(standby_value, standby_basis))
    assert below["standby"]["points"][0]["observation"] == "outside_interval"
    boundary_value = copy.deepcopy(standby_value)
    boundary_value["geometry"]["module_specs"][0]["electrical"]["vmpp_v"] = 47.5
    boundary = json_object(assess_pv_strings(boundary_value, standby_basis))
    assert boundary["standby"]["points"][0]["voltage_v"] == 950
    assert boundary["standby"]["points"][0]["observation"] == "boundary"
    assert "standby" not in result
    modeled_value = copy.deepcopy(standby_value)
    modeled_value["pv_string_plan"]["strings"].append(
        {"id": "s_b", "mppt": 2, "input": 1, "module_ids": standby_ids[20:]}
    )
    modeled_value["pv_string_plan"]["operating_conditions"] = {
        "irradiance_w_m2": 1000,
        "hot_cell_c": 60,
        "cold_cell_c": 20,
        "source_note": "Synthetic uniform operating points",
    }
    modeled = json_object(assess_pv_strings(modeled_value, standby_basis))
    assert len(modeled["standby"]["points"]) == 6
    assert {p["case"] for p in modeled["standby"]["points"]} == {"stc", "hot", "cold"}
    assessment = json_object(assess_equipment(value, basis))
    assert assessment["pv_electrical"] == result
    assert assessment["overall_status"] != "satisfied"
    operating_value = copy.deepcopy(value)
    operating_value["pv_string_plan"]["operating_conditions"] = {
        "irradiance_w_m2": 1000,
        "hot_cell_c": 60,
        "cold_cell_c": 20,
        "source_note": "Explicit synthetic uniform operating cases, not site extremes",
    }
    operating = json_object(assess_equipment(operating_value, basis))["pv_electrical"][
        "operating"
    ]
    model = operating["model"]
    assert model["status"] == "available"
    assert len(operating["points"]) == 4
    assert all(
        p["v_mp_v"] < 6 * 45.4 for p in operating["points"] if p["case"] == "hot"
    )
    assert all(
        p["v_mp_v"] > 6 * 45.4 for p in operating["points"] if p["case"] == "cold"
    )
    assert model["diagnostics"]["stc"]["v_mp"] == pytest.approx(45.4)
    assert model["diagnostics"]["stc"]["i_mp"] == pytest.approx(10.14)
    assert "noct" not in model["diagnostics"]
    assert "cells_in_series" not in model["parameters"]
    presentation = build_report(
        {
            "locale": "en",
            "title": "Wiring model fixture",
            "project_id": "a" * 32,
            "revision": 1,
            "input_sha256": "b" * 64,
            "generated_at": "2026-10-26T00:00:00+00:00",
            "source_runs": [],
            "equipment": json_object(assess_equipment(operating_value, basis)),
        }
    )
    assert any(section.id == "pv-operating" for section in presentation.sections)
    assert any(
        "e-12" in row.value for section in presentation.sections for row in section.rows
    )
    op_checks = {c["id"]: c for c in operating["checks"]}
    assert op_checks["pv_model_applicability"]["status"] == "unresolved"
    assert op_checks["pv_hot_current:1"]["actual"] < op_checks["pv_hot_isc:1"]["actual"]
    invalid_conditions = copy.deepcopy(operating_value)
    invalid_conditions["pv_string_plan"]["operating_conditions"]["hot_cell_c"] = 10
    outside = json_object(assess_equipment(invalid_conditions, basis))["pv_electrical"][
        "operating"
    ]
    assert outside["points"] == []
    assert (
        next(c for c in outside["checks"] if c["id"] == "pv_operating_conditions")[
            "status"
        ]
        == "violated"
    )
    # Reuse the valid fitted result to guard the observed success=True /
    # negative-resistance failure; do not rerun a root for this failure fixture.
    from linker_engine.planning import pv_iv_model
    from linker_engine.planning.declared_module import electrical_facts
    from linker_engine.planning.geometry_documents import ModuleSpec

    with monkeypatch.context() as patch:
        patch.setattr(
            pv_iv_model,
            "fit_desoto",
            lambda *args, **kwargs: (
                {**model["parameters"], "R_s": -1},
                SimpleNamespace(success=True, fun=[0, 0, 0, 0, 0]),
            ),
        )
        assert (
            pv_iv_model.derive_iv_model(
                electrical_facts(
                    ModuleSpec.read(panel_parameters(electrical=True)["specification"])
                )
            )["status"]
            == "unavailable"
        )
    without_target = copy.deepcopy(value)
    without_target["equipment_selection"]["pv_dc_kw"] = None
    no_target_assessment = json_object(assess_equipment(without_target, basis))
    assert no_target_assessment["pv_electrical"]["strings"] == result["strings"]
    assert (
        next(
            c
            for c in no_target_assessment["checks"]
            if c["id"] == "pv_nameplate_layout"
        )["status"]
        == "unresolved"
    )
    saved = copy.deepcopy(value)
    saved["pv_string_plan"]["minimum_ambient_c"] = None
    unknown = json_object(assess_pv_strings(saved, basis))
    assert (
        next(c for c in unknown["checks"] if c["id"] == "pv_cold_voc:s_a")["status"]
        == "unresolved"
    )
    saved = copy.deepcopy(value)
    saved["pv_string_plan"]["strings"][1]["module_ids"][0] = ids[0]
    with pytest.raises(InvalidInput):
        PvStringPlan.read(saved["pv_string_plan"])
    saved = copy.deepcopy(value)
    saved["geometry"]["arrays"][0]["excluded_slots"] = ["0:0"]
    with pytest.raises(InvalidInput, match="removed or excluded"):
        json_object(assess_pv_strings(saved, basis))


def test_multi_system_pv_strings_scope_currents_bindings_and_saved_reports(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from linker_engine.planning.errors import ProjectInputContractRequired
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.http_documents import ProjectInputs
    from linker_engine.planning.plant_assessment import assess_plant
    from linker_engine.planning.project_input_contracts import (
        GEOMETRIC_PV_INPUT_CONTRACT,
        require_input_contract,
    )
    from linker_engine.planning.pv_string_inputs import PvPlantStringPlan

    from .test_pv_generation import geometry

    layout = geometry()
    module = panel_parameters(electrical=True)
    layout["module_specs"] = [{**module["specification"], "id": "module"}]
    layout["arrays"][0].update(rows=2, columns=6, excluded_slots=[])
    mids = [p.id for p in panel_poses(read_geometry(layout)) if p.included]
    plant = plant_inputs(feed)
    plant["requirements"]["pv_dc_kw"] = 5.52
    for unit in plant["units"]:
        unit["selection"]["pv_dc_kw"] = 2.76
    wiring: FixtureObject = {
        "schema_version": 1,
        "units": [
            {
                "unit_id": uid,
                "inverter_instance_id": None,
                "plan": {
                    "schema_version": 1,
                    "inverter_product_id": 4107,
                    "minimum_ambient_c": -10,
                    "temperature_source": "Synthetic design condition",
                    "strings": [
                        {
                            "id": "string_" + uid,
                            "mppt": 1,
                            "input": 1,
                            "module_ids": ids,
                        }
                    ],
                },
            }
            for uid, ids in (("a", mids[:6]), ("b", mids[6:]))
        ],
    }
    value: FixtureObject = {
        "equipment_plant": plant,
        "geometry": layout,
        "pv_plant_string_plan": wiring,
    }
    basis: FixtureObject = {
        "products": feed["products"],
        "compatibility": engine.compatibility.snapshot(),
        "pv_module_inputs": panel_basis(),
        "publication": {"products": [], "documents": [], "reference_inputs": []},
    }
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(None, value, GEOMETRIC_PV_INPUT_CONTRACT)
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(
            value, {"equipment_plant": plant}, GEOMETRIC_PV_INPUT_CONTRACT
        )
    require_input_contract(value, value, "project_panel_parameters_v1")
    cached = {
        digest(encode(unit["selection"])): json_object(
            assess_equipment({"equipment_selection": unit["selection"]}, basis)
        )
        for unit in plant["units"]
    }
    result = json_object(assess_plant(value, basis, unit_assessments=cached))
    for unit in result["systems"]:
        checks = {c["id"]: c for c in unit["assessment"]["checks"]}
        assert checks["pv_stc_current:1"]["actual"] == pytest.approx(10.14)
        assert checks["pv_layout_coverage"]["status"] == "satisfied"
    assert result["pv_electrical"]["assigned_modules"] == 12
    assert result["pv_electrical"]["checks"][0]["status"] == "satisfied"
    assert all(
        u["instance_status"] == "not_recorded" for u in result["pv_electrical"]["units"]
    )
    assert all(
        c["unit_id"] in {"a", "b"}
        for c in result["checks"]
        if c["id"].startswith("unit:")
    )
    # A different inverter keeps its own maintained tracker limits.
    different = copy.deepcopy(value)
    other = next(product for product in feed["products"] if product["id"] == 1184)
    selection = different["equipment_plant"]["units"][1]["selection"]
    selection["inverter_product_id"] = 1184
    selection["product_revisions"].pop("4107")
    selection["product_revisions"]["1184"] = other["product_revision"]
    different["pv_plant_string_plan"]["units"][1]["plan"]["inverter_product_id"] = 1184
    other_result = json_object(assess_plant(different, basis))
    other_checks = {
        c["id"]: c for c in other_result["systems"][1]["assessment"]["checks"]
    }
    assert (
        other_checks["pv_stc_current:1"]["facts"][-1]
        == json_object(compile_product(other))["facts"]["mppt_max_current_a"]
    )
    assert (
        other_result["systems"][0]["assessment"]["pv_electrical"]
        == result["systems"][0]["assessment"]["pv_electrical"]
    )
    duplicate = copy.deepcopy(wiring)
    duplicate["units"][1]["plan"]["strings"][0]["module_ids"][0] = mids[0]
    with pytest.raises(InvalidInput):
        PvPlantStringPlan.read(duplicate)
    for key, change in (
        ("unit_id", "removed_unit"),
        ("product", 999999),
        ("instance", "removed_instance"),
    ):
        stale = copy.deepcopy(value)
        item = stale["pv_plant_string_plan"]["units"][0]
        if key == "product":
            item["plan"]["inverter_product_id"] = change
        else:
            item["inverter_instance_id" if key == "instance" else key] = change
        # Cross-document stale identities remain editable, while preflight rejects them.
        ProjectInputs.model_validate({"schema_version": 1, "inputs": stale})
        with pytest.raises(InvalidInput):
            assess_plant(stale, basis)
    missing = copy.deepcopy(value)
    missing["pv_plant_string_plan"]["units"].pop()
    for demand in (2.76, None, 0):
        missing["equipment_plant"]["units"][1]["selection"]["pv_dc_kw"] = demand
        partial = json_object(assess_plant(missing, basis))
        absent = [
            c for c in partial["checks"] if c["id"] == "unit:b:pv_electrical_topology"
        ]
        if demand != 0:
            assert any(c["status"] == "unresolved" for c in absent)
        assert partial["pv_electrical"]["checks"][0]["status"] == "violated"
    stale = copy.deepcopy(value)
    for unit in stale["equipment_plant"]["units"]:
        unit["selection"]["product_revisions"]["4107"] = "0" * 64
    with pytest.raises(ProductEvidenceChanged):
        assess_plant(stale, basis)

    from linker_engine.planning.installation_takeoff import route_takeoff
    from linker_engine.planning.project_materials import (
        materials_csv,
        project_materials,
    )

    linked = copy.deepcopy(value)
    revision = plant["units"][0]["selection"]["product_revisions"]["4107"]
    position = {"east_m": 0, "north_m": 0, "height_m": 0}
    linked["installation"] = {
        "schema_version": 1,
        "geometry_sha256": digest(encode(layout)),
        "instances": [
            {
                "id": key,
                "name": key,
                "product_id": 4107 if key != "site" else None,
                "product_revision": revision if key != "site" else None,
                "source_id": "survey",
                "ports": [{"id": "port", "name": "Port", "position": position}],
            }
            for key in ("inv_a", "inv_b", "site")
        ],
        "circuits": [
            {
                "id": "c_" + uid,
                "name": "Circuit " + uid,
                "kind": "pv_dc",
                "start": {"instance_id": "inv_" + uid, "port_id": "port"},
                "end": {"instance_id": "site", "port_id": "port"},
            }
            for uid in ("a", "b")
        ],
        "routes": [],
        "cable_runs": [],
        "pv_string_links": [
            {"string_id": "string_" + uid, "circuit_id": "c_" + uid}
            for uid in ("a", "b")
        ],
    }
    for item in linked["pv_plant_string_plan"]["units"]:
        item["inverter_instance_id"] = "inv_" + item["unit_id"]
    reconciled = json_object(route_takeoff(linked, basis))["pv_string_reconciliation"]
    assert (
        reconciled["schema_version"] == 2 and "pv_string_plan_sha256" not in reconciled
    )
    assert [row["status"] for row in reconciled["rows"]] == ["linked", "linked"]
    assert all(row["closure"]["recorded"] is False for row in reconciled["rows"])
    assert [row["unit_id"] for row in reconciled["rows"]] == ["a", "b"]
    for field, changed_value, expected in (
        ("product_id", 2090, "product_mismatch"),
        ("product_revision", "0" * 64, "revision_mismatch"),
    ):
        invalid = copy.deepcopy(linked)
        invalid["installation"]["instances"][0][field] = changed_value
        with pytest.raises(InvalidInput):
            assess_plant(invalid, basis)
        # Review is recovery-oriented even when current Woo evidence prevents
        # route_takeoff's separate device-facts check from running.
        from linker_engine.planning.installation_inputs import InstallationInputs
        from linker_engine.planning.installation_takeoff import _string_links

        review = json_object(
            _string_links(
                invalid, InstallationInputs.read(invalid["installation"]), [], set()
            )
        )
        assert review["rows"][0]["instance_status"] == expected
        assert review["rows"][0]["status"] == "inverter_endpoint_unresolved"
        if field == "product_revision":
            recovery = json_object(
                route_takeoff(invalid, basis, allow_stale_products=True)
            )
            instance = recovery["instances"][0]
            assert instance["product_revision"] == changed_value
            assert instance["brand"] is None and instance["model"] is None
            assert recovery["instances"][1]["model"] is not None
    draft = copy.deepcopy(linked)
    prepared = draft.pop("equipment_plant")
    draft["equipment_plant_setup"] = {
        "schema_version": 1,
        "requirements": prepared["requirements"],
        "units": [
            {
                "id": unit["id"],
                "name": unit["name"],
                "inputs": {"equipment_selection": unit["selection"]},
            }
            for unit in prepared["units"]
        ],
        "parallel_groups": [],
    }
    ProjectInputs.model_validate({"schema_version": 1, "inputs": draft})
    draft_review = json_object(route_takeoff(draft, basis))["pv_string_reconciliation"]
    assert all(
        row["instance_status"] == "unprepared_plant" and not row["closure"]["recorded"]
        for row in draft_review["rows"]
    )
    material_source: FixtureObject = {
        "project_id": "a" * 32,
        "revision": 1,
        "input_sha256": "b" * 64,
        "installation": json_object(route_takeoff(linked, basis)),
        "equipment": result,
    }
    material = json_object(project_materials(material_source))
    for locale in ("en", "de"):
        csv = materials_csv(material, digest(encode(material)), locale).decode(
            "utf-8-sig"
        )
        assert "inv_a" in csv and "inv_b" in csv

    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="plant-wiring-fixture",
    )

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    sources = ProductSources(lambda: shared)
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, sources), max_attempts=1
    )
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    registry = service_registry(energy, None, None, equipment)
    executor = Worker(
        Jobs(workspace),
        "plant-wiring-fixture",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    project = workspace.create(
        owner,
        "Two separately wired systems",
        linked,
        key="plant-wiring-create",
        input_contract="project_panel_parameters_v1",
    )
    run = equipment.evaluate(owner, project.id, 1, key="plant-wiring-evaluate")
    assert executor.run_once()
    run = workspace.run(owner, run.id)
    assert run.state == "succeeded", run.error
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=run.id,
        logo=None,
    )
    source = json_object(report_sources(workspace, sources, owner, project, options))
    assert (
        source["equipment"]["pv_electrical"]
        == json_object(run.result)["assessment"]["pv_electrical"]
    )
    for locale in ("en", "de"):
        report = build_report({**source, "locale": locale})
        section = next(s for s in report.sections if s.id == "pv-strings")
        assert section.table is not None
        assert [row[0] for row in section.table.rows] == ["A", "B"]
        assert [row[1] for row in section.table.rows] == ["inv_a", "inv_b"]
        from linker_engine.pdf import render

        assert render(report).startswith(b"%PDF")
    unrelated = copy.deepcopy(linked)
    unrelated["installation"]["instances"][0]["name"] = "A different display name"
    unrelated["installation"]["circuits"][0]["name"] = "An unrelated route description"
    assert (
        json_object(
            report_sources(
                workspace, sources, owner, replace(project, inputs=unrelated), options
            )
        )["equipment"]
        == source["equipment"]
    )
    identity_change = copy.deepcopy(linked)
    identity_change["installation"]["instances"][0]["product_revision"] = "0" * 64
    with pytest.raises(ReportInputsChanged):
        report_sources(
            workspace, sources, owner, replace(project, inputs=identity_change), options
        )
    changed = copy.deepcopy(linked)
    changed["pv_plant_string_plan"]["units"][0]["plan"]["minimum_ambient_c"] = -20
    with pytest.raises(ReportInputsChanged):
        report_sources(
            workspace, sources, owner, replace(project, inputs=changed), options
        )


def test_conditional_pairs_and_equipment_checks_assess_real_woo_candidates(
    feed: FixtureObject, workspace: Workspace
) -> None:
    basis = copy.deepcopy(feed)
    for pid, kind in (
        (1956, "battery_system"),
        (1958, "battery_system"),
        (2068, "battery_system"),
        (3611, "battery_module"),
    ):
        product = next(p for p in basis["products"] if p["id"] == pid)
        first_citation = next(iter(product["figures"].values()))["citation"]
        product["figures"]["sales_unit_kind"] = {
            "value": kind,
            "unit": None,
            "citation": copy.deepcopy(first_citation),
        }
    b2 = next(p for p in basis["products"] if p["id"] == 2068)
    b2["figures"]["modules_per_stack_min"]["unit"] = "count"
    b2["figures"]["modules_per_stack_max"]["unit"] = "count"
    b2["figures"]["module_energy_kwh_usable"] = {
        "value": "13.5",
        "unit": "kWh",
        "citation": copy.deepcopy(
            b2["figures"]["module_energy_kwh_nominal"]["citation"]
        ),
    }
    etr_template = copy.deepcopy(next(p for p in basis["products"] if p["id"] == 3595))
    etr_6508 = {
        **etr_template,
        "id": 6508,
        "canonical_product_id": 6508,
        "sku": "DLK-GOODWE-GW9999KETRG10",
        "model": "GW99.99K-ETR-G10",
        "ac_power_kw": 99.99,
        "pv_input_kw": 200,
    }
    etr_6508["figures"]["ac_output_kw_nominal"]["value"] = "99.99"
    etr_6508["figures"]["max_pv_input_power_w"]["value"] = "200"
    for doc in etr_6508["documents"]:
        doc["product_ids"] = [*doc.get("product_ids", []), 6508]
    basis["products"].append(etr_6508)
    basis["compatibility"]["pairs"].append(
        {
            "inverter": "^GW99\\.99K\\-ETR\\-G10$",
            "inverter_product_id": 6508,
            "battery": "^GW261\\.2\\-BAT\\-LCD\\-G10$",
            "battery_product_id": 1958,
            "verdict": "released",
            "conditions": [
                {
                    "en": "GoodWe's Battery Compatibility Overview (p. 6) lists GW261.2-BAT-LCD-G10 in its ETR 80–125 kW column, which covers the GW80K/99.99K/100K/110K/124.99K-ETR-G10 models.",
                    "de": "Die Batterie-Kompatibilitätsübersicht von GoodWe (S. 6) führt den GW261.2-BAT-LCD-G10 in der Spalte ETR 80–125 kW auf.",
                }
            ],
            "documents": [
                {
                    "url": etr_6508["documents"][0]["url"],
                    "page": 6,
                }
            ],
        }
    )
    basis = publication_feed(basis, basis["compatibility"])
    revisions = {str(p["id"]): p["product_revision"] for p in basis["products"]}

    # 1. 6508 + 1958: kW PV limit, MPPT topology, conditional release note,
    # fixed battery_system pack count, operating_voltage_range_v, 100% DoD
    # rated_energy_kwh, continuous AC output and discharge path all satisfy.
    # The 120 kWp array keeps the SolarEdge-derived DC/AC sizing band
    # (60%-135%) satisfied at 1.2; the manufacturer's 200 kW PV limit stays
    # the binding kW input fact under test.
    sel_6508: FixtureObject = {
        "schema_version": 1,
        "inverter_product_id": 6508,
        "battery_product_id": 1958,
        "modules_per_stack": 5,
        "parallel_stacks": 1,
        "accessory_product_ids": [],
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": 120.0,
        "required_usable_kwh": 200.0,
        "required_discharge_ac_kw": 99.99,
        "product_revisions": {"6508": revisions["6508"], "1958": revisions["1958"]},
    }
    assessed_6508 = json_object(
        assess_equipment({"equipment_selection": sel_6508}, basis)
    )
    assert assessed_6508["equipment_status"] == "satisfied"
    assert assessed_6508["overall_status"] == "satisfied"
    checks_6508 = {c["id"]: c for c in assessed_6508["checks"]}
    for check_id in (
        "converter_identity",
        "grid_phase",
        "pv_dc_input",
        "pv_electrical_topology",
        "manufacturer_pair",
        "modules_per_stack",
        "parallel_stacks",
        "battery_voltage",
        "battery_sales_unit",
        "usable_energy",
        "continuous_battery_ac_output",
        "battery_discharge_path",
    ):
        assert checks_6508[check_id]["status"] == "satisfied", check_id
    assert checks_6508["usable_energy"]["actual"] == pytest.approx(261.2)
    assert checks_6508["continuous_battery_ac_output"]["actual"] == pytest.approx(99.99)

    # 2. One-way non-warranty condition stays unresolved on manufacturer_pair.
    one_way_basis = copy.deepcopy(basis)
    one_way_basis["compatibility"]["pairs"][-1]["conditions"] = [
        {
            "en": "Listed one-way: a cited document lists the pair; GoodWe's Battery Compatibility Overview (p. 6) does not name it, so the manual's system table is not a complete warranty approval.",
            "de": "Einseitig gelistet: keine vollständige Garantiefreigabe.",
        }
    ]
    one_way_assessed = json_object(
        assess_equipment({"equipment_selection": sel_6508}, one_way_basis)
    )
    assert (
        next(c for c in one_way_assessed["checks"] if c["id"] == "manufacturer_pair")[
            "status"
        ]
        == "unresolved"
    )
    assert one_way_assessed["overall_status"] == "unresolved"

    # 3. SAJ B2-15.0 (2068) with unit='count' on modules_per_stack_min/max
    # and accessory 2092 resolves modules_per_stack=3, voltage and usable energy.
    sel_b2: FixtureObject = {
        "schema_version": 1,
        "inverter_product_id": 4107,
        "battery_product_id": 2068,
        "modules_per_stack": 3,
        "parallel_stacks": 1,
        "accessory_product_ids": [2092],
        "grid_phase": 3,
        "operating_mode": "grid_connected",
        "pv_dc_kw": 10.0,
        "required_usable_kwh": 12.0,
        "required_discharge_ac_kw": 5.0,
        "product_revisions": {
            "4107": revisions["4107"],
            "2068": revisions["2068"],
            "2092": revisions["2092"],
        },
    }
    assessed_b2 = json_object(assess_equipment({"equipment_selection": sel_b2}, basis))
    assert assessed_b2["overall_status"] == "satisfied"

    # 4. Unreleased Cartesian pairs do not consume work_budget or record
    # pair_release_not_established gaps during search.
    store = EquipmentCandidateStore(workspace)
    search_res = json_object(
        search_equipment(
            {
                "equipment_requirements": {
                    "schema_version": 1,
                    "grid_phase": 3,
                    "operating_mode": "grid_connected",
                    "pv_dc_kw": 120.0,
                    "required_usable_kwh": 200.0,
                    "required_discharge_ac_kw": 90.0,
                }
            },
            basis,
            EquipmentSearchLimits(work_budget=500),
            store,
            lambda: None,
        )
    )
    assert "pair_release_not_established" not in search_res["coverage"]["gaps"]
    assert search_res["qualified_count"] >= 1
    assert any(
        c["selection"]["inverter_product_id"] == 6508
        and c["selection"]["battery_product_id"] == 1958
        and c["status"] == "satisfied"
        for c in search_res["candidates"]
    )


def test_requirements_read_the_prepared_declarations_a_one_screen_start_sends() -> None:
    # The one-screen start sends both documents. `application` is declared by the
    # requirements only, so a setup that omits it must not read as a contradiction
    # — measured on the production project, where every country was refused.
    request: FixtureObject = {
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 13.7,
            "required_discharge_ac_kw": 6,
            "application": "residential",
        },
        "equipment_setup": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 13.7,
            "required_discharge_ac_kw": 6,
            "inverter_product_id": None,
            "battery_product_id": None,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
        },
    }
    assert EquipmentRequirements.from_inputs(request).application == "residential"
    # Current authored fields must agree with any retained prepared projection.
    for field, value in (
        ("required_usable_kwh", 99.0),
        ("application", None),
        ("application", "commercial"),
    ):
        contradicted = copy.deepcopy(request)
        contradicted["equipment_setup"][field] = value
        with pytest.raises(InvalidInput):
            EquipmentRequirements.from_inputs(contradicted)


@pytest.mark.parametrize(
    ("controller", "standard", "topology"),
    [
        ("self_consumption_with_reserve_v1", True, None),
        ("peak_shaving_with_reserve_v1", True, None),
        ("self_consumption_with_reserve_v1", False, None),
        ("peak_shaving_with_reserve_v1", False, None),
        ("self_consumption_with_reserve_v1", False, "wired_single"),
        ("self_consumption_with_reserve_v1", False, "wired_dc_plant"),
        ("self_consumption_with_reserve_v1", False, "wired_dc_plant_legacy"),
        ("self_consumption_with_reserve_v1", False, "plant_ac"),
        ("self_consumption_with_reserve_v1", False, "plant_shared_dc"),
        ("self_consumption_with_reserve_v1", False, "plant_shared_dc_ac_branch"),
        ("self_consumption_with_reserve_v1", False, "shared_dc"),
        ("peak_shaving_with_reserve_v1", False, "shared_dc"),
        ("self_consumption_with_reserve_v1", False, "undeclared_plant"),
        ("self_consumption_with_reserve_v1", False, "missing_load"),
        ("self_consumption_with_reserve_v1", False, "missing_pv"),
        ("peak_shaving_with_reserve_v1", False, "unavailable_load"),
    ],
)
def test_profile_goal_search_uses_owned_load_without_battery_preparation(
    feed: FixtureObject,
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    monkeypatch: pytest.MonkeyPatch,
    controller: str,
    standard: bool,
    topology: str | None,
) -> None:
    import base64

    from linker_engine.planning.csv_mapping import CsvMapping
    from linker_engine.planning.pvgis_reference_kernel import PvgisRoofReferenceKernel
    from linker_engine.planning.worker import Control

    from .test_private_http import Rig, standard_profile_command
    from .test_pv_generation import geometry
    from .test_pv_profile import import_pv, project_with_roof
    from .test_pvgis_roof_reference import limits as reference_limits
    from .test_pvgis_roof_reference import settings as roof_settings

    ac_branch = topology == "plant_shared_dc_ac_branch"
    if ac_branch:
        topology = "plant_shared_dc"
    dc = topology in ("shared_dc", "plant_shared_dc")
    legacy_dc = topology == "wired_dc_plant_legacy"
    wired_dc = topology == "wired_dc_plant" or legacy_dc
    wired = topology in ("wired_single", "plant_ac") or wired_dc
    peak = controller.startswith("peak")
    inverter = next(row for row in feed["products"] if row["id"] == 4107)
    for direction in ("charge", "discharge"):
        inverter["figures"][f"continuous_battery_{direction}_ac_power_kw"] = {
            "value": 1.5 if direction == "charge" else 6,
            "unit": "kW",
            "citation": copy.deepcopy(
                inverter["figures"]["battery_voltage_range_v"]["citation"]
            ),
        }
    inverter["figures"]["max_battery_terminal_discharge_power_kw"] = {
        "value": 2,
        "unit": "kW",
        "citation": copy.deepcopy(
            inverter["figures"]["battery_voltage_range_v"]["citation"]
        ),
    }
    feed, source, loaded, _, _, _ = prepared_dc_fixture_source(
        feed, engine, monkeypatch
    )
    ac = EnergyKernel(workspace, TOLERANCE, max_intervals=40000, products=source)
    energy = EnergyService(workspace, ac, max_attempts=1)
    search = EquipmentService(
        workspace,
        EquipmentSearchKernel(
            workspace,
            source,
            EquipmentSearchLimits(work_budget=1000),
            tolerance=TOLERANCE,
            max_intervals=40000,
            pvgis_reference=PvgisRoofReferenceKernel(
                workspace, source, reference_limits(), max_array_steps=20_000
            )
            if wired or dc
            else None,
        ),
        max_attempts=1,
    )
    if legacy_dc:
        # Reproduce the earlier result format before the real worker freezes it.
        compute = search.kernel.compute

        def legacy_result(
            inputs: Object, basis: Object, control: Control, *, pinned: Object
        ) -> Object:
            result = compute(inputs, basis, control, pinned=pinned)
            result.pop("pv_capacity_basis", None)
            return result

        monkeypatch.setattr(search.kernel, "compute", legacy_result)
    reports = ReportService(workspace, ReportKernel(workspace, source), max_attempts=1)
    equipment = EquipmentService(
        workspace, EquipmentKernel(workspace, source), max_attempts=1
    )
    registry = service_registry(
        energy, None, equipment=equipment, equipment_search=search, reports=reports
    )
    worker = Worker(
        Jobs(workspace),
        "profile-bounds-worker",
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
        limits=HttpLimits(1000000, 8000000, 40000, 32),
        equipment=equipment,
        equipment_search=search,
        reports=reports,
        product_provider=lambda: loaded,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        rig = Rig(workspace, ac, client)
        roof = project_with_roof(workspace, owner) if dc and not peak else None
        pid = roof.id if roof else rig.create("profile-bounds")

        def csv_profile(
            role: Literal["gross_load", "pv_available_ac"],
            values: tuple[int, ...],
            *,
            key: str | None = None,
        ) -> str:
            content = "time,power\n" + "".join(
                f"2026-01-01T{hour:02}:00:00+01:00,{value}\n"
                for hour, value in enumerate(values)
            )
            asset = rig.post(
                "/profiles/csv",
                {
                    "project_id": pid,
                    "content_base64": base64.b64encode(content.encode()).decode(),
                    "mapping": json_object(
                        CsvMapping(
                            "time",
                            "power",
                            role,
                            "interval_average_kw",
                            "start",
                            "Europe/Berlin",
                            "synthetic",
                            3600,
                            ",",
                            ".",
                        ).document()
                    ),
                    "source_label": "Profile bounds fixture",
                    "rights_note": "created by test",
                    "key": key or role,
                },
            )
            return str(asset["id"])

        selected = {
            "gross_load": rig.post(
                "/profiles/standard",
                standard_profile_command(pid, "standard-bounds-load"),
            )["id"]
            if standard
            else csv_profile("gross_load", (4, 4, 4, 4) if peak else (2, 2, 2, 2))
        }
        if standard or not peak:
            selected["pv_available_ac"] = csv_profile(
                "pv_available_ac", (10, 0) if standard else (8, 8, 0, 0)
            )
        declarations: FixtureObject = {
            "profile_selections": {
                "schema_version": 1,
                "selected": selected,
            },
            "equipment_setup": {
                "schema_version": 1,
                "grid_phase": 3,
                "operating_mode": "grid_connected",
                "pv_dc_kw": None,
                "required_usable_kwh": None,
                "required_discharge_ac_kw": None,
            },
            "energy_scenario": {
                "controller": controller,
                "battery": None,
                "schedule": [
                    {
                        "start_utc": "2026-01-01T00:00:00+01:00",
                        "end_utc": "2026-01-01T02:00:00+01:00"
                        if standard
                        else "2026-01-01T04:00:00+01:00",
                        "mode": "connected",
                        "pv_enabled": "pv_available_ac" in selected,
                        "reserve_kwh": None,
                        "import_cap_kw": 0.5 if peak else None,
                        "export_cap_kw": None,
                        "allow_grid_charge": None,
                    }
                ],
            },
        }
        if wired:
            layout = geometry()
            module = panel_parameters(electrical=True)
            layout["module_specs"] = [{**module["specification"], "id": "module"}]
            layout["arrays"][0].update(rows=2, columns=6, excluded_slots=[])
            declarations.update(
                brief={**incomplete_brief(), "system_scope": "new_pv_storage"},
                geometry=layout,
            )
        if peak and not standard and topology is None:
            period = declarations["energy_scenario"]["schedule"][0]
            split = "2026-01-01T02:00:00+01:00"
            declarations["energy_scenario"]["schedule"] = [
                {**period, "end_utc": split, "import_cap_kw": 0.25},
                {**period, "start_utc": split, "import_cap_kw": 0.75},
            ]
        command = {
            "project_id": pid,
            "expected_revision": 1,
            "inputs": declarations,
            "input_contract": "project_panel_parameters_v1"
            if wired
            else "backup_demand_v1",
            "key": "compare-profile-bounds",
        }
        if wired_dc or topology in ("plant_ac", "plant_shared_dc", "undeclared_plant"):
            setup = {**declarations.pop("equipment_setup"), "pv_dc_kw": 0}
            declarations["equipment_plant_setup"] = {
                "schema_version": 1,
                "requirements": setup,
                "units": [
                    {
                        "id": name,
                        "name": name,
                        "inputs": {
                            "equipment_setup": {
                                **setup,
                                "inverter_product_id": 4107,
                                "battery_product_id": 2090,
                                "modules_per_stack": 3,
                                "parallel_stacks": 1,
                                "equipment_use": {
                                    "inverter": "retain",
                                    "battery": "retain",
                                },
                            }
                        },
                    }
                    for name in ("east", "west")
                ],
                "parallel_groups": [],
            }
            if topology != "undeclared_plant":
                declarations["energy_plant_setup"] = {
                    "coupling": "plant_shared_dc" if wired_dc else topology
                }
            if wired_dc:
                declarations["equipment_plant_setup"]["requirements"]["pv_dc_kw"] = 5.52
                for unit in declarations["equipment_plant_setup"]["units"]:
                    unit["inputs"]["equipment_setup"]["pv_dc_kw"] = 2.76
            if topology in ("plant_ac", "undeclared_plant"):
                # Switching to a plant retains the earlier single-system declarations.
                declarations["energy_scenario"]["coupling"] = "shared_dc"
        elif topology == "shared_dc":
            declarations["energy_scenario"]["coupling"] = topology
            selected.pop("pv_available_ac", None)
        elif topology == "missing_load":
            del declarations["profile_selections"]
            declarations["brief"] = {
                "schema_version": 1,
                "project_use": None,
                "system_scope": "pv_only",
                "site": {
                    "country_code": "DE",
                    "location_label": "Leipzig",
                    "latitude": None,
                    "longitude": None,
                    "coordinate_basis": "not_provided",
                    "timezone": None,
                },
                "annual_load": {"kwh": None, "basis": None, "source_note": ""},
                "project_note": "",
            }
            declarations["energy_scenario"]["schedule"][0].update(
                start_utc="", end_utc=""
            )
            # Older project editors could save the scope while hiding
            # declarations that still make the search invalid.
            for storage in (
                {
                    "backup_demand": {
                        "schema_version": 1,
                        "load_kw": 5,
                        "duration_hours": 4,
                    }
                },
                {
                    "equipment_setup": {
                        **declarations["equipment_setup"],
                        "required_usable_kwh": 20,
                    }
                },
                {
                    "equipment_setup": {
                        **declarations["equipment_setup"],
                        "battery_product_id": 2090,
                        "modules_per_stack": 3,
                        "parallel_stacks": 1,
                        "equipment_use": {"inverter": "new", "battery": "retain"},
                    }
                },
            ):
                conflicting = rig.post(
                    "/runs/find-equipment",
                    {
                        **command,
                        "expected_revision": command["expected_revision"],
                        "inputs": {**declarations, **storage},
                        "key": f"legacy-conflict-{command['expected_revision']}",
                    },
                )
                assert worker.run_once()
                failed = rig.post("/runs/read", {"run_id": conflicting["run"]["id"]})
                assert failed["state"] == "failed", failed
                assert failed["error"]["code"] == "invalid_input"
                command["expected_revision"] = conflicting["project"]["revision"]
        elif topology == "missing_pv":
            selected.pop("pv_available_ac")
        elif topology == "unavailable_load":
            selected["gross_load"] = "a" * 32
            command["schema_version"] = 1
            reply = client.post(
                "/runs/find-equipment", json=command, headers=headers(owner)
            )
            assert reply.status_code == 404, reply.json()
            assert workspace.get(owner, pid).revision == 1
            return
        if roof:
            declarations.update(roof.inputs)
            declarations["brief"] = {
                **incomplete_brief(),
                "system_scope": "new_pv_storage",
            }
            if topology == "plant_shared_dc":
                declarations["pvgis_reference"] = roof_settings()
            selected["pv_reference"] = import_pv(workspace, owner, roof).id
            if not ac_branch:
                selected.pop("pv_available_ac", None)
            if topology == "plant_shared_dc":
                plant_setup = declarations["equipment_plant_setup"]
                plant_setup["requirements"]["pv_dc_kw"] = 4
                for unit in plant_setup["units"]:
                    unit["inputs"]["equipment_setup"]["pv_dc_kw"] = 2
            else:
                declarations["equipment_setup"]["pv_dc_kw"] = 4
        accepted = rig.post("/runs/find-equipment", command)
        assert accepted["project"]["inputs"] == declarations
        assert worker.run_once()
        run = rig.post("/runs/read", {"run_id": accepted["run"]["id"]})
        assert run["state"] == "succeeded", run
        result = run["result"]["search"]
        assert result["candidates"]

        if topology == "undeclared_plant":
            for item in result["candidates"]:
                assert item["demand"]["missing_facts"] == [
                    "common_ac_meter_and_storage_topology"
                ]

        if roof:
            pins = run["manifest"]["context"]["assets"]
            assert "gross_load.raw" in pins
            assert not any(
                key.startswith(("pv_available_ac.", "pvgis_reference.")) for key in pins
            )
            baseline = result["demand"]["baseline"]
            assert baseline["load_kwh"] == 8
            assert all(
                value is None for name, value in baseline.items() if name != "load_kwh"
            )
            for item in result["candidates"]:
                if topology == "plant_shared_dc":
                    assert item["plant"]["requirements"]["pv_dc_kw"] == 4
                    assert [
                        (
                            unit["id"],
                            unit["selection"]["pv_dc_kw"],
                            unit["selection"]["inverter_product_id"],
                        )
                        for unit in item["plant"]["units"]
                    ] == [("east", 2, 4107), ("west", 2, 4107)]
                else:
                    assert item["selection"]["pv_dc_kw"] == 4
                assert item["demand"]["missing_facts"] == [
                    "project_pv_output_through_assigned_dc_converters"
                ]
                assert item["demand"]["peak_import_lower_bound_kw"] is None

        def verify_wired_report(candidate: FixtureObject) -> None:
            from linker_engine.planning.geometry import panel_poses, read_geometry
            from linker_engine.planning.project_input_contracts import (
                SUPPORTED_INPUT_CONTRACTS,
            )

            choice = {
                "run_id": run["id"],
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            }
            values = copy.deepcopy(accepted["project"]["inputs"])
            values["equipment_candidate"] = choice
            if "plant" in candidate:
                values["equipment_plant"] = candidate["plant"]
                values["equipment_plant_setup"]["requirements"]["pv_dc_kw"] = candidate[
                    "plant"
                ]["requirements"]["pv_dc_kw"]
                for unit, built in zip(
                    values["equipment_plant_setup"]["units"],
                    candidate["plant"]["units"],
                    strict=True,
                ):
                    unit["inputs"]["equipment_setup"] = {
                        key: value
                        for key, value in built["selection"].items()
                        if key != "product_revisions"
                    }
            else:
                selection = candidate["selection"]
                values["equipment_selection"] = selection
                values["equipment_setup"] = {
                    key: value
                    for key, value in selection.items()
                    if key != "product_revisions"
                }
                values["equipment_setup"]["comparison_models"] = {
                    "inverter_product_id": None,
                    "battery_product_id": None,
                }
            command_base = {
                "project_id": pid,
                "input_contract": SUPPORTED_INPUT_CONTRACTS[-1],
            }
            adopted = rig.post(
                "/projects/revise",
                {
                    **command_base,
                    "expected_revision": accepted["project"]["revision"],
                    "inputs": values,
                    "key": "adopt-before-wiring",
                },
            )
            layout = values["geometry"]
            modules = [p.id for p in panel_poses(read_geometry(layout)) if p.included]
            compared = json_object(
                workspace.pinned_inputs(workspace.run(owner, run["id"]).manifest)
            )
            demand = (
                compared["equipment_plant_setup"]["requirements"]
                if "plant" in candidate
                else compared["equipment_requirements"]
            )
            assert demand["pv_dc_kw"] == pytest.approx(5.52)

            def plan(name: str, ids: list[str]) -> FixtureObject:
                return {
                    "schema_version": 1,
                    "inverter_product_id": 4107,
                    "minimum_ambient_c": -10,
                    "temperature_source": "Fixture design temperature",
                    "strings": [{"id": name, "mppt": 1, "input": 1, "module_ids": ids}],
                }

            if "plant" in candidate:
                values["pv_plant_string_plan"] = {
                    "schema_version": 1,
                    "units": [
                        {
                            "unit_id": unit,
                            "inverter_instance_id": None,
                            "plan": plan(f"s_{unit}", ids),
                        }
                        for unit, ids in (("east", modules[:6]), ("west", modules[6:]))
                    ],
                }
                names = ["s_east", "s_west"]
            else:
                values["pv_string_plan"] = plan("s_main", modules)
                names = ["s_main"]
            checked = rig.post(
                "/runs/check-equipment",
                {
                    **command_base,
                    "expected_revision": adopted["revision"],
                    "inputs": values,
                    "key": "check-adopted-wiring",
                },
            )
            assert worker.run_once()
            check = rig.post("/runs/read", {"run_id": checked["run"]["id"]})
            assert check["state"] == "succeeded", check["error"]
            options = {
                "locale": "en",
                "equipment_run_id": check["id"],
                "energy_run_id": None,
                "pv_run_id": None,
                "logo": None,
            }
            report_command = {
                "project_id": pid,
                "expected_revision": checked["project"]["revision"],
                "key": "report-adopted-wiring",
                "options": options,
            }
            queued = rig.post("/runs/report", report_command)
            assert worker.run_once()
            report = rig.post("/runs/read", {"run_id": queued["id"]})
            assert report["state"] == "succeeded", report["error"]
            pdf = workspace.blobs.read(
                report["result"]["prepared_asset"]["content_sha256"]
            )
            text = " ".join(
                " ".join(page.extract_text().split())
                for page in PdfReader(io.BytesIO(pdf)).pages
            )
            assert "PV wiring plan" in text
            if wired_dc:
                assert "Additional solar use, upper bound" not in text
            else:
                upper = 4 if "plant" in candidate else 3
                assert f"Additional solar use, upper bound {upper} kWh" in text
            frozen = json_object(
                workspace.blobs.object(
                    report["manifest"]["context"]["assets"]["report.source"]
                )
            )
            wiring = frozen["equipment"]["pv_electrical"]
            strings = (
                [s for unit in wiring["units"] for s in unit["assessment"]["strings"]]
                if "plant" in candidate
                else wiring["strings"]
            )
            assert [s["id"] for s in strings] == names
            assert frozen["candidate"] == choice
            assert [
                (item["run_id"], item.get("candidate_id"))
                for item in frozen["source_runs"]
            ] == [(run["id"], candidate["id"]), (check["id"], None)]
            changed = (
                values["pv_plant_string_plan"]["units"][0]["plan"]
                if "plant" in candidate
                else values["pv_string_plan"]
            )
            changed["strings"][0]["mppt"] = 2
            saved = rig.post(
                "/projects/revise",
                {
                    **command_base,
                    "expected_revision": checked["project"]["revision"],
                    "inputs": values,
                    "key": "rewire-again",
                },
            )
            stale = client.post(
                "/runs/report",
                json={
                    **report_command,
                    "schema_version": 1,
                    "expected_revision": saved["revision"],
                    "key": "stale-wiring",
                },
                headers=headers(owner),
            )
            assert (
                stale.status_code == 422
                and stale.json()["error"]["code"] == "report_inputs_changed"
            ), stale.text

            layout["arrays"][0]["excluded_slots"] = ["0:0"]
            changed["strings"][0]["module_ids"].remove(modules[0])
            rechecked = rig.post(
                "/runs/check-equipment",
                {
                    **command_base,
                    "expected_revision": saved["revision"],
                    "inputs": values,
                    "key": "check-eleven-modules",
                },
            )
            assert worker.run_once()
            assert (
                rig.post("/runs/read", {"run_id": rechecked["run"]["id"]})["state"]
                == "succeeded"
            )
            stale = client.post(
                "/runs/report",
                json={
                    **report_command,
                    "schema_version": 1,
                    "expected_revision": rechecked["project"]["revision"],
                    "options": {**options, "equipment_run_id": rechecked["run"]["id"]},
                    "key": "old-twelve-module-comparison",
                },
                headers=headers(owner),
            )
            if wired_dc and not legacy_dc:
                assert stale.status_code == 200, stale.text
                assert worker.run_once()
                updated = rig.post("/runs/read", {"run_id": stale.json()["id"]})
                assert updated["state"] == "succeeded", updated["error"]
                frozen = json_object(
                    workspace.blobs.object(
                        updated["manifest"]["context"]["assets"]["report.source"]
                    )
                )
                assert frozen["candidate"] == choice
                assert [entry["run_id"] for entry in frozen["source_runs"]] == [
                    run["id"],
                    rechecked["run"]["id"],
                ]
                # Even with current wiring, changing compared hardware requires a new choice.
                setup = values["equipment_plant_setup"]
                plant = values["equipment_plant"]
                for field, declaration, selection in (
                    ("plant", setup["requirements"], plant["requirements"]),
                    (
                        "east",
                        setup["units"][0]["inputs"]["equipment_setup"],
                        plant["units"][0]["selection"],
                    ),
                ):
                    original = declaration["pv_dc_kw"]
                    declaration["pv_dc_kw"] = selection["pv_dc_kw"] = 4
                    altered = client.post(
                        "/runs/check-equipment",
                        json={
                            **command_base,
                            "schema_version": 1,
                            "expected_revision": rechecked["project"]["revision"],
                            "inputs": values,
                            "key": f"old-choice-different-{field}-capacity",
                        },
                        headers=headers(owner),
                    )
                    assert altered.status_code == 422, altered.text
                    assert altered.json()["error"]["code"] == "invalid_input", (
                        altered.text
                    )
                    declaration["pv_dc_kw"] = selection["pv_dc_kw"] = original
                return
            assert stale.status_code == 422, stale.text
            assert stale.json()["error"]["code"] == "report_inputs_changed"

        if topology == "missing_load":
            assert "demand" not in result
            assert all(
                item["selection"]["battery_product_id"] is None
                for item in result["candidates"]
            )
            return
        assert result["demand"]["model"] == "profile_physical_bounds_v1"
        if topology == "missing_pv":
            assert result["demand"]["baseline"]["load_kwh"] == 8
            assert result["demand"]["baseline"]["pv_available_kwh"] is None
            assert all(
                item["demand"]["status"] == "unresolved"
                for item in result["candidates"]
            )
            return
        if topology == "wired_single":
            candidate = next(
                c
                for c in result["candidates"]
                if c["selection"]["inverter_product_id"] == 4107
                and c["demand"]["additional_pv_use_upper_kwh"] == 3
            )
            verify_wired_report(candidate)
            return
        if topology is not None:
            assert result["demand"]["baseline"]["load_kwh"] == (16 if peak else 8)
            candidates = result["candidates"]
            assert candidates
            if wired_dc:
                verify_wired_report(candidates[0])
                return
            if topology == "plant_ac":
                candidate = next(
                    item
                    for item in candidates
                    if all(
                        unit["selection"]["inverter_product_id"] == 4107
                        and unit["selection"]["battery_product_id"] == 2090
                        and unit["selection"]["modules_per_stack"] == 3
                        for unit in item["plant"]["units"]
                    )
                )
                assert candidate["demand"]["status"] == "bounded"
                assert candidate["demand"]["additional_pv_use_upper_kwh"] == 4
                verify_wired_report(candidate)
            elif topology == "shared_dc" and peak:
                candidate = next(
                    item
                    for item in candidates
                    if item["selection"]["inverter_product_id"] == 4107
                    and item["selection"]["battery_product_id"] == 2090
                )
                assert candidate["demand"]["status"] == "violated"
                assert candidate["demand"]["peak_import_lower_bound_kw"] == 2
            else:
                assert all(
                    item["demand"]["status"] == "unresolved" for item in candidates
                )
                assert all(
                    item["demand"]["additional_pv_use_upper_kwh"] is None
                    for item in candidates
                )
                if topology == "shared_dc":
                    assert result["demand"]["baseline"]["direct_pv_use_kwh"] is None
                    assert result["demand"]["baseline"]["grid_import_kwh"] is None
                candidate = candidates[0]
            detail = rig.post(
                "/equipment/candidates/read",
                {"run_id": run["id"], "candidate_id": candidate["id"]},
            )
            assert detail["assessment"]["provisional_bill_of_materials"]
            if topology == "plant_shared_dc":
                adopted_inputs = {
                    **accepted["project"]["inputs"],
                    "equipment_plant": candidate["plant"],
                    "equipment_candidate": {
                        "run_id": run["id"],
                        "candidate_id": candidate["id"],
                        "assessment_sha256": detail["assessment_sha256"],
                    },
                }
                for unit, built in zip(
                    adopted_inputs["equipment_plant_setup"]["units"],
                    candidate["plant"]["units"],
                    strict=True,
                ):
                    unit["inputs"]["equipment_setup"] = {
                        key: value
                        for key, value in built["selection"].items()
                        if key != "product_revisions"
                    }
                adopted = rig.post(
                    "/projects/revise",
                    {
                        **command,
                        "inputs": adopted_inputs,
                        "expected_revision": accepted["project"]["revision"],
                        "key": "adopt-shared-dc-candidate",
                    },
                )
                report = rig.post(
                    "/runs/report",
                    {
                        "project_id": pid,
                        "expected_revision": adopted["revision"],
                        "key": "report-shared-dc-candidate",
                        "options": {
                            "locale": "en",
                            "energy_run_id": None,
                            "pv_run_id": None,
                            "equipment_run_id": None,
                            "logo": None,
                        },
                    },
                )
                assert worker.run_once()
                completed = rig.post("/runs/read", {"run_id": report["id"]})
                assert completed["state"] == "succeeded", completed
                frozen = json_object(
                    workspace.blobs.object(
                        completed["manifest"]["context"]["assets"]["report.source"]
                    )
                )
                retained = frozen["self_use_comparison"]
                assert retained["baseline"] == result["demand"]["baseline"]
                assert retained["upper_kwh"] is None
                pdf = completed["result"]["prepared_asset"]
                csv = completed["result"]["prepared_attachments"][
                    "bill_of_materials_csv"
                ]
                for asset in (pdf, csv):
                    response = client.post(
                        "/assets/content",
                        json={
                            "schema_version": 1,
                            "project_id": pid,
                            "asset_id": asset["id"],
                        },
                        headers=headers(owner),
                    )
                    assert response.status_code == 200
                    assert response.content
                    if asset == pdf:
                        text = " ".join(
                            " ".join(page.extract_text().split())
                            for page in PdfReader(io.BytesIO(response.content)).pages
                        )
                        assert "Electricity use 8 kWh" in text
                        assert "Additional solar use, upper bound" not in text
            return
        baseline = result["demand"]["baseline"]
        if standard:
            assert baseline["pv_available_kwh"] == 10
            assert result["demand"]["interval_count"] == 8
            assert baseline["load_kwh"] > 0
        else:
            assert result["demand"]["interval_count"] == 4
            assert baseline["load_kwh"] == (16 if peak else 8)
            assert baseline["pv_available_kwh"] == (0 if peak else 16)
            assert baseline["over_target_kwh"] == (14 if peak else 0)
        assert result["candidates"]
        assert all(
            c["demand"]["status"] in ("bounded", "violated")
            for c in result["candidates"]
        )
        if standard:
            assert any(
                c["demand"]["additional_pv_use_upper_kwh"] > 0
                for c in result["candidates"]
                if c["selection"]["battery_product_id"] is not None
            )
        else:
            options = {
                c["usable_energy_kwh"]: c["demand"]
                for c in result["candidates"]
                if c["selection"]["inverter_product_id"] == 4107
                and c["selection"]["battery_product_id"] == 2090
            }
            if peak:
                assert result["demand"]["peak_target_kw"] is None
                assert result["demand"]["peak_target_periods"] == [
                    {
                        "start_utc": "2025-12-31T23:00:00+00:00",
                        "end_utc": "2026-01-01T01:00:00+00:00",
                        "import_cap_kw": 0.25,
                    },
                    {
                        "start_utc": "2026-01-01T01:00:00+00:00",
                        "end_utc": "2026-01-01T03:00:00+00:00",
                        "import_cap_kw": 0.75,
                    },
                ]
                assert baseline["peak_grid_import_kw"] == 4
                assert options[13.5]["status"] == "violated"
                assert options[13.5]["peak_import_lower_bound_kw"] == 0.625
                assert options[18]["status"] == "bounded"
            else:
                assert options[13.5]["additional_pv_use_upper_kwh"] == 3
                assert options[18]["additional_pv_use_upper_kwh"] == 3
                assert {
                    fact["source"]["figure_key"]
                    for fact in options[13.5]["source_facts"]
                } == {
                    "continuous_battery_charge_ac_power_kw",
                    "continuous_battery_discharge_ac_power_kw",
                }
        assert (
            rig.post("/runs/find-equipment", command)["run"]["id"]
            == accepted["run"]["id"]
        )
        assert len(workspace.runs(owner, pid)) == 1
        if standard:
            return
        candidate = next(
            c
            for c in result["candidates"]
            if c["demand"]["status"] == "bounded"
            and (peak or c["demand"]["additional_pv_use_upper_kwh"] == 3)
        )
        adopted_inputs = {
            **accepted["project"]["inputs"],
            "equipment_selection": candidate["selection"],
            "equipment_candidate": {
                "run_id": run["id"],
                "candidate_id": candidate["id"],
                "assessment_sha256": candidate["assessment_sha256"],
            },
        }

        def revise(values: FixtureObject, revision: int, key: str) -> FixtureObject:
            return rig.post(
                "/projects/revise",
                {
                    **command,
                    "inputs": values,
                    "expected_revision": revision,
                    "key": key,
                },
            )

        adopted = revise(adopted_inputs, accepted["project"]["revision"], "adopt-peak")
        report_command = {
            "schema_version": 1,
            "project_id": pid,
            "expected_revision": adopted["revision"],
            "key": "report-current-peak",
            "options": {
                "locale": "en",
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
            },
        }
        for locale, labels in (
            (
                "en",
                (
                    "Target grid import limit",
                    "Grid import peak without storage",
                    "Grid import peak, optimistic lower bound",
                    "Further checks required",
                ),
            ),
            (
                "de",
                (
                    "Gewünschte Netzbezugsgrenze",
                    "Netzbezugsspitze ohne Speicher",
                    "Optimistische Untergrenze der Netzbezugsspitze",
                    "Weitere Prüfung erforderlich",
                ),
            ),
        ):
            report = rig.post(
                "/runs/report",
                {
                    **report_command,
                    "key": f"report-current-peak-{locale}",
                    "options": {**report_command["options"], "locale": locale},
                },
            )
            assert worker.run_once()
            completed = rig.post("/runs/read", {"run_id": report["id"]})
            assert completed["state"] == "succeeded"
            pdf_asset = completed["result"]["prepared_asset"]
            pdf_bytes = workspace.blobs.read(pdf_asset["content_sha256"])
            text = " ".join(
                " ".join(page.extract_text().split())
                for page in PdfReader(io.BytesIO(pdf_bytes)).pages
            )
            if not peak:
                expected = (
                    (
                        "Direct solar use 4 kWh",
                        "Additional solar use, upper bound 3 kWh",
                        "Only surplus solar energy stored during this period counts",
                        "lossless storage",
                    )
                    if locale == "en"
                    else (
                        "Direkt genutzter Solarstrom 4 kWh",
                        "Zusätzlicher Eigenverbrauch, Obergrenze 3 kWh",
                        "Nur in diesem Zeitraum gespeicherte PV-Überschüsse zählen",
                        "verlustfreie Speicherung",
                    )
                )
                assert all(label in text for label in expected)
                continue
            bound = str(candidate["demand"]["peak_import_lower_bound_kw"])
            if locale == "de":
                bound = bound.replace(".", ",")
            for start, end, cap in (
                ("2025-12-31T23:00:00+00:00", "2026-01-01T01:00:00+00:00", "0.25"),
                ("2026-01-01T01:00:00+00:00", "2026-01-01T03:00:00+00:00", "0.75"),
            ):
                shown = cap if locale == "en" else cap.replace(".", ",")
                assert f"{labels[0]} {start} – {end}: {shown} kW" in text
            assert f"{labels[1]} 4 kW" in text
            assert (
                f"{labels[2]} {bound.removesuffix('.0').removesuffix(',0')} kW" in text
            )
            assert labels[3] in text
        model_changed = copy.deepcopy(adopted_inputs)
        model_changed["equipment_setup"]["comparison_models"] = {
            "inverter_product_id": None,
            "battery_product_id": candidate["selection"]["battery_product_id"],
        }
        peak_changed = copy.deepcopy(adopted_inputs)
        peak_changed["energy_scenario"]["schedule"][0]["import_cap_kw"] = 0.125
        load_changed = copy.deepcopy(adopted_inputs)
        load_changed["profile_selections"]["selected"]["gross_load"] = csv_profile(
            "gross_load", (6, 6, 6, 6), key="updated-load"
        )
        revision = adopted["revision"]
        for key, changed in (
            ("models", model_changed),
            ("peak", peak_changed),
            ("load", load_changed),
        ):
            revised = revise(changed, revision, "change-" + key)
            revision = revised["revision"]
            stale = client.post(
                "/runs/report",
                json={
                    **report_command,
                    "expected_revision": revision,
                    "key": "report-stale-" + key,
                },
                headers=headers(owner),
            )
            assert stale.status_code == 422, stale.text
            assert stale.json()["error"]["code"] == "report_inputs_changed"
