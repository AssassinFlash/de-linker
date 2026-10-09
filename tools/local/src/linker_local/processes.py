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

from linker_local.instance import HOST

# Seconds between SIGTERM and SIGKILL: the default grace period of `docker stop`
# for Linux containers (Docker CLI reference, read via Apify on 2026-10-09).
STOP_GRACE = 10
# Seconds between two looks at a starting or stopping process: the longest
# interval CPython's own Popen.wait() polls at (Lib/subprocess.py, 3.12).
POLL = 0.05


class ProcessError(RuntimeError):
    """A background process did not start or stop."""


class Background:
    """One background process: its pid file and its log."""

    def __init__(self, pid_file: Path, log_file: Path) -> None:
        self.pid_file = pid_file
        self.log_file = log_file
        self._log_start = 0

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

    def restart(
        self, argv: list[str], env: dict[str, str], port: int, timeout: float
    ) -> None:
        """Stop the process if it runs, start `argv` and wait until it listens on `port`."""
        self.stop()
        if not port_is_free(port):
            raise ProcessError(
                f"port {port} is in use by another program (lsof -nP -iTCP:{port} -sTCP:LISTEN)"
            )
        self.start(argv, env)
        self.wait_for_port(port, timeout)

    def start(self, argv: list[str], env: dict[str, str]) -> int:
        """Start `argv` (argv[0] an absolute path) detached; output goes to the log."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self._log_start = self.log_file.stat().st_size if self.log_file.exists() else 0
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
        """Return once HOST:port accepts connections; raise if the process exits first."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.pid() is None:
                raise ProcessError(
                    f"exited during start; {self.log_file}:\n{self.output()}"
                )
            try:
                with socket.create_connection((HOST, port), timeout=POLL):
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
        deadline = time.monotonic() + STOP_GRACE
        while _alive(pid) and time.monotonic() < deadline:
            time.sleep(POLL)
        if _alive(pid):
            # SIGKILL cannot be caught: the group ends as soon as the kernel delivers it.
            _signal_group(pid, signal.SIGKILL)
            while _alive(pid):
                time.sleep(POLL)
        self.pid_file.unlink(missing_ok=True)
        return True

    def output(self) -> str:
        """What the process has written to its log since the last start()."""
        try:
            with self.log_file.open("rb") as log:
                log.seek(self._log_start)
                return log.read().decode(errors="replace").rstrip()
        except FileNotFoundError:
            return ""


def port_is_free(port: int) -> bool:
    """Whether a server can listen on HOST:port.

    Nothing may answer there; a connection attempt also finds a server on
    *:port. The address must then bind as servers bind it, with SO_REUSEADDR
    (PHP's main/network.c and uvicorn's config.py both set it; read via Apify
    on 2026-10-09), which disregards the connections of a just-stopped
    server that are still in TIME_WAIT.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex((HOST, port)) == 0:
            return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


def _start_time(pid: int) -> str | None:
    """When the process started, to the second, or None if it is gone.

    ps prints the time in the caller's locale and time zone, so it runs with
    fixed ones: `up` and a later `status` from another terminal must agree.
    """
    result = subprocess.run(
        ["ps", "-o", "lstart=", "-p", str(pid)],
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _signal_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


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
