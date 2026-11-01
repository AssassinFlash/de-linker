"""Large-witness projection preserves legacy bytes and validates each row."""

from pathlib import Path

import pytest

from linker_engine.planning.canonical import encode
from linker_engine.planning.errors import LeaseLost, VersionUnavailable
from linker_engine.planning.frozen_documents import FrozenDocuments
from linker_engine.planning.geometric_pv_witness import project_witness
from linker_engine.planning.storage import Blobs


def test_projection_preserves_summary_selected_fields_and_blob_integrity(
    tmp_path: Path,
) -> None:
    blobs = Blobs(tmp_path / "blobs")
    witness = {
        "kind": "fixture",
        "inputs": {"note": 'nested "modules": [ remains data'},
        "modules": [
            {"module_id": "α", "values": [1.0, 2.0], "other": {"x": [3]}},
            {"module_id": "β", "values": [4.0, 5.0], "other": "text"},
        ],
        "schema_version": 1,
    }
    raw = encode(witness)
    sha = blobs.put(raw)
    assert project_witness(blobs, sha) == {**witness, "modules": []}
    assert project_witness(blobs, sha, module_fields=("module_id", "values")) == {
        **witness,
        "modules": [
            {"module_id": "α", "values": [1.0, 2.0]},
            {"module_id": "β", "values": [4.0, 5.0]},
        ],
    }
    assert blobs.object(sha) == witness
    reader = FrozenDocuments(blobs)
    assert reader.geometric_witness(blobs, sha)["modules"] == []
    assert reader.object(sha) == witness  # Full and projected caches never alias.
    assert reader.geometric_witness(blobs, sha)["modules"] == []

    def cancelled() -> None:
        raise LeaseLost("fixture cancellation")

    with pytest.raises(LeaseLost):
        project_witness(blobs, sha, checkpoint=cancelled)
    assert blobs.read(sha) == raw
    with pytest.raises(VersionUnavailable):
        project_witness(blobs, sha, module_fields=("missing",))
    blobs._path(sha).write_bytes(raw + b" ")
    with pytest.raises(VersionUnavailable, match="hash mismatch"):
        project_witness(blobs, sha)


def test_projection_rejects_malformed_module_rows(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    for raw in (
        b'{"modules":[{"x":1},],"schema_version":1}',
        b'{"modules":[{"x":NaN}],"schema_version":1}',
        b'{"modules":[1],"schema_version":1}',
        b'{"modules":[{"x":1}],"schema_version":1',
    ):
        with pytest.raises(VersionUnavailable):
            project_witness(blobs, blobs.put(raw))


def test_cancelled_projection_releases_reader_without_publishing(
    workspace, owner, context
) -> None:
    from linker_engine.planning.jobs import Jobs
    from linker_engine.planning.worker import Worker

    raw = encode({"modules": [{"module_id": "one", "values": [1.0]}]})
    sha = workspace.blobs.put(raw)
    project = workspace.create(owner, "Synthetic cancellation", {}, key="create")
    run = workspace.evaluate(owner, project.id, 1, context, key="run", max_attempts=1)

    def execute(_lease, control):
        def cancel():
            workspace.cancel(owner, run.id)
            control.revoke()
            control.checkpoint()

        project_witness(workspace.blobs, sha, checkpoint=cancel)
        return {"unexpected": True}

    worker = Worker(
        Jobs(workspace),
        "projection-cancel",
        {"evaluate": execute},
        lease_seconds=30,
        heartbeat_seconds=5,
        retry_seconds=1,
    )
    assert worker.run_once()
    cancelled = workspace.run(owner, run.id)
    assert cancelled.state == "cancelled" and cancelled.result is None
    assert workspace.blobs.read(sha) == raw
    assert not worker.run_once()
