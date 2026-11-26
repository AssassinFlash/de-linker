"""Publish or restore the S1 solution product links and German search copy."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import reviewed_page_pair as pairs
from batch_r3_pages import PAGES, publish_pair, save

SCOPES = {
    "solution": "hub",
    "residential-storage": "residential",
    "commercial-storage": "commercial",
    "utility-storage": "utility",
}
SEO = {
    "utility-storage": (
        "_seopress_titles_title",
        "Großspeicher für Energieprojekte | Linker",
        "Batteriegroßspeicher für Energieprojekte | Linker",
    ),
    "residential-storage": (
        "_seopress_titles_desc",
        "Ihre Kunden möchten mehr eigenen Solarstrom nutzen. Linker kombiniert passende Hybrid-Wechselrichter und Batteriespeicher mit Notstromoptionen und Produktsupport.",
        "Ihre Kunden möchten mehr eigenen Solarstrom nutzen. Linker kombiniert Hybrid-Wechselrichter und Batteriespeicher mit Notstromoptionen und Produktsupport.",
    ),
    "services-support": (
        "_seopress_titles_desc",
        "Technische Unterstützung für Ihre Solar- und Speicherprojekte. Linker hilft bei der Auslegung, der Inbetriebnahme und bei Fragen zu Produkten und Garantiefällen.",
        "Technischer Support für Solar- und Speicherprojekte. Linker hilft bei der Auslegung, der Inbetriebnahme und bei Fragen zu Produkten und Garantiefällen.",
    ),
}
H2_BEFORE = "Containerspeicher für die Anforderungen Ihres Projekts."
H2_AFTER = "Batteriegroßspeicher: Containerspeicher für Netz- und Energieprojekte."


def page_content(name: str, de: bool, content: str) -> str:
    if de and name == "utility-storage":
        first = re.search(r"(<h2\b[^>]*>)(.*?)</h2>", content, re.S | re.I)
        if not first or first[2] not in (H2_BEFORE, H2_AFTER):
            raise ValueError("The first German utility heading has changed")
        content = content[: first.start(2)] + H2_AFTER + content[first.end(2) :]
    shortcode = f'[linker_solution_products scope="{SCOPES[name]}"]'
    if shortcode in content:
        return content
    matches = list(re.finditer(r'<section\b[^>]*\bid="contact"[^>]*>', content))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected the closing contact section")
    pos = matches[0].start()
    return content[:pos] + shortcode + "\n" + content[pos:]


def seo_read(wp: str, name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    changes = [{"id": pid, "keys": [SEO[name][0]]} for pid in PAGES[name]]
    return changes, pairs.invoke(wp, {"mode": "read_descriptions", "changes": changes})


def seo_update(wp: str, folder: Path, name: str, action: str) -> None:
    changes, state = seo_read(wp, name)
    key, old, new = SEO[name]
    de = str(PAGES[name][1])
    path = folder / f"{name}-seo-change.json"
    value = state["values"][de][key]
    if action == "restore":
        if not path.exists():
            original = json.loads((folder / f"{name}-seo-before.json").read_text())
            if (
                state["home"] != original["home"]
                or state["values"] != original["values"]
            ):
                raise ValueError(
                    f"{name}: SEO values differ from their original backup"
                )
            return
        receipt = json.loads(path.read_text())
        target = receipt["before"]
        if state == target:
            return
        if state != receipt["after"]:
            raise ValueError(f"{name}: SEO fields or translation changed since release")
    else:
        if value == new:
            print(f"{name}: SEO current", flush=True)
            return
        if value != old or action == "read":
            raise ValueError(f"{name}: unexpected SEO field")
        if action == "dry-run":
            print(f"{name}: 1 German SEO field", flush=True)
            return
        values = {pid: dict(fields) for pid, fields in state["values"].items()}
        values[de][key] = new
        metadata = state["metadata"]
        if state["current"]:
            preview = pairs.invoke(
                wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": [
                        {"id": int(pid), "descriptions": fields}
                        for pid, fields in values.items()
                    ],
                },
            )
            metadata = preview["expected_metadata"]
        target = state | {"values": values, "metadata": metadata}
        receipt = {"before": state, "after": target}
        save(path, receipt)
        if json.loads(path.read_text()) != receipt:
            raise ValueError(f"{name}: SEO recovery point differs")
    pairs.invoke(
        wp,
        {
            "mode": "save_descriptions",
            "changes": changes,
            "before": state["values"],
            "after": target["values"],
            "require_current": state["current"],
            "metadata_before": state["metadata"],
            "expected_metadata": target["metadata"],
        },
    )
    if seo_read(wp, name)[1] != target:
        raise RuntimeError(f"{name}: SEO readback differs")
    print(f"{name}: German SEO field saved", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("dry-run", "backup", "apply", "read", "restore")
    )
    parser.add_argument("--wp", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    folder, wp, action = args.backup_dir, args.wp, args.action
    names = list(dict.fromkeys([*SCOPES, *SEO]))
    # Preserve all five pairs and the SEO fields before the first write.
    if action in ("dry-run", "backup", "apply"):
        for name in names:
            save(folder / f"{name}-before.json", pairs.read(wp, *PAGES[name]))
            if name in SEO:
                save(folder / f"{name}-seo-before.json", seo_read(wp, name)[1])
        if action == "backup":
            return
    if action == "restore":
        for name in SEO:
            seo_update(wp, folder, name, action)
    for name in SCOPES:
        ids = PAGES[name]
        state = pairs.read(wp, *ids)
        after = None
        if action != "restore":
            after = {
                str(pid): page_content(name, pid == ids[1], state["pages"][str(pid)])
                for pid in ids
            }
        if action == "dry-run":
            count = (
                sum(after[pid] != html for pid, html in state["pages"].items())
                if after
                else 0
            )
            print(f"{name}: {count} page changes", flush=True)
        else:
            publish_pair(wp, action, folder, name, ids, state, after)
    if action != "restore":
        for name in SEO:
            seo_update(wp, folder, name, action)


if __name__ == "__main__":
    main()
