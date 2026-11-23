"""Two worker processes share progress, capacity and short-lived checked replies."""

import multiprocessing
import os
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from linker_genie.jobs import RETENTION_SECONDS, Jobs
from linker_genie.work import Slots

SUBJECT = "a" * 64


def run_job(path: Path, ready: Any, finish: Any, crash: bool) -> None:
    slots = Slots(path)
    job = slots.acquire(SUBJECT)
    assert job is not None
    jobs = Jobs(slots)
    jobs.begin(job, "conversation", SUBJECT, "understanding")
    jobs.stage(job, "searching_documents")
    ready.send(job)
    ready.close()
    assert finish.wait(15)
    if crash:
        os._exit(3)
    jobs.finish(job, "event: done\ndata: {}\n\n")


@pytest.mark.parametrize("crash", [False, True])
def test_other_worker_can_read_and_capacity_tracks_worker_lifetime(
    tmp_path: Path, crash: bool
) -> None:
    path = tmp_path / "work.sqlite"
    ctx = multiprocessing.get_context("spawn")
    reader, writer = ctx.Pipe(duplex=False)
    finish = ctx.Event()
    worker = ctx.Process(target=run_job, args=(path, writer, finish, crash))
    worker.start()
    writer.close()
    try:
        assert reader.poll(15)
        job = reader.recv()
        assert uuid.UUID(job).version == 4
        slots = Slots(path)
        jobs = Jobs(slots)
        progress = jobs.read(job, SUBJECT)
        assert (
            progress
            and progress["stage"] == "searching_documents"
            and "stream" not in progress
        )
        assert jobs.read(job, "b" * 64) is None
        assert slots.acquire(SUBJECT) is None
        second = slots.acquire("b" * 64)
        assert second and slots.acquire("c" * 64) is None
        finish.set()
        worker.join(15)
        assert worker.exitcode == (3 if crash else 0)
        terminal = jobs.read(job, SUBJECT)
        assert terminal
        if crash:
            assert (
                terminal["status"] == "failed"
                and terminal["http_status"] == 503
                and "stream" not in terminal
            )
        else:
            assert terminal["status"] == "completed" and terminal["stream"].startswith(
                "event: done"
            )
        assert slots.acquire(SUBJECT)
        assert path.stat().st_mode & 0o077 == 0
    finally:
        finish.set()
        if worker.is_alive():
            worker.terminate()
        worker.join(10)
        reader.close()


def test_checked_file_readings_expire_and_deleted_threads_forget_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slots = Slots(tmp_path / "jobs.sqlite")
    jobs = Jobs(slots)
    job = slots.acquire(SUBJECT)
    assert job
    jobs.begin(job, "conversation", SUBJECT, "reading_attachments")
    jobs.finish(job, "private-nameplate-reading")
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + RETENTION_SECONDS + 1)
    jobs.prune()
    assert jobs.read(job, SUBJECT) is None
    job = slots.acquire(SUBJECT)
    assert job
    jobs.begin(job, "conversation", SUBJECT, "understanding")
    jobs.finish(job, "private-nameplate-reading")
    jobs.forget("conversation")
    assert jobs.read(job, SUBJECT) is None
    assert b"private-nameplate-reading" not in slots.path.read_bytes()
