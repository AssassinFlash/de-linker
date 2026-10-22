"""Whole-session ownership, actual transactions/races, restart and archive bytes."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient
from starlette.types import Receive, Scope, Send

from linker_engine.planning import archive
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object, digest
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.errors import Conflict, NotFound, VersionUnavailable
from linker_engine.planning.guest_claims import GuestClaims
from linker_engine.planning.http_app import HttpLimits, create_private_app
from linker_engine.planning.http_index import project_page
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.service_boundary import PREVIOUS_GUEST_SCOPE
from linker_engine.planning.workspace import Workspace

GUEST = Actor("guest", "woocommerce:t_verified_fixture")
USER = Actor("user", "wordpress:17")
OTHER = Actor("user", "wordpress:18")


def test_all_projects_assets_and_frozen_history_transfer_without_input_mutation(
    workspace: Workspace,
    context: Context,
) -> None:
    projects = [
        workspace.create(GUEST, f"Fixture {n}", {"original": n}, key=f"create{n}")
        for n in range(3)
    ]
    first = projects[0]
    revised = workspace.revise(GUEST, first.id, 1, {"edited": True}, key="revise")
    run = workspace.evaluate(GUEST, first.id, 2, context, key="run", max_attempts=1)
    asset = Assets(workspace).add(
        GUEST,
        first.id,
        b"private fixture",
        "text/plain",
        "fixture",
        {
            "retention": "permanent",
            "provenance": {
                "label": "Synthetic fixture",
                "basis": "synthetic_fixture",
                "rights_basis": "Owned test bytes",
            },
        },
        key="asset",
    )
    unrelated = workspace.create(OTHER, "Other account", {}, key="other")
    claims = GuestClaims(workspace)
    receipt = claims.claim(GUEST, USER, key="login-event")
    assert receipt == {
        "schema_version": 1,
        "status": "claimed",
        "transferred_count": 3,
        "guest_retired": True,
    }
    assert claims.claim(GUEST, USER, key="login-event") == receipt
    assert claims.claim(GUEST, USER, key="redelivery-key") == receipt
    assert workspace.get(USER, first.id).input_sha256 == revised.input_sha256
    assert workspace.get(USER, first.id, revision=1).inputs == {"original": 0}
    assert workspace.run(USER, run.id).manifest_sha256 == run.manifest_sha256
    assert (
        Assets(workspace).get(USER, first.id, asset.id).content_sha256
        == asset.content_sha256
    )
    assert workspace.get(OTHER, unrelated.id).owner == OTHER.key
    assert {item.id for item in workspace.projects(USER)} == {
        item.id for item in projects
    }
    with pytest.raises(Conflict):
        claims.claim(GUEST, OTHER, key="different-account")
    checks = [
        lambda: workspace.get(GUEST, first.id),
        lambda: workspace.projects(GUEST),
        lambda: project_page(workspace, GUEST, 10, None),
        lambda: workspace.create(GUEST, "Late request", {}, key="late"),
        lambda: workspace.revise(GUEST, first.id, 2, {}, key="late-revise"),
        lambda: workspace.evaluate(
            GUEST, first.id, 2, context, key="late-run", max_attempts=1
        ),
        lambda: workspace.cancel(GUEST, run.id),
        lambda: workspace.run(GUEST, run.id),
        lambda: Assets(workspace).get(GUEST, first.id, asset.id),
    ]
    for check in checks:
        with pytest.raises(NotFound):
            check()


def test_zero_project_session_is_still_retired(workspace: Workspace) -> None:
    receipt = GuestClaims(workspace).claim(GUEST, USER, key="empty-login")
    assert receipt["transferred_count"] == 0
    with pytest.raises(NotFound):
        workspace.create(GUEST, "After login", {}, key="late")
    assert GuestClaims(workspace).claim(GUEST, USER, key="retry") == receipt


def test_team_has_named_read_access_but_cannot_create_or_modify_legacy_owned_project(
    workspace: Workspace,
) -> None:
    team = Actor("team", "wordpress:auditor")
    with pytest.raises(NotFound):
        workspace.create(team, "Forbidden", {}, key="create")
    project = workspace.create(USER, "Legacy team-owned fixture", {}, key="legacy")
    with workspace.database.transaction() as connection:
        connection.execute(
            "UPDATE projects SET owner=? WHERE id=?", (team.key, project.id)
        )
    assert workspace.get(team, project.id).id == project.id
    with pytest.raises(NotFound):
        workspace.revise(team, project.id, 1, {"forbidden": True}, key="edit")


def test_request_admitted_before_login_cannot_publish_a_late_guest_project(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published, resume = Event(), Event()
    original = workspace.blobs.put_object

    def pause(value: Object) -> str:
        result = original(value)
        if value == {"late": True}:
            published.set()
            assert resume.wait(timeout=10)
        return result

    monkeypatch.setattr(workspace.blobs, "put_object", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(
            workspace.create, GUEST, "In flight", {"late": True}, key="late"
        )
        assert published.wait(timeout=10)
        receipt = GuestClaims(workspace).claim(GUEST, USER, key="login")
        resume.set()
        with pytest.raises(NotFound):
            request.result(timeout=10)
    assert receipt["transferred_count"] == 0
    assert workspace.projects(USER) == []


def test_competing_verified_accounts_cannot_split_one_guest_session(
    workspace: Workspace,
) -> None:
    projects = [workspace.create(GUEST, str(n), {}, key=str(n)) for n in range(5)]
    start = Barrier(2)

    def claim(user: Actor) -> Actor | None:
        start.wait(timeout=10)
        try:
            GuestClaims(workspace).claim(GUEST, user, key="same-native-event")
            return user
        except Conflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(claim, (USER, OTHER)))
    winners = [user for user in outcomes if user is not None]
    assert len(winners) == 1
    winner = winners[0]
    assert {project.id for project in workspace.projects(winner)} == {
        project.id for project in projects
    }
    loser = OTHER if winner == USER else USER
    assert workspace.projects(loser) == []


def test_failed_receipt_publication_rolls_back_transfer_and_retirement(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(GUEST, "Before login", {}, key="create")
    original = workspace.blobs.put_object

    def fail(value: Object) -> str:
        if value.get("status") == "claimed":
            raise OSError("synthetic receipt disk failure")
        return original(value)

    with monkeypatch.context() as patch:
        patch.setattr(workspace.blobs, "put_object", fail)
        with pytest.raises(OSError):
            GuestClaims(workspace).claim(GUEST, USER, key="login")
    assert workspace.get(GUEST, project.id).owner == GUEST.key
    assert workspace.projects(USER) == []
    receipt = GuestClaims(workspace).claim(GUEST, USER, key="login")
    assert receipt["transferred_count"] == 1


def test_restart_and_backup_restore_retain_retirement_and_validate_its_receipt(
    workspace: Workspace,
    tmp_path: Path,
) -> None:
    project = workspace.create(GUEST, "Private fixture", {"original": 1}, key="create")
    receipt = GuestClaims(workspace).claim(GUEST, USER, key="login")
    reopened = Workspace(workspace.database.path.parent)
    assert reopened.get(USER, project.id).input_sha256 == project.input_sha256
    with pytest.raises(NotFound):
        reopened.create(GUEST, "After restart", {}, key="late")
    snapshot = tmp_path / "snapshot"
    archive.backup(reopened, snapshot)
    restored = archive.restore(snapshot, tmp_path / "restored")
    assert restored.get(USER, project.id).inputs == {"original": 1}
    assert GuestClaims(restored).claim(GUEST, USER, key="new-key") == receipt
    with pytest.raises(NotFound):
        restored.create(GUEST, "After restore", {}, key="late")
    with restored.database.read() as connection:
        receipt_hash = connection.execute(
            "SELECT receipt_sha256 FROM principal_closures"
        ).fetchone()[0]
    # Remove only the closure's reference from the archive blob set, proving
    # it is checked independently of the command receipt table.
    connection = sqlite3.connect(snapshot / "workspace.sqlite")
    connection.execute("DELETE FROM idempotency WHERE scope LIKE 'claim-session:%'")
    connection.commit()
    connection.close()
    import json

    manifest = json.loads((snapshot / "backup.json").read_bytes())
    manifest["database_sha256"] = digest((snapshot / "workspace.sqlite").read_bytes())
    manifest["blobs"] = [value for value in manifest["blobs"] if value != receipt_hash]
    (snapshot / "backup.json").write_text(json.dumps(manifest))
    (snapshot / "blobs" / receipt_hash[:2] / receipt_hash).unlink()
    with pytest.raises(VersionUnavailable):
        archive.restore(snapshot, tmp_path / "damaged")
    assert not (tmp_path / "damaged").exists()


def test_v1_archive_upgrades_before_publication_without_changing_source(
    workspace: Workspace,
    tmp_path: Path,
) -> None:
    project = workspace.create(
        GUEST, "Legacy schema fixture", {"retained": True}, key="create"
    )
    with workspace.database.transaction() as connection:
        connection.execute("DROP TABLE principal_closures")
        connection.execute("PRAGMA user_version=1")
    snapshot = tmp_path / "v1-snapshot"
    archive.backup(workspace, snapshot)
    before = (snapshot / "workspace.sqlite").read_bytes()
    restored = archive.restore(snapshot, tmp_path / "v2-restored")
    assert (snapshot / "workspace.sqlite").read_bytes() == before
    assert restored.get(GUEST, project.id).input_sha256 == project.input_sha256
    with restored.database.read() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
    GuestClaims(restored).claim(GUEST, USER, key="login")
    with pytest.raises(NotFound):
        restored.get(GUEST, project.id)


def test_private_claim_uses_two_gateway_assertions_and_rejects_body_authority(
    workspace: Workspace,
) -> None:
    token = "synthetic-service-token"
    kernel = EnergyKernel(workspace, Tolerance(1e-7, 1e-7, 1e-9), max_intervals=100)
    app = create_private_app(
        workspace,
        EnergyService(workspace, kernel, max_attempts=1),
        credential=lambda: token,
        limits=HttpLimits(100_000, 10_000, 10, 16),
    )

    async def stale_scope(scope: Scope, receive: Receive, send: Send) -> None:
        scope = dict(scope)
        scope[PREVIOUS_GUEST_SCOPE] = GUEST
        await app(scope, receive, send)

    project = workspace.create(GUEST, "Native assertion fixture", {}, key="create")
    headers = {
        "X-Linker-Service-Token": token,
        "X-Linker-Planner-Principal-Kind": USER.kind,
        "X-Linker-Planner-Principal-Subject": USER.subject,
    }
    with TestClient(stale_scope) as client:
        body = {"schema_version": 1, "key": "native-event"}
        assert (
            client.post(
                "/identity/claim-session", json=body, headers=headers
            ).status_code
            == 404
        )
        bad = client.post(
            "/identity/claim-session",
            json={**body, "guest": GUEST.subject},
            headers=headers,
        )
        assert bad.status_code == 422
        previous = {**headers, "X-Linker-Planner-Previous-Guest": GUEST.subject}
        for kind in ("guest", "team"):
            denied = {**previous, "X-Linker-Planner-Principal-Kind": kind}
            assert (
                client.post(
                    "/identity/claim-session", json=body, headers=denied
                ).status_code
                == 404
            )
        for subject in ("", "bad space", "a" * 257):
            denied = {**previous, "X-Linker-Planner-Previous-Guest": subject}
            assert (
                client.post(
                    "/identity/claim-session", json=body, headers=denied
                ).status_code
                == 400
            )
        result = client.post("/identity/claim-session", json=body, headers=previous)
        assert result.status_code == 200
        assert result.json()["transferred_count"] == 1
        assert result.headers["cache-control"] == "no-store, private"
        assert (
            client.post("/identity/claim-session", json=body, headers=previous).json()
            == result.json()
        )
        duplicate = [
            *headers.items(),
            ("X-Linker-Planner-Previous-Guest", GUEST.subject),
            ("x-linker-planner-previous-guest", GUEST.subject),
        ]
        assert (
            client.post(
                "/identity/claim-session", json=body, headers=duplicate
            ).status_code
            == 400
        )
    assert workspace.get(USER, project.id).owner == USER.key
