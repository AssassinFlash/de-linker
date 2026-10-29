#!/usr/bin/env python3
"""Run the checks selected by the current branch diff before a push.

The path classifier intentionally mirrors check.yml's conservative scopes.
Unknown, new, binary, control-plane or shared changes select the full suite.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = {"AGENTS.md", "CLAUDE.md", "CONTEXT.md", "README.md"}
PRESENTATION = re.compile(
    r"plugins/linker-commerce/content/(?:livecanvas/(?:de/)?[a-z0-9_-]+[.]html|windpress/[a-z0-9_-]+[.]css)"
)
COMMERCE = re.compile(
    r"plugins/linker-commerce/(?:"
    r"includes/(?:Presentation/(?:ProductShortcodes|LanguageLinks|LibraryPage)[.]php|"
    r"Storefront/ProductView[.]php|Registration/PendingProfileCapacity[.]php)|"
    r"assets/[a-z0-9-]+[.]js|"
    r"content/(?:livecanvas/(?:de/)?[a-z0-9_-]+[.]html|windpress/[a-z0-9_-]+[.]css)|"
    r"languages/linker-commerce-de_DE_formal[.](?:po|mo)|"
    r"tests/php/(?:Unit/(?:Presentation/(?:ProductShortcodes|LanguageLinks|LibraryPage)Test[.]php|"
    r"Storefront/ProductViewTest[.]php)|Integration/RegistrationCapacityTest[.]php)|"
    r"tests/js/[a-z0-9-]+[.]test[.]mjs)"
)


@dataclass(frozen=True)
class Change:
    status: str
    path: str


@dataclass(frozen=True)
class Lane:
    name: str
    command: tuple[str, ...]
    timeout_seconds: int


def _git(*arguments: str, check: bool = True) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=check,
        capture_output=True,
    ).stdout


def _is_document(path: str) -> bool:
    return path in DOCUMENTS or (
        path.startswith("docs/") and path.endswith((".md", ".rst", ".txt"))
    )


def _is_acceptance_record(path: str) -> bool:
    return path.startswith("docs/acceptance/") and path.endswith(
        (".json", ".png", ".pdf", ".jpg", ".jpeg")
    )


def _presentation(path: str) -> bool:
    return bool(PRESENTATION.fullmatch(path)) or path == (
        "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php"
    )


def _commerce(path: str) -> bool:
    return bool(COMMERCE.fullmatch(path))


def classify(changes: Sequence[Change]) -> str:
    """Return the same conservative four-way scope used by CI."""
    if changes and all(
        _is_document(change.path) or _is_acceptance_record(change.path)
        for change in changes
    ):
        return "docs"
    if changes and all(
        _is_document(change.path)
        or _is_acceptance_record(change.path)
        or (change.status == "M" and _presentation(change.path))
        for change in changes
    ):
        return "presentation"
    if changes and all(
        _is_document(change.path)
        or _is_acceptance_record(change.path)
        or (change.status == "M" and _commerce(change.path))
        for change in changes
    ):
        return "commerce"
    return "full"


def changes_from(base: str) -> list[Change]:
    """Include committed, staged, unstaged and untracked work against base."""
    fields = (
        _git("diff", "--name-status", "--no-renames", "-z", base, "--")
        .decode(errors="surrogateescape")
        .split("\0")
    )
    changes = [
        Change(status, path)
        for status, path in zip(fields[0:-1:2], fields[1:-1:2])
        if status and path
    ]
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


def full_lanes() -> list[Lane]:
    """Independent toolchains; the build waits until these shared trees settle."""
    return [
        Lane("python-genie", ("just", "py-test-group", "genie"), 900),
        Lane("python-engine", ("just", "py-test-group", "engine"), 900),
        Lane("python-tools", ("just", "py-test-group", "tools"), 900),
        Lane("python-harnesses", ("just", "py-test-group", "harnesses"), 600),
        Lane("python-static", ("just", "py-check"), 600),
        Lane("pull-test", ("just", "pull::test"), 600),
        Lane("cutover-test", ("just", "cutover::test"), 600),
        Lane("php", ("just", "php-check", "php-test"), 900),
        Lane("javascript", ("just", "js-check", "e2e-check", "js-test"), 900),
        Lane("content", ("just", "ci-content"), 600),
    ]


def initial_lanes(mode: str) -> list[Lane]:
    if mode == "docs":
        return []
    if mode == "presentation":
        return [Lane("presentation", ("just", "ci-presentation"), 900)]
    if mode == "commerce":
        return [Lane("commerce", ("just", "commerce-check"), 900)]
    return full_lanes()


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run_lane(
    lane: Lane,
    stop: threading.Event,
) -> tuple[str, int | None, str | None]:
    """Run one lane, stream prefixed output, and stop as soon as another fails."""
    print(f"==> {lane.name}: {' '.join(lane.command)}", flush=True)
    process = subprocess.Popen(
        lane.command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def copy_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            print(f"[{lane.name}] {line}", end="", flush=True)

    reader = threading.Thread(target=copy_output, daemon=True)
    reader.start()
    started = time.monotonic()
    while process.poll() is None:
        if stop.is_set():
            _terminate(process)
            reader.join(timeout=2)
            return lane.name, None, "cancelled after another lane failed"
        if time.monotonic() - started > lane.timeout_seconds:
            _terminate(process)
            reader.join(timeout=2)
            return lane.name, None, f"timed out after {lane.timeout_seconds}s"
        time.sleep(0.1)
    reader.join(timeout=2)
    code = process.returncode
    if code:
        return lane.name, code, None
    print(f"<== {lane.name}: ok ({time.monotonic() - started:.1f}s)", flush=True)
    return lane.name, 0, None


def run_parallel(lanes: Iterable[Lane]) -> bool:
    lanes = list(lanes)
    if not lanes:
        return True
    stop = threading.Event()
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=min(4, len(lanes))) as pool:
        futures = [pool.submit(run_lane, lane, stop) for lane in lanes]
        for future in as_completed(futures):
            name, code, error = future.result()
            if code not in (0, None):
                failures.append(f"{name}: exit {code}")
                stop.set()
            elif error:
                failures.append(f"{name}: {error}")
                stop.set()
    if failures:
        print("CI preflight stopped: " + "; ".join(failures), file=sys.stderr)
        return False
    return True


def run_one(name: str, command: Sequence[str], timeout: int) -> bool:
    return run_parallel([Lane(name, tuple(command), timeout)])


def _version(command: Sequence[str]) -> str:
    return subprocess.check_output(command, text=True).strip().splitlines()[0]


def configure_toolchains() -> str | None:
    """Pin local commands to the Node, PHP and Python versions used by CI."""
    node = shutil.which("node")
    node_version = _version([node, "--version"]) if node else ""
    if not node_version.startswith("v22."):
        candidate = Path("/opt/homebrew/opt/node@22/bin")
        if not (candidate / "node").exists():
            return f"Node 22 is required; found {node_version or 'nothing'}"
        os.environ["PATH"] = f"{candidate}:{os.environ['PATH']}"

    php = os.environ.get("PHP") or shutil.which("php") or ""
    php_version = _version([php, "-r", "echo PHP_VERSION;"]) if php else ""
    if not php_version.startswith("8.3."):
        candidate = Path("/opt/homebrew/opt/php@8.3/bin/php")
        if not candidate.exists():
            return f"PHP 8.3 is required; found {php_version or 'nothing'}"
        os.environ["PHP"] = str(candidate)

    os.environ["UV_PYTHON"] = "3.12"
    return None


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
        help="run one full-scope lane by name, repeatable; skips the diff classifier",
    )
    args = parser.parse_args(argv)

    if shutil.which("just") is None:
        parser.error("just is required")
    toolchain_error = configure_toolchains()
    if toolchain_error:
        parser.error(toolchain_error)
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
    mode = classify(changes)
    print(f"Local CI scope: {mode} ({len(changes)} changed paths)", flush=True)
    for change in changes[:20]:
        print(f"  {change.status:>1} {change.path}")
    if len(changes) > 20:
        print(f"  ... {len(changes) - 20} more")

    lanes = initial_lanes(mode if not args.only else "full")
    if args.only:
        selected = set(args.only)
        selectable = [*lanes, Lane("build", ("just", "ci-build"), 900)]
        lanes = [lane for lane in selectable if lane.name in selected]
        missing = selected.difference(lane.name for lane in selectable)
        if missing:
            parser.error("unknown lane: " + ", ".join(sorted(missing)))
        mode = "full"
    if args.print_plan:
        for lane in lanes:
            print(f"{lane.name}: {' '.join(lane.command)}")
        if mode == "full" and not args.only:
            print("build: just ci-build")
            print(f"native: just ci-native all {args.instance}")
        return 0
    if mode == "docs":
        print("Documentation-only scope: no runtime checks required.", flush=True)
        return 0

    selected = set(args.only)
    needs_dependencies = not selected or bool(
        selected & {"php", "javascript", "python-engine"}
    )
    if (
        mode == "full"
        and needs_dependencies
        and not run_one("dependencies", ("just", "ci-deps"), 600)
    ):
        return 1

    if not run_parallel(lanes):
        return 1

    if (
        mode == "full"
        and not args.only
        and not run_one("build", ("just", "ci-build"), 900)
    ):
        return 1

    if mode not in {"full", "commerce"} or args.only:
        print("CI preflight passed.", flush=True)
        return 0

    instance = args.instance
    up_ok = run_one("instance", ("just", "up", instance), 600)
    if not up_ok:
        return 1
    try:
        if not run_one(
            "native",
            ("just", "ci-native", "all", instance),
            1500,
        ):
            return 1
    finally:
        run_one("instance-stop", ("just", "down", instance), 120)

    print("CI preflight passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
