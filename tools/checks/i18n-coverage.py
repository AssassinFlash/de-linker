#!/usr/bin/env python3
"""German formal catalog coverage gate.

For every plugins/*/languages/*-de_DE_formal.po, untranslated entries
(msgattrib --untranslated --no-obsolete) minus the exemption list must be
zero. An exemption is a developer-facing string: a REST/Abilities JSON Schema
description, an ERP error returned as JSON, or a post type that no screen
shows. Customer and staff strings are not exempt.

Prints one line per catalog: path, untranslated, exempt, gap.
Also rejects obsolete messages still used in PHP gettext calls, JS/build
gettext calls or LiveCanvas fragment text/labels. Source usage is checked
independently of the POT's references.

For linker-tools (#302), runtime PHP/JS/TS messages in the plugin's text domain
must also exist in the PO, and every shipped script JSON must match the native
WP-CLI make-json output byte-for-byte. Regeneration runs in a temporary directory
with --no-purge so the source PO is never modified.

Exit 0 when every gap is 0 and no live message is obsolete. Exit 1 when a gap
remains, an exemption is stale, a live message is obsolete, or msgattrib fails.

Usage:
    python3 tools/checks/i18n-coverage.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from i18n_sources import catalog_msgids, code_references, source_references

ROOT = Path(__file__).resolve().parents[2]
EXEMPT_PATH = Path(__file__).resolve().parent / "i18n-exempt.json"


def catalogs() -> list[Path]:
    found = sorted(ROOT.glob("plugins/*/languages/*-de_DE_formal.po"))
    return [path.relative_to(ROOT) for path in found]


def untranslated(catalog: Path) -> list[str]:
    """msgids msgattrib reports as untranslated.

    The catalog header is the empty msgid whose msgstr holds the metadata.
    msgattrib still prints that header, so it is dropped here. A real entry
    always has a non-empty msgid.
    """
    result = subprocess.run(
        ["msgattrib", "--untranslated", "--no-obsolete", str(ROOT / catalog)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"i18n-coverage: msgattrib failed on {catalog}", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(1)
    entries: list[str] = []
    msgid: list[str] | None = None
    msgstr: list[str] | None = None
    for line in result.stdout.splitlines() + [""]:
        if line.startswith("msgid "):
            flush(entries, msgid, msgstr)
            msgid = [decode(line[len("msgid ") :])]
            msgstr = None
        elif line.startswith("msgstr"):
            msgstr = []
        elif line.startswith('"') and msgstr is not None:
            msgstr.append(decode(line))
        elif line.startswith('"') and msgid is not None:
            msgid.append(decode(line))
        elif line == "":
            flush(entries, msgid, msgstr)
            msgid = None
            msgstr = None
    return entries


def flush(
    entries: list[str], msgid: list[str] | None, msgstr: list[str] | None
) -> None:
    if not msgid:
        return
    text = "".join(msgid)
    # Header: empty msgid, metadata in msgstr. Not a translatable entry.
    if text == "":
        return
    translated = "".join(msgstr or [])
    if translated == "":
        entries.append(text)


def decode(quoted: str) -> str:
    return json.loads(quoted)


def load_exemptions() -> dict[str, list[dict[str, str]]]:
    data = json.loads(EXEMPT_PATH.read_text(encoding="utf-8"))
    catalogs_in = data.get("catalogs")
    if not isinstance(catalogs_in, dict):
        print("i18n-coverage: exemptions file has no catalogs object", file=sys.stderr)
        raise SystemExit(1)
    return catalogs_in


def script_json_problems(catalog: Path) -> list[str]:
    """Compare shipped script JSON byte-for-byte with native, non-purging output."""
    wp = shutil.which("wp")
    if wp is None:
        # Version source: tools/local/src/linker_local/wpcli.py (production).
        return ["JSON reproducibility requires WP-CLI 2.12 (the local stack version)."]
    with TemporaryDirectory(prefix="linker-i18n-") as directory:
        result = subprocess.run(
            [
                os.environ.get("PHP", "php"),
                wp,
                "i18n",
                "make-json",
                str(catalog),
                directory,
                "--no-purge",
                "--quiet",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return [f"JSON regeneration failed: {result.stderr.strip()}"]
        generated = {path.name: path for path in Path(directory).glob("*.json")}
        shipped = {path.name: path for path in catalog.parent.glob("*.json")}
        problems = []
        for name in sorted(generated.keys() | shipped.keys()):
            if name not in generated:
                problems.append(f"JSON not generated from PO: {name}")
            elif name not in shipped:
                problems.append(f"JSON missing from languages/: {name}")
            elif generated[name].read_bytes() != shipped[name].read_bytes():
                problems.append(f"JSON differs from make-json output: {name}")
        return problems


def planner_json_problems(
    plugin: Path, catalog: Path, references: dict[str, list[tuple[str, int]]]
) -> list[str]:
    """PO presence alone does not bind a reused message to this script module."""
    messages = {
        msgid
        for msgid, paths in references.items()
        if any(
            path.replace("\\", "/").startswith("../../apps/planner/src/")
            for path, _ in paths
        )
    }
    if not messages:
        return []
    try:
        manifest = json.loads((plugin / "build/planner/vite-manifest.json").read_text())
        script = "build/planner/" + manifest["src/main.tsx"]["file"]
        # Native WP-CLI and wp_set_script_module_translations name JSON by
        # md5 of the plugin-relative script path; this is not a security hash.
        suffix = hashlib.md5(script.encode(), usedforsecurity=False).hexdigest()
        path = catalog.with_name(catalog.stem + "-" + suffix + ".json")
        data = json.loads(path.read_text())["locale_data"]["messages"]
    except (OSError, ValueError, KeyError, TypeError):
        return ["planner script JSON is missing or invalid"]
    if not isinstance(data, dict):
        return ["planner script JSON is missing or invalid"]
    return [
        f"planner script JSON lacks source msgid: {msgid!r}"
        for msgid in sorted(messages)
        if not data.get(msgid)
    ]


def main() -> int:
    exemptions = load_exemptions()
    found = catalogs()
    if not found:
        print("i18n-coverage: no de_DE_formal catalogs", file=sys.stderr)
        return 1

    failed = False
    known = {str(path) for path in found}
    for name in sorted(exemptions):
        if name not in known:
            print(
                f"i18n-coverage: exemption names a missing catalog: {name}",
                file=sys.stderr,
            )
            failed = True

    for catalog in found:
        plugin = (ROOT / catalog).parent.parent
        if plugin.name == "linker-tools":
            messages = set(catalog_msgids(ROOT / catalog))
            runtime_sources = code_references(plugin)
            missing_source = {
                msgid: references
                for msgid, references in runtime_sources.items()
                if msgid not in messages
            }
            for msgid, references in missing_source.items():
                print(f"{catalog}: source msgid missing from PO: {msgid!r}")
                for path, line in references:
                    print(f"  source: {plugin.relative_to(ROOT)}/{path}:{line}")
                failed = True
            problems = script_json_problems(ROOT / catalog)
            problems.extend(
                planner_json_problems(plugin, ROOT / catalog, runtime_sources)
            )
            for problem in problems:
                print(f"{catalog}: {problem}")
                failed = True
            print(
                f"{catalog}: source gaps={len(missing_source)} "
                f"JSON problems={len(problems)}"
            )
        used_obsolete = source_references(
            plugin, catalog_msgids(ROOT / catalog, obsolete=True)
        )
        for msgid, references in used_obsolete.items():
            print(f"{catalog}: live msgid is obsolete: {msgid!r}")
            for path, line in references:
                print(f"  source: {plugin.relative_to(ROOT)}/{path}:{line}")
            failed = True
        missing = untranslated(catalog)
        rows = exemptions.get(str(catalog), [])
        allowed = {row["msgid"] for row in rows}
        stale = sorted(allowed - set(missing))
        gap = [entry for entry in missing if entry not in allowed]
        print(
            f"{catalog}: untranslated={len(missing)} exempt={len(missing) - len(gap)} "
            f"gap={len(gap)}"
        )
        for entry in gap:
            print(f"  gap: {entry}")
            failed = True
        for entry in stale:
            print(f"  stale exemption (now translated or gone): {entry}")
            failed = True

    if failed:
        print("i18n-coverage: FAIL", file=sys.stderr)
        return 1
    print("i18n-coverage: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
