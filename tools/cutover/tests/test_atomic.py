"""Whole-deployment filesystem behavior through the publication boundary."""

import json
import os
import shutil
from pathlib import Path

import pytest

from linker_cutover import atomic
from linker_cutover.target import CutoverError, Target


def target_at(root: Path) -> Target:
    """The production shell/rsync path, without SSH or WordPress."""
    return Target("fixture", str(root), "http://127.0.0.1", (), None, None)


def test_all_artifacts_are_uploaded_before_one_switch(tmp_path: Path) -> None:
    """An upload of a later dependency must still observe every live version as old."""
    root = tmp_path / "site with spaces"
    relatives = ("wp-content/plugins/first", "wp-content/plugins/second")
    for relative in relatives:
        live = root / relative
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
    uploads_seen: list[str] = []
    switches: list[str] = []

    class ObservedTarget(Target):
        def copy_in(self, source: Path, relative: str) -> None:
            assert all(
                (root / path / "plugin.php").read_text() == "old" for path in relatives
            )
            super().copy_in(source, relative)
            uploads_seen.append(relative)

        def shell(self, script: str) -> str:
            if "TIMEFORMAT=" in script:
                assert len(uploads_seen) == len(relatives)
                switches.append(script)
            return super().shell(script)

    target = ObservedTarget("fixture", str(root), "http://127.0.0.1", (), None, None)
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    artifacts = [atomic.Artifact(source, relative) for relative in relatives]

    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-abc123")

    assert all((root / path / "plugin.php").read_text() == "new" for path in relatives)
    assert len(switches) == 1
    assert receipt.deploy_id == "20261018T000000Z-abc123"
    assert receipt.switch_seconds is not None
    assert receipt.switch_seconds >= 0


def test_rollback_rejects_mixed_deploy_ids_before_changing_live(tmp_path: Path) -> None:
    """A saved path from another deployment must be named, not silently mixed in."""
    target = target_at(tmp_path / "site")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    relatives = ("wp-content/plugins/first", "wp-content/plugins/second")
    for relative in relatives:
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
    receipt = atomic.publish(
        target,
        [atomic.Artifact(source, path) for path in relatives],
        deploy_id="20261018T000000Z-abc123",
    )
    manifest_path = Path(receipt.backup_directory) / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["backups"][0]["deploy_id"] = "20261017T000000Z-older"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(RuntimeError, match="first.*deploy id"):
        atomic.rollback(target, list(relatives))

    assert all(
        (Path(target.root) / path / "plugin.php").read_text() == "new"
        for path in relatives
    )


