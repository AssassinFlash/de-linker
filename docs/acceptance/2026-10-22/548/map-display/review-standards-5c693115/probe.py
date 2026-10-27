"""Pinned Standards correction readback; no checkout, copy, build or network."""
from pathlib import Path
import datetime as dt
import hashlib
import io
import json
import re
import struct
import subprocess
from urllib.parse import urlsplit, parse_qs

BASE = "be5711bf429c86dc5118e55227c0a48bb78d26b1"
PRIOR = "81cd1c5b1a7d5ff5592131602c12d642d13c162b"
TARGET = "5c693115d345a676d7a737bdfb886597b74fbe80"
REPO = Path("/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548")
OUT = Path(__file__).resolve().parent
ACCEPTANCE = "docs/acceptance/2026-10-22/548/map-display/"
RESEARCH = "docs/research/2026-10-23-map-workbench-integration/registry-canonicalization/"
MANIFEST = "plugins/linker-tools/build/planner/source-manifest.json"
LOCK = "apps/planner/package-lock.json"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


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


def tree(revision):
    return set(git("ls-tree", "-r", "--name-only", revision).decode().splitlines())


def json_blob(blobs, path):
    return json.loads(blobs[path])


def without_resolved(lock):
    return {**lock, "packages": {
        key: {field: value for field, value in package.items() if field != "resolved"}
        for key, package in lock["packages"].items()
    }}


target_tree, prior_tree = tree(TARGET), tree(PRIOR)
changed = git("diff", "--name-only", f"{BASE}...{TARGET}").decode().splitlines()
delta = git("diff", "--name-only", f"{PRIOR}...{TARGET}").decode().splitlines()
source_delta = [p for p in delta if not p.startswith(("docs/acceptance/", "docs/research/"))]
expected_delta = {"README.md", "apps/planner/.npmrc", LOCK,
                  "apps/planner/bin/build-manifest.mjs", MANIFEST}
assert set(source_delta) == expected_delta, source_delta
manifest = json.loads(git("show", f"{TARGET}:{MANIFEST}"))
prior_manifest = json.loads(git("show", f"{PRIOR}:{MANIFEST}"))
source_paths = {"apps/planner/" + p for p in manifest["sources"]}
build_paths = {"plugins/linker-tools/build/planner/" + p for p in manifest["build"]}
runtime_paths = {"apps/planner/" + p for p in manifest["sources"] if p.startswith("src/")}
all_src_paths = {p for p in target_tree if p.startswith("apps/planner/src/")}
assert len(runtime_paths) == 97
assert all_src_paths == {p for p in prior_tree if p.startswith("apps/planner/src/")}
prior_evidence = {
    ACCEPTANCE + "review-standards-81cd1c5b/" + name
    for name in ("REVIEW.md", "findings.json", "probe.py", "probe.json")
}
rules = {"AGENTS.md", "README.md", "CONTEXT.md", "docs/adr/0002-isolated-planner-runtime.md"}
target = read_many(TARGET, source_paths | build_paths | all_src_paths | prior_evidence | rules |
                   {MANIFEST} | {p for p in delta if p in target_tree})
prior = read_many(PRIOR, all_src_paths | build_paths | rules | {MANIFEST, LOCK})
assert all(target[p] == prior[p] for p in all_src_paths | build_paths)
assert all(target[p] == prior[p] for p in rules - {"README.md"})
assert len(manifest["sources"]) == 103 and len(manifest["build"]) == 7
assert manifest["build"] == prior_manifest["build"]
hash_gaps = [p for p, data in target.items() if
             (p.startswith("apps/planner/") and p[13:] in manifest["sources"] and
              sha(data) != manifest["sources"][p[13:]]) or
             (p in build_paths and sha(data) != manifest["build"][p[35:]])]
assert not hash_gaps, hash_gaps
manifest_changes = [key for key in sorted(set(manifest["sources"]) | set(prior_manifest["sources"]))
                    if manifest["sources"].get(key) != prior_manifest["sources"].get(key)]
assert manifest_changes == [".npmrc", "bin/build-manifest.mjs", "package-lock.json"]
assert target["apps/planner/.npmrc"].decode().splitlines()[-1] == "replace-registry-host=always"
readme_lines = target["README.md"].decode().splitlines()
assert "registry.npmjs.org" in readme_lines[59] and "replace-registry-host=always" in readme_lines[59]

old_lock, new_lock = json_blob(prior, LOCK), json_blob(target, LOCK)
assert without_resolved(old_lock) == without_resolved(new_lock)
url_changes = []
for key, package in new_lock["packages"].items():
    if "resolved" not in package:
        continue
    before = urlsplit(old_lock["packages"][key]["resolved"])
    after = urlsplit(package["resolved"])
    assert after.scheme == "https" and after.netloc == "registry.npmjs.org"
    assert not after.query and not after.fragment
    assert before._replace(netloc=after.netloc) == after
    assert before.netloc == "registry.npmmirror.com"
    url_changes.append(key)
