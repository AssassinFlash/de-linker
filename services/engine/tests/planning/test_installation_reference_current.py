"""Manufacturer table comparison is independent of impedance and approval."""

from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace
from typing import cast

import pytest
from conftest import publication_manifest

from linker_engine.engine import Engine
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.installation_reference_current import (
    reference_current_confirmation_context,
)
from linker_engine.planning.installation_takeoff import route_takeoff
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    REFERENCE_CURRENT_INPUT_CONTRACT,
    TERMINAL_INPUT_CONTRACT,
    require_input_contract,
)
from linker_engine.planning.records import Actor
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_sources import report_sources
from linker_engine.planning.workspace import Workspace
from linker_engine.products import Products
from linker_engine.publication import Publication

from .conftest import FixtureObject, json_object
from .test_equipment import feed as equipment_feed  # noqa: F401
from .test_installation_electrical import circuit_fixture

LAYINGS = (
    "single_in_air",
    "single_on_surface",
    "two_touching_on_surface",
)
IDS = (
    "single-in-air-60c-120c",
    "single-on-surface-60c-120c",
    "two-touching-on-surface-60c-120c",
)


def confirm(inputs: FixtureObject) -> None:
    """Record a fresh context for each explicitly declared physical run."""
    plan = InstallationInputs.read(inputs["installation"])
    for run, dumped in zip(
        plan.cable_runs, inputs["installation"]["cable_runs"], strict=True
    ):
        if run.reference_current_installation is not None:
            dumped["reference_current_installation"]["confirmation_context"] = (
                reference_current_confirmation_context(plan, run)
            )


def prepared(
    laying_index: int = 0,
) -> tuple[FixtureObject, FixtureObject]:
    inputs, basis = circuit_fixture()
    for reference, values in zip(
        basis["cable_references"], ((55, 52, 44), (70, 67, 57)), strict=True
    ):
        source = copy.deepcopy(reference["cable_facts"]["source"])
        source["page"] = 2
        reference["cable_facts"]["reference_current_ratings"] = [
            {
                "id": identifier,
                "laying": laying,
                "ambient_temperature_c": 60,
                "rated_conductor_temperature_c": 120,
                "current_a": value,
                "source": source,
            }
            for identifier, laying, value in zip(IDS, LAYINGS, values, strict=True)
        ]
        reference.pop("product_revision")
        reference.pop("reference_revision")
        reference["product_revision"] = digest(encode(reference))
        reference["reference_revision"] = reference["product_revision"]
    runs = inputs["installation"]["cable_runs"]
    for index, run in enumerate(runs):
        ref = basis["cable_references"][index]
        run["conductor"]["cable_reference"]["product_revision"] = ref[
            "product_revision"
        ]
        run["reference_current_installation"] = {
            "rating_id": IDS[laying_index],
            "laying": LAYINGS[laying_index],
            "ambient_temperature_c": 60,
            "touching_run_id": f"run_{1 - index}" if laying_index == 2 else None,
            "current_path": "single_unbranched",
            "conditions_confirmed": True,
            "source_note": "Private project conditions",
        }
    if laying_index == 2:
        # The manufacturer's two touching entries do not document mixed sizes.
        runs[1]["conductor"] = copy.deepcopy(runs[0]["conductor"])
        runs[1]["route_id"] = runs[0]["route_id"]
    confirm(inputs)
    return inputs, basis


def rows(inputs: FixtureObject, basis: FixtureObject) -> list[FixtureObject]:
    return cast(
        list[FixtureObject],
        json_object(route_takeoff(inputs, basis))["electrical"][
            "reference_current_segments"
        ],
    )


