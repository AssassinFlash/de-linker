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
from linker_engine.planning.dc_plant_inputs import DcPlantEnergyInputs
from linker_engine.planning.direct_beam_inputs import DirectBeamTaskInputs
from linker_engine.planning.energy_inputs import BatteryParameters, EnergyInputs
from linker_engine.planning.equipment_condition_inputs import EquipmentConditionInputs
from linker_engine.planning.equipment_plant import EquipmentPlant
from linker_engine.planning.geometric_pv_inputs import (
    GeometricPvInputs,
    GeometricPvLimits,
)
from linker_engine.planning.installation_inputs import InstallationInputs
from linker_engine.planning.plant_energy_inputs import PlantEnergyInputs
from linker_engine.planning.plant_search_plan import PlantSearchPlan
from linker_engine.planning.project_input_contracts import SUPPORTED_INPUT_CONTRACTS
from linker_engine.planning.pv_parameters import PvGenerationParameters
from linker_engine.planning.pvgis_reference_inputs import PvgisReferenceInputs
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.weather_inputs import WeatherAcquisitionInputs

TARGET = Path(__file__).resolve().parents[3] / "apps" / "planner" / "src" / "contracts"


def closed_document(
    value: dict[str, Any], *, serialized_output: bool = False
) -> dict[str, Any]:
    """Keep the existing browser's closed presentation documents generated."""
    # Pydantic emits an OpenAPI annotation; the browser uses strict JSON Schema
    # and the generated oneOf/const constraints already enforce this union.
    value.pop("discriminator", None)
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
    result = {
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
            ("direct-beam", DirectBeamTaskInputs),
            ("geometric-pv", GeometricPvInputs),
            ("geometric-pv-limits", GeometricPvLimits),
            ("pvgis-roof-reference", PvgisReferenceInputs),
            ("planning-report", Report),
            ("planning-report-options", ReportOptions),
            ("installation", InstallationInputs),
            ("equipment-plant", EquipmentPlant),
            ("equipment-condition-inputs", EquipmentConditionInputs),
            ("plant-energy-inputs", PlantEnergyInputs),
            ("dc-plant-energy-inputs", DcPlantEnergyInputs),
            ("plant-search-plan", PlantSearchPlan),
        )
    }
    result["project-input-contracts.json"] = (
        json.dumps(
            {
                "schema_version": 1,
                "project_input_contracts": list(SUPPORTED_INPUT_CONTRACTS),
            },
            indent=2,
        )
        + "\n"
    )
    return result


if __name__ == "__main__":
    for name, text in documents().items():
        (TARGET / name).write_text(text)
        if name == "project-input-contracts.json":
            (TARGET.parents[3] / "plugins/linker-tools" / name).write_text(text)
