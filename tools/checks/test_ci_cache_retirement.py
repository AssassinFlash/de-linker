"""Run the deployed cleanup shell against an isolated GitHub CLI boundary."""

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/cache-retirement.yml"
GH = r"""#!/usr/bin/env python3
import json, os, pathlib, sys
a=sys.argv[1:]; root=pathlib.Path(os.environ['FAKE_GH_ROOT']); scenario=os.environ['SCENARIO']
with (root/'calls').open('a') as f: f.write(json.dumps(a)+'\n')
if a[0]=='api':
    if scenario=='api_error': sys.exit(7)
    if any('/pulls/' in x for x in a):
        if scenario=='recheck_error' and '--jq' in a: sys.exit(7)
        state='open' if scenario=='open' else 'closed'
        print(state if '--jq' in a else json.dumps({'state':state,'head':{'ref':'feature/test'}}))
    elif any(x.endswith('/pulls') for x in a):
        print(json.dumps([[{'number':820,'head':{'repo':{'full_name':'fixture/repo'},'ref':'feature/test','sha':'new-head'}}]]))
    elif scenario=='active': print('123456')
elif a[:2]==['cache','list']:
    deleted=(root/'deleted').read_text().splitlines() if (root/'deleted').exists() else []
    rows=[{'id':i,'ref':'refs/heads/main' if scenario=='wrong_ref' else 'refs/pull/820/merge','sizeInBytes':i*10} for i in (11,12) if str(i) not in deleted]
    if scenario=='historical_cap':
        rows=[{'id':i,'ref':f'refs/pull/{820 if i<=80 else 821}/merge','sizeInBytes':10} for i in range(1,161) if str(i) not in deleted]
        if '--ref' in a: rows=[row for row in rows if row['ref']==a[a.index('--ref')+1]]
        rows=rows[:int(a[a.index('--limit')+1])]
    print(len(rows) if '--jq' in a else json.dumps(rows))
elif a[:2]==['cache','delete']:
    if scenario=='delete_error': sys.exit(8)
    with (root/'deleted').open('a') as f: f.write(a[2]+'\n')
    if scenario=='delete_lost_reply': sys.exit(8)
else: sys.exit(9)
"""


class CacheRetirement(unittest.TestCase):
    def run_cleanup(self, scenario):
        body = textwrap.dedent(WORKFLOW.read_text().split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory(prefix="linker-cache-lifecycle-") as temporary:
            root = Path(temporary)
            gh = root / "gh"
            gh.write_text(GH)
            gh.chmod(0o700)
            result = subprocess.run(
                ["bash", "-c", body],
                env={
                    **os.environ,
                    "PATH": str(root) + os.pathsep + os.environ["PATH"],
                    "GH_TOKEN": "fixture-only",
                    "GH_REPO": "fixture/repo",
                    "PULL_NUMBER": ""
                    if scenario == "completed_tail"
                    else "all"
                    if scenario in {"historical", "historical_cap"}
                    else "820",
                    "SCENARIO": scenario,
                    "SOURCE_OWNER": "fixture",
                    "SOURCE_REPO": "fixture/repo",
                    "SOURCE_BRANCH": "feature/test",
                    "FAKE_GH_ROOT": str(root),
                    "GITHUB_STEP_SUMMARY": str(root / "summary"),
                },
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            calls = [
                json.loads(line) for line in (root / "calls").read_text().splitlines()
            ]
            deleted = (
                (root / "deleted").read_text().splitlines()
                if (root / "deleted").exists()
                else []
            )
            return result, calls, deleted

    def test_closed_idle_ref_is_retired_and_read_back(self):
        result, calls, deleted = self.run_cleanup("closed")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["11", "12"], deleted)
        self.assertIn("retired 2 caches (230 bytes); remaining=0", result.stdout)
        self.assertEqual(2, sum(call[:2] == ["cache", "list"] for call in calls))

    def test_open_or_active_work_is_preserved(self):
        for scenario in ("open", "active"):
            with self.subTest(scenario=scenario):
                result, calls, deleted = self.run_cleanup(scenario)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual([], deleted)
                self.assertFalse(any(call[0] == "cache" for call in calls))

    def test_completed_old_check_resolves_pr_without_payload_association(self):
        result, calls, deleted = self.run_cleanup("completed_tail")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["11", "12"], deleted)
        self.assertTrue(any("head=fixture:feature/test" in call for call in calls))

    def test_historical_pass_and_lost_delete_reply_use_native_readback(self):
        for scenario in ("historical", "delete_lost_reply"):
            with self.subTest(scenario=scenario):
                result, _, deleted = self.run_cleanup(scenario)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(["11", "12"], deleted)

    def test_historical_limit_is_global_not_multiplied_by_pr_count(self):
        result, _, deleted = self.run_cleanup("historical_cap")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([str(i) for i in range(1, 101)], deleted)
        self.assertIn("remaining=60", result.stdout)
        self.assertIn("unselected caches remain", result.stdout)

    def test_foreign_ref_and_api_failure_never_delete(self):
        for scenario in ("wrong_ref", "api_error", "recheck_error"):
            with self.subTest(scenario=scenario):
                result, _, deleted = self.run_cleanup(scenario)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], deleted)

    def test_delete_failure_is_visible_not_a_success_receipt(self):
        result, _, deleted = self.run_cleanup("delete_error")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], deleted)
        self.assertNotIn("retired 2 caches", result.stdout)


if __name__ == "__main__":
    unittest.main()
