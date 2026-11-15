"""The official 3D model outside Germany: what it answers, and where it is silent.

The Dutch service is fetched live at Amsterdam's centre in the first test's
comment but its answer is pinned below, so these tests run without a network:
the shape is what the module has to read, and a test that reaches the internet
is a test that fails on a train.
"""

from __future__ import annotations

import math

from linker_engine.roof import europe

# The structure the 3D BAG answers with, reduced to one building: a vertex
# table, a transform, and roof surfaces indexed into it. Two sloped planes face
# east and west at 45°, which makes the expected tilt and facing exact.
DOCUMENT = {
    "type": "CityJSON",
    "version": "2.0",
    "transform": {
        "scale": [0.001, 0.001, 0.001],
        "translate": [121000.0, 487000.0, 0.0],
    },
    "vertices": [
        [0, 0, 0],  # 0 west eave, south
        [0, 10000, 0],  # 1 west eave, north
        [5000, 10000, 5000],  # 2 ridge, north
        [5000, 0, 5000],  # 3 ridge, south
        [10000, 0, 0],  # 4 east eave, south
        [10000, 10000, 0],  # 5 east eave, north
        [0, 0, 0],  # 6 footprint, west south
        [10000, 0, 0],  # 7 east south
        [10000, 10000, 0],  # 8 east north
        [0, 10000, 0],  # 9 west north
    ],
    "features": [
        {
            "CityObjects": {
                "NL.IMBAG.Pand.0363100012165291": {
                    "attributes": {
                        "b3_dak_type": "slanted",
                        "b3_h_nok": 15.0035,
                        "b3_h_dak_min": 7.465,
                        "b3_bouwlagen": 4,
                    },
                    "geometry": [
                        {
                            "lod": "2.2",
                            "type": "MultiSurface",
                            "boundaries": [
                                [
                                    [[0, 1, 2, 3]],  # west slope: eave 0 m, ridge 5 m
                                    [[4, 3, 2, 5]],  # east slope
                                ]
                            ],
                        },
                        {
                            "lod": "0",
                            "type": "MultiSurface",
                            "boundaries": [[[[6, 7, 8, 9]]]],
                        },
                    ],
                }
            }
        }
    ],
}


def test_the_dutch_model_yields_roof_planes_with_tilt_and_facing() -> None:
    buildings = europe._dutch_buildings(DOCUMENT)  # noqa: SLF001 - the parser is the subject
    assert len(buildings) == 1
    building = buildings[0]
    assert building.id.startswith("NL.IMBAG.Pand.")
    assert len(building.planes) == 2
    west, east = building.planes
    # 5 m rise over 5 m run: 45°, facing west (270) and east (90).
    assert west.tilt_deg == 45.0
    assert math.isclose(west.azimuth_deg, 270.0, abs_tol=0.1)
    assert math.isclose(east.azimuth_deg, 90.0, abs_tol=0.1)
    # The transform is applied: coordinates come back in metres of RD New.
    assert west.ring[0][0] >= 121000.0
    assert building.footprint, "the LoD 0 envelope is kept as the footprint"


def test_a_building_without_roof_surfaces_is_not_a_roof() -> None:
    """A LoD 0 envelope alone carries no plane, so it must not be offered."""
    document = {
        "transform": {"scale": [1, 1, 1], "translate": [0, 0, 0]},
        "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]],
        "features": [
            {
                "CityObjects": {
                    "x": {
                        "attributes": {"b3_dak_type": "slanted"},
                        "geometry": [
                            {
                                "lod": "0",
                                "type": "MultiSurface",
                                "boundaries": [[[[0, 1, 2]]]],
                            }
                        ],
                    }
                }
            }
        ],
    }
    assert europe._dutch_buildings(document) == []  # noqa: SLF001


def test_a_building_the_model_calls_roofless_is_skipped() -> None:
    document = {
        "transform": {"scale": [1, 1, 1], "translate": [0, 0, 0]},
        "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 1]],
        "features": [
            {
                "CityObjects": {
                    "x": {
                        "attributes": {"b3_dak_type": "no_roof"},
                        "geometry": [
                            {
                                "lod": "2.2",
                                "type": "MultiSurface",
                                "boundaries": [[[[0, 1, 2]]]],
                            }
                        ],
                    }
                }
            }
        ],
    }
    assert europe._dutch_buildings(document) == []  # noqa: SLF001


def test_only_countries_with_a_documented_model_are_read() -> None:
    # Every other European country publishes footprints only; asking for one
    # answers None rather than inventing a roof.
    for country in ("GR", "PT", "GB", "ES", "IT", "PL", "FR", "DE"):
        assert europe.read(country, 37.98, 23.73) is None
    assert set(europe.documented_models()) == {"NL", "CH"}


def test_a_point_is_measured_against_a_footprint_ring() -> None:
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert europe.distance_m(ring, 5.0, 5.0) == 0.0, "inside the ring"
    assert europe.distance_m(ring, 13.0, 5.0) == 3.0
    assert math.isclose(europe.distance_m(ring, -2.0, -2.0), math.hypot(2, 2))
