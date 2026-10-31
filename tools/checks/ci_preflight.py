#!/usr/bin/env python3
"""Run the checks selected by the current branch diff before a push.

The path classifier and package recipes are shared with hosted CI.
Unknown, structural, control-plane or shared changes select the full suite.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import ci_scope

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Change:
    status: str
    path: str


@dataclass(frozen=True)
class Lane:
    name: str
    command: tuple[str, ...]
    timeout_seconds: int
    environment: dict[str, str] = field(default_factory=dict)


def _git(*arguments: str, check: bool = True) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=check,
        capture_output=True,
    ).stdout


def classify(changes: Sequence[Change], base: str = "origin/main") -> list[str]:
    """Use CI's package classifier against base and the current working tree."""
    try:
        return ci_scope.classify([(c.status, c.path) for c in changes], base, "")
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError, IndexError):
        return list(ci_scope.FULL_LANES)


def changes_from(base: str) -> list[Change]:
    """Include structural, committed, staged, unstaged and untracked work."""
    changes = [Change(*change) for change in ci_scope.diff_changes(base, "")]
    tracked = {change.path for change in changes}
    untracked = (
        _git("ls-files", "--others", "--exclude-standard", "-z")
        .decode(errors="surrogateescape")
        .split("\0")
    )
    changes.extend(
        Change("A", path) for path in untracked if path and path not in tracked
    )
    return changes


def python_lanes() -> list[Lane]:
    """Independent Python groups used by the full CI package lane."""
    return [
        Lane("python-genie", ("just", "py-test-group", "genie"), 900),
        Lane("python-engine", ("just", "py-test-group", "engine"), 900),
        Lane("python-tools", ("just", "py-test-group", "tools"), 900),
        Lane("python-harnesses", ("just", "py-test-group", "harnesses"), 600),
        Lane("python-static", ("just", "py-check"), 600),
        Lane("pull-test", ("just", "pull::test"), 600),
        Lane("cutover-test", ("just", "cutover::test"), 600),
    ]


def initial_lanes(
    selected: Sequence[str], flags: dict[str, bool] | None = None
) -> list[Lane]:
    flags = flags or {}
    environment = {name.upper(): str(value).lower() for name, value in flags.items()}
    lanes: list[Lane] = []
    for name in selected:
        if name == "python":
            lanes.extend(python_lanes())
        elif name not in {"native", "build"}:
            commands = {
                "presentation": "ci-presentation",
                "commerce": "commerce-check",
                "php": "php-check",
                "js": "js-check",
                "content": "ci-content",
                "planner": "ci-planner",
                "engine": "ci-engine",
                "genie": "ci-genie",
            }
            command = {
                "php": ("just", "php-check", "php-test"),
                "js": ("just", "js-check", "e2e-check", "js-test"),
            }.get(name, ("just", commands[name]))
            lanes.append(
                Lane("javascript" if name == "js" else name, command, 900, environment)
            )
    return lanes


