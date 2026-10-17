"""The deploy's filesystem seam, using real rsync and shell on a temp target."""

import os
import shutil
from pathlib import Path

import pytest

from linker_cutover import atomic
from linker_cutover.target import Target


def local_target(root: Path) -> Target:
    """An sshd-free stand-in; production runs the same scripts via Target.shell."""
    return Target("fixture", str(root), "http://127.0.0.1", (), None, None)


def test_plugin_switch_renames_complete_trees_and_retains_previous(
    tmp_path: Path,
) -> None:
    """The previous tree's inode survives: it was renamed, never copied in place."""
    target = local_target(tmp_path / "site with spaces")
    live = Path(target.path_of("wp-content/plugins/example"))
    live.mkdir(parents=True)
    (live / "plugin.php").write_text("old entry")
    (live / "removed.php").write_text("old dependency")
    old_inode = live.stat().st_ino
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new entry")
    (source / "dependency.php").write_text("new dependency")

    receipt = atomic.publish(target, source, "wp-content/plugins/example")

    assert (live / "plugin.php").read_text() == "new entry"
    assert (live / "dependency.php").read_text() == "new dependency"
    assert not (live / "removed.php").exists()
    previous = live.with_name(".example.prev")
    assert previous.stat().st_ino == old_inode
    assert (previous / "removed.php").read_text() == "old dependency"
    assert "rename wp-content/plugins/example:" in receipt
    assert receipt.strip().endswith(" s")


def test_owned_file_is_replaced_by_rename_without_removing_neighbours(
    tmp_path: Path,
) -> None:
    """MU plugins and child theme assets owned by the host stay in place."""
    target = local_target(tmp_path / "site")
    live = Path(target.path_of("wp-content/mu-plugins/recorder.php"))
    live.parent.mkdir(parents=True)
    live.write_text("old recorder")
    neighbour = live.with_name("host.php")
    neighbour.write_text("host plugin")
    source = tmp_path / "recorder.php"
    source.write_text("new recorder")
    # Keeping this descriptor open proves the live file was not truncated by rsync.
    with live.open() as old:
        atomic.publish(target, source, "wp-content/mu-plugins/recorder.php")
        assert old.read() == "old recorder"
    assert live.read_text() == "new recorder"
    assert live.with_name(".recorder.php.prev").read_text() == "old recorder"
    assert neighbour.read_text() == "host plugin"


def test_rollback_restores_plugins_and_owned_files_in_one_call(tmp_path: Path) -> None:
    """The rollback command restores both path kinds and removes new additions."""
    target = local_target(tmp_path / "site")
    plugin = "wp-content/plugins/example"
    theme = "wp-content/themes/child/functions.php"
    added = "wp-content/mu-plugins/new.php"
    live = Path(target.path_of(plugin))
    live.mkdir(parents=True)
    (live / "plugin.php").write_text("old plugin")
    theme_file = Path(target.path_of(theme))
    theme_file.parent.mkdir(parents=True)
    theme_file.write_text("old theme")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new plugin")
    new_file = tmp_path / "new.php"
    new_file.write_text("new file")
    atomic.publish(target, source, plugin)
    atomic.publish(target, new_file, theme)
    atomic.publish(target, new_file, added)

    atomic.rollback(target, [plugin, theme, added])

    assert (live / "plugin.php").read_text() == "old plugin"
    assert theme_file.read_text() == "old theme"
    assert not Path(target.path_of(added)).exists()


def test_rollback_preflights_every_path_before_changing_anything(
    tmp_path: Path,
) -> None:
    """A missing saved version stops the operator before a partial rollback."""
    target = local_target(tmp_path / "site")
    live = Path(target.path_of("wp-content/plugins/example"))
    live.mkdir(parents=True)
    (live / "plugin.php").write_text("old")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    atomic.publish(target, source, "wp-content/plugins/example")
    with pytest.raises(RuntimeError, match="no previous deployment"):
        atomic.rollback(target, ["wp-content/plugins/example", "missing"])
    assert (live / "plugin.php").read_text() == "new"


@pytest.mark.parametrize("interrupt", [False, True])
def test_failed_second_rename_restores_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interrupt: bool
) -> None:
    """A failed mv or TERM in the two-rename gap must not leave live missing."""
    target = local_target(tmp_path / "site")
    live = Path(target.path_of("wp-content/plugins/example"))
    live.mkdir(parents=True)
    (live / "plugin.php").write_text("old")
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    commands = tmp_path / "bin"
    commands.mkdir()
    real_mv = shutil.which("mv")
    assert real_mv
    failure = 'kill -TERM "$PPID"; exit 1' if interrupt else "exit 1"
    shim = commands / "mv"
    shim.write_text(
        "#!/bin/bash\n"
        f'if [[ "$1" == */.example.next ]]; then {failure}; fi\n'
        f'exec "{real_mv}" "$@"\n'
    )
    shim.chmod(0o755)  # Executable fixture command, the POSIX program mode.
    monkeypatch.setenv("PATH", f"{commands}{os.pathsep}{os.environ['PATH']}")
    with pytest.raises(RuntimeError):
        atomic.publish(target, source, "wp-content/plugins/example")
    assert (live / "plugin.php").read_text() == "old"


@pytest.mark.parametrize("directory", [False, True])
def test_interrupted_upload_keeps_live_and_previous_and_can_be_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: bool
) -> None:
    """A partial transfer never reaches live or destroys the last rollback."""
    target = local_target(tmp_path / "site")
    relative = (
        "wp-content/plugins/example"
        if directory
        else "wp-content/mu-plugins/example.php"
    )
    live = Path(target.path_of(relative))
    live.parent.mkdir(parents=True)
    source = tmp_path / "release"
    if directory:
        source.mkdir()
        live.mkdir()
        old_file, new_file = live / "plugin.php", source / "plugin.php"
    else:
        old_file, new_file = live, source
    old_file.write_text("version one")
    new_file.write_text("version two")
    atomic.publish(target, source, relative)
    new_file.write_text("version three")
    commands = tmp_path / "bin"
    commands.mkdir()
    shim = commands / "rsync"
    shim.write_text(
        '#!/bin/bash\ndestination="${@: -1}"\n'
        'if [[ "$destination" == */ ]]; then\n'
        '    mkdir -p "$destination"\n'
        '    printf partial > "$destination/plugin.php"\n'
        'else\n'
        '    printf partial > "$destination"\n'
        'fi\nexit 23\n'  # rsync partial-transfer exit status.
    )
    shim.chmod(0o755)  # Executable POSIX program mode.
    original_path = os.environ["PATH"]
    monkeypatch.setenv("PATH", f"{commands}{os.pathsep}{original_path}")
    with pytest.raises(RuntimeError):
        atomic.publish(target, source, relative)
    assert old_file.read_text() == "version two"
    previous = live.with_name(f".{live.name}.prev")
    saved_file = previous / "plugin.php" if directory else previous
    assert saved_file.read_text() == "version one"
    monkeypatch.setenv("PATH", original_path)
    atomic.publish(target, source, relative)
    assert old_file.read_text() == "version three"
    assert saved_file.read_text() == "version two"
