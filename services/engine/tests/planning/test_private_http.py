"""Real ASGI/SQLite/CSV/Worker paths; native WP identity is a separate gate."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from conftest import publication_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from linker_engine.planning import timezone_rules
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.csv_mapping import CsvMapping
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.execution_control import ExecutionControl
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
from linker_engine.publication import Publication, PublicationUnavailable

from .conftest import FixtureObject, json_object

TOKEN = "synthetic-private-service-token"
USER = Actor("user", "wordpress:17")
FOREIGN = Actor("user", "wordpress:18")
TEAM = Actor("team", "wordpress:auditor")


def brief_inputs(timezone: str) -> FixtureObject:
    return {
        "brief": {
            "schema_version": 1,
            "project_use": "commercial",
            "system_scope": None,
            "site": {
                "country_code": "NO",
                "location_label": "Synthetic site",
                "latitude": None,
                "longitude": None,
                "coordinate_basis": "not_provided",
                "timezone": timezone,
            },
            "annual_load": {"kwh": None, "basis": None, "source_note": ""},
            "project_note": "",
        }
    }


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

    def post(
        self, path: str, body: FixtureObject, actor: Actor = USER
    ) -> FixtureObject:
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

    def replay(
        self, path: str, body: FixtureObject, actor: Actor = USER
    ) -> FixtureObject:
        return self.post("/operations/replay" + path, body, actor)


def test_geometry_import_has_owned_original_receipt_and_separate_project_save(
    rig: Rig,
) -> None:
    root = Path(__file__).resolve().parents[4]
    source = (root / "fixtures/planning/source-roof-wgs84.geojson").read_bytes()
    options = json.loads(
        (root / "fixtures/planning/geometry-import-options.json").read_text()
    )
    project_id = rig.create("geometry-import")
    command: FixtureObject = {
        "project_id": project_id,
        "content_base64": base64.b64encode(source).decode(),
        "options": options,
        "key": "owned-source",
    }
    asset = rig.post("/geometry/import", command)
    assert asset["purpose"] == "geometry_import_v1"
    assert asset["content_sha256"] == digest(source)
    assert rig.post("/geometry/import", command) == asset
    replay = rig.replay("/geometry/import", command)
    assert replay["status"] == "replayed" and replay["result"] == asset
    before = rig.post("/projects/read", {"project_id": project_id, "revision": None})
    assert before["revision"] == 1 and before["inputs"] == {}
    metadata = cast(Object, asset["metadata"])
    prepared = cast(Object, metadata["geometry_import"])
    geometry = cast(Object, prepared["geometry"])
    source_id = str(cast(list[Object], geometry["sources"])[0]["id"])
    inputs: FixtureObject = {
        "geometry": geometry,
        "geometry_imports": {"schema_version": 1, "selected": {source_id: asset["id"]}},
    }
    saved = rig.post(
        "/projects/revise",
        {
            "project_id": project_id,
            "expected_revision": 1,
            "inputs": inputs,
            "key": "attach-source",
        },
    )
    assert saved["revision"] == 2 and saved["inputs"] == inputs
    tampered = json.loads(json.dumps(inputs))
    tampered["geometry"]["sources"][0]["reference_sha256"] = "0" * 64
    refused_hash = rig.client.post(
        "/projects/revise",
        json={
            "schema_version": 1,
            "project_id": project_id,
            "expected_revision": 2,
            "inputs": tampered,
            "key": "tampered-hash",
        },
        headers=headers(),
    )
    assert refused_hash.status_code == 422
    assert (
        rig.post("/projects/read", {"project_id": project_id, "revision": None})[
            "revision"
        ]
        == 2
    )
    original = rig.client.post(
        "/assets/content",
        json={"schema_version": 1, "project_id": project_id, "asset_id": asset["id"]},
        headers=headers(),
    )
    assert original.content == source
    before_blobs = set(rig.workspace.blobs.directory.rglob("*"))
    refused = rig.client.post(
        "/geometry/import",
        json={"schema_version": 1, **command, "content_base64": "!"},
        headers=headers(FOREIGN),
    )
    assert refused.status_code == 404
    assert set(rig.workspace.blobs.directory.rglob("*")) == before_blobs
    other_project = rig.create("different-geometry-project")
    foreign_asset = rig.client.post(
        "/projects/revise",
        json={
            "schema_version": 1,
            "project_id": other_project,
            "expected_revision": 1,
            "inputs": inputs,
            "key": "foreign-source",
        },
        headers=headers(),
    )
    assert foreign_asset.status_code == 404
    invalid_new = rig.client.post(
        "/projects/create",
        json={
            "schema_version": 1,
            "title": "Cannot borrow files",
            "inputs": inputs,
            "key": "borrowed-source",
        },
        headers=headers(),
    )
    assert invalid_new.status_code == 422


def test_geometry_review_uses_owned_draft_without_publishing_or_saving(
    rig: Rig,
) -> None:
    path = Path(__file__).resolve().parents[4] / "fixtures/planning/geometry-flat.json"
    geometry = json.loads(path.read_text())
    project_id = rig.create("geometry")
    before = set(rig.workspace.blobs.directory.rglob("*"))
    body: FixtureObject = {"project_id": project_id, "geometry": geometry}
    report = rig.post("/geometry/review", body)
    assert (
        report["module_count"] == 5 and report["engineering_status"] == "not_evaluated"
    )
    assert report["geometry_sha256"] == digest(encode(geometry))
    assert rig.workspace.get(USER, project_id).revision == 1
    assert rig.workspace.get(USER, project_id).inputs == {}
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    # Foreign access is refused before the intentionally unusable geometry is read.
    response = rig.client.post(
        "/geometry/review",
        json={"schema_version": 1, "project_id": project_id, "geometry": {}},
        headers=headers(FOREIGN),
    )
    assert response.status_code == 404
    response = rig.client.post(
        "/geometry/review",
        json={"schema_version": 1, "project_id": project_id, "geometry": {}},
        headers=headers(),
    )
    assert response.status_code == 422
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_geometry_save_refuses_bad_references_and_keeps_unfinished_polygon(
    rig: Rig,
) -> None:
    path = Path(__file__).resolve().parents[4] / "fixtures/planning/geometry-flat.json"
    geometry = json.loads(path.read_text())
    project_id = rig.create("geometry-write")
    geometry["arrays"][0]["roof_id"] = "foreign"
    before = set(rig.workspace.blobs.directory.rglob("*"))
    command = {
        "schema_version": 1,
        "project_id": project_id,
        "expected_revision": 1,
        "inputs": {"geometry": geometry},
        "key": "geometry-save",
    }
    response = rig.client.post("/projects/revise", json=command, headers=headers())
    assert response.status_code == 422
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    geometry["arrays"][0]["roof_id"] = "roof"
    geometry["roofs"][0]["boundary_uv"] = [[0, 0], [10, 10], [0, 10], [10, 0]]
    saved = rig.post(
        "/projects/revise",
        cast(
            Object,
            {key: value for key, value in command.items() if key != "schema_version"},
        ),
    )
    assert saved["revision"] == 2
    assert rig.workspace.get(USER, project_id).inputs == {"geometry": geometry}
    report = rig.post(
        "/geometry/review", {"project_id": project_id, "geometry": geometry}
    )
    assert report["geometry_status"] == "conflicts_detected"


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


def test_current_products_use_shared_woo_preparation_and_close_on_change(
    rig: Rig, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Reuse the site's actual service loader and real engineering fixture.
    assert isinstance(client.app, FastAPI)
    provider = client.app.state.planning_product_provider
    loaded = provider()
    manifest = publication_manifest(loaded.publication.feed)
    chosen = manifest["products"][0]
    reference = next(
        row
        for row in manifest["products"]
        if row.get("engineering_role") == "reference_pv_module"
    )
    chosen["ready"]["engineering"] = True
    reference["ready"]["engineering"] = True
    calls = 0
    mode = "current"

    def current(_self: Publication) -> FixtureObject:
        nonlocal calls
        calls += 1
        if mode == "unavailable":
            raise PublicationUnavailable("source offline")
        value = json.loads(json.dumps(manifest))
        if mode == "changed" and calls > 1:
            value["products"][0]["ready"]["engineering"] = False
        return json_object(value)

    monkeypatch.setattr(Publication, "read", current)
    service = EnergyService(rig.workspace, rig.kernel, max_attempts=1)
    app = create_private_app(
        rig.workspace,
        service,
        credential=lambda: TOKEN,
        limits=HttpLimits(100_000, 10_000, 2, 16),
        product_provider=provider,
    )
    body = {"schema_version": 1}
    path = "/products/current"
    with TestClient(app, raise_server_exceptions=False) as private:
        assert private.post(path, json=body).status_code == 401
        reply = private.post(path, json=body, headers=headers())
        assert reply.status_code == 200, reply.text
        assert reply.headers["cache-control"] == "no-store, private"
        result = reply.json()
        template = result["pv_modules"][0]
        specification = template["specification"]
        assert specification["stc_power_w"] == 460
        assert specification["width_m"] == 1.134
        assert template["parameters"]["gamma_pdc_per_c"] == -0.0029
        assert specification["source"]["woo"]["product_id"] == reference["product_id"]
        assert [row["id"] for row in result["products"]] == [chosen["product_id"]]
        assert [row["canonical_product_id"] for row in result["references"]] == [
            reference["product_id"]
        ]
        assert (
            result["loaded_source_revision"]
            == loaded.publication.feed["source_revision"]
        )
        assert result["publication"]["products"] == [
            {key: row[key] for key in ("product_id", "product_revision")}
            for row in (chosen, reference)
        ]
        geometry = json.loads(
            (
                Path(__file__).resolve().parents[4]
                / "fixtures/planning/geometry-flat.json"
            ).read_text()
        )
        geometry["module_specs"] = [
            {**specification, "id": geometry["module_specs"][0]["id"]}
        ]
        create = {
            "schema_version": 1,
            "title": "Woo-bound fixture",
            "inputs": {"geometry": geometry},
            "key": "woo-create",
        }
        created = private.post("/projects/create", json=create, headers=headers())
        assert created.status_code == 200, created.text
        changed = json.loads(json.dumps(create["inputs"]))
        changed["geometry"]["module_specs"][0]["stc_power_w"] += 1
        refused = private.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": created.json()["id"],
                "expected_revision": 1,
                "inputs": changed,
                "key": "fake-woo-figure",
            },
            headers=headers(),
        )
        assert refused.status_code == 422
        stale = json.loads(json.dumps(create["inputs"]))
        stale["geometry"]["module_specs"][0]["source"]["woo"]["product_revision"] = (
            "f" * 64
        )
        refused = private.post(
            "/projects/revise",
            json={
                "schema_version": 1,
                "project_id": created.json()["id"],
                "expected_revision": 1,
                "inputs": stale,
                "key": "old-woo-revision",
            },
            headers=headers(),
        )
        assert (
            refused.status_code == 409
            and refused.json()["error"]["code"] == "product_evidence_changed"
        )
        mode = "unavailable"
        replay = private.post("/projects/create", json=create, headers=headers())
        assert replay.status_code == 200 and replay.json() == created.json()
        mode, calls = "changed", 0
        assert private.post(path, json=body, headers=headers()).status_code == 409
        mode = "unavailable"
        assert private.post(path, json=body, headers=headers()).status_code == 503
    # An absent shared provider is unavailable, never a hand-entered fallback.
    assert rig.client.post(path, json=body, headers=headers()).status_code == 503
    snapshot = json.loads(rig.kernel.runtime.content)
    names = {row["path"] for row in snapshot["files"]}
    assert {"schemas/feed.schema.json", "schemas/compatibility.schema.json"} <= names


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


@pytest.mark.parametrize(
    "number", [2**53, -(2**53), 9223372036854775809, 10**400, 1e100]
)
def test_http_rejects_unrepresentable_numbers_before_any_durable_write(
    rig: Rig, number: int | float
) -> None:
    before = set(rig.workspace.blobs.directory.rglob("*"))
    command = {
        "schema_version": 1,
        "title": "Number fixture",
        "inputs": {"n": number},
        "key": "numeric",
    }
    for path in ("/projects/create", "/operations/replay/projects/create"):
        response = rig.client.post(path, json=command, headers=headers())
        assert response.status_code == 422
    assert rig.post("/projects/list", {"page_size": 2, "after": None})["items"] == []
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_saved_intake_receipts_survive_an_installed_timezone_name_change(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    create: FixtureObject = {
        "title": "Zone receipt fixture",
        "inputs": brief_inputs("Europe/Berlin"),
        "key": "create-zone",
    }
    original = rig.post("/projects/create", create)
    revise: FixtureObject = {
        "project_id": original["id"],
        "expected_revision": 1,
        "inputs": brief_inputs("Europe/Oslo"),
        "key": "revise-zone",
    }
    revised = rig.post("/projects/revise", revise)
    before = set(rig.workspace.blobs.directory.rglob("*"))
    monkeypatch.setattr(
        timezone_rules, "installed_iana_names", lambda: frozenset({"UTC"})
    )
    assert rig.post("/projects/create", create) == original
    assert rig.post("/projects/revise", revise) == revised
    assert rig.replay("/projects/create", create)["result"] == original
    assert rig.replay("/projects/revise", revise)["result"] == revised
    for path, command in (
        ("/projects/create", {**create, "key": "new-create"}),
        ("/projects/revise", {**revise, "expected_revision": 2, "key": "new-revise"}),
    ):
        assert rig.replay(path, command)["status"] == "absent"
        response = rig.client.post(
            path, json={"schema_version": 1, **command}, headers=headers()
        )
        assert response.status_code == 422
        assert response.json() == {"error": {"code": "invalid_input"}}
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    assert (
        rig.post("/projects/read", {"project_id": original["id"], "revision": None})
        == revised
    )


@pytest.mark.parametrize(
    "zone",
    ["posixrules", "localtime", "right/UTC", "posix/Europe/Oslo", "Europe/Imaginary"],
)
def test_new_brief_rejects_non_iana_names_before_publishing_any_bytes(
    rig: Rig, zone: str
) -> None:
    before = set(rig.workspace.blobs.directory.rglob("*"))
    body: FixtureObject = {
        "title": "Invalid zone fixture",
        "inputs": brief_inputs(zone),
        "key": "new-zone",
    }
    assert rig.replay("/projects/create", body)["status"] == "absent"
    response = rig.client.post(
        "/projects/create", json={"schema_version": 1, **body}, headers=headers()
    )
    assert response.status_code == 422
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_depth_check_ignores_brackets_quotes_and_escapes_inside_strings(
    rig: Rig,
) -> None:
    value = "å😀" + '{["\\' * 1000
    project = rig.post(
        "/projects/create",
        {"title": "Unicode fixture", "inputs": {"text": value}, "key": "text"},
    )
    assert project["inputs"] == {"text": value}


def test_permanent_http_replay_survives_days_without_writes_or_latest_revision(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    command: FixtureObject = {
        "title": "Permanent retry",
        "inputs": {"object": {}, "list": [], "fraction": 1.0},
        "key": "permanent",
    }
    before = set(rig.workspace.blobs.directory.rglob("*"))
    pending = rig.replay("/projects/create", command)
    assert pending["schema_version"] == 1 and pending["status"] == "absent"
    command_hash = pending["command_sha256"]
    assert isinstance(command_hash, str) and len(command_hash) == 64
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    created = rig.post("/projects/create", command)
    assert rig.replay("/projects/create", command)["command_sha256"] == command_hash
    revision_command: FixtureObject = {
        "project_id": created["id"],
        "expected_revision": 1,
        "inputs": {"changed": True},
        "key": "permanent-revision",
    }
    assert rig.replay("/projects/revise", revision_command)["status"] == "absent"
    revised = rig.post("/projects/revise", revision_command)
    before = set(rig.workspace.blobs.directory.rglob("*"))
    now = rig.workspace.clock()
    monkeypatch.setattr(rig.workspace, "clock", lambda: now + 2 * 86400)

    def no_write(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a replay must not call a mutation")

    monkeypatch.setattr(rig.workspace, "create", no_write)
    monkeypatch.setattr(rig.workspace, "revise", no_write)
    assert rig.replay("/projects/create", command)["result"] == created
    assert rig.replay("/projects/revise", revision_command)["result"] == revised
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    assert rig.replay("/projects/create", command, FOREIGN)["status"] == "absent"
    foreign = rig.client.post(
        "/operations/replay/projects/revise",
        json={"schema_version": 1, **revision_command},
        headers=headers(FOREIGN),
    )
    assert foreign.status_code == 404
    changed = rig.client.post(
        "/operations/replay/projects/create",
        json={"schema_version": 1, **command, "inputs": {"fraction": 1}},
        headers=headers(),
    )
    assert changed.status_code == 409


@pytest.mark.parametrize(
    "path",
    [
        "projects/create",
        "projects/revise",
        "profiles/csv",
        "battery/scenario",
        "runs/energy",
    ],
)
def test_replay_has_no_public_or_team_mutation_authority(rig: Rig, path: str) -> None:
    response = rig.client.post("/operations/replay/" + path, content=b"not-json")
    assert response.status_code == 401
    response = rig.client.post(
        "/operations/replay/" + path, json={"schema_version": 1}, headers=headers(TEAM)
    )
    assert response.status_code == 404
    response = rig.client.post(
        "/operations/replay/" + path,
        json={"schema_version": True, "owner": "someone"},
        headers=headers(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert len(response.json()["error"]["fields"]) <= 16


def test_replay_cannot_call_private_identity_or_unknown_command(rig: Rig) -> None:
    response = rig.client.post(
        "/operations/replay/identity/claim-session",
        json={"schema_version": 1, "key": "x"},
        headers=headers(),
    )
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found"}}


@pytest.mark.parametrize(
    "encoding", ["utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"]
)
def test_other_json_encodings_cannot_bypass_utf8_nesting_gate(
    rig: Rig, encoding: str
) -> None:
    text = (
        '{"schema_version":1,"title":"x","inputs":{"text":"\\"","tree":'
        + "[" * 1200
        + "0"
        + "]" * 1200
        + '},"key":"deep"}'
    )
    response = rig.client.post(
        "/projects/create",
        content=text.encode(encoding),
        headers={**headers(), "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "invalid_input"}}
    assert len(response.content) < 100


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


@pytest.mark.parametrize("kind", ["source_error", "unencodable_secret", "app_error"])
def test_outer_boundary_errors_are_private_and_typed_before_any_app_response(
    kind: str,
) -> None:
    def credential() -> str:
        if kind == "source_error":
            raise OSError("private credential-source failure")
        if kind == "unencodable_secret":
            return "\ud800"
        return TOKEN

    async def app(_scope: Scope, _receive: Receive, _send: Send) -> None:
        raise RuntimeError("private downstream fixture content")

    boundary = ServiceBoundary(
        app, credential=credential, max_body_bytes=1000, max_json_depth=16
    )
    # This deliberately minimal downstream has no lifespan protocol.
    client = TestClient(boundary, raise_server_exceptions=False)
    try:
        response = client.post("/", content=b"{}", headers=headers())
    finally:
        client.close()
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "execution_failed"}}
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"


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
    length_cases: tuple[tuple[list[tuple[bytes, bytes]], list[Message]], ...] = (
        (wire_headers(), [{"type": "http.disconnect"}]),
        (
            wire_headers() + [(b"content-length", b"2")],
            [{"type": "http.request", "body": b"1"}],
        ),
    )
    for raw_headers, chunks in length_cases:
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
    extra_commands: tuple[FixtureObject, ...] = (
        {"owner": FOREIGN.key},
        {"actor": {"kind": "team"}},
        {"context": {"models": {}}},
    )
    for extra in extra_commands:
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
        command: FixtureObject = {
            "project_id": project_id,
            "content_base64": base64.b64encode(content).decode(),
            "mapping": json_object(mapping.document()),
            "source_label": "Synthetic analytic fixture",
            "rights_note": "created by this test",
            "key": role,
        }
        assert rig.replay("/profiles/csv", command)["status"] == "absent"
        asset = rig.post("/profiles/csv", command)
        assert rig.replay("/profiles/csv", command)["result"] == asset
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
    battery_command: FixtureObject = {
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
    }
    assert rig.replay("/battery/scenario", battery_command)["status"] == "absent"
    battery = rig.post("/battery/scenario", battery_command)
    assert rig.replay("/battery/scenario", battery_command)["result"] == battery
    energy: FixtureObject = {
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
    evaluate_command: FixtureObject = {
        "project_id": project_id,
        "expected_revision": 2,
        "key": "evaluate",
    }
    assert rig.replay("/runs/energy", evaluate_command)["result"] == run
    assert run["state"] == "queued" and run["result"] is None
    control = ExecutionControl(rig.workspace)
    control.set_draining(True)
    assert rig.post("/runs/energy", evaluate_command) == run
    refused = rig.client.post(
        "/runs/energy",
        json={"schema_version": 1, **evaluate_command, "key": "during-drain"},
        headers=headers(),
    )
    assert refused.status_code == 503
    assert refused.json()["error"]["code"] == "service_draining"
    assert control.status()["pending"] == 1
    control.set_draining(False)
    rig.post(
        "/projects/revise",
        {
            "project_id": project_id,
            "expected_revision": 2,
            "inputs": {"note": "new revision after queue"},
            "key": "newer",
        },
    )
    stale_new = rig.client.post(
        "/runs/energy",
        json={"schema_version": 1, **evaluate_command, "key": "stale-new"},
        headers=headers(),
    )
    assert stale_new.status_code == 409
    assert stale_new.json() == {"error": {"code": "evaluation_revision_changed"}}
    assert len(rig.workspace.runs(USER, project_id)) == 1
    assert Worker(
        Jobs(rig.workspace),
        "http-fixture-worker",
        {"evaluate": rig.kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    ).run_once()
    completed = rig.post("/runs/read", {"run_id": run["id"]})
    assert rig.replay("/runs/energy", evaluate_command)["result"] == completed
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
    window = rig.post("/runs/trace", {"run_id": run["id"], "offset": 1, "page_size": 1})
    source = json.loads(trace.content)["flows"][1]
    assert window["trace_sha256"] == result["trace_sha256"]
    assert window["offset"] == 1 and window["next_offset"] is None
    row = cast(list[Object], window["rows"])[0]
    assert row["start_utc"] == source["frame"]["interval"]["start_utc"]
    assert row["load_kw"] == source["frame"]["load_kw"]
    assert row["stored_kwh"] == sum(source["after"].values())
    bounded = {**trace_body, "offset": 0, "page_size": 1_000_000}
    assert (
        rig.client.post("/runs/trace", json=bounded, headers=headers()).status_code
        == 422
    )
    assert (
        rig.client.post(
            "/runs/trace",
            json={**trace_body, "offset": 0, "page_size": 1},
            headers=headers(FOREIGN),
        ).status_code
        == 404
    )
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
    body: FixtureObject = {
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
    body: FixtureObject = {
        "schema_version": 1,
        "project_id": project_id,
        "content_base64": "!!"
        if content is None
        else base64.b64encode(content).decode(),
        "mapping": json_object(
            CsvMapping(
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
            ).document()
        ),
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


def csv_preview_command(project_id: str, content: bytes, key: str) -> FixtureObject:
    return {
        "schema_version": 1,
        "project_id": project_id,
        "content_base64": base64.b64encode(content).decode(),
        "mapping": json_object(
            CsvMapping(
                "time",
                "power",
                "gross_load",
                "interval_average_kw",
                "start",
                "Europe/Berlin",
                "synthetic",
                900,
                ";",
                ",",
            ).document()
        ),
        "source_label": "Synthetic source for interpretation",
        "rights_note": "Created by this test",
        "key": key,
    }


def test_http_unknown_creation_and_csv_import_recover_original_after_native_claim(
    rig: Rig,
) -> None:
    from linker_engine.planning.guest_claims import GuestClaims

    guest = Actor("guest", "synthetic-native-handover")
    create: FixtureObject = {
        "title": "Synthetic handover",
        "inputs": {},
        "key": "lost-create",
    }
    original = rig.post("/projects/create", create, guest)
    project_id = cast(str, original["id"])
    command = csv_preview_command(
        project_id,
        b"time;power\n2024-10-27T02:00:00+02:00;-4\n2024-10-27T02:00:00+01:00;8\n",
        "lost-upload",
    )
    cast(Object, command["mapping"])["measurement"] = "net_import"
    asset = rig.post("/profiles/csv", command, guest)
    GuestClaims(rig.workspace).claim(guest, USER, key="native-login")
    with rig.workspace.database.read() as connection:
        before = connection.execute("SELECT count(*) FROM idempotency").fetchone()[0]
    assert rig.replay("/projects/create", create)["result"] == original
    assert rig.replay("/profiles/csv", command)["result"] == asset
    assert rig.post("/projects/create", create) == original
    assert rig.post("/profiles/csv", command) == asset
    with rig.workspace.database.read() as connection:
        assert (
            connection.execute("SELECT count(*) FROM idempotency").fetchone()[0]
            == before
        )
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 1
        )
    assert rig.replay("/projects/create", create, FOREIGN)["status"] == "absent"
    assert (
        rig.client.post(
            "/profiles/csv", json=command, headers=headers(FOREIGN)
        ).status_code
        == 404
    )
    assert (
        rig.client.post(
            "/projects/create",
            json={"schema_version": 1, **create},
            headers=headers(guest),
        ).status_code
        == 404
    )


def test_csv_column_inspection_is_owned_read_only_and_not_a_quality_release(
    rig: Rig,
) -> None:
    project_id = rig.create("csv-columns")
    raw = b'time;power;note\n\nPRIVATE-TIME;PRIVATE-NUMBER;"two\nlines"\nnext;2;last\n'
    before = set(rig.workspace.blobs.directory.rglob("*"))
    command: FixtureObject = {
        "project_id": project_id,
        "content_base64": base64.b64encode(raw).decode(),
        "delimiter": ";",
        "page_size": 1,
    }
    result = rig.post("/profiles/inspect", command)
    assert result == {
        "schema_version": 1,
        "evaluation_scope": "csv_structure_only",
        "content_sha256": digest(raw),
        "delimiter": ";",
        "columns": ["time", "power", "note"],
        "record_count": 2,
        "rows": [
            {"line": 3, "cells": ["PRIVATE-TIME", "PRIVATE-NUMBER", "two\nlines"]}
        ],
        "rows_truncated": True,
    }
    assert rig.workspace.get(USER, project_id).revision == 1
    assert set(rig.workspace.blobs.directory.rglob("*")) == before
    foreign = rig.client.post(
        "/profiles/inspect",
        json={"schema_version": 1, **command, "content_base64": "not base64"},
        headers=headers(FOREIGN),
    )
    assert foreign.status_code == 404
    assert "PRIVATE" not in foreign.text
    too_many = rig.client.post(
        "/profiles/inspect",
        json={"schema_version": 1, **command, "page_size": 3},
        headers=headers(),
    )
    assert too_many.status_code == 422


def test_csv_column_inspection_validates_rows_beyond_the_displayed_sample(
    rig: Rig,
) -> None:
    project_id = rig.create("csv-structure")
    response = rig.client.post(
        "/profiles/inspect",
        json={
            "schema_version": 1,
            "project_id": project_id,
            "content_base64": base64.b64encode(
                b"time;power\nfirst;1\nsecond;2\nPRIVATE;3;extra\n"
            ).decode(),
            "delimiter": ";",
            "page_size": 1,
        },
        headers=headers(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["profile_issue"] == {
        "issue": "row_width",
        "line": 4,
        "field": None,
    }
    assert "PRIVATE" not in response.text


def test_legal_large_cells_follow_declared_source_limits_through_inspection_and_import(
    workspace: Workspace,
) -> None:
    kernel = EnergyKernel(workspace, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=100)
    app = create_private_app(
        workspace,
        EnergyService(workspace, kernel, max_attempts=1),
        credential=lambda: TOKEN,
        limits=HttpLimits(1_000_000, 300_000, 2, 16),
    )
    # This legal comment exceeds Python csv's default 131072-character ceiling.
    # Its size remains below the deployment's declared source/reply bounds.
    comment = "x" * 140_000
    raw = f"time;power;note\n2024-01-01T00:00Z;4;{comment}\n".encode()
    with TestClient(app, raise_server_exceptions=False) as client:
        local = Rig(workspace, kernel, client)
        project_id = local.create("large-legal-csv-field")
        before = set(workspace.blobs.directory.rglob("*"))
        inspected = local.post(
            "/profiles/inspect",
            {
                "project_id": project_id,
                "content_base64": base64.b64encode(raw).decode(),
                "delimiter": ";",
                "page_size": 1,
            },
        )
        assert inspected["rows"] == [
            {"line": 2, "cells": ["2024-01-01T00:00Z", "4", comment]}
        ]
        assert inspected["content_sha256"] == digest(raw)
        assert set(workspace.blobs.directory.rglob("*")) == before
        asset = local.post(
            "/profiles/csv", csv_preview_command(project_id, raw, "large-legal-cell")
        )
        assert asset["content_sha256"] == digest(raw)
        preview = local.post(
            "/profiles/preview",
            {
                "project_id": project_id,
                "asset_id": asset["id"],
                "offset": 0,
                "page_size": 1,
            },
        )
        assert cast(Object, preview["summary"])["energy_kwh"] == 1
        assert workspace.get(USER, project_id).revision == 1


@pytest.mark.parametrize(
    ("raw", "issue", "row", "field"),
    [
        (b"time;power\nPRIVATE-CELL;1\n", "timestamp_format", 2, "timestamp"),
        (b"time;power\n2024-03-31T02:30;1\n", "local_time_nonexistent", 2, "timestamp"),
        (b"time;power\n2024-10-27T02:30;1\n", "local_time_ambiguous", 2, "timestamp"),
        (b"time;power\n2024-01-01T00:00Z;PRIVATE-CELL\n", "number_format", 2, "value"),
        (
            b"time;power\n\n2024-01-01T00:00Z;PRIVATE-CELL\n",
            "number_format",
            3,
            "value",
        ),
        (b"time;power\n2024-01-01T00:00Z;1e999\n", "number_nonfinite", 2, "value"),
        (b"time;power\n2024-01-01T00:00Z;-1\n", "value_sign", 2, "value"),
        (
            b"time;power\n2024-01-01T00:00Z;1\n2024-01-01T00:10Z;2\n",
            "interval_order",
            3,
            "timestamp",
        ),
        (b"time;power\n2024-01-01T00:00Z;1;extra\n", "row_width", 2, None),
        (b'time;power\n2024-01-01T00:00Z;"1\n', "csv_syntax", 2, None),
        (b"time;power;power\n", "headers", 1, "header"),
        (b"time;power\n", "empty", None, None),
        (b"time;power\n\xff", "encoding", None, None),
    ],
)
def test_csv_import_returns_safe_localizable_row_and_role_without_storing_bad_data(
    rig: Rig, raw: bytes, issue: str, row: int | None, field: str | None
) -> None:
    project_id = rig.create("csv-issues")
    before = set(rig.workspace.blobs.directory.rglob("*"))
    response = rig.client.post(
        "/profiles/csv",
        json=csv_preview_command(project_id, raw, "invalid"),
        headers=headers(),
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_input",
            "profile_issue": {"issue": issue, "line": row, "field": field},
        }
    }
    assert "PRIVATE-CELL" not in response.text and "Europe/Berlin" not in response.text
    assert response.headers["cache-control"] == "no-store, private"
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_source_selection_cannot_relabel_measurement_or_reference_another_project(
    rig: Rig,
) -> None:
    project_id = rig.create("selection")
    other_id = rig.create("other-source")
    command = csv_preview_command(
        project_id, b"time;power\n2024-01-01T00:00Z;-4\n", "source"
    )
    command["mapping"] = {
        **cast(Object, command["mapping"]),
        "measurement": "net_import",
    }
    asset = rig.post("/profiles/csv", command)

    def revision(project: str, role: str, key: str) -> FixtureObject:
        return {
            "schema_version": 1,
            "project_id": project,
            "expected_revision": 1,
            "inputs": {
                "profile_selections": {
                    "schema_version": 1,
                    "selected": {role: asset["id"]},
                }
            },
            "key": key,
        }

    for body, status in (
        (revision(project_id, "gross_load", "bad-role"), 422),
        (revision(other_id, "net_import", "bad-project"), 404),
        (revision(project_id, "invented", "bad-measurement"), 422),
    ):
        response = rig.client.post("/projects/revise", json=body, headers=headers())
        assert response.status_code == status
    assert rig.workspace.get(USER, project_id).revision == 1
    assert rig.workspace.get(USER, other_id).revision == 1
    chosen = rig.post("/projects/revise", revision(project_id, "net_import", "valid"))
    assert chosen["revision"] == 2
    assert chosen["inputs"] == {
        "profile_selections": {
            "schema_version": 1,
            "selected": {"net_import": asset["id"]},
        }
    }


@pytest.mark.parametrize("second_value", [b"1e308", b"-1e308"])
def test_csv_integral_overflow_returns_typed_refusal_without_publishing(
    rig: Rig, second_value: bytes
) -> None:
    project_id = rig.create("csv-overflow")
    before = set(rig.workspace.blobs.directory.rglob("*"))
    command = csv_preview_command(
        project_id,
        b"time;power\n2024-01-01T00:00Z;1e308\n2024-01-01T02:00Z;"
        + second_value
        + b"\n",
        "overflow",
    )
    command["mapping"] = {
        **cast(Object, command["mapping"]),
        "measurement": "net_import",
        "interval_seconds": 7200,
    }
    response = rig.client.post("/profiles/csv", json=command, headers=headers())
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_input",
            "profile_issue": {"issue": "energy_range", "line": None, "field": "value"},
        }
    }
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_profile_preview_uses_full_pinned_interpretation_and_pages_without_filling_gaps(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = rig.create("preview")
    content = b"time;power\n2024-01-01T00:00Z;4\n2024-01-01T00:15Z;8\n2024-01-01T01:00Z;12\n2024-01-01T01:30Z;16\n"
    asset = rig.post("/profiles/csv", csv_preview_command(project_id, content, "valid"))
    before = set(rig.workspace.blobs.directory.rglob("*"))
    monkeypatch.setattr(timezone_rules, "installed_iana_names", lambda: frozenset())

    def no_recapture(_name: str) -> None:
        raise AssertionError("preview must use captured TZif bytes")

    monkeypatch.setattr(timezone_rules, "load_timezone", no_recapture)
    command: FixtureObject = {
        "project_id": project_id,
        "asset_id": asset["id"],
        "offset": 0,
        "page_size": 2,
    }
    first = rig.post("/profiles/preview", command)
    assert first["content_sha256"] == asset["content_sha256"] == digest(content)
    assert first["metadata_sha256"] == asset["metadata_sha256"]
    assert first["evaluation_scope"] == "profile_interpretation"
    assert first["summary"] == {
        "start_utc": "2024-01-01T00:00:00+00:00",
        "end_utc": "2024-01-01T01:45:00+00:00",
        "interval_count": 4,
        "covered_seconds": 3600.0,
        "span_seconds": 6300.0,
        "gap_seconds": 2700.0,
        "gap_count": 2,
        "energy_kwh": 10.0,
        "min_interval_mean_kw": 4.0,
        "max_interval_mean_kw": 16.0,
        "native_max_interval_seconds": 900.0,
        "effective_max_interval_seconds": 900.0,
        "reconstructed_means": False,
    }
    assert [row["interval_mean_kw"] for row in cast(list[Object], first["rows"])] == [
        4,
        8,
    ]
    assert first["next_offset"] == 2 and first["gaps_truncated"] is False
    tail = rig.post("/profiles/preview", {**command, "offset": 2})
    assert tail["summary"] == first["summary"]
    assert [row["interval_index"] for row in cast(list[Object], tail["rows"])] == [2, 3]
    assert tail["next_offset"] is None
    narrow = rig.post("/profiles/preview", {**command, "page_size": 1})
    assert (
        narrow["gaps_truncated"] is True
        and len(cast(list[Object], narrow["first_gaps"])) == 1
    )
    assert rig.post("/profiles/preview", {**command, "offset": 99})["rows"] == []
    assert set(rig.workspace.blobs.directory.rglob("*")) == before


def test_preview_does_not_relabel_signed_net_import_as_gross_consumption(
    rig: Rig,
) -> None:
    project_id = rig.create("signed-preview")
    command = csv_preview_command(
        project_id, b"time;power\n2024-01-01T00:00Z;-4\n2024-01-01T00:15Z;8\n", "signed"
    )
    command["mapping"] = {
        **cast(Object, command["mapping"]),
        "measurement": "net_import",
    }
    asset = rig.post("/profiles/csv", command)
    preview = rig.post(
        "/profiles/preview",
        {
            "project_id": project_id,
            "asset_id": asset["id"],
            "offset": 0,
            "page_size": 2,
        },
    )
    assert preview["measurement"] == "net_import"
    assert cast(Object, preview["summary"])["energy_kwh"] == 1
    assert cast(Object, preview["summary"])["min_interval_mean_kw"] == -4
    assert [row["interval_mean_kw"] for row in cast(list[Object], preview["rows"])] == [
        -4,
        8,
    ]


def test_profile_preview_checks_owner_before_parsing_and_enforces_wire_page_bounds(
    rig: Rig, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = rig.create("preview-owner")
    asset = rig.post(
        "/profiles/csv",
        csv_preview_command(project_id, b"time;power\n2024-01-01T00:00Z;4\n", "valid"),
    )

    def forbidden_parse(*_args: object) -> None:
        raise AssertionError("unauthorised preview reached source parsing")

    monkeypatch.setattr(
        "linker_engine.planning.frozen_profiles.read_profile", forbidden_parse
    )
    body: FixtureObject = {
        "schema_version": 1,
        "project_id": project_id,
        "asset_id": asset["id"],
        "offset": 0,
        "page_size": 1,
    }
    foreign = rig.client.post("/profiles/preview", json=body, headers=headers(FOREIGN))
    assert foreign.status_code == 404 and foreign.json() == {
        "error": {"code": "not_found"}
    }
    for changed in (
        {"offset": True},
        {"offset": -1},
        {"offset": 0.0},
        {"page_size": 0},
        {"page_size": 3},
    ):
        response = rig.client.post(
            "/profiles/preview", json={**body, **changed}, headers=headers()
        )
        assert response.status_code == 422
