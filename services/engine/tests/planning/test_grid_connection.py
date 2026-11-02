"""Grid declarations survive revisions without becoming country approval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning import plant_assessment
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_inputs import EquipmentSelection
from linker_engine.planning.errors import InvalidInput, ProjectInputContractRequired
from linker_engine.planning.grid_connection import GridConnection, country_assessment
from linker_engine.planning.http_documents import ProjectCreate
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.plant_assessment import assess_plant
from linker_engine.planning.project_input_contracts import (
    GRID_CONNECTION_INPUT_CONTRACT,
    SUPPORTED_INPUT_CONTRACTS,
    require_input_contract,
)
from linker_engine.planning.project_input_floor import (
    check_project_input_contracts,
    read_project_input_floor,
)
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_equipment import feed as feed
from .test_equipment import inputs, plant_inputs


def declared(*, country: str | None = "DE", complete: bool = False) -> Object:
    return {
        "brief": {
            "schema_version": 1,
            "project_use": "commercial",
            "system_scope": "new_pv_storage",
            "site": {
                "country_code": country,
                "location_label": "Synthetic grid evidence project",
                "latitude": None,
                "longitude": None,
                "coordinate_basis": "not_provided",
                "timezone": None,
            },
            "annual_load": {"kwh": None, "basis": None, "source_note": ""},
            "project_note": "",
        },
        "grid_connection": {
            "schema_version": 1,
            "dso_name": "Synthetic declared operator" if complete else None,
            "dso_source_url": "https://example.org/operator" if complete else None,
            "voltage_level": "low" if complete else None,
            "tab": {
                "title": "Synthetic declared TAB" if complete else None,
                "source_url": "https://example.org/tab.pdf" if complete else None,
                "edition": "project-declared 2026" if complete else None,
                "date": "2026-11-01" if complete else None,
            },
        },
    }


def test_complete_project_declaration_is_neither_verified_rule_nor_permission() -> None:
    result = country_assessment(declared(complete=True))
    assert result["missing_inputs"] == []
    assert result["status"] == "unresolved"
    assert result["independent_verification"] == "not_assessed"
    assert result["connection_permission"] == "not_established"
    assert result["standard_transition"] == result["numeric_rules"] == "not_assessed"
    checks = {r["id"]: r["status"] for r in cast(list[Object], result["checks"])}
    assert checks == {
        "responsible_dso": "provided",
        "connection_voltage": "provided",
        "applicable_tab": "provided",
        "independent_dso_tab_verification": "unresolved",
        "connection_permission": "unresolved",
    }
    sources = cast(list[Object], result["rule_sources"])
    assert sources[0]["edition"] is None and sources[0]["raw_sha256"] is None
    assert sources[0]["evidence_snapshot_date"] == "2026-10-28"
    assert sources[1]["edition"] == "VDE-AR-N 4110:2023-09"
    assert sources[1]["raw_sha256"] is None
    assert "135" not in json.dumps(result)


@pytest.mark.parametrize("country", ["FR", "NL", None])
def test_other_countries_do_not_inherit_german_sources(country: str | None) -> None:
    values = declared(country=country, complete=True)
    result = country_assessment(values)
    assert result["country_code"] == country
    assert result["rule_sources"] == []
    assert result["reason"] == "country_rules_not_available"
    assert result["status"] == "unresolved"
    assert result["project_facts"] == values["grid_connection"]
    assert ("country_code" in cast(list[str], result["missing_inputs"])) == (
        country is None
    )


def test_missing_fields_are_explicit_and_calendar_date_can_identify_source() -> None:
    values = declared()
    result = country_assessment(values)
    assert result["missing_inputs"] == [
        "dso_name",
        "dso_source_url",
        "voltage_level",
        "tab.source_url",
        "tab.edition_or_date",
    ]
    facts = cast(Object, values["grid_connection"])
    tab = cast(Object, facts["tab"])
    tab.update(source_url="https://example.org/tab", date="2026-10-31")
    result = country_assessment(values)
    checks = cast(list[Object], result["checks"])
    assert checks[2]["status"] == "provided"
    assert "tab.edition_or_date" not in cast(list[str], result["missing_inputs"])


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("voltage_level",), "230V"),
        (("dso_name",), "   "),
        (("dso_source_url",), "javascript:alert(1)"),
        (("dso_source_url",), "https://user:secret@example.org/"),
        (("tab", "source_url"), "file:///tmp/tab.pdf"),
        (("tab", "date"), "2026-02-30"),
        (("approved",), True),
    ],
)
def test_invalid_or_approval_bearing_inputs_are_rejected_at_write_boundary(
    workspace: Workspace, owner: Actor, path: tuple[str, ...], value: Any
) -> None:
    values = declared()
    target = cast(dict[str, Any], values["grid_connection"])
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(InvalidInput):
        workspace.create(
            owner,
            "Invalid grid evidence",
            values,
            key="create",
            input_contract=GRID_CONNECTION_INPUT_CONTRACT,
        )
    assert workspace.projects(owner) == []
    with pytest.raises(ValueError):
        ProjectCreate.model_validate(
            {
                "schema_version": 1,
                "title": "Invalid grid evidence",
                "inputs": values,
                "key": "create",
                "input_contract": GRID_CONNECTION_INPUT_CONTRACT,
            }
        )


def test_old_writers_cannot_add_preserve_or_remove_grid_evidence() -> None:
    values = declared()
    first_grid_writer = SUPPORTED_INPUT_CONTRACTS.index(GRID_CONNECTION_INPUT_CONTRACT)
    for before, after in ((None, values), (values, values), (values, {})):
        for token in (None, *SUPPORTED_INPUT_CONTRACTS[:first_grid_writer]):
            with pytest.raises(ProjectInputContractRequired):
                require_input_contract(before, after, token)
        for token in SUPPORTED_INPUT_CONTRACTS[first_grid_writer:]:
            require_input_contract(before, after, token)


def test_saved_revisions_run_and_input_floor_keep_the_new_contract(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    old = workspace.create(owner, "Grid", {}, key="create")
    old_run = workspace.evaluate(owner, old.id, 1, context, key="old", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(lease, {"assessment": country_assessment({})})
    current = workspace.revise(
        owner,
        old.id,
        1,
        declared(complete=True),
        key="grid",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    with pytest.raises(ProjectInputContractRequired):
        workspace.revise(owner, old.id, 2, {}, key="unaware")
    run = workspace.evaluate(owner, old.id, 2, context, key="new", max_attempts=1)
    assert workspace.pinned_inputs(old_run.manifest) == {}
    before = country_assessment(workspace.pinned_inputs(run.manifest))
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(lease, {"assessment": before})
    workspace.revise(
        owner,
        old.id,
        current.revision,
        declared(country="FR"),
        key="fr",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    assert workspace.run(owner, run.id).result == {"assessment": before}
    assert workspace.get(owner, old.id, revision=2).inputs == declared(complete=True)
    workspace.revise(
        owner,
        old.id,
        3,
        {},
        key="remove-grid",
        input_contract=GRID_CONNECTION_INPUT_CONTRACT,
    )
    assert country_assessment({}) == {
        "status": "unresolved",
        "country_code": None,
        "reason": "versioned_country_rules_required",
    }
    floor = read_project_input_floor(workspace.database.path.parent)
    assert floor["required_input_contracts"] == [GRID_CONNECTION_INPUT_CONTRACT]
    previous = [
        token
        for token in SUPPORTED_INPUT_CONTRACTS
        if token != GRID_CONNECTION_INPUT_CONTRACT
    ]
    with pytest.raises(ValueError, match="does not support retained"):
        check_project_input_contracts(workspace.database.path.parent, previous)
    assert (
        check_project_input_contracts(
            workspace.database.path.parent, list(SUPPORTED_INPUT_CONTRACTS)
        )
        == floor
    )


def test_single_plant_and_reused_unit_assessment_use_this_revision(
    feed: FixtureObject, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = {**inputs(feed, 3), **declared(complete=True)}
    single = assess_equipment(values, feed)
    selection = EquipmentSelection.read(values["equipment_selection"]).model_dump(
        mode="json"
    )
    stale = assess_equipment(inputs(feed, 3), feed)
    cache = {digest(encode(selection)): stale}

    def unexpected_unit_recalculation(*args: Any, **kwargs: Any) -> Object:
        raise AssertionError("the real unit cache must be used")

    monkeypatch.setattr(
        plant_assessment, "assess_equipment", unexpected_unit_recalculation
    )
    plant = assess_plant(
        {**declared(complete=True), "equipment_plant": plant_inputs(feed)},
        feed,
        unit_assessments=cache,
    )
    assert plant["country_assessment"] == single["country_assessment"]
    for row in cast(list[Object], plant["systems"]):
        assert (
            json_object(row["assessment"])["country_assessment"]
            == single["country_assessment"]
        )
    assert "model" not in json_object(stale["country_assessment"])
    assert stale == assess_equipment(inputs(feed, 3), feed)


def test_schema_is_exact_and_shared_contract_declarations_match() -> None:
    root = Path(__file__).resolve().parents[4]
    contract = root / "apps/planner/src/contracts/grid-connection.schema.json"
    assert json.loads(contract.read_text()) == GridConnection.model_json_schema()
    browser = root / "apps/planner/src/contracts/project-input-contracts.json"
    wordpress = root / "plugins/linker-tools/project-input-contracts.json"
    assert browser.read_bytes() == wordpress.read_bytes()
    assert json.loads(browser.read_text())["project_input_contracts"] == list(
        SUPPORTED_INPUT_CONTRACTS
    )
