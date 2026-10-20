"""#405 cases registered for #339.

The four reads run on a local instance (`just page-cache-chain`). This module
only checks that the registration is still on disk, the way a harness case is
checked: `just test` does not start WordPress.

docs/acceptance/2026-10-20/405/cases.md is the index.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "405" / "page-cache.json"
INDEX = REPO / "docs" / "acceptance" / "2026-10-20" / "405" / "cases.md"
PHP = REPO / "plugins/linker-tools/tests/php/Integration/PageCacheChainTest.php"
PROBE = Path(__file__).parent / "page_cache_probe.py"
IDS = ("405-product-en", "405-product-de", "405-blog-en", "405-blog-de")


def test_the_page_cache_cases_are_registered_for_339() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw["ticket"] == 405
    assert raw["regression"] == 339
    assert raw["command"] == "just page-cache-chain <instance>"
    assert [case["id"] for case in raw["cases"]] == list(IDS)
    php = PHP.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    probe = PROBE.read_text(encoding="utf-8")
    assert "wp_update_post" in php
    assert "wp_remote_post" in php
    assert "/__page_cache_test/read" in probe
    for case_id in IDS:
        assert case_id in php
        assert case_id in index
