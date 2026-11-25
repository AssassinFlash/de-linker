"""Two worker processes share progress, capacity and short-lived checked replies."""

import multiprocessing
import os
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from linker_genie.jobs import RETENTION_SECONDS, Jobs
from linker_genie.work import Slots, WorkError

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


def test_waiting_job_uses_only_actual_execution_for_its_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [1000.0]
    monkeypatch.setattr("linker_genie.jobs.time.time", lambda: clock[0])
    jobs = Jobs(Slots(tmp_path / "private/work.sqlite"))
    job = str(uuid.uuid4())
    jobs.begin(job, "card-en", SUBJECT, "waiting")
    clock[0] += 110
    waiting = jobs.read(job, SUBJECT)
    assert waiting and waiting["queued_seconds"] == 110
    assert jobs.claim(job, SUBJECT, "understanding") == "claimed"
    clock[0] += 3
    running = jobs.read(job, SUBJECT)
    assert (
        running
        and running["stage"] == "understanding"
        and running["queued_seconds"] == 110
    )
    jobs.finish(job, "done")
    clock[0] += 2
    complete = jobs.read(job, SUBJECT)
    assert (
        complete
        and complete["status"] == "completed"
        and complete["queued_seconds"] == 110
    )


def test_deleting_a_queued_conversation_prevents_execution(tmp_path: Path) -> None:
    jobs = Jobs(Slots(tmp_path / "private/work.sqlite"))
    job = str(uuid.uuid4())
    jobs.begin(job, "card-en", SUBJECT, "waiting")
    jobs.forget("card-en")
    assert jobs.claim(job, SUBJECT, "reading_attachments") == "gone"
    assert jobs.read(job, SUBJECT) is None


def test_old_jobs_can_finish_after_queue_schema_upgrade(tmp_path: Path) -> None:
    slots = Slots(tmp_path / "private/work.sqlite")
    job = slots.acquire(SUBJECT)
    assert job
    with slots.transaction() as db:
        db.execute("""CREATE TABLE turn_jobs (job_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
              subject TEXT NOT NULL,pid INTEGER NOT NULL,slot_id TEXT NOT NULL,status TEXT NOT NULL,
              stage TEXT NOT NULL,result_stream TEXT,error_status INTEGER,error_code TEXT,error_detail TEXT,
              created_at REAL NOT NULL,updated_at REAL NOT NULL,expires_at REAL)""")
        db.execute(
            "INSERT INTO turn_jobs (job_id,conversation_id,subject,pid,slot_id,status,stage,created_at,updated_at) VALUES(?,?,?,?,?,'running','understanding',?,?)",
            (job, "old", SUBJECT, os.getpid(), job, time.time(), time.time()),
        )
    jobs = Jobs(slots)
    assert jobs.finish(job, "old stream")
    assert jobs.read(job, SUBJECT) == {
        "job_id": job,
        "status": "completed",
        "stream": "old stream",
    }


def test_private_reads_use_the_current_owner_after_a_long_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The queue and the poll run in different API workers.
    now = [1000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    slots = Slots(tmp_path / "private/work.sqlite")
    worker, poll = Jobs(slots), Jobs(slots)
    worker.begin("job", "conversation", SUBJECT, "waiting")
    original = "44|1120|start-signature"
    now[0] += 110
    assert poll.read("job", "other-subject", "99|1230|other") is None
    assert worker.user_context("job", SUBJECT, original) == original
    renewed = "44|1230|current-signature"
    state = poll.read("job", SUBJECT, renewed)
    assert state and renewed not in repr(state)
    assert worker.claim("job", SUBJECT, "understanding") == "claimed"
    now[0] += 11
    assert worker.user_context("job", SUBJECT, original) == renewed
    # An older in-flight poll cannot replace the newer credential.
    poll.read("job", SUBJECT, original)
    assert worker.user_context("job", SUBJECT, original) == renewed
    now[0] += 110
    with pytest.raises(WorkError) as expired:
        worker.user_context("job", SUBJECT, original)
    assert expired.value.status == 401
    worker.finish("job", "answer")
    with slots.transaction() as db:
        assert db.execute("SELECT owner_context FROM turn_jobs").fetchone() == (None,)
