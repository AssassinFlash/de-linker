"""Shared intake schema and browser/PHP/Python numeric boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from linker_engine.planning.brief import PlanningBrief, brief_schema, validate_new_brief
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.http_documents import ProjectCreate


def incomplete_brief() -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_use": None,
        "system_scope": None,
        "site": {
            "country_code": None,
            "location_label": "",
            "latitude": None,
            "longitude": None,
            "coordinate_basis": "not_provided",
            "timezone": None,
        },
        "annual_load": {"kwh": None, "basis": None, "source_note": ""},
        "project_note": "",
    }


def test_partial_brief_keeps_missing_information_as_null() -> None:
    brief = incomplete_brief()
    assert PlanningBrief.model_validate(brief).model_dump(mode="json") == brief
    assert ProjectCreate.model_validate(
        {
            "schema_version": 1,
            "title": "Incomplete project",
            "key": "fixture",
            "inputs": {"brief": brief},
        }
    ).inputs == {"brief": brief}


def test_schema_is_the_published_frontend_contract() -> None:
    root = Path(__file__).resolve().parents[4]
    path = root / "apps/planner/src/contracts/brief.schema.json"
    assert json.loads(path.read_text()) == brief_schema()


@pytest.mark.parametrize("value", ["10", True, -1, float("inf")])
def test_annual_load_never_coerces_or_fills_missing_facts(value: object) -> None:
    brief = incomplete_brief()
    brief["annual_load"] = {"kwh": value, "basis": None, "source_note": ""}
    with pytest.raises(ValidationError):
        PlanningBrief.model_validate(brief)


def test_timezone_and_country_are_not_selected_by_interface_language() -> None:
    brief = incomplete_brief()
    site = dict(brief["site"])  # type: ignore[call-overload]
    site.update(
        country_code="NO", timezone="Europe/Oslo", latitude=59.91, longitude=10.75
    )
    brief["site"] = site
    assert PlanningBrief.model_validate(brief).site.timezone == "Europe/Oslo"
    validate_new_brief({"brief": brief})
    site["timezone"] = "Europe/Imaginary"
    with pytest.raises(InvalidInput, match="known IANA"):
        validate_new_brief({"brief": brief})


@pytest.mark.parametrize(
    "name", ["posixrules", "localtime", "right/UTC", "posix/Europe/Oslo"]
)
def test_host_tzif_aliases_are_not_project_iana_names(name: str) -> None:
    brief = incomplete_brief()
    site = dict(brief["site"])  # type: ignore[call-overload]
    site["timezone"] = name
    brief["site"] = site
    with pytest.raises(InvalidInput, match="known IANA"):
        validate_new_brief({"brief": brief})


@pytest.mark.parametrize(
    "value", [2**53, -(2**53), 9223372036854775809, 10**400, 1e100]
)
def test_unsupported_command_numbers_are_rejected_before_storage(
    value: int | float,
) -> None:
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate(
            {
                "schema_version": 1,
                "title": "Numeric fixture",
                "key": "fixture",
                "inputs": {"nested": [{"n": value}]},
            }
        )


@pytest.mark.parametrize("value", [2**53 - 1, -(2**53 - 1), 0.125, 1e-100])
def test_supported_command_numbers_remain_unchanged(value: int | float) -> None:
    inputs = {"n": value}
    command = ProjectCreate.model_validate(
        {
            "schema_version": 1,
            "title": "Numeric fixture",
            "key": "fixture",
            "inputs": inputs,
        }
    )
    assert command.inputs == inputs and type(command.inputs["n"]) is type(value)
