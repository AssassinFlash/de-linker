#!/usr/bin/env python3
"""Assert the WindPress volume can compile the header foundation.

After `wp linker-commerce present`, the volume directory must hold tokens.css
and site-base.css, and main.css must import both. This is the check the
acceptance record runs; it does not compile.

Usage: python3 tools/windpress_volume_check.py <instance>
Prints one JSON object. Exits 1 when a required file or import is missing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path.home() / "de-linker-local"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: windpress_volume_check.py <instance>", file=sys.stderr)
        return 2
    data = ROOT / sys.argv[1] / "wordpress" / "wp-content" / "uploads" / "windpress" / "data"
    required = ("tokens.css", "site-base.css")
    missing: list[str] = []
    sizes: dict[str, int] = {}
    for name in required:
        path = data / name
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(name)
            continue
        sizes[name] = path.stat().st_size
    entry = data / "main.css"
    main_css = entry.read_text(encoding="utf-8") if entry.is_file() else ""
    imports = {name: f'"./{name}"' in main_css or f'"{name}"' in main_css for name in required}
    for name, present in imports.items():
        if not present:
            missing.append(f"main.css import {name}")
    report = {
        "data_dir": str(data),
        "sizes": sizes,
        "imports": imports,
        "missing": missing,
        "ok": not missing,
    }
    print(json.dumps(report))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
