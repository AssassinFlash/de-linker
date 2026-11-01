import os
import signal
import socket
import sys
import time
from pathlib import Path

import pytest

from linker_local import processes
from linker_local.processes import Background, ProcessError, port_is_free

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]


def process_environment() -> dict[str, str]:
    """Fixtures need no application credentials, including in failure reports."""
    return {key: os.environ[key] for key in ("PATH", "LC_ALL", "TZ") if key in os.environ}


def background(tmp_path: Path) -> Background:
    return Background(tmp_path / "run" / "p.pid", tmp_path / "logs" / "p.log")


def free_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port: int = probe.getsockname()[1]
        return port


def test_starts_a_detached_process_and_stops_it(tmp_path: Path) -> None:
    process = background(tmp_path)

    pid = process.start(SLEEPER, process_environment())

    assert process.pid() == pid
    assert os.getsid(pid) == pid  # its own session, so stop() reaches its children
    assert process.stop() is True
    assert process.pid() is None
    assert not process.pid_file.exists()
    assert process.stop() is False


def test_child_cannot_receive_research_credentials(tmp_path: Path) -> None:
    process = background(tmp_path)
    env = {
        **process_environment(),
        "APIFY_TOKEN_ALT": "fake-research-token",
        "APIFY_OTHER": "fake-research-setting",
        "apify_Token_alias": "fake-case-alias",
        "LINKER_TEST_SENTINEL": "ordinary-setting-preserved",
    }
    before = env.copy()
    process.start(
        [
            sys.executable,
            "-c",
            "import os,time; "
            "assert not any(key.upper().startswith('APIFY_') for key in os.environ); "
            "print(os.environ['LINKER_TEST_SENTINEL'],flush=True); time.sleep(60)",
        ],
        env,
    )
    try:
        deadline = time.monotonic() + 5
        while not process.output() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert process.output() == "ordinary-setting-preserved"
        assert env == before
    finally:
        process.stop()


def test_a_terminal_in_another_locale_and_time_zone_finds_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = background(tmp_path)
    # `up` ran in one terminal ...
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    monkeypatch.setenv("TZ", "America/New_York")
    pid = process.start(SLEEPER, process_environment())
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
        process_environment(),
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
        process_environment(),
    )

    with pytest.raises(ProcessError, match="cannot bind") as failure:
        process.wait_for_port(free_port(), timeout=10)
    assert "earlier run" not in str(failure.value)


def test_a_listening_port_is_not_free() -> None:
    with socket.create_server(("127.0.0.1", 0)) as server:
        assert not port_is_free(server.getsockname()[1])


def stubborn_child(port: int) -> str:
    """A real inherited-group child that keeps its socket after TERM."""
    return (
        "import signal,socket,time; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        f"s=socket.create_server(('127.0.0.1',{port})); "
        "time.sleep(60)"
    )


def parent_with_child(port: int, *, exit_early: bool = False) -> list[str]:
    code = f"""
import socket,subprocess,sys,time
subprocess.Popen([sys.executable,'-c',{stubborn_child(port)!r}])
deadline=time.monotonic()+5
while True:
    try:
        socket.create_connection(('127.0.0.1',{port}),timeout=0.05).close()
        break
    except OSError:
        if time.monotonic()>=deadline:
            raise
        time.sleep(0.01)
print('startup diagnostic',flush=True)
{"raise SystemExit(1)" if exit_early else "time.sleep(60)"}
"""
    return [sys.executable, "-c", code]


def kill_fixture_group(pid: int) -> None:
    """The test owns this newly spawned session even when its assertion is red."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        if processes._group_running(pid):
            raise
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass


def test_stop_waits_for_children_when_the_leader_exits_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(processes, "STOP_GRACE", 0.2)
    process = background(tmp_path)
    port = free_port()
    pid = process.start(parent_with_child(port), process_environment())
    try:
        process.wait_for_port(port, timeout=5)

        assert process.stop() is True

        assert port_is_free(port), "the TERM-ignoring child still owns its socket"
        assert not process.pid_file.exists()
    finally:
        kill_fixture_group(pid)


@pytest.mark.parametrize("exit_early", [False, True])
def test_restart_failure_cleans_its_group_and_preserves_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_early: bool
) -> None:
    monkeypatch.setattr(processes, "STOP_GRACE", 0.2)
    process = background(tmp_path)
    child_port, expected_port = free_port(), free_port()
    while child_port == expected_port:
        expected_port = free_port()
    pid = 0
    start = process.start

    def capture_start(argv: list[str], env: dict[str, str]) -> int:
        nonlocal pid
        pid = start(argv, env)
        return pid

    monkeypatch.setattr(process, "start", capture_start)
    try:
        with pytest.raises(ProcessError) as failure:
            process.restart(
                parent_with_child(child_port, exit_early=exit_early),
                process_environment(),
                expected_port,
                timeout=0.5,
            )

        assert "startup diagnostic" in str(failure.value)
        assert port_is_free(child_port), "failed startup leaked its child process"
        assert not process.pid_file.exists()
        assert process.output() == "startup diagnostic"
    finally:
        if pid:
            kill_fixture_group(pid)


def test_pid_record_write_failure_cleans_the_spawned_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(processes, "STOP_GRACE", 0.2)
    process = background(tmp_path)
    port = free_port()
    pid = 0
    write_text = Path.write_text

    def reject_record(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        nonlocal pid
        if path != process.pid_file:
            return write_text(path, data, encoding, errors, newline)
        pid = int(data.splitlines()[0])
        deadline = time.monotonic() + 5
        while port_is_free(port) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not port_is_free(port), "fixture child never opened its socket"
        raise OSError("injected pid record write failure")

    monkeypatch.setattr(Path, "write_text", reject_record)
    try:
        with pytest.raises(OSError, match="injected pid record"):
            process.start(parent_with_child(port), process_environment())

        assert port_is_free(port), "unrecorded startup leaked its session"
        assert not process.pid_file.exists()
    finally:
        if pid:
            kill_fixture_group(pid)


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
