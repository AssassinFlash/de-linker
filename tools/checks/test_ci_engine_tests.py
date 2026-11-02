"""The bounded Engine test runner preserves failures and stops its sibling."""

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import ci_engine_tests
import ci_preflight


class EngineRunnerTest(unittest.TestCase):
    def test_failure_terminates_the_other_process_group(self):
        real_popen = subprocess.Popen
        children = {}

        commands = []

        def launch(command, **kwargs):
            commands.append(command)
            for key, value in ci_engine_tests.THREAD_LIMITS.items():
                self.assertEqual(kwargs["env"][key], value)
            self.assertEqual(kwargs["cwd"], ci_engine_tests.ROOT / "services/engine")
            code = (
                "import time; time.sleep(0.2); raise SystemExit(7)"
                if command[-1] == "not ci_expensive"
                else "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
            )
            process = real_popen([sys.executable, "-c", code], **kwargs)
            children[command[-1]] = process
            return process

        start = time.monotonic()
        with patch.object(ci_preflight.subprocess, "Popen", side_effect=launch):
            self.assertEqual(ci_engine_tests.run(), 1)
        self.assertLess(time.monotonic() - start, 5)
        self.assertEqual(len(children), 2)
        self.assertEqual(
            {command[-1] for command in commands}, {"ci_expensive", "not ci_expensive"}
        )
        self.assertEqual(children["not ci_expensive"].returncode, 7)
        self.assertEqual(children["ci_expensive"].returncode, -signal.SIGKILL)
        for process in children.values():
            self.assertIsNotNone(process.poll())
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)

    def test_sigterm_stops_both_test_groups(self):
        # The private temporary shim replaces pytest only for these children.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pytest.py").write_text(
                "import os,signal,time\n"
                "from pathlib import Path\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                "Path(os.environ['ENGINE_TEST_ROOT'], str(os.getpid())).touch()\n"
                "time.sleep(30)\n"
            )
            env = {
                **os.environ,
                "ENGINE_TEST_ROOT": directory,
                "PYTHONPATH": directory,
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            process = subprocess.Popen(
                [sys.executable, ci_engine_tests.__file__],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            pids = []
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    pids = [int(p.name) for p in root.iterdir() if p.name.isdecimal()]
                    if len(pids) == 2:
                        break
                    time.sleep(0.05)
                self.assertEqual(len(pids), 2)
                process.send_signal(signal.SIGTERM)
                self.assertNotEqual(process.wait(timeout=5), 0)
                for pid in pids:
                    with self.assertRaises(ProcessLookupError):
                        os.killpg(pid, 0)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                for pid in pids:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
