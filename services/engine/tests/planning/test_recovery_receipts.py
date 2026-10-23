"""Lost acknowledgements across native guest retirement, without copied owners."""

from __future__ import annotations

from pathlib import Path

import pytest

from linker_engine.planning import archive
from linker_engine.planning.assets import Assets
from linker_engine.planning.canonical import Object
from linker_engine.planning.errors import Conflict, NotFound
from linker_engine.planning.guest_claims import GuestClaims
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace

GUEST = Actor("guest", "synthetic-native-session")
USER = Actor("user", "synthetic-native-account")
OTHER = Actor("user", "synthetic-other-account")
METADATA: Object = {
    "retention": "permanent",
    "provenance": {
        "label": "Synthetic source",
        "basis": "synthetic_fixture",
        "rights_basis": "Created by this test",
    },
}


def test_committed_guest_create_revise_asset_and_run_keep_original_receipts(
    workspace: Workspace,
    context: Context,
) -> None:
    created = workspace.create(GUEST, "Synthetic project", {}, key="create")
    revised = workspace.revise(GUEST, created.id, 1, {"value": 2}, key="edit")
    assets = Assets(workspace)
    asset = assets.add(
        GUEST, created.id, b"fixture", "text/plain", "fixture", METADATA, key="upload"
    )
    run = workspace.evaluate(
        GUEST, created.id, 2, context, key="calculate", max_attempts=1
    )
    GuestClaims(workspace).claim(GUEST, USER, key="native-login")

    # Retrying the same original commands cannot create a second project,
    # advance to revision3, recapture another asset or schedule another run.
    assert (
        workspace.create(USER, "Synthetic project", {}, key="create").id == created.id
    )
    assert (
        workspace.revise(USER, created.id, 1, {"value": 2}, key="edit").input_sha256
        == revised.input_sha256
    )
    assert (
        assets.add(
            USER,
            created.id,
            b"fixture",
            "text/plain",
            "fixture",
            METADATA,
            key="upload",
        )
        == asset
    )
    assert (
        workspace.evaluate(
            USER, created.id, 2, context, key="calculate", max_attempts=1
        ).id
        == run.id
    )
    assert len(workspace.projects(USER)) == 1
    assert workspace.get(USER, created.id).revision == 2
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT count(*) FROM project_assets").fetchone()[0] == 1
        )
        assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
    with pytest.raises(NotFound):
        workspace.create(GUEST, "Synthetic project", {}, key="create")
    with pytest.raises(NotFound):
        workspace.revise(OTHER, created.id, 1, {"value": 2}, key="edit")
    with pytest.raises(Conflict):
        workspace.create(USER, "Changed original bytes", {}, key="create")


def test_claim_first_uncommitted_intent_can_commit_once_for_account(
    workspace: Workspace,
) -> None:
    stale_process = Workspace(workspace.database.path.parent)
    GuestClaims(workspace).claim(GUEST, USER, key="native-login")
    with pytest.raises(NotFound):
        stale_process.create(GUEST, "Never committed before login", {}, key="unknown")
    created = workspace.create(USER, "Never committed before login", {}, key="unknown")
    assert (
        workspace.create(USER, "Never committed before login", {}, key="unknown").id
        == created.id
    )
    assert len(workspace.projects(USER)) == 1


@pytest.mark.parametrize("same_body", [True, False])
def test_existing_account_key_collision_never_selects_or_overwrites_a_receipt(
    workspace: Workspace,
    same_body: bool,
) -> None:
    guest = workspace.create(GUEST, "Source", {}, key="collided-key")
    title = "Source" if same_body else "Different"
    account = workspace.create(USER, title, {}, key="collided-key")
    GuestClaims(workspace).claim(GUEST, USER, key="native-login")
    with pytest.raises(Conflict):
        workspace.create(USER, title, {}, key="collided-key")
    assert {p.id for p in workspace.projects(USER)} == {guest.id, account.id}
    assert workspace.get(USER, guest.id).inputs == {}


def test_receipts_from_another_accounts_claim_do_not_leak_or_block_own_key(
    workspace: Workspace,
) -> None:
    original = workspace.create(GUEST, "Private source", {}, key="known-key")
    GuestClaims(workspace).claim(GUEST, OTHER, key="native-login")
    unrelated = workspace.create(USER, "Own independent source", {}, key="known-key")
    assert unrelated.id != original.id
    with pytest.raises(NotFound):
        workspace.get(USER, original.id)
    assert (
        workspace.create(OTHER, "Private source", {}, key="known-key").id == original.id
    )


def test_original_receipts_survive_verified_backup_restore(
    workspace: Workspace,
    tmp_path: Path,
) -> None:
    original = workspace.create(GUEST, "Restore fixture", {}, key="lost-ack")
    GuestClaims(workspace).claim(GUEST, USER, key="native-login")
    snapshot = tmp_path / "backup"
    archive.backup(workspace, snapshot)
    restored = archive.restore(snapshot, tmp_path / "restored")
    assert (
        restored.create(USER, "Restore fixture", {}, key="lost-ack").id == original.id
    )