@pytest.mark.parametrize(
    ("index", "expected"), [(0, [55, 70]), (1, [52, 67]), (2, [44, 44])]
)
def test_exact_table_rows_and_separate_comparison(
    index: int, expected: list[int]
) -> None:
    inputs, basis = prepared(index)
    result = rows(inputs, basis)
    assert [r["run_id"] for r in result] == ["run_0", "run_1"]
    assert [r["reference_current_a"] for r in result] == expected
    assert all(r["status"] == "below_reference" for r in result)
    assert all(r["project_current_a"] == 20 and not r["qualified"] for r in result)
    assert all(r["rating"]["source"]["page"] == 2 for r in result)
    assert all(r["rating"]["rated_conductor_temperature_c"] == 120 for r in result)
    assert all(r["installation"]["ambient_temperature_c"] == 60 for r in result)
    assert (
        inputs["installation"]["circuits"][0]["operating_conditions"][0][
            "conductor_temperature_c"
        ]
        == 20
    )
    condition = inputs["installation"]["circuits"][0]["operating_conditions"][0]
    condition["current_a"] = expected[0]
    assert rows(inputs, basis)[0]["status"] == "equal_reference"
    condition["current_a"] = expected[0] + 0.01
    assert rows(inputs, basis)[0]["status"] == "above_reference"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("missing_condition", "operating_condition_missing"),
        ("battery", "circuit_kind_not_supported"),
        ("ac_method", "condition_method_not_supported"),
        ("parallel", "current_path_not_single_pair"),
        ("unknown_path", "current_path_not_confirmed"),
        ("unconfirmed", "installation_conditions_not_confirmed"),
        ("touching", "touching_pair_mismatch"),
        ("revision", "cable_reference_unavailable"),
        ("section", "cable_specification_mismatch"),
        ("missing_rating", "reference_rating_unavailable"),
        ("ambient", "reference_rating_conditions_mismatch"),
        ("rating_temperature", "reference_rating_conditions_mismatch"),
        ("source", "reference_source_unavailable"),
    ],
)
def test_incomplete_or_changed_evidence_never_compares(
    change: str, reason: str
) -> None:
    inputs, basis = prepared()
    plan = inputs["installation"]
    run = plan["cable_runs"][0]
    decl = run["reference_current_installation"]
    if change == "missing_condition":
        plan["circuits"][0]["operating_conditions"] = []
    elif change == "battery":
        plan["circuits"][0]["kind"] = "battery_dc"
    elif change == "ac_method":
        plan["circuits"][0]["operating_conditions"][0]["method"] = "ac_two_wire"
    elif change == "parallel":
        duplicate = copy.deepcopy(run)
        duplicate["id"] = "parallel"
        plan["cable_runs"].append(duplicate)
    elif change == "unknown_path":
        plan["cable_runs"][1]["reference_current_installation"]["current_path"] = (
            "unknown"
        )
    elif change == "unconfirmed":
        decl["conditions_confirmed"] = False
    elif change == "touching":
        decl["touching_run_id"] = "run_1"
    elif change == "revision":
        run["conductor"]["cable_reference"]["product_revision"] = "a" * 64
    elif change == "section":
        run["conductor"]["cross_section_mm2"] = 10
    elif change == "missing_rating":
        decl["rating_id"] = "not-published"
    elif change == "ambient":
        decl["ambient_temperature_c"] = 59
    elif change == "rating_temperature":
        basis["cable_references"][0]["cable_facts"]["reference_current_ratings"][0][
            "rated_conductor_temperature_c"
        ] = 90
    else:
        basis["cable_references"][0]["cable_facts"]["reference_current_ratings"][0][
            "source"
        ]["blob_sha256"] = "a" * 64
    result = rows(inputs, basis)[0]
    assert result["status"] == "not_evaluated" and reason in result["reasons"]
    assert result["project_current_a"] is None and result["reference_current_a"] is None
    assert not result["qualified"]


def test_touching_requires_reciprocal_same_route_and_selected_product() -> None:
    inputs, basis = prepared(2)
    runs = inputs["installation"]["cable_runs"]
    assert [r["reference_current_a"] for r in rows(inputs, basis)] == [44, 44]
    runs[1]["reference_current_installation"]["touching_run_id"] = None
    assert all("touching_pair_mismatch" in r["reasons"] for r in rows(inputs, basis))
    runs[1]["reference_current_installation"]["touching_run_id"] = "run_0"
    runs[1]["route_id"] = "route_1"
    assert all("touching_pair_mismatch" in r["reasons"] for r in rows(inputs, basis))
    runs[1]["route_id"] = "route_0"
    reference = basis["cable_references"][1]
    runs[1]["conductor"]["cross_section_mm2"] = 6
    runs[1]["conductor"]["cable_reference"] = {
        "product_id": reference["canonical_product_id"],
        "product_revision": reference["product_revision"],
    }
    assert all("touching_pair_mismatch" in r["reasons"] for r in rows(inputs, basis))
    runs[0]["conductor"] = copy.deepcopy(runs[1]["conductor"])
    confirm(inputs)
    assert [r["reference_current_a"] for r in rows(inputs, basis)] == [57, 57]