def test_rollback_restores_whole_batch_and_reports_actual_identities(
    tmp_path: Path,
) -> None:
    """Trees, owned files and first-time additions share one reversible batch."""
    php = shutil.which("php")
    if php is None:
        pytest.skip("native PHP is required for the UI compatibility guard")
    php_command: str = php
    state_file = tmp_path / "private-state.json"
    state = {
        "schema_version": 1,
        "input_inventory_sha256": "a" * 64,
        "retained_revision_count": 0,
        "retained_input_count": 0,
        "required_input_contracts": [],
        "supported_input_contracts": ["installation_pv_string_links_v1"],
    }
    state_file.write_text(json.dumps(state))
    # Real PHP guard/rename code; only the already-tested private transport is
    # replaced by an exact team-only status reply in this filesystem fixture.
    prelude = r"""
namespace Linker\Tools\Planner {
class Principal { public function __construct(public string $kind, public string $subject) {} }
class Transport { public function object($actor,$path,$body) { if ($actor->kind!=='team'||$path!=='inputs/contracts'||$body!==['schema_version'=>1]) throw new \RuntimeException('wrong private contract'); return json_decode(file_get_contents(getenv('PLANNER_FIXTURE_STATE')),true); } }
}
namespace { define('WP_CLI',true); function get_option($key,$default='') { return $key==='linker_planner_url'?'https://private.invalid/planning':$default; } function is_wp_error($value) { return false; } eval($argv[2]); }
"""

    class NativeGuardTarget(Target):
        def wp_on_target(self) -> list[str]:
            return [
                "env",
                "PLANNER_FIXTURE_STATE=" + str(state_file),
                php_command,
                "-r",
                prelude,
            ]

    target = NativeGuardTarget(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    old_tree = Path(target.path_of("wp-content/plugins/linker-tools"))
    old_tree.mkdir(parents=True)
    (old_tree / "plugin.php").write_text("old plugin")
    old_inode = old_tree.stat().st_ino
    theme = Path(target.path_of("wp-content/themes/child/functions.php"))
    theme.parent.mkdir(parents=True)
    theme.write_text("old theme")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new plugin")
    (source / "project-input-contracts.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_input_contracts": ["installation_pv_string_links_v1"],
            }
        )
    )
    (source / "build/planner").mkdir(parents=True)
    (source / "build/planner/source-manifest.json").write_text(
        json.dumps({"project_input_contracts": ["installation_pv_string_links_v1"]})
    )
    new_file = tmp_path / "new.php"
    new_file.write_text("new file")
    artifacts = [
        atomic.Artifact(source, "wp-content/plugins/linker-tools"),
        atomic.Artifact(new_file, "wp-content/themes/child/functions.php"),
        atomic.Artifact(new_file, "wp-content/mu-plugins/added.php"),
    ]
    atomic.publish(target, artifacts, deploy_id="20261018T000000Z-abc123")

    # No retained link inputs are needed to refuse an old UI: the active
    # backend's write capabilities alone protect its next complete-input save.
    with pytest.raises(CutoverError, match="planner UI input compatibility refused"):
        atomic.rollback(target, [entry.relative for entry in artifacts])
    assert (old_tree / "plugin.php").read_text() == "new plugin"
    assert theme.read_text() == "new file"
    assert not theme.with_name(".functions.php.next").exists()
    # A legitimate backend rollback is allowed here because history is empty.
    state["supported_input_contracts"] = []
    state_file.write_text(json.dumps(state))

    restored = atomic.rollback(target, [entry.relative for entry in artifacts])

    assert (old_tree / "plugin.php").read_text() == "old plugin"
    assert old_tree.stat().st_ino == old_inode
    assert theme.read_text() == "old theme"
    assert not Path(target.path_of("wp-content/mu-plugins/added.php")).exists()
    assert any(
        "wp-content/plugins/linker-tools" in line and str(old_inode) in line
        for line in restored.readbacks
    )
    assert any("added.php: absent" in line for line in restored.readbacks)


def test_verified_backup_moves_outside_web_root_and_only_latest_is_kept(
    tmp_path: Path,
) -> None:
    """Archiving and rollback both rename the original tree on the same device."""
    target = target_at(tmp_path / "site")
    relative = "wp-content/plugins/first"
    live = Path(target.path_of(relative))
    live.mkdir(parents=True)
    (live / "plugin.php").write_text("original")
    original_inode = live.stat().st_ino
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("version one")
    artifacts = [atomic.Artifact(source, relative)]
    first = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-first")

    atomic.archive(target, first)

    saved = Path(first.backup_directory) / "files" / relative
    assert saved.stat().st_ino == original_inode
    assert not saved.is_relative_to(Path(target.root))
    assert not list(Path(target.root).rglob("*.prev"))
    assert not list(Path(target.root).rglob("*.prev-absent"))
    (source / "plugin.php").write_text("version two")
    second = atomic.publish(target, artifacts, deploy_id="20261018T000001Z-second")
    atomic.archive(target, second)
    assert not Path(first.backup_directory).exists()
    atomic.rollback(target, [relative])
    assert (live / "plugin.php").read_text() == "version one"


