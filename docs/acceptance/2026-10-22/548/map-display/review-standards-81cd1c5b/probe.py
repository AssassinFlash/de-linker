"""Bounded fixed-object Standards readback. No checkout, source copy or network."""
from pathlib import Path
import datetime as dt
import gettext
import hashlib
import io
import json
import re
import subprocess

BASE = "be5711bf429c86dc5118e55227c0a48bb78d26b1"
TARGET = "81cd1c5b1a7d5ff5592131602c12d642d13c162b"
REPO = Path("/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548")
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_many(rev, paths):
    paths = sorted(set(paths))
    completed = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "--batch"],
        input="".join(f"{rev}:{path}\n" for path in paths).encode(),
        capture_output=True,
        check=True,
    )
    stream = io.BytesIO(completed.stdout)
    result = {}
    for path in paths:
        head = stream.readline().split()
        assert len(head) == 3 and head[1] == b"blob", (path, head)
        result[path] = stream.read(int(head[2]))
        assert stream.read(1) == b"\n"
    assert not stream.read()
    return result


changed = git("diff", "--name-only", f"{BASE}...{TARGET}").decode().splitlines()
target_paths = set(git("ls-tree", "-r", "--name-only", TARGET).decode().splitlines())
base_paths = set(git("ls-tree", "-r", "--name-only", BASE).decode().splitlines())
manifest_path = "plugins/linker-tools/build/planner/source-manifest.json"
manifest = json.loads(git("show", f"{TARGET}:{manifest_path}"))
all_target_paths = set(changed) & target_paths
all_target_paths.update("apps/planner/" + path for path in manifest["sources"])
all_target_paths.update("plugins/linker-tools/build/planner/" + path for path in manifest["build"])
all_target_paths.update({"README.md", "AGENTS.md", "CONTEXT.md", "docs/adr/0002-isolated-planner-runtime.md"})
all_target_paths.add("plugins/linker-tools/languages/linker-tools-de_DE_formal.mo")
all_target_paths.add("plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json")
target = read_many(TARGET, all_target_paths)
base = read_many(BASE, ["apps/planner/package-lock.json"])

lock_path = "apps/planner/package-lock.json"
old_lock = json.loads(base[lock_path])["packages"]
new_lock = json.loads(target[lock_path])["packages"]
lock_lines = target[lock_path].decode().splitlines()
starts = {match.group(1): number for number, line in enumerate(lock_lines, 1)
          if (match := re.match(r'^\t\t"([^"]+)": \{$', line))}
added_packages = []
for package in sorted(set(new_lock) - set(old_lock)):
    value = new_lock[package]
    resolved = value.get("resolved")
    added_packages.append({"package": package, "version": value.get("version"),
                           "resolved": resolved, "integrity": value.get("integrity"),
                           "entry_line": starts[package],
                           "resolved_line": starts[package] + 2 if resolved else None})
added_mirror = [p for p in added_packages if p["resolved"] and "registry.npmmirror.com/" in p["resolved"]]
existing_changes = [p for p in set(old_lock) & set(new_lock) if p and old_lock[p] != new_lock[p]]
readme_rule = target["README.md"].decode().splitlines()[59]
assert "registry.npmjs.org" in readme_rule and "replace-registry-host=always" in readme_rule

build_mismatches = []
for group, prefix in [("sources", "apps/planner/"), ("build", "plugins/linker-tools/build/planner/")]:
    for name, expected in manifest[group].items():
        if sha(target[prefix + name]) != expected:
            build_mismatches.append(prefix + name)
assert not build_mismatches

css_path = "plugins/linker-commerce/content/windpress/planner-maplibre.css"
css = target[css_path].decode()
vendor_root = REPO / "apps/planner/node_modules/maplibre-gl"
original = (vendor_root / "dist/maplibre-gl.css").read_text()
licence = (vendor_root / "LICENSE.txt").read_text()
vendor_version = json.loads((vendor_root / "package.json").read_text())["version"]
opening, closing = "@layer components {\n@scope ([data-linker-planner]) {\n", "\n}\n}\n"
assert vendor_version == "5.24.0"
assert f"Source SHA256: {sha(original.encode())}" in css
assert licence in css and css.endswith(closing)
assert css[css.index(opening) + len(opening):-len(closing)] == original
assert not re.search(r"@import\s", original)
css_urls = re.findall(r"url\(\s*[\"']?([^\"')\s]+)", original)
assert css_urls and all(url.startswith("data:") for url in css_urls)

