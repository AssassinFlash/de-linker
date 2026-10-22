"""Published browser schemas are the actual strict service documents."""

from __future__ import annotations

import json
from pathlib import Path

from linker_engine.planning.http_documents import CsvImport
from linker_engine.planning.profile_selections import ProfileSelections


def test_profile_contracts_match_the_published_browser_schemas() -> None:
    root = Path(__file__).resolve().parents[4] / "apps/planner/src/contracts"
    for name, model in (
        ("profile-import", CsvImport),
        ("profile-selections", ProfileSelections),
    ):
        assert (
            json.loads((root / f"{name}.schema.json").read_text())
            == model.model_json_schema()
        )
