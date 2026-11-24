"""Microsoft global building footprints: the outline where no roof model exists.

Measured 2026-11-16 against the published part for quadkey `120230113`
(Vienna centre, 37.9 MB compressed, 320,031 outlines): the reader keeps the
outlines near the position and returns the one containing it as a 32-point,
4,138 m2 ring. These tests pin the rules that run proved.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from linker_engine.roof import footprints


def _part(rings: list[list[tuple[float, float]]]) -> bytes:
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


def _box(lon: float, lat: float, size: float = 0.0002) -> list[tuple[float, float]]:
    return [
        (lon, lat),
        (lon + size, lat),
        (lon + size, lat + size),
        (lon, lat + size),
        (lon, lat),
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
    assert footprints.nearest(footprints.outlines(blob, 48.5, 16.7), 48.5, 16.7) is None


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


def test_the_lookup_a_screen_calls_carries_the_aerial_layer() -> None:
    # The one-screen start asks `places/lookup`, not `/geo/plz`: an aerial layer
    # added only to the latter is a layer no visitor sees. Measured 2026-11-16,
    # the frontend contains no reference to `imagery` at all until this field
    # arrives on the answer it already reads.
    from linker_engine import geo, imagery

    expectations = (
        ("80538", "DE", "geoservices.bayern.de"),
        ("1012JS", "NL", "service.pdok.nl"),
        ("75001", "FR", "data.geopf.fr"),
        ("28001", "ES", "ign.es"),
        ("8001", "CH", "wms.geo.admin.ch"),
        ("SW1A 1AA", "GB", "image.discomap.eea.europa.eu"),
        ("3750-000", "PT", "cartografia.dgterritorio.gov.pt"),
        ("110 00", "CZ", "ags.cuzk.gov.cz"),
    )
    for postcode, country, host in expectations:
        place = geo.lookup(postcode, country)
        assert place is not None, postcode
        service = imagery.for_state(place.iso_region or "") or imagery.for_country(
            place.country
        )
        assert service is not None, postcode
        assert host in service.tiles[0], postcode


def test_italy_answers_through_its_https_relay() -> None:
    # Italy's PCN ArcGIS MapServer export serves a real 20-26 KB 50 cm JPEG, but
    # redirects HTTPS to plaintext HTTP without CORS headers; the same-origin
    # HTTPS relay validates the EPSG:3857 bounding box and serves verified JPEGs.
    from linker_engine import geo, imagery

    place = geo.lookup("20121", "IT")
    assert place is not None
    service = imagery.for_state(place.iso_region or "") or imagery.for_country(
        place.country
    )
    assert service is not None
    assert (
        service.tiles[0]
        == "https://de-linker.com/wp-json/linker/v1/imagery/it?bbox={bbox-epsg-3857}"
    )


def test_a_country_with_no_service_still_records_no_layer() -> None:
    # Ukraine lies outside the EU Copernicus VHR2021 mosaic (measured 2026-11-16:
    # exportImage returns a 334-byte transparent PNG), so the map keeps its
    # plain background and building outline rather than requesting blank tiles.
    from linker_engine import geo, imagery

    place = geo.lookup("01001", "UA")
    assert place is not None
    assert (
        imagery.for_state(place.iso_region or "") or imagery.for_country(place.country)
    ) is None


def test_the_outline_answer_carries_the_source_and_licence() -> None:
    # The screen must show where the shape came from: an outline is not a
    # survey, and the licence travels with it.
    from linker_engine.roof import footprints as module

    payload = module.outline_payload("AT", 48.2082, 16.3738)
    # The published part is 38 MB; the network may be unavailable in CI, and a
    # refused download must answer None rather than a guessed shape.
    if payload is None:
        return
    assert payload["source"] == "Microsoft building footprints"
    assert payload["licence"] == module.LICENCE
    assert len(payload["outline"]) >= 3
    for longitude, latitude in payload["outline"]:
        assert -180.0 <= longitude <= 180.0
        assert -90.0 <= latitude <= 90.0


def test_truncated_footprint_catalogue_uses_the_next_attributed_source(
    monkeypatch: object,
) -> None:
    from http.client import IncompleteRead

    import pytest

    assert isinstance(monkeypatch, pytest.MonkeyPatch)

    def interrupted(country: str, key: str) -> str:
        raise IncompleteRead(b"Location,QuadKey", 16)

    ring = _box(16.37, 48.21)
    monkeypatch.setattr(footprints, "part_url", interrupted)
    monkeypatch.setattr(footprints, "_overpass_outline", lambda *a, **kw: ring)
    payload = footprints.outline_payload("AT", 48.21, 16.37)
    assert payload is not None
    assert payload["source"] == "OpenStreetMap contributors"
    assert payload["licence"] == footprints.OSM_LICENCE


def test_a_position_with_no_mapped_building_answers_none() -> None:
    from linker_engine.roof import footprints as module

    assert module.outline_at("ZZ", 48.2082, 16.3738) is None


def test_a_published_tile_template_is_used_as_is() -> None:
    # Austria publishes basemap.at as a tile template, not a WMS. Measured
    # 2026-11-16: zooms 15, 16 and 17 all returned real JPEGs of 19-22 KB.
    from linker_engine import imagery

    service = imagery.for_country("AT")
    assert service is not None
    assert "{z}" in service.tiles[0] and "{x}" in service.tiles[0]
    assert "basemap.at" in service.licence or "basemap" in service.credit


def test_each_recorded_country_answers_a_usable_layer() -> None:
    from linker_engine import imagery

    for country in (
        "AT",
        "BE",
        "CH",
        "CZ",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GB",
        "GR",
        "IE",
        "IT",
        "LT",
        "LU",
        "MC",
        "NL",
        "NO",
        "PL",
        "PT",
        "SE",
    ):
        service = imagery.for_country(country)
        assert service is not None, country
        assert service.tiles[0].startswith("https://"), country
        assert "{bbox-epsg-3857}" in service.tiles[0] or "{z}" in service.tiles[0]


def test_all_50_geo_countries_have_footprint_region_mapping() -> None:
    from linker_engine import geo

    missing = geo.countries() - set(footprints.REGION_NAMES)
    assert missing == set()


def test_microstate_part_url_falls_back_to_exact_quadkey(
    monkeypatch: object,
) -> None:
    import pytest

    mp = monkeypatch
    assert isinstance(mp, pytest.MonkeyPatch)
    mp.setattr(
        footprints,
        "_catalogue",
        lambda: {
            ("Italy", "120233021"): "https://example.invalid/italy-cell.geojsonl.gz"
        },
    )
    assert (
        footprints.part_url("VA", "120233021")
        == "https://example.invalid/italy-cell.geojsonl.gz"
    )
    assert footprints.part_url("ZZ", "120233021") is None


def test_streaming_disk_lru_and_overpass_fallback(
    tmp_path: Path, monkeypatch: object
) -> None:
    import io
    import os
    import time

    import pytest

    mp = monkeypatch
    assert isinstance(mp, pytest.MonkeyPatch)
    mp.setenv("LINKER_ENGINE_CACHE", str(tmp_path))

    # 1. Streaming from a .geojsonl.gz Path on disk works.
    gz_path = tmp_path / "sample.geojsonl.gz"
    gz_path.write_bytes(_part([_box(15.64, 78.22)]))
    kept = footprints.outlines(gz_path, 78.2201, 15.6401)
    assert len(kept) == 1

    # 2. Disk LRU keeps at most MAX_CACHED_PARTS (10) files.
    fp_dir = footprints.cache_dir(tmp_path)
    base_ts = time.time() - 100
    for idx in range(10):
        old_file = fp_dir / f"XX-{idx:09d}.geojsonl.gz"
        old_file.write_bytes(b"old")
        os.utime(old_file, (base_ts + idx, base_ts + idx))

    part_bytes = _part([_box(15.64, 78.22)])
    mp.setattr(
        footprints,
        "_catalogue",
        lambda: {
            (
                "Norway",
                footprints.quadkey(78.2201, 15.6401),
            ): "https://example.invalid/sj.gz"
        },
    )

    class FakeResp(io.BytesIO):
        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_: object) -> None:
            self.close()

    mp.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=0: FakeResp(part_bytes),
    )
    payload = footprints.outline_payload("SJ", 78.2201, 15.6401)
    assert payload is not None
    assert payload["source"] == "Microsoft building footprints"
    assert payload["planes"] == []
    cached = list(fp_dir.glob("*.geojsonl.gz"))
    assert len(cached) == 10
    assert not (fp_dir / "XX-000000000.geojsonl.gz").exists()

    # 3. When Microsoft has a part that misses the position (or no part), Overpass fallback returns OSM outline.
    for cached_part in fp_dir.glob("SJ-*.geojsonl.gz"):
        cached_part.unlink()
    osm_json = json.dumps(
        {
            "elements": [
                {
                    "type": "way",
                    "geometry": [
                        {"lat": 78.2200, "lon": 15.6400},
                        {"lat": 78.2200, "lon": 15.6403},
                        {"lat": 78.2203, "lon": 15.6403},
                        {"lat": 78.2203, "lon": 15.6400},
                        {"lat": 78.2200, "lon": 15.6400},
                    ],
                }
            ]
        }
    ).encode()
    miss_part = _part([_box(15.9, 78.9)])
    mp.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=0: FakeResp(
            miss_part
            if "example.invalid"
            in (req.full_url if hasattr(req, "full_url") else str(req))
            else osm_json
        ),
    )
    miss_then_osm = footprints.outline_payload("SJ", 78.2201, 15.6401)
    assert miss_then_osm is not None
    assert miss_then_osm["source"] == "OpenStreetMap contributors"

    mp.setattr(footprints, "_catalogue", lambda: {})
    mp.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=0: FakeResp(osm_json),
    )
    osm_payload = footprints.outline_payload("SJ", 78.2201, 15.6401)
    assert osm_payload is not None
    assert osm_payload["source"] == "OpenStreetMap contributors"
    assert osm_payload["licence"] == "ODbL 1.0 (OpenStreetMap)"
    assert osm_payload["planes"] == []

    # 4. Overpass timeout/error never raises and returns None.
    def fail_urlopen(*_args: object, **_kwargs: object) -> None:
        raise TimeoutError("overpass timed out")

    mp.setattr("urllib.request.urlopen", fail_urlopen)
    assert footprints.outline_payload("SJ", 78.2201, 15.6401) is None
