"""Capture pages of a local instance as the page reader's test fixtures.

    uv run python eval/page/capture_pages.py http://127.0.0.1:9102 tests/fixtures/pages

Keeps each page's `<main>` element only (page.py reads nothing else), so the fixtures
stay small. Run it against an instance loaded with the latest live snapshot
(`just sync <instance>`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

# One page of each kind the tests read: the FAQ page (longer than the budget), a
# blog post, a German solution page and a product page.
PAGES = {
    "faq-en.html": "/faq-download/",
    "blog-post-en.html": "/hybrid-inverter-vs-ac-coupled-storage/",
    "solution-de.html": "/de/loesung/heimspeicher/",
    "product-en.html": "/product/goodwe-esa-gw10k-eha-g20-10-kw-single-phase-power-module/",
}
_MAIN = re.compile(r"<main\b.*</main>", re.DOTALL)
# What the reader never reads (page._MainText._SKIP): dropped to keep the fixtures small.
_NOT_TEXT = re.compile(r"<(script|style|svg)\b.*?</\1>", re.DOTALL)


def main() -> None:
    base, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base, timeout=30.0, follow_redirects=True) as client:
        for name, path in PAGES.items():
            response = client.get(path)
            response.raise_for_status()
            found = _MAIN.search(response.text)
            if found is None:
                raise SystemExit(f"{path}: no <main>")
            kept = _NOT_TEXT.sub("", found.group(0))
            (out / name).write_text(kept + "\n", encoding="utf-8")
            print(f"{name}: {len(kept)} characters")


if __name__ == "__main__":
    main()
