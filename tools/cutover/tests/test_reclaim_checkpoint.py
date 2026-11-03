"""A terminated host batch releases its leftover local checkpoint; pending keeps it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_steps import FilesystemTarget

from linker_cutover import atomic, deployment, steps
from linker_cutover.target import CutoverError


def _batch(tmp_path: Path, deploy_id: str, state: str | None) -> FilesystemTarget:
    target = FilesystemTarget(tmp_path / "site")
    if state is not None:
        directory = Path(atomic.backup_root(target)) / deploy_id
        directory.mkdir(parents=True)
        (directory / "manifest.json").write_text(
            json.dumps({"deploy_id": deploy_id, "state": state, "backups": []})
        )
    return target


def _checkpoint(staging: Path, deploy_id: str) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "linker-commerce").mkdir(exist_ok=True)
    stamp = staging / ".stage"
    stamp.mkdir(exist_ok=True)
    (stamp / "linker-commerce.sha256").write_text("fixture")
    deployment.save(
        staging,
        deployment.Checkpoint(
            deploy_id,
            "fixture-source",
            ["fixture", None, "http://127.0.0.1", None],
            {},
            prepared={"wp-content/plugins/linker-commerce": "x"},
        ),
    )


@pytest.mark.parametrize("state", ["archived", "rolled_back"])
def test_terminated_batch_releases_leftover_checkpoint(
    tmp_path: Path, state: str
) -> None:
    deploy_id = "20261103T180122673374Z-fixture0"
    target = _batch(tmp_path, deploy_id, state)
    staging = tmp_path / "staging"
    _checkpoint(staging, deploy_id)

    steps._reclaim_finished_checkpoint(target, staging)

    assert not deployment.path(staging).exists()
    assert not (staging / "linker-commerce").exists()
    assert not (staging / ".stage" / "linker-commerce.sha256").exists()


def test_pending_batch_keeps_the_refusal(tmp_path: Path) -> None:
    deploy_id = "20261103T180122673374Z-fixture1"
    target = _batch(tmp_path, deploy_id, "pending")
    staging = tmp_path / "staging"
    _checkpoint(staging, deploy_id)

    with pytest.raises(CutoverError, match="unfinished deployment"):
        steps._reclaim_finished_checkpoint(target, staging)

    assert deployment.path(staging).exists()


def test_missing_manifest_keeps_the_refusal(tmp_path: Path) -> None:
    deploy_id = "20261103T180122673374Z-fixture2"
    target = _batch(tmp_path, deploy_id, None)
    staging = tmp_path / "staging"
    _checkpoint(staging, deploy_id)

    with pytest.raises(CutoverError, match="unfinished deployment"):
        steps._reclaim_finished_checkpoint(target, staging)

    assert deployment.path(staging).exists()
