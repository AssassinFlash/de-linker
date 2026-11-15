"""Microsoft global building footprints: the outline where no roof model exists.

Measured 2026-11-16 against the published part for quadkey `120230113`
(Vienna centre, 37.9 MB compressed, 320,031 outlines): the reader keeps the
outlines near the position and returns the one containing it as a 32-point,
4,138 m2 ring. These tests pin the rules that run proved.
"""

from __future__ import annotations

import gzip
import json

from linker_engine.roof import footprints


def _part(rings: list[list[list[float]]]) -> bytes:
    lines = [
        json.dumps(
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        )
        for ring in rings
    ]
    return gzip.compress("\n".join(lines).encode())


def _box(lon: float, lat: float, size: float = 0.0002) -> list[list[float]]:
    return [
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]


def test_the_quadkey_of_a_position_matches_the_published_part() -> None:
    # The catalogue keys this position's part by this key; a different bit order
    # or zoom would name a part the dataset does not publish.
    assert footprints.quadkey(48.2082, 16.3738) == "120230113"


def test_only_the_outlines_near_the_position_are_kept() -> None:
    blob = _part([_box(16.9, 48.9), _box(16.3738, 48.2082)])
    kept = footprints.outlines(blob, 48.2082, 16.3738)
    assert len(kept) == 1
    assert abs(kept[0][0][0] - 16.3738) < 1e-6


def test_the_outline_containing_the_position_is_returned() -> None:
    blob = _part([_box(16.9, 48.9), _box(16.3738, 48.2082)])
    ring = footprints.nearest(
        footprints.outlines(blob, 48.2082, 16.3738), 48.2082, 16.3738
    )
    assert ring is not None
    assert len(ring) >= 4


def test_a_position_far_from_every_outline_finds_nothing() -> None:
    blob = _part([_box(16.3738, 48.2082)])
    assert (
        footprints.nearest(footprints.outlines(blob, 48.5, 16.7), 48.5, 16.7) is None
    )


def test_the_area_of_an_outline_is_in_square_metres() -> None:
    # 0.0002 degrees of latitude is about 22 m, so a square of that size is
    # about 500 m2; a degrees-based figure would be 4e-8 and read as nothing.
    area = footprints.area_m2(_box(16.3738, 48.2082))
    assert 300.0 < area < 700.0


def test_a_raster_outline_keeps_its_corners_and_drops_repeats() -> None:
    dense = [
        (16.0, 48.0),
        (16.0 + 1e-7, 48.0),
        (16.0 + 2e-7, 48.0),
        (16.0002, 48.0),
        (16.0002, 48.0002),
        (16.0, 48.0002),
    ]
    simplified = footprints.simplify(dense)
    assert len(simplified) < len(dense)
    assert simplified[0] == dense[0]