assert len(url_changes) == 189
old_finding = json_blob(target, ACCEPTANCE + "review-standards-81cd1c5b/findings.json")["hard_documented_breaches"][0]
assert len(old_finding["affected_added_entries"]) == 28
closed_entries = []
for entry in old_finding["affected_added_entries"]:
    package = new_lock["packages"][entry["package"]]
    assert package["version"] == entry["version"] and package["integrity"] == entry["integrity"]
    assert urlsplit(package["resolved"]).netloc == "registry.npmjs.org"
    closed_entries.append({"package": entry["package"], "resolved_line": entry["resolved_line"],
                           "resolved": package["resolved"]})

verification = json_blob(target, RESEARCH + "verification.json")
run = json_blob(target, RESEARCH + "run.json")
actor_input = json_blob(target, RESEARCH + "input.json")
results = {item["url"]: item for item in json_blob(target, RESEARCH + "apify-results.json")}
first_run = json_blob(target, RESEARCH + "first-run.json")
first_failure = json_blob(target, RESEARCH + "first-failure-summary.json")
assert run["id"] == verification["run"] and run["status"] == "SUCCEEDED"
assert run["options"]["memoryMbytes"] == 2048 and actor_input["maxConcurrency"] == 1
assert first_run["status"] == "FAILED" and first_failure["status"] == "FAILED"
assert any("Memory is critically overloaded" in line for line in first_failure["relevant_log"])
publisher_readback = []
for row in verification["packages"]:
    raw_path = RESEARCH + row["name"] + ".json"
    raw = json_blob(target, raw_path)
    package = new_lock["packages"]["node_modules/" + row["name"]]
    assert raw["name"] == row["name"]
    assert raw["version"] == row["version"] == package["version"]
    assert raw["dist"]["integrity"] == row["integrity"] == package["integrity"]
    assert raw["dist"]["tarball"] == row["tarball"] == package["resolved"]
    assert sha(target[raw_path]) == row["sha256"]
    assert results[row["url"]]["crawl"]["httpStatusCode"] == row["http_status"] == 200
    assert results[row["url"]]["crawl"]["loadedUrl"] == row["url"]
    publisher_readback.append({"name": raw["name"], "version": raw["version"],
                              "http_status": 200, "raw_sha256": sha(target[raw_path]),
                              "locked_integrity_and_tarball_match": True})
assert len(publisher_readback) == 3

native_root = ACCEPTANCE + "system-identity/native/"
matrix = json_blob(target, ACCEPTANCE + "system-identity/native-matrix.json")
entry_sha = manifest["build"]["assets/planner.js"]
native_readback = []
for row in matrix["accepted"]:
    png_path, json_path = (native_root + row["name"] + ext for ext in (".png", ".json"))
    png = target[png_path]
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR"
    dimensions = list(struct.unpack(">II", png[16:24]))
    capture = json_blob(target, json_path)
    before, after = capture["before"], capture["after"]
    assert dimensions == row["size"] == before["viewport"] == after["viewport"]
    assert before["scroll"] == after["scroll"] and before["fields"] == after["fields"]
    assert before["identity"] == after["identity"]
    assert before["fonts"] == after["fonts"] == "loaded"
    assert before["details"] and after["details"]
    assert before["widths"] == after["widths"] == [dimensions[0], dimensions[0]]
    box = before["identityBox"]
    assert 0 <= box["left"] <= box["right"] <= dimensions[0]
    assert 0 <= box["top"] <= box["bottom"] <= dimensions[1]
    assert len(before["links"]) == len(after["links"]) == row["links"] == 10
    assert all(parse_qs(urlsplit(url).query).get("ver") == [entry_sha] for url in before["entry"])
    assert before.get("revision") == after.get("revision") == row["revision"]
    if dimensions[0] == 390:
        assert capture["captureBeyondViewport"] is False
    native_readback.append({"name": row["name"], "dimensions": dimensions,
                            "json_sha256": sha(target[json_path]), "png_sha256": sha(png),
                            "unchanged_fields_and_scroll": True, "identity_fully_framed": True,
                            "loaded_entry_matches_fixed_build": True})
assert len(native_readback) == 5
workspaces = json_blob(target, native_root + "native-all-workspaces.json")
assert {s["workspace"] for s in workspaces["states"]} == {"site", "energy", "design", "overview"}
assert all(s["identityCount"] == 1 and s["revision"] == "Gespeichert · Version 3"
           for s in workspaces["states"])
assert workspaces["fieldsUnchanged"] and workspaces["beforeRevision"] == workspaces["afterRevision"]
keyboard = json_blob(target, native_root + "de-desktop-keyboard-toggle.json")
assert keyboard["fieldsUnchanged"] and keyboard["keyboardReopened"] and not keyboard["requests"]
assert keyboard["beforeRevision"] == keyboard["afterRevision"] == "Gespeichert · Version 3"
reopened = json_blob(target, native_root + "native-project-reopen.json")
english = json_blob(target, native_root + "en-desktop-system-about-framed.json")["before"]
assert reopened["revision"] == "Saved · revision 3" and reopened["identityCount"] == 1
assert urlsplit(reopened["url"]).query == urlsplit(english["url"]).query
assert len(reopened["fields"]) == 11
assert [{k: v for k, v in field.items() if k != "id"} for field in reopened["fields"]] == [
    {k: v for k, v in field.items() if k != "id"} for field in english["fields"]]
