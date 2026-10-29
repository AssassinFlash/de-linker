"""Contracts for the workflow's actual scope selector, without an API call."""

import ast
import json
import os
import re
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/check.yml"
TEXT = WORKFLOW.read_text()
JUSTFILE = (ROOT / "justfile").read_text()
SCRIPT = TEXT.split("          python3 - <<'PYTHON'\n", 1)[1].split(
    "          PYTHON\n", 1
)[0]
SCRIPT = "\n".join(line[10:] for line in SCRIPT.splitlines())
TREE = ast.parse(SCRIPT)
FUNCTIONS = ast.Module(
    body=[node for node in TREE.body if isinstance(node, ast.FunctionDef)],
    type_ignores=[],
)


class ScopeTest(unittest.TestCase):
    def setUp(self):
        self.ns = {"re": re, "json": json, "subprocess": subprocess}
        exec(compile(FUNCTIONS, str(WORKFLOW), "exec"), self.ns)

    def classify(self, *changes):
        return self.ns["classify"](list(changes))

    def test_existing_surfaces_and_both_next_batch_consumers(self):
        self.assertEqual(self.classify(("M", "AGENTS.md")), "docs")
        self.assertEqual(
            self.classify(
                ("M", "plugins/linker-commerce/content/windpress/tokens.css")
            ),
            "presentation",
        )
        for path in (
            "includes/Presentation/ProductShortcodes.php",
            "includes/Registration/PendingProfileCapacity.php",
            "includes/Storefront/ProductView.php",
            "assets/account-ui.js",
            "languages/linker-commerce-de_DE_formal.mo",
            "tests/php/Integration/RegistrationCapacityTest.php",
            "tests/js/library-ui.test.mjs",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    self.classify(("M", "plugins/linker-commerce/" + path)), "commerce"
                )

    def test_shared_or_unknown_change_requires_full_even_with_commerce(self):
        for path in (
            ".github/workflows/check.yml",
            "justfile",
            "plugins/linker-commerce/composer.lock",
            "plugins/linker-commerce/package-lock.json",
            "plugins/linker-commerce/src/index.tsx",
            "plugins/linker-commerce/build/index.js",
            "plugins/linker-commerce/includes/Registration/Approval.php",
            "plugins/linker-commerce/includes/Module.php",
            "plugins/linker-commerce/includes/Presentation/PageUrls.php",
            "plugins/linker-commerce/includes/Presentation/WindPressVolume.php",
            "plugins/linker-commerce/includes/Presentation/Module.php",
            "plugins/linker-commerce/includes/Presentation/UnknownSurface.php",
            "plugins/linker-commerce/tests/php/Unit/Presentation/PageUrlsTest.php",
            "plugins/linker-tools/includes/Module.php",
            "tools/checks/test_ci_scope.py",
            "services/engine/app.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    self.classify(
                        ("M", "plugins/linker-commerce/assets/account-ui.js"),
                        ("M", path),
                    ),
                    "full",
                )
        for status in ("A", "D", "R100", "T"):
            self.assertEqual(
                self.classify((status, "plugins/linker-commerce/assets/account-ui.js")),
                "full",
            )
        self.assertEqual(self.classify(), "full")

    def test_dispatch_requires_checked_base_and_missing_base_stays_full(self):
        top = ast.Module(
            body=[node for node in TREE.body if not isinstance(node, ast.FunctionDef)],
            type_ignores=[],
        )
        with TemporaryDirectory() as folder:
            for base, proven, expected in (
                ("", True, "full"),
                ("0" * 40, True, "full"),
                ("a" * 40, False, "full"),
                ("a" * 40, True, "commerce"),
            ):
                with self.subTest(base=base, proven=proven):
                    output = Path(folder) / "output"
                    output.write_text("")
                    self.ns["git"] = Mock(
                        side_effect=[
                            b"",
                            b"M\0plugins/linker-commerce/assets/account-ui.js\0",
                        ]
                    )
                    self.ns["regular_change"] = Mock(return_value=True)
                    self.ns["checked_base"] = Mock(return_value=proven)
                    with (
                        patch.dict(
                            os.environ,
                            {
                                "EVENT_NAME": "pull_request",
                                "HEAD_SHA": "b" * 40,
                                "BASE_SHA": base,
                                "GITHUB_OUTPUT": str(output),
                                "GITHUB_STEP_SUMMARY": str(Path(folder) / "summary"),
                            },
                        ),
                        patch(
                            "subprocess.run",
                            return_value=subprocess.CompletedProcess([], 0),
                        ),
                    ):
                        exec(compile(top, str(WORKFLOW), "exec"), self.ns)
                    self.assertIn("mode=" + expected + "\n", output.read_text())

    def test_symlink_or_missing_blob_cannot_enter_commerce(self):
        self.ns["git"] = Mock(
            side_effect=[b"100644 blob hash\tpath", b"120000 blob hash\tpath"]
        )
        self.assertFalse(self.ns["regular_change"]("M", "path", "base", "head"))
        self.assertFalse(self.ns["regular_change"]("T", "path", "base", "head"))

    def test_successful_baseline_requires_same_workflow_tree_and_scope(self):
        commit = "a" * 40
        run = {
            "status": "completed",
            "conclusion": "success",
            "event": "pull_request",
            "display_title": "check #1 | tree-ref=" + commit,
            "id": 1,
            "run_attempt": 1,
        }
        self.ns["os"] = type("Env", (), {"environ": {"REPOSITORY": "owner/repo"}})
        for scope in ("full", "presentation", "commerce"):
            self.ns["git"] = Mock(
                side_effect=[b"workflow", b"workflow", b"tree", b"tree"]
            )
            self.ns["api"] = Mock(
                return_value={
                    "jobs": [
                        {
                            "name": "check (8.3, 22, 3.12)",
                            "steps": [
                                {
                                    "name": f"Record validation scope ({scope})",
                                    "conclusion": "success",
                                }
                            ],
                        }
                    ]
                }
            )
            self.assertTrue(self.ns["checked_run"](run, commit))
        self.ns["git"] = Mock(side_effect=[b"old-workflow", b"new-workflow"])
        self.assertFalse(self.ns["checked_run"](run, commit))
        self.ns["git"] = Mock(
            side_effect=[b"workflow", b"workflow", b"old-tree", b"new-tree"]
        )
        self.assertFalse(self.ns["checked_run"](run, commit))
        self.assertFalse(
            self.ns["checked_run"]({**run, "conclusion": "failure"}, commit)
        )
        self.assertFalse(
            self.ns["checked_run"]({**run, "status": "in_progress"}, commit)
        )

    def test_squash_merge_and_merge_commit_find_the_pr_head(self):
        commit = "a" * 40
        source = "b" * 40
        run = {"id": 1}
        self.ns["latest_run"] = Mock(return_value=run)
        self.ns["checked_run"] = Mock(return_value=True)

        self.ns["git"] = Mock(return_value=f"{commit} {'c' * 40} {source}\n".encode())
        self.assertIs(self.ns["checked_pr_tree"](commit), run)

        self.ns["git"] = Mock(return_value=f"{commit}\n".encode())
        self.ns["os"] = type("Env", (), {"environ": {"REPOSITORY": "owner/repo"}})
        self.ns["api"] = Mock(
            return_value=[
                {"merge_commit_sha": "d" * 40, "head": {"sha": "e" * 40}},
                {"merge_commit_sha": commit, "head": {"sha": source}},
            ]
        )
        self.assertIs(self.ns["checked_pr_tree"](commit), run)

    def test_plan_retains_fail_closed_baseline_and_native_commerce_checks(self):
        # Check the actual dispatch wiring as well as the pure classifier.
        self.assertIn(
            'elif candidate in {"presentation", "commerce"} and event == "pull_request":\n                if checked_base(base):',
            SCRIPT,
        )
        self.assertIn(
            'mode, reason = "full", "Change or baseline proof unavailable;', SCRIPT
        )
        self.assertIn("group: [core, mail, inquiry, inventory, runtime, admin]", TEXT)
        self.assertIn('just ci-native "${{ matrix.group }}" smoke', TEXT)
        self.assertNotIn("/Justfile", JUSTFILE)
        for marker in (
            "run_mail()",
            "GlobalBusinessCapacityTest",
            "run_inquiry()",
            "PublicAdmissionOwnersTest",
            "ProformaPriceGateTest",
            "GenieInquiryTest",
            "InquiryAssessmentTest",
            "run_admin()",
            "admin-mfa",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, JUSTFILE)


if __name__ == "__main__":
    unittest.main()
