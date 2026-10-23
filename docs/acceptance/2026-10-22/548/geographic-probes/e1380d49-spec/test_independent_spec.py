"""Independent fixed-SHA analytic/ASGI cases; synthetic files only."""
from __future__ import annotations

import base64
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import digest
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geographic import GeographicBridge, GeographicReference, geographic_on_roof, horizontal_on_roof
from linker_engine.planning.geometry import on_roof
from linker_engine.planning.geometry_import_documents import GeometryImportOptions, ImportedPlane
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.http_views import asset_view
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

ROOT = Path(__file__).resolve().parent
OPTIONS = json.loads((ROOT / "fixtures/planning/geometry-import-options.json").read_text())
SOURCE = (ROOT / "fixtures/planning/source-roof-wgs84.geojson").read_bytes()
TOKEN = "synthetic-fixed-spec-service-token"
HEADERS = {"X-Linker-Service-Token": TOKEN, "X-Linker-Planner-Principal-Kind": "user", "X-Linker-Planner-Principal-Subject": "fixed-spec-owner"}
OWNER = Actor("user", "fixed-spec-owner")


def bridge():
    return GeographicBridge(GeographicReference.model_validate({**OPTIONS["reference"], "longitude_deg": 0, "latitude_deg": 0}))


def plane(origin=(0, 0, 0), u=(1, 0, 0), v=(0, 1, 0)):
    return ImportedPlane(origin_enu=list(origin), u_axis_enu=list(u), v_axis_enu=list(v), basis_note="Independent analytic plane, synthetic only")


@pytest.mark.parametrize("up", [-100, 0, 20])
@pytest.mark.parametrize("longitude", [-40, -.001, .001, 40])
def test_equatorial_oblique_plane_analytic_intersection(up, longitude):
    # At source latitude 0, N=0. Thus v=-On/.8, Up=Ou-.6v,
    # and ECEF x=6378137+Up yields E=(6378137+Up)*tan(lon).
    p = plane(origin=(-.25, .5, up), v=(0, .8, -.6))
    expected_v = -.5 / .8
    actual_up = up - .6 * expected_v
    expected_u = (6378137 + actual_up) * math.tan(math.radians(longitude)) + .25
    uv = geographic_on_roof(bridge(), p, longitude, 0)
    assert uv == pytest.approx((expected_u, expected_v), abs=2e-9)
    back = bridge().inverse(*on_roof(p, *uv))
    assert back[:2] == pytest.approx((longitude, 0), abs=1e-12)


def test_local_metric_projection_is_independent_of_absolute_up():
    for up in [0, 5, 1e9, 1e15]:
        assert horizontal_on_roof(plane(origin=(0, 0, up), v=(0, .8, -.6)), 0, .1) == pytest.approx((0, .125), abs=1e-16)


@pytest.mark.parametrize("longitude,p", [
    (179.9999, plane(origin=(0, 0, 5))),
    (89.9999, plane(origin=(0, 0, 5))),
    (90, plane()),
    # UV is tiny but resulting ENU is too coarse.
    (math.degrees(math.atan(1e7 / 6378137)), plane(origin=(1e7, 0, 0))),
    # Resulting ENU is small but UV is too coarse.
    (0, plane(origin=(-1e7, 0, 0))),
    # Facing is positive, but inverse belongs to the opposite geodetic branch.
    (0, plane(origin=(0, 0, -6378137-100))),
])
def test_facing_metric_spacing_and_inverse_branch_are_distinct_refusals(longitude, p):
    with pytest.raises(InvalidInput):
        geographic_on_roof(bridge(), p, longitude, 0)


def test_no_arbitrary_radius_refusal_and_negative_derived_height_is_valid():
    b = bridge()
    # This declared plane passes through the zero-height source itself. It is
    # far in anchor ENU, but has adequate spacing and a valid inverse branch.
    longitude = 89.99
    base = b.forward(longitude, 0, 0)
    uv = geographic_on_roof(b, plane(origin=(0, 0, base[2])), longitude, 0)
    assert uv[0] == pytest.approx(base[0], abs=2e-9)
    uv = geographic_on_roof(b, plane(origin=(0, 0, -100)), .001, 0)
    inverse = b.inverse(*on_roof(plane(origin=(0, 0, -100)), *uv))
    assert inverse[2] < 0
    assert inverse[:2] == pytest.approx((.001, 0), abs=1e-12)


@pytest.fixture
def api(tmp_path):
    ws = Workspace(tmp_path)
    energy = EnergyService(ws, EnergyKernel(ws, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=100), max_attempts=1)
    with TestClient(create_private_app(ws, energy, credential=lambda: TOKEN, limits=HttpLimits(256000, 10000, 10, 32)), raise_server_exceptions=False) as client:
        def post(path, body, headers=HEADERS):
            return client.post(path, json={"schema_version": 1, **body}, headers=headers)
        created = post("/projects/create", {"title": "Independent geographic Spec fixture", "inputs": {}, "key": "create"})
        assert created.status_code == 200, created.text
        yield ws, post, created.json()["id"]


def request(pid, *, options=None, key="source", raw=SOURCE):
    return {"project_id": pid, "content_base64": base64.b64encode(raw).decode(), "options": copy.deepcopy(options or OPTIONS), "key": key}


