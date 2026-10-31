"""Behavioral contracts for local CI selection, cancellation and cleanup."""

import contextlib
import io
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import ci_preflight as preflight
import ci_scope
from ci_preflight import Change, Lane


class PreflightScopeTest(unittest.TestCase):
    def setUp(self):
        regular = patch.object(ci_scope, "regular_change", return_value=True)
        non_runtime = patch.object(ci_scope, "non_runtime_change", return_value=True)
        regular.start()
        non_runtime.start()
        self.addCleanup(regular.stop)
        self.addCleanup(non_runtime.stop)

    def test_same_packages_and_guards_as_ci(self):
        changes = [
            Change("A", "apps/planner/src/example.ts"),
            Change("M", "services/engine/app.py"),
            Change("D", "services/genie/tests/test_old.py"),
        ]
        selected = preflight.classify(changes)
        self.assertEqual(selected, ["planner", "engine", "genie"])
        lanes = preflight.initial_lanes(selected)
        self.assertEqual(
            [lane.command for lane in lanes],
            [("just", "ci-planner"), ("just", "ci-engine"), ("just", "ci-genie")],
        )
        self.assertEqual(preflight.classify([Change("A", "docs/specs/test.md")]), [])
        self.assertEqual(preflight.initial_lanes([]), [])
        self.assertEqual(
            preflight.classify([Change("M", "justfile")]), list(ci_scope.FULL_LANES)
        )
        presentation = [
            Change("M", "plugins/linker-commerce/content/livecanvas/home.html"),
            Change(
                "M",
                "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php",
            ),
        ]
        flags = ci_scope.change_flags(
            [(change.status, change.path) for change in presentation]
        )
        lane = preflight.initial_lanes(preflight.classify(presentation), flags)[0]
        self.assertEqual(lane.environment["PHP_TEST_CHANGED"], "true")
        self.assertEqual(lane.environment["CATALOG_CHANGED"], "true")

    def test_full_plan_preserves_all_python_groups_and_language_checks(self):
        lanes = preflight.initial_lanes(ci_scope.FULL_LANES)
        self.assertEqual(
            {lane.name for lane in lanes},
            {
                "php",
                "javascript",
                "python-genie",
                "python-engine",
                "python-tools",
                "python-harnesses",
                "python-static",
                "pull-test",
                "cutover-test",
                "content",
            },
        )
        self.assertEqual(
            next(lane.command for lane in lanes if lane.name == "php"),
            ("just", "php-check", "php-test"),
        )


