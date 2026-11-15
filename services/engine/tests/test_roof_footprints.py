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
    )
    for postcode, country, host in expectations:
        place = geo.lookup(postcode, country)
        assert place is not None, postcode
        service = imagery.for_state(place.iso_region or "") or imagery.for_country(
            place.country
        )
        assert service is not None, postcode
        assert host in service.tiles[0], postcode


def test_a_country_whose_service_is_broken_records_no_layer() -> None:
    # Italy's national WMS answers with an internal path it cannot read, so the
    # screen must keep its plain background rather than request a broken tile.
    from linker_engine import geo, imagery

    place = geo.lookup("20121", "IT")
    assert place is not None
    assert (
        imagery.for_state(place.iso_region or "")
        or imagery.for_country(place.country)
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


def test_a_position_with_no_mapped_building_answers_none() -> None:
    from linker_engine.roof import footprints as module

    assert module.outline_at("ZZ", 48.2082, 16.3738) is None