@pytest.mark.parametrize("west,east", [(179.99990, 179.99999), (89.99990, 89.99999)])
def test_original_a0_fold_counterexamples_fail_through_http_without_publication(api, west, east):
    ws, post, pid = api
    options = copy.deepcopy(OPTIONS)
    options["reference"].update(longitude_deg=0, latitude_deg=0)
    options["plane"].update(origin_enu=[0, 0, 5], u_axis_enu=[1, 0, 0], v_axis_enu=[0, 1, 0])
    raw = json.dumps({"type": "Polygon", "coordinates": [[[west, 0], [east, 0], [east, .00009], [west, .00009], [west, 0]]]}).encode()
    before = {p.relative_to(ws.blobs.directory) for p in ws.blobs.directory.rglob("*") if p.is_file()}
    reply = post("/geometry/import", request(pid, options=options, raw=raw))
    assert reply.status_code == 422, reply.text
    assert before == {p.relative_to(ws.blobs.directory) for p in ws.blobs.directory.rglob("*") if p.is_file()}


def test_bound_hash_http_rejection_preserves_last_revision_and_original(api):
    ws, post, pid = api
    reply = post("/geometry/import", request(pid)); assert reply.status_code == 200, reply.text
    asset = reply.json(); geometry = asset["metadata"]["geometry_import"]["geometry"]
    source = geometry["sources"][0]
    inputs = {"geometry": geometry, "geometry_imports": {"schema_version": 1, "selected": {source["id"]: asset["id"]}}}
    attached = post("/projects/revise", {"project_id": pid, "expected_revision": 1, "inputs": inputs, "key": "attach"}); assert attached.status_code == 200
    source["note"] = "Later notes remain editable"
    noted = post("/projects/revise", {"project_id": pid, "expected_revision": 2, "inputs": inputs, "key": "notes"}); assert noted.status_code == 200
    source["reference_sha256"] = "0" * 64
    bad = post("/projects/revise", {"project_id": pid, "expected_revision": 3, "inputs": inputs, "key": "tamper"})
    assert bad.status_code == 422, bad.text
    actual = ws.get(OWNER, pid)
    assert actual.revision == 3
    assert actual.inputs["geometry"]["sources"][0]["reference_sha256"] == digest(SOURCE)
    assert actual.inputs["geometry"]["sources"][0]["note"] == "Later notes remain editable"
    assert post("/assets/content", {"project_id": pid, "asset_id": asset["id"]}).content == SOURCE


def load_legacy(name):
    module_name = "linker_engine.planning._independent_legacy_" + name
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "legacy-src" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_real_a0_receipt_compatibility_and_explicit_new_method_identity(api, monkeypatch):
    ws, post, pid = api
    # Execute the actual three a0 blobs, not a newly fabricated result. Alias
    # their geographic helpers so a0's original transformation is retained.
    old_geo = load_legacy("geographic")
    old_options_module = load_legacy("geometry_import_documents")
    old_intake_module = load_legacy("geometry_import")
    old_intake_module.GeographicBridge = old_geo.GeographicBridge
    old_intake_module.horizontal_on_roof = old_geo.horizontal_on_roof
    legacy = copy.deepcopy(OPTIONS); del legacy["plane_intersection_method"]
    old_options = old_options_module.GeometryImportOptions.model_validate(legacy)
    old_asset = old_intake_module.GeometryImport(Assets(ws)).prepare(OWNER, pid, SOURCE, old_options, key="actual-a0-receipt")
    original = asset_view(old_asset)
    new_command = request(pid, key="new-explicit-method")
    modern = post("/geometry/import", new_command); assert modern.status_code == 200, modern.text
    modern_json = modern.json()
    assert modern_json["metadata"]["geometry_import"]["plane_intersection_method"] == "geodetic_vertical_line_v1"
    assert modern_json["metadata"]["geometry_import"]["geometry"]["sources"][0]["id"] != original["metadata"]["geometry_import"]["geometry"]["sources"][0]["id"]

    import linker_engine.planning.geometry_import as new_module
    def should_not_convert(*_args, **_kwargs):
        raise AssertionError("Existing immutable receipts must not re-run conversion")
    monkeypatch.setattr(new_module, "GeographicBridge", should_not_convert)
    for path in ["/geometry/import", "/operations/replay/geometry/import"]:
        reply = post(path, request(pid, options=legacy, key="actual-a0-receipt"))
        assert reply.status_code == 200, reply.text
        assert (reply.json() if path == "/geometry/import" else reply.json()["result"]) == original
    changed = post("/geometry/import", request(pid, key="actual-a0-receipt")); assert changed.status_code == 409
    explicit_null = copy.deepcopy(legacy); explicit_null["plane_intersection_method"] = None
    null_changed = post("/geometry/import", request(pid, options=explicit_null, key="actual-a0-receipt")); assert null_changed.status_code == 409
    for name, options in [("missing", legacy), ("null", explicit_null)]:
        fresh = post("/geometry/import", request(pid, options=options, key="fresh-" + name))
        assert fresh.status_code == 503, fresh.text
    foreign = {**HEADERS, "X-Linker-Planner-Principal-Subject": "other-fixed-spec-owner"}
    invalid_foreign = post("/geometry/import", {**request(pid), "content_base64": "!"}, foreign)
    assert invalid_foreign.status_code == 404

