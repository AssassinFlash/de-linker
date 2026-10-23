"""Independent analytic dimensions, frozen storage and conservative plan rules."""

from __future__ import annotations

import copy
import dataclasses
import json
import math
import random
from pathlib import Path
from typing import Any, cast

import pytest
from shapely.geometry import Polygon

from linker_engine.planning import geometry, geometry_review
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.errors import InvalidInput, NotFound
from linker_engine.planning.geometry import panel_poses, read_geometry, roof_coordinates
from linker_engine.planning.geometry_documents import geometry_schema
from linker_engine.planning.geometry_review import review_geometry
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace

ROOT = Path(__file__).resolve().parents[4]


def fixture() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / "fixtures/planning/geometry-flat.json").read_text()),
    )


def kinds(report: Object) -> list[str]:
    return [str(item["kind"]) for item in cast(list[Object], report["issues"])]


def one_panel() -> dict[str, Any]:
    value = fixture()
    value["arrays"][0].update(rows=1, columns=1, excluded_slots=[])
    return value


def test_schema_matches_the_browser_contract() -> None:
    assert (
        json.loads(
            (ROOT / "apps/planner/src/contracts/geometry.schema.json").read_text()
        )
        == geometry_schema()
    )
    assert json.loads(
        (ROOT / "apps/planner/src/contracts/geometry-policy.json").read_text()
    ) == {
        "max_panels": geometry.MAX_PANELS,
        "max_vertices": geometry.MAX_VERTICES,
        "max_objects": geometry.MAX_OBJECTS,
    }


def test_exact_slot_ids_declared_rating_and_excluded_quantity() -> None:
    value = fixture()
    poses = panel_poses(read_geometry(value))
    assert len(poses) == 6
    assert poses[0].id == "array:0:0" and poses[-1].id == "array:1:2"
    assert poses[0].centre_enu == pytest.approx((11.5, -17, 4.12))
    assert not poses[-1].included
    report = review_geometry(value)
    assert report["module_count"] == 5 and report["declared_stc_kwp"] == 2.5
    assert (
        report["conflict_count"] == 0
        and report["engineering_status"] == "not_evaluated"
    )
    assert report["geometry_sha256"] == digest(encode(value))
    assert kinds(report) == [
        "north_reference_unspecified",
        "source_precision_unspecified",
    ]


def test_frozen_browser_server_pose_reference_still_matches() -> None:
    reference = json.loads(
        (ROOT / "fixtures/planning/geometry-pose-reference.json").read_text()
    )
    for case in reference["cases"]:
        value = fixture()
        value["roofs"][0]["v_axis_enu"] = case["roof_v_axis_enu"]
        value["arrays"][0].update(
            rotation_deg=case["rotation_deg"], mount_tilt_deg=case["mount_tilt_deg"]
        )
        actual = json.loads(
            json.dumps(
                [dataclasses.asdict(p) for p in panel_poses(read_geometry(value))]
            )
        )
        assert len(actual) == len(case["poses"])
        # Keep the original reference unchanged. New local-frame fields are
        # tested separately; display vectors retain ordinary-scale behaviour.
        for result, expected in zip(actual, case["poses"], strict=True):
            for key, value in expected.items():
                if isinstance(value, list):
                    assert result[key] == pytest.approx(value, abs=1e-12)
                else:
                    assert result[key] == value


