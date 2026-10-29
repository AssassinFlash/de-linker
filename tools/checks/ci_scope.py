"""Select and audit CI package lanes from the actual Git diff."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LANES = (
    "presentation",
    "php",
    "commerce",
    "tools",
    "planner",
    "engine",
    "genie",
    "python",
    "content",
    "build",
    "mu",
)
FULL_LANES = tuple(lane for lane in LANES if lane != "presentation")
WORKFLOW = ".github/workflows/check.yml"


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def document(path):
    return path in {"AGENTS.md", "CLAUDE.md", "CONTEXT.md", "README.md"} or (
        path.startswith("docs/") and path.endswith((".md", ".rst", ".txt"))
    )


def acceptance_record(path):
    return path.startswith("docs/acceptance/") and path.endswith(
        (".json", ".png", ".pdf", ".jpg", ".jpeg")
    )


def non_runtime_file(commit, path):
    if git("ls-tree", commit, "--", path).split()[0] != b"100644":
        return False
    content = git("show", f"{commit}:{path}")
    if acceptance_record(path):
        if path.endswith(".png"):
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if path.endswith((".jpg", ".jpeg")):
            return content.startswith(b"\xff\xd8\xff")
        if path.endswith(".pdf"):
            return content.startswith(b"%PDF-")
        json.loads(content)
        return True
    if b"\0" in content:
        return False
    content.decode("utf-8")
    return True


def regular_change(status, path, base, head):
    revisions = {"M": (base, head), "A": (head,), "D": (base,)}.get(status, ())
    return bool(revisions) and all(
        git("ls-tree", rev, "--", path).split()[0] == b"100644" for rev in revisions
    )


def non_runtime_change(status, path, base, head):
    revisions = {"M": (base, head), "A": (head,), "D": (base,)}.get(status, ())
    return bool(revisions) and all(non_runtime_file(rev, path) for rev in revisions)


def commerce(path):
    return bool(
        re.fullmatch(
            r"plugins/linker-commerce/(includes/(Presentation/(ProductShortcodes|LanguageLinks|LibraryPage)[.]php|Storefront/ProductView[.]php|Registration/PendingProfileCapacity[.]php)|assets/[a-z0-9-]+[.]js|content/(livecanvas/(de/)?[a-z0-9_-]+[.]html|windpress/[a-z0-9_-]+[.]css)|languages/linker-commerce-de_DE_formal[.](po|mo)|tests/php/(Unit/(Presentation/(ProductShortcodes|LanguageLinks|LibraryPage)Test[.]php|Storefront/ProductViewTest[.]php)|Integration/RegistrationCapacityTest[.]php)|tests/js/[a-z0-9-]+[.]test[.]mjs)",
            path,
        )
    )


def presentation(path):
    return (
        bool(
            re.fullmatch(
                r"plugins/linker-commerce/content/(livecanvas/(de/)?[a-z0-9_-]+[.]html|windpress/[a-z0-9_-]+[.]css)",
                path,
            )
        )
        or path
        == "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php"
    )


def manifest_entries(commit):
    value = json.loads(
        git(
            "show",
            f"{commit}:plugins/linker-tools/build/manifest.json",
        )
    )
    if set(value) != {"sources", "build"}:
        raise ValueError("Unexpected Tools manifest")
    for section in value.values():
        if not isinstance(section, dict) or not all(
            isinstance(path, str)
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            for path, digest in section.items()
        ):
            raise ValueError("Invalid Tools manifest entries")
    return value


def planner_manifest_isolated(base, head):
    if not base or not head:
        return False
    before = manifest_entries(base)
    after = manifest_entries(head)
    if before["sources"] != after["sources"]:
        return False
    for entries in (before["build"], after["build"]):
        if not any(path.startswith("build/planner/") for path in entries):
            return False
    before_other = {
        path: digest
        for path, digest in before["build"].items()
        if not path.startswith("build/planner/")
    }
    after_other = {
        path: digest
        for path, digest in after["build"].items()
        if not path.startswith("build/planner/")
    }
    return before_other == after_other


def classify(changes, base="", head=""):
    if not changes or any(status not in {"A", "M", "D"} for status, _ in changes):
        return list(FULL_LANES)
    if all(
        (document(path) or acceptance_record(path))
        and non_runtime_change(status, path, base, head)
        for status, path in changes
    ):
        return []
    if all(
        (document(path) or acceptance_record(path))
        or (status == "M" and presentation(path))
        for status, path in changes
    ) and all(
        non_runtime_change(status, path, base, head)
        if document(path) or acceptance_record(path)
        else regular_change(status, path, base, head)
        for status, path in changes
    ):
        return ["presentation"]
    if any(
        not (
            non_runtime_change(status, path, base, head)
            if document(path) or acceptance_record(path)
            else regular_change(status, path, base, head)
        )
        for status, path in changes
    ):
        return list(FULL_LANES)
    lanes = set()
    planner_changed = any(
        path.startswith("apps/planner/")
        or path.startswith("plugins/linker-tools/build/planner/")
        for _, path in changes
    )
    for status, path in changes:
        if document(path) or acceptance_record(path):
            continue
        if path.startswith("apps/planner/") or path.startswith(
            "plugins/linker-tools/build/planner/"
        ):
            lanes.add("planner")
        elif path == "plugins/linker-tools/build/manifest.json":
            if not planner_changed or not planner_manifest_isolated(base, head):
                return list(FULL_LANES)
        elif path.startswith("services/engine/"):
            lanes.add("engine")
        elif path.startswith("services/genie/"):
            lanes.add("genie")
        elif status == "M" and commerce(path):
            lanes.add("commerce")
            lanes.add("mu")
        else:
            return list(FULL_LANES)
    return [lane for lane in LANES if lane in lanes]


def diff_changes(base, head):
    def records(*options):
        raw = git("diff", "--name-status", "-z", *options, base, head)
        if not raw:
            return []
        fields = raw.decode(errors="surrogateescape").split("\0")
        if fields[-1]:
            raise ValueError("Incomplete Git name-status record")
        fields = fields[:-1]
        changes = []
        while fields:
            status = fields.pop(0)
            if not fields:
                raise ValueError("Missing path in Git name-status record")
            path = fields.pop(0)
            if status.startswith(("R", "C")):
                if not fields:
                    raise ValueError("Missing destination in Git structural record")
                fields.pop(0)
            changes.append((status, path))
        return changes

    changes = records("--no-renames")
    structural = [
        (status, path)
        for status, path in records("--find-renames", "--find-copies")
        if status not in {"A", "M", "D"}
    ]
    return structural + changes


def api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def latest_run(sha, event=""):
    repo = os.environ["REPOSITORY"]
    endpoint = (
        f"repos/{repo}/actions/workflows/check.yml/runs?head_sha={sha}&per_page=100"
    )
    if event:
        endpoint += "&event=" + event
    runs = api(endpoint)["workflow_runs"]
    runs = [
        run
        for run in runs
        if run["head_sha"] == sha
        and run["path"] == WORKFLOW
        and run["event"] in {"pull_request", "push", "workflow_dispatch"}
        and (not event or run["event"] == event)
    ]
    return max(
        runs, key=lambda run: (run["run_number"], run["run_attempt"]), default=None
    )


def validated_scope(run):
    if not run or run["status"] != "completed" or run["conclusion"] != "success":
        return None
    repo = os.environ["REPOSITORY"]
    jobs = api(
        f"repos/{repo}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100"
    )["jobs"]
    for job in jobs:
        for step in job.get("steps", []):
            marker = re.fullmatch(
                r"Record (?:validation|validated) scope \((docs|full|scoped|commerce|presentation|reuse)\)",
                step["name"],
            )
            if marker and step.get("conclusion") == "success":
                return marker.group(1)
    return None


def checked_run(run, commit, *, full=False, docs_only=False):
    if not run or run["status"] != "completed" or run["conclusion"] != "success":
        return False
    if git("rev-parse", f"{commit}:{WORKFLOW}") != git("rev-parse", f"HEAD:{WORKFLOW}"):
        return False
    marker = re.fullmatch(
        r"check #[^\n]+ [|] tree-ref=([0-9a-f]{40})",
        run.get("display_title", ""),
    )
    if not marker:
        return False
    tested = marker.group(1)
    try:
        tree = git("rev-parse", tested + "^{tree}").decode().strip()
    except subprocess.CalledProcessError:
        repo = os.environ["REPOSITORY"]
        tree = api(f"repos/{repo}/git/commits/{tested}")["tree"]["sha"]
    if tree != git("rev-parse", commit + "^{tree}").decode().strip():
        return False
    scope = validated_scope(run)
    if full:
        return scope == "full"
    if docs_only:
        return scope == "docs"
    return scope in {"docs", "full", "scoped", "commerce", "presentation", "reuse"}


def checked_pr_tree(commit, *, full=False):
    source = git("rev-parse", commit + "^2").decode().strip()
    run = latest_run(source, "pull_request")
    return run if checked_run(run, commit, full=full) else None


def checked_base(commit):
    seen = set()
    while commit not in seen:
        seen.add(commit)
        run = latest_run(commit)
        if checked_run(run, commit, full=True):
            return True
        if checked_run(run, commit, docs_only=True):
            try:
                parent = git("rev-parse", commit + "^1").decode().strip()
            except subprocess.CalledProcessError:
                git("fetch", "--deepen=1", "origin", commit)
                parent = git("rev-parse", commit + "^1").decode().strip()
            changes = diff_changes(parent, commit)
            if classify(changes, parent, commit) or not all(
                non_runtime_change(status, path, parent, commit)
                for status, path in changes
            ):
                return False
            commit = parent
            continue
        if (
            run
            and run["status"] == "completed"
            and run["conclusion"] == "success"
            and validated_scope(run) == "reuse"
        ):
            return bool(checked_pr_tree(commit, full=True))
        if run and (run["status"] != "completed" or run["conclusion"] != "cancelled"):
            return False
        return bool(checked_pr_tree(commit, full=True))
    return False


def write_output(name, value):
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"{name}={value}\n")


def plan():
    event = os.environ["EVENT_NAME"]
    head = os.environ["HEAD_SHA"]
    base = os.environ.get("BASE_SHA", "")
    changes = []
    candidate = list(FULL_LANES)
    mode = "full"
    reason = "The complete package and native integration checks are required."
    error = ""
    if base and set(base) != {"0"}:
        try:
            try:
                git("cat-file", "-e", base + "^{commit}")
            except subprocess.CalledProcessError:
                git("fetch", "--depth=1", "origin", base)
            subprocess.run(["git", "diff", "--check", base, head], check=True)
            changes = diff_changes(base, head)
            candidate = classify(changes, base, head)
            if event == "pull_request":
                if not candidate:
                    mode = "docs"
                    reason = "Documentation and acceptance records only."
                elif candidate != list(FULL_LANES):
                    try:
                        proven = checked_base(base)
                    except (OSError, subprocess.SubprocessError, KeyError, ValueError):
                        proven = False
                    if proven:
                        mode = "scoped"
                        reason = "Only declared package inputs changed on a fully checked base."
                    else:
                        reason = (
                            "No fully checked base; narrow selection is not allowed."
                        )
        except (
            OSError,
            subprocess.SubprocessError,
            UnicodeError,
            KeyError,
            ValueError,
            IndexError,
        ) as exception:
            error = f"{type(exception).__name__}: {exception}"
            candidate = list(FULL_LANES)
            mode = "full"
            reason = "The complete diff could not be proven; the final gate will reject an incomplete ledger."
    if event == "push":
        if not candidate and changes and not error:
            mode = "docs"
            reason = "Documentation and acceptance records only."
        else:
            mode = "full"
            try:
                run = checked_pr_tree(head)
                if run:
                    mode = "reuse"
                    reason = f"Identical Git tree already checked by pull-request run {run['id']}."
            except (OSError, subprocess.SubprocessError, KeyError, ValueError):
                reason = "No proven successful check for this tree; complete checks required."
    selected = (
        []
        if mode in {"docs", "reuse"}
        else list(FULL_LANES)
        if mode == "full"
        else candidate
    )
    ledger = {
        "base": base,
        "head": head,
        "mode": mode,
        "candidate": candidate,
        "lanes": selected,
        "changes": [{"status": status, "path": path} for status, path in changes],
    }
    if error:
        ledger["error"] = error
    write_output("mode", mode)
    write_output("ledger", json.dumps(ledger, separators=(",", ":")))
    for lane in LANES:
        write_output(lane, str(lane in selected).lower())
    write_output(
        "catalog_changed",
        str(
            any(
                path.startswith("plugins/linker-commerce/content/livecanvas/")
                for _, path in changes
            )
        ).lower(),
    )
    write_output(
        "php_test_changed",
        str(
            any(
                path
                == "plugins/linker-commerce/tests/php/Unit/Presentation/TemplatesTest.php"
                for _, path in changes
            )
        ).lower(),
    )
    write_output(
        "planner_build_changed",
        str(
            any(
                path.startswith("plugins/linker-tools/build/planner/")
                for _, path in changes
            )
        ).lower(),
    )
    lines = [
        f"### Validation scope: {mode}",
        "",
        reason,
        "",
        "| Status | Path | Package lane |",
        "| --- | --- | --- |",
    ]
    for status, path in changes:
        isolated = classify([(status, path)], base, head) if base else FULL_LANES
        lanes = ", ".join(isolated) if isolated != FULL_LANES else "full"
        lines.append(f"| {status} | `{path.replace('|', chr(92) + '|')}` | {lanes} |")
    if error:
        lines.extend(["", f"Ledger error: `{error}`"])
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def audit_gate(ledger, results, changes):
    errors = []
    if results.get("plan", {}).get("result") != "success":
        return ["plan did not succeed"]
    if ledger.get("base") != os.environ.get("BASE_SHA", "") or ledger.get(
        "head"
    ) != os.environ.get("HEAD_SHA"):
        errors.append("plan and gate use different commits")
    recorded = [(item["status"], item["path"]) for item in ledger.get("changes", [])]
    if recorded != changes:
        errors.append("the changed-path ledger is incomplete or different")
    candidate = classify(changes, ledger.get("base", ""), ledger.get("head", ""))
    if ledger.get("candidate") != candidate:
        errors.append("the independently recomputed package selection differs")
    mode = ledger.get("mode")
    event = os.environ.get("EVENT_NAME", "")
    selected = ledger.get("lanes")
    if mode not in {"docs", "full", "scoped", "reuse"}:
        errors.append("unrecognized validation mode")
    if (
        not isinstance(selected, list)
        or set(selected) - set(LANES)
        or len(selected) != len(set(selected))
    ):
        errors.append("invalid lane list")
        selected = []
    if mode in {"docs", "reuse"} and selected:
        errors.append("a documentation or reused run cannot execute package jobs")
    if mode == "docs" and (candidate or event not in {"pull_request", "push"}):
        errors.append("documentation scope requires only non-runtime changes")
    if mode == "reuse" and event != "push":
        errors.append("identical-tree reuse is only valid for a main push")
    if mode == "scoped" and (
        not selected
        or selected != candidate
        or candidate == list(FULL_LANES)
        or event != "pull_request"
    ):
        errors.append("the scoped jobs do not match the changed packages")
    if mode == "full" and selected != list(FULL_LANES):
        errors.append("full validation does not select every required package")
    for lane in LANES:
        actual = results.get(lane, {}).get("result")
        expected = "success" if lane in selected else "skipped"
        if actual != expected:
            errors.append(f"{lane}: expected {expected}, got {actual}")
    return errors


def gate():
    ledger = json.loads(os.environ["EXPECTED_LEDGER"])
    results = json.loads(os.environ["JOB_RESULTS"])
    if git("rev-parse", "HEAD").decode().strip() != os.environ["HEAD_SHA"]:
        raise ValueError("The gate checked out a different commit")
    base = os.environ["BASE_SHA"]
    if base and set(base) != {"0"}:
        try:
            git("cat-file", "-e", base + "^{commit}")
        except subprocess.CalledProcessError:
            git("fetch", "--depth=1", "origin", base)
        changes = diff_changes(base, os.environ["HEAD_SHA"])
    else:
        changes = []
    errors = audit_gate(ledger, results, changes)
    if not errors and ledger["mode"] in {"scoped", "reuse"}:
        try:
            proven = (
                checked_base(base)
                if ledger["mode"] == "scoped"
                else bool(checked_pr_tree(os.environ["HEAD_SHA"]))
            )
        except (OSError, subprocess.SubprocessError, KeyError, ValueError):
            proven = False
        if not proven:
            errors.append(f"the {ledger['mode']} proof could not be reproduced")
    for lane in LANES:
        print(f"{lane}: {results.get(lane, {}).get('result')}")
    if errors:
        for error in errors:
            print(f"GATE FAILURE: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"Validated {ledger['mode']}: every selected job succeeded; every other job was skipped."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "classify", "gate"))
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    if args.command == "plan":
        plan()
    elif args.command == "gate":
        gate()
    else:
        changes = diff_changes(args.base, args.head)
        print(
            json.dumps(
                {"changes": changes, "lanes": classify(changes, args.base, args.head)},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
