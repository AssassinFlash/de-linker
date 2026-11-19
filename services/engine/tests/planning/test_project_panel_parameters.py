"""PV layout parameters belong to the project, including when Woo is unavailable."""

import json
from pathlib import Path

from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_materials import project_materials
from linker_engine.planning.report_pv_components import saved_roof_components
from linker_engine.planning.storage import Blobs


def test_layout_and_materials_use_authored_dimensions_without_product_or_temperature(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[4]
    geometry = json.loads((root / "fixtures/planning/geometry-flat.json").read_text())
    module = geometry["module_specs"][0]
    module.update(
        model="PV 415 Wp",
        stc_power_w=415,
        gamma_pdc_per_c=None,
        source={
            "kind": "user_declared",
            "note": "declared_reference — Customer-provided panel parameters.",
            "document_sha256": None,
            "url": None,
            "page": None,
        },
    )

    def offline():
        raise AssertionError("no Woo module lookup for a declared layout")

    products = ProductSources(offline)
    inputs = {"geometry": geometry}
    products.check_project(inputs)
    basis = products.roof_basis(inputs)
    products.confirm_basis(basis)
    parts = saved_roof_components(geometry, offline, Blobs(tmp_path / "blobs"), 4)
    assert parts["status"] == "available"
    (part,) = parts["components"]
    assert part["quantity"] == 5
    assert part["stc_power_w"] == 415
    assert "woo" not in part["source"]
    lines = project_materials(
        {
            "pv_components": parts,
            "project_id": "project",
            "revision": 4,
            "input_sha256": "a" * 64,
        }
    )["lines"]
    assert all(line.get("product_id") is None for line in lines)
    assert lines[0]["quantity"] == part["quantity"]
