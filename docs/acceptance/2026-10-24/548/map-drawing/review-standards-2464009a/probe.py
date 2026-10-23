"""Small pinned Standards probes; no source copy, install, build or network."""
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
TARGET = "2464009a7456da75154d36bfecb9d24187a99e18"
MANIFEST = "plugins/linker-tools/build/planner/source-manifest.json"
ROOT_RULES = Path("/Users/chesterjohn/Documents/de-linker/AGENTS.md")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read_many(revision, paths):
    paths = sorted(set(paths))
    completed = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "--batch"],
        input="".join(f"{revision}:{path}\n" for path in paths).encode(),
        capture_output=True, check=True,
    )
    stream = io.BytesIO(completed.stdout)
    result = {}
    for path in paths:
        header = stream.readline().split()
        assert len(header) == 3 and header[1] == b"blob", (path, header)
        result[path] = stream.read(int(header[2]))
        assert stream.read(1) == b"\n"
    assert not stream.read()
    return result


patch = git("diff", f"{BASE}...{TARGET}")
changed = git("diff", "--name-only", f"{BASE}...{TARGET}").decode().splitlines()
assert len(changed) == 9
target_paths = set(git("ls-tree", "-r", "--name-only", TARGET).decode().splitlines())
manifest = json.loads(git("show", f"{TARGET}:{MANIFEST}"))
old_manifest = json.loads(git("show", f"{BASE}:{MANIFEST}"))
source_paths = {"apps/planner/" + name for name in manifest["sources"]}
build_paths = {"plugins/linker-tools/build/planner/" + name for name in manifest["build"]}
rules = {"CONTEXT.md", "docs/adr/0002-isolated-planner-runtime.md", "apps/planner/tsconfig.json"}
target = read_many(TARGET, set(changed) | source_paths | build_paths | rules)
base = read_many(BASE, build_paths | {MANIFEST})
assert manifest["build"] == old_manifest["build"]
assert all(target[path] == base[path] for path in build_paths)
manifest_gaps = []
for group, prefix in [("sources", "apps/planner/"), ("build", "plugins/linker-tools/build/planner/")]:
    for name, expected in manifest[group].items():
        if sha(target[prefix + name]) != expected:
            manifest_gaps.append(prefix + name)
assert not manifest_gaps
added_sources = sorted(set(manifest["sources"]) - set(old_manifest["sources"]))
assert added_sources == ["src/data/MapDrawingController.ts", "src/domain/mapDrawingGeometry.ts", "src/domain/mapRingEdit.ts"]
assert all(manifest["sources"][name] == expected for name, expected in old_manifest["sources"].items())
assert len(manifest["sources"]) == 106 and len(build_paths) == 7
# Runtime tests execute the owned files only after binding them to the fixed pin.
test_support = ["apps/planner/tests/tsx-loader.mjs", "apps/planner/package-lock.json", "apps/planner/package.json"]
support = read_many(TARGET, test_support)
for path, data in {**target, **support}.items():
    if path.startswith("apps/planner/"):
        assert (REPO / path).read_bytes() == data, path

controller = target["apps/planner/src/data/MapDrawingController.ts"].decode()
classes = [{"name": m.group(1), "line": controller[:m.start()].count("\n") + 1}
           for m in re.finditer(r"^export class (\w+)", controller, re.M)]
assert classes == [{"name": "MapPickGate", "line": 57}, {"name": "MapDrawingController", "line": 87}]
rule_text = ROOT_RULES.read_text()
rule_line = next(i for i, line in enumerate(rule_text.splitlines(), 1) if "一个组件/类/模块一个文件" in line)
assert rule_line == 78
legacy_hits = []
secret_hits = []
for path in changed:
    for line_number, line in enumerate(target[path].decode().splitlines(), 1):
        if re.search(r"tv_b2b_|Linker_AI_|dlk-", line):
            legacy_hits.append({"path": path, "line": line_number})
        if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{25,}|sk_live_[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{16})", line):
            secret_hits.append({"path": path, "line": line_number})
assert not legacy_hits and not secret_hits
# A declaration/factory is allowed in this internal increment; it must not be mounted.
mount_hits = git("grep", "-n", "MapDrawingController", TARGET, "--", "apps/planner/src").decode().splitlines()
assert mount_hits and all(":apps/planner/src/data/MapDrawingController.ts:" in line for line in mount_hits)

