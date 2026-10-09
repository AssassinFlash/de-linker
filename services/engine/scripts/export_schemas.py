"""Write the JSON Schemas of the API's request bodies.

The configurator validates its forms against these schemas, so each input rule
(ranges, required fields, the PLZ pattern) is written once, in the Pydantic
models of `linker_engine.models`. Two copies are written: `schemas/api/` for
readers of the engine, and the configurator's `src/configurator/schema/`, which
the front-end build bundles. tests/test_schemas.py fails when either is stale.

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
TARGETS = (
    ENGINE / "schemas" / "api",
    ENGINE.parents[1] / "plugins" / "linker-tools" / "src" / "configurator" / "schema",
)
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
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        for name, text in documents().items():
            (target / name).write_text(text)
        print(f"wrote {len(MODELS)} schemas to {target}")


if __name__ == "__main__":
    main()
