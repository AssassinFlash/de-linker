"""Manufacturer terminal identities are scoped to one end and one source."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import jsonschema
import pytest
from conftest import publication_manifest
from fastapi.testclient import TestClient

from linker_engine.engine import Engine
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.equipment_service import EquipmentService
from linker_engine.planning.errors import (
    InvalidInput,
    ProductEvidenceChanged,
    ProjectInputContractRequired,
)
from linker_engine.planning.execution_registry import service_registry
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_takeoff import product_basis, route_takeoff
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductProvider, ProductSources
from linker_engine.planning.project_input_contracts import (
    SUPPORTED_INPUT_CONTRACTS,
    TERMINAL_INPUT_CONTRACT,
    require_input_contract,
)
from linker_engine.planning.project_input_floor import (
    check_project_input_contracts,
    read_project_input_floor,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.report_sources import ReportInputsChanged
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_energy_kernel import TOLERANCE
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_equipment import inputs as equipment_inputs
from .test_installation_electrical import circuit_fixture
from .test_private_http import TOKEN, headers

ROOT = Path(__file__).resolve().parents[4]
URL = "https://de-linker.com/wp-content/uploads/terminal-test-document.pdf"


def real_projection(pid: int) -> FixtureObject:
    """Local Woo intake projection with an isolated synthetic publication proof."""
    intake = json.loads(
        (ROOT / "tools/migrate/548-installation-facts.json").read_text()
    )
    product = intake["products"][str(pid)]
    items = copy.deepcopy(product["items"])
    documents = {}
    for item in items:
        source = item["source"]
        source["url"] = URL
        documents[source["document_id"]] = {
            "document_id": source["document_id"],
            "document_revision": source["document_revision"],
            "blob_sha256": source["blob_sha256"],
            "product_ids": [pid],
            "url": URL,
            "title": "Fixture for exact recorded manufacturer source",
            "type": "manual",
            "lang": "en",
        }
    return {
        "id": pid,
        "canonical_product_id": pid,
        "product_revision": product["product_revision"],
        "model": product["model"],
        "brand": "GoodWe",
        "documents": list(documents.values()),
        "installation_facts": {"status": "documented", "items": items},
    }


def sample(pid: int = 1956) -> tuple[FixtureObject, FixtureObject]:
    inputs, basis = circuit_fixture()
    product = real_projection(pid)
    installation = inputs["installation"]
    circuit = installation["circuits"][0]
    circuit["kind"] = "control"
    circuit.pop("operating_conditions")
    circuit["communication_use"] = "external_communication"
    installation["cable_runs"] = [
        {
            "id": "run_0",
            "name": "One physical route",
            "circuit_id": "circuit",
            "route_id": "route_0",
            "construction": "unspecified",
        }
    ]
    for instance in installation["instances"]:
        instance.update(product_id=pid, product_revision=product["product_revision"])
    basis["products"] = [product]
    basis["publication"]["products"] = [
        {"product_id": pid, "product_revision": product["product_revision"]}
    ]
    basis["publication"]["documents"] = [
        {
            "product_id": pid,
            "document_id": doc["document_id"],
            "document_revision": doc["document_revision"],
        }
        for doc in product["documents"]
    ]
    basis.pop("cable_references")
    return inputs, basis


def bind(
    inputs: FixtureObject, basis: FixtureObject, index: int, fact_id: str, terminal: str
) -> None:
    instance = inputs["installation"]["instances"][index]
    fact = next(
        f
        for f in basis["products"][0]["installation_facts"]["items"]
        if f["id"] == fact_id
    )
    instance["ports"][0]["terminal_binding"] = {
        "instance_id": instance["id"],
        "product_id": instance["product_id"],
        "product_revision": instance["product_revision"],
        "fact_id": fact_id,
        "terminal": terminal,
        "document_id": fact["source"]["document_id"],
        "document_revision": fact["source"]["document_revision"],
    }


def endpoints(inputs: FixtureObject, basis: FixtureObject) -> list[FixtureObject]:
    output = json_object(route_takeoff(inputs, basis))
    result = output["terminal_assessment"]
    assert result["scope"] == "manufacturer_one_end_mapping"
    assert result["qualified"] is False and output["qualified"] is False
    return cast(list[FixtureObject], result["circuits"][0]["endpoints"])


@pytest.mark.parametrize("pid", [1956, 1957, 1958])
@pytest.mark.parametrize("internal_terminal", ["COM2", "COM3", "COM4"])
def test_real_intake_maps_both_ends_without_qualifying_circuit(
    pid: int, internal_terminal: str
) -> None:
    inputs, basis = sample(pid)
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    bind(inputs, basis, 1, "internal-communication-terminals", internal_terminal)
    start, end = endpoints(inputs, basis)
    assert [start["status"], end["status"]] == ["documented", "documented"]
    assert [start["domain_status"], end["domain_status"]] == ["matches", "matches"]
    assert [start["use_status"], end["use_status"]] == ["matches", "mismatch"]
    assert [start["fact"]["source"]["page"], end["fact"]["source"]["page"]] == [23, 23]
    assert start["binding"]["instance_id"] != end["binding"]["instance_id"]
    inputs["installation"]["circuits"][0]["communication_use"] = (
        "internal_communication"
    )
    assert [row["use_status"] for row in endpoints(inputs, basis)] == [
        "mismatch",
        "matches",
    ]
    inputs["installation"]["circuits"][0]["communication_use"] = None
    assert all(row["use_status"] == "not_declared" for row in endpoints(inputs, basis))


@pytest.mark.parametrize("pid", [1954, 1955])
def test_generic_terminal_map_never_guesses_communication_use(pid: int) -> None:
    inputs, basis = sample(pid)
    bind(inputs, basis, 0, "bms-communication-terminals", "COM")
    start, end = endpoints(inputs, basis)
    assert start["status"] == "documented" and start["use_status"] == "not_documented"
    assert end["status"] == "not_bound" and end["fact"] is None


def test_product_fact_document_and_instance_mismatches_are_never_promoted() -> None:
    original, source = sample()
    bind(original, source, 0, "external-communication-terminal", "COM1")
    cases = []
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    inputs["installation"]["instances"][0]["ports"][0]["terminal_binding"][
        "instance_id"
    ] = "load"
    cases.append((inputs, basis, "instance_mismatch"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    basis["products"] = []
    cases.append((inputs, basis, "product_unavailable"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    basis["products"][0]["product_revision"] = "a" * 64
    cases.append((inputs, basis, "product_revision_changed"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    basis["products"][0]["installation_facts"]["items"] = []
    cases.append((inputs, basis, "fact_unavailable"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    inputs["installation"]["instances"][0]["ports"][0]["terminal_binding"][
        "document_revision"
    ] = "a" * 64
    cases.append((inputs, basis, "document_changed"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    inputs["installation"]["instances"][0]["ports"][0]["terminal_binding"][
        "terminal"
    ] = "COM2"
    cases.append((inputs, basis, "terminal_unavailable"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    basis["publication"]["documents"] = []
    cases.append((inputs, basis, "invalid_evidence"))
    inputs, basis = copy.deepcopy(original), copy.deepcopy(source)
    basis["products"][0]["documents"][0]["blob_sha256"] = "f" * 64
    cases.append((inputs, basis, "invalid_evidence"))
    for inputs, basis, expected in cases:
        row = endpoints(inputs, basis)[0]
        assert row["status"] == expected
        assert row["fact"] is None and row["use_status"] == "not_assessed"


def test_scoped_binding_confirms_current_manifest_document_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, basis = sample()
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    basis["schema_version"] = 1
    basis["publication"].update(
        engineering_contract=2, compatibility_revision="fixture-compatibility"
    )
    selected = json_object(
        product_basis(InstallationInputs.read(inputs["installation"]), basis)
    )
    expected = basis["products"][0]["documents"][0]["blob_sha256"]
    assert selected["publication"]["documents"][0]["blob_sha256"] == expected
    manifest = {
        "compatibility_revision": "fixture-compatibility",
        "products": [
            {
                **basis["publication"]["products"][0],
                "ready": {"engineering": True},
            }
        ],
        "documents": copy.deepcopy(basis["products"][0]["documents"]),
    }
    publication = Publication({})
    monkeypatch.setattr(publication, "read", lambda: manifest)
    shared = cast(
        ProductProvider,
        SimpleNamespace(engine=object(), publication=publication, version="fixture"),
    )
    sources = ProductSources(lambda: shared)
    sources.confirm_basis(selected, require_reference=False)
    manifest["documents"][0]["blob_sha256"] = "f" * 64
    with pytest.raises(ProductEvidenceChanged):
        sources.confirm_basis(selected, require_reference=False)


def test_stale_terminal_device_cannot_close_existing_pv_string_link() -> None:
    inputs, basis = sample()
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    plan = inputs["installation"]
    plan["instances"][1].update(product_id=None, product_revision=None)
    plan["circuits"][0].update(kind="pv_dc", communication_use=None)
    plan["pv_string_links"] = [{"string_id": "string_a", "circuit_id": "circuit"}]
    inputs["pv_string_plan"] = {
        "schema_version": 1,
        "inverter_product_id": 1956,
        "minimum_ambient_c": None,
        "temperature_source": None,
        "strings": [
            {"id": "string_a", "mppt": 1, "input": 1, "module_ids": ["module_a"]}
        ],
    }
    original = json_object(route_takeoff(inputs, basis))
    assert original["pv_string_reconciliation"]["rows"][0]["status"] == "linked"
    basis["products"][0]["product_revision"] = "a" * 64
    stale = json_object(route_takeoff(inputs, basis))
    assert (
        stale["terminal_assessment"]["circuits"][0]["endpoints"][0]["status"]
        == "product_revision_changed"
    )
    assert (
        stale["pv_string_reconciliation"]["rows"][0]["status"]
        == "inverter_endpoint_unresolved"
    )
    assert stale["pv_string_reconciliation"]["rows"][0]["closure"]["recorded"] is False


def test_new_and_edited_bindings_require_current_proof_but_old_stale_binding_survives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, basis = sample()
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    source = ProductSources(lambda: None)  # type: ignore[arg-type,return-value]
    monkeypatch.setattr(source, "equipment_basis", lambda **_: copy.deepcopy(basis))
    monkeypatch.setattr(source, "confirm_basis", lambda *_args, **_kwargs: None)
    source.check_installation(cast(Object, inputs), {})
    stale = copy.deepcopy(basis)
    stale["publication"]["documents"] = []
    monkeypatch.setattr(source, "equipment_basis", lambda **_: copy.deepcopy(stale))
    with pytest.raises(ProductEvidenceChanged):
        source.check_installation(cast(Object, inputs), {})
    changed = copy.deepcopy(inputs)
    changed["installation"]["routes"][0]["name"] = "Edited route"
    source.check_installation(cast(Object, changed), cast(Object, inputs))
    changed["installation"]["instances"][0]["ports"][0]["terminal_binding"][
        "instance_id"
    ] = "load"
    with pytest.raises(InvalidInput):
        source.check_installation(cast(Object, changed), cast(Object, inputs))


def test_legacy_bytes_and_complete_input_contract() -> None:
    inputs, _ = sample()
    plan = inputs["installation"]
    plan["circuits"][0].pop("communication_use")
    # The established RoutePoint model normalizes numbers to floating point.
    for instance in plan["instances"]:
        for port in instance["ports"]:
            for key in ("east_m", "north_m", "height_m"):
                port["position"][key] = float(port["position"][key])
    for route in plan["routes"]:
        route["extra_length_m"] = float(route["extra_length_m"])
        for point in route["points"]:
            for key in ("east_m", "north_m", "height_m"):
                point[key] = float(point[key])
    legacy = InstallationInputs.read(plan)
    assert legacy.project_document() == plan
    assert digest(encode(legacy.project_document())) == digest(encode(plan))
    plan["instances"][0]["ports"][0]["terminal_binding"] = None
    for token in (
        None,
        *(t for t in SUPPORTED_INPUT_CONTRACTS if t != TERMINAL_INPUT_CONTRACT),
    ):
        for before, after in ((None, inputs), (inputs, inputs), (inputs, {})):
            with pytest.raises(ProjectInputContractRequired):
                require_input_contract(before, after, token)
    require_input_contract(None, inputs, TERMINAL_INPUT_CONTRACT)
    invalid = copy.deepcopy(inputs)
    invalid["installation"]["circuits"][0].update(
        kind="ac", communication_use="internal_communication"
    )
    with pytest.raises(InvalidInput):
        InstallationInputs.read(invalid["installation"])


def test_scoped_report_source_and_retained_floor_are_frozen(
    workspace: Workspace, owner: Actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, basis = sample()
    bind(inputs, basis, 0, "external-communication-terminal", "COM1")
    # A bound endpoint is sufficient even before a communication cable or a
    # circuit-use declaration has been recorded.
    inputs["installation"]["circuits"][0].pop("communication_use")
    inputs["installation"]["cable_runs"] = []
    source = ProductSources(lambda: None)  # type: ignore[arg-type,return-value]
    monkeypatch.setattr(source, "equipment_basis", lambda **_: copy.deepcopy(basis))
    monkeypatch.setattr(source, "confirm_basis", lambda *_args, **_kwargs: None)
    project = workspace.create(
        owner,
        "Terminal fixture",
        cast(Object, inputs),
        key="terminal",
        input_contract=TERMINAL_INPUT_CONTRACT,
    )
    options = ReportOptions.read(
        {
            "locale": "en",
            "energy_run_id": None,
            "pv_run_id": None,
            "equipment_run_id": None,
            "logo": None,
            "include_installation": True,
        }
    )
    context = ReportKernel(workspace, source).context(
        owner, project.id, project.revision, options
    )
    frozen = json_object(workspace.blobs.object(context.assets["report.source"]))
    row = frozen["installation"]["terminal_assessment"]["circuits"][0]["endpoints"][0]
    assert row["status"] == "documented" and row["fact"]["source"]["page"] == 23
    assert frozen["installation"]["cables"] == []
    assert all(line["quantity"] is None for line in frozen["materials"]["lines"])
    basis["products"] = []
    assert workspace.blobs.object(context.assets["report.source"]) == frozen
    floor = read_project_input_floor(workspace.database.path.parent)
    assert TERMINAL_INPUT_CONTRACT in floor["required_input_contracts"]
    with pytest.raises(ValueError, match="does not support"):
        check_project_input_contracts(
            workspace.database.path.parent,
            [x for x in SUPPORTED_INPUT_CONTRACTS if x != TERMINAL_INPUT_CONTRACT],
        )


def test_current_woo_to_owned_save_preview_and_report(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The publication and product document are synthetic, not a live readback."""
    feed = copy.deepcopy(request.getfixturevalue("equipment_feed"))
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    product = next(p for p in feed["products"] if p["id"] == 1956)
    document = product["documents"][0]
    facts = real_projection(1956)["installation_facts"]
    for fact in facts["items"]:
        fact["source"].update(
            product_id=product["id"],
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
    inputs, _ = sample()
    for device in inputs["installation"]["instances"]:
        device["product_revision"] = product["product_revision"]
    bind(inputs, {"products": [product]}, 0, "external-communication-terminal", "COM1")
    bind(inputs, {"products": [product]}, 1, "internal-communication-terminals", "COM2")
    energy = EnergyService(
        workspace, EnergyKernel(workspace, TOLERANCE, max_intervals=10), max_attempts=1
    )
    app = create_private_app(
        workspace,
        energy,
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 10_000, 10, 32),
        product_provider=lambda: shared,
    )
    with TestClient(app) as client:
        current = client.post(
            "/products/current", json={"schema_version": 1}, headers=headers(owner)
        )
        assert current.status_code == 200, current.text
        projected = next(row for row in current.json()["products"] if row["id"] == 1956)
        assert projected["installation_facts"] == facts
        created = client.post(
            "/projects/create",
            json={
                "schema_version": 1,
                "title": "Synthetic terminal project",
                "inputs": inputs,
                "key": "terminal-http",
                "input_contract": TERMINAL_INPUT_CONTRACT,
            },
            headers=headers(owner),
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]
        body = {
            "schema_version": 1,
            "project_id": project_id,
            "expected_revision": 1,
            "geometry": inputs["geometry"],
            "installation": inputs["installation"],
            "bind_geometry": False,
        }
        reviewed = client.post(
            "/installation/review", json=body, headers=headers(owner)
        )
        assert reviewed.status_code == 200, reviewed.text
        rows = reviewed.json()["terminal_assessment"]["circuits"][0]["endpoints"]
        assert [row["use_status"] for row in rows] == ["matches", "mismatch"]
        options = ReportOptions.read(
            {
                "locale": "en",
                "energy_run_id": None,
                "pv_run_id": None,
                "equipment_run_id": None,
                "logo": None,
                "include_installation": True,
            }
        )
        context = ReportKernel(workspace, sources).context(
            owner, project_id, 1, options
        )
        frozen = json_object(workspace.blobs.object(context.assets["report.source"]))
        frozen_rows = frozen["installation"]["terminal_assessment"]["circuits"][0][
            "endpoints"
        ]
        assert frozen_rows == rows
        scope = json_object(workspace.blobs.object(frozen["woo_bases"]["installation"]))
        bound = next(
            d
            for d in scope["publication"]["documents"]
            if d["document_id"] == document["document_id"]
        )
        assert bound["blob_sha256"] == document["blob_sha256"]
        current_doc = next(
            d
            for d in manifest["documents"]
            if d["document_id"] == document["document_id"]
        )
        current_doc["blob_sha256"] = "f" * 64
        rejected = client.post(
            "/installation/review", json=body, headers=headers(owner)
        )
        assert rejected.status_code == 409, rejected.text