proof = "docs/acceptance/2026-10-22/548/map-display/"
reviewed = json.loads(target[proof + "copy-final.json"])
reviewed += json.loads(target[proof + "system-identity-copy/copy-final.json"])["messages"]
catalog = gettext.GNUTranslations(io.BytesIO(target["plugins/linker-tools/languages/linker-tools-de_DE_formal.mo"]))
locale_json = json.loads(target["plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json"])
locale_messages = locale_json["locale_data"]["messages"]
copy_gaps = []
for message in reviewed:
    if catalog.gettext(message["en"]) != message["de"]:
        copy_gaps.append({"en": message["en"], "channel": "MO"})
    if locale_messages.get(message["en"], [None])[0] != message["de"]:
        copy_gaps.append({"en": message["en"], "channel": "WP JSON"})
assert not copy_gaps

production_paths = [p for p in changed if p in target_paths and
                    (p.startswith("apps/planner/src/") or p.endswith((".php", ".css")))]
legacy_hits = []
for path in production_paths:
    if path == css_path:
        continue
    patch = git("diff", "--unified=0", f"{BASE}...{TARGET}", "--", path).decode()
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++") and re.search(r"tv_b2b_|Linker_AI_|dlk-", line):
            legacy_hits.append({"path": path, "added_line": line[1:]})
assert not legacy_hits

style_dir = "docs/research/2026-10-23-map-workbench-integration/provider-style/"
style = target[style_dir + "liberty-style.json"]
style_manifest = json.loads(target[style_dir + "style-manifest.json"])
assert len(style) == style_manifest["bytes"] and sha(style) == style_manifest["sha256"]
acquisition_dir = "docs/research/2026-10-23-map-workbench-integration/"
acquisition = json.loads(target[acquisition_dir + "map-display-primary/source-manifest.json"])
assert all(len(target[acquisition_dir + p]) == data["bytes"] and sha(target[acquisition_dir + p]) == data["sha256"]
           for p, data in acquisition.items())

diff = git("diff", "--no-ext-diff", f"{BASE}...{TARGET}")
result = {
    "at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "base": BASE, "target": TARGET, "full_diff_command": f"git diff {BASE}...{TARGET}",
    "commits": git("log", "--format=%H %s", f"{BASE}..{TARGET}").decode().splitlines(),
    "diff_bytes": len(diff), "diff_sha256": sha(diff),
    "files_in_full_fixed_diff": len(changed),
    "new_lock_packages": len(added_packages), "added_mirror_resolved_entries": len(added_mirror),
    "added_dependency_entries": added_packages, "modified_existing_dependency_entries": sorted(existing_changes),
    "documented_registry_rule": {"path": "README.md", "line": 60, "text": readme_rule,
                                 "owner_scope_readback": "Root reviewer confirmed the canonical registry rule applies to the isolated planner; existing mirror URLs do not waive it."},
    "source_build_manifest": {"source_count": len(manifest["sources"]), "build_count": len(manifest["build"]), "mismatches": build_mismatches},
    "vendor_css": {"version": vendor_version, "upstream_sha256": sha(original.encode()),
                   "full_licence_sha256": sha(licence.encode()), "full_licence_retained": True,
                   "scoped_body_exact": True, "all_css_urls_inline": True},
    "reviewed_copy": {"entries_including_shared_keys": len(reviewed), "unique_messages": len({m["en"] for m in reviewed}),
                      "MO_and_wordpress_JSON_gaps": copy_gaps},
    "new_legacy_identifier_hits": legacy_hits,
    "provider_style_and_acquisition_manifests": "fixed source bytes/digests matched",
    "file_inventory": [{"path": p, "bytes": len(target[p]), "sha256": sha(target[p])}
                       if p in target else {"path": p, "status": "removed"} for p in changed],
    "verification_boundary": "Static fixed-object readback only. Existing tests/build/PHP/locale logs inspected without rerunning suites. No checkout, snapshot, source copy, network, stack change or native execution.",
}
(OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ["base", "target", "files_in_full_fixed_diff", "new_lock_packages", "added_mirror_resolved_entries", "source_build_manifest", "vendor_css", "reviewed_copy", "new_legacy_identifier_hits"]}, ensure_ascii=False, indent=2))
