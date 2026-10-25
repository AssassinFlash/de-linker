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


def test_guard_refusal_cleans_only_its_mixed_preparation_and_allows_retry(
    tmp_path: Path,
) -> None:
    """A refused directory/MU/theme batch leaves the old recovery record usable."""
    target = Target(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    plugin = "wp-content/plugins/example"
    mu = "wp-content/mu-plugins/guard.php"
    style = "wp-content/themes/child/style.css"
    added = "wp-content/plugins/added"
    source = tmp_path / "source"
    private_file(source / "assets" / "header.js", "previous browser code")
    mu_source = tmp_path / "guard.php"
    private_file(mu_source, "previous MU code")
    previous = atomic.publish(
        target,
        [atomic.Artifact(source, plugin), atomic.Artifact(mu_source, mu)],
        deploy_id="20261024T000000Z-prior",
    )
    atomic.archive(target, previous)
    root = Path(atomic.backup_root(target))
    prior_manifest = (Path(previous.backup_directory) / "manifest.json").read_bytes()
    prior_pointer = (root / "latest").read_bytes()
    old_directory = Path(target.path_of(plugin))
    old_mu = Path(target.path_of(mu))
    directory_inode = old_directory.stat().st_ino
    mu_inode = old_mu.stat().st_ino
    mu_mode = mode(old_mu)
    private_file(source / "assets" / "header.js", "new browser code")
    private_file(mu_source, "new MU code")
    style_source = tmp_path / "style.css"
    private_file(style_source, "new CSS")
    artifacts = [
        atomic.Artifact(source, plugin),
        atomic.Artifact(mu_source, mu),
        atomic.Artifact(style_source, style),
        atomic.Artifact(source, added),
    ]
    refused_id = "20261024T000001Z-refused"

    def damage() -> None:
        incoming = old_directory.with_name(".example.next")
        (incoming / "assets" / "header.js").chmod(0o600)

    with pytest.raises(CutoverError, match="public.asset"):
        atomic.publish(target, artifacts, deploy_id=refused_id, on_switch=damage)

    assert old_directory.stat().st_ino == directory_inode
    assert (
        old_directory / "assets" / "header.js"
    ).read_text() == "previous browser code"
    assert old_mu.stat().st_ino == mu_inode
    assert old_mu.read_text() == "previous MU code"
    assert mode(old_mu) == mu_mode
    assert not Path(target.path_of(style)).exists()
    assert not Path(target.path_of(added)).exists()
    assert (root / "latest").read_bytes() == prior_pointer
    assert (
        Path(previous.backup_directory) / "manifest.json"
    ).read_bytes() == prior_manifest
    assert not (root / refused_id).exists()
    assert not list(Path(target.root).rglob("*.prev"))
    assert not list(Path(target.root).rglob("*.prev-absent"))
    assert not list(Path(target.root).rglob("*.failed"))

    # A normal retry replaces the damaged .next candidates, without manual cleanup.
    receipt = atomic.publish(target, artifacts, deploy_id=refused_id)
    assert (old_directory / "assets" / "header.js").read_text() == "new browser code"
    assert old_mu.read_text() == "new MU code"
    assert mode(Path(target.path_of(style))) == 0o644
    assert mode(Path(target.path_of(added)) / "assets" / "header.js") == 0o644
    atomic.archive(target, receipt)
    atomic.rollback(target, [artifact.relative for artifact in artifacts])
    assert old_directory.stat().st_ino == directory_inode
    assert (
        old_directory / "assets" / "header.js"
    ).read_text() == "previous browser code"
    assert old_mu.read_text() == "previous MU code"
    assert mode(old_mu) == mu_mode
    assert not Path(target.path_of(style)).exists()
    assert not Path(target.path_of(added)).exists()


@pytest.mark.parametrize(
    "replaced", ["copy", "marker", "batch", "unreadable-batch", "newline-batch"]
)
def test_guard_refusal_retains_foreign_preparation_for_inspection(
    tmp_path: Path, replaced: str
) -> None:
    """Refusal cannot delete a replaced backup, marker or batch directory."""
    target = Target(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    relative = "wp-content/plugins/example"
    live = Path(target.path_of(relative))
    private_file(live / "assets" / "header.js", "old browser code")
    mu = Path(target.path_of("wp-content/mu-plugins/guard.php"))
    private_file(mu, "old MU code")
    source = tmp_path / "source"
    private_file(source / "assets" / "header.js", "new browser code")
    mu_source = tmp_path / "guard.php"
    private_file(mu_source, "new MU code")
    style_source = tmp_path / "style.css"
    private_file(style_source, "new CSS")
    style = Path(target.path_of("wp-content/themes/child/style.css"))
    deploy_id = "20261024T000001Z-replaced"
    batch = Path(atomic.backup_root(target)) / deploy_id
    copy = mu.with_name(".guard.php.prev")
    marker = style.with_name(".style.css.prev-absent")
    foreign = {"copy": copy, "marker": marker}.get(replaced, batch)
    live_inode = live.stat().st_ino

    def damage() -> None:
        (live.with_name(".example.next") / "assets" / "header.js").chmod(0o600)
        if replaced in ("unreadable-batch", "newline-batch"):
            name = "inspection-evidence" if replaced == "unreadable-batch" else "\n"
            private_file(batch / name, "retain this private evidence")
            if replaced == "unreadable-batch":
                batch.chmod(0o000)
            return
        foreign.rename(tmp_path / "our-original-preparation")
        if replaced == "batch":
            foreign.mkdir(mode=0o700)
        else:
            # Even a replacement bearing this deploy id is not our saved inode.
            private_file(foreign, deploy_id)

    with pytest.raises(CutoverError, match="public.asset"):
        atomic.publish(
            target,
            [
                atomic.Artifact(source, relative),
                atomic.Artifact(mu_source, "wp-content/mu-plugins/guard.php"),
                atomic.Artifact(style_source, "wp-content/themes/child/style.css"),
            ],
            deploy_id=deploy_id,
            on_switch=damage,
        )

    if replaced == "unreadable-batch":
        batch.chmod(0o700)
        assert (
            batch / "inspection-evidence"
        ).read_text() == "retain this private evidence"
    elif replaced == "newline-batch":
        assert (batch / "\n").read_text() == "retain this private evidence"
    assert foreign.exists()
    assert copy.exists()
    assert marker.exists()
    assert batch.exists()
    assert live.stat().st_ino == live_inode
    assert (live / "assets" / "header.js").read_text() == "old browser code"
    assert mu.read_text() == "old MU code"
    assert not style.exists()
    assert not (batch.parent / "latest").exists()


def test_uncertain_switch_transport_retains_preparation(tmp_path: Path) -> None:
    """A missing final SSH result is never treated as an explicit guard refusal."""

    class LostTransport(Target):
        def shell(self, script: str) -> str:
            if "TIMEFORMAT=" in script:
                raise CutoverError("fixture SSH result unknown")
            return super().shell(script)

    target = LostTransport(
        "fixture", str(tmp_path / "site"), "http://127.0.0.1", (), None, None
    )
    source = tmp_path / "guard.php"
    private_file(source, "new MU code")
    relative = "wp-content/mu-plugins/guard.php"
    live = Path(target.path_of(relative))
    private_file(live, "old MU code")
    deploy_id = "20261024T000001Z-uncertain"

    with pytest.raises(CutoverError, match="SSH result unknown"):
        atomic.publish(target, [atomic.Artifact(source, relative)], deploy_id=deploy_id)

    assert live.read_text() == "old MU code"
    assert live.with_name(".guard.php.prev").read_text() == "old MU code"
    assert (Path(atomic.backup_root(target)) / deploy_id).is_dir()


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
