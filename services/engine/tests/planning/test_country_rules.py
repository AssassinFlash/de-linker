"""Country rule results are conditional on explicit, versioned project facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning import plant_assessment
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.country_rules import CountryRuleInputs, review_country_rules
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_inputs import EquipmentSelection
from linker_engine.planning.errors import ProjectInputContractRequired
from linker_engine.planning.grid_connection import country_assessment
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.project_input_contracts import (
    ENGINEERING_V10_INPUT_CONTRACT,
    MATERIALS_INPUT_CONTRACT,
    require_input_contract,
)
from linker_engine.planning.project_input_floor import read_project_input_floor
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_equipment import feed as feed
from .test_equipment import inputs, plant_inputs
from .test_grid_connection import declared


def rule_input(basis: str, **changes: Any) -> Object:
    value: Object = {
        "schema_version": 1,
        "basis": basis,
        "rule_date": "2026-11-01",
        "power_kw": None,
        "connection_voltage_kv": None,
        "de_before_control_test": None,
        "de_remuneration": None,
        "de_plug_in_exception": None,
        "fr_enedis_full_self_consumption": None,
    }
    value.update(changes)
    return value


def outcomes(review: Object | None) -> dict[str, str]:
    assert review is not None
    return {
        str(check["id"]): str(check["outcome"])
        for check in cast(list[Object], review["checks"])
    }


@pytest.mark.parametrize(
    ("power", "voltage", "expected"),
    [
        (0.79, 0.4, "below_range"),
        (0.8, 0.4, "type_a"),
        (999.9, 20.0, "type_a"),
        (1000.0, 20.0, "type_b"),
        (18000.0, 20.0, "type_c"),
        (75000.0, 20.0, "type_d"),
        (0.8, 110.0, "type_d"),
    ],
)
def test_fr_generation_uses_declared_pmax_and_connection_voltage(
    power: float, voltage: float, expected: str
) -> None:
    result = review_country_rules(
        "FR",
        rule_input("fr_generation_pmax", power_kw=power, connection_voltage_kv=voltage),
    )
    assert outcomes(result)["fr_generation_type"] == expected
    assert result is not None
    assert result["country_code"] == "FR"
    assert cast(list[Object], result["sources"])[0]["clause"] == "Article 35"
    assert cast(list[Object], result["checks"])[0]["status"] in {
        "conditional",
        "unresolved",
    }


@pytest.mark.parametrize(
    ("power", "expected_type", "expected_lfsm"),
    [
        (0.79, "below_range", "below_range"),
        (0.8, "type_a", "boundary_not_established"),
        (0.81, "type_a", "statism_2_percent"),
        (999.9, "type_a", "statism_2_percent"),
        (1000.0, "type_b", "statism_1_percent"),
        (50000.0, "type_c", "statism_1_percent"),
        (60000.0, "type_d", "statism_1_percent"),
    ],
)
def test_nl_storage_unit_thresholds_and_lfsm_boundary_are_distinct(
    power: float, expected_type: str, expected_lfsm: str
) -> None:
    result = outcomes(
        review_country_rules("NL", rule_input("nl_storage_max_active", power_kw=power))
    )
    assert result == {
        "nl_storage_type": expected_type,
        "nl_storage_lfsm": expected_lfsm,
    }


@pytest.mark.parametrize(
    ("power", "remuneration", "plug", "control", "export"),
    [
        (150.0, "other", None, "fetch_and_reduce", "no_60_percent_in_9_2_2b_3"),
        (25.0, "other", None, "reduce", "not_in_tariff"),
        (25.0, "feed_in_or_tenant", None, "reduce", "sixty_percent_conditionally"),
        (
            12.0,
            "feed_in_or_tenant",
            None,
            "no_requirement_in_9_2_1_2",
            "sixty_percent_conditionally",
        ),
        (2.0, "feed_in_or_tenant", True, "no_requirement_in_9_2_1_2", "exempt_plug_in"),
        (2.0, "feed_in_or_tenant", None, "no_requirement_in_9_2_1_2", "missing_inputs"),
    ],
)
def test_de_pre_test_control_and_export_are_conditional(
    power: float, remuneration: str, plug: bool | None, control: str, export: str
) -> None:
    result = outcomes(
        review_country_rules(
            "DE",
            rule_input(
                "de_pv_installed",
                power_kw=power,
                de_before_control_test=True,
                de_remuneration=remuneration,
                de_plug_in_exception=plug,
            ),
        )
    )
    assert result == {"de_eeg_control": control, "de_eeg_export": export}


def test_missing_inputs_versions_and_unrelated_countries_do_not_infer() -> None:
    assert (
        outcomes(review_country_rules("FR", rule_input("fr_generation_pmax")))[
            "fr_generation_type"
        ]
        == "missing_inputs"
    )
    assert (
        outcomes(
            review_country_rules(
                "FR",
                rule_input(
                    "fr_generation_pmax",
                    rule_date="2026-11-02",
                    power_kw=10,
                    connection_voltage_kv=0.4,
                ),
            )
        )["fr_generation_type"]
        == "outside_version"
    )
    assert review_country_rules("FR", rule_input("nl_storage_max_active")) is None
    assert review_country_rules("AT", rule_input("fr_generation_pmax")) is None
    original = declared(country="AT", complete=True)
    newer = {**original, "country_rule_inputs": rule_input("fr_generation_pmax")}
    assert country_assessment(newer) == country_assessment(original)


def test_enedis_scope_requires_explicit_operator_and_complete_self_use() -> None:
    inputs = rule_input("fr_generation_pmax", fr_enedis_full_self_consumption=True)
    expected = {
        "fr_generation_type": "missing_inputs",
        "fr_enedis_declaration": "enedis_declare_cacsi",
        "fr_enedis_certification": "enedis_consuel_or_attestation",
    }
    result = review_country_rules("FR", inputs, operator=" Enedis ")
    assert outcomes(result) == expected
    assert result is not None and len(cast(list[Object], result["sources"])) == 2
    assert outcomes(review_country_rules("FR", inputs, operator="Other")) == {
        "fr_generation_type": "missing_inputs"
    }
    assert outcomes(review_country_rules("FR", inputs)) == {
        "fr_generation_type": "missing_inputs"
    }
    assert outcomes(
        review_country_rules(
            "FR",
            rule_input("fr_generation_pmax", fr_enedis_full_self_consumption=False),
            operator="Enedis",
        )
    ) == {"fr_generation_type": "missing_inputs"}


def test_invalid_or_approval_bearing_rule_input_is_rejected() -> None:
    for changes in (
        {"power_kw": -1},
        {"power_kw": float("inf")},
        {"rule_date": "2026-02-30"},
        {"de_before_control_test": "yes"},
        {"approved": True},
    ):
        with pytest.raises(ValueError):
            CountryRuleInputs.model_validate(rule_input("de_pv_installed", **changes))


def test_browser_schema_matches_the_authoritative_input_model() -> None:
    root = Path(__file__).resolve().parents[4]
    schema = root / "apps/planner/src/contracts/country-rules.schema.json"
    assert json.loads(schema.read_text()) == CountryRuleInputs.model_json_schema()


def test_rule_input_is_revision_bound_and_requires_an_aware_writer(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    initial = declared(country="FR", complete=True)
    values: Object = {
        **initial,
        "country_rule_inputs": rule_input(
            "fr_generation_pmax", power_kw=11, connection_voltage_kv=0.4
        ),
    }
    for before, after in ((None, values), (values, values), (values, initial)):
        with pytest.raises(ProjectInputContractRequired):
            require_input_contract(before, after, MATERIALS_INPUT_CONTRACT)
        require_input_contract(before, after, ENGINEERING_V10_INPUT_CONTRACT)
    project = workspace.create(
        owner,
        "Rules",
        values,
        key="create",
        input_contract=ENGINEERING_V10_INPUT_CONTRACT,
    )
    revision_one = country_assessment(project.inputs)
    run = workspace.evaluate(
        owner, project.id, 1, context, key="rule-run", max_attempts=1
    )
    assert workspace.pinned_inputs(run.manifest) == values
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    jobs.complete(lease, {"assessment": revision_one})
    updated = {
        **values,
        "country_rule_inputs": rule_input(
            "fr_generation_pmax", power_kw=1200, connection_voltage_kv=20
        ),
    }
    workspace.revise(
        owner,
        project.id,
        1,
        updated,
        key="revise",
        input_contract=ENGINEERING_V10_INPUT_CONTRACT,
    )
    assert outcomes(cast(Object, revision_one["rule_review"])) == {
        "fr_generation_type": "type_a"
    }
    assert (
        country_assessment(workspace.get(owner, project.id, revision=1).inputs)
        == revision_one
    )
    assert outcomes(cast(Object, country_assessment(updated)["rule_review"])) == {
        "fr_generation_type": "type_b"
    }
    assert revision_one["connection_permission"] == "not_established"
    assert workspace.run(owner, run.id).result == {"assessment": revision_one}
    floor = read_project_input_floor(workspace.database.path.parent)
    assert ENGINEERING_V10_INPUT_CONTRACT in floor["required_input_contracts"]


def test_plant_reuses_electrical_cache_but_not_previous_rule_review(
    feed: FixtureObject, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = {**inputs(feed, 3), **declared(country="FR", complete=True)}
    selected = EquipmentSelection.read(base["equipment_selection"]).model_dump(
        mode="json"
    )
    stale = assess_equipment(base, feed)
    rules = rule_input("fr_generation_pmax", power_kw=11, connection_voltage_kv=0.4)
    current = {**base, "country_rule_inputs": rules}
    expected = assess_equipment(current, feed)["country_assessment"]

    def unexpected_recalculation(*args: Any, **kwargs: Any) -> Object:
        raise AssertionError("the electrical unit result should be reused")

    monkeypatch.setattr(plant_assessment, "assess_equipment", unexpected_recalculation)
    result = plant_assessment.assess_plant(
        {
            **declared(country="FR", complete=True),
            "country_rule_inputs": rules,
            "equipment_plant": plant_inputs(feed),
        },
        feed,
        unit_assessments={digest(encode(selected)): stale},
    )
    assert result["country_assessment"] == expected
    for row in cast(list[Object], result["systems"]):
        assert json_object(row["assessment"])["country_assessment"] == expected
