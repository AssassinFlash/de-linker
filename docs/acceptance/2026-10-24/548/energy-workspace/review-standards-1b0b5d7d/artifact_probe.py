"""Read pinned artifacts; write nothing and use no third-party dependencies."""

from __future__ import annotations

import gettext
import io
import json
from pathlib import Path
import re
import subprocess


PIN = "1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb"
REPO = Path(__file__).resolve().parents[6]
EVIDENCE = "docs/acceptance/2026-10-24/548/energy-workspace"
LANGUAGES = "plugins/linker-tools/languages"


def pinned_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{PIN}:{path}"], cwd=REPO)


def pinned_json(path: str):
    return json.loads(pinned_bytes(path))


def main() -> None:
    needed = pinned_json(f"{EVIDENCE}/copy-german-needed.json")
    final = pinned_json(f"{EVIDENCE}/copy-german-final.json")
    assert len(needed) == len(final) == 187
    assert {entry["text"] for entry in needed} == set(final)
    mo = gettext.GNUTranslations(
        io.BytesIO(pinned_bytes(f"{LANGUAGES}/linker-tools-de_DE_formal.mo"))
    )
    wp = pinned_json(
        f"{LANGUAGES}/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json"
    )["locale_data"]["messages"]
    placeholder = re.compile(r"%(?:[1-9][0-9]*\$)?[ds]")
    for english, german in final.items():
        assert german.strip(), english
        assert sorted(placeholder.findall(english)) == sorted(
            placeholder.findall(german)
        ), english
        assert mo.gettext(english) == german, english
        assert wp[english] == [german], english
    print("PASS: all 187 new German entries, placeholders, compiled MO and WP JSON agree.")

    run = pinned_json("apps/planner/tests/fixtures/energy-run.json")
    actual = pinned_json(
        "docs/acceptance/2026-10-24/548/managed-energy-worker/http.json"
    )["finished"]
    assert run == actual
    print("PASS: entire browser energy-run fixture equals the recorded managed HTTP result.")
    print(f"Pinned source: {PIN}")


if __name__ == "__main__":
    main()
