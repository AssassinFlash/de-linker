from pathlib import Path

import pytest

from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.errors import NotFound
from linker_engine.planning.panel_migration import migrate
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_pv_generation import geometry


def test_migration_preserves_roof_positions_count_ownership_and_original_revision(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    workspace = Workspace(root)
    owner = Actor("user", "retained-customer")
    roof = geometry()
    module = roof["module_specs"][0]
    source = {
        "kind": "datasheet",
        "note": "Historical maker Panel-X",
        "url": "https://example.org/panel-x.pdf",
        "page": 2,
        "document_sha256": "a" * 64,
        "woo": {
            "product_id": 180,
            "product_revision": "a" * 64,
            "reference_input_id": "old_panel_x",
        },
    }
    module.update(model=source["note"], source=source)
    inputs: FixtureObject = {
        "geometry": roof,
        "pv_generation": {
            "modules": [
                {
                    "module_spec_id": module["id"],
                    "source": source,
                    "gamma_pdc_per_c": -0.003,
                }
            ]
        },
    }
    original = workspace.create(owner, "Customer roof", inputs, key="create")
    assert migrate(root, apply=False)["current_projects"] == 1
    assert workspace.get(owner, original.id).revision == 1
    assert migrate(root, apply=True)["current_projects"] == 1
    current = workspace.get(owner, original.id)
    assert current.revision == 2
    updated = json_object(current.inputs["geometry"])
    assert updated["roofs"] == roof["roofs"] and updated["arrays"] == roof["arrays"]
    (projected,) = updated["module_specs"]
    assert (
        projected["id"] == module["id"]
        and projected["stc_power_w"] == module["stc_power_w"]
    )
    assert projected["gamma_pdc_per_c"] == -0.003
    assert "Historical maker" not in str(current.inputs)
    assert original.input_sha256 == digest(
        encode(workspace.get(owner, original.id, revision=1).inputs)
    )
    assert migrate(root, apply=True)["current_projects"] == 0
    with pytest.raises(NotFound):
        workspace.get(Actor("user", "somebody-else"), original.id)