@pytest.mark.parametrize("peer_context", ["missing", "stale", "one_reconfirmed"])
def test_touching_requires_both_current_confirmation_contexts(
    peer_context: str,
) -> None:
    inputs, basis = prepared(2)
    peer = inputs["installation"]["cable_runs"][1]
    declaration = peer["reference_current_installation"]
    if peer_context == "missing":
        declaration["confirmation_context"] = None
    elif peer_context == "stale":
        declaration["confirmation_context"]["declaration"]["rating_id"] = "old-rating"
    else:
        inputs["installation"]["routes"][0]["points"][1]["east_m"] = 11
        plan = InstallationInputs.read(inputs["installation"])
        first = plan.cable_runs[0]
        inputs["installation"]["cable_runs"][0]["reference_current_installation"][
            "confirmation_context"
        ] = reference_current_confirmation_context(plan, first)
    result = rows(inputs, basis)
    assert all(row["status"] == "not_evaluated" for row in result)
    assert "touching_pair_mismatch" in result[0]["reasons"]
    assert "confirmation_context_changed" in result[1]["reasons"]
    confirm(inputs)
    assert [row["status"] for row in rows(inputs, basis)] == [
        "below_reference",
        "below_reference",
    ]


@pytest.mark.parametrize(
    "change",
    [
        "route_points",
        "extra_length",
        "route_id",
        "circuit_id",
        "endpoint",
        "endpoint_position",
        "product",
        "roles",
        "selected_table",
    ],
)
def test_confirmation_follows_the_physical_context_and_can_be_reconfirmed(
    change: str,
) -> None:
    inputs, basis = prepared()
    plan = inputs["installation"]
    original = copy.deepcopy(plan["cable_runs"][0]["reference_current_installation"])
    if change == "route_points":
        plan["routes"][0]["points"][1]["east_m"] = 11
    elif change == "extra_length":
        plan["routes"][0]["extra_length_m"] = 21
    elif change == "route_id":
        plan["cable_runs"][0]["route_id"] = "route_1"
    elif change == "circuit_id":
        circuit = copy.deepcopy(plan["circuits"][0])
        circuit["id"] = "moved_circuit"
        plan["circuits"].append(circuit)
        for run in plan["cable_runs"]:
            run["circuit_id"] = "moved_circuit"
    elif change == "endpoint":
        circuit = plan["circuits"][0]
        circuit["start"], circuit["end"] = circuit["end"], circuit["start"]
    elif change == "endpoint_position":
        plan["instances"][0]["ports"][0]["position"]["height_m"] = 2
    elif change == "roles":
        runs = plan["cable_runs"]
        runs[0]["core_roles"], runs[1]["core_roles"] = (
            runs[1]["core_roles"],
            runs[0]["core_roles"],
        )
    elif change == "selected_table":
        for run in plan["cable_runs"]:
            run["reference_current_installation"].update(
                laying=LAYINGS[1], rating_id=IDS[1]
            )
    else:
        plan["instances"][0]["product_id"] = 123
        plan["instances"][0]["product_revision"] = "f" * 64
        basis["products"].append(
            {
                "canonical_product_id": 123,
                "product_revision": "f" * 64,
                "model": "Synthetic endpoint",
                "brand": "Synthetic",
            }
        )
    # Previewing unsaved changes already invalidates the old attestation.
    result = rows(inputs, basis)[0]
    assert result["status"] == "not_evaluated"
    assert "confirmation_context_changed" in result["reasons"]
    if change != "selected_table":
        assert plan["cable_runs"][0]["reference_current_installation"] == original
    else:
        assert (
            plan["cable_runs"][0]["reference_current_installation"][
                "confirmation_context"
            ]
            == original["confirmation_context"]
        )
    # Reconfirmation is an ordinary change to the same project document.
    confirm(inputs)
    result = rows(inputs, basis)[0]
    assert "confirmation_context_changed" not in result["reasons"]
    assert result["status"] == "below_reference"