build_log = target[ACCEPTANCE + "system-identity/registry-build.log"].decode()
check_log = target[ACCEPTANCE + "system-identity/registry-build-check.log"].decode()
format_log = target[ACCEPTANCE + "system-identity/registry-format.log"].decode()
assert "✓ built in" in build_log
assert "Planner build matches its sources." in check_log and "pass 1" in check_log and "fail 0" in check_log
assert "All matched files use Prettier code style!" in format_log

patch = git("diff", f"{BASE}...{TARGET}")
prior_probe = json_blob(target, ACCEPTANCE + "review-standards-81cd1c5b/probe.json")
result = {
    "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "base": BASE, "prior_review_target": PRIOR, "target": TARGET,
    "full_diff_command": f"git diff {BASE}...{TARGET}",
    "full_diff_bytes": len(patch), "full_diff_sha256": sha(patch),
    "full_diff_files": len(changed),
    "commits": git("log", "--reverse", "--format=%H %s", f"{BASE}..{TARGET}").decode().splitlines(),
    "correction_delta_files": delta, "non_evidence_delta_files": source_delta,
    "applicable_rules": {path: sha(target[path]) for path in sorted(rules)},
    "nearby_contributing_or_coding_standards": sorted(p for p in target_tree if
        re.search(r"(^|/)(CONTRIBUTING|CODING_STANDARDS)(\.[^/]*)?$", p, re.I)),
    "prior_exhaustive_review": {
        "files": {p: sha(target[p]) for p in sorted(prior_evidence)},
        "prior_review_records_now_pinned_in_target": True,
        "carried_forward_scope": "Full source/tests/dependencies/emitted modules/languages/PHP/local CSP; vendor, copy, legacy and lifecycle checks.",
        "vendor_css": prior_probe["vendor_css"],
        "reviewed_copy": prior_probe["reviewed_copy"],
        "new_legacy_identifier_hits": prior_probe["new_legacy_identifier_hits"],
    },
    "registry_correction": {
        "resolved_urls_normalized": len(url_changes), "all_other_lock_data_unchanged": True,
        "canonical_host": "registry.npmjs.org", "package_local_replace_registry_host": "always",
        "before_sha256": sha(prior[LOCK]), "after_sha256": sha(target[LOCK]),
        "closed_prior_added_entries": closed_entries, "readme_rule_line": 60,
    },
    "runtime_equivalence": {
        "runtime_source_files_byte_identical": len(runtime_paths),
        "all_tracked_src_files_including_tests_byte_identical": len(all_src_paths),
        "emitted_artifacts_byte_identical": len(build_paths), "entry_sha256": entry_sha,
        "source_manifest_entries": len(manifest["sources"]), "build_manifest_entries": len(manifest["build"]),
        "manifest_hash_gaps": hash_gaps, "changed_source_manifest_keys": manifest_changes,
        "runtime_source_hashes": {p: sha(target[p]) for p in sorted(runtime_paths)},
        "emitted_artifact_hashes": {p: sha(target[p]) for p in sorted(build_paths)},
    },
    "stored_official_metadata": {
        "run": run["id"], "status": run["status"], "raw_status_message": run["statusMessage"],
        "status_message_limit": "Actor statusMessage reports three failed crawl requests; the independently checked stored responses are HTTP200 downloadable JSON. No error-free crawl claim is inferred.",
        "memory_mb": run["options"]["memoryMbytes"], "max_concurrency": actor_input["maxConcurrency"],
        "first_failed_run_retained": first_run["id"], "first_failure_has_memory_evidence": True,
        "packages": publisher_readback,
    },
    "native_record_consistency": {
        "captures": native_readback, "all_four_workspaces_one_identity_saved_v3": True,
        "keyboard_reopens_preserving_fields_v3": True, "same_project_v3_reopened": True,
        "limits": "Read retained native records, not a new browser execution. Identity/list/workspace continuity only; no complete map, packet-level privacy, engineering, country, provider/legal, production or whole-goal acceptance.",
    },
    "retained_logs_inspected_not_rerun": ["registry-build.log", "registry-build-check.log", "registry-format.log"],
    "file_inventory": [{"path": p, "target_sha256": sha(target[p])} for p in changed if p in target],
    "resources_created": {"source_copies": 0, "checkouts": 0, "stacks": 0, "dependencies": 0, "network_requests": 0},
    "verdict": "PASS", "open_hard_documented_breaches": [], "fowler_baseline_judgment_calls": [],
}
(OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"verdict": "PASS", "full_diff_files": len(changed), "normalized_urls": len(url_changes),
                  "closed_added_entries": len(closed_entries), "runtime_source_files_unchanged": len(runtime_paths),
                  "emitted_artifacts_unchanged": len(build_paths), "manifest_entries_checked": [103, 7],
                  "stored_official_package_records_checked": len(publisher_readback),
                  "native_capture_records_checked": len(native_readback)}, indent=2))
