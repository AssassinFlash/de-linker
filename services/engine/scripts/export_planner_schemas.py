"""Export the actual versioned workspace energy contracts for browser validation.

Run from services/engine: uv run python scripts/export_planner_schemas.py
No browser defaults or independent numerical constraints are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from linker_engine.planning.energy_inputs import BatteryParameters, EnergyInputs
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.weather_inputs import WeatherAcquisitionInputs

TARGET = Path(__file__).resolve().parents[3] / "apps" / "planner" / "src" / "contracts"


def documents() -> dict[str, str]:
    return {
        f"{name}.schema.json": json.dumps(
            {
                **model.model_json_schema(),
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
        for name, model in (
            ("battery-parameters", BatteryParameters),
            ("energy-inputs", EnergyInputs),
            ("pv-generation", PvGenerationParameters),
            ("weather-acquisition", WeatherAcquisitionInputs),
        )
    }


if __name__ == "__main__":
    for name, text in documents().items():
        (TARGET / name).write_text(text)