@pytest.mark.parametrize(
    "change", ["partner_cable", "partner_route", "partner_endpoint"]
)
def test_touching_pair_confirmation_includes_both_physical_runs(change: str) -> None:
    inputs, basis = prepared(2)
    plan = inputs["installation"]
    if change == "partner_cable":
        plan["cable_runs"][1]["conductor"]["cross_section_mm2"] = 10
    elif change == "partner_route":
        plan["cable_runs"][1]["route_id"] = "route_1"
    else:
        plan["instances"][0]["ports"][0]["position"]["north_m"] = 4
    result = rows(inputs, basis)
    assert all("confirmation_context_changed" in row["reasons"] for row in result)
    assert all(row["status"] == "not_evaluated" for row in result)


def test_unrelated_names_notes_and_roof_changes_keep_confirmation() -> None:
    inputs, basis = prepared(2)
    plan = inputs["installation"]
    plan["routes"][0].update(name="Renamed route", extra_length_note="Edited note")
    plan["circuits"][0]["name"] = "Renamed circuit"
    plan["instances"][0]["name"] = "Renamed device"
    plan["instances"][0]["ports"][0]["name"] = "Renamed port"
    plan["cable_runs"][0]["name"] = "Renamed cable"
    plan["cable_runs"][0]["conductor"]["source_note"] = "Edited cable note"
    plan["cable_runs"][0]["reference_current_installation"]["source_note"] = (
        "Edited note"
    )
    inputs["geometry"]["sources"][0]["note"] = "Edited roof source note"
    assert all(row["status"] == "below_reference" for row in rows(inputs, basis))


def test_absent_confirmation_keeps_legacy_bytes_but_requires_reconfirmation() -> None:
    inputs, basis = prepared()
    for run in inputs["installation"]["cable_runs"]:
        run["reference_current_installation"].pop("confirmation_context")
    original = copy.deepcopy(inputs["installation"])
    assert InstallationInputs.read(original).project_document() == original
    result = rows(inputs, basis)
    assert all(row["status"] == "not_evaluated" for row in result)
    assert all("confirmation_context_changed" in row["reasons"] for row in result)
    assert all("confirmation_context" not in row["installation"] for row in result)
    inputs["installation"]["cable_runs"][0]["reference_current_installation"][
        "confirmation_context"
    ] = None
    assert (
        InstallationInputs.read(inputs["installation"]).project_document() == original
    )
    assert "confirmation_context" not in rows(inputs, basis)[0]["installation"]
    confirm(inputs)
    assert all(row["status"] == "below_reference" for row in rows(inputs, basis))


def test_impedance_and_reference_comparisons_are_independent_and_old_bytes_stable() -> (
    None
):
    inputs, basis = prepared()
    condition = inputs["installation"]["circuits"][0]["operating_conditions"][0]
    condition["conductor_temperature_c"] = 70
    electrical = json_object(route_takeoff(inputs, basis))["electrical"]
    assert electrical["circuits"][0]["conditions"][0]["voltage_drop_v"] is None
    assert [
        r["reference_current_a"] for r in electrical["reference_current_segments"]
    ] == [
        55,
        70,
    ]
    condition["conductor_temperature_c"] = 20
    for ref in basis["cable_references"]:
        ref["cable_facts"].pop("reference_current_ratings")
    electrical = json_object(route_takeoff(inputs, basis))["electrical"]
    assert electrical["circuits"][0]["conditions"][0][
        "voltage_drop_v"
    ] == pytest.approx(5.088)
    assert all(
        r["status"] == "not_evaluated" for r in electrical["reference_current_segments"]
    )
    old_inputs, old_basis = circuit_fixture()
    original = copy.deepcopy(old_inputs["installation"])
    assert InstallationInputs.read(original).project_document() == original
    assert (
        "reference_current_segments"
        not in json_object(route_takeoff(old_inputs, old_basis))["electrical"]
    )
    with pytest.raises(ProjectInputContractRequired):
        require_input_contract(inputs, {}, TERMINAL_INPUT_CONTRACT)
    require_input_contract(inputs, {}, REFERENCE_CURRENT_INPUT_CONTRACT)


def test_publication_rejects_unbound_rating_document(
    engine: Engine, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, basis = prepared()
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    feed["overlay"].extend(basis["cable_references"])
    engine = replace(engine, products=Products.from_feed(feed))

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
        engine=engine, publication=Publication(feed), version="fixture"
    )
    sources = ProductSources(lambda: shared)
    assert len(json_object(sources.current())["cable_references"]) == 2
    # A citation to a changed blob cannot enter the prepared Woo intersection.
    feed["overlay"][-1]["cable_facts"]["reference_current_ratings"][0]["source"][
        "blob_sha256"
    ] = "a" * 64
    assert len(json_object(sources.current())["cable_references"]) == 1