def _signal_group(process: subprocess.Popen[str], sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def _terminate(process: subprocess.Popen[str]) -> None:
    """Every command gets its own session; include its shell/uv/browser children."""
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # The leader may have exited while a descendant ignored SIGTERM.
    _signal_group(process, signal.SIGKILL)
    process.wait()


def run_lane(lane: Lane, stop: threading.Event) -> tuple[str, int | None, str | None]:
    if stop.is_set():
        return lane.name, None, "cancelled before start"
    started = time.monotonic()
    print(
        f"==> {lane.name}: {' '.join(lane.command)} (timeout {lane.timeout_seconds}s)",
        flush=True,
    )
    try:
        process = subprocess.Popen(
            lane.command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
            env={**os.environ, **lane.environment},
        )
    except OSError as error:
        stop.set()
        return lane.name, None, str(error)

    def copy_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            print(f"[{lane.name}] {line}", end="", flush=True)

    reader = threading.Thread(target=copy_output, daemon=True)
    reader.start()
    next_progress = started + 30
    try:
        while process.poll() is None:
            if stop.is_set():
                return lane.name, None, "cancelled after another lane failed"
            elapsed = time.monotonic() - started
            if elapsed > lane.timeout_seconds:
                stop.set()
                return lane.name, None, f"timed out after {lane.timeout_seconds}s"
            if time.monotonic() >= next_progress:
                print(f"... {lane.name}: running {elapsed:.0f}s", flush=True)
                next_progress += 30
            time.sleep(0.1)
        if process.returncode:
            stop.set()  # Set before this worker can pick up another queued lane.
        return lane.name, process.returncode, None
    finally:
        _terminate(process)
        reader.join(timeout=2)
        if process.stdout is not None and not reader.is_alive():
            process.stdout.close()
        state = "cancelled/failed" if stop.is_set() else "ok"
        print(
            f"<== {lane.name}: {state} ({time.monotonic() - started:.1f}s)", flush=True
        )


def run_parallel(lanes: Iterable[Lane]) -> bool:
    lanes = list(lanes)
    if not lanes:
        return True
    stop = threading.Event()
    failures: list[str] = []
    print("Queued checks: " + ", ".join(lane.name for lane in lanes), flush=True)
    pool = ThreadPoolExecutor(max_workers=min(4, len(lanes)))
    try:
        futures = [pool.submit(run_lane, lane, stop) for lane in lanes]
        for future in as_completed(futures):
            name, code, error = future.result()
            if code not in (0, None) or error:
                failures.append(f"{name}: {error or f'exit {code}'}")
                stop.set()
    except BaseException:
        stop.set()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    if failures:
        print("CI preflight stopped: " + "; ".join(failures), file=sys.stderr)
        return False
    return True


def run_one(name: str, command: Sequence[str], timeout: int) -> bool:
    return run_parallel([Lane(name, tuple(command), timeout)])


def check_instance(name: str) -> None:
    """Only refresh a stopped instance belonging to this checkout."""
    sys.path.insert(0, str(ROOT / "tools/local/src"))
    from linker_local.instance import check_name, home
    from linker_local.processes import Background, port_is_free
    from linker_local.registry import Registry

    check_name(name)
    instance = Registry(home()).get(name)
    if instance is None:
        if (home() / name).exists():
            raise RuntimeError(f"unregistered instance directory: {home() / name}")
        return
    plugin = instance.wp_content / "plugins/linker-commerce"
    if (
        not plugin.is_symlink()
        or plugin.resolve() != (ROOT / "plugins/linker-commerce").resolve()
    ):
        raise RuntimeError(
            f"instance {name} does not belong to this checkout; choose --instance"
        )
    if any(
        Background(path, path).pid() is not None
        for path in instance.run_dir.glob("*.pid")
    ) or any(
        not port_is_free(port)
        for port in (instance.port, instance.engine_port, instance.genie_port)
    ):
        raise RuntimeError(
            f"instance {name} is already running; preflight will not restart or stop it"
        )


def registered_instance(name: str) -> bool:
    root = Path(
        os.environ.get("LINKER_LOCAL_HOME", str(Path.home() / "de-linker-local"))
    )
    registry = root / "instances.toml"
    return name in (tomllib.loads(registry.read_text()) if registry.exists() else {})


def run_native(instance: str) -> bool:
    sys.path.insert(0, str(ROOT / "tools/local/src"))
    from linker_local.instance import check_name, home

    check_name(instance)
    # All worktrees share the instance registry and this per-name ownership lock.
    # Retain its zero-byte inode with the registry so waiters cannot lock a replacement.
    root = home()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / f".ci-preflight-{instance}.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(
                "another preflight owns this checkout's native instance"
            ) from error
        check_instance(instance)
        passed = False
        try:
            # Failed up may already have registered and started part of the instance.
            if run_one("instance", ("just", "up", instance), 600):
                passed = run_one("native", ("just", "ci-native", "all", instance), 1500)
        finally:
            # up can fail before registration, with nothing to stop.
            stopped = (
                run_one("instance-stop", ("just", "down", instance), 120)
                if registered_instance(instance)
                else True
            )
        return passed and stopped


def _version(command: Sequence[str]) -> str:
    return subprocess.check_output(command, text=True).strip().splitlines()[0]


def configure_toolchains(selected: Sequence[str]) -> str | None:
    """Pin only the selected lane's commands to the versions used by CI."""
    if set(selected) & {
        "js",
        "javascript",
        "php",
        "python",
        "python-engine",
        "planner",
        "engine",
        "commerce",
        "build",
        "native",
    }:
        node = shutil.which("node")
        node_version = _version([node, "--version"]) if node else ""
        if not node_version.startswith("v22."):
            candidate = Path("/opt/homebrew/opt/node@22/bin")
            if not (candidate / "node").exists():
                return f"Node 22 is required; found {node_version or 'nothing'}"
            os.environ["PATH"] = f"{candidate}:{os.environ['PATH']}"
    if set(selected) & {
        "php",
        "python",
        "python-tools",
        "pull-test",
        "cutover-test",
        "commerce",
        "presentation",
        "native",
    }:
        php = os.environ.get("PHP") or shutil.which("php") or ""
        php_version = _version([php, "-r", "echo PHP_VERSION;"]) if php else ""
        if not php_version.startswith("8.3."):
            candidate = Path("/opt/homebrew/opt/php@8.3/bin/php")
            if not candidate.exists():
                return f"PHP 8.3 is required; found {php_version or 'nothing'}"
            os.environ["PHP"] = str(candidate)
    os.environ["UV_PYTHON"] = "3.12"
    return None