def test_owned_file_rename_keeps_open_descriptor_and_host_neighbour(
    tmp_path: Path,
) -> None:
    target = target_at(tmp_path / "site")
    relative = "wp-content/mu-plugins/recorder.php"
    live = Path(target.path_of(relative))
    live.parent.mkdir(parents=True)
    live.write_text("old")
    host = live.with_name("host.php")
    host.write_text("host")
    source = tmp_path / "recorder.php"
    source.write_text("new")
    with live.open() as descriptor:
        receipt = atomic.publish(
            target,
            [atomic.Artifact(source, relative)],
            deploy_id="20261018T000000Z-file",
        )
        assert descriptor.read() == "old"
    atomic.archive(target, receipt)
    assert live.read_text() == "new"
    assert host.read_text() == "host"
    assert not list(live.parent.glob(".*.prev*"))


def test_successful_archive_prunes_killed_batches_without_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incomplete private batches survive a failed archive, then are pruned."""
    target, artifacts = batch_fixture(tmp_path)
    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000001Z-current")
    killed = Path(atomic.backup_root(target)) / "20261018T000000Z-killed"
    killed.mkdir()
    (killed / "manifest.json.next").write_text("partial")
    original_path = os.environ["PATH"]
    real_mv = shutil.which("mv")
    command_shim(
        tmp_path,
        monkeypatch,
        "mv",
        f'if [[ "$1" == */.first.prev ]]; then exit 1; fi\nexec "{real_mv}" "$@"\n',
    )
    with pytest.raises(CutoverError):
        atomic.archive(target, receipt)
    assert killed.exists()
    monkeypatch.setenv("PATH", original_path)

    atomic.archive(target, receipt)

    assert not killed.exists()
    assert Path(receipt.backup_directory, "manifest.json").is_file()
    atomic.rollback(target, [item.relative for item in artifacts])


def batch_fixture(tmp_path: Path) -> tuple[Target, list[atomic.Artifact]]:
    target = target_at(tmp_path / "site")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    source_file = tmp_path / "file.php"
    source_file.write_text("new file")
    artifacts = [
        atomic.Artifact(source, "wp-content/plugins/first"),
        atomic.Artifact(source_file, "wp-content/mu-plugins/owned.php"),
        atomic.Artifact(source, "wp-content/plugins/second"),
    ]
    for artifact in artifacts:
        live = Path(target.path_of(artifact.relative))
        live.parent.mkdir(parents=True, exist_ok=True)
        if artifact.source.is_dir():
            live.mkdir()
            (live / "plugin.php").write_text("old")
        else:
            live.write_text("old file")
    return target, artifacts


@pytest.mark.parametrize("operation", ["publish", "rollback"])
@pytest.mark.parametrize("reply", ["noise", "missing", "invalid"])
def test_switch_timing_uses_only_marker_and_reports_parse_failure(
    tmp_path: Path, operation: str, reply: str
) -> None:
    """A noisy transport reply is harmless; lost timing is a managed failure."""
    target, artifacts = batch_fixture(tmp_path)

    class ReplyTarget(Target):
        def shell(self, script: str) -> str:
            output = super().shell(script)
            if "TIMEFORMAT=" not in script:
                return output
            if reply == "noise":
                return "transport notice\n" + output + "unrelated stderr\n"
            return "" if reply == "missing" else "LINKER_CUTOVER_SWITCH_SECONDS=bad\n"

    noisy = ReplyTarget("fixture", target.root, target.base_url, (), None, None)
    deploy_id = "20261018T000000Z-timing"
    if operation == "rollback":
        atomic.publish(target, artifacts, deploy_id=deploy_id)

    def switch() -> atomic.Receipt:
        if operation == "publish":
            return atomic.publish(noisy, artifacts, deploy_id=deploy_id)
        return atomic.rollback(noisy, [item.relative for item in artifacts])

    if reply == "noise":
        elapsed = switch().switch_seconds
        assert elapsed is not None and elapsed >= 0
    else:
        with pytest.raises(CutoverError, match="switch timing"):
            switch()
        if operation == "publish":
            _, manifest = atomic.latest_manifest(target)
            assert manifest.state == "pending"
            atomic.rollback(target, [item.relative for item in artifacts])


def command_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, program: str, body: str
) -> None:
    commands = tmp_path / "commands"
    commands.mkdir(exist_ok=True)
    shim = commands / program
    shim.write_text("#!/bin/bash\n" + body)
    shim.chmod(0o755)  # Executable fixture: the POSIX program mode.
    monkeypatch.setenv("PATH", f"{commands}{os.pathsep}{os.environ['PATH']}")


def test_publish_recovery_restores_live_before_failing_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed rm must only leave the rejected tree, never damage restored live."""
    target, artifacts = batch_fixture(tmp_path)
    live = Path(target.path_of(artifacts[0].relative))
    old_inode = live.stat().st_ino
    real_mv, real_rm = shutil.which("mv"), shutil.which("rm")
    command_shim(
        tmp_path,
        monkeypatch,
        "mv",
        f'if [[ "$1" == */.second.next ]]; then exit 1; fi\nexec "{real_mv}" "$@"\n',
    )
    command_shim(
        tmp_path,
        monkeypatch,
        "rm",
        'path="${@: -1}"\n'
        'if [[ "$path" == */plugins/first || "$path" == */.first.failed ]]; then exit 1; fi\n'
        f'exec "{real_rm}" "$@"\n',
    )

    with pytest.raises(RuntimeError):
        atomic.publish(target, artifacts, deploy_id="20261018T000000Z-rm-failed")

    assert (live / "plugin.php").read_text() == "old"
    assert live.stat().st_ino == old_inode
    assert (live.with_name(".first.failed") / "plugin.php").read_text() == "new"


