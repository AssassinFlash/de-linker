"""Fixed full-diff Standards readback; reuse exhaustive review, no source copy."""
from pathlib import Path
import datetime as dt
import hashlib
import io
import json
import re
import subprocess

REPO = Path("/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548")
OUT = Path(__file__).resolve().parent
BASE = "66324a39fb449425dd1144b46b4d3abc21dc52d0"
PRIOR = "2464009a7456da75154d36bfecb9d24187a99e18"
TARGET = "71cd719aa67021aee6398ae58f359738005d1f57"
PREFIX = "docs/acceptance/2026-10-24/548/map-drawing/"
MANIFEST = "plugins/linker-tools/build/planner/source-manifest.json"
CONTROLLER = "apps/planner/src/data/MapDrawingController.ts"
GATE = "apps/planner/src/data/MapPickGate.ts"
TEST = "apps/planner/tests/map-drawing-controller.test.mjs"
IMPLEMENTATION = "docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_many(revision, paths):
    paths = sorted(set(paths))
    run = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"],
                         input="".join(f"{revision}:{p}\n" for p in paths).encode(),
                         capture_output=True, check=True)
    stream = io.BytesIO(run.stdout)
    result = {}
    for path in paths:
        header = stream.readline().split()
        assert len(header) == 3 and header[1] == b"blob", (path, header)
        result[path] = stream.read(int(header[2]))
        assert stream.read(1) == b"\n"
    assert not stream.read()
    return result


full_diff = git("diff", f"{BASE}...{TARGET}")
changed = git("diff", "--name-only", f"{BASE}...{TARGET}").decode().splitlines()
delta = git("diff", "--name-only", f"{PRIOR}...{TARGET}").decode().splitlines()
assert len(changed) == 11 and set(delta) == {CONTROLLER, GATE, TEST, IMPLEMENTATION, MANIFEST}
manifest = json.loads(git("show", f"{TARGET}:{MANIFEST}"))
base_manifest = json.loads(git("show", f"{BASE}:{MANIFEST}"))
source_paths = {"apps/planner/" + p for p in manifest["sources"]}
build_paths = {"plugins/linker-tools/build/planner/" + p for p in manifest["build"]}
standards = {"CONTEXT.md", "docs/adr/0002-isolated-planner-runtime.md", "apps/planner/tsconfig.json"}
target = read_many(TARGET, set(changed) | source_paths | build_paths | standards)
prior = read_many(PRIOR, (set(changed) - {GATE}) | standards)
base = read_many(BASE, build_paths)
assert all(target[p] == prior[p] for p in set(changed) - set(delta))
assert all(target[p] == prior[p] for p in standards)
gate = target[GATE]
assert prior[CONTROLLER].count(gate + b"\n") == 1
assert prior[CONTROLLER].replace(gate + b"\n", b"", 1) == target[CONTROLLER]
old_import = b'import {\n\tMapDrawingController,\n\tMapPickGate,\n} from "../src/data/MapDrawingController.ts";'
new_import = b'import { MapDrawingController } from "../src/data/MapDrawingController.ts";\nimport { MapPickGate } from "../src/data/MapPickGate.ts";'
assert prior[TEST].replace(old_import, new_import, 1) == target[TEST]
assert re.findall(rb"^export class (\w+)", target[CONTROLLER], re.M) == [b"MapDrawingController"]
assert re.findall(rb"^export class (\w+)", gate, re.M) == [b"MapPickGate"]
header_lines = target[IMPLEMENTATION].decode().splitlines()
assert len(header_lines) == len(prior[IMPLEMENTATION].decode().splitlines()) + 2
assert "实施状态读法，2026-10-24 更新" in header_lines[4]
assert "控制器尚未挂入客户界面" in header_lines[4]
assert "实现进展不会把原研究中的设计项整体改成已验收能力" in header_lines[4]
assert "\n".join(header_lines[:4] + header_lines[6:]) + "\n" == prior[IMPLEMENTATION].decode()

assert len(manifest["sources"]) == 107 and len(manifest["build"]) == 7
assert manifest["build"] == base_manifest["build"]
assert all(target[p] == base[p] for p in build_paths)
assert all(manifest["sources"][key] == value for key, value in base_manifest["sources"].items())
manifest_gaps = []
for group, prefix in [("sources", "apps/planner/"), ("build", "plugins/linker-tools/build/planner/")]:
    for key, value in manifest[group].items():
        if sha(target[prefix + key]) != value:
            manifest_gaps.append(prefix + key)
assert not manifest_gaps
for path in source_paths | {TEST}:
    assert (REPO / path).read_bytes() == target[path], path

old_evidence = REPO / PREFIX / "review-standards-2464009a"
old_probe = json.loads((old_evidence / "probe.json").read_text())
root_rule = Path("/Users/chesterjohn/Documents/de-linker/AGENTS.md")
assert sha(root_rule.read_bytes()) == old_probe["standards_sources"][0]["sha256"]
assert "一个组件/类/模块一个文件" in root_rule.read_text().splitlines()[77]
for row in old_probe["files_read_in_full_diff"]:
    assert sha(prior[row["path"]]) == row["sha256"], row["path"]
for library in old_probe["installed_primary_source"]:
    name = library["package"]
    filename = name + ".modern.js.map"
    data = (REPO / "apps/planner/node_modules" / name / "dist" / filename).read_bytes()
    assert sha(data) == library["published_sourcemap_sha256"]
