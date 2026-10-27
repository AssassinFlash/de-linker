"""Mixed task navigation reads bounded manifests, not inputs or results."""

from dataclasses import replace

import pytest

from linker_engine.planning.errors import NotFound
from linker_engine.planning.http_index import run_page
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace

from .conftest import Clock


def test_mixed_task_history_keeps_cursor_and_needs_no_input_or_result_bytes(
    workspace: Workspace, owner: Actor, context: Context, clock: Clock
) -> None:
    project = workspace.create(owner, "Mixed tasks", {}, key="project")
    kinds = [
        "single_ac_energy_replay_v1",
        "prepare_roof_pv_reference_v1",
        "acquire_pvgis_tmy_weather_v1",
    ]
    for number, kind in enumerate(kinds):
        clock.advance(1)
        workspace.evaluate(
            owner,
            project.id,
            project.revision,
            replace(context, parameters={"kind": kind}),
            key=f"task-{number}",
            max_attempts=1,
        )
    # Project navigation and task type are manifest facts, not profile parsing.
    (
        workspace.blobs.directory / project.input_sha256[:2] / project.input_sha256
    ).unlink()
    first = run_page(workspace, owner, project.id, 2, None, None)
    first_items = first["items"]
    assert isinstance(first_items, list)
    assert [
        item["task_kind"] for item in first_items if isinstance(item, dict)
    ] == list(reversed(kinds))[:2]
    cursor = first["next"]
    assert isinstance(cursor, dict)
    before_created_at, before_id = cursor["before_created_at"], cursor["before_id"]
    assert isinstance(before_created_at, (int, float)) and isinstance(before_id, str)
    second = run_page(
        workspace,
        owner,
        project.id,
        2,
        before_created_at,
        before_id,
    )
    second_items = second["items"]
    assert isinstance(second_items, list) and isinstance(second_items[0], dict)
    assert second_items[0]["task_kind"] == kinds[0] and second["next"] is None


def test_foreign_task_index_cannot_read_even_a_manifest(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = workspace.create(owner, "Owned tasks", {}, key="project")
    workspace.evaluate(owner, project.id, 1, context, key="task", max_attempts=1)

    def refuse(_sha: str) -> None:
        raise AssertionError("foreign navigation reached private bytes")

    monkeypatch.setattr(workspace.blobs, "object", refuse)
    with pytest.raises(NotFound):
        run_page(workspace, Actor("user", "foreign"), project.id, 2, None, None)
