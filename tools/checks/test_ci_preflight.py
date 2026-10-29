"""Contracts for the local CI preflight scope and lane plan."""

import unittest

from ci_preflight import Change, classify, initial_lanes


class PreflightScopeTest(unittest.TestCase):
    def test_docs_and_records_need_no_runtime_lanes(self) -> None:
        self.assertEqual(
            classify(
                [
                    Change("M", "AGENTS.md"),
                    Change("A", "docs/acceptance/2026-10-29/result.json"),
                ]
            ),
            "docs",
        )
        self.assertEqual(initial_lanes("docs"), [])

    def test_presentation_and_commerce_keep_their_existing_counts(self) -> None:
        self.assertEqual(
            classify(
                [
                    Change(
                        "M",
                        "plugins/linker-commerce/content/windpress/tokens.css",
                    )
                ]
            ),
            "presentation",
        )
        self.assertEqual(
            classify(
                [
                    Change(
                        "M",
                        "plugins/linker-commerce/includes/Presentation/"
                        "ProductShortcodes.php",
                    )
                ]
            ),
            "commerce",
        )
        self.assertEqual(len(initial_lanes("presentation")), 1)
        self.assertEqual(len(initial_lanes("commerce")), 1)

    def test_unknown_new_shared_or_binary_surface_is_full(self) -> None:
        for change in (
            Change("M", ".github/workflows/check.yml"),
            Change("M", "Justfile"),
            Change("A", "plugins/linker-commerce/includes/Unknown.php"),
            Change("M", "plugins/linker-commerce/src/index.tsx"),
            Change("A", "plugins/linker-commerce/assets/new-surface.js"),
            Change("D", "plugins/linker-commerce/assets/account-ui.js"),
        ):
            with self.subTest(change=change):
                self.assertEqual(classify([change]), "full")

    def test_full_plan_runs_languages_in_parallel_and_content(self) -> None:
        names = [lane.name for lane in initial_lanes("full")]
        self.assertEqual(
            names,
            [
                "python-genie",
                "python-engine",
                "python-tools",
                "python-harnesses",
                "python-static",
                "pull-test",
                "cutover-test",
                "php",
                "javascript",
                "content",
            ],
        )
        commands = {lane.name: lane.command for lane in initial_lanes("full")}
        self.assertEqual(
            commands["python-genie"],
            ("just", "py-test-group", "genie"),
        )
        self.assertEqual(
            commands["javascript"],
            ("just", "js-check", "e2e-check", "js-test"),
        )


if __name__ == "__main__":
    unittest.main()
