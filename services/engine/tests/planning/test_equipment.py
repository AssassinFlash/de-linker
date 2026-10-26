"""Current Woo fixture -> typed quantities -> one real durable qualification.

The source numbers/documents reuse the existing engineering fixture and shipped
pair contract. Synthetic publication identities are never runtime product data.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
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
from linker_engine.planning.energy_equipment import assess_energy_equipment
from linker_engine.planning.energy_inputs import BatteryParameters
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_candidate_choice import check_equipment_candidate
from linker_engine.planning.equipment_candidate_store import EquipmentCandidateStore
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
    VersionUnavailable,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_model import build_report
from linker_engine.planning.report_sources import ReportInputsChanged, report_sources
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication, PublicationUnavailable

from .test_energy_kernel import BATTERY, TOLERANCE, create_scenario
from .test_energy_kernel import worker as energy_worker
from .test_private_http import TOKEN, USER, headers


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


def plant_inputs(feed: dict, *, coordinated: bool = False) -> Object:
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


def test_cabinet_sales_unit_and_factory_count_share_cited_woo_basis(feed: dict) -> None:
    from linker_engine.planning.battery_assembly import battery_assembly
    from linker_engine.planning.equipment_inputs import EquipmentSelection

    basis = copy.deepcopy(feed)
    cabinet = next(p for p in basis["products"] if p["id"] == 1955)
    original = compile_product(cabinet)
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
    assembly = battery_assembly(compile_product(cabinet))
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
    result = assess_equipment(
        {"equipment_selection": selection.model_dump(mode="json")}, basis
    )
    assert [
        row["quantity"]
        for row in result["provisional_bill_of_materials"]
        if row["product_id"] == 1955
    ] == [1]
    cabinet["figures"]["modules_per_stack_max"]["qualifier"] = {"unassessed": True}
    conditional = battery_assembly(compile_product(cabinet))
    assert conditional is not None and conditional["fixed_modules_per_stack"] is None
    del cabinet["figures"]["sales_unit_kind"]
    assert battery_assembly(compile_product(cabinet)) is None
    assert not any(
        row["product_id"] == 1955
        for row in assess_equipment(
            {"equipment_selection": selection.model_dump(mode="json")}, basis
        )["provisional_bill_of_materials"]
    )


def test_multi_converter_plant_keeps_unit_ownership_and_source_revisions(
    feed: dict,
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


def test_multi_converter_native_job_freezes_plant_materials_and_report_lineage(
    feed: dict,
    engine: Engine,
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from linker_engine.planning.plant_assessment import assess_plant
    from linker_engine.planning.project_materials import project_materials

    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="plant-fixture",
    )

    def current(self):
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    sources = ProductSources(lambda: shared)
    controller = next(p for p in feed["products"] if p["id"] == 2409)
    plant = plant_inputs(feed, coordinated=True)
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
    source = report_sources(
        workspace, sources, actor, workspace.get(actor, project["id"]), options
    )
    materials = project_materials(source)
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
    report = build_report(source)
    assert source == frozen_source
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
    assessment = assess_plant({"equipment_plant": wrong}, sources.equipment_basis())
    assert any(
        c["id"] == "plant:allocation:pv_dc_kw" and c["status"] == "violated"
        for c in assessment["checks"]
    )
    # A deliberately synthetic source bound tests the group constraint. It
    # does not assert that these SAJ devices actually use a GoodWe controller.
    limited = copy.deepcopy(sources.equipment_basis())
    limited["compatibility"]["requirements"].append(
        {
            "kind": "parallel_controller",
            "inverter": "^H2-10K-T3$",
            "inverter_product_id": 4107,
            "included": False,
            "phase": 3,
            "max_units": 1,
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
    restricted = assess_plant({"equipment_plant": plant}, limited)
    assert any(
        c["id"].endswith(":parallel_count") and c["status"] == "violated"
        for c in restricted["checks"]
    )
    workspace.revise(
        actor, project["id"], 1, {"equipment_plant": wrong}, key="change-plant-demand"
    )
    with pytest.raises(InvalidInput):
        report_sources(
            workspace, sources, actor, workspace.get(actor, project["id"]), options
        )

    # The same private command/worker/store/report path can now search a whole
    # layout before any converter or battery has been manually chosen.
    from linker_engine.planning.plant_search_plan import PlantSearchPlan

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
    plan = {
        "schema_version": 1,
        "requirements": raw_search["requirements"],
        "units": [
            {
                "id": u["id"],
                "name": u["name"],
                "requirements": {
                    key: u["inputs"]["equipment_setup"][key]
                    for key in EquipmentRequirements.model_fields
                },
            }
            for u in raw_search["units"]
        ],
        "parallel_groups": raw_search["parallel_groups"],
    }
    request_inputs = {
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
        result = searched.result["search"]
        assert (
            result["coverage"]["template"]
            == "declared_plant_one_external_assembly_per_converter"
        )
        assert result["coverage"]["identical_demand_cache_entries"] == 1
        assert result["candidates"]
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
        compact = workspace.blobs.object(candidate["assessment_sha256"])
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
                "key": "adopt-plant-search",
            },
        )
        assert adopted.status_code == 200, adopted.text
    selected_source = report_sources(
        workspace,
        sources,
        actor,
        workspace.get(actor, project["id"]),
        options.model_copy(update={"equipment_run_id": None}),
    )
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
    source = {
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
            ],
            "installation_requirements": [
                {"kind": "meter", "included": True, "unit_id": "a", "unit_name": "A"},
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
    material = project_materials(source)
    unknown = [
        r for r in material["lines"] if r.get("basis") == "manufacturer_included"
    ]
    assert len(unknown) == 1 and unknown[0]["quantity"] is None
    assert material_name(unknown[0], "en").startswith("B · ")
    assert unknown[0]["source"]["documents"] == [
        {"url": "https://fixture.invalid/b.pdf"}
    ]


def test_shared_dc_native_asset_command_worker_and_stage_bound_trace(
    feed: dict,
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

    inverter = next(row for row in feed["products"] if row["id"] == 4107)
    battery = next(row for row in feed["products"] if row["id"] == 2090)

    def figure(
        product: dict, key: str, value: float | str, unit: str, citation: dict
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
    voltage["qualifier"] = {
        "quantity_kind": "operating_range",
        "scope": "battery_system",
        "module_count_basis": "columns",
    }
    voltage["columns"] = [
        {
            "module_count": i,
            "min": column["value"][0],
            "max": column["value"][1],
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

    feed = publication_feed(feed, feed["compatibility"])
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    loaded = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )

    def current(publication: Publication) -> dict:
        result = publication_manifest(publication.feed)
        for row in result["products"]:
            row["ready"]["engineering"] = True
        return result

    monkeypatch.setattr(Publication, "read", current)
    source = ProductSources(lambda: loaded)
    layout = geometry()
    module_id = layout["module_specs"][0]["id"]
    module_basis = source.module_basis()["module"]
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
        project.inputs["geometry"], meteo, parameters, max_array_steps=10
    )
    metadata = {
        "schema": 1,
        "profile_type": PROFILE_PURPOSE,
        "retention": "permanent",
        "provenance": PROVENANCE,
        "geometry_sha256": digest(encode(project.inputs["geometry"])),
        "parameters_sha256": digest(encode(project.inputs["pv_generation"])),
        "woo_module_inputs": source.module_basis(),
        "dependencies": {
            "pv_model_inputs": workspace.blobs.put(generated.inputs_json),
            "pv_model_witness": workspace.blobs.put(generated.witness_json),
        },
    }
    full_parts = pv_components(workspace.blobs, raw_hash, metadata)
    assert full_parts["components"][0]["quantity"] == 6
    roof_parts = saved_roof_components(
        layout, source.module_basis(), workspace.blobs, project.revision
    )
    assert roof_parts["components"] == full_parts["components"]
    assert roof_parts["scope"] == "saved_roof"
    group_parts = pv_components(
        workspace.blobs, raw_hash, metadata, converter_id=parameters.converters[0].id
    )
    assert group_parts["components"][0]["quantity"] == 5
    assert "array:1:2" not in group_parts["components"][0]["module_ids"]
    assert pv_components(workspace.blobs, raw_hash, {})["reason"] == "no_saved_layout"
    without_proof = {k: v for k, v in metadata.items() if k != "woo_module_inputs"}
    assert (
        pv_components(workspace.blobs, raw_hash, without_proof)["reason"]
        == "no_woo_module_proof"
    )
    corrupted = generated.witness()
    corrupted["arrays"][0]["module_count"] += 1
    with pytest.raises(VersionUnavailable):
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
                    role,
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
        body = {
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
        assert workspace.blobs.object(asset["content_sha256"]) == scenario.model_dump(
            mode="json"
        )
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
    assert saved.result["kind"] == dc.kind
    assert saved.result["model"]["usable_window_kwh"] == 13.5
    assert saved.result["model"]["charge_terminal_kw"] == pytest.approx(8.064)
    assert saved.result["metrics"]["load_demand_kwh"] == 4
    assert saved.result["scenario_constraint_status"] == "satisfied"
    assert "pv_generated_ac_kwh" not in saved.result["metrics"]
    assert (
        saved.result["prepared_dc_parameters"]["product_revisions"]
        == project.inputs["equipment_selection"]["product_revisions"]
    )
    from linker_engine.planning.dc_energy_parameters import DcPreparedParameters
    from linker_engine.planning.energy_equipment import assess_dc_energy_equipment
    from linker_engine.planning.trace_window import TraceWindow

    page = TraceWindow(workspace).page(owner, saved.id, offset=0, page_size=2)
    assert page["measurement_boundaries"]["pv"] == "PV_DC_bus"
    assert page["measurement_boundaries"]["charge"] == "battery_DC_terminal"
    witness = workspace.blobs.object(metadata["dependencies"]["pv_model_witness"])
    selected_pv = next(
        group
        for group in witness["converters"]
        if group["id"] == project.inputs["energy_replay"]["pv_converter_id"]
    )
    assert page["rows"][0]["pv_kw"] == selected_pv["dc_available_w"][0] / 1000
    assert page["rows"][0]["pv_kw"] > selected_pv["available_ac_w"][0] / 1000
    # Reuse the saved physical model and source to check the hardware mode.
    # This does not replay physics or invent a backup rating for the fixture.
    outage_inputs = copy.deepcopy(project.inputs)
    outage_inputs["energy_replay"]["schedule"][0]["mode"] = "outage"
    prepared_model = DcPreparedParameters.read(
        saved.result["prepared_dc_parameters"]
    ).battery_model(saved.result["pinned_assets"]["battery.dc_prepared_parameters"])
    mismatch = assess_dc_energy_equipment(
        outage_inputs, source.equipment_basis(), prepared_model
    )
    assert any(
        check["id"] == "scenario_operating_mode" and check["status"] == "violated"
        for check in mismatch["assessment"]["checks"]
    )
    for locale in ("en", "de"):
        frozen_report = report_sources(
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
        report = build_report(
            {**frozen_report, "locale": locale, "generated_at": "2026-10-25T00:00:00Z"}
        )
        assert (
            frozen_report["equipment"]
            == saved.result["equipment_binding"]["assessment"]
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
        assert any(
            row[0] == ("5 pc" if locale == "en" else "5 St.") and "460" in row[1]
            for row in bom.table.rows
        )
        assert any(
            row[0] == ("3 pc" if locale == "en" else "3 St.")
            and battery["model"] in row[1]
            for row in bom.table.rows
        )
        part_table = next(
            section for section in report.sections if section.id == "pv-components"
        ).table
        assert part_table is not None and part_table.rows[0][0] == "5"
        section = next(section for section in report.sections if section.id == "energy")
        dc_rows = [row for row in section.rows if "(DC)" in row.label]
        assert len(dc_rows) == 2 and all(row.value.endswith("kWh") for row in dc_rows)
        assert "DC" in section.paragraphs[0] and "AC" in section.paragraphs[0]
    facts = saved.result["prepared_dc_parameters"]["source_facts"]
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
        saved.result["prepared_dc_parameters"]["battery"]["charge_power_limit_kw"]
        == 9.216
    )
    # A table declared in W cannot silently carry a mismatching duplicate cell.
    from linker_engine.planning.equipment_fact_resolution import (
        FactContext,
        resolve_fact,
    )
    from linker_engine.planning.equipment_inputs import EquipmentSelection

    bad = copy.deepcopy(compile_product(battery)["facts"]["rated_power_w"])
    bad["columns"][2]["unit"] = "Wp"
    context = FactContext(
        EquipmentSelection.read(project.inputs["equipment_selection"]),
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


def test_pv_reference_proof_tracks_its_component_instead_of_sales_compatibility(
    feed: dict, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    withdrawn = False

    def current(self: Publication) -> dict:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        if withdrawn:
            manifest["products"] = [
                row
                for row in manifest["products"]
                if row.get("engineering_role") != "reference_pv_module"
            ]
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    source = ProductSources(lambda: loaded)
    proof = source.module_basis()
    proof["publication"]["compatibility_revision"] = "0" * 64
    source.confirm_basis(proof)
    electrical = source.electrical_module_basis()
    source.confirm_basis(electrical)
    changed_electrical = copy.deepcopy(electrical)
    changed_electrical["electrical_product"]["figures"]["voc_v"]["value"] = 1
    with pytest.raises(ProductEvidenceChanged):
        source.confirm_basis(changed_electrical)
    changed = copy.deepcopy(proof)
    changed["module"]["parameters"]["gamma_pdc_per_c"] = -0.01
    with pytest.raises(ProductEvidenceChanged):
        source.confirm_basis(changed)
    changed = copy.deepcopy(proof)
    changed["publication"]["documents"][0]["blob_sha256"] = "0" * 64
    with pytest.raises(ProductEvidenceChanged):
        source.confirm_basis(changed)
    withdrawn = True
    with pytest.raises(ProductEvidenceChanged):
        source.confirm_basis(proof)


def test_cited_quantities_keep_apparent_power_conditions_and_table_columns(
    feed: dict,
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
    generic = compile_product(battery)["facts"]["rated_power_w"]
    context = FactContext(
        EquipmentSelection.read(inputs(feed, 3)["equipment_selection"]),
        {p["canonical_product_id"]: p for p in feed["products"]},
    )
    assert (
        resolve_fact(generic, context, "bank_rated_dc_power").issue
        == "system_power_basis_required"
    )

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


def test_energy_uses_its_simulated_window_instead_of_the_manual_sizing_target(
    feed: dict, workspace: Workspace, owner: Actor
) -> None:
    scenario = create_scenario(workspace, owner)
    proposed = {**scenario.inputs, **inputs(feed, 3)}
    basis = {"products": feed["products"], "compatibility": feed["compatibility"]}
    model = BatteryParameters.read(BATTERY).battery("a" * 64)
    binding = assess_energy_equipment(
        proposed, basis, replace(model, usable_window_kwh=15)
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
    feed: dict,
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

    def current(self: Publication) -> dict:
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
    result = saved.result
    assert result is not None
    binding = result["equipment_binding"]
    assert binding["selection"] == project.inputs["equipment_selection"]
    assert (
        workspace.blobs.object(result["pinned_assets"]["equipment.selection"])
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
    report_source = report_sources(workspace, source, owner, project, options)
    assert report_source["energy_equipment"] == binding
    assert (
        report_source["woo_bases"]["energy_equipment"]
        == result["pinned_assets"]["woo.equipment_inputs"]
    )
    for locale in ("en", "de"):
        report = build_report({**report_source, "locale": locale})
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
    bad_voltage = assess_energy_equipment(
        {**project.inputs, **inputs(feed, 1)},
        workspace.blobs.object(result["pinned_assets"]["woo.equipment_inputs"]),
        BatteryParameters.read(BATTERY).battery("a" * 64),
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
                **project.inputs["equipment_selection"],
                "modules_per_stack": 4,
            },
        },
        key="different-equipment-same-energy-input",
    )
    with pytest.raises(ReportInputsChanged):
        report_sources(workspace, source, owner, changed, options)


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
    with pytest.raises(VersionUnavailable):
        source.equipment_basis()
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
        proof = completed.result["pinned_assets"]["woo.equipment_inputs"]
        assert workspace.blobs.object(proof)["figure_projection_version"] == 2
        search_command = {**command, "key": "search-first"}
        found = client.post(
            "/runs/equipment-search", json=search_command, headers=headers()
        )
        assert found.status_code == 200, found.text
        assert worker.run_once()
        searched = workspace.run(owner, found.json()["id"])
        assert searched.state == "succeeded", searched.error
        candidate = searched.result["search"]["candidates"][0]
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
        selected_inputs = {
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


def test_search_enumerates_documented_counts_and_keeps_budget_exhaustion_visible(
    feed: dict, workspace: Workspace
) -> None:
    basis = {
        "products": [p for p in feed["products"] if p["id"] in [4107, 2090, 2092]],
        "compatibility": feed["compatibility"],
    }
    demand = {
        "equipment_requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": 10,
            "required_usable_kwh": 15,
            "required_discharge_ac_kw": 5,
        }
    }
    store = EquipmentCandidateStore(workspace)
    with pytest.raises(InvalidInput):
        EquipmentRequirements.read(
            {**demand["equipment_requirements"], "grid_phase": True}
        )
    result = search_equipment(
        demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
    )
    assert result["completion"] == "exhausted_supported_domain"
    rows = result["candidates"]
    assert [r["selection"]["modules_per_stack"] for r in rows] == [2, 3, 4, 5]
    assert all(r["selection"]["accessory_product_ids"] == [2092] for r in rows)
    assert rows[1]["status"] == "violated" and rows[2]["status"] == "unresolved"
    assert result["qualified_count"] == 0
    compact = workspace.blobs.object(rows[2]["assessment_sha256"])
    assert "facts" not in compact["selected_products"][0]
    assert all("facts" not in c for c in compact["checks"])
    limited = search_equipment(
        demand, basis, EquipmentSearchLimits(work_budget=2), store, lambda: None
    )
    assert (
        limited["completion"] == "budget_exhausted" and len(limited["candidates"]) == 1
    )

    # A necessary ceiling excludes underpowered grid proposals without
    # replacing the separate missing continuous battery-output evidence.
    ceiling_inputs = inputs(feed, 3)
    ceiling_inputs["equipment_selection"]["required_discharge_ac_kw"] = 50
    bounded = assess_equipment(ceiling_inputs, basis)
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
        == "unresolved"
    )
    ceiling_inputs["equipment_selection"]["operating_mode"] = "backup"
    assert not any(
        c["id"] == "grid_output_ceiling"
        for c in assess_equipment(ceiling_inputs, basis)["checks"]
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
    plant_demand = {"equipment_plant_requirements": plan, "equipment_plant_setup": raw}
    whole = search_plant(
        plant_demand, basis, EquipmentSearchLimits(work_budget=100), store, lambda: None
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
    partial = search_plant(
        plant_demand, basis, EquipmentSearchLimits(work_budget=8), store, lambda: None
    )
    assert partial["completion"] == "budget_exhausted"
    assert len(partial["candidates"]) == 1 and partial["work_used"] == 8
    # A large declared layout must pay for the expanded selection before a
    # result entry is created. This is an execution bound, not a device limit.
    large_plan = copy.deepcopy(plan)
    large_raw = copy.deepcopy(raw)
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
    weighted = search_plant(
        {
            "equipment_plant_requirements": large_plan,
            "equipment_plant_setup": large_raw,
        },
        basis,
        EquipmentSearchLimits(work_budget=400),
        store,
        lambda: None,
    )
    assert weighted["completion"] == "budget_exhausted"
    assert weighted["candidates"] == [] and weighted["work_used"] <= 400


def test_roof_string_plan_uses_cited_woo_facts_and_keeps_design_gaps(
    feed: dict, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One wiring representative: series voltage, parallel current and stale IDs."""
    from linker_engine.planning.geometry import panel_poses, read_geometry
    from linker_engine.planning.pv_string_assessment import assess_pv_strings
    from linker_engine.planning.pv_string_inputs import PvStringPlan
    from linker_engine.planning.woo_module import module_template

    from .test_pv_generation import geometry

    reference = feed["overlay"][0]
    proof = {"module": module_template(reference), "electrical_product": reference}
    layout = geometry()
    layout["module_specs"] = [{**proof["module"]["specification"], "id": "module"}]
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
    result = assess_pv_strings(value, basis)
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
    assessment = assess_equipment(value, basis)
    assert assessment["pv_electrical"] == result
    assert assessment["overall_status"] != "satisfied"
    operating_value = copy.deepcopy(value)
    operating_value["pv_string_plan"]["operating_conditions"] = {
        "irradiance_w_m2": 1000,
        "hot_cell_c": 60,
        "cold_cell_c": 20,
        "source_note": "Explicit synthetic uniform operating cases, not site extremes",
    }
    operating = assess_equipment(operating_value, basis)["pv_electrical"]["operating"]
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
    assert model["diagnostics"]["noct"]["cell_c_interval"] == [41, 45]
    assert model["diagnostics"]["noct"]["declared_p_mp_w"] == 352
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
            "equipment": assess_equipment(operating_value, basis),
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
    invalid_conditions["pv_string_plan"]["operating_conditions"]["hot_cell_c"] = 100
    outside = assess_equipment(invalid_conditions, basis)["pv_electrical"]["operating"]
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
    from linker_engine.planning.equipment_facts import compile_facts

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
            pv_iv_model.derive_iv_model(compile_facts(reference))["status"]
            == "unavailable"
        )
    without_target = copy.deepcopy(value)
    without_target["equipment_selection"]["pv_dc_kw"] = None
    no_target_assessment = assess_equipment(without_target, basis)
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
    unknown = assess_pv_strings(saved, basis)
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
        assess_pv_strings(saved, basis)
