"""Real owned bytes/receipts and polygon conversion, without a map/API substitute."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import digest
from linker_engine.planning.errors import Conflict, InvalidInput, NotFound
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_geojson import selected_polygon
from linker_engine.planning.geometry_import import (
    MAX_GEOMETRY_FILE_BYTES,
    GeometryImport,
)
from linker_engine.planning.geometry_import_documents import GeometryImportOptions
from linker_engine.planning.geometry_import_selections import (
    GeometryImports,
    check_geometry_imports,
)
from linker_engine.planning.http_documents import GeometryImportCommand
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

ROOT = Path(__file__).resolve().parents[4]
USER = Actor("user", "geometry-import-owner")
FOREIGN = Actor("user", "geometry-import-foreign")


def options() -> GeometryImportOptions:
    return GeometryImportOptions.model_validate(
        json.loads(
            (ROOT / "fixtures/planning/geometry-import-options.json").read_text()
        )
    )


def source() -> bytes:
    return (ROOT / "fixtures/planning/source-roof-wgs84.geojson").read_bytes()


def test_browser_schemas_and_file_policy_match_the_server() -> None:
    contracts = ROOT / "apps/planner/src/contracts"
    for name, model in [
        ("geometry-import-options", GeometryImportOptions),
        ("geometry-import-command", GeometryImportCommand),
        ("geometry-import-selections", GeometryImports),
    ]:
        assert (
            json.loads((contracts / f"{name}.schema.json").read_text())
            == model.model_json_schema()
        )
    assert (
        json.loads((contracts / "geometry-import-policy.json").read_text())[
            "max_file_bytes"
        ]
        == MAX_GEOMETRY_FILE_BYTES
    )


def test_original_bytes_manifest_opening_slope_and_receipt_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = Workspace(tmp_path)
    project = workspace.create(USER, "Synthetic intake", {}, key="create")
    assets = Assets(workspace)
    intake = GeometryImport(assets)
    content = b" \n" + source() + b"\n "
    asset = intake.prepare(USER, project.id, content, options(), key="source")
    assert assets.content(USER, project.id, asset.id) == content
    prepared = asset.metadata["geometry_import"]
    assert isinstance(prepared, dict)
    assert prepared["original_content_sha256"] == digest(content)
    geometry = read_geometry(prepared["geometry"])
    roof = geometry.roofs[0]
    assert (
        len(roof.boundary_uv) == 4
        and len(roof.holes_uv) == 1
        and len(roof.holes_uv[0]) == 4
    )
    assert geometry.sources[0].reference_sha256 == digest(content)
    assert geometry.sources[0].spatial_precision_m is None
    assert roof.origin_enu[2] == 5
    assert prepared["engineering_status"] == "not_evaluated"
    assert workspace.get(USER, project.id).revision == 1
    assert workspace.get(USER, project.id).inputs == {}
    flat = options().model_copy(
        update={"plane": options().plane.model_copy(update={"v_axis_enu": [0, 1, 0]})}
    )
    flat_asset = intake.prepare(USER, project.id, content, flat, key="flat")
    flat_manifest = flat_asset.metadata["geometry_import"]
    assert isinstance(flat_manifest, dict)
    flat_roof = read_geometry(flat_manifest["geometry"]).roofs[0]
    for actual, expected in zip(roof.boundary_uv, flat_roof.boundary_uv, strict=True):
        assert actual[0] == pytest.approx(expected[0], abs=1e-12)
        assert actual[1] == pytest.approx(expected[1] / 0.8, abs=1e-12)

    def unexpected_transform(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "receipt retry must not recapture a changed conversion runtime"
        )

    monkeypatch.setattr(
        "linker_engine.planning.geometry_import.GeographicBridge", unexpected_transform
    )
    assert intake.prepare(USER, project.id, content, options(), key="source") == asset
    with pytest.raises(Conflict):
        intake.prepare(USER, project.id, content + b" ", options(), key="source")


def test_foreign_writer_and_invalid_source_publish_no_blob(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    project = workspace.create(USER, "Synthetic intake", {}, key="create")
    intake = GeometryImport(Assets(workspace))
    before = set(workspace.blobs.directory.rglob("*"))
    with pytest.raises(NotFound):
        intake.prepare(FOREIGN, project.id, b"bad", options(), key="foreign")
    with pytest.raises(InvalidInput):
        intake.prepare(USER, project.id, b'{"type":{}}', options(), key="bad")
    for feature_id in [float("inf"), "\ud800", 2**54]:
        invalid = json.loads(source())
        invalid["id"] = feature_id
        with pytest.raises(InvalidInput):
            intake.prepare(
                USER, project.id, json.dumps(invalid).encode(), options(), key="bad-id"
            )
    assert set(workspace.blobs.directory.rglob("*")) == before


@pytest.mark.parametrize(
    "content",
    [
        b'{"type":"Polygon","type":"Feature"}',
        b'{"type":"Polygon","coordinates":[[[385700,5500000],[385701,5500000],[385701,5500001],[385700,5500000]]]}',
        b'{"type":"Polygon","coordinates":[[[0,0,2],[1,0,2],[1,1,2],[0,0,2]]]}',
        b'{"type":"Polygon","coordinates":[[[false,0],[1,0],[1,1],[false,0]]]}',
        b'{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1]]]}',
        b'{"type":"Feature","geometry":null}',
        b'{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]],"crs":{}}',
        b'{"type":"Polygon","coordinates":[[[NaN,0],[1,0],[1,1],[NaN,0]]]}',
    ],
)
def test_invalid_or_ambiguous_geometry_is_not_repaired(content: bytes) -> None:
    with pytest.raises(InvalidInput):
        selected_polygon(content, 0, 0)


def test_multipolygon_requires_exact_explicit_selection() -> None:
    feature = json.loads(source())
    rings = feature["geometry"]["coordinates"]
    document = {
        "type": "FeatureCollection",
        "features": [
            feature,
            {
                "type": "Feature",
                "id": "part-two",
                "geometry": {"type": "MultiPolygon", "coordinates": [rings, rings]},
            },
        ],
    }
    polygon, feature_id = selected_polygon(json.dumps(document).encode(), 1, 1)
    assert feature_id == "part-two" and len(polygon.coordinates) == 2
    for feature_index, polygon_index in [(2, 0), (0, 1), (1, 2)]:
        with pytest.raises(InvalidInput):
            selected_polygon(
                json.dumps(document).encode(), feature_index, polygon_index
            )


def test_attachment_requires_the_same_project_asset_and_source(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    project = workspace.create(USER, "Synthetic intake", {}, key="create")
    other = workspace.create(USER, "Another project", {}, key="other")
    assets = Assets(workspace)
    asset = GeometryImport(assets).prepare(
        USER, project.id, source(), options(), key="source"
    )
    prepared = asset.metadata["geometry_import"]
    assert isinstance(prepared, dict)
    geometry = read_geometry(prepared["geometry"])
    inputs = {
        "geometry": prepared["geometry"],
        "geometry_imports": {
            "schema_version": 1,
            "selected": {geometry.sources[0].id: asset.id},
        },
    }
    check_geometry_imports(assets, USER, project.id, inputs)
    with pytest.raises(NotFound):
        check_geometry_imports(assets, USER, other.id, inputs)
    with pytest.raises(InvalidInput):
        check_geometry_imports(assets, USER, None, inputs)


def test_size_and_base64_are_admitted_before_parsing() -> None:
    assert GeometryImport.decode(base64.b64encode(source()).decode()) == source()
    for content in [
        "!",
        "",
        base64.b64encode(b"x" * (MAX_GEOMETRY_FILE_BYTES + 1)).decode(),
    ]:
        with pytest.raises(InvalidInput):
            GeometryImport.decode(content)
