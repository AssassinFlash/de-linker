"""The HTTP surface the configurator calls."""

import io

from conftest import TRIFTSTRASSE_5
from fastapi.testclient import TestClient
from pypdf import PdfReader

RESIDENTIAL = {
    "plz": "80538",
    "country": "DE",
    "annual_kwh": 5000,
    "pv_kwp": 10,
    "phase": 3,
}


def test_postcode_gives_position_state_and_imagery(client: TestClient) -> None:
    # The country names the place: 80538 is both a Bavarian and a Ukrainian
    # code, so the country parameter is what makes it one site.
    response = client.get("/geo/plz/80538", params={"country": "DE"})
    assert response.status_code == 200
    body = response.json()
    assert (body["state"], round(body["latitude"], 3)) == ("DE-BY", 48.14)
    assert "geoservices.bayern.de" in body["imagery"]["tiles"][0]
    assert body["imagery"]["licence"] == "CC BY 4.0"
    # Without a country the same digits name more than one country, so the
    # answer is "not one place" rather than a guess.
    assert client.get("/geo/plz/80538").status_code == 404
    assert client.get("/geo/plz/00000", params={"country": "DE"}).status_code == 404


def test_a_greek_or_portuguese_postcode_answers_with_its_own_country(
    client: TestClient,
) -> None:
    athens = client.get("/geo/plz/10431", params={"country": "GR"})
    assert athens.status_code == 200
    greek = athens.json()
    assert greek["country"] == "GR" and greek["timezone"] == "Europe/Athens"
    assert abs(greek["latitude"] - 37.98) < 0.05
    lisbon = client.get("/geo/plz/3750-000", params={"country": "PT"})
    assert lisbon.status_code == 200
    assert lisbon.json()["timezone"] == "Europe/Lisbon"


def test_residential_design_answers_with_the_specified_shape(
    client: TestClient,
) -> None:
    response = client.post("/design/residential", json={**RESIDENTIAL, "locale": "de"})
    assert response.status_code == 200
    body = response.json()
    for key in (
        "yield",
        "storage",
        "metrics",
        "candidates",
        "selected",
        "rules",
        "warnings",
        "report",
    ):
        assert key in body
    assert body["storage"]["usable_kwh_range"] == {"low": 7.5, "high": 7.5}
    assert set(body["candidates"]) == {
        "inverters",
        "batteries",
        "accessories",
        "excluded",
    }
    assert body["report"]["title"] == "Auslegungsbericht"


def test_invalid_input_is_refused_by_field(client: TestClient) -> None:
    assert (
        client.post(
            "/design/residential", json={**RESIDENTIAL, "plz": "8053"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/design/residential", json={**RESIDENTIAL, "plz": "00000"}
        ).status_code
        == 422
    )
    planes = [{"kwp": 4, "tilt_deg": 30, "azimuth_deg": 90}]
    assert (
        client.post(
            "/design/residential", json={**RESIDENTIAL, "planes": planes}
        ).status_code
        == 422
    )


def test_report_pdf(client: TestClient) -> None:
    fingerprint = client.post("/design/residential", json=RESIDENTIAL).json()[
        "selection_fingerprint"
    ]
    response = client.post(
        "/report/pdf",
        json={
            "input": {**RESIDENTIAL, "locale": "en"},
            "selection_fingerprint": fingerprint,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # The served PDF names the generation it was built from, so a downloaded
    # sheet can be traced back to the data behind its numbers.
    text = "\n".join(
        page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages
    )
    publication = client.post("/design/residential", json=RESIDENTIAL).json()[
        "publication"
    ]
    assert publication["source_revision"][:12] in text
    assert "Revision" in text
    bad = client.post(
        "/report/pdf",
        json={
            "input": RESIDENTIAL,
            "logo": "data:text/plain;base64,eA==",
            "selection_fingerprint": fingerprint,
        },
    )
    assert bad.status_code == 422


def test_roof_outline(client: TestClient) -> None:
    latitude, longitude = TRIFTSTRASSE_5
    response = client.post(
        "/roof/outline",
        json={
            "plz": "80538",
            "country": "DE",
            "location": {"latitude": latitude, "longitude": longitude},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["found"] and body["modules"] > 0 and body["address"] == "Triftstraße 5"


def test_commercial_without_profile(client: TestClient) -> None:
    response = client.post(
        "/design/commercial",
        json={
            "plz": "80538",
            "country": "DE",
            "grid_connection_kva": 100,
            "annual_kwh": 150000,
            "goals": ["self_consumption"],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "indicative"


def test_a_non_german_postcode_is_served_by_its_country_mosaic(
    client: TestClient,
) -> None:
    # Germany publishes per state and the others publish one national service,
    # so the state lookup misses abroad and the country lookup has to answer.
    # Measured 2026-11-16: each of these endpoints returned a real aerial tile.
    for code, country, host in (
        ("1012JS", "NL", "service.pdok.nl"),
        ("75001", "FR", "data.geopf.fr"),
        ("28001", "ES", "ign.es"),
        ("8001", "CH", "wms.geo.admin.ch"),
        ("20121", "IT", "de-linker.com/wp-json/linker/v1/imagery/it"),
        ("SW1A 1AA", "GB", "image.discomap.eea.europa.eu"),
    ):
        response = client.get(f"/geo/plz/{code}", params={"country": country})
        assert response.status_code == 200, code
        body = response.json()
        assert body["imagery"] is not None, code
        assert host in body["imagery"]["tiles"][0], code
        assert body["imagery"]["licence"], code


def test_a_country_without_a_recorded_mosaic_answers_no_imagery(
    client: TestClient,
) -> None:
    # Ukraine sits outside the EEA Copernicus VHR mosaic and has no open
    # national service recorded, so the map falls back rather than requesting a
    # transparent tile.
    response = client.get("/geo/plz/01001", params={"country": "UA"})
    assert response.status_code == 200
    assert response.json()["imagery"] is None