library = []
expected_maps = {
    "terra-draw": ("1.35.0", "terra-draw.modern.js.map", "52684d483063ff148d5b9fdc94d94c2c8657a82ac955372ca8043d0f3237ef25"),
    "terra-draw-maplibre-gl-adapter": ("1.4.1", "terra-draw-maplibre-gl-adapter.modern.js.map", "398a7f121b2b9b3b65c6735cc9f7b5d6fd9d6ab8241ca70888d400ad06ab467c"),
}
for name, (version, filename, expected) in expected_maps.items():
    package = REPO / "apps/planner/node_modules" / name
    data = (package / "dist" / filename).read_bytes()
    assert sha(data) == expected
    assert json.loads((package / "package.json").read_text())["version"] == version
    parsed = json.loads(data)
    source_entries = {path: sha(content.encode()) for path, content in zip(parsed["sources"], parsed["sourcesContent"])
                      if path.rsplit("/", 1)[-1] in {"terra-draw.ts", "base.adapter.ts", "select.mode.ts", "limit-decimal-precision.ts", "terra-draw-maplibre-gl-adapter.ts"}}
    library.append({"package": name, "version": version, "published_sourcemap_sha256": sha(data),
                    "inspected_original_source_entries": source_entries})

commands = [
    ("domain-tests.log", ["node", "--test", "src/domain/mapRingEdit.test.ts", "src/domain/mapDrawingGeometry.test.ts"]),
    ("controller-tests.log", ["node", "--no-warnings=ExperimentalWarning", "--loader", "./tests/tsx-loader.mjs", "--test", "tests/map-drawing-controller.test.mjs"]),
]
test_results = []
for filename, command in commands:
    process = subprocess.run(command, cwd=REPO / "apps/planner", capture_output=True, timeout=60)
    output = process.stdout + process.stderr
    (OUT / filename).write_bytes(output)
    text = output.decode()
    totals = {}
    for label in ("tests", "pass", "fail", "cancelled", "skipped"):
        matches = re.findall(r"(?:ℹ|#) " + label + r" (\d+)", text)
        assert len(matches) == 1, (label, text[-1000:])
        totals[label] = int(matches[0])
    assert process.returncode == 0 and totals["fail"] == 0 and totals["pass"] == totals["tests"]
    test_results.append({"command": command, "cwd": str(REPO / "apps/planner"), "exit_code": process.returncode,
                         "totals": totals, "log": filename, "sha256": sha(output)})
assert sum(row["totals"]["tests"] for row in test_results) == 34

result = {
    "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "base": BASE, "target": TARGET,
    "full_diff_command": f"git diff {BASE}...{TARGET}", "diff_bytes": len(patch), "diff_sha256": sha(patch),
    "commits": git("log", "--reverse", "--oneline", f"{BASE}..{TARGET}").decode().splitlines(),
    "files_read_in_full_diff": [{"path": p, "bytes": len(target[p]), "sha256": sha(target[p])} for p in changed],
    "standards_sources": [{"path": str(ROOT_RULES), "sha256": sha(ROOT_RULES.read_bytes()), "class_per_file_rule_line": rule_line}] +
                         [{"path": p, "sha256": sha(target[p])} for p in sorted(rules)],
    "contributing_or_coding_standards": sorted(p for p in target_paths if re.search(r"(^|/)(CONTRIBUTING|CODING_STANDARDS)(\.[^/]*)?$", p, re.I)),
    "manifest": {"sources_checked": len(manifest["sources"]), "build_checked": len(build_paths),
                 "hash_gaps": manifest_gaps, "existing_source_hashes_unchanged": True,
                 "added_sources": added_sources, "all_seven_emitted_artifacts_byte_identical_to_base": True,
                 "artifacts": manifest["build"]},
    "exported_classes_in_controller_file": classes,
    "no_customer_mount": True, "legacy_identifier_hits": legacy_hits,
    "high_confidence_secret_pattern_hits": secret_hits,
    "secret_check_limit": "Pattern scan plus full manual hunk inspection; not a universal secret detector.",
    "installed_primary_source": library,
    "targeted_layer_tests": test_results, "new_cases_passed": 34,
    "node_version": subprocess.check_output(["node", "--version"]).decode().strip(),
    "parent_validation_receipt_inspected": {
        "path": "docs/acceptance/2026-10-24/548/map-drawing/validation.json",
        "sha256": sha((REPO / "docs/acceptance/2026-10-24/548/map-drawing/validation.json").read_bytes()),
        "limit": "Owner receipt reports full 195 tests/build/build-check/format; this review reran only the 34 relevant cases, not the unchanged full suite.",
    },
    "review_boundary": "Independent Standards only; full 9-file pinned diff. Installed-library/JSDOM/domain evidence, not native/GPU/touch, customer mounting/recovery, engineering, provider permission, production or full-goal acceptance.",
    "created_resources": {"source_copies": 0, "worktrees": 0, "dependencies": 0, "stacks": 0, "network_requests": 0},
}
(OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"pin": TARGET, "full_diff_files": len(changed), "layer_cases_passed": 34,
                  "source_hashes_checked": 106, "emitted_artifacts_unchanged": 7,
                  "legacy_hits": len(legacy_hits), "secret_pattern_hits": len(secret_hits),
                  "exported_classes_in_controller_file": classes}, indent=2))
