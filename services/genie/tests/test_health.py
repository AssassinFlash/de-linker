from fastapi.testclient import TestClient

from linker_genie.app import app
from linker_genie.preparation import RUNTIME_SERVING_REVISION


def test_health_reports_ok_and_the_actual_serving_release() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "serving_revision": RUNTIME_SERVING_REVISION,
    }
