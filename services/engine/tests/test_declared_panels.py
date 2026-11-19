import pytest
from conftest import PANEL_ELECTRICAL
from fastapi.testclient import TestClient

from linker_engine.engine import Engine
from linker_engine.publication import Publication, PublicationChanged, View


def test_residential_without_declared_panel_keeps_string_design_unassessed(
    client: TestClient,
) -> None:
    reply = client.post(
        "/design/residential",
        json={
            "plz": "80538",
            "country": "DE",
            "annual_kwh": 5000,
            "pv_kwp": 10,
            "phase": 3,
        },
    )
    assert reply.status_code == 200
    design = reply.json()
    assert design["selected"]["strings"] is None
    assert design["publication"]["reference_inputs"] == []
    assert all(line["role"] != "pv_module" for line in design["selected"]["lines"])


def test_withdrawn_panel_receipt_cannot_authorise_new_work(engine: Engine) -> None:
    from linker_engine.publication import ENGINEERING_CONTRACT

    scope = {
        "engineering_contract": ENGINEERING_CONTRACT,
        "compatibility_revision": "retained-contract",
        "products": [],
        "documents": [],
        "reference_inputs": [{"kind": "pv_module"}],
    }
    with pytest.raises(PublicationChanged):
        Publication({}).confirm(
            View(engine, scope),
            current={
                "compatibility_revision": "retained-contract",
                "products": [],
                "documents": [],
            },
        )


def test_string_design_uses_supplied_panel_without_a_manufacturer(
    client: TestClient,
) -> None:
    reply = client.post(
        "/design/residential",
        json={
            "plz": "80538",
            "country": "DE",
            "annual_kwh": 5000,
            "pv_kwp": 10,
            "phase": 3,
            "module": PANEL_ELECTRICAL.model_dump(),
        },
    )
    assert reply.status_code == 200
    design = reply.json()
    assert design["selected"]["strings"]["module"] == "460 Wp"
    assert design["publication"]["reference_inputs"] == []