legacy = []
secrets = []
for path in changed:
    for line_number, line in enumerate(target[path].decode().splitlines(), 1):
        if re.search(r"tv_b2b_|Linker_AI_|dlk-", line): legacy.append({"path": path, "line": line_number})
        if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{25,}|sk_live_[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{16})", line):
            secrets.append({"path": path, "line": line_number})
assert not legacy and not secrets
hits = git("grep", "-n", "MapDrawingController", TARGET, "--", "apps/planner/src").decode().splitlines()
assert hits and all(":apps/planner/src/data/MapDrawingController.ts:" in line for line in hits)

command = ["node", "--no-warnings=ExperimentalWarning", "--loader", "./tests/tsx-loader.mjs", "--test", "tests/map-drawing-controller.test.mjs"]
run = subprocess.run(command, cwd=REPO / "apps/planner", capture_output=True, timeout=60)
output = run.stdout + run.stderr
(OUT / "controller-tests.log").write_bytes(output)
totals = {label: int(re.search(r"(?:ℹ|#) " + label + r" (\d+)", output.decode()).group(1))
          for label in ("tests", "pass", "fail", "cancelled", "skipped")}
assert run.returncode == 0 and totals["tests"] == totals["pass"] == 22 and totals["fail"] == 0
receipt_path = REPO / PREFIX / "validation.json"
receipt = json.loads(receipt_path.read_text())
assert receipt["source_pin"] == TARGET and receipt["base"] == BASE
assert receipt["checks"]["npm_test"]["total"] == 195
assert receipt["source_manifest_entries_verified"] == 107
tree = git("ls-tree", "-r", "--name-only", TARGET).decode().splitlines()
result = {
    "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "base": BASE, "prior_review_target": PRIOR, "target": TARGET,
    "full_diff_command": f"git diff {BASE}...{TARGET}", "full_diff_files": len(changed),
    "diff_bytes": len(full_diff), "diff_sha256": sha(full_diff),
    "commits": git("log", "--reverse", "--oneline", f"{BASE}..{TARGET}").decode().splitlines(),
    "file_inventory": [{"path": p, "bytes": len(target[p]), "sha256": sha(target[p])} for p in changed],
    "correction_delta": delta, "gate_body_moved_byte_identically": True,
    "controller_changed_only_by_gate_removal": True, "test_changed_only_by_direct_import": True,
    "old_p3": "CLOSED; one independent exported class per file now satisfies current root AGENTS.md:78.",
    "applicable_rules": {str(root_rule): sha(root_rule.read_bytes()), **{p: sha(target[p]) for p in sorted(standards)}},
    "contributing_or_coding_standards": [p for p in tree if re.search(r"(^|/)(CONTRIBUTING|CODING_STANDARDS)(\.[^/]*)?$", p, re.I)],
    "prior_exhaustive_review_preserved": {f.name: sha(f.read_bytes()) for f in sorted(old_evidence.iterdir()) if f.is_file()},
    "unchanged_prior_source_test_dossier_hunks": True,
    "prior_targeted_tests_carried_forward": {"total": 34, "domain": 12, "controller": 22,
        "binding": "Previous tested source fingerprints match 2464009a; domain files unchanged, controller body and gate implementation unchanged after the move."},
    "controller_tests_reexecuted_for_new_import": {"command": command, "exit_code": run.returncode, "totals": totals,
                                                   "log": "controller-tests.log", "sha256": sha(output)},
    "manifest": {"sources_checked": 107, "build_checked": 7, "hash_gaps": manifest_gaps,
                 "all_base_source_hashes_unchanged": True, "all_seven_emitted_artifacts_byte_identical_to_base": True,
                 "source_manifest_sha256": sha(target[MANIFEST]), "artifacts": manifest["build"]},
    "research_update": "Exactly two inserted lines clearly distinguish historical b008 status and unaccepted design from current installed/import/map/controller boundaries; no new whole-goal claim.",
    "legacy_identifier_hits": legacy, "high_confidence_secret_pattern_hits": secrets,
    "secret_check_limit": "Pattern scan plus manual full-hunk inspection, not a universal secret detector.",
    "installed_primary_source_shas_match_prior_independent_audit": True, "no_customer_mount": True,
    "owner_validation_receipt": {"path": str(receipt_path), "sha256": sha(receipt_path.read_bytes()),
        "source_pin_matches": True, "scope": "Inspected 195 tests/build/build-check/format receipt; did not repeat the unchanged full suite or claim its execution as this review's own."},
    "resources_created": {"source_copies": 0, "worktrees": 0, "dependency_installs": 0, "stacks": 0, "network_requests": 0},
    "verdict": "PASS", "hard_documented_breaches": [], "fowler_baseline_judgment_calls": [],
    "boundary": "Independent full fixed Standards diff. Real Terra Draw with callback adapter/JSDOM and domain evidence only; no new real-MapLibre-adapter DOM, native/GPU/touch, customer mounting/recovery, engineering, provider/legal, production or full-goal acceptance.",
}
(OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"verdict": "PASS", "full_diff_files": 11, "prior_p3": "CLOSED", "gate_move_byte_identical": True,
                  "controller_cases_reexecuted": 22, "source_hashes_checked": 107,
                  "emitted_artifacts_byte_identical_to_base": 7}, indent=2))
