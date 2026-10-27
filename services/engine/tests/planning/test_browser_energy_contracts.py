"""Shared positive/negative fixtures use the real browser and server contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from linker_engine.planning.energy_inputs import BatteryParameters, EnergyInputs

ENGINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ENGINE / "scripts"))

import export_planner_schemas  # noqa: E402

FIXTURES = ENGINE.parents[1] / "apps" / "planner" / "tests" / "fixtures"


def test_workspace_schemas_are_the_actual_backend_exports() -> None:
    for name, expected in export_planner_schemas.documents().items():
        assert (export_planner_schemas.TARGET / name).read_text() == expected


def test_shared_browser_energy_fixtures() -> None:
    scenario = json.loads((FIXTURES / "energy-scenario.json").read_text())
    parameters = scenario["battery_binding"]["parameters"]
    inputs = json.loads((FIXTURES / "energy-inputs.json").read_text())
    assert BatteryParameters.model_validate(parameters).eta_charge == 0.9
    assert EnergyInputs.model_validate(inputs).initial_inventory.pv_kwh == 0
    cases = json.loads((FIXTURES / "energy-invalid.json").read_text())
    for case in cases:
        model, original = (
            (BatteryParameters, parameters)
            if case["target"] == "parameters"
            else (EnergyInputs, inputs)
        )
        changed = {**original, **case["set"]}
        for key in case["delete"]:
            del changed[key]
        with pytest.raises(ValidationError):
            model.model_validate(changed)
