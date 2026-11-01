"""Local contracts for CI selection and the final result gate."""

import hashlib
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
        native = {"native:" + name for name in ci_scope.NATIVE_GROUPS}
        planner_gateway = {"php:tools", "content", "engine", "planner", *native}
        cases = (
            (
                "tools/local/src/linker_local/registry.py",
                {"content", "python:local", "python:pull", "python:cutover", *native},
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
            ("plugins/linker-tools/includes/Planner/Gateway.php", planner_gateway),
            ("plugins/linker-tools/includes/Planner/Transport.php", planner_gateway),
            (
                "plugins/linker-tools/includes/Planner/ClaimOutbox.php",
                {"php:tools", "content", *native},
            ),
            (
                "plugins/linker-tools/tests/php/Unit/PlannerClaimOutboxTest.php",
                {"php:tools", *native},
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
            self.classify(("A", "apps/planner/src/domain/new.ts")),
            ["planner", "engine"],
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

        outbox = [
            ("M", "plugins/linker-tools/includes/Planner/ClaimOutbox.php"),
            ("M", "plugins/linker-tools/tests/php/Unit/PlannerClaimOutboxTest.php"),
            ("M", "docs/acceptance/2026-10-31/548/INDEX.md"),
        ]
        engine = ("M", "services/engine/src/linker_engine/planning/guest_claims.py")
        planner = ("M", "apps/planner/src/data/client.ts")
        for additional, expected in (
            ([], ["php", "content", "native"]),
            ([engine], ["php", "content", "native", "engine"]),
            ([planner], ["php", "content", "native", "planner", "engine"]),
            ([engine, planner], ["php", "content", "native", "planner", "engine"]),
        ):
            with self.subTest(additional=additional):
                self.assertEqual(self.classify(*outbox, *additional), expected)

    def test_shared_browser_contracts_select_the_actual_engine_consumer(self):
        # Engine's native schema parity and energy/equipment contracts open
        # these browser inputs directly, including pre-existing non-solar files.
        for path in (
            "apps/planner/src/contracts/profile-import.schema.json",
            "apps/planner/src/contracts/geometry-policy.json",
            "apps/planner/tests/fixtures/energy-invalid.json",
            "apps/planner/tests/fixtures/dc-energy-run.json",
            "apps/planner/tests/fixtures/preparation-flow-linux-x86_64.json",
            "apps/planner/src/domain/solarSetup.ts",
            "apps/planner/src/domain/draft.ts",
            "apps/planner/src/data/readProtocol.ts",
            "apps/planner/package-lock.json",
            "apps/planner/bin/echarts-types.mjs",
        ):
            for status in ("A", "M", "D"):
                with self.subTest(path=path, status=status):
                    changes = [(status, path)]
                    self.assertEqual(self.classify(*changes), ["planner", "engine"])
                    self.assertEqual(
                        ci_scope.selected_modules(changes, "base", "head"),
                        ["planner", "engine"],
                    )
        # Component and standalone frontend tests are not Engine inputs.
        self.assertEqual(
            self.classify(("M", "apps/planner/src/components/ReportView.tsx")),
            ["planner"],
        )
        self.assertEqual(
            self.classify(("M", "apps/planner/src/domain/draft.test.ts")),
            ["planner"],
        )
        self.assertEqual(
            self.classify(("M", "apps/planner/src/data/client.test.ts")),
            ["planner"],
        )

    def test_cross_service_sources_select_their_actual_consumers(self):
        for path in (
            "plugins/linker-commerce/includes/Abilities/SearchProducts.php",
            "plugins/linker-commerce/includes/Products/SelectionFacts.php",
        ):
            with self.subTest(path=path):
                self.assertIn("genie", ci_scope.selected_modules([("M", path)]))
        path = "plugins/linker-tools/src/configurator/schema/roof.schema.json"
        self.assertIn("engine", ci_scope.selected_modules([("M", path)]))
        path = "plugins/linker-tools/src/genie/attachments/prepare.ts"
        self.assertIn("genie", ci_scope.selected_modules([("M", path)]))
        path = "plugins/linker-commerce/includes/Account/AuthTemplates.php"
        self.assertNotIn("genie", ci_scope.selected_modules([("M", path)]))

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
            for known in (
                "apps/planner/src/App.tsx",
                "plugins/linker-tools/includes/Planner/ClaimOutbox.php",
            ):
                with self.subTest(path=path, known=known):
                    self.assertEqual(
                        self.classify(("M", known), ("M", path)),
                        list(ci_scope.FULL_LANES),
                    )
        for status in ("R100", "C100", "T", "U"):
            for path in (
                "apps/planner/src/App.tsx",
                "plugins/linker-tools/includes/Planner/ClaimOutbox.php",
            ):
                with self.subTest(status=status, path=path):
                    self.assertEqual(
                        self.classify((status, path)), list(ci_scope.FULL_LANES)
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
        with (
            patch.object(
                ci_scope,
                "git",
                side_effect=[json.dumps(before).encode(), json.dumps(after).encode()],
            ),
            patch.object(ci_scope, "tools_manifest_matches_changes", return_value=True),
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

    def test_tools_manifest_matches_real_changed_files_and_remains_conservative(self):
        self.regular.stop()
        self.non_runtime.stop()
        with TemporaryDirectory() as folder:
            previous = Path.cwd()
            try:
                os.chdir(folder)

                def run(*args):
                    return subprocess.check_output(args, text=True).strip()

                def write(path, content):
                    file = Path(path)
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text(content)

                def manifest():
                    root = Path("plugins/linker-tools")
                    sources = (
                        "package.json",
                        "package-lock.json",
                        "webpack.config.js",
                        "bin/build.cjs",
                        "project-input-contracts.json",
                        *(
                            path.relative_to(root).as_posix()
                            for path in sorted((root / "src").rglob("*"))
                            if path.is_file()
                        ),
                    )
                    build = ("build/genie.js", "build/planner/index.js")
                    return {
                        section: {
                            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                            for name in names
                        }
                        for section, names in (("sources", sources), ("build", build))
                    }

                def commit(message):
                    run("git", "add", ".")
                    run("git", "commit", "-qm", message)
                    return run("git", "rev-parse", "HEAD")

                run("git", "init", "-q")
                run("git", "config", "user.email", "ci@example.invalid")
                run("git", "config", "user.name", "CI fixture")
                prefix = "plugins/linker-tools/"
                for name in (
                    "package.json",
                    "package-lock.json",
                    "webpack.config.js",
                    "bin/build.cjs",
                    "project-input-contracts.json",
                    "src/genie/App.tsx",
                    "src/genie/Legacy.tsx",
                    "build/genie.js",
                    "build/planner/index.js",
                ):
                    write(prefix + name, "base " + name)
                write("justfile", "base")
                write("apps/planner/src/App.tsx", "planner base")
                write(prefix + "build/manifest.json", json.dumps(manifest()))
                base = commit("base")

                write(prefix + "src/genie/App.tsx", "changed source")
                Path(prefix + "src/genie/Legacy.tsx").unlink()
                write(prefix + "src/genie/Fresh.tsx", "brand new content")
                write(prefix + "build/genie.js", "changed built output")
                write(prefix + "build/manifest.json", json.dumps(manifest()))
                head = commit("tools source and build")
                changes = ci_scope.diff_changes(base, head)
                self.assertTrue(
                    ci_scope.tools_manifest_matches_changes(changes, base, head)
                )
                modules = ci_scope.selected_modules(changes, base, head)
                self.assertEqual(
                    set(modules),
                    {"php:tools", "js:tools", "build:tools", "genie"}
                    | {"native:" + name for name in ci_scope.NATIVE_GROUPS},
                )
                self.assertNotIn("engine", modules)
                self.assertEqual(
                    ci_scope.module_fingerprint(base, "engine"),
                    ci_scope.module_fingerprint(head, "engine"),
                )
                self.assertEqual(
                    ci_scope.classify(changes + [("M", "justfile")], base, head),
                    list(ci_scope.FULL_LANES),
                )

                # Planner-only builds retain their existing narrow path.
                write("apps/planner/src/App.tsx", "planner source changed")
                write(prefix + "build/planner/index.js", "planner output changed")
                write(prefix + "build/manifest.json", json.dumps(manifest()))
                planner_only = ci_scope.diff_changes(head, "")
                self.assertEqual(ci_scope.classify(planner_only, head, ""), ["planner"])
                planner_head = commit("planner only")

                # A Planner source change does not authorize a forged manifest
                # digest for an unchanged Planner output.
                write("apps/planner/src/App.tsx", "planner source only")
                fabricated = manifest()
                fabricated["build"]["build/planner/index.js"] = "0" * 64
                write(prefix + "build/manifest.json", json.dumps(fabricated))
                self.assertEqual(
                    ci_scope.classify(
                        ci_scope.diff_changes(planner_head, ""), planner_head, ""
                    ),
                    list(ci_scope.FULL_LANES),
                )

                # A Planner output and a separately changed Tools source are
                # checked together, including in the local worktree preflight.
                write("apps/planner/src/App.tsx", "another planner source change")
                write(prefix + "build/planner/index.js", "another planner output")
                write(prefix + "src/genie/App.tsx", "second source change")
                write(prefix + "build/genie.js", "second built output")
                write(prefix + "build/manifest.json", json.dumps(manifest()))
                local = ci_scope.diff_changes(planner_head, "")
                local_modules = ci_scope.selected_modules(local, planner_head, "")
                self.assertIn("planner", local_modules)
                self.assertIn("build:tools", local_modules)
                self.assertNotIn("engine", local_modules)
                planner_mixed = commit("planner and tools")
                self.assertEqual(
                    ci_scope.selected_modules(
                        ci_scope.diff_changes(planner_head, planner_mixed),
                        planner_head,
                        planner_mixed,
                    ),
                    local_modules,
                )

                # An unrelated known consumer still enters the union.
                write("services/engine/src/linker_engine/example.py", "engine input")
                mixed = commit("mixed engine input")
                mixed_changes = ci_scope.diff_changes(base, mixed)
                self.assertIn(
                    "engine", ci_scope.selected_modules(mixed_changes, base, mixed)
                )

                source_path = Path(prefix + "src/genie/App.tsx")
                build_path = Path(prefix + "build/genie.js")
                manifest_path = Path(prefix + "build/manifest.json")
                original_source = source_path.read_text()
                original_build = build_path.read_text()
                original_manifest = manifest_path.read_text()
                write(str(source_path), "changed without updating its manifest")
                write(str(build_path), "changed with an updated manifest")
                incorrect = manifest()
                incorrect["sources"]["src/genie/App.tsx"] = json.loads(
                    original_manifest
                )["sources"]["src/genie/App.tsx"]
                for bad_digest in (incorrect["sources"]["src/genie/App.tsx"], "0" * 64):
                    incorrect["sources"]["src/genie/App.tsx"] = bad_digest
                    write(str(manifest_path), json.dumps(incorrect))
                    self.assertEqual(
                        ci_scope.classify(ci_scope.diff_changes(mixed, ""), mixed, ""),
                        list(ci_scope.FULL_LANES),
                    )
                write(str(source_path), original_source)
                write(str(build_path), original_build)
                write(str(manifest_path), original_manifest)

                write("unclassified/new.py", "unknown input")
                unknown_changes = ci_scope.diff_changes(base, "") + [
                    ("A", "unclassified/new.py")
                ]
                self.assertEqual(
                    ci_scope.classify(unknown_changes, base, ""),
                    list(ci_scope.FULL_LANES),
                )
                Path("unclassified/new.py").unlink()

                # A changed digest with no corresponding file change cannot be
                # hidden by a separately legitimate source/build change.
                forged = manifest()
                forged["sources"]["package.json"] = "f" * 64
                write(prefix + "build/manifest.json", json.dumps(forged))
                bad = commit("forged manifest")
                self.assertEqual(
                    ci_scope.classify(ci_scope.diff_changes(mixed, bad), mixed, bad),
                    list(ci_scope.FULL_LANES),
                )
                self.assertEqual(
                    ci_scope.classify(ci_scope.diff_changes(base, bad), base, bad),
                    list(ci_scope.FULL_LANES),
                )

                write(
                    prefix + "build/manifest.json",
                    '{"sources":{},"sources":{},"build":{}}',
                )
                invalid = commit("invalid duplicate manifest")
                self.assertEqual(
                    ci_scope.classify(
                        ci_scope.diff_changes(bad, invalid), bad, invalid
                    ),
                    list(ci_scope.FULL_LANES),
                )
            finally:
                os.chdir(previous)

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

    def test_planner_chunk_hash_rotation_retains_both_checked_paths(self):
        source = "plugins/linker-tools/build/planner/assets/"
        old = source + "planner-core-12A4_bC0.js"
        new = source + "planner-core-78x0Y-z1.js"

        def detected(destination, status="R099"):
            records = [["D", old, "A", destination], [status, old, destination]]
            with patch.object(
                ci_scope,
                "git",
                side_effect=[("\0".join(row) + "\0").encode() for row in records],
            ):
                return ci_scope.diff_changes("base", "head")

        self.assertEqual(detected(new), [("D", old), ("A", new)])
        self.assertEqual(self.classify(*detected(new)), ["planner"])
        for result in (
            detected(source + "different-78x0Y-z1.js"),
            detected("apps/planner/src/planner-core-78x0Y-z1.js"),
            detected(new, "C099"),
        ):
            self.assertEqual(self.classify(*result), list(ci_scope.FULL_LANES))
        self.assertEqual(
            set(ci_scope.selected_modules([("M", ci_scope.COMMERCE_COMPATIBILITY)])),
            {
                "engine",
                "content",
                "python:migrate",
                "php:commerce",
                "php:tools",
                *("native:" + group for group in ci_scope.NATIVE_GROUPS),
            },
        )

    def test_reviewed_cable_adoption_input_selects_its_native_consumer(self):
        self.assertEqual(
            set(ci_scope.selected_modules([("A", ci_scope.CABLE_ADOPTION)])),
            {"php:commerce", "content"},
        )
        self.assertIsNone(
            ci_scope.selected_modules(
                [("A", "plugins/linker-commerce/data/unknown.json")]
            )
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

    def run_plan(self, event, candidate, proven=True, reused=None):
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
                    **(
                        {"side_effect": ValueError("unavailable proof")}
                        if reused is None
                        else {"return_value": reused}
                    ),
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

    def test_full_candidate_keeps_all_required_modules_while_reusing_proven_success(
        self,
    ):
        proof = {
            "engine": {
                "run": 10,
                "attempt": 1,
                "job": 20,
                "commit": "c" * 40,
                "inputs": "f" * 64,
            }
        }
        output, _ = self.run_plan(
            "pull_request", list(ci_scope.FULL_LANES), reused=proof
        )
        ledger = json.loads(
            next(
                line.removeprefix("ledger=")
                for line in output.splitlines()
                if line.startswith("ledger=")
            )
        )
        self.assertEqual(ledger["mode"], "full")
        self.assertEqual(ledger["modules"], list(ci_scope.FULL_MODULES))
        self.assertEqual(ledger["reused"], proof)
        self.assertNotIn("engine", ledger["lanes"])
        self.assertEqual(self.audit(ledger, self.results(ledger["lanes"])), [])

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
        self.assertIn("run: just ci-service-check engine", engine)
        self.assertIn("run: just ci-service-test engine", engine)
        self.assertIn("ci-engine: ci-planner-deps", JUSTFILE)
        self.assertIn("uv run --locked pytest", JUSTFILE)
        python = TEXT.split("\n  python:\n", 1)[1].split("\n  content:\n", 1)[0]
        self.assertLess(
            python.index("Python unit native helpers"),
            python.index("Validate module"),
        )

    def test_visible_phases_match_workflow_and_planner_typechecks_once(self):
        for module, checks in (
            ("engine", ("ci-service-check engine", "ci-service-test engine")),
            ("genie", ("ci-service-check genie", "ci-service-test genie")),
            ("planner", ("ci-planner-check", "ci-planner-test", "ci-planner-build")),
        ):
            section = TEXT.split(f"\n  {module}:\n", 1)[1].split("\n\n  ", 1)[0]
            for phase, recipe in zip(("Check", "Test", "Build"), checks, strict=False):
                self.assertIn(f"- name: {phase}\n        run: just {recipe}", section)
            self.assertNotIn("Validate module", section)
        self.assertIn("tools/checks/ci_phase.sh", ci_scope.CONTROL_INPUTS)
        # Real recipes, synthetic commands: no dependency install/build/test replay.
        # TemporaryDirectory owns and removes all shims, command log and children.
        with TemporaryDirectory() as folder:
            fixture = Path(folder)
            runner = fixture / "runner"
            runner.write_text(
                f"#!{sys.executable}\n"
                "import json,os,subprocess,sys\nfrom pathlib import Path\n"
                "name=Path(sys.argv[0]).name\n"
                "args=sys.argv[1:]\n"
                "with Path(os.environ['COMMAND_LOG']).open('a') as log:\n"
                "    log.write(json.dumps([name,*args])+'\\n')\n"
                "if os.environ.get('FAIL_CHECK') == 'true' and (name == 'tsc' or (name == 'uv' and 'mypy' in args)):\n"
                "    sys.exit(17)\n"
                "if name == 'npm' and args[:1] == ['run']:\n"
                "    script=json.loads(Path('package.json').read_text())['scripts'][args[1]]\n"
                "    sys.exit(subprocess.call(['bash','-euo','pipefail','-c',script]))\n"
            )
            runner.chmod(0o755)
            for name in ("npm", "node", "tsc", "vite", "prettier", "git", "uv"):
                (fixture / name).symlink_to(runner)
            log = fixture / "commands.jsonl"
            environment = {
                **os.environ,
                "PATH": str(fixture) + os.pathsep + os.environ["PATH"],
                "COMMAND_LOG": str(log),
                "PLANNER_BUILD_CHANGED": "false",
            }
            just = shutil.which("just")
            assert just is not None
            for module in ("planner", "engine", "genie"):
                for fail in (False, True):
                    with self.subTest(module=module, fail=fail):
                        log.write_text("")
                        result = subprocess.run(
                            [
                                just,
                                "--justfile",
                                str(ROOT / "justfile"),
                                "ci-" + module,
                            ],
                            env={**environment, "FAIL_CHECK": str(fail).lower()},
                            capture_output=True,
                            text=True,
                            timeout=30,
                            check=False,
                        )
                        commands = [
                            json.loads(line) for line in log.read_text().splitlines()
                        ]
                        self.assertEqual(
                            result.returncode == 0,
                            not fail,
                            result.stdout + result.stderr,
                        )
                        output = result.stdout + result.stderr
                        self.assertIn("Check: started", output)
                        self.assertRegex(output, r"Check: (passed|failed) \(\d+s")
                        if fail:
                            self.assertNotIn(["npm", "test"], commands)
                            self.assertNotIn(["npm", "run", "build:assets"], commands)
                            self.assertFalse(
                                any(
                                    command[0] == "uv" and "pytest" in command
                                    for command in commands
                                )
                            )
                            self.assertIn(
                                "npm run lint:types"
                                if module == "planner"
                                else "uv run --locked mypy .",
                                output,
                            )
                        elif module == "planner":
                            self.assertEqual(commands.count(["tsc", "--noEmit"]), 1)
                            self.assertIn(["npm", "run", "build:assets"], commands)
                        else:
                            self.assertIn(
                                ["uv", "run", "--locked", "pytest", "--durations=10"],
                                commands,
                            )
            log.write_text("")
            result = subprocess.run(
                [str(fixture / "npm"), "run", "build"],
                cwd=ROOT / "apps/planner",
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(commands.count(["tsc", "--noEmit"]), 1)
            self.assertIn(["vite", "build"], commands)

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

    def test_tools_php_prepares_its_node_reader_dependencies(self):
        # Run the actual package/dependency recipes with command shims. They
        # own only this marker; no existing vendor/node_modules is changed.
        with TemporaryDirectory() as folder:
            fixture = Path(folder)
            marker = fixture / "tools-node-ready"
            real_just = shutil.which("just")
            assert real_just is not None
            php = fixture / "php"
            php.write_text(
                f"#!{sys.executable}\n"
                "import os,sys\nfrom pathlib import Path\n"
                "if sys.argv[1:] == ['vendor/bin/phpunit'] and Path.cwd().name == 'linker-tools':\n"
                "    if not Path(os.environ['TOOLS_NODE_READY']).exists():\n"
                "        sys.exit('PHP loader contract ran before Tools Node dependencies')\n"
            )
            php.chmod(0o755)
            just = fixture / "just"
            just.write_text(
                f"#!{sys.executable}\n"
                "import os,sys\nfrom pathlib import Path\n"
                "if 'ci-node-deps' in sys.argv:\n"
                "    assert sys.argv[-1] == 'plugins/linker-tools'\n"
                "    Path(os.environ['TOOLS_NODE_READY']).touch()\n"
                "else:\n"
                "    os.execv(os.environ['REAL_JUST'], [os.environ['REAL_JUST'], *sys.argv[1:]])\n"
            )
            just.chmod(0o755)
            result = subprocess.run(
                [
                    real_just,
                    "--justfile",
                    str(ROOT / "justfile"),
                    "ci-php-package",
                    "plugins/linker-tools",
                ],
                env={
                    **os.environ,
                    "PHP": str(php),
                    "PATH": str(fixture) + os.pathsep + os.environ["PATH"],
                    "REAL_JUST": real_just,
                    "TOOLS_NODE_READY": str(marker),
                    "LINKER_CI_PHP_READY": "false",
                },
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(marker.exists())

    def test_repeated_node_prepare_preserves_active_reader_dependencies(self):
        # PHP and JS use this same installer in one local checkout. Redirect
        # only its rendered root into an owned empty fixture; never move deps.
        real_just = shutil.which("just")
        assert real_just is not None
        rendered = subprocess.run(
            [
                real_just,
                "--justfile",
                str(ROOT / "justfile"),
                "--dry-run",
                "ci-node-deps",
                "plugins/linker-tools",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        with TemporaryDirectory() as folder:
            fixture = Path(folder)
            project = fixture / "plugins/linker-tools"
            project.mkdir(parents=True)
            (project / "package.json").write_text("{}")
            (project / "package-lock.json").write_text("{}")
            npm = fixture / "npm"
            npm.write_text(
                f"#!{sys.executable}\n"
                "import os,sys\nfrom pathlib import Path\n"
                "root=Path(os.environ['NODE_FIXTURE'])\n"
                "if (root/'reader-active').exists(): sys.exit('npm ci would replace active PHP dependencies')\n"
                "(root/'installed-once').touch()\n"
                "Path('node_modules').mkdir()\n"
                "Path('node_modules/.package-lock.json').write_text('{}')\n"
                "Path('node_modules/reader-input').write_text('preserved')\n"
            )
            npm.chmod(0o755)
            environment = {
                **os.environ,
                "PATH": str(fixture) + os.pathsep + os.environ["PATH"],
                "NODE_FIXTURE": str(fixture),
            }
            script = (rendered.stderr + rendered.stdout).replace(
                str(ROOT), str(fixture)
            )
            subprocess.run(
                ["bash", "-c", script, "ci-node-deps", "plugins/linker-tools"],
                env=environment,
                check=True,
            )
            self.assertTrue((fixture / "installed-once").exists())
            (fixture / "reader-active").touch()
            subprocess.run(
                ["bash", "-c", script, "ci-node-deps", "plugins/linker-tools"],
                env=environment,
                check=True,
            )
            self.assertEqual(
                (project / "node_modules/reader-input").read_text(), "preserved"
            )

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
        planner = TEXT.split("\n  planner:\n", 1)[1].split("\n  engine:\n", 1)[0]
        environment, steps = planner.split("    steps:\n", 1)
        for entry in (
            "PLANNER_BUILD_CHANGED: ${{ needs.plan.outputs.planner_build_changed }}",
            "BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}",
            "HEAD_SHA: ${{ github.sha }}",
            "EVENT_NAME: ${{ github.event_name }}",
        ):
            self.assertIn(entry, environment)
        self.assertNotIn("PLANNER_BUILD_CHANGED:", steps)
        self.assertIn("fetch-depth: 2", steps)
        self.assertIn("python3 tools/checks/ci_scope.py verify-planner", steps)
        self.assertLess(
            steps.index("Verify Planner invocation"), steps.index("name: Check")
        )
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
            "steps": [
                {"name": name, "conclusion": "success"}
                for name in ci_scope.MODULE_PHASE_STEPS["engine"]
            ],
        }

    def api(self, endpoint):
        if "workflows/check.yml/runs?" in endpoint:
            self.assertIn("per_page=10", endpoint)
            return {"workflow_runs": [self.prior_run]}
        if "/attempts/" in endpoint:
            return {"total_count": 1, "jobs": [self.job]}
        return self.prior_run

    def test_module_proof_requires_every_successful_phase_and_native_php_condition(
        self,
    ):
        for module, required in ci_scope.MODULE_PHASE_STEPS.items():
            job = {
                "name": module,
                "conclusion": "success",
                "steps": [{"name": name, "conclusion": "success"} for name in required],
            }
            if module == "planner":
                job["steps"].append({"name": "Planner PHP", "conclusion": "success"})
            self.assertTrue(
                ci_scope.successful_module_job(job, module, planner_build_changed=True)
            )
            for name in required:
                for state in (None, "skipped", "failure", "cancelled"):
                    with self.subTest(module=module, phase=name, state=state):
                        altered = {
                            **job,
                            "steps": [
                                {**step, "conclusion": state}
                                if step["name"] == name
                                else step
                                for step in job["steps"]
                                if state is not None or step["name"] != name
                            ],
                        }
                        self.assertFalse(
                            ci_scope.successful_module_job(
                                altered, module, planner_build_changed=True
                            )
                        )
            legacy = {
                **job,
                "steps": [{"name": "Validate module", "conclusion": "success"}],
            }
            self.assertFalse(
                ci_scope.successful_module_job(
                    legacy, module, planner_build_changed=True
                )
            )
            if module == "planner":
                self.assertFalse(ci_scope.successful_module_job(job, module))
                for flag in (False, True):
                    for state in (None, "success", "skipped", "failure", "cancelled"):
                        with self.subTest(flag=flag, php=state):
                            altered = {
                                **job,
                                "steps": [
                                    step
                                    for step in job["steps"]
                                    if step["name"] != "Planner PHP"
                                ],
                            }
                            if state is not None:
                                altered["steps"].append(
                                    {"name": "Planner PHP", "conclusion": state}
                                )
                            self.assertEqual(
                                ci_scope.successful_module_job(
                                    altered, module, planner_build_changed=flag
                                ),
                                state == ("success" if flag else "skipped"),
                            )
        self.assertTrue(
            ci_scope.successful_module_job(
                {
                    "name": "content",
                    "conclusion": "success",
                    "steps": [{"name": "Validate module", "conclusion": "success"}],
                },
                "content",
            )
        )

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

    def test_full_candidate_increment_requires_known_complete_git_delta(self):
        with TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            self.addCleanup(os.chdir, previous)

            def run(*args):
                return subprocess.check_output(args, text=True).strip()

            def commit(message):
                run("git", "add", ".")
                run("git", "commit", "-qm", message)
                return run("git", "rev-parse", "HEAD")

            run("git", "init", "-q")
            run("git", "config", "user.email", "ci@example.invalid")
            run("git", "config", "user.name", "CI fixture")
            for name in ("services/engine/runtime.py", "services/genie/app.py"):
                path = Path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original")
            base = commit("base")
            workflow = Path(".github/workflows/cache-retirement.yml")
            workflow.parent.mkdir(parents=True)
            workflow.write_text("new workflow")
            proof_commit = commit("full candidate with new workflow")
            Path("services/genie/app.py").write_text("fixed")
            head = commit("only known service fix")
            self.assertIsNone(
                ci_scope.selected_modules(ci_scope.diff_changes(base, head), base, head)
            )
            self.assertTrue(ci_scope.same_module_inputs(proof_commit, head, "engine"))
            self.assertFalse(ci_scope.same_module_inputs(proof_commit, head, "genie"))
            self.assertTrue(ci_scope.same_module_inputs(head, head, "engine"))
            self.prior_run["display_title"] = "check #820 | tree-ref=" + proof_commit
            with patch.object(ci_scope, "api", side_effect=self.api):
                proof = ci_scope.reusable_modules(["engine"], head)
                self.assertEqual(set(proof), {"engine"})
                self.assertTrue(ci_scope.validate_module_reuse(proof, ["engine"], head))
                for mutation in ("unknown", "rename", "symlink", "control"):
                    with self.subTest(mutation=mutation):
                        run("git", "reset", "--hard", head)
                        if mutation == "unknown":
                            Path("new-shared-input.conf").write_text("unknown")
                        elif mutation == "rename":
                            Path("services/genie/app.py").write_text("original")
                            run(
                                "git",
                                "mv",
                                "services/genie/app.py",
                                "services/genie/renamed.py",
                            )
                        elif mutation == "symlink":
                            Path("services/genie/app.py").unlink()
                            Path("services/genie/app.py").symlink_to("other.py")
                        else:
                            Path("justfile").write_text("new control")
                        changed = commit(mutation)
                        if mutation != "control":
                            self.assertEqual(
                                ci_scope.module_fingerprint(head, "engine"),
                                ci_scope.module_fingerprint(changed, "engine"),
                            )
                        self.assertFalse(
                            ci_scope.same_module_inputs(proof_commit, changed, "engine")
                        )
                        self.assertFalse(
                            ci_scope.validate_module_reuse(proof, ["engine"], changed)
                        )
                        self.assertEqual(
                            ci_scope.reusable_modules(["engine"], changed), {}
                        )

    def test_planner_reuse_requires_matching_verified_merge_invocations(self):
        with TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            self.addCleanup(os.chdir, previous)

            def run(*args):
                return subprocess.check_output(args, text=True).strip()

            def commit(message):
                run("git", "add", ".")
                run("git", "commit", "-qm", message)
                return run("git", "rev-parse", "HEAD")

            def merge(base, source):
                run("git", "checkout", "-qB", "merge", base)
                run("git", "merge", "--no-ff", "-qm", "CI merge", source)
                return run("git", "rev-parse", "HEAD")

            run("git", "init", "-q")
            run("git", "config", "user.email", "ci@example.invalid")
            run("git", "config", "user.name", "CI fixture")
            build = Path("plugins/linker-tools/build/planner/app.js")
            build.parent.mkdir(parents=True)
            build.write_text("old build")
            original_base = commit("original base")
            build.write_text("current build")
            unchanged_base = commit("build already on base")
            run("git", "checkout", "-qB", "source", original_base)
            build.write_text("current build")
            app = Path("apps/planner/src/app.ts")
            app.parent.mkdir(parents=True)
            app.write_text("current source")
            source = commit("planner change")
            Path("AGENTS.md").write_text("acceptance guidance")
            next_source = commit("documentation only")
            self.job["name"] = "planner"
            verification = {
                "name": "Verify Planner invocation",
                "conclusion": "success",
            }
            self.job["steps"] = [
                {"name": name, "conclusion": "success"}
                for name in ci_scope.MODULE_PHASE_STEPS["planner"]
                if name != "Verify Planner invocation"
            ] + [verification]
            php_phase = {"name": "Planner PHP", "conclusion": "skipped"}
            self.job["steps"].append(php_phase)
            self.prior_run["head_sha"] = source
            bases = {False: unchanged_base, True: original_base}
            with patch.object(ci_scope, "api", side_effect=self.api):
                for old_flag, new_flag in (
                    (False, False),
                    (True, True),
                    (False, True),
                    (True, False),
                ):
                    with self.subTest(old=old_flag, new=new_flag):
                        php_phase["conclusion"] = "success" if old_flag else "skipped"
                        before = merge(bases[old_flag], source)
                        head = merge(bases[new_flag], next_source)
                        self.prior_run["display_title"] = (
                            "check #820 | tree-ref=" + before
                        )
                        self.assertTrue(
                            ci_scope.same_module_inputs(before, head, "planner")
                        )
                        # The old job must have used the reconstructed condition,
                        # even when its plan fell back to an empty change list.
                        with patch.dict(
                            os.environ,
                            {
                                "BASE_SHA": bases[old_flag],
                                "HEAD_SHA": before,
                                "PLANNER_BUILD_CHANGED": str(old_flag).lower(),
                            },
                        ):
                            ci_scope.verify_planner_invocation()
                            with patch.dict(
                                os.environ,
                                {"PLANNER_BUILD_CHANGED": str(not old_flag).lower()},
                            ):
                                with self.assertRaises(SystemExit):
                                    ci_scope.verify_planner_invocation()
                        with patch.dict(
                            os.environ, {"BASE_SHA": bases[new_flag], "HEAD_SHA": head}
                        ):
                            proof = ci_scope.reusable_modules(["planner"], head)
                            if old_flag != new_flag:
                                self.assertEqual(proof, {})
                                # Even an otherwise valid success/input proof is insufficient.
                                proof = {
                                    "planner": {
                                        "run": 10,
                                        "attempt": 1,
                                        "job": 20,
                                        "commit": before,
                                        "inputs": ci_scope.module_fingerprint(
                                            head, "planner"
                                        ),
                                    }
                                }
                                self.assertFalse(
                                    ci_scope.validate_module_reuse(
                                        proof, ["planner"], head
                                    )
                                )
                                continue
                            self.assertEqual(set(proof), {"planner"})
                            self.assertTrue(
                                ci_scope.validate_module_reuse(proof, ["planner"], head)
                            )
                            # A success job from an older workflow or a failed
                            # condition check cannot prove the actual invocation.
                            for state in (None, "failure", "skipped"):
                                if state is None:
                                    self.job["steps"].remove(verification)
                                else:
                                    verification["conclusion"] = state
                                    if verification not in self.job["steps"]:
                                        self.job["steps"].append(verification)
                                self.assertEqual(
                                    ci_scope.reusable_modules(["planner"], head), {}
                                )
                                self.assertFalse(
                                    ci_scope.validate_module_reuse(
                                        proof, ["planner"], head
                                    )
                                )
                            verification["conclusion"] = "success"
                            # Gate reads native merge/run evidence again, not a supplied flag.
                            with patch.dict(
                                os.environ, {"BASE_SHA": bases[not new_flag]}
                            ):
                                self.assertFalse(
                                    ci_scope.validate_module_reuse(
                                        proof, ["planner"], head
                                    )
                                )
                            for invalid_source in (None, next_source):
                                self.prior_run["head_sha"] = invalid_source
                                self.assertEqual(
                                    ci_scope.reusable_modules(["planner"], head), {}
                                )
                                self.assertFalse(
                                    ci_scope.validate_module_reuse(
                                        proof, ["planner"], head
                                    )
                                )
                            self.prior_run["head_sha"] = source
                            for invalid in (source, "f" * 40):
                                self.prior_run["display_title"] = (
                                    "check #820 | tree-ref=" + invalid
                                )
                                self.assertEqual(
                                    ci_scope.reusable_modules(["planner"], head), {}
                                )
                            self.prior_run["display_title"] = (
                                "check #820 | tree-ref=" + before
                            )
                            self.assertEqual(
                                ci_scope.reusable_modules(["planner"], next_source), {}
                            )
                            with patch.dict(
                                os.environ,
                                {
                                    "HEAD_SHA": next_source,
                                    "PLANNER_BUILD_CHANGED": "false",
                                },
                            ):
                                with self.assertRaises(SystemExit):
                                    ci_scope.verify_planner_invocation()
                            with patch.dict(
                                os.environ,
                                {"EVENT_NAME": "push", "HEAD_SHA": next_source},
                            ):
                                # Main/dispatch do not claim PR module reuse.
                                ci_scope.verify_planner_invocation()
                            # A merge whose first parent object is unavailable is not evidence.
                            missing = (
                                subprocess.check_output(
                                    [
                                        "git",
                                        "hash-object",
                                        "-t",
                                        "commit",
                                        "-w",
                                        "--stdin",
                                    ],
                                    input=(
                                        f"tree {run('git', 'rev-parse', before + '^{tree}')}\n"
                                        f"parent {'f' * 40}\nparent {source}\n"
                                        "author CI <ci@example.invalid> 1 +0000\n"
                                        "committer CI <ci@example.invalid> 1 +0000\n\n"
                                        "missing base\n"
                                    ).encode(),
                                )
                                .decode()
                                .strip()
                            )
                            self.prior_run["display_title"] = (
                                "check #820 | tree-ref=" + missing
                            )
                            self.assertEqual(
                                ci_scope.reusable_modules(["planner"], head), {}
                            )
                            self.prior_run["display_title"] = (
                                "check #820 | tree-ref=" + before
                            )
                            self.job["name"] = "presentation"
                            self.assertEqual(
                                ci_scope.reusable_modules(["presentation"], head), {}
                            )
                            self.job["name"] = "planner"

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

    def test_reuse_inputs_distinguish_local_tests_from_actual_consumers(self):
        with TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            self.addCleanup(os.chdir, previous)

            def run(*args):
                return subprocess.check_output(args, text=True).strip()

            run("git", "init", "-q")
            run("git", "config", "user.email", "ci@example.invalid")
            run("git", "config", "user.name", "CI fixture")
            paths = (
                "tools/local/tests/test_wpcli.py",
                "tools/local/src/linker_local/wpcli.py",
                "tools/local/tests/fixtures/wordpress.php",
                "tools/migrate/548-controller-facts.py",
                "tools/migrate/548-controller-facts.php",
                "tools/migrate/7-facts.json",
            )
            for name in paths:
                path = Path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original")
            run("git", "add", ".")
            run("git", "commit", "-qm", "base")
            base = run("git", "rev-parse", "HEAD")
            native = {"native:" + group for group in ci_scope.NATIVE_GROUPS}
            local_consumers = {
                "php:local",
                "python:local",
                "python:pull",
                "python:cutover",
                "content",
                *native,
            }
            modules = [*local_consumers, "php:commerce", "python:migrate"]
            cases = (
                (paths[0], {"python:local"}, {"python:local"}),
                (
                    paths[1],
                    local_consumers,
                    {"python:local", "python:pull", "python:cutover", *native},
                ),
                (
                    paths[2],
                    local_consumers,
                    {
                        "php:local",
                        "python:local",
                        "python:pull",
                        "python:cutover",
                        *native,
                    },
                ),
                (paths[3], {"python:migrate"}, {"python:migrate"}),
                (
                    paths[4],
                    {"php:commerce", "python:migrate"},
                    {"php:commerce", "python:migrate"},
                ),
                (
                    paths[5],
                    {"php:commerce", "python:migrate"},
                    {"php:commerce", "python:migrate"},
                ),
            )
            for name, invalidated, selected in cases:
                Path(name).write_text("changed")
                run("git", "add", ".")
                run("git", "commit", "-qm", "change")
                head = run("git", "rev-parse", "HEAD")
                changes = ci_scope.diff_changes(base, head)
                with self.subTest(path=name):
                    self.assertEqual(
                        set(ci_scope.selected_modules(changes, base, head)), selected
                    )
                    cache = ci_scope.ProofCache()
                    for module in modules:
                        with self.subTest(module=module):
                            self.assertEqual(
                                not ci_scope.same_module_inputs(
                                    base, head, module, cache
                                ),
                                module in invalidated,
                            )
                run("git", "reset", "--hard", base)

    def test_immutable_proof_cache_reuses_only_local_git_inputs(self):
        with TemporaryDirectory() as folder:
            previous = Path.cwd()
            os.chdir(folder)
            self.addCleanup(os.chdir, previous)

            def run(*args):
                return subprocess.check_output(args, text=True).strip()

            run("git", "init", "-q")
            run("git", "config", "user.email", "ci@example.invalid")
            run("git", "config", "user.name", "CI fixture")
            path = Path("services/genie/app.py")
            path.parent.mkdir(parents=True)
            path.write_text("first")
            run("git", "add", ".")
            run("git", "commit", "-qm", "base")
            base = run("git", "rev-parse", "HEAD")
            path.write_text("second")
            run("git", "add", ".")
            run("git", "commit", "-qm", "head")
            head = run("git", "rev-parse", "HEAD")
            expected = {
                module: ci_scope.same_module_inputs(base, head, module)
                for module in ("engine", "genie", "php:local")
            }
            with patch.object(ci_scope, "git", wraps=ci_scope.git) as git:
                cache = ci_scope.ProofCache()
                for module, value in expected.items():
                    self.assertEqual(
                        ci_scope.same_module_inputs(base, head, module, cache), value
                    )
                    ci_scope.module_fingerprint(head, module, cache)
                calls = [call.args for call in git.call_args_list]
                self.assertEqual(
                    sum(args[:3] == ("ls-tree", "-r", "-z") for args in calls), 2
                )
                self.assertEqual(
                    sum(args[:2] == ("diff", "--name-status") for args in calls), 2
                )
                self.assertEqual(
                    sum(args[:2] == ("cat-file", "-e") for args in calls), 1
                )
            self.assertEqual(
                expected, {"engine": True, "genie": False, "php:local": True}
            )
            # An unknown new root remains unprovable even with a warm cache.
            unknown = Path("unclassified/new.py")
            unknown.parent.mkdir()
            unknown.write_text("new")
            run("git", "add", ".")
            run("git", "commit", "-qm", "unknown")
            changed = run("git", "rev-parse", "HEAD")
            self.assertFalse(
                ci_scope.same_module_inputs(base, changed, "engine", cache)
            )
            self.assertFalse(
                ci_scope.same_module_inputs(base, changed, "php:local", cache)
            )
            # Symbolic references are mutable and are never cached by name.
            before_head = ci_scope.module_fingerprint("HEAD", "engine", cache)
            engine = Path("services/engine/app.py")
            engine.parent.mkdir(parents=True)
            engine.write_text("changed")
            run("git", "add", ".")
            run("git", "commit", "-qm", "move HEAD")
            self.assertNotEqual(
                before_head, ci_scope.module_fingerprint("HEAD", "engine", cache)
            )
            with patch.object(
                ci_scope, "proof_increment_known", side_effect=[RuntimeError(), True]
            ) as checked:
                retry_cache = ci_scope.ProofCache()
                with self.assertRaises(RuntimeError):
                    retry_cache.pair(base, head)
                self.assertTrue(retry_cache.pair(base, head))
                self.assertEqual(checked.call_count, 2)

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
                ("justfile", set(originals)),
                ("tools/checks/ci_phase.sh", set(originals)),
                (".editorconfig", set(originals)),
                ("services/engine/uv.lock", {"engine"}),
                ("apps/planner/src/domain/draft.test.ts", set()),
                ("apps/planner/src/data/client.test.ts", set()),
                ("apps/planner/src/components/ReportView.tsx", set()),
                ("apps/planner/src/domain/draft.ts", {"engine"}),
                ("apps/planner/src/domain/solarSetup.ts", {"engine"}),
                ("apps/planner/tests/fixtures/energy-invalid.json", {"engine"}),
                ("apps/planner/src/contracts/geometry.schema.json", {"engine"}),
                ("apps/planner/package-lock.json", {"engine"}),
                ("apps/planner/bin/echarts-types.mjs", {"engine"}),
                ("plugins/linker-tools/src/configurator/schema/roof.json", {"engine"}),
                (
                    "plugins/linker-commerce/includes/Account/AuthTemplates.php",
                    {"php:commerce"},
                ),
                (
                    "plugins/linker-commerce/includes/Abilities/SearchProducts.php",
                    {"php:commerce", "genie"},
                ),
                (
                    "plugins/linker-commerce/includes/Products/SelectionFacts.php",
                    {"php:commerce", "genie"},
                ),
                (
                    "plugins/linker-commerce/includes/Products/Publication.php",
                    {"php:commerce", "engine", "genie"},
                ),
                (
                    "services/engine/src/linker_engine/planning/assistant_context.py",
                    {"engine", "genie"},
                ),
                ("plugins/linker-tools/includes/Protection/Policy.php", {"genie"}),
                ("plugins/linker-tools/src/genie/attachments/prepare.ts", {"genie"}),
                (
                    "services/engine/tests/fixtures/compatibility.json",
                    {"engine", "genie"},
                ),
                (
                    "services/engine/tests/fixtures/feed.json",
                    {"php:commerce", "engine", "genie"},
                ),
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
