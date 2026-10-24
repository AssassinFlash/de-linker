"""Private staging modes must not disable a published browser application."""

import os
import shutil
import stat
from pathlib import Path

import pytest

from linker_cutover import atomic, steps
from linker_cutover.target import CutoverError, Target


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def private_file(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o600)


@pytest.mark.parametrize("cached_stage", [False, True])
def test_private_staging_publishes_readable_assets_without_exposing_private_files(
    tmp_path: Path, cached_stage: bool
) -> None:
    """Exercise real rsync, cache reuse, rename, archive and original-mode rollback."""
    original_umask = os.umask(0o077)
    try:
        repository = tmp_path / "checkout"
        source = repository / "plugins" / "example"
        private_file(source / "example.php", "private PHP")
        private_file(source / ".env", "synthetic private setting")
        private_file(source / "vendor" / "runtime.php", "private dependency")
        private_file(source / "assets" / "header-menu.js", "browser menu")
        private_file(source / "assets" / "fonts" / "font.ttf", "browser font")
        private_file(source / "build" / "application.js", "browser application")
        private_file(source / "build" / "application.css", "browser style")
        private_file(source / "build" / "application.asset.php", "private loader")
        private_file(source / "assets" / "private.json", "not a declared browser file")
        staging = tmp_path / "private staging"
        staged = steps.stage_plugin(repository, "example", staging)
        # Production vendor is prepared after the development vendor is excluded.
        private_file(staged / "vendor" / "runtime.php", "private runtime dependency")
        if cached_stage:
            assert steps.stage_plugin(repository, "example", staging) == staged
        assert mode(staged) == 0o700
        assert mode(staged / "assets" / "header-menu.js") == 0o600
        source_modes = {p: mode(p) for p in source.rglob("*")}
        staged_modes = {p: mode(p) for p in staged.rglob("*")}
        target = Target(
            "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
        )
        relative = "wp-content/plugins/example"
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        live.chmod(0o755)
        private_file(live / "example.php", "previous code")
        old_inode = live.stat().st_ino

        receipt = atomic.publish(
            target,
            [atomic.Artifact(staged, relative)],
            deploy_id="20261024T000000Z-modes",
        )

        for directory in (live, live / "assets", live / "assets/fonts", live / "build"):
            assert mode(directory) == 0o755
        for path in (
            "assets/header-menu.js",
            "assets/fonts/font.ttf",
            "build/application.js",
            "build/application.css",
        ):
            assert mode(live / path) == 0o644
            assert (live / path).read_bytes() == (source / path).read_bytes()
        for path in (
            "example.php",
            ".env",
            "vendor/runtime.php",
            "build/application.asset.php",
            "assets/private.json",
        ):
            assert mode(live / path) == 0o600
        assert mode(live / "vendor") == 0o700
        assert source_modes == {p: mode(p) for p in source.rglob("*")}
        assert staged_modes == {p: mode(p) for p in staged.rglob("*")}
        assert mode(staging) == 0o700
        assert mode(staging / ".stage" / "example.sha256") == 0o600
        atomic.archive(target, receipt)
        assert mode(Path(atomic.backup_root(target))) == 0o700
        atomic.rollback(target, [relative])
        assert live.stat().st_ino == old_inode
        assert mode(live) == 0o755
        assert (live / "example.php").read_text() == "previous code"
    finally:
        os.umask(original_umask)


