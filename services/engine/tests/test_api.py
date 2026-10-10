"""The HTTP surface the configurator calls."""

from conftest import TRIFTSTRASSE_5
from fastapi.testclient import TestClient

RESIDENTIAL = {"plz": "80538", "annual_kwh": 5000, "pv_kwp": 10, "phase": 3}


def test_postcode_gives_position_state_and_imagery(client: TestClient) -> None:
    response = client.get("/geo/plz/80538")
    assert response.status_code == 200
    body = response.json()
    assert (body["state"], round(body["latitude"], 3)) == ("DE-BY", 48.14)
    assert "geoservices.bayern.de" in body["imagery"]["tiles"][0]
    assert body["imagery"]["licence"] == "CC BY 4.0"
    assert client.get("/geo/plz/00000").status_code == 404


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
    response = client.post(
        "/report/pdf", json={"input": {**RESIDENTIAL, "locale": "en"}}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    bad = client.post(
        "/report/pdf",
        json={"input": RESIDENTIAL, "logo": "data:text/plain;base64,eA=="},
    )
    assert bad.status_code == 422


def test_roof_outline(client: TestClient) -> None:
    latitude, longitude = TRIFTSTRASSE_5
    response = client.post(
        "/roof/outline",
        json={
            "plz": "80538",
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
            "grid_connection_kva": 100,
            "annual_kwh": 150000,
            "goals": ["self_consumption"],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "indicative"
