"""swissBUILDINGS3D tiles: a DXF polyface mesh becomes roof surfaces.

The fixtures are hand-written in the DXF group-code grammar rather than taken
from the 16 MB published tile: the published file proves the reader against
real data (see the acceptance record), and these prove the grouping rules that
the real file exposed.
"""

from __future__ import annotations

import math

from linker_engine.roof import swiss


def _vertex(x: float, y: float, z: float) -> str:
    return (
        "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n"
        f"10\n{x}\n20\n{y}\n30\n{z}\n"
    )


def _face(first: int, second: int, third: int) -> str:
    return (
        "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n128\n"
        f"71\n{first}\n72\n{second}\n73\n{third}\n"
    )


def _polyline() -> str:
    return "0\nPOLYLINE\n8\nGebaeude Einzelhaus\n70\n128\n"


def _gable(first_x: float, end_x: float) -> str:
    """Two roof halves meeting at a ridge, as a polyface mesh would write them.

    The ridge runs along x at mid-depth, higher than the eaves, so each half is
    a real slope: the eaves are at z=10 and the ridge at z=13 over a 5 m run.
    """
    return "".join(
        [
            _polyline(),
            _vertex(first_x, 0.0, 10.0),
            _vertex(end_x, 0.0, 10.0),
            _vertex(first_x, 10.0, 10.0),
            _vertex(end_x, 10.0, 10.0),
            _vertex(first_x, 5.0, 13.0),
            _vertex(end_x, 5.0, 13.0),
            _face(1, 5, 2),
            _face(2, 5, 6),
            _face(3, 4, 6),
            _face(3, 6, 5),
        ]
    )


def test_a_face_numbers_its_vertices_within_its_own_polyline() -> None:
    # Measured on the published Bern tile: a face's indices are local to the
    # polyline that carries it. Read as file-wide indices, the tenth building's
    # faces land on the first building's corners and report thousands of m².
    text = _gable(0.0, 20.0) + _gable(1000.0, 1020.0)
    tile = swiss.parse(swiss._pairs(text))  # noqa: SLF001
    assert len(tile.faces) == 8
    assert tile.buildings().keys() == {0, 1}
    for owner, positions in tile.buildings().items():
        base = 1000.0 if owner else 0.0
        for position in positions:
            for index in tile.faces[position]:
                assert base <= tile.vertices[index][0] <= base + 20.0


def test_a_mesh_vertex_and_a_face_record_are_told_apart_by_the_whole_flag() -> None:
    # 192 is 64|128, so any bit mask that accepts 192 also accepts a face.
    text = _polyline() + _vertex(0.0, 0.0, 0.0) + _vertex(10.0, 0.0, 0.0)
    text += _vertex(0.0, 10.0, 0.0) + _face(1, 2, 3)
    tile = swiss.parse(swiss._pairs(text))  # noqa: SLF001
    assert len(tile.vertices) == 3
    assert len(tile.faces) == 1


def test_two_gable_halves_merge_into_two_planes_with_real_tilt() -> None:
    tile = swiss.parse(swiss._pairs(_gable(0.0, 20.0)))  # noqa: SLF001
    found = tile.nearest(10.0, 5.0, 5.0)
    assert found is not None
    sloped = [surface for surface in found.surfaces if surface.tilt_deg > 1.0]
    assert len(sloped) == 2
    for surface in sloped:
        assert 5.0 < surface.tilt_deg < 85.0
        assert surface.area_m2 <= swiss.MAX_ROOF_PLANE_M2
    # The two halves face opposite ways.
    facing = sorted(surface.azimuth_deg for surface in sloped)
    assert abs(facing[1] - facing[0]) > 90.0


def test_a_wall_is_not_a_roof() -> None:
    # A vertical quad has tilt 90 and carries no module.
    text = (
        _polyline()
        + _vertex(0.0, 0.0, 0.0)
        + _vertex(10.0, 0.0, 0.0)
        + _vertex(10.0, 0.0, 10.0)
        + _face(1, 2, 3)
    )
    tile = swiss.parse(swiss._pairs(text))  # noqa: SLF001
    found = tile.nearest(5.0, 0.0, 2.0)
    assert found is None or found.surfaces == []


def test_a_position_far_from_every_building_finds_nothing() -> None:
    tile = swiss.parse(swiss._pairs(_gable(0.0, 20.0)))  # noqa: SLF001
    assert tile.nearest(5000.0, 5000.0, 3.0) is None


def test_the_tile_grid_names_one_kilometre_square() -> None:
    # Measured 2026-11-16: tile `1166-42` covers 7.414-7.471 E, and the grid
    # step is 1000 m of EPSG:2056.
    assert swiss.MAX_ROOF_PLANE_M2 == 3000.0
    assert math.isclose(swiss.CELL_M, 32.0)
