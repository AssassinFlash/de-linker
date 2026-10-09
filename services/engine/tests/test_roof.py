"""Roof step: the official LoD2 outline at a real Munich address (PLZ 80538) and a module count."""

from pathlib import Path

import pytest
from conftest import TRIFTSTRASSE_5, munich_tile

from linker_engine.catalog import Catalog
from linker_engine.models import Location, RoofRequest
from linker_engine.roof import lod2
from linker_engine.roof.service import RoofService


@pytest.fixture
def service(tmp_path: Path, catalog: Catalog) -> RoofService:
    return RoofService(tmp_path, catalog.module, lod2.TileIndex(tmp_path, munich_tile))


def test_triftstrasse_5_has_an_outline_planes_and_modules(
    service: RoofService, catalog: Catalog
) -> None:
    latitude, longitude = TRIFTSTRASSE_5
    result = service.outline(
        RoofRequest(
            plz="80538", location=Location(latitude=latitude, longitude=longitude)
        )
    )
    assert result.found
    assert result.address == "Triftstraße 5"
    assert result.outline and len(result.outline[0]) >= 4
    assert result.planes
    assert all(
        0 <= p.azimuth_deg < 360 and 0 <= p.tilt_deg <= 90 for p in result.planes
    )
    usable = [p for p in result.planes if p.usable]
    assert usable and all(p.modules == len(p.module_polygons) for p in result.planes)
    assert result.modules == sum(p.modules for p in result.planes) > 0
    assert result.kwp == pytest.approx(result.modules * catalog.module.pmax_w / 1000)
    north = [p for p in result.planes if p.excluded_reason == "roof_faces_north"]
    assert north and all(p.modules == 0 for p in north)
    assert result.licence.startswith("CC BY 4.0")


def test_a_click_beside_any_building_finds_nothing(service: RoofService) -> None:
    result = service.outline(
        RoofRequest(
            plz="80538", location=Location(latitude=48.14095, longitude=11.58700)
        )
    )
    assert not result.found and result.modules == 0


def test_the_index_is_built_once(tmp_path: Path, catalog: Catalog) -> None:
    calls: list[str] = []

    def counting(tile: lod2.Tile, target: Path) -> None:
        calls.append(tile.key)
        munich_tile(tile, target)

    service = RoofService(tmp_path, catalog.module, lod2.TileIndex(tmp_path, counting))
    request = RoofRequest(
        plz="80538",
        location=Location(latitude=TRIFTSTRASSE_5[0], longitude=TRIFTSTRASSE_5[1]),
    )
    service.outline(request)
    service.outline(request)
    assert calls == ["DE-BY_32_692_5334"]


@pytest.mark.parametrize(
    ("state", "position", "url"),
    [
        (
            "DE-BY",
            TRIFTSTRASSE_5,
            "https://download1.bayernwolke.de/a/lod2/citygml/692_5334.gml",
        ),
        (
            "DE-NW",
            (51.2277, 6.7735),
            "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/lod2_gml/LoD2_32_344_5677_1_NW.gml",
        ),
        (
            "DE-BW",
            (48.7758, 9.1829),
            "https://opengeodata.lgl-bw.de/data/lod2/LoD2_32_513_5402_2_bw.zip",
        ),
        (
            "DE-SH",
            (54.3233, 10.1228),
            "https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/massen.php?file=LoD2_32_573_6020_1_SH.xml&id=4&live=2024&km=32570_6020",
        ),
    ],
)
def test_tile_urls_follow_each_states_grid(
    state: str, position: tuple[float, float], url: str
) -> None:
    assert lod2.tile_for(state, *position).url == url


def test_portal_states_fall_back_to_drawing() -> None:
    tile = lod2.tile_for("DE-HE", 50.0782, 8.2398)
    with pytest.raises(lod2.Lod2Unavailable):
        lod2.fetch(tile, Path("/nonexistent"))
