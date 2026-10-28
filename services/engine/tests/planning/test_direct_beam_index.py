"""Same rational two-blocker scene; exact primitives remain the narrowphase."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import replace
from fractions import Fraction

import pytest

from linker_engine.planning import direct_beam_index
from linker_engine.planning.direct_beam_geometry import (
    Face,
    Opaque,
    Receiver,
    Scene,
    polygon,
    prism,
)
from linker_engine.planning.direct_beam_index import DirectBeamIndex
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geometry import Vector


def test_analytic_candidates_conservative_contacts_and_real_bvh_pruning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    square = polygon([[0, 0], [1, 0], [1, 1], [0, 1]], [])
    receiver = Receiver(
        "receiver:0:0",
        "receiver",
        "roof",
        (0.5, 0.5, 1),
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        1,
        1,
    )
    own = prism(
        receiver.id,
        "module_volume",
        Face((0, 0, 0.9), (1, 0, 0), (0, 1, 0), square),
        (0, 0, 1),
        0.1,
    )
    roof = Face(
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        polygon([[-4, -2], [2, -2], [2, 2], [-4, 2]], []),
    )
    wall = prism(
        "wall",
        "obstacle_volume",
        Face(
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            polygon([[-1.5, -1], [-1, -1], [-1, 2], [-1.5, 2]], []),
        ),
        (0, 0, 1),
        7 / 3,
    )
    other = prism(
        "other_panel:0:0",
        "module_volume",
        Face((-2.1, -2 / 3, 8 / 3), (0, 1, 0), (0, 0, 1), square),
        (1, 0, 0),
        0.1,
    )
    # Same declared planes/heights as the existing visibility acceptance:
    # wall hides x<=1/3, other module adds x<=2/3,y<=1/3 at receiver z=1.
    assert 1 - (Fraction(1, 3) + Fraction(2, 9) - Fraction(1, 9)) == Fraction(5, 9)
    off_ray = tuple(
        prism(
            f"off:{index}",
            "obstacle_volume",
            Face((20 + index, 10 + index, 0), (1, 0, 0), (0, 1, 0), square),
            (0, 0, 1),
            2,
        )
        for index in range(64)
    )
    scene = Scene(
        (receiver,),
        (
            Opaque("roof", "roof_surface", roof, None, None, (roof,)),
            own,
            wall,
            other,
            *off_ray,
        ),
        (),
        1e-9,
    )
    index = DirectBeamIndex.from_scene(scene, leaf_size=2)
    direction = (-1 / math.sqrt(2), 0.0, 1 / math.sqrt(2))

    def blockers(items: tuple[Opaque, ...], point: Vector) -> set[str]:
        result = set()
        for item in items:
            if item.kind == "module_volume" and item.id == receiver.id:
                continue
            assert not item.contains_receiver(point, scene.epsilon_m)
            for face in item.faces:
                if face.ray_hit(point, direction, scene.epsilon_m):
                    result.add(item.id)
        return result

    for count, expected in [(4, 0.625), (8, 0.53125), (16, 0.5703125)]:
        visible = 0
        counts: Counter[str] = Counter()
        for y in range(count):
            for x in range(count):
                point = receiver.midpoint(x, y, count)
                selected = index.query(point, direction)
                actual = blockers(selected.opaque, point)
                assert actual == blockers(scene.opaque, point)
                visible += not actual
                counts.update(actual)
        assert visible / count**2 == expected
        if count == 8:
            assert counts == {"wall": 24, "other_panel:0:0": 15}
    query = index.query((0.5, 0.5, 1), direction)
    assert len(query.opaque) <= 3
    assert query.bounds_tested < len(scene.opaque) // 2
    assert [item.id for item in query.opaque] == sorted(
        item.id for item in query.opaque
    )
    reversed_index = DirectBeamIndex.from_scene(
        replace(scene, opaque=tuple(reversed(scene.opaque))),
        leaf_size=2,
    )
    assert reversed_index.query((0.5, 0.5, 1), direction) == query

    charged = 0

    def charge() -> None:
        nonlocal charged
        charged += 1

    assert index.query((0.5, 0.5, 1), direction, on_bounds_check=charge) == query
    assert charged == query.bounds_tested
    # One node followed by entries makes both callback sites observable. The
    # third preflight must stop before a third actual AABB test is performed.
    actual_checks = 0
    intersects = direct_beam_index._Bounds.intersects

    def observed(
        bounds: direct_beam_index._Bounds, point: Vector, ray: Vector, epsilon: float
    ) -> bool:
        nonlocal actual_checks
        actual_checks += 1
        return intersects(bounds, point, ray, epsilon)

    def limited() -> None:
        nonlocal charged
        if charged == 2:
            raise InvalidInput("fixture bounds budget exhausted")
        charged += 1

    charged = 0
    with monkeypatch.context() as patch:
        patch.setattr(direct_beam_index._Bounds, "intersects", observed)
        with pytest.raises(InvalidInput, match="bounds budget"):
            DirectBeamIndex.from_scene(scene, leaf_size=len(scene.opaque)).query(
                (0.5, 0.5, 1),
                direction,
                on_bounds_check=limited,
            )
    assert charged == actual_checks == 2

    # Closed contact/inside/zero-axis rays remain for the original exact checks.
    for point, ray in [
        ((-1.25, 0, 1), (1, 0, 0)),
        ((-1, -1, 0), (0, 0, 1)),
        ((-1, math.nextafter(-1, -math.inf), 0), (0, 0, 1)),
        ((-2, 0, 0), (math.ulp(0.0), 0, 1)),
    ]:
        assert wall in index.query(point, ray).opaque
    uncertain = Face((0, 0, 0), (1, 0, 0), (1, 1e-10, 0), square)
    uncertain_scene = replace(
        scene,
        opaque=(
            Opaque("uncertain", "roof_surface", uncertain, None, None, (uncertain,)),
        ),
    )
    assert (
        len(
            DirectBeamIndex.from_scene(uncertain_scene, leaf_size=1)
            .query((9, 9, 9), (0, 0, 1))
            .opaque
        )
        == 1
    )
    for point, ray in [((math.nan, 0, 0), (0, 0, 1)), ((0, 0, 0), (0, 0, 0))]:
        with pytest.raises(InvalidInput):
            index.query(point, ray)
    with pytest.raises(InvalidInput, match="extrusion"):
        DirectBeamIndex.from_scene(
            replace(scene, opaque=(replace(wall, axis=(0, 0, 0)),)), leaf_size=2
        )
    for face in [
        replace(roof, origin=(math.nan, 0, 0)),
        replace(roof, v=(2, 0, 0)),
    ]:
        with pytest.raises(InvalidInput):
            DirectBeamIndex.from_scene(
                replace(
                    scene,
                    opaque=(Opaque("bad", "roof_surface", face, None, None, (face,)),),
                ),
                leaf_size=2,
            )
