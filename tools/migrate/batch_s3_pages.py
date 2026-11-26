"""Publish or restore the reviewed bilingual storage descriptions and site tagline."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

import reviewed_page_pair as pairs
from batch_r3_pages import PAGES, save

FIELDS = (
    "_seopress_titles_desc",
    "_seopress_social_fb_desc",
    "_seopress_social_twitter_desc",
)
TAGLINE = "Residential and C&I energy storage systems — Linker Technology GmbH"
DESCRIPTIONS = {
    "home": (
        "Get solar and storage projects moving with matched systems, documented compatibility and practical technical support from Linker.",
        "Solar- und Speicherprojekte voranbringen: mit passenden Systemen, dokumentierter Kompatibilität und technischer Unterstützung von Linker.",
    ),
    "about": (
        "Build your next solar and storage project with Linker: matched systems, documented compatibility and technical support for installers and EPCs in Europe.",
        "Ihr Partner für Solar- und Speicherprojekte: passende Systeme, dokumentierte Kompatibilität und technische Unterstützung für Installateure in Europa.",
    ),
    "for-installer": (
        "Find matching solar and storage equipment for each installation, with documented compatibility, system sizing and technical support from Linker.",
        "Passende Solar- und Speichersysteme für Ihre Projekte. Linker unterstützt Sie bei der Auslegung und dokumentiert, welche Geräte zusammenpassen.",
    ),
}


def desired_values(name: str, stored: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        str(pid): dict.fromkeys(stored[str(pid)], description)
        for pid, description in zip(PAGES[name], DESCRIPTIONS[name], strict=True)
    }


def update_pair(wp: str, folder: Path, name: str, action: str) -> None:
    changes = [{"id": pid, "keys": FIELDS} for pid in PAGES[name]]
    request = {"mode": "read_descriptions", "changes": changes}
    current = pairs.invoke(wp, request)
    path = folder / f"{name}.json"
    if not path.exists():
        if action in ("restore", "read"):
            raise ValueError(f"{name}: missing approved snapshot")
        after = current | {"values": desired_values(name, current["values"])}
        if after != current and current["current"]:
            preview = pairs.invoke(
                wp,
                {
                    "mode": "preview_page_adoption",
                    "changes": [
                        {"id": pid, "descriptions": fields}
                        for pid, fields in after["values"].items()
                    ],
                },
            )
            after["metadata"] = preview["expected_metadata"]
        save(path, {"before": current, "after": after})
    receipt = json.loads(path.read_text())
    before, after = receipt["before"], receipt["after"]
    if current not in (before, after):
        raise ValueError(f"{name}: published fields differ from the reviewed pair")
    target = before if action == "restore" else after
    if action == "backup" or current == target:
        return
    if action == "read":
        raise ValueError(f"{name}: reviewed fields are not live")
    pairs.invoke(
        wp,
        {
            "mode": "save_descriptions",
            "changes": changes,
            "before": current["values"],
            "after": target["values"],
            "metadata_before": current["metadata"],
            "expected_metadata": target["metadata"],
            "require_current": current["current"],
        },
    )
    if pairs.invoke(wp, request) != target:
        raise RuntimeError(f"{name}: bilingual publication readback failed")


def tagline(wp: str, folder: Path, action: str) -> None:
    def command(*args: str) -> str:
        prefix = shlex.split(wp)
        options = [shlex.join(args)] if Path(prefix[0]).name == "ssh" else list(args)
        return subprocess.check_output([*prefix, *options], text=True).rstrip("\n")

    path = folder / "tagline.json"
    original = command("option", "get", "blogdescription")
    if not path.exists():
        if action in ("restore", "read"):
            raise ValueError("Missing original site tagline")
        save(
            path,
            {
                "before": original,
                "after": TAGLINE,
                "site": command("option", "get", "home"),
            },
        )
    saved = json.loads(path.read_text())
    if saved["site"] != command("option", "get", "home") or original not in (
        saved["before"],
        TAGLINE,
    ):
        raise ValueError("The site or tagline differs from the reviewed snapshot")
    wanted = saved["before"] if action == "restore" else TAGLINE
    if action == "backup" or wanted == original:
        return
    if action == "read":
        raise ValueError("Reviewed site tagline is not live")
    command("option", "update", "blogdescription", wanted)
    if command("option", "get", "blogdescription") != wanted:
        raise RuntimeError("Site tagline readback failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group(required=True)
    for action in ("backup", "apply", "read", "restore"):
        flags.add_argument(
            "--" + action, dest="action", action="store_const", const=action
        )
    parser.add_argument("--wp", default="wp", help="WP-CLI prefix for the target site")
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    for action in ["backup", "apply"] if args.action == "apply" else [args.action]:
        for name in DESCRIPTIONS:
            update_pair(args.wp, args.backup_dir, name, action)
        tagline(args.wp, args.backup_dir, action)


if __name__ == "__main__":
    main()
