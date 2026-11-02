"""The bounded Engine test runner preserves failures and stops its sibling."""

import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import ci_engine_tests


class EngineRunnerTest(unittest.TestCase):
    def test_failure_terminates_the_other_process_group(self):
        real_popen = subprocess.Popen
        children = []

        def launch(_command, **kwargs):
            code = (
                "import time; time.sleep(0.2); raise SystemExit(7)"
                if not children
                else "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
            )
            process = real_popen([sys.executable, "-c", code], **kwargs)
            children.append(process)
            return process

        start = time.monotonic()
        with patch.object(ci_engine_tests.subprocess, "Popen", side_effect=launch):
            self.assertEqual(ci_engine_tests.run(), 7)
        self.assertLess(time.monotonic() - start, 5)
        self.assertEqual(len(children), 2)
        for process in children:
            self.assertIsNotNone(process.poll())
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)


if __name__ == "__main__":
    unittest.main()
