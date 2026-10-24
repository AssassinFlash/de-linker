"""Real durable start permits and original-byte recovery; no new external run."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning import archive
from linker_engine.planning.apify_run import ApifyRun
from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.errors import (
    Conflict,
    InvalidInput,
    LeaseLost,
    NotFound,
    VersionUnavailable,
)
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.pv_source import PvSource
from linker_engine.planning.records import Actor, Context, Lease, Run
from linker_engine.planning.weather_fetch_plan import (
    WeatherFetchLimits,
    WeatherFetchPlan,
)
from linker_engine.planning.weather_journal import (
    WeatherDeadlineExceeded,
    WeatherJournal,
    WeatherStartUnknown,
)
from linker_engine.planning.workspace import Workspace

from .conftest import Clock
from .test_pv_profile import PROVENANCE
from .test_pvgis_tmy import capture, interpretation, raw, request


def plan() -> WeatherFetchPlan:
    # Operational fixture budgets; not a production sizing recommendation.
    return WeatherFetchPlan(
        schema_version=1,
        kind="pvgis_tmy_apify_acquisition_v1",
        request=request(),
        interpretation=interpretation(),
        limits=WeatherFetchLimits(
            max_response_bytes=2_000_000,
            max_metadata_bytes=100_000,
            max_weather_rows=9000,
            connect_timeout_seconds=5,
            read_timeout_seconds=20,
            max_elapsed_seconds=60,
            poll_seconds=1,
            max_polls=10,
            actor_timeout_seconds=180,
            actor_memory_mb=1024,
            max_total_charge_usd=0.05,
            request_timeout_seconds=90,
            request_retries=1,
            minimum_download_kb_per_second=1,
        ),
    )


def operation(
    workspace: Workspace, owner: Actor, *, key: str = "weather"
) -> tuple[Run, Lease]:
    frozen = plan()
    project = workspace.create(
        owner, "Weather journal fixture", {}, key="weather-project"
    )
    context = Context(
        digest(b"weather-journal-fixture-not-production-executor"),
        {"fixture": "durable_weather_intent"},
        {"weather_acquisition.plan": workspace.blobs.put_object(frozen.document())},
        {"fixture_only": True},
    )
    run = workspace.evaluate(
        owner, project.id, project.revision, context, key=key, max_attempts=5
    )
    lease = Jobs(workspace).claim(
        "journal-test", kinds=("evaluate",), lease_seconds=300
    )
    assert lease is not None
    return run, lease


def remote(status: str = "READY") -> ApifyRun:
    path = (
        Path(__file__).resolve().parents[4]
        / "docs/research/2026-10-24-pv-generation/raw/acquisition.json"
    )
    original = ApifyRun.from_provider(json.loads(path.read_bytes()))
    return ApifyRun.read(
        {
            **original.document(),
            "status": status,
            "finished_at": original.finished_at
            if status in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED")
            else None,
        }
    )


def source() -> PvSource:
    return PvSource(
        raw(),
        request(),
        capture().model_copy(
            update={"source_identifiers": {"apify_run_id": remote().id}}
        ),
        interpretation(),
        encode(PROVENANCE),
    )


def succeeded(workspace: Workspace, lease: Lease):
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    journal.acknowledge(intent, remote())
    return journal, journal.observe(intent, remote("SUCCEEDED"))


def test_plan_pins_provider_and_roundtrips_without_browser_overrides() -> None:
    value = plan()
    assert WeatherFetchPlan.from_document(value.document()) == value
    data = cast(dict[str, Any], value.document())
    data["provider"]["input"]["startUrls"][0]["url"] = "https://example.invalid/"
    with pytest.raises(VersionUnavailable):
        WeatherFetchPlan.from_document(data)
    expected = value.actor_input()
    assert expected["maxResults"] == 1 and expected["maxCrawlDepth"] == 0
    assert expected["startUrls"] == [{"url": request().url}]


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_memory_mb", 129),
        ("request_retries", 21),
        ("max_elapsed_seconds", 0),
        ("max_metadata_bytes", 3_000_000),
        ("max_total_charge_usd", float("inf")),
    ],
)
def test_operational_limits_reject_invalid_or_unbounded_policy(
    field: str, value: Any
) -> None:
    document = plan().limits.model_dump(mode="json")
    document[field] = value
    with pytest.raises(InvalidInput):
        WeatherFetchLimits.read(document)


def test_leap_scenario_is_rejected_before_any_provider_operation() -> None:
    document = cast(dict[str, Any], plan().model_dump(mode="json"))
    document["interpretation"]["synthetic_energy_year"] = 2024
    with pytest.raises(InvalidInput):
        WeatherFetchPlan.read(document)


def test_unconsumed_intent_survives_reopen_but_post_permit_is_consumed_once(
    workspace: Workspace, owner: Actor
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    first = journal.begin(lease, plan())
    reopened = WeatherJournal(
        Workspace(workspace.database.path.parent, clock=workspace.clock)
    )
    second = reopened.begin(lease, plan())
    assert first == second and first.may_start
    reopened.authorize_post(lease, second)
    third = reopened.begin(lease, plan())
    assert not third.may_start and third.nonce == first.nonce
    assert reopened.view(owner, run.id)["acquisition_state"] == "start_outcome_unknown"
    with pytest.raises(WeatherStartUnknown):
        reopened.authorize_post(lease, first)


def test_concurrent_authorization_grants_only_one_post(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())

    def claim() -> bool:
        try:
            journal.authorize_post(lease, intent)
            return True
        except WeatherStartUnknown:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert sorted(results) == [False, True]


def test_replacement_lease_keeps_original_intent_and_cannot_repeat_issued_post(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    clock.advance(301)
    replacement = Jobs(workspace).claim(
        "replacement", kinds=("evaluate",), lease_seconds=300
    )
    assert replacement is not None
    with pytest.raises(LeaseLost):
        journal.authorize_post(lease, intent)
    resumed = journal.begin(replacement, plan())
    assert resumed.nonce == intent.nonce and resumed.deadline_at == intent.deadline_at
    with pytest.raises(WeatherStartUnknown):
        journal.authorize_post(replacement, resumed)


def test_cancellation_blocks_new_start_but_retains_late_ack_without_publication(
    workspace: Workspace, owner: Actor
) -> None:
    run, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    workspace.cancel(owner, run.id)
    with pytest.raises(LeaseLost):
        journal.authorize_post(lease, intent)
    acknowledged = journal.acknowledge(intent, remote())
    assert acknowledged.remote_run_id == remote().id
    view = journal.view(owner, run.id)
    assert view["task_state"] == "cancelled" and view["acquisition_state"] == "READY"
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0] == 0
        )
    assert workspace.run(owner, run.id).result is None


def test_cancelled_run_cannot_create_an_intent(
    workspace: Workspace, owner: Actor
) -> None:
    run, lease = operation(workspace, owner)
    workspace.cancel(owner, run.id)
    with pytest.raises(LeaseLost):
        WeatherJournal(workspace).begin(lease, plan())
    with workspace.database.read() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM weather_acquisitions").fetchone()[
                0
            ]
            == 0
        )


def test_plan_must_be_the_actual_frozen_dependency(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    other = plan().model_copy(
        update={"limits": plan().limits.model_copy(update={"max_polls": 11})}
    )
    with pytest.raises(VersionUnavailable, match="not frozen"):
        WeatherJournal(workspace).begin(lease, other)


def test_intent_cannot_be_used_by_a_different_run_or_nonce(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    with pytest.raises(Conflict):
        journal.authorize_post(replace(lease, run_id="0" * 32), intent)
    journal.authorize_post(lease, intent)
    with pytest.raises(Conflict):
        journal.acknowledge(replace(intent, nonce="other"), remote())


def test_deadline_is_persistent_and_checked_before_post(
    workspace: Workspace, owner: Actor, clock: Clock
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    clock.advance(61)
    assert journal.begin(lease, plan()).deadline_at == intent.deadline_at
    with pytest.raises(WeatherDeadlineExceeded):
        journal.authorize_post(lease, intent)


def test_acknowledgement_replay_preserves_first_receipt_and_terminal_fact(
    workspace: Workspace, owner: Actor
) -> None:
    run, lease = operation(workspace, owner)
    journal, intent = succeeded(workspace, lease)
    first = intent.acknowledgement_sha256
    replay = journal.acknowledge(intent, remote())
    assert (
        replay.acknowledgement_sha256 == first
        and replay.observation_sha256 == intent.observation_sha256
    )
    assert (
        cast(Object, journal.view(owner, run.id)["observation"])["status"]
        == "SUCCEEDED"
    )
    with pytest.raises(Conflict):
        journal.observe(intent, remote("ABORTED"))


@pytest.mark.parametrize(
    "field,value",
    [("id", "anotherRun"), ("dataset_id", "otherDataset"), ("store_id", "otherStore")],
)
def test_acknowledged_provider_identity_and_storage_cannot_change(
    workspace: Workspace, owner: Actor, field: str, value: str
) -> None:
    _, lease = operation(workspace, owner)
    journal, intent = succeeded(workspace, lease)
    with pytest.raises(Conflict):
        journal.acknowledge(intent, remote().model_copy(update={field: value}))


def test_pinned_build_and_known_status_are_required() -> None:
    for changed in (
        {"build_number": "latest"},
        {"status": "TIMED_OUT"},
        {"finished_at": None},
    ):
        with pytest.raises(InvalidInput):
            ApifyRun.read({**remote("SUCCEEDED").document(), **changed})


def test_progress_and_abort_confirmation_follow_project_ownership(
    workspace: Workspace,
) -> None:
    guest = Actor("guest", "weather-guest")
    account = Actor("user", "weather-account")
    run, lease = operation(workspace, guest)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    journal.acknowledge(intent, remote())
    workspace.cancel(guest, run.id)
    journal.abort_reply(intent, remote("ABORTED"))
    workspace.claim_guest(guest, account, run.project_id, key="transfer")
    with pytest.raises(NotFound):
        journal.view(guest, run.id)
    with pytest.raises(NotFound):
        journal.view(Actor("user", "foreign"), run.id)
    view = journal.view(account, run.id)
    assert view["acquisition_state"] == "ABORTED" and view["abort_sha256"] is not None


def test_exact_captured_original_is_reused_and_cannot_be_replaced(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal, intent = succeeded(workspace, lease)
    evidence = {
        "dependencies": {"submitted": workspace.blobs.put_object(plan().actor_input())}
    }
    retained = journal.retain_capture(intent, source(), evidence)
    assert journal.captured_source(retained) == source()
    assert (
        journal.retain_capture(intent, source(), evidence).capture_sha256
        == retained.capture_sha256
    )
    changed = replace(
        source(), provenance_json=encode({**PROVENANCE, "label": "changed evidence"})
    )
    with pytest.raises(Conflict):
        journal.retain_capture(intent, changed, evidence)


def test_failed_run_cannot_supply_a_weather_capture(
    workspace: Workspace, owner: Actor
) -> None:
    _, lease = operation(workspace, owner)
    journal = WeatherJournal(workspace)
    intent = journal.begin(lease, plan())
    journal.authorize_post(lease, intent)
    journal.acknowledge(intent, remote("FAILED"))
    with pytest.raises(Conflict, match="succeeded"):
        journal.retain_capture(intent, source(), {})


def test_capture_and_uncertain_start_survive_real_backup_restore(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    run, lease = operation(workspace, owner)
    journal, intent = succeeded(workspace, lease)
    evidence = {
        "dependencies": {
            "effective_input": workspace.blobs.put_object(plan().actor_input())
        }
    }
    retained = journal.retain_capture(intent, source(), evidence)
    other, second = operation(workspace, owner, key="uncertain")
    uncertain = journal.begin(second, plan())
    journal.authorize_post(second, uncertain)
    archive.backup(workspace, tmp_path / "backup")
    restored = archive.restore(tmp_path / "backup", tmp_path / "restored")
    recovered = WeatherJournal(restored)
    assert recovered.captured_source(retained) == source()
    assert recovered.view(owner, run.id)["capture_sha256"] == retained.capture_sha256
    assert (
        recovered.view(owner, other.id)["acquisition_state"] == "start_outcome_unknown"
    )
    assert not recovered.current(uncertain).may_start


def test_archive_checks_child_evidence_and_old_v2_without_journal(
    workspace: Workspace, owner: Actor, tmp_path: Path
) -> None:
    _, lease = operation(workspace, owner)
    journal, intent = succeeded(workspace, lease)
    child = workspace.blobs.put(b"retained evidence fixture")
    journal.retain_capture(intent, source(), {"dependencies": {"child": child}})
    (workspace.blobs.directory / child[:2] / child).unlink()
    with pytest.raises(VersionUnavailable):
        archive.backup(workspace, tmp_path / "broken")
    old = Workspace(tmp_path / "old-core-v2")
    with old.database.transaction() as connection:
        connection.execute("DROP TABLE weather_acquisitions")
    archive.backup(old, tmp_path / "old-backup")
    restored = archive.restore(tmp_path / "old-backup", tmp_path / "upgraded")
    with restored.database.read() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM weather_acquisitions").fetchone()[
                0
            ]
            == 0
        )
