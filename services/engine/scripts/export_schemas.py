"""Write the JSON Schemas of the API's request bodies.

The engine publishes its Pydantic request contracts in schemas/api/.

    uv run python scripts/export_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from linker_engine.models import (
    CommercialInput,
    ReportRequest,
    ResidentialInput,
    RoofPackRequest,
    RoofRequest,
)

ENGINE = Path(__file__).resolve().parents[1]
TARGET = ENGINE / "schemas" / "api"
MODELS: dict[str, type[BaseModel]] = {
    "residential-input": ResidentialInput,
    "commercial-input": CommercialInput,
    "roof-request": RoofRequest,
    "roof-pack-request": RoofPackRequest,
    "report-request": ReportRequest,
}


def documents() -> dict[str, str]:
    return {
        f"{name}.schema.json": json.dumps(
            model.model_json_schema(), ensure_ascii=False, indent="\t"
        )
        + "\n"
        for name, model in MODELS.items()
    }


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, text in documents().items():
        (TARGET / name).write_text(text)
    print(f"wrote {len(MODELS)} schemas to {TARGET}")


if __name__ == "__main__":
    main()
