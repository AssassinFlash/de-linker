from dataclasses import replace
from types import SimpleNamespace
from typing import Literal, cast

import pytest
from conftest import publication_manifest

from linker_engine.engine import Engine
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import ProductEvidenceChanged
from linker_engine.planning.handoffs import Handoffs
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.partial_equipment import partial_equipment
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_equipment import feed as feed


@pytest.fixture
def products(
    feed: FixtureObject, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> ProductSources:
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    provider = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
    )
    manifest = publication_manifest(feed)
    for row in manifest["products"]:
        row["ready"]["engineering"] = True
    monkeypatch.setattr(Publication, "read", lambda self: manifest)
    return ProductSources(lambda: provider)


BATTERY = {
    "schema_version": 1,
    "inverter_product_id": None,
    "battery_product_id": 2090,
    "modules_per_stack": 3,
    "parallel_stacks": 2,
    "accessory_product_ids": [2092],
}


@pytest.mark.parametrize(
    ("inputs", "locale", "orders", "quantities"),
    [
        ({"equipment_setup": BATTERY}, "en", {2090: 6}, ["6 pc", "—"]),
        (
            {"equipment_setup": {**BATTERY, "parallel_stacks": None}},
            "de",
            {},
            ["—", "—"],
        ),
        ({"equipment_setup": {**BATTERY, "battery_product_id": None}}, "en", {}, ["—"]),
        (
            {
                "equipment_plant_setup": {
                    "schema_version": 1,
                    "requirements": {},
                    "parallel_groups": [],
                    "units": [
                        {
                            "id": "main",
                            "name": "First system",
                            "inputs": {
                                "equipment_setup": {
                                    **BATTERY,
                                    "inverter_product_id": 4107,
                                    "operating_mode": "grid_connected",
                                    "accessory_product_ids": [],
                                    "equipment_use": {
                                        "inverter": "retain",
                                        "battery": "new",
                                    },
                                }
                            },
                        },
                        {
                            "id": "second",
                            "name": "Second system",
                            "inputs": {
                                "equipment_setup": {
                                    **BATTERY,
                                    "accessory_product_ids": [],
                                }
                            },
                        },
                    ],
                },
                "inquiry_quantities": {
                    "2090": {"planned_purchase": 12, "requested": 5}
                },
            },
            "en",
            {2090: 5},
            ["1 pc", "12 pc"],
        ),
    ],
)
def test_partial_selection_freezes_catalog_items_for_the_report_and_inquiry(
    workspace: Workspace,
    owner: Actor,
    products: ProductSources,
    feed: FixtureObject,
    inputs: FixtureObject,
    locale: Literal["en", "de"],
    orders: dict[int, int],
    quantities: list[str],
) -> None:
    project = workspace.create(
        owner,
        "Customer selection",
        inputs,
        key="project",
        input_contract=SUPPORTED_INPUT_CONTRACTS[-1],
    )
    kernel = ReportKernel(workspace, products)
    options = ReportOptions(
        locale=locale,
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    run = ReportService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 1, options, key="report"
    )
    assert Worker(
        Jobs(workspace),
        "partial-report",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    result = json_object(workspace.run(owner, run.id).result)
    assert result["has_draft_items"] is bool(orders)
    assert bool(result.get("has_report_only_handoff")) is (not orders)
    sections = {s["id"]: s for s in result["report"]["sections"]}
    assert "customer-selected-equipment" in sections and "equipment" not in sections
    rows = sections["bom"]["table"]["rows"]
    assert [row[0] for row in rows] == quantities
    expected_products = (
        {2090, 4107}
        if "equipment_plant_setup" in inputs
        else {2090, 2092}
        if inputs["equipment_setup"].get("battery_product_id")
        else {2092}
    )
    assert {row[2] for row in rows} == {
        p["sku"] for p in feed["products"] if p["id"] in expected_products
    }
    snapshot = json_object(
        Handoffs(workspace).prepare(owner, project.id, run.id, 1, key="inquiry")
    )["snapshot"]
    assert {i["product_id"]: i["quantity"] for i in snapshot["items"]} == orders
    assert snapshot["kind"] == (
        "planning_products_v1" if orders else "planning_report_only_v1"
    )
    assert {
        p["product_id"] for p in snapshot["publication"]["products"]
    } == expected_products


def test_unpublished_customer_selection_cannot_enter_a_report(
    workspace: Workspace,
    owner: Actor,
    products: ProductSources,
) -> None:
    project = workspace.create(
        owner,
        "Unavailable device",
        {"equipment_setup": cast(Object, {**BATTERY, "battery_product_id": 999999})},
        key="project",
    )
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
    )
    with pytest.raises(ProductEvidenceChanged):
        ReportKernel(workspace, products).context(owner, project.id, 1, options)


@pytest.mark.parametrize(
    ("plant_mode", "unit_mode", "partial"),
    [("grid_connected", None, False), (None, "grid_connected", True)],
)
def test_plant_readiness_uses_the_shared_operating_mode(
    products: ProductSources,
    plant_mode: str | None,
    unit_mode: str | None,
    partial: bool,
) -> None:
    units = [
        {
            "id": key,
            "inputs": {
                "equipment_setup": {
                    "inverter_product_id": 4107,
                    "operating_mode": mode,
                    "accessory_product_ids": [],
                },
            },
        }
        for key, mode in (("main", "grid_connected"), ("annex", unit_mode))
    ]
    inputs = {
        "equipment_plant_setup": {
            "units": units,
            "requirements": {"operating_mode": plant_mode},
            "parallel_groups": [],
        }
    }
    assert (partial_equipment(cast(Object, inputs), products) is not None) is partial