def test_saved_review_and_frozen_source_keep_the_same_cited_rows(
    engine: Engine,
    workspace: Workspace,
    owner: Actor,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, basis = prepared(1)
    feed = request.getfixturevalue("equipment_feed")
    feed.update(figure_projection_version=2, compatibility_origin="woocommerce")
    feed["overlay"].extend(basis["cable_references"])

    def current(self: Publication) -> FixtureObject:
        manifest = publication_manifest(self.feed)
        for item in manifest["products"]:
            item["ready"]["engineering"] = True
            if item["product_id"] in {9101, 9102}:
                item.update(
                    engineering_role="reference_cable",
                    engineering_id=f"fixture_cable_{item['product_id']}",
                )
        return manifest

    monkeypatch.setattr(Publication, "read", current)
    shared = SimpleNamespace(
        engine=replace(engine, products=Products.from_feed(feed)),
        publication=Publication(feed),
        version="fixture",
    )
    sources = ProductSources(lambda: shared)
    sources.check_installation(inputs, {})
    project = workspace.create(
        owner,
        "Reference current fixture",
        inputs,
        key="reference-current-fixture",
        input_contract=REFERENCE_CURRENT_INPUT_CONTRACT,
    )
    saved = workspace.get(owner, project.id, revision=project.revision)
    reviewed = rows(
        json_object(saved.inputs),
        json_object(sources.equipment_basis(include_cables=True)),
    )
    assert [r["reference_current_a"] for r in reviewed] == [52, 67]
    options = ReportOptions(
        locale="en",
        energy_run_id=None,
        pv_run_id=None,
        equipment_run_id=None,
        logo=None,
        include_installation=True,
    )
    source = report_sources(workspace, sources, owner, saved, options)
    frozen_sha = workspace.blobs.put_object(source)
    frozen = json_object(workspace.blobs.object(frozen_sha))
    assert (
        frozen["installation"]["electrical"]["reference_current_segments"] == reviewed
    )
    assert frozen["installation"]["prepared_inputs"] == inputs["installation"]
    assert (
        frozen["installation"]["electrical"]["reference_current_segments"][0]["rating"][
            "source"
        ]["document_revision"]
        == basis["cable_references"][0]["documents"][0]["document_revision"]
    )
    feed["overlay"][-1]["cable_facts"]["reference_current_ratings"][0]["source"][
        "blob_sha256"
    ] = "a" * 64
    renewed = rows(
        json_object(saved.inputs),
        json_object(sources.equipment_basis(include_cables=True)),
    )
    assert renewed[0]["reference_current_a"] == 52
    assert renewed[1]["status"] == "not_evaluated"
    assert "cable_reference_unavailable" in renewed[1]["reasons"]
    retained = json_object(workspace.blobs.object(frozen_sha))
    assert (
        retained["installation"]["electrical"]["reference_current_segments"] == reviewed
    )


@pytest.mark.parametrize("laying", [0, 2])
def test_another_circuit_cannot_claim_contact_with_an_isolated_segment_or_pair(
    laying: int,
) -> None:
    inputs, basis = prepared(laying)
    plan = inputs["installation"]
    foreign_circuit = copy.deepcopy(plan["circuits"][0])
    foreign_circuit["id"] = "other_circuit"
    plan["circuits"].append(foreign_circuit)
    foreign = copy.deepcopy(plan["cable_runs"][0])
    foreign.update(id="third_run", circuit_id="other_circuit")
    foreign["reference_current_installation"].update(
        laying="two_touching_on_surface", rating_id=IDS[2], touching_run_id="run_0"
    )
    plan["cable_runs"].append(foreign)
    result = rows(inputs, basis)
    expected_ids = {"run_0", "run_1"} if laying == 2 else {"run_0"}
    affected = [row for row in result if row["run_id"] in expected_ids]
    assert {row["run_id"] for row in affected} == expected_ids
    assert all(
        row["status"] == "not_evaluated" and "touching_pair_mismatch" in row["reasons"]
        for row in affected
    )