@pytest.mark.parametrize("interrupt", [False, True])
def test_failure_in_later_rename_restores_every_earlier_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interrupt: bool
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    real_mv = shutil.which("mv")
    action = 'kill -TERM "$PPID"; exit 1' if interrupt else "exit 1"
    command_shim(
        tmp_path,
        monkeypatch,
        "mv",
        f'if [[ "$1" == */.second.next ]]; then {action}; fi\nexec "{real_mv}" "$@"\n',
    )
    with pytest.raises(RuntimeError):
        atomic.publish(target, artifacts, deploy_id="20261018T000000Z-failure")
    for item in artifacts:
        live = Path(target.path_of(item.relative))
        assert (
            (live / "plugin.php").read_text()
            if item.source.is_dir()
            else live.read_text()
        ) == ("old" if item.source.is_dir() else "old file")


@pytest.mark.parametrize("interrupted_plugin", ["first", "second"])
def test_interrupted_whole_rollback_restores_current_batch_then_can_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interrupted_plugin: str
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-rollback")
    atomic.archive(target, receipt)
    real_mv = shutil.which("mv")
    original_path = os.environ["PATH"]
    command_shim(
        tmp_path,
        monkeypatch,
        "mv",
        f'if [[ "$1" == */files/wp-content/plugins/{interrupted_plugin} ]]; then kill -TERM "$PPID"; exit 1; fi\n'
        + f'exec "{real_mv}" "$@"\n',
    )
    with pytest.raises(RuntimeError):
        atomic.rollback(target, [item.relative for item in artifacts])
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "new"
    assert Path(target.path_of(artifacts[1].relative)).read_text() == "new file"
    monkeypatch.setenv("PATH", original_path)
    atomic.rollback(target, [item.relative for item in artifacts])
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "old"


def test_archive_interrupted_after_manifest_commit_restores_pending_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    receipt = atomic.publish(
        target, artifacts, deploy_id="20261018T000000Z-archive-commit"
    )
    real_mv = shutil.which("mv")
    original_path = os.environ["PATH"]
    command_shim(
        tmp_path,
        monkeypatch,
        "mv",
        'source="${@: -2:1}"\ndestination="${@: -1}"\n'
        'if [[ "$destination" == */manifest.json ]]; then\n'
        '    contents=$(<"$source")\n'
        '    if [[ "$contents" == *\'"state": "archived"\'* ]]; then\n'
        f'        "{real_mv}" "$@"\n'
        '        kill -TERM "$PPID"; exit 1\n'
        "    fi\nfi\n"
        f'exec "{real_mv}" "$@"\n',
    )
    with pytest.raises(RuntimeError):
        atomic.archive(target, receipt)
    monkeypatch.setenv("PATH", original_path)
    _, manifest = atomic.latest_manifest(target)
    assert manifest.state == "pending"
    atomic.archive(target, receipt)
    atomic.rollback(target, [item.relative for item in artifacts])
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "old"


