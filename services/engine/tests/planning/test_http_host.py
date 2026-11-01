"""Actual composed ASGI routing, private isolation and native legacy lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from linker_engine.app import create_app as legacy_app
from linker_engine.planning.errors import VersionUnavailable
from linker_engine.planning.guest_claims import GuestClaims
from linker_engine.planning.http_host import EngineApplications, configured_private_app
from linker_engine.planning.records import Actor
from linker_engine.planning.runtime_config import RuntimeConfig
from linker_engine.planning.workspace import Workspace

from .conftest import json_object

TOKEN = "synthetic-host-token"


def settings(directory: Path) -> RuntimeConfig:
    return RuntimeConfig(
        schema_version=1,
        directory=str(directory),
        max_body_bytes=100_000,
        max_csv_bytes=10_000,
        max_page_size=5,
        max_json_depth=16,
        max_intervals=100,
        max_attempts=1,
        absolute_kwh=1e-7,
        absolute_kw=1e-7,
        relative=1e-9,
    )


def test_configured_kernels_share_one_durably_pinned_runtime(tmp_path: Path) -> None:
    config = settings(tmp_path)
    workspace, energy = config.open()
    runtime = energy.kernel.runtime
    kernels = [
        *energy.kernels,
        config.equipment_service(workspace).kernel,
        config.report_service(workspace).kernel,
    ]
    assert all(kernel.runtime is runtime for kernel in kernels)
    assert workspace.blobs.read(runtime.sha256) == runtime.content

    # A new host must still verify the actual bytes in its own workspace.
    blob = workspace.blobs.directory / runtime.sha256[:2] / runtime.sha256
    blob.write_bytes(b"corrupt")
    with pytest.raises(VersionUnavailable, match="hash mismatch"):
        config.open()


def authority() -> dict[str, str]:
    return {
        "X-Linker-Service-Token": TOKEN,
        "X-Linker-Planner-Principal-Kind": "user",
        "X-Linker-Planner-Principal-Subject": "wordpress:host-fixture",
    }


def test_planning_bypasses_neither_its_auth_nor_legacy_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("LINKER_ENGINE_CORS_ORIGINS", "https://client.example")
    private = configured_private_app(settings(tmp_path / "private"))
    app = EngineApplications(legacy_app(), private)
    origin = {
        "Origin": "https://client.example",
        "Access-Control-Request-Method": "POST",
    }
    with TestClient(app) as client:
        for method in ("GET", "HEAD", "POST", "OPTIONS", "DELETE", "TRACE"):
            for path in (
                "/planning",
                "/planning/",
                "/planning/projects/create",
                "/planning/unknown",
            ):
                response = client.request(
                    method, path, headers=origin, content=b"not JSON"
                )
                assert response.status_code == 401, (method, path, response.text)
                assert response.headers["cache-control"] == "no-store, private"
                assert "access-control-allow-origin" not in response.headers
        # Existing health/CORS and POST Gate still belong to the legacy app.
        assert client.get("/health").json() == {"status": "ok"}
        old_options = client.options("/design/residential", headers=origin)
        assert old_options.status_code == 200
        assert old_options.headers["access-control-allow-origin"] == origin["Origin"]
        assert client.post("/design/residential", json={}).status_code == 401
        # No legacy resource-subject/version headers are required on this
        # separate authenticated planning protocol.
        result = client.post(
            "/planning/projects/create",
            headers=authority(),
            json={
                "schema_version": 1,
                "title": "Real persistent fixture",
                "inputs": {"site": {"country": "FR"}},
                "key": "create",
            },
        )
        assert result.status_code == 200, result.text
        project = result.json()
        assert project["revision"] == 1
        read = client.post(
            "/planning/projects/read",
            headers=authority(),
            json={"schema_version": 1, "project_id": project["id"], "revision": None},
        )
        assert read.json() == project
        assert "access-control-allow-origin" not in result.headers
    assert json_object(
        Workspace(tmp_path / "private").blobs.object(project["input_sha256"])
    ) == {"site": {"country": "FR"}}


def test_missing_or_bad_configuration_keeps_legacy_available_and_private_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LINKER_PLANNER_CONFIG", raising=False)
    app = EngineApplications(legacy_app(), configured_private_app())
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        for path in ("/planning", "/planning/", "/planning/version"):
            response = client.post(path, content=b"not JSON")
            assert response.status_code == 503
            assert response.json() == {"error": {"code": "service_unconfigured"}}
            assert response.headers["cache-control"] == "no-store, private"
    config = tmp_path / "invalid.json"
    config.write_text('{"directory":"private fixture must not leak"}')
    monkeypatch.setenv("LINKER_PLANNER_CONFIG", str(config))
    with TestClient(
        EngineApplications(legacy_app(), configured_private_app())
    ) as client:
        response = client.post("/planning/version")
        assert response.status_code == 503
        assert "fixture" not in response.text
        assert client.get("/health").status_code == 200


def test_private_initialisation_failure_does_not_take_down_site_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_self: RuntimeConfig) -> object:
        raise RuntimeError("private failure fixture")

    monkeypatch.setattr(RuntimeConfig, "open", fail)
    app = EngineApplications(
        legacy_app(), configured_private_app(settings(tmp_path / "private"))
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/planning/version")
        assert response.status_code == 503
        assert "private failure fixture" not in response.text


def test_legacy_lifespan_is_forwarded_once() -> None:
    calls: list[str] = []

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        calls.append("start")
        yield
        calls.append("stop")

    old = FastAPI(lifespan=lifespan)
    with TestClient(EngineApplications(old, old)):
        assert calls == ["start"]
    assert calls == ["start", "stop"]


def test_expanded_geometric_budget_is_explicit_and_visible_to_clients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pydantic import ValidationError

    from .test_pv_profile import LIMITS

    monkeypatch.setenv("GENIE_SERVICE_TOKEN", TOKEN)
    values = settings(tmp_path / "private").model_dump(mode="json")
    ordinary = {
        "max_module_steps": 220000,
        "max_samples": 2000000,
        "max_ray_face_checks": 20000000,
        "max_bounds_checks": 50000000,
        "index_leaf_size": 8,
    }
    expanded = {
        "max_module_steps": 841000,
        "max_samples": 4300000,
        "max_modules": 96,
        "max_strings": 6,
        "max_weather_rows": 8760,
    }
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate(
            {**values, "geometric_pv_clear_flat_roof": expanded}
        )
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate(
            {
                **values,
                "pv_preparation": LIMITS.model_dump(mode="json"),
                "geometric_pv_generation": ordinary,
                "geometric_pv_clear_flat_roof": {**expanded, "max_modules": 97},
            }
        )
    config = RuntimeConfig.model_validate(
        {
            **values,
            "pv_preparation": LIMITS.model_dump(mode="json"),
            "geometric_pv_generation": ordinary,
            "geometric_pv_clear_flat_roof": expanded,
        }
    )
    app = EngineApplications(legacy_app(), configured_private_app(config))
    with TestClient(app) as client:
        response = client.post(
            "/planning/version", json={"schema_version": 1}, headers=authority()
        )
        assert response.status_code == 200
        assert response.json()["limits"]["geometric_pv_generation"] == ordinary
        assert response.json()["limits"]["geometric_pv_clear_flat_roof"] == expanded


def test_status_and_limits_describe_only_the_authenticated_principal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", TOKEN)
    config = settings(tmp_path / "private")
    app = EngineApplications(legacy_app(), configured_private_app(config))
    workspace = Workspace(tmp_path / "private")
    guest = Actor("guest", "woocommerce:old")
    GuestClaims(workspace).claim(guest, Actor("user", "wordpress:claimed"), key="login")
    guest_headers = {
        **authority(),
        "X-Linker-Planner-Principal-Kind": guest.kind,
        "X-Linker-Planner-Principal-Subject": guest.subject,
    }
    with TestClient(app) as client:
        version = client.post(
            "/planning/version", json={"schema_version": 1}, headers=authority()
        ).json()
        assert version["limits"] == {
            "max_body_bytes": 100_000,
            "max_csv_bytes": 10_000,
            "max_page_size": 5,
            "max_json_depth": 16,
        }
        retired = client.post(
            "/planning/identity/status",
            json={"schema_version": 1},
            headers=guest_headers,
        )
        assert retired.json() == {"schema_version": 1, "status": "retired"}
        assert "claimed" not in retired.text
        active = client.post(
            "/planning/identity/status", json={"schema_version": 1}, headers=authority()
        )
        assert active.json() == {"schema_version": 1, "status": "active"}
        assert (
            client.post(
                "/planning/identity/status",
                json={"schema_version": 1, "subject": guest.subject},
                headers=authority(),
            ).status_code
            == 422
        )


@pytest.mark.parametrize(
    "field",
    [
        "max_body_bytes",
        "max_page_size",
        "max_intervals",
        "max_attempts",
        "schema_version",
    ],
)
def test_operational_config_has_no_bool_integer_or_extra_field_coercion(
    tmp_path: Path, field: str
) -> None:
    values = settings(tmp_path / "private").model_dump()
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate({**values, field: True})
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate({**values, "hidden_setting": 1})
    assert not (tmp_path / "private").exists()


def test_config_rejects_nonfinite_arithmetic_and_relative_storage(
    tmp_path: Path,
) -> None:
    values = settings(tmp_path / "private").model_dump()
    for patch in (
        {"directory": "relative"},
        {"relative": float("nan")},
        {"absolute_kw": -1},
        {"max_csv_bytes": 100_001},
    ):
        with pytest.raises(ValidationError):
            RuntimeConfig.model_validate({**values, **patch})
