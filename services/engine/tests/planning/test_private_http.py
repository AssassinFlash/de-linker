"""Real ASGI/SQLite/CSV/Worker paths; native WP identity is a separate gate."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.power_series import Measurement
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.service_boundary import (
    ACTOR_SCOPE,
    ServiceBoundary,
    verified_actor,
)
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

TOKEN = "synthetic-private-service-token"
USER = Actor("user", "wordpress:17")
FOREIGN = Actor("user", "wordpress:18")
TEAM = Actor("team", "wordpress:auditor")


def headers(actor: Actor = USER) -> dict[str, str]:
    return {
        "X-Linker-Service-Token": TOKEN,
        "X-Linker-Planner-Principal-Kind": actor.kind,
        "X-Linker-Planner-Principal-Subject": actor.subject,
    }


@dataclass
class Rig:
    workspace: Workspace
    kernel: EnergyKernel
    client: TestClient

    def post(self, path: str, body: Object, actor: Actor = USER) -> Object:
        response = self.client.post(
            path, json={"schema_version": 1, **body}, headers=headers(actor)
        )
        assert response.status_code == 200, (response.status_code, response.text)
        assert response.headers["cache-control"] == "no-store, private"
        return cast(Object, response.json())

    def create(self, key: str, actor: Actor = USER) -> str:
        project = self.post(
            "/projects/create",
            {"title": "Private synthetic fixture", "inputs": {}, "key": key},
            actor,
        )
        assert "owner" not in project
        return str(project["id"])


@pytest.fixture
def rig(workspace: Workspace) -> Iterator[Rig]:
    kernel = EnergyKernel(workspace, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=100)
    service = EnergyService(workspace, kernel, max_attempts=1)
    app = create_private_app(
        workspace,
        service,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 2, 16),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield Rig(workspace, kernel, client)


@pytest.mark.parametrize(
    "method", ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
def test_every_http_method_is_private_even_when_old_gate_mode_is_off(
    rig: Rig, method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "off")
    response = rig.client.request(method, "/projects/read", content="not valid JSON")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("method", "path", "content", "status", "code"),
    [
        ("POST", "/unknown", b"{}", 404, "not_found"),
        ("GET", "/projects/read", b"", 405, "method_not_allowed"),
        ("POST", "/projects/read", b"\xff", 400, "invalid_input"),
        (
            "POST",
            "/projects/create",
            b'{"schema_version":1,"title":"x","inputs":{"text":"\\ud800"},"key":"x"}',
            422,
            "invalid_input",
        ),
        (
            "POST",
            "/projects/create",
            b'{"schema_version":1,"title":"x","inputs":{"\\ud800":0},"key":"x"}',
            422,
            "invalid_input",
        ),
    ],
)
def test_framework_and_unicode_errors_use_the_private_error_contract(
    rig: Rig, method: str, path: str, content: bytes, status: int, code: str
) -> None:
    response = rig.client.request(
        method,
        path,
        content=content,
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert response.status_code == status
    assert response.json() == {"error": {"code": code}}
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert rig.post("/projects/list", {"page_size": 2, "after": None})["items"] == []


def test_unexpected_failure_has_a_code_without_private_exception_content(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("private fixture content must not escape")

    monkeypatch.setattr(rig.workspace, "create", fail)
    response = rig.client.post(
        "/projects/create",
        json={"schema_version": 1, "title": "x", "inputs": {}, "key": "x"},
        headers=headers(),
    )
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "execution_failed"}}
    assert response.headers["cache-control"] == "no-store, private"


def test_deep_small_json_is_rejected_before_recursive_union_error_amplification(
    rig: Rig,
) -> None:
    body = (
        b'{"schema_version":1,"title":"x","inputs":{"tree":'
        + b"[" * 1200
        + b"0"
        + b"]" * 1200
        + b'},"key":"deep"}'
    )
    assert len(body) < 2500
    response = rig.client.post(
        "/projects/create",
        content=body,
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "json_too_deep"}}
    assert len(response.content) < 100
    assert rig.post("/projects/list", {"page_size": 2, "after": None})["items"] == []


def test_depth_check_ignores_brackets_quotes_and_escapes_inside_strings(
    rig: Rig,
) -> None:
    value = "å😀" + '{["\\' * 1000
    project = rig.post(
        "/projects/create",
        {"title": "Unicode fixture", "inputs": {"text": value}, "key": "text"},
    )
    assert project["inputs"] == {"text": value}


def test_validation_diagnostics_are_bounded_and_explicitly_truncated(rig: Rig) -> None:
    response = rig.client.post(
        "/projects/create",
        json={
            "schema_version": 1,
            "title": "x",
            "inputs": {},
            "key": "bounded",
            **{f"unknown{n}" + "a" * 200: "private-value" for n in range(100)},
        },
        headers=headers(),
    )
    assert response.status_code == 422
    detail = response.json()["error"]
    assert detail["truncated"] is True
    assert len(detail["fields"]) == 16
    assert len(response.content) < 3000
    assert "private-value" not in response.text
    for field in detail["fields"]:
        assert len(field["path"]) <= 16
        assert all(len(part) <= 64 for part in field["path"])


def exercise_boundary(
    raw_headers: list[tuple[bytes, bytes]],
    chunks: list[Message],
    *,
    configured: bool = True,
    limit: int = 8,
) -> tuple[list[Message], list[str], int]:
    messages: list[Message] = []
    actors: list[str] = []
    consumed = 0

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        actors.append(verified_actor(scope).key)
        await receive()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"public")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    boundary = ServiceBoundary(
        downstream,
        credential=lambda: TOKEN if configured else "",
        max_body_bytes=limit,
        max_json_depth=16,
    )

    async def run() -> None:
        nonlocal consumed

        async def receive() -> Message:
            nonlocal consumed
            assert consumed < len(chunks), "boundary read beyond available request"
            message = chunks[consumed]
            consumed += 1
            return message

        async def send(message: Message) -> None:
            messages.append(message)

        await boundary(
            {
                "type": "http",
                "method": "POST",
                "headers": raw_headers,
                ACTOR_SCOPE: FOREIGN,
            },
            receive,
            send,
        )

    asyncio.run(run())
    return messages, actors, consumed


def wire_headers() -> list[tuple[bytes, bytes]]:
    return [
        (name.lower().encode(), value.encode()) for name, value in headers().items()
    ]


def test_missing_configuration_and_invalid_auth_do_not_read_any_body() -> None:
    for raw_headers, configured, status in (
        ([], True, 401),
        (wire_headers(), False, 503),
    ):
        messages, actors, consumed = exercise_boundary(
            raw_headers, [], configured=configured
        )
        assert messages[0]["status"] == status and not actors and consumed == 0


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_token",
        "duplicate_kind",
        "missing_subject",
        "bad_kind",
        "nonascii_subject",
    ],
)
def test_ambiguous_or_unverified_principal_is_rejected_before_parsing(
    change: str,
) -> None:
    values = wire_headers()
    if change == "duplicate_token":
        values.append((b"x-linker-service-token", TOKEN.encode()))
    elif change == "duplicate_kind":
        values.append((b"x-linker-planner-principal-kind", b"user"))
    elif change == "missing_subject":
        values = [
            (key, value)
            for key, value in values
            if key != b"x-linker-planner-principal-subject"
        ]
    elif change == "bad_kind":
        values = [
            (key, b"admin" if key == b"x-linker-planner-principal-kind" else value)
            for key, value in values
        ]
    else:
        values = [
            (key, b"\xff" if key == b"x-linker-planner-principal-subject" else value)
            for key, value in values
        ]
    messages, actors, consumed = exercise_boundary(values, [])
    assert messages[0]["status"] in (400, 401) and not actors and consumed == 0


@pytest.mark.parametrize("declared", [b"9", b"9" * 5000, b"-1", b"\xb2", b"8.0"])
def test_declared_length_has_strict_finite_bounded_parsing(declared: bytes) -> None:
    messages, actors, consumed = exercise_boundary(
        wire_headers() + [(b"content-length", declared)], []
    )
    assert messages[0]["status"] in (400, 413) and not actors and consumed == 0


def test_streamed_cap_disconnect_length_mismatch_and_principal_overwrite() -> None:
    messages, actors, _ = exercise_boundary(
        wire_headers(),
        [
            {"type": "http.request", "body": b"12345", "more_body": True},
            {"type": "http.request", "body": b"6789", "more_body": False},
        ],
    )
    assert messages[0]["status"] == 413 and not actors
    for raw_headers, chunks in (
        (wire_headers(), [{"type": "http.disconnect"}]),
        (
            wire_headers() + [(b"content-length", b"2")],
            [{"type": "http.request", "body": b"1"}],
        ),
    ):
        messages, actors, _ = exercise_boundary(raw_headers, chunks)
        assert messages[0]["status"] == 400 and not actors
    messages, actors, _ = exercise_boundary(
        wire_headers() + [(b"content-length", b"0" * 5000 + b"1")],
        [{"type": "http.request", "body": b"x"}],
    )
    assert messages[0]["status"] == 200 and actors == [USER.key]
    assert (b"cache-control", b"no-store, private") in messages[0]["headers"]
    assert (b"cache-control", b"public") not in messages[0]["headers"]


def test_browser_owner_context_and_schema_coercions_are_not_commands(rig: Rig) -> None:
    for extra in (
        {"owner": FOREIGN.key},
        {"actor": {"kind": "team"}},
        {"context": {"models": {}}},
    ):
        response = rig.client.post(
            "/projects/create",
            headers=headers(),
            json={
                "schema_version": 1,
                "title": "fixture",
                "inputs": {},
                "key": "create",
                **extra,
            },
        )
        assert response.status_code == 422
    response = rig.client.post(
        "/projects/create",
        headers=headers(),
        json={
            "schema_version": True,
            "title": "sensitive-name-not-in-error",
            "inputs": {},
            "key": "create",
        },
    )
    assert (
        response.status_code == 422
        and "sensitive-name-not-in-error" not in response.text
    )
    assert response.json()["error"]["fields"][0]["path"] == ["body", "schema_version"]
    assert (
        rig.client.post(
            "/version", headers=headers(), json={"schema_version": 1}
        ).json()["runtime_sha256"]
        == rig.kernel.runtime.sha256
    )


def test_owned_project_refresh_reopen_pagination_and_readonly_team(rig: Rig) -> None:
    ids = [rig.create(f"project-{index}") for index in range(3)]
    foreign = rig.create("foreign", FOREIGN)
    first = rig.post("/projects/list", {"page_size": 2, "after": None})
    second = rig.post("/projects/list", {"page_size": 2, "after": first["next"]})
    items = cast(list[Object], first["items"]) + cast(list[Object], second["items"])
    assert {item["id"] for item in items} == set(ids) and foreign not in {
        item["id"] for item in items
    }
    assert second["next"] is None and all("inputs" not in item for item in items)
    read = {"schema_version": 1, "project_id": ids[0], "revision": None}
    assert (
        rig.client.post(
            "/projects/read", json=read, headers=headers(FOREIGN)
        ).status_code
        == 404
    )
    assert (
        rig.post("/projects/read", {"project_id": ids[0], "revision": None}, TEAM)["id"]
        == ids[0]
    )
    assert (
        rig.client.post(
            "/projects/create",
            json={
                "schema_version": 1,
                "title": "team cannot create",
                "inputs": {},
                "key": "team",
            },
            headers=headers(TEAM),
        ).status_code
        == 404
    )
    revised = rig.post(
        "/projects/revise",
        {
            "project_id": ids[0],
            "expected_revision": 1,
            "inputs": {"site": {"country": "NL"}},
            "key": "edit",
        },
    )
    assert revised["revision"] == 2
    assert (
        rig.post("/projects/read", {"project_id": ids[0], "revision": 1})["inputs"]
        == {}
    )
    assert Workspace(rig.workspace.database.path.parent).get(USER, ids[0]).inputs == {
        "site": {"country": "NL"}
    }
    stale = rig.client.post(
        "/projects/revise",
        json={
            "schema_version": 1,
            "project_id": ids[0],
            "expected_revision": 1,
            "inputs": {},
            "key": "stale",
        },
        headers=headers(),
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "conflict"


def test_full_http_csv_enqueue_worker_result_history_and_private_bytes(
    rig: Rig,
) -> None:
    project_id = rig.create("create")
    profiles: dict[str, str] = {}
    for role, powers in (
        ("gross_load", (2, 2)),
        ("pv_available_ac", (4, 0)),
        ("aux_ac", (0, 0)),
    ):
        content = f"time,power\n2024-03-30T23:00:00Z,{powers[0]}\n2024-03-31T00:00:00Z,{powers[1]}\n".encode()
        mapping = CsvMapping(
            "time",
            "power",
            cast(Measurement, role),
            "interval_average_kw",
            "start",
            "Europe/Berlin",
            "synthetic",
            3600,
            ",",
            ".",
        )
        asset = rig.post(
            "/profiles/csv",
            {
                "project_id": project_id,
                "content_base64": base64.b64encode(content).decode(),
                "mapping": mapping.document(),
                "source_label": "Synthetic analytic fixture",
                "rights_note": "created by this test",
                "key": role,
            },
        )
        profiles[role] = str(asset["id"])
        assert (
            cast(Object, cast(Object, asset["metadata"])["provenance"])["basis"]
            == "user_upload_declaration"
        )
        download = {
            "schema_version": 1,
            "project_id": project_id,
            "asset_id": asset["id"],
        }
        assert (
            rig.client.post("/assets/content", json=download, headers=headers()).content
            == content
        )
        assert (
            rig.client.post(
                "/assets/content", json=download, headers=headers(FOREIGN)
            ).status_code
            == 404
        )
    battery = rig.post(
        "/battery/scenario",
        {
            "project_id": project_id,
            "source_note": "Analytic scenario, no actual SKU",
            "key": "battery",
            "parameters": {
                "schema_version": 1,
                "model": "constant_window_single_ac_bus_v1",
                "parameter_basis": "explicit_scenario",
                "usable_window_kwh": 5,
                "charge_ac_kw": 5,
                "discharge_ac_kw": 5,
                "eta_charge": 0.9,
                "eta_discharge": 0.9,
                "internal_aux_kw": 0,
                "standing_loss_rate_per_hour": 0,
            },
        },
    )
    energy: Object = {
        "schema_version": 1,
        "gross_load_asset_id": profiles["gross_load"],
        "critical_load_asset_id": None,
        "pv_available_asset_id": profiles["pv_available_ac"],
        "aux_ac_asset_id": profiles["aux_ac"],
        "battery_parameters_asset_id": battery["id"],
        "initial_inventory": {
            "pv_kwh": 0,
            "grid_kwh": 0,
            "initial_unknown_kwh": 0,
            "basis": "synthetic_fixture",
            "source_note": "explicit empty initial state",
        },
        "schedule": [
            {
                "start_utc": "2024-03-30T23:00:00Z",
                "end_utc": "2024-03-31T01:00:00Z",
                "mode": "connected",
                "reserve_kwh": 0,
                "import_cap_kw": None,
                "export_cap_kw": 0,
                "pv_enabled": True,
                "allow_grid_charge": False,
            }
        ],
        "controller": "self_consumption_with_reserve_v1",
        "terminal_min_kwh": 0,
    }
    revision = rig.post(
        "/projects/revise",
        {
            "project_id": project_id,
            "expected_revision": 1,
            "inputs": {"energy_replay": energy},
            "key": "scenario",
        },
    )
    run = rig.post(
        "/runs/energy",
        {"project_id": project_id, "expected_revision": 2, "key": "evaluate"},
    )
    assert run["state"] == "queued" and run["result"] is None
    rig.post(
        "/projects/revise",
        {
            "project_id": project_id,
            "expected_revision": 2,
            "inputs": {"note": "new revision after queue"},
            "key": "newer",
        },
    )
    assert Worker(
        Jobs(rig.workspace),
        "http-fixture-worker",
        {"evaluate": rig.kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    completed = rig.post("/runs/read", {"run_id": run["id"]})
    assert completed["state"] == "succeeded" and completed["is_current"] is False
    result = cast(Object, completed["result"])
    assert result["input_sha256"] == revision["input_sha256"]
    metrics = cast(Object, result["metrics"])
    assert metrics["solar_load_kwh"] == pytest.approx(3.62)
    assert metrics["grid_import_kwh"] == pytest.approx(0.38)
    assert cast(Object, result["equipment_release"])["status"] == "not_assessed"
    trace_body = {"schema_version": 1, "run_id": run["id"]}
    trace = rig.client.post("/runs/trace", json=trace_body, headers=headers())
    assert trace.status_code == 200 and digest(trace.content) == result["trace_sha256"]
    assert len(json.loads(trace.content)["flows"]) == 2
    for path in ("/runs/read", "/runs/trace", "/runs/cancel"):
        assert (
            rig.client.post(path, json=trace_body, headers=headers(FOREIGN)).status_code
            == 404
        )
    listed = rig.post(
        "/projects/runs",
        {
            "project_id": project_id,
            "page_size": 1,
            "before_created_at": None,
            "before_id": None,
        },
    )
    assert cast(list[Object], listed["items"])[0]["id"] == run["id"]
    assert "result" not in cast(list[Object], listed["items"])[0]
    assert listed["next"] is None


def test_file_page_caps_and_foreign_writes_do_not_publish_input_blobs(rig: Rig) -> None:
    project_id = rig.create("create")
    initial = set(rig.workspace.blobs.directory.rglob("*"))
    body: Object = {
        "schema_version": 1,
        "project_id": project_id,
        "expected_revision": 1,
        "inputs": {"private_foreign_attempt": "should never be written"},
        "key": "foreign",
    }
    assert (
        rig.client.post(
            "/projects/revise", json=body, headers=headers(FOREIGN)
        ).status_code
        == 404
    )
    assert set(rig.workspace.blobs.directory.rglob("*")) == initial
    assert (
        rig.client.post(
            "/projects/list",
            json={"schema_version": 1, "page_size": 3, "after": None},
            headers=headers(),
        ).status_code
        == 422
    )
    assert (
        rig.client.post(
            "/projects/runs",
            json={
                "schema_version": 1,
                "project_id": project_id,
                "page_size": 1,
                "before_created_at": 100,
                "before_id": None,
            },
            headers=headers(),
        ).status_code
        == 422
    )
    assert (
        rig.client.post(
            "/projects/create", content=b"x" * 100_001, headers=headers()
        ).status_code
        == 413
    )
    assert encode(body)  # fixture itself is valid finite JSON, not a parse failure


def test_run_history_is_bounded_and_paged_without_loading_result_blobs(
    rig: Rig, context: Context
) -> None:
    project_id = rig.create("history")
    ids = {
        rig.workspace.evaluate(
            USER, project_id, 1, context, key=f"fixture-{index}", max_attempts=1
        ).id
        for index in range(3)
    }
    first = rig.post(
        "/projects/runs",
        {
            "project_id": project_id,
            "page_size": 2,
            "before_created_at": None,
            "before_id": None,
        },
    )
    second = rig.post(
        "/projects/runs",
        {"project_id": project_id, "page_size": 2, **cast(Object, first["next"])},
    )
    items = cast(list[Object], first["items"]) + cast(list[Object], second["items"])
    assert {item["id"] for item in items} == ids and len(items) == 3
    assert second["next"] is None and all(
        "manifest" not in item and "result" not in item for item in items
    )


@pytest.mark.parametrize("content", [b"x" * 10_001, None])
def test_csv_file_ceiling_and_bad_base64_are_rejected_before_asset_publication(
    rig: Rig, content: bytes | None
) -> None:
    project_id = rig.create("csv-limit")
    initial = set(rig.workspace.blobs.directory.rglob("*"))
    body: Object = {
        "schema_version": 1,
        "project_id": project_id,
        "content_base64": "!!"
        if content is None
        else base64.b64encode(content).decode(),
        "mapping": CsvMapping(
            "time",
            "power",
            "gross_load",
            "interval_average_kw",
            "start",
            "UTC",
            "synthetic",
            3600,
            ",",
            ".",
        ).document(),
        "source_label": "Synthetic file rejection fixture",
        "rights_note": "created by this test",
        "key": "file",
    }
    response = rig.client.post("/profiles/csv", json=body, headers=headers())
    assert (
        response.status_code == 422
        and response.json()["error"]["code"] == "invalid_input"
    )
    assert set(rig.workspace.blobs.directory.rglob("*")) == initial
