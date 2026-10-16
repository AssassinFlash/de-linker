#!/usr/bin/env python3
"""Offline rehearsal of 12-site-chrome.py's plan and dry apply on a live dump.

Runs the real do_plan()/do_apply(write=False) against the fetched live
content (`live-dump.json`, `live-alts.json`) with a WP double, so pair
mismatches surface here in seconds instead of after a five-minute live plan
run. Read-only by construction: the double serves reads and refuses writes.

The `--check` mode applies every step's pairs and rules to the live content
and reports any stale token (name or address) left in the result, which is
what do_verify refuses after an apply.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The migration script of the checked-out branch by default; M2_SCRIPT points
# at the fix/m2-chrome-pairs worktree's copy when this runs from another
# branch's checkout.
SCRIPT = Path(
    os.environ.get("M2_SCRIPT", HERE.parent.parent / "tools/migrate/12-site-chrome.py")
)

spec = importlib.util.spec_from_file_location("twelve_site_chrome", SCRIPT)
assert spec is not None and spec.loader is not None
chrome = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chrome)

# The fetched live dump sits in .scratch/ (not committed: it is site content,
# 3.2 MB, regenerated read-only with fetch-live-dump.php).
dump = json.loads((HERE.parent / "live-dump.json").read_text())
alts = json.loads((HERE / "live-alts.json").read_text())

IDS: dict[str, dict[str, int]] = {
    "header": {"en": 17, "de": 6909},
    "footer": {"en": 18, "de": 6911},
    "linker-advisor": {"en": 4083, "de": 6633},
    "linker-planner": {"en": 3302, "de": 6693},
    "design-canvas": {"en": 3198, "de": 6696},
    "quote-configurator": {"en": 3998, "de": 6637},
    "quote-configurator-2": {"en": 3999, "de": 6635},
    "request-a-project": {"en": 2747, "de": 6702},
    "home": {"en": 13, "de": 6913},
    "solution": {"en": 746, "de": 6871},
    "residential-storage": {"en": 749, "de": 6923},
    "commercial-storage": {"en": 792, "de": 6921},
    "for-installer": {"en": 826, "de": 6869},
    "about": {"en": 862, "de": 6865},
    "capability": {"en": 874, "de": 6919},
    "faq-download": {"en": 932, "de": 6863},
    "privacy-policy": {"en": 1673, "de": 6827},
    "services-support": {"en": 2748, "de": 6700},
    "gateway-post": {"en": 558, "de": 6897},
    "blog-index-template": {"en": 574, "de": 6881},
    "thank-you": {"en": 623, "de": 6873},
    "utility-storage": {"en": 1755, "de": 6917},
    "terms-of-sale": {"en": 1674, "de": 6825},
}

SLUGS = {3302: "solution-configurator", 6693: "loesungskonfigurator", 4083: "genie",
         6633: "genie"}


class FakeWP:
    def run(self, *args: str, **kwargs: object) -> str:
        if args[:2] == ("post", "get") and "--field=post_name" in args:
            return SLUGS[int(args[2])]
        raise AssertionError(f"unexpected wp call: {args!r}")

    def json(self, *args: str, **kwargs: object) -> object:
        if args[:2] == ("post", "get"):
            row = dump["posts"][args[2]]
            return {
                "post_title": row["post_title"],
                "post_content": row["post_content"],
                "post_status": row["post_status"],
            }
        raise AssertionError(f"unexpected wp json: {args!r}")

    def eval_php(self, code: str, payload: object) -> object:
        if code is chrome.LEGACY_META_PHP:
            wanted = {str(i) for i in payload}  # type: ignore[union-attr]
            return {k: v for k, v in dump["legacy"].items() if k in wanted}
        if code is chrome.ALT_READ_PHP:
            return alts
        raise AssertionError("unexpected eval_php in the read-only rehearsal")


def fake_seo_meta(wp: object, post_id: int | None = None) -> object:
    if post_id:
        return dump["seo"].get(str(post_id), {})
    return dump["seo"]


def patch() -> None:
    chrome.resolve = lambda wp: IDS  # type: ignore[assignment]
    chrome.seo_meta = fake_seo_meta  # type: ignore[assignment]


def rehearsal_check() -> int:
    """Post-apply stale-token check over every step of the real plan."""
    plan = chrome.steps(IDS)
    bad = 0
    for step in plan:
        content = dump["posts"][str(step.post_id)]["post_content"]
        new = step.planned(content)
        left = chrome.stale_tokens(new)
        if left:
            bad += 1
            print(f"LEFT {step.key} #{step.post_id}: {', '.join(left)}")
    print(f"stale left behind: {bad} step(s) (excluded sentence-level items "
          "do not match the tokens)")
    return 1 if bad else 0


def main() -> int:
    patch()
    if "--check" in sys.argv:
        return rehearsal_check()
    if "--apply" in sys.argv:
        return chrome.do_apply(FakeWP(), write=False)  # type: ignore[arg-type]
    return chrome.do_plan(FakeWP())  # type: ignore[arg-type]


if __name__ == "__main__":
    sys.exit(main())
