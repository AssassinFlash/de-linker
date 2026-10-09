import os
import socket
import sys
from pathlib import Path

import pytest

from linker_local.processes import Background, ProcessError

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]


def background(tmp_path: Path) -> Background:
    return Background(tmp_path / "run" / "p.pid", tmp_path / "logs" / "p.log")


def free_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port: int = probe.getsockname()[1]
        return port


def test_starts_a_detached_process_and_stops_it(tmp_path: Path) -> None:
    process = background(tmp_path)

    pid = process.start(SLEEPER, dict(os.environ))

    assert process.pid() == pid
    assert os.getsid(pid) == pid  # its own session, so stop() reaches its children
    assert process.stop() is True
    assert process.pid() is None
    assert not process.pid_file.exists()
    assert process.stop() is False


def test_a_pid_now_used_by_another_program_is_left_alone(tmp_path: Path) -> None:
    process = background(tmp_path)
    process.pid_file.parent.mkdir(parents=True)
    # This test's own pid, recorded with a start time it does not have.
    process.pid_file.write_text(
        f"{os.getpid()}\nThu Jan  1 00:00:00 1970\n/opt/homebrew/opt/php@8.3/bin/php -S x\n"
    )

    assert process.pid() is None
    assert process.stop() is False
    assert not process.pid_file.exists()


def test_waits_until_the_port_answers(tmp_path: Path) -> None:
    process = background(tmp_path)
    port = free_port()
    process.start(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        dict(os.environ),
    )
    try:
        process.wait_for_port(port, timeout=10)
    finally:
        process.stop()


def test_a_process_that_exits_during_start_is_reported_with_its_log(
    tmp_path: Path,
) -> None:
    process = background(tmp_path)
    process.start(
        [sys.executable, "-c", "print('cannot bind'); raise SystemExit(1)"],
        dict(os.environ),
    )

    with pytest.raises(ProcessError, match="cannot bind"):
        process.wait_for_port(free_port(), timeout=10)