def _interrupted(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run affected CI checks locally before pushing."
    )
    parser.add_argument(
        "--base",
        default="origin/main",
        help="diff base (default: origin/main)",
    )
    parser.add_argument(
        "--instance",
        default="ci_preflight",
        help="local instance reused for native checks (default: ci_preflight)",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="print the selected scope and commands without running them",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="run one package or full-scope lane by name, repeatable; skips the diff classifier",
    )
    args = parser.parse_args(argv)

    os.chdir(ROOT)
    signal.signal(signal.SIGTERM, _interrupted)
    if shutil.which("just") is None:
        parser.error("just is required")
    if _git("rev-parse", "--verify", args.base, check=False) == b"":
        parser.error(f"base does not resolve: {args.base}")
    formatting = subprocess.run(
        ["git", "diff", "--check", args.base, "--"],
        cwd=ROOT,
        check=False,
    )
    if formatting.returncode:
        return formatting.returncode

    changes = changes_from(args.base)
    selected = classify(changes, args.base)
    flags = ci_scope.change_flags([(change.status, change.path) for change in changes])
    lanes = initial_lanes(selected, flags)
    if args.only:
        available = {
            lane.name: lane for lane in initial_lanes(ci_scope.FULL_LANES, flags)
        }
        available.update(
            {
                lane.name: lane
                for lane in initial_lanes(["planner", "engine", "genie"], flags)
            }
        )
        available["build"] = Lane("build", ("just", "ci-build"), 900)
        missing = set(args.only) - available.keys()
        if missing:
            parser.error("unknown lane: " + ", ".join(sorted(missing)))
        lanes = [available[name] for name in dict.fromkeys(args.only)]
        selected = []  # Explicit lanes do not implicitly start build/native.
    mode = (
        ", ".join(args.only)
        if args.only
        else "full"
        if selected == list(ci_scope.FULL_LANES)
        else ", ".join(selected) or "docs"
    )
    print(f"Local CI scope: {mode} ({len(changes)} changed paths)", flush=True)
    for change in changes[:20]:
        print(f"  {change.status} {change.path}")
    if len(changes) > 20:
        print(f"  ... {len(changes) - 20} more")
    if args.print_plan:
        for lane in lanes:
            guards = " ".join(
                f"{name}={value}" for name, value in lane.environment.items()
            )
            print(f"{lane.name}: {guards} {' '.join(lane.command)}".strip())
        if "build" in selected:
            print("build: just ci-build (after package checks)")
        if "native" in selected:
            print(
                f"native: just ci-native all {args.instance} (owned stopped instance; always stopped afterwards)"
            )
        return 0
    if not lanes and not selected:
        print("Documentation-only scope: no runtime checks required.", flush=True)
        return 0
    names = {lane.name for lane in lanes}
    toolchain_error = configure_toolchains(
        [
            *(selected or args.only),
            *(["php"] if flags["planner_build_changed"] and "planner" in names else []),
        ]
    )
    if toolchain_error:
        parser.error(toolchain_error)
    # Never inherit readiness from another process or an earlier main() call.
    os.environ.pop("LINKER_CI_PHP_READY", None)
    # Engine's Python contracts load Planner; PHP unit tests also read built JS.
    if names & {"python-engine", "php"} and not run_one(
        "javascript-dependencies", ("just", "js-install"), 600
    ):
        return 1
    if names & {"planner", "engine"} and not run_one(
        "planner-dependencies", ("just", "ci-planner-deps"), 600
    ):
        return 1
    if not run_parallel(lanes):
        return 1
    if "build" in selected and not run_one("build", ("just", "ci-build"), 900):
        return 1
    if "php" in selected:
        os.environ["LINKER_CI_PHP_READY"] = "true"
    if "native" in selected:
        try:
            if not run_native(args.instance):
                return 1
        except RuntimeError as error:
            parser.error(str(error))
    print("CI preflight passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
