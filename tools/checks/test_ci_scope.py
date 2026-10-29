"""Local contracts for CI selection and the final result gate."""

import json
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import ci_scope

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / ".github/workflows/check.yml").read_text()


class ScopeTest(unittest.TestCase):
    def setUp(self):
        self.regular = patch.object(ci_scope, "regular_change", return_value=True)
        self.non_runtime = patch.object(
            ci_scope, "non_runtime_change", return_value=True
        )
        self.regular.start()
        self.non_runtime.start()
        self.addCleanup(self.regular.stop)
        self.addCleanup(self.non_runtime.stop)

    def classify(self, *changes):
        return ci_scope.classify(list(changes), "base", "head")

    def test_document_presentation_and_existing_commerce_surfaces(self):
        self.assertEqual(self.classify(("M", "AGENTS.md")), [])
        self.assertEqual(
            self.classify(
                ("M", "plugins/linker-commerce/content/windpress/tokens.css")
            ),
            ["presentation"],
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
                    self.classify(("M", "plugins/linker-commerce/" + path)),
                    ["commerce", "mu"],
                )

    def test_packages_compose_without_an_instance_for_service_changes(self):
        self.assertEqual(
            self.classify(("A", "apps/planner/src/domain/new.ts")), ["planner"]
        )
        self.assertEqual(
            self.classify(
                ("M", "services/engine/app.py"),
                ("D", "services/genie/tests/test_old.py"),
            ),
            ["engine", "genie"],
        )
        self.assertEqual(
            self.classify(
                ("M", "docs/specs/13-genie.md"),
                ("M", "services/genie/app.py"),
            ),
            ["genie"],
        )

    def test_shared_unknown_empty_and_structural_changes_are_full(self):
        for path in (
            ".github/workflows/check.yml",
            "justfile",
            "tools/build.just",
            "tools/checks/ci_scope.py",
            "tools/checks/test_ci_scope.py",
            "plugins/linker-commerce/composer.lock",
            "plugins/linker-commerce/src/index.tsx",
            "plugins/linker-commerce/includes/Module.php",
            "plugins/linker-tools/includes/Planner/Gateway.php",
            "plugins/linker-tools/project-input-contracts.json",
            "plugins/linker-tools/build/index.js",
            "mu-plugins/linker-engine-pin.php",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    self.classify(("M", "apps/planner/src/App.tsx"), ("M", path)),
                    list(ci_scope.FULL_LANES),
                )
        for status in ("R100", "C100", "T", "U"):
            with self.subTest(status=status):
                self.assertEqual(
                    self.classify((status, "apps/planner/src/App.tsx")),
                    list(ci_scope.FULL_LANES),
                )
        self.assertEqual(self.classify(), list(ci_scope.FULL_LANES))
        self.assertEqual(
            self.classify(("A", "plugins/linker-commerce/assets/account-ui.js")),
            list(ci_scope.FULL_LANES),
        )

    def test_planner_manifest_requires_unchanged_non_planner_entries(self):
        before = {
            "sources": {"package.json": "a" * 64},
            "build": {
                "build/index.js": "b" * 64,
                "build/planner/index.js": "c" * 64,
            },
        }
        after = {
            "sources": before["sources"],
            "build": {**before["build"], "build/planner/index.js": "d" * 64},
        }
        changes = [
            ("M", "apps/planner/src/App.tsx"),
            ("M", "plugins/linker-tools/build/planner/index.js"),
            ("M", "plugins/linker-tools/build/manifest.json"),
        ]
        with patch.object(
            ci_scope,
            "git",
            side_effect=[json.dumps(before).encode(), json.dumps(after).encode()],
        ):
            self.assertEqual(ci_scope.classify(changes, "base", "head"), ["planner"])
        for mutation in (
            {"sources": {"package.json": "e" * 64}},
            {"build": {"build/index.js": "e" * 64}},
        ):
            changed = {
                key: {**after.get(key, {}), **mutation.get(key, {})}
                if key in mutation
                else value
                for key, value in after.items()
            }
            with (
                self.subTest(mutation=mutation),
                patch.object(
                    ci_scope,
                    "git",
                    side_effect=[
                        json.dumps(before).encode(),
                        json.dumps(changed).encode(),
                    ],
                ),
            ):
                self.assertEqual(
                    ci_scope.classify(changes, "base", "head"),
                    list(ci_scope.FULL_LANES),
                )
        with patch.object(ci_scope, "planner_manifest_isolated", return_value=False):
            self.assertEqual(
                self.classify(("M", "plugins/linker-tools/build/manifest.json")),
                list(ci_scope.FULL_LANES),
            )

    def test_file_type_and_non_runtime_blob_checks_fail_closed(self):
        self.regular.stop()
        self.non_runtime.stop()
        with patch.object(
            ci_scope,
            "git",
            side_effect=[b"100644 blob hash\tpath", b"120000 blob hash\tpath"],
        ):
            self.assertFalse(ci_scope.regular_change("M", "path", "base", "head"))
        with patch.object(ci_scope, "non_runtime_change", return_value=False):
            self.assertEqual(
                ci_scope.classify(
                    [("M", "docs/specs/13-genie.md"), ("M", "services/genie/app.py")],
                    "base",
                    "head",
                ),
                list(ci_scope.FULL_LANES),
            )

    def test_real_git_diff_detects_rename_and_symlink(self):
        self.regular.stop()
        self.non_runtime.stop()
        with TemporaryDirectory() as folder:
            repo = Path(folder)
            previous = Path.cwd()
            self.addCleanup(os.chdir, previous)
            os.chdir(repo)

            def run(*args):
                return subprocess.check_output(args, text=True).strip()

            run("git", "init", "-q")
            run("git", "config", "user.email", "ci@example.invalid")
            run("git", "config", "user.name", "CI fixture")
            source = repo / "apps/planner/src"
            source.mkdir(parents=True)
            (source / "old.ts").write_text("export const value = 1;\n")
            run("git", "add", ".")
            run("git", "commit", "-qm", "base")
            base = run("git", "rev-parse", "HEAD")
            run("git", "mv", "apps/planner/src/old.ts", "apps/planner/src/new.ts")
            run("git", "commit", "-qm", "rename")
            head = run("git", "rev-parse", "HEAD")
            changes = ci_scope.diff_changes(base, head)
            self.assertTrue(any(status.startswith("R") for status, _ in changes))
            self.assertEqual(
                ci_scope.classify(changes, base, head), list(ci_scope.FULL_LANES)
            )
            (source / "new.ts").unlink()
            (source / "new.ts").symlink_to("target.ts")
            run("git", "add", ".")
            run("git", "commit", "-qm", "symlink")
            symlink = run("git", "rev-parse", "HEAD")
            self.assertEqual(
                ci_scope.classify(ci_scope.diff_changes(head, symlink), head, symlink),
                list(ci_scope.FULL_LANES),
            )

    def run_plan(self, event, candidate, proven=True):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            output.write_text("")
            environment = {
                "EVENT_NAME": event,
                "HEAD_SHA": "b" * 40,
                "BASE_SHA": "a" * 40,
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(Path(folder) / "summary"),
            }
            with (
                patch.dict(os.environ, environment),
                patch.object(ci_scope, "git", return_value=b""),
                patch.object(
                    ci_scope,
                    "diff_changes",
                    return_value=[("M", "services/genie/app.py")],
                ),
                patch.object(ci_scope, "classify", return_value=candidate),
                patch.object(ci_scope, "checked_base", return_value=proven) as checked,
                patch(
                    "subprocess.run", return_value=subprocess.CompletedProcess([], 0)
                ),
            ):
                ci_scope.plan()
            return output.read_text(), checked

    def test_only_a_fully_checked_pull_request_base_enables_a_narrow_lane(self):
        for event, proven, expected in (
            ("pull_request", True, "scoped"),
            ("pull_request", False, "full"),
            ("workflow_dispatch", True, "full"),
        ):
            with self.subTest(event=event, proven=proven):
                output, checked = self.run_plan(event, ["genie"], proven)
                self.assertIn("mode=" + expected + "\n", output)
                self.assertIn("genie=true\n", output)
                if expected == "full":
                    self.assertIn("php=true\n", output)
                    self.assertIn("mu=true\n", output)
                else:
                    self.assertIn("php=false\n", output)
                    self.assertIn("mu=false\n", output)
                self.assertEqual(checked.called, event == "pull_request")

    def test_full_candidate_never_becomes_scoped(self):
        output, checked = self.run_plan(
            "pull_request", list(ci_scope.FULL_LANES), proven=True
        )
        self.assertIn("mode=full\n", output)
        checked.assert_not_called()

    def test_document_push_keeps_its_non_runtime_scope(self):
        output, checked = self.run_plan("push", [], proven=False)
        self.assertIn("mode=docs\n", output)
        self.assertIn("php=false\n", output)
        self.assertIn("mu=false\n", output)
        checked.assert_not_called()

    def ledger(self, mode="scoped", lanes=None):
        lanes = ["genie"] if lanes is None else lanes
        return {
            "base": "a" * 40,
            "head": "b" * 40,
            "mode": mode,
            "candidate": lanes if mode == "scoped" else list(ci_scope.FULL_LANES),
            "lanes": lanes,
            "changes": [{"status": "M", "path": "services/genie/app.py"}],
        }

    def results(self, selected):
        return {
            lane: {
                "result": "success" if lane == "plan" or lane in selected else "skipped"
            }
            for lane in ("plan", *ci_scope.LANES)
        }

    def audit(self, ledger, results, recomputed=None):
        candidate = ledger["candidate"] if recomputed is None else recomputed
        event = "push" if ledger["mode"] == "reuse" else "pull_request"
        with (
            patch.dict(
                os.environ,
                {
                    "BASE_SHA": "a" * 40,
                    "HEAD_SHA": "b" * 40,
                    "EVENT_NAME": event,
                },
            ),
            patch.object(ci_scope, "classify", return_value=candidate),
        ):
            return ci_scope.audit_gate(
                ledger, results, [("M", "services/genie/app.py")]
            )

    def test_gate_rejects_missing_unselected_or_duplicate_execution(self):
        self.assertEqual(self.audit(self.ledger(), self.results(["genie"])), [])
        self.assertEqual(
            self.audit(
                self.ledger("full", list(ci_scope.FULL_LANES)),
                self.results(ci_scope.FULL_LANES),
            ),
            [],
        )
        for name, ledger, results in (
            ("selected job skipped", self.ledger(), self.results([])),
            (
                "unselected job succeeded",
                self.ledger(),
                self.results(["genie", "planner"]),
            ),
            (
                "full run missing a package",
                self.ledger("full", list(ci_scope.FULL_LANES)),
                self.results(["genie"]),
            ),
            (
                "full and narrow results mixed",
                self.ledger("full", list(ci_scope.FULL_LANES)),
                self.results(["genie"]),
            ),
            (
                "missing job result",
                self.ledger(),
                {
                    key: value
                    for key, value in self.results(["genie"]).items()
                    if key != "genie"
                },
            ),
            (
                "failed plan",
                self.ledger(),
                {**self.results(["genie"]), "plan": {"result": "failure"}},
            ),
        ):
            with self.subTest(name=name):
                self.assertTrue(self.audit(ledger, results))

    def test_gate_recomputes_the_whole_ledger(self):
        ledger = self.ledger()
        ledger["changes"] = []
        self.assertIn(
            "the changed-path ledger is incomplete or different",
            self.audit(ledger, self.results(["genie"])),
        )
        ledger = self.ledger(lanes=["planner"])
        self.assertTrue(
            self.audit(ledger, self.results(["planner"]), recomputed=["genie"])
        )
        docs = self.ledger("docs", [])
        docs["candidate"] = ["genie"]
        self.assertTrue(self.audit(docs, self.results([])))

    def test_gate_rechecks_baseline_and_reuse_proofs(self):
        for mode in ("scoped", "reuse"):
            with self.subTest(mode=mode):
                ledger = self.ledger(mode, [] if mode == "reuse" else ["genie"])
                environment = {
                    "BASE_SHA": "a" * 40,
                    "HEAD_SHA": "b" * 40,
                    "EXPECTED_LEDGER": json.dumps(ledger),
                    "JOB_RESULTS": json.dumps(self.results(ledger["lanes"])),
                }
                with (
                    patch.dict(os.environ, environment),
                    patch.object(
                        ci_scope, "git", return_value=("b" * 40 + "\n").encode()
                    ),
                    patch.object(
                        ci_scope,
                        "diff_changes",
                        return_value=[("M", "services/genie/app.py")],
                    ),
                    patch.object(ci_scope, "audit_gate", return_value=[]),
                    patch.object(ci_scope, "checked_base", return_value=False) as base,
                    patch.object(
                        ci_scope, "checked_pr_tree", return_value=None
                    ) as reuse,
                ):
                    with self.assertRaises(SystemExit):
                        ci_scope.gate()
                self.assertEqual(base.called, mode == "scoped")
                self.assertEqual(reuse.called, mode == "reuse")

    def test_baseline_proof_does_not_inherit_a_scoped_or_reused_run(self):
        run = {
            "status": "completed",
            "conclusion": "success",
            "display_title": "check #1 | tree-ref=" + "a" * 40,
        }
        with (
            patch.object(
                ci_scope,
                "git",
                side_effect=[b"workflow", b"workflow", b"tree", b"tree"] * 3,
            ),
            patch.object(
                ci_scope, "validated_scope", side_effect=["scoped", "scoped", "reuse"]
            ),
        ):
            self.assertFalse(ci_scope.checked_run(run, "a" * 40, full=True))
            self.assertTrue(ci_scope.checked_run(run, "a" * 40))
            self.assertFalse(ci_scope.checked_run(run, "a" * 40, full=True))

    def test_reused_main_commit_traces_back_to_a_full_pr(self):
        reused = {"status": "completed", "conclusion": "success"}
        with (
            patch.object(ci_scope, "latest_run", return_value=reused),
            patch.object(ci_scope, "checked_run", side_effect=[False, False]),
            patch.object(ci_scope, "validated_scope", return_value="reuse"),
            patch.object(ci_scope, "checked_pr_tree", return_value=reused) as original,
        ):
            self.assertTrue(ci_scope.checked_base("a" * 40))
        original.assert_called_once_with("a" * 40, full=True)

    def test_split_jobs_keep_the_shared_toolchain_inputs(self):
        php = TEXT.split("\n  php:\n", 1)[1].split("\n  commerce:\n", 1)[0]
        self.assertIn('cd "$GITHUB_WORKSPACE/plugins/linker-commerce"', php)
        self.assertIn("uses: actions/setup-node@", php)
        self.assertLess(php.index("composer install"), php.index("for project in"))
        self.assertLess(php.index("npm ci"), php.index("for project in"))

        tools = TEXT.split("\n  tools:\n", 1)[1].split("\n  planner:\n", 1)[0]
        self.assertLess(
            tools.index("npx playwright install"), tools.index("npm run test:unit")
        )

        engine = TEXT.split("\n  engine:\n", 1)[1].split("\n  genie:\n", 1)[0]
        self.assertIn("uses: actions/setup-node@", engine)
        self.assertLess(engine.index("npm ci"), engine.index("uv run --locked pytest"))

        python = TEXT.split("\n  python:\n", 1)[1].split("\n  content:\n", 1)[0]
        self.assertLess(
            python.index("apt-get install -y gettext"),
            python.index("Other Python packages and migration contracts"),
        )

    def test_workflow_preserves_native_recovery_and_has_one_real_gate(self):
        self.assertIn("cancel-in-progress: true", TEXT)
        self.assertNotIn("on:\n  pull_request:\n    paths", TEXT)
        self.assertNotIn("if: always()", TEXT)
        for title in (
            "business and native notification capacity in both stores",
            "public verification and atomic admission",
            "inquiry status price gate",
            "proforma price gate",
            "genie inquiry chain",
            "inquiry assessment, customer evidence and staff review",
            "administrator MFA without mandatory customer factors",
        ):
            step = TEXT.split("      - name: " + title + "\n", 1)[1].split(
                "      - name:", 1
            )[0]
            self.assertIn(
                "if: needs.plan.outputs.mode == 'full' || needs.plan.outputs.mode == 'scoped'",
                step,
            )
        for lane in ci_scope.LANES:
            with self.subTest(lane=lane):
                self.assertIn(f"\n  {lane}:\n", TEXT)
                self.assertIn(
                    f"if: ${{{{ !cancelled() && needs.plan.outputs.{lane} == 'true' }}}}",
                    TEXT,
                )
        mail = TEXT.split("      - name: internal SMTP", 1)[1].split(
            "      - name:", 1
        )[0]
        self.assertIn("MessageIdWitnessTest", mail)
        self.assertIn("Browser regression suite's own source checks", TEXT)
        self.assertIn("if: ${{ !cancelled() }}", TEXT)
        self.assertIn("JOB_RESULTS: ${{ toJson(needs) }}", TEXT)


if __name__ == "__main__":
    unittest.main()