def test_slope_length_and_tilted_rows_use_their_own_lower_edges() -> None:
    value = fixture()
    value["roofs"][0]["v_axis_enu"] = [0, math.sqrt(3) / 2, 0.5]
    value["arrays"][0]["mount_tilt_deg"] = 30
    document = read_geometry(value)
    poses = panel_poses(document)
    roof = document.roofs[0]
    # Every row's lower surface starts at the same .1m normal clearance.
    for row in (0, 1):
        pose = poses[row * 3]
        lower = pose.corners()[0]
        # The lower-left base corner, analytically .1 above its supporting plane.
        normal = geometry.cross(roof.u_axis_enu, roof.v_axis_enu)
        assert geometry.dot(
            geometry.add(lower, geometry.scale(roof.origin_enu, -1)), normal
        ) == pytest.approx(0.1)
    uv0 = roof_coordinates(roof, poses[0].centre_enu)
    uv1 = roof_coordinates(roof, poses[3].centre_enu)
    assert uv1[1] - uv0[1] == pytest.approx(math.sqrt(3) + 0.4)
    assert review_geometry(value)["conflict_count"] == 0


@pytest.mark.parametrize("field,value", [("schema_version", True), ("extra", 1)])
def test_no_coercion_or_unrecognised_top_level_fields(
    field: str, value: object
) -> None:
    data = fixture()
    data[field] = value
    with pytest.raises(InvalidInput):
        read_geometry(data)


@pytest.mark.parametrize(
    "change",
    [
        lambda x: x["arrays"][0].update(rows="2"),
        lambda x: x["arrays"][0].update(rows=True),
        lambda x: x["arrays"][0].update(rows=10**10),
        lambda x: x["arrays"][0].update(excluded_slots=["01:0"]),
        lambda x: x["arrays"][0].update(excluded_slots=["0:0", "0:0"]),
        lambda x: x["arrays"][0].update(module_spec_id="foreign"),
        lambda x: x["arrays"][0].update(source_id="foreign"),
        lambda x: x["roofs"][0].update(u_axis_enu=[2, 0, 0]),
        lambda x: x["roofs"][0].update(v_axis_enu=[0, -1, 0]),
        lambda x: x["coordinate_system"].update(north_reference="true_north"),
        lambda x: x["module_specs"][0].update(width_m=float("inf")),
        lambda x: x["module_specs"][0]["source"].update(
            url="https://user:secret@example.test/file"
        ),
        lambda x: x["sources"][0]["permissions"].update(retain="unknown"),
        lambda x: x["sources"][0].update(kind="licensed_dataset"),
        lambda x: x["sources"][0].update(acquired_at_utc="2024-01-01T00:00:00"),
        lambda x: x["sources"][0].update(id="roof"),
    ],
)
def test_unsafe_or_unresolved_wire_data_is_rejected(change: Any) -> None:
    data = fixture()
    change(data)
    with pytest.raises(InvalidInput):
        read_geometry(data)


def test_opening_outside_edge_clearance_and_no_hidden_setback() -> None:
    value = one_panel()
    value["arrays"][0]["origin_uv"] = [0, 0]
    assert review_geometry(value)["conflict_count"] == 0  # exact zero-contact
    value["layout_rules"][0]["edge_clearance_m"] = 0.2
    assert "panel_edge_clearance" in kinds(review_geometry(value))
    value["arrays"][0]["origin_uv"] = [-0.01, 0]
    assert "panel_outside_roof" in kinds(review_geometry(value))
    value["arrays"][0]["origin_uv"] = [1, 2]
    value["roofs"][0]["holes_uv"] = [
        [[1.25, 2.25], [1.75, 2.25], [1.75, 3.75], [1.25, 3.75]]
    ]
    assert "panel_over_opening" in kinds(review_geometry(value))
    value["layout_rules"] = []
    report = review_geometry(value)
    assert "edge_clearance_unspecified" in kinds(
        report
    ) and "obstacle_clearance_unspecified" in kinds(report)


def test_invalid_boundary_is_preserved_and_diagnosed_without_repair() -> None:
    value = one_panel()
    value["roofs"][0]["boundary_uv"] = [[0, 0], [10, 10], [0, 10], [10, 0]]
    before = copy.deepcopy(value)
    assert kinds(review_geometry(value))[-1] == "invalid_roof_polygon"
    assert value == before


