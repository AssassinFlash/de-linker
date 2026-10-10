"""The exported request schemas match the models the API validates with."""

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE / "scripts"))

import export_schemas  # noqa: E402


def test_exported_schemas_are_current() -> None:
    for target in export_schemas.TARGETS:
        for name, text in export_schemas.documents().items():
            path = target / name
            assert path.exists(), f"run scripts/export_schemas.py ({path} is missing)"
            assert path.read_text() == text, (
                f"run scripts/export_schemas.py ({path} is stale)"
            )