def test_combined_report_requires_assessed_revision_and_supports_terminal_only(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = copy.deepcopy(request.getfixturevalue("equipment_feed"))
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for row in manifest["products"]:
            row["ready"]["engineering"] = True
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    shared = cast(
        ProductProvider,
        SimpleNamespace(
            engine=replace(engine, products=Products.from_feed(feed)),
            publication=Publication(feed),
            version="synthetic-loaded-generation",
        ),
    )
    sources = ProductSources(lambda: shared)
    inputs, _ = sample()
    inputs.update(equipment_inputs(feed, 3))
    plan = inputs["installation"]
    revision_b = next(
        p["product_revision"] for p in feed["products"] if p["id"] == 4107
    )
    plan["instances"][0].update(product_id=4107, product_revision=revision_b)
    plan["instances"][1].update(product_id=None, product_revision=None)
    plan["cable_runs"] = []
    project = workspace.create(
        owner,
        "Terminal-only equipment scope",
        cast(Object, inputs),
        key="combined-scope",
        input_contract=TERMINAL_INPUT_CONTRACT,
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
        "terminal-scope",
        {"evaluate": registry},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
        routing=registry.routing(8),
    )
    checked = equipment.evaluate(owner, project.id, 1, key="equipment")
    assert worker.run_once()
    completed = workspace.run(owner, checked.id)
    assert completed.state == "succeeded", completed.error
    assessment = json_object(json_object(completed.result)["assessment"])
    selected = next(
        p for p in assessment["selected_products"] if p["product_id"] == 4107
    )
    assert selected["product_revision"] == revision_b
    assert (
        next(
            p
            for p in assessment["provisional_bill_of_materials"]
            if p["product_id"] == 4107
        )["quantity"]
        == 1
    )
    options = ReportOptions.read(
        {
            "locale": "en",
            "energy_run_id": None,
            "pv_run_id": None,
            "equipment_run_id": checked.id,
            "logo": None,
            "include_installation": True,
        }
    )
    generated = reports.evaluate(owner, project.id, 1, options, key="combined-report")
    assert worker.run_once()
    report_run = workspace.run(owner, generated.id)
    assert report_run.state == "succeeded", report_run.error
    original = copy.deepcopy(json_object(report_run.result))
    frozen = json_object(
        workspace.blobs.object(original["dependencies"]["report_source"])
    )
    assert frozen["installation"]["cables"] == []
    assert (
        frozen["installation"]["terminal_assessment"]["circuits"][0]["endpoints"][0][
            "status"
        ]
        == "not_bound"
    )
    terminal_lines = [
        line
        for line in frozen["materials"]["lines"]
        if line["basis"] == "manufacturer_one_end_mapping"
    ]
    assert len(terminal_lines) == 1 and terminal_lines[0]["quantity"] is None
    assert not any(
        line["basis"] == "installation_route_takeoff_v1"
        for line in frozen["materials"]["lines"]
    )

    # The same selected product and count with an older physical instance
    # revision must not be merged into this equipment assessment.
    stale = copy.deepcopy(inputs)
    stale["installation"]["instances"][0]["product_revision"] = "a" * 64
    changed = workspace.revise(
        owner,
        project.id,
        1,
        cast(Object, stale),
        key="stale",
        input_contract=TERMINAL_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged, match="assessment scope"):
        reports.kernel.context(owner, project.id, changed.revision, options)

    route_only = reports.kernel.context(
        owner,
        project.id,
        changed.revision,
        options.model_copy(update={"equipment_run_id": None}),
    )
    route_source = json_object(
        workspace.blobs.object(route_only.assets["report.source"])
    )
    assert (
        route_source["installation"]["instances"][0]["product_status"]
        == "product_revision_changed"
    )
    assert route_source["installation"]["cables"] == []
    assert all(line["quantity"] is None for line in route_source["materials"]["lines"])
    assert workspace.run(owner, generated.id).result == original
    assert workspace.blobs.object(original["dependencies"]["report_source"]) == frozen

    # The source assessment permits one converter, not two physical copies.
    extra = copy.deepcopy(inputs)
    extra["installation"]["instances"][1].update(
        product_id=4107, product_revision=revision_b
    )
    changed = workspace.revise(
        owner,
        project.id,
        changed.revision,
        cast(Object, extra),
        key="extra",
        input_contract=TERMINAL_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged, match="assessment scope"):
        reports.kernel.context(owner, project.id, changed.revision, options)

    other = copy.deepcopy(inputs)
    selected_other = next(p for p in feed["products"] if p["id"] == 1956)
    other["installation"]["instances"][0].update(
        product_id=1956, product_revision=selected_other["product_revision"]
    )
    changed = workspace.revise(
        owner,
        project.id,
        changed.revision,
        cast(Object, other),
        key="other",
        input_contract=TERMINAL_INPUT_CONTRACT,
    )
    with pytest.raises(ReportInputsChanged, match="assessment scope"):
        reports.kernel.context(owner, project.id, changed.revision, options)

    # With neither a cable, a terminal declaration nor a string link, the
    # original routing admission remains closed.
    legacy = copy.deepcopy(inputs)
    legacy["installation"]["circuits"][0].pop("communication_use")
    changed = workspace.revise(
        owner,
        project.id,
        changed.revision,
        cast(Object, legacy),
        key="no-terminal-or-cable",
        input_contract=TERMINAL_INPUT_CONTRACT,
    )
    with pytest.raises(InvalidInput, match="physical cable"):
        reports.kernel.context(
            owner,
            project.id,
            changed.revision,
            options.model_copy(update={"equipment_run_id": None}),
        )


def test_feed_schema_restricts_structured_usage_to_communication_maps() -> None:
    schema = json.loads((ROOT / "services/engine/schemas/feed.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/installationFact", "$defs": schema["$defs"]}
    )
    fact = next(
        f
        for f in real_projection(1956)["installation_facts"]["items"]
        if f["id"] == "external-communication-terminal"
    )
    assert validator.is_valid(fact)
    for field, value in (
        ("basis", "manufacturer_included_per_sales_unit"),
        ("terminal_domain", "ac"),
        ("terminals", []),
    ):
        edited = copy.deepcopy(fact)
        (edited if field == "basis" else edited["specification"])[field] = value
        assert not validator.is_valid(edited)
