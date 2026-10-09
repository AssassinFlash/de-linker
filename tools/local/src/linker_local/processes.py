"""Background processes (the PHP server, the services), each tracked by a pid file.

A process is started in a session of its own, so stopping it signals its whole
process group: PHP's server forks workers and `uv run` starts a Python child.
The pid file also records when the process started; a pid whose process
started at another time belongs to someone else now and is never signalled.
(The command line cannot tell: macOS's framework Python re-executes itself
under another path.)
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from pathlib import Path

# Seconds between SIGTERM and SIGKILL: the default grace period of `docker stop`
# for Linux containers (Docker CLI reference, read via Apify on 2026-10-09).
STOP_GRACE = 10
# Seconds between two looks at a starting or stopping process.
POLL = 0.1
# Log lines shown when a process fails to start: PHP's and uvicorn's start-up
# errors, with a short traceback, fit in them.
TAIL_LINES = 20


class ProcessError(RuntimeError):
    """A background process did not start."""


class Background:
    """One background process: its pid file and its log."""

    def __init__(self, pid_file: Path, log_file: Path) -> None:
        self.pid_file = pid_file
        self.log_file = log_file

    def pid(self) -> int | None:
        """The pid of the recorded process if it is still running, else None."""
        try:
            lines = self.pid_file.read_text().splitlines()
            pid, started = int(lines[0]), lines[1]
        except (FileNotFoundError, IndexError, ValueError):
            return None
        if not _alive(pid) or _start_time(pid) != started:
            self.pid_file.unlink(missing_ok=True)
            return None
        return pid

    def start(self, argv: list[str], env: dict[str, str]) -> int:
        """Start `argv` (argv[0] an absolute path) detached; output goes to the log."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid = os.posix_spawn(
            argv[0],
            argv,
            env,
            file_actions=[
                (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
                (
                    os.POSIX_SPAWN_OPEN,
                    1,
                    str(self.log_file),
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o644,
                ),
                (os.POSIX_SPAWN_DUP2, 1, 2),
            ],
            setsid=True,
        )
        # Line 3, the command, is for people reading the file.
        self.pid_file.write_text(f"{pid}\n{_start_time(pid)}\n{' '.join(argv)}\n")
        return pid

    def wait_for_port(self, port: int, timeout: float) -> None:
        """Return once 127.0.0.1:port accepts connections; raise if the process exits first."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.pid() is None:
                raise ProcessError(
                    f"exited during start; see {self.log_file}:\n{self.tail()}"
                )
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=POLL):
                    return
            except OSError:
                time.sleep(POLL)
        raise ProcessError(
            f"no answer on port {port} after {timeout} s; see {self.log_file}"
        )

    def stop(self) -> bool:
        """Stop the process group; return whether something was running."""
        pid = self.pid()
        if pid is None:
            return False
        _signal_group(pid, signal.SIGTERM)
        if not _gone_within(pid, STOP_GRACE):
            _signal_group(pid, signal.SIGKILL)
            if not _gone_within(pid, STOP_GRACE):
                raise ProcessError(f"pid {pid} is still running after SIGKILL")
        self.pid_file.unlink(missing_ok=True)
        return True

    def tail(self) -> str:
        try:
            lines = self.log_file.read_text(errors="replace").splitlines()
        except FileNotFoundError:
            return ""
        return "\n".join(lines[-TAIL_LINES:])


def _start_time(pid: int) -> str | None:
    """When the process started, as ps prints it (to the second), or None if it is gone."""
    result = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _signal_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def _gone_within(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while _alive(pid):
        if time.monotonic() > deadline:
            return False
        time.sleep(POLL)
    return True


def _alive(pid: int) -> bool:
    """Whether the process exists; reaps it first when it is our own child."""
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