def test_thickness_and_slope_are_in_full_projected_footprints() -> None:
    value = one_panel()
    value["arrays"][0].update(mount_tilt_deg=30, origin_uv=[1, 0.01])
    # A 4cm thick panel shifts .02m towards the lower side when tilted 30deg.
    assert "panel_outside_roof" in kinds(review_geometry(value))
    value["arrays"][0]["origin_uv"] = [1, 0.03]
    assert "panel_outside_roof" not in kinds(review_geometry(value))


def test_rotated_keepout_and_obstacle_clearance_are_not_invented_collision_claims() -> (
    None
):
    value = one_panel()
    value["arrays"][0].update(rotation_deg=90, origin_uv=[5, 5])
    value["keepouts"] = [
        {
            "id": "walkway",
            "name": "Declared access",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[3, 5], [5, 5], [5, 6], [3, 6]],
            "reason": "Synthetic keepout",
        }
    ]
    assert "panel_in_keepout" in kinds(review_geometry(value))
    value["keepouts"] = []
    value["obstacles"] = [
        {
            "id": "vent",
            "name": "Synthetic vent",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[5.1, 5], [6, 5], [6, 6], [5.1, 6]],
            "extrusion_axis_enu": [0, 0, 1],
            "height_m": 1,
        }
    ]
    value["layout_rules"][0]["obstacle_clearance_m"] = 0.2
    report = review_geometry(value)
    assert "panel_obstacle_clearance" in kinds(report)
    assert "panel_projected_obstacle_overlap" not in kinds(report)
    value["arrays"][0]["excluded_slots"] = ["0:0"]
    assert review_geometry(value)["conflict_count"] == 0


def test_indexed_overlap_matches_independent_brute_force_rectangles() -> None:
    randomizer = random.Random(548)
    value = one_panel()
    base = value["arrays"][0]
    value["arrays"] = [
        {
            **base,
            "id": f"a{i}",
            "origin_uv": [
                randomizer.randrange(1, 35) / 2,
                randomizer.randrange(1, 30) / 2,
            ],
        }
        for i in range(60)
    ]
    report = review_geometry(value)
    expected = set()
    rectangles = [
        (a["id"], Polygon([(x, y), (x + 1, y), (x + 1, y + 2), (x, y + 2)]))
        for a in value["arrays"]
        for x, y in [a["origin_uv"]]
    ]
    for i, (a, shape) in enumerate(rectangles):
        for b, other in rectangles[i + 1 :]:
            if shape.intersection(other).area > 0:
                expected.add(frozenset([a + ":0:0", b + ":0:0"]))
    actual = {
        frozenset([str(i["object_id"]), str(i["related_id"])])
        for i in cast(list[Object], report["issues"])
        if i["kind"] == "panel_projected_overlap"
    }
    assert actual == expected and report["review_complete"]


def test_concave_obstacle_recess_is_not_filled_by_a_convex_hull() -> None:
    value = one_panel()
    value["arrays"][0]["origin_uv"] = [1.5, 1.5]
    value["obstacles"] = [
        {
            "id": "recess",
            "name": "Synthetic L-shaped obstruction",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]],
            "extrusion_axis_enu": [0, 0, 1],
            "height_m": 1,
        }
    ]
    report = review_geometry(value)
    assert "panel_projected_obstacle_overlap" not in kinds(report)
    assert report["conflict_count"] == 0
    # A diagonal extrusion sweeps into that same initially empty recess.
    value["obstacles"][0]["extrusion_axis_enu"] = [math.sqrt(0.5), 0, math.sqrt(0.5)]
    value["obstacles"][0]["height_m"] = 3
    assert "panel_projected_obstacle_overlap" in kinds(review_geometry(value))


def test_resource_limits_never_turn_a_partial_check_into_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = one_panel()
    base = value["arrays"][0]
    value["arrays"] = [{**base, "id": f"a{i}"} for i in range(8)]
    monkeypatch.setattr(geometry_review, "MAX_CANDIDATE_CHECKS", 3)
    monkeypatch.setattr(geometry_review, "MAX_DIAGNOSTICS", 2)
    report = review_geometry(value)
    assert report["geometry_status"] == "incomplete" and not report["review_complete"]
    assert (
        report["diagnostics_truncated"]
        and len(cast(list[Object], report["issues"])) == 2
    )


