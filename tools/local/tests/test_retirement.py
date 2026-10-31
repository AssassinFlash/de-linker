"""Synthetic owned resources only: no real database, Redis or local site."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from linker_local import cli, objectcache, retirement, server, services
from linker_local.checkout import Checkout
from linker_local.instance import Instance
from linker_local.private_config import lifecycle_lock
from linker_local.registry import Registry


@pytest.fixture
def owned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Instance:
    root = tmp_path / "instances"
    instance = Instance("retire_test", 19001, 19002, 19003, root)
    instance.dir.mkdir(parents=True)
    registry = Registry(root)
    registry._write({instance.name: instance})
    monkeypatch.setenv("LINKER_LOCAL_HOME", str(root))
    monkeypatch.setattr("linker_local.registry.SHARED", root)
    monkeypatch.setattr(server, "stop", Mock(return_value=False))
    monkeypatch.setattr(services, "stop", Mock(return_value=[]))
    monkeypatch.setattr(retirement, "port_is_free", lambda port: True)
    mysql = Mock()
    mysql.query.return_value = ""
    mysql.database_exists.return_value = False
    monkeypatch.setattr(retirement, "MySQL", Mock(return_value=mysql))
    monkeypatch.setattr(objectcache, "forget", Mock(return_value=0))
    return instance


def run(
    instance: Instance,
    *,
    write: bool = False,
    preserve: list[str] | None = None,
    discard: list[str] | None = None,
    destination: Path | None = None,
) -> dict[str, object]:
    return retirement.retire(
        instance.root,
        instance.name,
        write=write,
        preserve=preserve or [],
        discard=discard or [],
        preserve_to=destination,
    )


def test_plan_is_read_only_and_lists_unknown_evidence(owned: Instance) -> None:
    (owned.dir / "unique-failure.json").write_text("failure")
    assert run(owned)["unconfirmed"] == ["unique-failure.json"]
    assert not (owned.root / ".lifecycle").exists()
    with pytest.raises(RuntimeError, match="confirm evidence"):
        run(owned, write=True)
    assert (owned.dir / "unique-failure.json").is_file()
    assert Registry(owned.root).get(owned.name) == owned


def test_complete_retirement_moves_only_selected_evidence_and_preserves_shared(
    owned: Instance,
    tmp_path: Path,
) -> None:
    snapshot = owned.root / "snapshots" / "current"
    snapshot.mkdir(parents=True)
    (snapshot / "original").write_text("original")
    (owned.dir / "snapshot.json").write_text("source metadata")
    owned.wp_content.mkdir(parents=True)
    (owned.wp_content / "uploads").symlink_to(snapshot, target_is_directory=True)
    (owned.dir / "failure.txt").write_text("unique failure")
    destination = tmp_path / "accepted-evidence"
    result = run(
        owned,
        write=True,
        preserve=["failure.txt"],
        discard=["snapshot.json", "wordpress/wp-content/uploads"],
        destination=destination,
    )
    assert result["status"] == "retired"
    assert (destination / "failure.txt").read_text() == "unique failure"
    assert (snapshot / "original").read_text() == "original"
    assert not owned.dir.exists()
    assert Registry(owned.root).get(owned.name) is None
    assert not retirement.marker_path(owned.root, owned.name).exists()
    assert run(owned, write=True)["status"] == "already retired"


def test_failed_redis_reclamation_resumes_after_directory_and_registry_removal(
    owned: Instance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forget = Mock(side_effect=RuntimeError("redis unavailable"))
    monkeypatch.setattr(objectcache, "forget", forget)
    with pytest.raises(RuntimeError, match="redis unavailable"):
        run(owned, write=True)
    assert not owned.dir.exists()
    assert Registry(owned.root).get(owned.name) is None
    assert retirement.marker_path(owned.root, owned.name).exists()
    with pytest.raises(RuntimeError, match="retirement is incomplete"):
        retirement.require_available(owned.root, owned.name)
    forget.side_effect = None
    forget.return_value = 0
    assert run(owned, write=True)["status"] == "retired"


def test_lifecycle_lock_survives_instance_directory_deletion(owned: Instance) -> None:
    path = retirement.lock_path(owned.root, owned.name)
    with lifecycle_lock(path):
        owned.dir.rmdir()
        with pytest.raises(RuntimeError, match="already being managed"):
            run(owned, write=True)
    assert path.is_file()
    assert run(owned, write=True)["status"] == "retired"


def test_drain_failure_preserves_database_files_and_registration(
    owned: Instance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = owned.dir / "planner"
    planner.mkdir()
    (planner / "runtime.json").write_text("{}")
    worker = Mock()
    worker.control.return_value = {"draining": False}
    worker.drain.side_effect = RuntimeError("active calculation")
    monkeypatch.setattr(retirement, "PlannerWorker", Mock(return_value=worker))
    monkeypatch.setattr(Checkout, "here", Mock())
    monkeypatch.setattr(retirement, "engine_project", Mock())
    monkeypatch.setattr(services, "_uv", Mock())
    with pytest.raises(RuntimeError, match="active calculation"):
        run(owned, write=True, discard=["planner"])
    assert (planner / "runtime.json").exists()
    assert Registry(owned.root).get(owned.name) == owned
    assert isinstance(server.stop, Mock) and server.stop.call_count == 0
    assert isinstance(services.stop, Mock) and services.stop.call_count == 0
    assert worker.control.call_args_list[-1].args == ("resume",)
    assert not retirement.marker_path(owned.root, owned.name).exists()


def test_active_database_connection_blocks_removal(
    owned: Instance, monkeypatch: pytest.MonkeyPatch
) -> None:
    mysql = Mock()
    monkeypatch.setattr(retirement, "MySQL", Mock(return_value=mysql))
    mysql.query.return_value = "123\n"
    with pytest.raises(RuntimeError, match="still has connections"):
        run(owned, write=True)
    mysql.drop_database.assert_not_called()
    assert owned.dir.exists()


def test_changed_registration_blocks_resume(
    owned: Instance, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        objectcache, "forget", Mock(side_effect=RuntimeError("offline"))
    )
    with pytest.raises(RuntimeError, match="offline"):
        run(owned, write=True)
    other = Instance(owned.name, 20001, 20002, 20003, owned.root)
    Registry(owned.root)._write({other.name: other})
    with pytest.raises(RuntimeError, match="registration changed"):
        run(owned, write=True)
    assert Registry(owned.root).get(owned.name) == other


def test_up_refuses_pending_retirement_before_provisioning(
    owned: Instance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_preconditions", Mock(return_value=(Path("php"), Mock())))
    marker = retirement.marker_path(owned.root, owned.name)
    marker.parent.mkdir()
    marker.write_text("{}")
    assert cli.main(["up", owned.name]) == 1
    assert Registry(owned.root).get(owned.name) == owned


def test_database_failure_after_evidence_transfer_is_resumable(
    owned: Instance,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (owned.dir / "unique.txt").write_text("only copy")
    destination = tmp_path / "unique-evidence"
    mysql = Mock()
    mysql.query.return_value = ""
    mysql.database_exists.return_value = False
    mysql.drop_database.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(retirement, "MySQL", Mock(return_value=mysql))
    with pytest.raises(RuntimeError, match="database unavailable"):
        run(owned, write=True, preserve=["unique.txt"], destination=destination)
    assert (destination / "unique.txt").read_text() == "only copy"
    assert Registry(owned.root).get(owned.name) == owned
    mysql.drop_database.side_effect = None
    assert run(owned, write=True)["status"] == "retired"
    assert (destination / "unique.txt").read_text() == "only copy"


def test_cache_readback_failure_keeps_resumable_marker(
    owned: Instance, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(objectcache, "forget", Mock(side_effect=[3, 1]))
    with pytest.raises(RuntimeError, match="cache changed"):
        run(owned, write=True)
    assert retirement.marker_path(owned.root, owned.name).exists()


def test_registry_cannot_reuse_name_before_cache_reclamation_finishes(
    owned: Instance,
) -> None:
    marker = retirement.marker_path(owned.root, owned.name)
    marker.parent.mkdir()
    marker.write_text("{}")
    with pytest.raises(RuntimeError, match="retirement must finish"):
        Registry(owned.root).register(owned.name)


def test_live_worker_without_policy_is_never_force_stopped(
    owned: Instance, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = Mock()
    process.pid.return_value = 42
    monkeypatch.setattr(retirement, "Background", Mock(return_value=process))
    with pytest.raises(RuntimeError, match="no runtime policy"):
        run(owned, write=True)
    process.stop.assert_not_called()
    assert owned.dir.exists()


def test_preserve_never_overwrites_dangling_destination(
    owned: Instance, tmp_path: Path
) -> None:
    (owned.dir / "unique").write_text("only copy")
    destination = tmp_path / "accepted"
    destination.mkdir()
    (destination / "unique").symlink_to(tmp_path / "missing")
    with pytest.raises(RuntimeError, match="destination already exists"):
        run(owned, write=True, preserve=["unique"], destination=destination)
    assert (owned.dir / "unique").read_text() == "only copy"


def test_parent_preserve_choice_deduplicates_children_before_transfer(
    owned: Instance,
    tmp_path: Path,
) -> None:
    logs = owned.dir / "logs"
    logs.mkdir()
    (logs / "failure.json").write_text("only copy")
    destination = tmp_path / "evidence"
    assert (
        run(
            owned,
            write=True,
            preserve=["logs/failure.json", "logs"],
            destination=destination,
        )["status"]
        == "retired"
    )
    assert (destination / "logs/failure.json").read_text() == "only copy"


def test_drain_keeps_php_dependency_running_until_pending_work_finishes(
    owned: Instance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = owned.dir / "planner"
    planner.mkdir()
    (planner / "runtime.json").write_text("{}")
    worker = Mock()
    worker.control.return_value = {"draining": False}
    events: list[str] = []

    def drain() -> None:
        assert not events  # Neither PHP nor engine/worker has been stopped.
        events.append("drained-with-publication-available")

    worker.drain.side_effect = drain
    monkeypatch.setattr(retirement, "PlannerWorker", Mock(return_value=worker))
    monkeypatch.setattr(Checkout, "here", Mock())
    monkeypatch.setattr(retirement, "engine_project", Mock())
    monkeypatch.setattr(services, "_uv", Mock())
    monkeypatch.setattr(server, "stop", lambda _: events.append("php-stopped"))
    monkeypatch.setattr(services, "stop", lambda _: events.append("pair-stopped"))
    assert run(owned, write=True, discard=["planner"])["status"] == "retired"
    assert events == [
        "drained-with-publication-available",
        "pair-stopped",
        "php-stopped",
    ]


def test_marker_publication_failure_restores_admission_and_removes_own_marker(
    owned: Instance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = owned.dir / "planner"
    planner.mkdir()
    (planner / "runtime.json").write_text("{}")
    worker = Mock()
    worker.control.return_value = {"draining": False}
    monkeypatch.setattr(retirement, "PlannerWorker", Mock(return_value=worker))
    monkeypatch.setattr(Checkout, "here", Mock())
    monkeypatch.setattr(retirement, "engine_project", Mock())
    monkeypatch.setattr(services, "_uv", Mock())

    def failed_publish(path: Path, note: dict[str, object]) -> None:
        path.write_text("{}")
        raise OSError("directory fsync failed")

    monkeypatch.setattr(retirement, "publish_once", failed_publish)
    with pytest.raises(OSError, match="fsync"):
        run(owned, write=True, discard=["planner"])
    assert worker.control.call_args_list[-1].args == ("resume",)
    assert not retirement.marker_path(owned.root, owned.name).exists()
    retirement.require_available(owned.root, owned.name)


def test_private_policy_write_failure_removes_its_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    from linker_local.private_config import publish_once

    def fail(_: int) -> None:
        raise OSError("write fsync failed")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="fsync"):
        publish_once(tmp_path / "policy.json", {"schema": 1})
    assert list(tmp_path.iterdir()) == []


def test_wordpress_files_and_local_code_edits_require_explicit_retirement_decisions(
    owned: Instance,
    tmp_path: Path,
) -> None:
    plugin = owned.wp_content / "plugins/local-code"
    plugin.mkdir(parents=True)
    (plugin / "uncommitted.php").write_text("unique local edit")
    (owned.docroot / "failure-proof.json").write_text("unique evidence")
    shared = tmp_path / "shared-wordpress-snapshot"
    shared.mkdir()
    (shared / "shared-file").write_text("original")
    (owned.wp_content / "themes").symlink_to(shared, target_is_directory=True)
    plan = run(owned)
    assert plan["unconfirmed"] == [
        "wordpress/failure-proof.json",
        "wordpress/wp-content/plugins/local-code/uncommitted.php",
        "wordpress/wp-content/themes",
    ]
    with pytest.raises(RuntimeError, match="confirm evidence"):
        run(owned, write=True)
    destination = tmp_path / "preserved-code"
    assert (
        run(
            owned,
            write=True,
            preserve=["wordpress/wp-content/plugins/local-code"],
            discard=["wordpress/failure-proof.json", "wordpress/wp-content/themes"],
            destination=destination,
        )["status"]
        == "retired"
    )
    assert (
        destination / "wordpress/wp-content/plugins/local-code/uncommitted.php"
    ).read_text() == "unique local edit"
    assert (shared / "shared-file").read_text() == "original"


def test_new_evidence_after_drain_can_be_explicitly_preserved_on_resume(
    owned: Instance,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = owned.dir / "planner"
    planner.mkdir()
    (planner / "runtime.json").write_text("{}")
    worker = Mock()
    worker.control.return_value = {"draining": False}
    late = owned.dir / "new-failure.json"
    worker.drain.side_effect = lambda: late.write_text("unique late evidence")
    monkeypatch.setattr(retirement, "PlannerWorker", Mock(return_value=worker))
    monkeypatch.setattr(Checkout, "here", Mock())
    monkeypatch.setattr(retirement, "engine_project", Mock())
    monkeypatch.setattr(services, "_uv", Mock())
    with pytest.raises(RuntimeError, match="new evidence appeared"):
        run(owned, write=True, discard=["planner"])
    assert retirement.marker_path(owned.root, owned.name).exists()
    assert late.read_text() == "unique late evidence"
    worker.drain.side_effect = None
    destination = tmp_path / "late-evidence"
    assert (
        run(owned, write=True, preserve=["new-failure.json"], destination=destination)[
            "status"
        ]
        == "retired"
    )
    assert (destination / "new-failure.json").read_text() == "unique late evidence"
    assert not retirement.marker_path(owned.root, owned.name).exists()