@pytest.mark.parametrize(
    "damaged",
    [
        "root",
        "nested",
        "file",
        "link",
        "unreadable",
        "missing",
        "extra",
        "missing-tree",
        "unreadable-root",
    ],
)
def test_final_static_permission_drift_is_rejected_before_any_live_rename(
    tmp_path: Path, damaged: str
) -> None:
    """A last callback cannot make the verified candidate unreadable or redirect it."""
    source = tmp_path / "source"
    private_file(source / "assets" / "nested" / "header.js", "new")
    target = Target(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    relative = "wp-content/plugins/example"
    live = Path(target.path_of(relative))
    private_file(live / "assets" / "nested" / "header.js", "old")
    original_inode = live.stat().st_ino
    incoming = live.with_name(".example.next")

    def damage() -> None:
        if damaged == "root":
            incoming.chmod(0o700)
        elif damaged == "nested":
            (incoming / "assets" / "nested").chmod(0o700)
        elif damaged == "file":
            (incoming / "assets" / "nested" / "header.js").chmod(0o600)
        elif damaged == "link":
            (incoming / "assets" / "escaped").symlink_to(
                source, target_is_directory=True
            )
        elif damaged == "unreadable":
            (incoming / "assets" / "nested").chmod(0o000)
        elif damaged == "missing":
            (incoming / "assets" / "nested" / "header.js").unlink()
        elif damaged == "missing-tree":
            shutil.rmtree(incoming / "assets")
        elif damaged == "unreadable-root":
            incoming.chmod(0o000)
        else:
            private_file(incoming / "assets" / "extra.js", "injected browser code")
            (incoming / "assets" / "extra.js").chmod(0o644)

    with pytest.raises(CutoverError, match="public.asset"):
        atomic.publish(
            target,
            [atomic.Artifact(source, relative)],
            deploy_id="20261024T000000Z-drift",
            on_switch=damage,
        )
    assert live.stat().st_ino == original_inode
    assert (live / "assets" / "nested" / "header.js").read_text() == "old"
    assert not (Path(atomic.backup_root(target)) / "latest").exists()
    if damaged == "unreadable":
        (incoming / "assets" / "nested").chmod(0o700)
    if damaged == "unreadable-root":
        incoming.chmod(0o700)


def test_preparation_never_follows_a_link_into_private_data(tmp_path: Path) -> None:
    """A linked asset tree cannot expand the normalization scope."""
    target = Target(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    source = tmp_path / "source"
    secret = tmp_path / "private" / "setting.js"
    private_file(secret, "synthetic private data")
    private_file(source / "plugin.php", "new code")
    (source / "assets").symlink_to(secret.parent, target_is_directory=True)
    relative = "wp-content/plugins/example"
    live = Path(target.path_of(relative))
    private_file(live / "plugin.php", "old code")
    old_inode = live.stat().st_ino

    with pytest.raises(CutoverError, match="public.asset"):
        atomic.publish(
            target,
            [atomic.Artifact(source, relative)],
            deploy_id="20261024T000000Z-link",
        )

    assert mode(secret) == 0o600
    assert secret.read_text() == "synthetic private data"
    assert live.stat().st_ino == old_inode
    assert (live / "plugin.php").read_text() == "old code"


def test_static_theme_file_is_readable_and_private_mu_file_and_neighbour_stay_private(
    tmp_path: Path,
) -> None:
    """A file artifact gets its own static policy, without a recursive parent chmod."""
    target = Target(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    style = tmp_path / "style.css"
    mu = tmp_path / "guard.php"
    private_file(style, "public CSS")
    private_file(mu, "private PHP")
    neighbour = Path(target.path_of("wp-content/themes/child/private.php"))
    private_file(neighbour, "unowned code")
    before_parent = mode(neighbour.parent)

    receipt = atomic.publish(
        target,
        [
            atomic.Artifact(style, "wp-content/themes/child/style.css"),
            atomic.Artifact(mu, "wp-content/mu-plugins/guard.php"),
        ],
        deploy_id="20261024T000000Z-files",
    )

    assert mode(Path(target.path_of("wp-content/themes/child/style.css"))) == 0o644
    assert mode(Path(target.path_of("wp-content/mu-plugins/guard.php"))) == 0o600
    assert mode(neighbour) == 0o600
    assert mode(neighbour.parent) == before_parent
    atomic.archive(target, receipt)
    assert mode(Path(atomic.backup_root(target))) == 0o700
