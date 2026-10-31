"""Local contracts for CI selection and the final result gate."""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import ci_scope

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / ".github/workflows/check.yml").read_text()
JUSTFILE = (ROOT / "justfile").read_text()


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
        for path, expected in (
            (
                "includes/Presentation/ProductShortcodes.php",
                ["php", "content", "native"],
            ),
            (
                "includes/Registration/PendingProfileCapacity.php",
                ["php", "content", "native"],
            ),
            ("includes/Storefront/ProductView.php", ["php", "content", "native"]),
            ("assets/account-ui.js", ["php", "js", "build", "native"]),
            ("languages/linker-commerce-de_DE_formal.mo", ["php", "content", "native"]),
            ("tests/php/Integration/RegistrationCapacityTest.php", ["php", "native"]),
            ("tests/js/library-ui.test.mjs", ["php", "js", "build", "native"]),
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    self.classify(("M", "plugins/linker-commerce/" + path)),
                    expected,
                )

    def test_general_php_mu_and_service_changes_do_not_select_unrelated_stacks(self):
        self.assertEqual(
            self.classify(
                ("M", "plugins/linker-commerce/includes/Products/Publication.php"),
                ("M", "mu-plugins/linker-publication-worker-access.php"),
                ("M", "services/engine/src/linker_engine/planning/retention.py"),
                ("M", "services/genie/src/linker_genie/publication.py"),
                ("M", "apps/planner/tests/fixtures/preparation-flow-linux-x86_64.json"),
            ),
            ["php", "content", "native", "planner", "engine", "genie"],
        )

    def test_declared_package_dependencies_and_module_matrices(self):
        cases = (
            (
                "tools/local/src/linker_local/registry.py",
                {"python:local", "python:pull", "python:cutover"},
            ),
            (
                "services/engine/src/linker_engine/assistant_context.py",
                {"engine", "genie"},
            ),
            (
                "services/engine/src/linker_engine/planning/project_input_floor.py",
                {"engine", "python:local"},
            ),
            ("docs/acceptance/2026-10-20/339/case-map.md", {"genie"}),
            (
                "docs/research/2026-10-20-campaign-330/verdicts.jsonl",
                {"genie", "python:harnesses"},
            ),
            (
                "docs/research/2026-10-20-campaign-332/verdicts.jsonl",
                {"python:harnesses"},
            ),
            (
                "docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png",
                {"python:harnesses"},
            ),
            (
                "services/genie/eval/attachments/photos/goodwe-gw10k-et.jpg",
                {"genie", "python:harnesses"},
            ),
            ("services/genie/tests/page_cache_probe.py", {"genie", "native:inquiry"}),
            ("docs/debt/DE-PARITY-2026-10-13.md", {"python:migrate"}),
            (
                "services/engine/tests/fixtures/feed.json",
                {"engine", "genie", "php:commerce", "php:tools"},
            ),
            (
                "plugins/linker-tools/includes/Planner/Gateway.php",
                {
                    "php:tools",
                    "content",
                    "engine",
                    "planner",
                    *["native:" + name for name in ci_scope.NATIVE_GROUPS],
                },
            ),
        )
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(
                    set(ci_scope.selected_modules([("M", path)], "base", "head")),
                    expected,
                )
        modules = ci_scope.selected_modules(
            [
                ("M", "mu-plugins/linker-publication-worker-access.php"),
                ("M", "services/genie/src/linker_genie/publication.py"),
            ],
            "base",
            "head",
        )
        self.assertEqual(ci_scope.module_matrix(modules, "php"), ["mu-plugins"])
        self.assertEqual(ci_scope.module_matrix(modules, "js"), ["none"])
        self.assertEqual(
            ci_scope.module_matrix(modules, "native"), list(ci_scope.NATIVE_GROUPS)
        )
        self.assertEqual(len(ci_scope.FULL_MODULES), len(set(ci_scope.FULL_MODULES)))

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
            ".editorconfig",
            "justfile",
            "tools/build.just",
            "tools/checks/ci_scope.py",
            "tools/checks/test_ci_scope.py",
            "plugins/linker-tools/project-input-contracts.json",
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
            ["php", "js", "build", "native"],
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
            # Local classification reads uncommitted files, including their mode.
            (source / "old.ts").write_text("export const value = 2;\n")
            self.assertEqual(
                ci_scope.classify(ci_scope.diff_changes(base, ""), base, ""),
                ["planner"],
            )
            (source / "old.ts").chmod(0o755)
            self.assertEqual(
                ci_scope.classify(ci_scope.diff_changes(base, ""), base, ""),
                list(ci_scope.FULL_LANES),
            )
            (source / "old.ts").chmod(0o644)
            (source / "old.ts").write_text("export const value = 1;\n")
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
                patch.object(
                    ci_scope,
                    "reusable_modules",
                    side_effect=ValueError("unavailable proof"),
                ),
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
                    self.assertIn("native=true\n", output)
                else:
                    self.assertIn("php=false\n", output)
                    self.assertIn("native=false\n", output)
                    self.assertIn('"reused":{}', output)
                    self.assertIn('python_matrix=["none"]', output)
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
        self.assertIn("native=false\n", output)
        checked.assert_not_called()

    def ledger(self, mode="scoped", lanes=None):
        lanes = ["genie"] if lanes is None else lanes
        return {
            "base": "a" * 40,
            "head": "b" * 40,
            "mode": mode,
            "candidate": lanes if mode == "scoped" else list(ci_scope.FULL_LANES),
            "lanes": lanes,
            "modules": list(ci_scope.FULL_MODULES)
            if mode == "full"
            else ["genie"]
            if mode == "scoped"
            else [],
            "reused": {},
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
        failed = self.ledger("full", list(ci_scope.FULL_LANES))
        failed["error"] = "diff --check failed"
        self.assertIn(
            "plan could not prove the complete diff: diff --check failed",
            self.audit(failed, self.results(ci_scope.FULL_LANES)),
        )

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

    def test_reused_main_commit_traces_to_a_validated_scoped_pr(self):
        reused = {"status": "completed", "conclusion": "success"}
        with (
            patch.object(ci_scope, "latest_run", return_value=reused),
            patch.object(ci_scope, "checked_run", side_effect=[False, False]),
            patch.object(ci_scope, "validated_scope", side_effect=["reuse", "scoped"]),
            patch.object(ci_scope, "checked_pr_tree", return_value=reused) as original,
        ):
            self.assertTrue(ci_scope.checked_base("a" * 40))
        original.assert_called_once_with("a" * 40)

    def test_whitespace_failure_stops_before_selecting_lanes(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            output.write_text("")
            environment = {
                "EVENT_NAME": "pull_request",
                "HEAD_SHA": "b" * 40,
                "BASE_SHA": "a" * 40,
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(Path(folder) / "summary"),
            }
            with (
                patch.dict(os.environ, environment),
                patch.object(ci_scope, "git", return_value=b""),
                patch(
                    "subprocess.run", return_value=subprocess.CompletedProcess([], 1)
                ),
            ):
                with self.assertRaises(SystemExit):
                    ci_scope.plan()
            self.assertEqual(output.read_text(), "")

    def test_squash_merge_and_merge_commit_find_the_pr_head(self):
        commit = "a" * 40
        source = "b" * 40
        run = {"id": 1}
        with (
            patch.object(ci_scope, "latest_run", return_value=run),
            patch.object(ci_scope, "checked_run", return_value=True),
            patch.object(
                ci_scope,
                "git",
                return_value=f"{commit} {'c' * 40} {source}\n".encode(),
            ),
        ):
            self.assertIs(ci_scope.checked_pr_tree(commit), run)
        with (
            patch.object(ci_scope, "git", return_value=f"{commit}\n".encode()),
            patch.dict(os.environ, {"REPOSITORY": "owner/repo"}),
            patch.object(
                ci_scope,
                "api",
                return_value=[
                    {"merge_commit_sha": "d" * 40, "head": {"sha": "e" * 40}},
                    {"merge_commit_sha": commit, "head": {"sha": source}},
                ],
            ),
            patch.object(ci_scope, "latest_run", return_value=run),
            patch.object(ci_scope, "checked_run", return_value=True),
        ):
            self.assertIs(ci_scope.checked_pr_tree(commit), run)

    def test_split_jobs_keep_the_shared_toolchain_inputs(self):
        php = TEXT.split("\n  php:\n", 1)[1].split("\n  js:\n", 1)[0]
        self.assertIn('just ci-php-package "${{ matrix.project }}"', php)
        self.assertIn("fromJson(needs.plan.outputs.php_matrix)", php)
        js = TEXT.split("\n  js:\n", 1)[1].split("\n  python:\n", 1)[0]
        self.assertLess(
            js.index("npx playwright install"), js.index("just ci-js-package")
        )
        engine = TEXT.split("\n  engine:\n", 1)[1].split("\n  genie:\n", 1)[0]
        self.assertIn("uses: actions/setup-node@", engine)
        self.assertIn("run: just ci-engine", engine)
        self.assertIn("ci-engine: ci-planner-deps", JUSTFILE)
        self.assertIn("uv run --locked pytest", JUSTFILE)
        python = TEXT.split("\n  python:\n", 1)[1].split("\n  content:\n", 1)[0]
        self.assertLess(
            python.index("Python unit native helpers"),
            python.index("Validate module"),
        )

    def test_javascript_installs_browser_before_browser_backed_unit_tests(self):
        # Empty browser state plus command shims exercises the actual just recipe.
        # The fixture owns all files/processes until TemporaryDirectory exits.
        with TemporaryDirectory() as folder:
            fixture = Path(folder)
            runner = fixture / "runner"
            runner.write_text(
                f"#!{sys.executable}\n"
                "import os,sys\nfrom pathlib import Path\n"
                "name=Path(sys.argv[0]).name\n"
                "marker=Path(os.environ['BROWSER_MARKER'])\n"
                "if name == 'npx' and sys.argv[1:] == ['playwright','install','--only-shell','chromium']:\n"
                "    marker.touch()\n"
                "if name == 'npm' and sys.argv[1:] == ['run','test:unit'] and not marker.exists():\n"
                "    sys.exit('browser-backed unit test ran before Chromium installation')\n"
            )
            runner.chmod(0o755)
            for name in ("npm", "npx", "node"):
                (fixture / name).symlink_to(runner)
            just = shutil.which("just")
            assert just is not None
            result = subprocess.run(
                [just, "--justfile", str(ROOT / "justfile"), "js-test"],
                env={
                    **os.environ,
                    "PATH": str(fixture) + os.pathsep + os.environ["PATH"],
                    "BROWSER_MARKER": str(fixture / "installed"),
                },
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((fixture / "installed").exists())

    def test_workflow_preserves_native_recovery_and_has_one_real_gate(self):
        self.assertIn("cancel-in-progress: true", TEXT)
        self.assertNotIn("on:\n  pull_request:\n    paths", TEXT)
        self.assertEqual(TEXT.count("if: always()"), 1)
        self.assertIn("group: ${{ fromJson(needs.plan.outputs.native_matrix) }}", TEXT)
        self.assertNotIn("fail-fast: true", TEXT)
        self.assertIn("pytest --durations=10", JUSTFILE)
        self.assertIn("PublicationPreparationRecipeTest", JUSTFILE)
        self.assertIn('just ci-native "${{ matrix.group }}" smoke', TEXT)
        self.assertNotIn("/Justfile", JUSTFILE)
        self.assertIn('export PHP="{{ php }}"', JUSTFILE)
        self.assertEqual(
            JUSTFILE.count(
                'just --justfile "$root/justfile" wp "$name" '
                "linker-i18n setup --user=local-admin"
            ),
            1,
        )
        self.assertRegex(
            JUSTFILE,
            r"(?s)ensure_i18n\(\) \{.*?linker-i18n setup --user=local-admin"
            r".*?\n    ensure_i18n\n    case \"\$groups\"",
        )
        for marker in (
            "run_mail()",
            "GlobalBusinessCapacityTest",
            "run_inquiry()",
            "PublicAdmissionOwnersTest",
            "ProformaPriceGateTest",
            "GenieInquiryTest",
            "InquiryAssessmentTest",
            "MessageIdWitnessTest",
            "run_admin()",
            "admin-mfa",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, JUSTFILE)
        for lane in ci_scope.LANES:
            with self.subTest(lane=lane):
                self.assertIn(f"\n  {lane}:\n", TEXT)
                self.assertIn(
                    f"if: ${{{{ !cancelled() && needs.plan.outputs.{lane} == 'true' }}}}",
                    TEXT,
                )
        self.assertIn("if: ${{ !cancelled() }}", TEXT)
        self.assertIn("JOB_RESULTS: ${{ toJson(needs) }}", TEXT)
        self.assertTrue(
            set(ci_scope.FULL_LANES).isdisjoint({"presentation", "commerce"})
        )


class ModuleReuseTest(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(
            os.environ,
            {
                "REPOSITORY": "owner/repo",
                "PR_NUMBER": "820",
                "EVENT_NAME": "pull_request",
                "HEAD_SHA": "b" * 40,
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.prior_run = {
            "id": 10,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "failure",
            "path": ci_scope.WORKFLOW,
            "event": "pull_request",
            "head_sha": "a" * 40,
            "display_title": "check #820 | tree-ref=" + "c" * 40,
            "pull_requests": [{"number": 820}],
        }
        self.job = {
            "id": 20,
            "name": "engine",
            "conclusion": "success",
            "steps": [{"name": "Validate module", "conclusion": "success"}],
        }

    def api(self, endpoint):
        if "workflows/check.yml/runs?" in endpoint:
            self.assertIn("per_page=10", endpoint)
            return {"workflow_runs": [self.prior_run]}
        if "/attempts/" in endpoint:
            return {"total_count": 1, "jobs": [self.job]}
        return self.prior_run

    def test_successful_independent_module_is_reused_and_gate_rechecks_it(self):
        with (
            patch.object(ci_scope, "api", side_effect=self.api) as api,
            patch.object(ci_scope, "same_module_inputs", return_value=True),
            patch.object(ci_scope, "module_fingerprint", return_value="f" * 64),
        ):
            proof = ci_scope.reusable_modules(["engine", "genie"], "b" * 40)
            self.assertEqual(set(proof), {"engine"})
            self.assertTrue(
                ci_scope.validate_module_reuse(proof, ["engine", "genie"], "b" * 40)
            )
            self.assertEqual(
                sum(
                    "/actions/runs/10" in call.args[0]
                    and "/attempts/" not in call.args[0]
                    for call in api.call_args_list
                ),
                1,
            )
            self.job["conclusion"] = "cancelled"
            self.assertFalse(
                ci_scope.validate_module_reuse(proof, ["engine", "genie"], "b" * 40)
            )

    def test_diff_guarded_recipe_cannot_reuse_only_a_source_tree_proof(self):
        self.job["name"] = "planner"
        with (
            patch.object(ci_scope, "api", side_effect=self.api),
            patch.object(ci_scope, "same_module_inputs", return_value=True),
            patch.object(ci_scope, "module_fingerprint", return_value="f" * 64),
        ):
            self.assertEqual(ci_scope.reusable_modules(["planner"], "b" * 40), {})
            self.assertFalse(
                ci_scope.validate_module_reuse({"planner": {}}, ["planner"], "b" * 40)
            )

    def test_gate_rejects_forged_attempt_input_job_and_module_proofs(self):
        proof = {
            "engine": {
                "run": 10,
                "attempt": 1,
                "job": 20,
                "commit": "c" * 40,
                "inputs": "f" * 64,
            }
        }
        for key, value in (
            ("attempt", 2),
            ("job", 21),
            ("commit", "d" * 40),
            ("inputs", "e" * 64),
        ):
            with (
                self.subTest(key=key),
                patch.object(ci_scope, "api", side_effect=self.api),
                patch.object(ci_scope, "same_module_inputs", return_value=True),
                patch.object(ci_scope, "module_fingerprint", return_value="f" * 64),
            ):
                altered = {"engine": {**proof["engine"], key: value}}
                self.assertFalse(
                    ci_scope.validate_module_reuse(altered, ["engine"], "b" * 40)
                )
        self.assertFalse(ci_scope.validate_module_reuse(proof, ["genie"], "b" * 40))

    def test_failed_skipped_missing_or_changed_inputs_never_supply_success(self):
        for mutation in (
            "failure",
            "cancelled",
            "skipped",
            "missing step",
            "different PR",
            "different workflow",
            "changed inputs",
        ):
            with self.subTest(mutation=mutation):
                job, run = dict(self.job), dict(self.prior_run)
                if mutation in {"failure", "cancelled", "skipped"}:
                    job["conclusion"] = mutation
                elif mutation == "missing step":
                    job["steps"] = []
                elif mutation == "different PR":
                    run["pull_requests"] = [{"number": 821}]
                elif mutation == "different workflow":
                    run["path"] = ".github/workflows/other.yml"
                with (
                    patch.object(
                        ci_scope,
                        "api",
                        side_effect=[
                            {"workflow_runs": [run]},
                            {"total_count": 1, "jobs": [job]},
                        ],
                    ),
                    patch.object(
                        ci_scope,
                        "same_module_inputs",
                        return_value=mutation != "changed inputs",
                    ),
                    patch.object(ci_scope, "module_fingerprint", return_value="f" * 64),
                ):
                    self.assertEqual(
                        ci_scope.reusable_modules(["engine"], "b" * 40), {}
                    )
        with patch.object(
            ci_scope, "api", return_value={"total_count": 101, "jobs": [self.job]}
        ):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                ci_scope.run_module_jobs(self.prior_run)

    def test_real_git_input_hash_preserves_unrelated_service_but_invalidates_consumed_inputs(
        self,
    ):
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
            for name in (
                ci_scope.WORKFLOW,
                "services/engine/uv.lock",
                "services/genie/app.py",
                "plugins/linker-commerce/data/compatibility.json",
                "docs/acceptance/2026-10-31/548/INDEX.md",
            ):
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original")
            run("git", "add", ".")
            run("git", "commit", "-qm", "base")
            base = run("git", "rev-parse", "HEAD")
            originals = {
                module: ci_scope.module_fingerprint(base, module)
                for module in ("php:commerce", "engine", "genie", "python:harnesses")
            }
            record = repo / "docs/acceptance/2026-10-31/548/INDEX.md"
            record.write_text(record.read_text() + "\nadditional acceptance evidence")
            run("git", "add", ".")
            run("git", "commit", "-qm", "record only")
            report_head = run("git", "rev-parse", "HEAD")
            for module, original in originals.items():
                self.assertEqual(
                    ci_scope.module_fingerprint(report_head, module), original, module
                )
            run("git", "reset", "--hard", base)
            for name, changed in (
                ("services/genie/app.py", {"genie"}),
                (
                    "plugins/linker-commerce/data/compatibility.json",
                    {"php:commerce", "engine"},
                ),
                (ci_scope.WORKFLOW, set(originals)),
                (".editorconfig", set(originals)),
                ("services/engine/uv.lock", {"engine"}),
                (
                    "docs/research/2026-10-23-pv-inputs/raw/era5-berlin-2020.seriescalc.json",
                    {"engine"},
                ),
                ("docs/acceptance/2026-10-20/339/case-map.md", {"genie"}),
                (
                    "docs/research/2026-10-20-campaign-330/verdicts.jsonl",
                    {"genie", "python:harnesses"},
                ),
                (
                    "docs/research/2026-10-20-campaign-332/verdicts.jsonl",
                    {"python:harnesses"},
                ),
                (
                    "services/genie/tests/page_cache_probe.py",
                    {"genie", "native:inquiry"},
                ),
                (
                    "docs/research/2026-10-17-deepseek-flash-vision/raw/datasheet-probe.pdf",
                    {"genie"},
                ),
                (
                    "plugins/linker-commerce/content/livecanvas/home.html",
                    {"php:commerce"},
                ),
                (
                    "docs/research/2026-10-20-campaign-330/verdicts.jsonl",
                    {"genie", "python:harnesses"},
                ),
                (
                    "docs/research/2026-10-20-campaign-332/verdicts.jsonl",
                    {"python:harnesses"},
                ),
                (
                    "docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png",
                    {"python:harnesses"},
                ),
                (
                    "services/genie/eval/attachments/photos/goodwe-gw10k-et.jpg",
                    {"genie", "python:harnesses"},
                ),
                ("AGENTS.md", set()),
                ("CONTEXT.md", set()),
                ("docs/research/unrelated-notes.md", set()),
            ):
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("changed")
                run("git", "add", ".")
                run("git", "commit", "-qm", "input")
                head = run("git", "rev-parse", "HEAD")
                for module, original in originals.items():
                    with self.subTest(path=name, module=module):
                        self.assertEqual(
                            ci_scope.module_fingerprint(head, module) != original,
                            module in changed,
                        )
                run("git", "reset", "--hard", base)


if __name__ == "__main__":
    unittest.main()