class PreflightLifecycleTest(unittest.TestCase):
    def test_cancelled_queue_does_not_spawn_and_failure_stops_next_lane(self):
        stop = threading.Event()
        stop.set()
        with patch.object(subprocess, "Popen") as popen:
            self.assertIn(
                "before start",
                preflight.run_lane(Lane("queued", ("missing",), 10), stop)[2],
            )
        popen.assert_not_called()
        with TemporaryDirectory() as directory:
            marker = Path(directory) / "must-not-start"
            lanes = [
                Lane("fail", (sys.executable, "-c", "raise SystemExit(7)"), 10),
                Lane(
                    "queued",
                    (
                        sys.executable,
                        "-c",
                        f"from pathlib import Path; Path({str(marker)!r}).touch()",
                    ),
                    10,
                ),
            ]
            with patch.object(
                preflight,
                "ThreadPoolExecutor",
                side_effect=lambda **_: ThreadPoolExecutor(max_workers=1),
            ):
                self.assertFalse(preflight.run_parallel(lanes))
            self.assertFalse(marker.exists())

    def test_timeout_and_cancellation_reap_term_ignoring_grandchild(self):
        # Temporary directory, leader and descendant belong to this test only.
        # run_lane must stop the whole group even when the leader exits first.
        for cause in ("timeout", "cancel"):
            with self.subTest(cause=cause), TemporaryDirectory() as directory:
                marker = Path(directory) / "pid"
                child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
                script = (
                    "import subprocess,sys,time; from pathlib import Path; "
                    f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
                    f"Path({str(marker)!r}).write_text(str(p.pid)); time.sleep(60)"
                )
                stop = threading.Event()
                timer = threading.Timer(0.5, stop.set) if cause == "cancel" else None
                pid = None
                try:
                    if timer:
                        timer.start()
                    result = preflight.run_lane(
                        Lane(cause, (sys.executable, "-c", script), 1), stop
                    )
                    self.assertIn(
                        "timed out" if cause == "timeout" else "cancelled", result[2]
                    )
                    pid = int(marker.read_text())
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        state = subprocess.run(
                            ["ps", "-o", "stat=", "-p", str(pid)],
                            capture_output=True,
                            text=True,
                            check=False,
                        ).stdout.strip()
                        if not state or state.startswith("Z"):
                            break
                        time.sleep(0.02)
                    self.assertTrue(not state or state.startswith("Z"), state)
                finally:
                    if timer:
                        timer.cancel()
                        timer.join()
                    if pid is not None:
                        with contextlib.suppress(ProcessLookupError):
                            os.kill(pid, signal.SIGKILL)

    def test_native_partial_start_and_stop_failure_are_not_success(self):
        for results, expected_calls in (
            ([False, True], ["instance", "instance-stop"]),
            ([True, True, False], ["instance", "native", "instance-stop"]),
        ):
            with self.subTest(results=results), TemporaryDirectory() as directory:
                with (
                    patch.dict(os.environ, {"LINKER_LOCAL_HOME": directory}),
                    patch.object(preflight, "check_instance"),
                    patch.object(preflight, "registered_instance", return_value=True),
                    patch.object(preflight, "run_one", side_effect=results) as run,
                ):
                    self.assertFalse(preflight.run_native("owned"))
                self.assertEqual(
                    [call.args[0] for call in run.call_args_list], expected_calls
                )

    def test_unowned_instance_is_never_started_or_stopped(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"LINKER_LOCAL_HOME": directory}),
            patch.object(
                preflight,
                "check_instance",
                side_effect=RuntimeError("foreign checkout"),
            ),
            patch.object(preflight, "run_one") as run,
            self.assertRaisesRegex(RuntimeError, "foreign checkout"),
        ):
            preflight.run_native("foreign")
        run.assert_not_called()

    def test_existing_instance_requires_this_checkout_and_free_ports(self):
        sys.path.insert(0, str(preflight.ROOT / "tools/local/src"))
        from linker_local.instance import Instance

        with TemporaryDirectory() as directory:
            root = Path(directory)
            instance = Instance("owned", 8888, 8889, 8890, root)
            plugins = instance.wp_content / "plugins"
            plugins.mkdir(parents=True)
            plugin = plugins / "linker-commerce"
            with (
                patch("linker_local.registry.Registry.get", return_value=instance),
                patch("linker_local.processes.port_is_free", return_value=True) as free,
            ):
                plugin.symlink_to(root / "foreign")
                with self.assertRaisesRegex(RuntimeError, "does not belong"):
                    preflight.check_instance("owned")
                plugin.unlink()
                plugin.symlink_to(preflight.ROOT / "plugins/linker-commerce")
                preflight.check_instance("owned")
                free.return_value = False
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    preflight.check_instance("owned")

    def test_print_plan_has_no_toolchain_or_dependency_side_effects(self):
        with (
            patch.object(preflight, "_git", return_value=b"sha"),
            patch.object(preflight, "changes_from", return_value=[]),
            patch.object(preflight, "classify", return_value=["genie"]),
            patch.object(preflight, "configure_toolchains") as configure,
            patch.object(preflight, "run_parallel") as run,
            patch.object(
                subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(preflight.main(["--print-plan"]), 0)
        self.assertIn("just ci-genie", output.getvalue())
        configure.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
