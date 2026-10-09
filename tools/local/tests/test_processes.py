import os
import socket
import sys
from pathlib import Path

import pytest

from linker_local.processes import Background, ProcessError, port_is_free

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


def test_a_terminal_in_another_locale_and_time_zone_finds_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = background(tmp_path)
    # `up` ran in one terminal ...
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.setenv("TZ", "America/New_York")
    pid = process.start(SLEEPER, dict(os.environ))
    try:
        # ... and `status` runs in another (this Mac's own locale and time zone).
        monkeypatch.setenv("LC_ALL", "zh_CN.UTF-8")
        monkeypatch.setenv("TZ", "Asia/Shanghai")

        assert process.pid() == pid
    finally:
        assert process.stop() is True


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


def test_a_pid_now_used_by_another_users_process_is_left_alone(tmp_path: Path) -> None:
    process = background(tmp_path)
    process.pid_file.parent.mkdir(parents=True)
    # pid 1 is launchd (root): it exists, and this user may not signal it.
    process.pid_file.write_text(
        "1\nThu Jan  1 00:00:00 1970\n/opt/homebrew/opt/php@8.3/bin/php -S x\n"
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

        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass
    finally:
        process.stop()


def test_a_process_that_exits_during_start_is_reported_with_its_own_output(
    tmp_path: Path,
) -> None:
    process = background(tmp_path)
    process.log_file.parent.mkdir(parents=True)
    process.log_file.write_text("an earlier run's output\n")
    process.start(
        [sys.executable, "-c", "print('cannot bind'); raise SystemExit(1)"],
        dict(os.environ),
    )

    with pytest.raises(ProcessError, match="cannot bind") as failure:
        process.wait_for_port(free_port(), timeout=10)
    assert "earlier run" not in str(failure.value)


def test_a_listening_port_is_not_free() -> None:
    with socket.create_server(("127.0.0.1", 0)) as server:
        assert not port_is_free(server.getsockname()[1])


def test_a_port_whose_server_stopped_is_free_while_its_connections_are_in_time_wait() -> (
    None
):
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port)) as client:
            accepted, _ = server.accept()
            # The server side closes first, so its end of the connection waits in TIME_WAIT.
            accepted.close()
            client.recv(1)
    with socket.socket() as plain:
        with pytest.raises(OSError):
            plain.bind(
                ("127.0.0.1", port)
            )  # without SO_REUSEADDR the port still looks taken

    assert port_is_free(port)