def test_saved_geometries_replay_reopen_and_refuse_foreign_writers(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, foreign = Actor("user", "geometry-owner"), Actor("user", "geometry-foreign")
    data = fixture()
    inputs: Object = {"geometry": data}
    project = workspace.create(user, "Synthetic geometry", inputs, key="create")
    revised = workspace.revise(
        user, project.id, 1, {"geometry": data, "note": "kept"}, key="revise"
    )
    before = set(workspace.blobs.directory.rglob("*"))
    with pytest.raises(NotFound):
        workspace.revise(foreign, project.id, 2, {"geometry": data}, key="foreign")
    assert set(workspace.blobs.directory.rglob("*")) == before
    monkeypatch.setattr(geometry, "MAX_PANELS", 1)
    assert (
        workspace.create(user, "Synthetic geometry", inputs, key="create").revision == 1
    )
    assert (
        workspace.revise(
            user, project.id, 1, {"geometry": data, "note": "kept"}, key="revise"
        ).revision
        == 2
    )
    assert workspace.get(user, project.id).inputs == revised.inputs
    assert workspace.get(user, project.id, revision=1).inputs == inputs
    with pytest.raises(InvalidInput):
        workspace.create(user, "New over policy", inputs, key="new")


@pytest.mark.parametrize("rotation", [0, 30, 45, 60])
@pytest.mark.parametrize("origin", [0, 10, 1e6, 1e15])
def test_roof_rotation_and_translation_do_not_break_zero_contact(
    rotation: float, origin: float
) -> None:
    value = one_panel()
    value["arrays"][0]["origin_uv"] = [0, 0]
    angle = math.radians(rotation)
    value["roofs"][0].update(
        origin_enu=[origin, origin, 4],
        u_axis_enu=[math.cos(angle), math.sin(angle), 0],
        v_axis_enu=[-math.sin(angle), math.cos(angle), 0],
        boundary_uv=[[0, 0], [1, 0], [1, 2], [0, 2]],
    )
    assert review_geometry(value)["conflict_count"] == 0


def test_one_centimetre_overlap_survives_large_enu_translation() -> None:
    value = one_panel()
    value["arrays"].append(
        {**value["arrays"][0], "id": "second", "origin_uv": [1.99, 2]}
    )
    for origin in (0, 1e15):
        value["roofs"][0]["origin_enu"] = [origin, 0, 4]
        report = review_geometry(value)
        assert report["conflict_count"] == 1
        assert "panel_projected_overlap" in kinds(report)


def test_review_rebases_large_uv_chart_before_constructing_small_panels() -> None:
    value = one_panel()
    value["arrays"][0]["origin_uv"] = [1e15 + 1, 1e15 + 2]
    value["module_specs"][0].update(width_m=0.01, length_m=0.02)
    value["roofs"][0]["boundary_uv"] = [
        [1e15, 1e15],
        [1e15 + 10, 1e15],
        [1e15 + 10, 1e15 + 10],
        [1e15, 1e15 + 10],
    ]
    assert review_geometry(value)["conflict_count"] == 0


@pytest.mark.parametrize(
    "degrees", [360, -360, 6898968225049280, 9007199254740991, -9007199254740991]
)
def test_rotation_reduces_before_trig_and_keeps_periodic_semantics(
    degrees: float,
) -> None:
    value = one_panel()
    value["arrays"][0]["rotation_deg"] = degrees
    actual = panel_poses(read_geometry(value))[0]
    value["arrays"][0]["rotation_deg"] = math.fmod(degrees, 360)
    expected = panel_poses(read_geometry(value))[0]
    assert actual == expected
