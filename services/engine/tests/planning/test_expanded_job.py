"""Expanded jobs retain lease control while ordinary work takes priority."""

from __future__ import annotations

import io
import os
import subprocess
from pathlib import Path
from threading import Event
from typing import Any, cast

import pytest

from linker_engine.planning import expanded_job
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.errors import (
    EvidenceMissing,
    ExpandedResourceUnavailable,
    LeaseLost,
    VersionUnavailable,
)
from linker_engine.planning.expanded_job import (
    DelegatedGroup,
    ExpandedExecutor,
    cleanup_owned_temps,
)
from linker_engine.planning.records import Lease
from linker_engine.planning.worker import Control, Published
from linker_engine.planning.worker_policy import ExpandedJobPolicy


@pytest.mark.parametrize(
    "outcome", ["success", "cancel", "timeout", "version-error", "evidence"]
)
def test_expanded_executor_yields_and_cleans_up_on_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    normal, stop, control = Event(), Event(), Control()
    normal.set()
    events: list[bool] = []

    class Group:
        def __init__(self) -> None:
            self.group = tmp_path / "group"
            self.child_fd = -1
            self.closed = False

        def create(self, _policy: ExpandedJobPolicy) -> None:
            self.group.mkdir()

        def freeze(self, paused: bool) -> None:
            events.append(paused)

        def close(self) -> None:
            self.closed = True
            if self.child_fd >= 0:
                os.close(self.child_fd)

    group = Group()

    class Process:
        pid = 123
        returncode: int | None = None

        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            group.child_fd = os.dup(kwargs["pass_fds"][0])
            self.stdin = io.BytesIO()
            response: Object = (
                {
                    "error": "version_unavailable",
                    "location": {
                        "module": "fixture.module",
                        "function": "read",
                        "line": 42,
                    },
                }
                if outcome == "version-error"
                else {
                    "error": "evidence_missing",
                    "details": {"constraint_id": "pv_reference_missing"},
                }
                if outcome == "evidence"
                else {"published": "c" * 64}
            )
            self.stdout = io.BytesIO(encode(response))
            self.polls = 0

        def poll(self) -> int | None:
            self.polls += 1
            if outcome == "cancel" and self.polls == 1:
                control.revoke()
            if self.polls == 2:
                normal.clear()
            if outcome in ("success", "version-error", "evidence") and self.polls >= 3:
                self.returncode = 0
            return self.returncode

        def wait(self, timeout: float) -> int:
            assert timeout > 0
            self.returncode = 0
            return 0

        def kill(self) -> None:
            self.returncode = -9

    monkeypatch.setattr(expanded_job, "available_memory", lambda: 3 * 1024**3)
    monkeypatch.setattr(expanded_job, "healthy", lambda _ports: True)
    monkeypatch.setattr(subprocess, "Popen", Process)
    policy = ExpandedJobPolicy(
        cpu_quota_percent=20,
        memory_max_bytes=1200 * 1024**2,
        minimum_available_bytes=1536 * 1024**2,
        timeout_seconds=0.01 if outcome == "timeout" else 10,
        health_ports=(18901, 18911),
    )
    lease = Lease("job", "run", "evaluate", 1, "worker", "a" * 32, 100, {})
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    executor = ExpandedExecutor(
        cast(DelegatedGroup, group), policy, normal, stop, blobs
    )
    if outcome == "cancel":
        with pytest.raises(LeaseLost):
            executor(lease, control)
    elif outcome == "timeout":
        with pytest.raises(ExpandedResourceUnavailable, match="runtime"):
            executor(lease, control)
    elif outcome == "version-error":
        with pytest.raises(VersionUnavailable):
            executor(lease, control)
        assert "fixture.module.read:42" in caplog.text
    elif outcome == "evidence":
        with pytest.raises(EvidenceMissing) as captured:
            executor(lease, control)
        assert captured.value.public_details == {
            "constraint_id": "pv_reference_missing"
        }
    else:
        assert executor(lease, control) == Published("c" * 64)
        assert events == [True, False]
    assert group.closed


def test_cleanup_removes_only_the_finished_lease_temporary_writes(
    tmp_path: Path,
) -> None:
    owner, other = "a" * 32, "b" * 32
    for prefix in ("00", "fe"):
        directory = tmp_path / prefix
        directory.mkdir()
        (directory / (".incoming-" + owner)).write_bytes(b"partial owner")
        (directory / (".incoming-" + other)).write_bytes(b"another writer")
    cleanup_owned_temps(tmp_path, owner)
    for prefix in ("00", "fe"):
        directory = tmp_path / prefix
        assert not (directory / (".incoming-" + owner)).exists()
        assert (directory / (".incoming-" + other)).read_bytes() == b"another writer"