def test_archive_on_another_filesystem_is_rejected_before_live_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    real_stat = shutil.which("stat")
    command_shim(
        tmp_path,
        monkeypatch,
        "stat",
        'if [[ "${@: -1}" == */deploy-prev ]]; then printf "other-device:inode\\n"; exit 0; fi\n'
        + f'exec "{real_stat}" "$@"\n',
    )
    with pytest.raises(RuntimeError, match="filesystem differs"):
        atomic.publish(target, artifacts, deploy_id="20261018T000000Z-device")
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "old"
    assert not list(Path(target.root).rglob("*.prev"))


@pytest.mark.parametrize("damage", ["missing", "replaced"])
def test_rollback_names_missing_or_replaced_backup_before_any_write(
    tmp_path: Path, damage: str
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-damaged")
    atomic.archive(target, receipt)
    saved = Path(receipt.backup_directory) / "files" / artifacts[0].relative
    # Keep the original directory alive so the replacement cannot reuse its inode.
    saved.rename(saved.with_name("kept-original"))
    if damage == "replaced":
        saved.mkdir()
        (saved / "plugin.php").write_text("another deploy")
    with pytest.raises(RuntimeError, match="first.*inode mismatch"):
        atomic.rollback(target, [item.relative for item in artifacts])
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "new"


def test_failed_upload_keeps_live_and_archive_and_retry_uses_new_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    first = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-first")
    atomic.archive(target, first)
    original_path = os.environ["PATH"]
    command_shim(
        tmp_path,
        monkeypatch,
        "rsync",
        'destination="${@: -1}"\nif [[ "$destination" == */ ]]; then mkdir -p "$destination"; printf partial > "$destination/plugin.php"; else printf partial > "$destination"; fi\nexit 23\n',
    )  # rsync's partial-transfer status.
    with pytest.raises(RuntimeError):
        atomic.publish(target, artifacts, deploy_id="20261018T000001Z-second")
    assert (
        Path(target.path_of(artifacts[0].relative)) / "plugin.php"
    ).read_text() == "new"
    assert (
        Path(first.backup_directory) / "files" / artifacts[0].relative / "plugin.php"
    ).read_text() == "old"
    monkeypatch.setenv("PATH", original_path)
    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000002Z-retry")
    assert receipt.deploy_id.endswith("retry")


def test_failed_rollback_preparation_can_be_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    receipt = atomic.publish(
        target, artifacts, deploy_id="20261018T000000Z-rollback-prep"
    )
    atomic.archive(target, receipt)
    original_path = os.environ["PATH"]
    command_shim(tmp_path, monkeypatch, "ln", 'printf partial > "${@: -1}"\nexit 1\n')
    with pytest.raises(RuntimeError):
        atomic.rollback(target, [item.relative for item in artifacts])
    monkeypatch.setenv("PATH", original_path)
    restored = atomic.rollback(target, [item.relative for item in artifacts])
    assert restored.readbacks


def test_failed_backup_preparation_can_be_retried_without_mixing_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, artifacts = batch_fixture(tmp_path)
    original_path = os.environ["PATH"]
    command_shim(tmp_path, monkeypatch, "cp", 'printf partial > "${@: -1}"\nexit 1\n')
    with pytest.raises(RuntimeError):
        atomic.publish(target, artifacts, deploy_id="20261018T000000Z-failed")
    monkeypatch.setenv("PATH", original_path)
    receipt = atomic.publish(target, artifacts, deploy_id="20261018T000001Z-retry")
    assert receipt.deploy_id.endswith("retry")
