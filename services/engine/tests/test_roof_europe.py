"""The official 3D model outside Germany: what it answers, and where it is silent.

The Dutch service is fetched live at Amsterdam's centre in the first test's
comment but its answer is pinned below, so these tests run without a network:
the shape is what the module has to read, and a test that reaches the internet
is a test that fails on a train.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

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
    assert set(europe.documented_models()) == {"NL", "CH", "LI"}


def test_liechtenstein_and_bounded_swiss_disk_lru_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io
    import json
    import os
    import time
    import zipfile

    from pyproj import Transformer

    # Vaduz, Liechtenstein (LV95 coordinates inside Liechtenstein)
    lat, lon = 47.1410, 9.5209
    to_lv95 = Transformer.from_crs("EPSG:4326", "EPSG:2056", always_xy=True)
    vx, vy = to_lv95.transform(lon, lat)

    dxf = "".join(
        [
            "0\nPOLYLINE\n8\nGebaeude Einzelhaus\n70\n128\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx - 5}\n20\n{vy - 5}\n30\n10.0\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx + 5}\n20\n{vy - 5}\n30\n10.0\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx - 5}\n20\n{vy + 5}\n30\n10.0\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx + 5}\n20\n{vy + 5}\n30\n10.0\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx - 5}\n20\n{vy}\n30\n13.0\n",
            f"0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n192\n10\n{vx + 5}\n20\n{vy}\n30\n13.0\n",
            "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n128\n71\n1\n72\n5\n73\n2\n",
            "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n128\n71\n2\n72\n5\n73\n6\n",
            "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n128\n71\n3\n72\n4\n73\n6\n",
            "0\nVERTEX\n8\nGebaeude Einzelhaus\n70\n128\n71\n3\n72\n6\n73\n5\n",
        ]
    )
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as bundle:
        bundle.writestr("vaduz.dxf", dxf)
    zip_bytes = zip_buf.getvalue()

    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    swiss_dir = tmp_path / "swiss"
    swiss_dir.mkdir(parents=True)
    # Seed 6 older cached tiles to verify LRU eviction keeps <= 6 files.
    base_ts = time.time() - 100
    for idx in range(6):
        old_file = swiss_dir / f"old-{idx}.dxf.zip"
        old_file.write_bytes(b"stale")
        os.utime(old_file, (base_ts + idx, base_ts + idx))

    stac_doc = {
        "features": [
            {
                "id": "li-vaduz-tile",
                "bbox": [lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02],
                "assets": {
                    "dxf": {"href": "https://example.invalid/li-vaduz-tile.dxf.zip"}
                },
            }
        ]
    }

    class FakeResponse(io.BytesIO):
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_: object) -> None:
            self.close()

    def fake_urlopen(req: object, timeout: float = 0) -> FakeResponse:
        url = getattr(req, "full_url", str(req))
        if "stac" in url:
            return FakeResponse(json.dumps(stac_doc).encode())
        return FakeResponse(zip_bytes)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = europe.read("LI", lat, lon)
    assert result is not None
    assert result.country == "LI"
    assert len(result.buildings) == 1
    assert result.buildings[0].id.startswith("LI ")
    assert len(result.buildings[0].planes) == 2

    cached_files = sorted(p.name for p in swiss_dir.glob("*.dxf.zip"))
    assert len(cached_files) == 6
    assert "li-vaduz-tile.dxf.zip" in cached_files
    assert "old-0.dxf.zip" not in cached_files


def test_a_point_is_measured_against_a_footprint_ring() -> None:
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert europe.distance_m(ring, 5.0, 5.0) == 0.0, "inside the ring"
    assert europe.distance_m(ring, 13.0, 5.0) == 3.0
    assert math.isclose(europe.distance_m(ring, -2.0, -2.0), math.hypot(2, 2))
