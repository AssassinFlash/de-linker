"""Tests for /places/outline returning 3D planes (DE/NL/CH/LI) and 2D fallback."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import TRIFTSTRASSE_5, munich_tile
from fastapi.testclient import TestClient
from pyproj import Transformer

from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.records import Actor
from linker_engine.planning.workspace import Workspace
from linker_engine.roof import europe, lod2
from linker_engine.roof.citygml import Building, RoofPlane

TOKEN = "synthetic-outline-token"
USER = Actor("user", "wordpress:17")


def _headers() -> dict[str, str]:
    return {
        "X-Linker-Service-Token": TOKEN,
        "X-Linker-Planner-Principal-Kind": USER.kind,
        "X-Linker-Planner-Principal-Subject": USER.subject,
    }


@pytest.fixture
def outline_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path))
    workspace = Workspace(tmp_path / "private")
    kernel = EnergyKernel(workspace, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=100)
    service = EnergyService(workspace, kernel, max_attempts=1)
    app = create_private_app(
        workspace,
        service,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 2, 16),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_place_outline_returns_german_lod2_planes(
    outline_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tile = lod2.tile_for("DE-BY", *TRIFTSTRASSE_5)
    lod2_dir = tmp_path / "lod2"
    lod2_dir.mkdir(parents=True, exist_ok=True)
    # Pre-populate the exact TileIndex cache file so no network fetch occurs.
    lod2.TileIndex(lod2_dir, munich_tile).load(tile)

    response = outline_client.post(
        "/places/outline",
        json={
            "schema_version": 1,
            "query": "80538",
            "country": "DE",
            "latitude": TRIFTSTRASSE_5[0],
            "longitude": TRIFTSTRASSE_5[1],
        },
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["country_code"] == "DE"
    assert body["source"] == "LoD2 DE-BY"
    assert len(body["outline"]) >= 3
    assert len(body["planes"]) >= 2
    for plane in body["planes"]:
        assert 0.0 <= plane["tilt_deg"] < 90.0
        assert 1.0 <= plane["area_m2"] <= 3000.0
        assert len(plane["polygon"]) >= 3


def test_place_outline_returns_3d_planes_for_nl_and_falls_back_to_footprints(
    outline_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. NL 3D BAG returns planes
    to_rd = Transformer.from_crs("EPSG:4326", "EPSG:7415", always_xy=True)
    to_wgs84 = Transformer.from_crs("EPSG:7415", "EPSG:4326", always_xy=True)
    lat, lon = 52.3702, 4.8952
    rx, ry = to_rd.transform(lon, lat)
    square = [
        (rx - 5.0, ry - 5.0),
        (rx + 5.0, ry - 5.0),
        (rx + 5.0, ry + 5.0),
        (rx - 5.0, ry + 5.0),
    ]
    model = europe.ModelResult(
        country="NL",
        buildings=[
            Building(
                id="NL.IMBAG.Pand.test",
                address=None,
                footprint=[square],
                planes=[
                    RoofPlane(
                        ring=square, tilt_deg=35.0, azimuth_deg=180.0, area_m2=122.0
                    )
                ],
            )
        ],
        licence=europe.LICENCES["NL"],
        transformer=to_wgs84,
    )
    monkeypatch.setattr(europe, "read", lambda c, la, lo: model if c == "NL" else None)

    nl_res = outline_client.post(
        "/places/outline",
        json={
            "schema_version": 1,
            "query": "1012JS",
            "country": "NL",
            "latitude": lat,
            "longitude": lon,
        },
        headers=_headers(),
    )
    assert nl_res.status_code == 200
    nl_body = nl_res.json()
    assert nl_body["found"] is True
    assert nl_body["source"] == "NL 3D model"
    assert len(nl_body["planes"]) == 1
    assert nl_body["planes"][0]["tilt_deg"] == 35.0
    assert nl_body["planes"][0]["azimuth_deg"] == 180.0

    # 2. Fallback to footprints when 3D model is unavailable (e.g. AT)
    monkeypatch.setattr(
        "linker_engine.roof.footprints.outline_payload",
        lambda c, la, lo: {
            "outline": [[16.3738, 48.2082], [16.3740, 48.2082], [16.3740, 48.2084]],
            "source": "Microsoft building footprints",
            "licence": "CDLA-Permissive 2.0 (Microsoft Building Footprints)",
            "planes": [],
        },
    )
    at_res = outline_client.post(
        "/places/outline",
        json={
            "schema_version": 1,
            "query": "1010",
            "country": "AT",
            "latitude": 48.2082,
            "longitude": 16.3738,
        },
        headers=_headers(),
    )
    assert at_res.status_code == 200
    at_body = at_res.json()
    assert at_body["found"] is True
    assert at_body["source"] == "Microsoft building footprints"
    assert at_body["planes"] == []
