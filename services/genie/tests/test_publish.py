"""Index releases: publish into a local root (the VPS layout), roll back, prune."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import index_release
import publish_index


def build(root: Path, version: str) -> Path:
    """A build directory as index.build writes it, with a minimal index file."""
    directory = root / "builds" / version
    directory.mkdir(parents=True)
    db = sqlite3.connect(directory / "index.sqlite")
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("INSERT INTO meta VALUES ('version', ?)", (version,))
    db.commit()
    db.close()
    digest = hashlib.sha256((directory / "index.sqlite").read_bytes()).hexdigest()
    manifest = {"version": version, "file": {"name": "index.sqlite", "sha256": digest}}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


def test_publish_puts_the_release_in_place_and_makes_it_current(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "linker-genie" / "index"

    report = publish_index.publish(
        build(tmp_path, "20261009T100000Z"), str(root), host=None
    )

    assert report["current"] == "20261009T100000Z"
    assert report["index_version"] == "20261009T100000Z"
    assert report["sha256_ok"] is True
    assert (root / "current").resolve() == (root / "20261009T100000Z").resolve()
    assert not list(root.glob(".incoming-*"))


def test_rollback_returns_to_the_previous_release(tmp_path: Path) -> None:
    root = tmp_path / "index"
    publish_index.publish(build(tmp_path, "20261009T100000Z"), str(root), host=None)
    publish_index.publish(build(tmp_path, "20261009T110000Z"), str(root), host=None)

    report = publish_index.release(None, "rollback", str(root))

    assert report["current"] == "20261009T100000Z"
    assert report["index_version"] == "20261009T100000Z"
    assert report["releases"] == ["20261009T100000Z", "20261009T110000Z"]


def test_rollback_without_an_older_release_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "index"
    publish_index.publish(build(tmp_path, "20261009T100000Z"), str(root), host=None)

    with pytest.raises(SystemExit):
        index_release.rollback(root)


def test_a_release_whose_bytes_differ_from_the_manifest_is_not_activated(
    tmp_path: Path,
) -> None:
    root = tmp_path / "index"
    directory = build(tmp_path, "20261009T100000Z")
    index_release.prepare(root, "20261009T100000Z")
    (root / ".incoming-20261009T100000Z" / "index.sqlite").write_bytes(b"truncated")

    with pytest.raises(SystemExit, match="sha256"):
        index_release.activate(
            root,
            "20261009T100000Z",
            json.loads((directory / "manifest.json").read_text())["file"]["sha256"],
        )
    assert not (root / "current").exists()


def test_publish_checks_the_build_against_its_own_manifest(tmp_path: Path) -> None:
    directory = build(tmp_path, "20261009T100000Z")
    (directory / "index.sqlite").write_bytes(b"changed after the build")

    with pytest.raises(SystemExit, match="manifest"):
        publish_index.publish(directory, str(tmp_path / "index"), host=None)


def test_old_releases_beyond_the_kept_number_are_deleted(tmp_path: Path) -> None:
    root = tmp_path / "index"
    versions = [f"20261009T1{hour}0000Z" for hour in range(5)]
    for version in versions:
        publish_index.publish(build(tmp_path, version), str(root), host=None)

    assert index_release.releases(root) == versions[-index_release.KEEP :]
    assert index_release.current(root) == versions[-1]
