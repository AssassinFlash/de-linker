"""Export the actual versioned workspace energy contracts for browser validation.

Run from services/engine: uv run python scripts/export_planner_schemas.py
No browser defaults or independent numerical constraints are added.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linker_engine.models import Report
from linker_engine.planning.dc_energy_parameters import (
    DcLossScenario,
    DcPreparedParameters,
)
from linker_engine.planning.energy_inputs import BatteryParameters, EnergyInputs
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.weather_inputs import WeatherAcquisitionInputs

TARGET = Path(__file__).resolve().parents[3] / "apps" / "planner" / "src" / "contracts"


def closed_document(
    value: dict[str, Any], *, serialized_output: bool = False
) -> dict[str, Any]:
    """Keep the existing browser's closed presentation documents generated."""
    for child in value.values():
        if isinstance(child, dict):
            closed_document(child, serialized_output=serialized_output)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, dict):
                    closed_document(item, serialized_output=serialized_output)
    if value.get("type") == "object" and "properties" in value:
        value.setdefault("additionalProperties", False)
        if serialized_output:
            # A serialized report includes model defaults; the existing UI
            # requires them and does not insert missing arrays/nulls. Only the
            # new layout hint stays optional for immutable older report tables.
            value["required"] = [
                key
                for key in value["properties"]
                if not (value.get("title") == "ReportTable" and key == "column_weights")
            ]
    return value


def documents() -> dict[str, str]:
    return {
        f"{name}.schema.json": json.dumps(
            {
                **closed_document(
                    model.model_json_schema(), serialized_output=model is Report
                ),
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
        for name, model in (
            ("battery-parameters", BatteryParameters),
            ("dc-loss-scenario", DcLossScenario),
            ("dc-prepared-parameters", DcPreparedParameters),
            ("energy-inputs", EnergyInputs),
            ("pv-generation", PvGenerationParameters),
            ("weather-acquisition", WeatherAcquisitionInputs),
            ("planning-report", Report),
            ("planning-report-options", ReportOptions),
            ("installation", InstallationInputs),
        )
    }


if __name__ == "__main__":
    for name, text in documents().items():
        (TARGET / name).write_text(text)
