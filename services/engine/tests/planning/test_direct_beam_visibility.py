"""Independent rational shadow union; synthetic geometry, not product facts."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning.canonical import Json
from linker_engine.planning.direct_beam_geometry import (
    Face,
    build_scene,
    polygon,
    prism,
)
from linker_engine.planning.direct_beam_inputs import (
    DirectBeamLimits,
    DirectBeamSampling,
)
from linker_engine.planning.direct_beam_visibility import geometric_visibility
from linker_engine.planning.errors import InvalidInput, NumericalFailure


def test_analytic_union_midpoints_local_frames_and_fail_closed_boundaries() -> None:
    root = Path(__file__).resolve().parents[4]
    value: dict[str, Any] = json.loads(
        (root / "fixtures/planning/geometry-flat.json").read_text()
    )
    roof = value["roofs"][0]
    roof.update(origin_enu=[0, 0, 0], boundary_uv=[[-4, -2], [2, -2], [2, 2], [-4, 2]])
    value["module_specs"][0].update(
        model="Synthetic analytic unit square", length_m=1, thickness_m=0.1
    )
    receiver = value["arrays"][0]
    receiver.update(
        id="receiver",
        origin_uv=[0, 0],
        rows=1,
        columns=1,
        excluded_slots=[],
        lower_edge_clearance_m=0.9,
    )
    blocker = deepcopy(receiver)
    blocker.update(
        id="other_panel",
        origin_uv=[-2.1, -2 / 3],
        rotation_deg=90,
        mount_tilt_deg=90,
        lower_edge_clearance_m=8 / 3,
    )
    value["arrays"].append(blocker)
    value["obstacles"] = [
        {
            "id": "wall",
            "name": "Analytic opaque prism",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[-1.5, -1], [-1, -1], [-1, 2], [-1.5, 2]],
            "extrusion_axis_enu": [0, 0, 1],
            "height_m": 7 / 3,
        }
    ]
    value["keepouts"] = [
        {
            "id": "annotation",
            "name": "No declared opaque volume",
            "source_id": "survey",
            "roof_id": "roof",
            "footprint_uv": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "reason": "Synthetic non-opaque annotation",
        }
    ]
    direction = (-1 / math.sqrt(2), 0.0, 1 / math.sqrt(2))
    limits = DirectBeamLimits(
        max_selected_rows=1,
        max_samples=1000,
        max_ray_face_checks=100000,
        max_bounds_checks=100000,
        index_leaf_size=2,
    )
    scene = build_scene(cast(Json, value))
    assert scene.excluded_nonopaque_ids == ("annotation",)
    assert {item.id for item in scene.opaque} == {
        "roof",
        "wall",
        "receiver:0:0",
        "other_panel:0:0",
    }
    # At receiver z=1, the prism's x=-1 front/top7/3 hides x<=1/3.
    # The other module's x=-2 front/top11/3 hides x<=2/3,y<=1/3.
    # Independent planar union: 1/3 + 2/9 - 1/9 = 4/9, visibility5/9.
    union = Fraction(1, 3) + Fraction(2, 3) * Fraction(1, 3) - Fraction(1, 3) ** 2
    assert 1 - union == Fraction(5, 9)
    result = geometric_visibility(
        scene,
        direction,
        DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
        limits,
    )
    rows = cast(list[dict[str, Any]], result["modules"])
    active = rows[0]
    assert active["coarse"]["visible_fraction"] == 0.625
    assert active["fine"]["visible_fraction"] == 0.53125
    assert (
        active["coarse"]["sample_count"] == 16 and active["fine"]["sample_count"] == 64
    )
    assert active["observed_absolute_delta"] == 0.09375
    assert active["fine"]["blocker_sample_counts"] == {
        "other_panel:0:0": 15,
        "wall": 24,
    }
    assert rows[1]["status"] == "back_facing_or_tangent" and rows[1]["fine"] is None
    refined = geometric_visibility(
        scene,
        direction,
        DirectBeamSampling(coarse_cells_per_edge=8, fine_cells_per_edge=16),
        limits,
    )
    refined_row = cast(list[dict[str, Any]], refined["modules"])[0]
    assert refined_row["fine"]["visible_fraction"] == 0.5703125
    assert refined_row["fine"]["blocker_sample_counts"] == {
        "other_panel:0:0": 55,
        "wall": 80,
    }
    assert refined_row["observed_absolute_delta"] == 0.0390625
    moved = deepcopy(value)
    # Common large ENU translation and exact90deg rotation leave local metre
    # detail intact. No absolute display centre is subtracted after rounding.
    moved["roofs"][0].update(
        origin_enu=[2**40, -(2**40), 2**40], u_axis_enu=[0, 1, 0], v_axis_enu=[-1, 0, 0]
    )
    rotated = geometric_visibility(
        build_scene(cast(Json, moved)),
        (0.0, direction[0], direction[2]),
        DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
        limits,
    )
    assert rotated["modules"] == result["modules"]
    assert rotated["sample_count"] == result["sample_count"]
    # AABB traversal work is axis-dependent; it is not a physical result.

    square = polygon([[0, 0], [1, 0], [1, 1], [0, 1]], [])
    off_ray = tuple(
        prism(
            f"off:{number}",
            "obstacle_volume",
            Face((20 + number, 10 + number, 0), (1, 0, 0), (0, 1, 0), square),
            (0, 0, 1),
            2,
        )
        for number in range(64)
    )
    sparse = replace(scene, opaque=(*scene.opaque, *off_ray))
    sparse_result = geometric_visibility(
        sparse,
        direction,
        DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
        limits,
    )
    assert sparse_result["modules"] == result["modules"]
    assert sparse_result["ray_face_checks"] == result["ray_face_checks"]
    # The accepted analytic oracle fixes every fraction/blocker count above.
    # An exhaustive narrowphase must visit all other faces for each of these
    # 80 sampled points; compare actual BVH+exact work, not just face work.
    brute_face_checks = (16 + 64) * sum(
        len(item.faces) for item in sparse.opaque if item.id != "receiver:0:0"
    )
    bounds_work = cast(int, sparse_result["bounds_checks"])
    exact_work = cast(int, sparse_result["ray_face_checks"])
    assert bounds_work > 0
    assert bounds_work + exact_work < brute_face_checks
    night = geometric_visibility(
        scene,
        (0.0, 0.0, -1.0),
        DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
        limits,
    )
    assert night["sample_count"] == 0
    assert all(
        row["status"] == "night" and row["fine"] is None
        for row in cast(list[dict[str, Any]], night["modules"])
    )
    # Same polygon engine supports concavity, holes and a real sheared prism.
    face = Face(
        (0, 0, 2),
        (1, 0, 0),
        (0, 1, 0),
        polygon(
            [[-3, -3], [3, -3], [3, 3], [0, 3], [0, 0], [-3, 0]],
            [[[1, 1], [2, 1], [2, 2], [1, 2]]],
        ),
    )
    assert not face.ray_hit((1.5, 1.5, 1), (0, 0, 1), scene.epsilon_m)
    assert not face.ray_hit((-1, 1, 1), (0, 0, 1), scene.epsilon_m)
    assert face.ray_hit((2.5, 2.5, 1), (0, 0, 1), scene.epsilon_m)
    sheared = prism(
        "sheared",
        "obstacle_volume",
        Face(
            (0, 0, 2),
            (1, 0, 0),
            (0, 1, 0),
            polygon([[0, 0], [1, 0], [1, 1], [0, 1]], []),
        ),
        (0.6, 0, 0.8),
        1,
    )
    assert any(
        f.ray_hit((1.2, 0.5, 1), (0, 0, 1), scene.epsilon_m) for f in sheared.faces
    )
    assert not any(
        f.ray_hit((1.8, 0.5, 1), (0, 0, 1), scene.epsilon_m) for f in sheared.faces
    )
    with pytest.raises(NumericalFailure):
        face.ray_hit((1, 1.5, 1), (0, 0, 1), scene.epsilon_m)
    touching = deepcopy(value)
    touching["obstacles"][0].update(
        footprint_uv=[[0, 0], [1, 0], [1, 1], [0, 1]], height_m=1
    )
    with pytest.raises(NumericalFailure, match="intersects"):
        geometric_visibility(
            build_scene(cast(Json, touching)),
            direction,
            DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
            limits,
        )
    degenerate = deepcopy(value)
    degenerate["obstacles"][0]["extrusion_axis_enu"] = [1, 0, 0]
    with pytest.raises(NumericalFailure, match="tangent"):
        build_scene(cast(Json, degenerate))
    with pytest.raises(InvalidInput, match="resource budget"):
        geometric_visibility(
            scene,
            direction,
            DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
            limits.model_copy(update={"max_ray_face_checks": 1}),
        )
    with pytest.raises(InvalidInput, match="bounds resource budget"):
        geometric_visibility(
            scene,
            direction,
            DirectBeamSampling(coarse_cells_per_edge=4, fine_cells_per_edge=8),
            limits.model_copy(update={"max_bounds_checks": 1}),
        )
