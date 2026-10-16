#!/usr/bin/env python3
"""Rehearses 12-site-chrome.py's verify against a simulated post-apply state.

Applies every step to the live dump in memory (content, titles, statuses,
the SEO pairs, the German source metas, the media alts), then runs the real
do_verify() over that state with a WP double. "verify: OK" here means an
apply on the live site leaves nothing for verify to refuse (the live site
itself would fail today — it has not been applied).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rehearse  # noqa: E402  (its loader, dump, ids and seo double)

chrome = rehearse.chrome
dump = rehearse.dump
IDS = rehearse.IDS

SLUGS = {
    3302: "solution-configurator",
    6693: "loesungskonfigurator",
    4083: "genie",
    6633: "genie",
}


def simulate() -> dict[str, object]:
    posts = json.loads(json.dumps(dump["posts"]))
    seo = json.loads(json.dumps(dump["seo"]))
    legacy = json.loads(json.dumps(dump["legacy"]))
    alts = dict(rehearse.alts)
    plan = chrome.steps(IDS)
    for step in plan:
        key = str(step.post_id)
        row = posts[key]
        row["post_content"] = step.planned(row["post_content"])
        if step.title and row["post_title"] == step.title[0]:
            row["post_title"] = step.title[1]
        if step.status:
            row["post_status"] = step.status
        current = seo.get(key, {})
        for field, pair in (("title", step.seo), ("desc", step.seo_desc)):
            if pair and current.get(field) == pair[0]:
                current[field] = pair[1]
        if current:
            seo[key] = current
        if step.lang == "de":
            source = str(step.english_id)
            twin_content = row["post_content"]
            if source in legacy:
                legacy[source]["content"] = twin_content
                if step.title and legacy[source].get("title") == step.title[0]:
                    legacy[source]["title"] = step.title[1]
    for alt_id, alt in alts.items():
        alts[alt_id] = chrome.renamed_alt(alt)
    return {
        "posts": posts,
        "seo": seo,
        "legacy": legacy,
        "alts": alts,
        "slugs": SLUGS,
    }


STATE = simulate()


class FakeWP:
    def run(self, *args: str, **kwargs: object) -> str:
        if args[:2] == ("post", "get") and "--field=post_name" in args:
            return STATE["slugs"][int(args[2])]  # type: ignore[index]
        if args[:2] == ("post", "get") and "--field=post_content" in args:
            row = STATE["posts"][args[2]]  # type: ignore[index]
            return row["post_content"]
        raise AssertionError(f"unexpected wp call: {args!r}")

    def json(self, *args: str, **kwargs: object) -> object:
        if args[:2] == ("post", "list"):
            return [
                {"ID": int(post_id), "post_title": row["post_title"]}
                for post_id, row in STATE["posts"].items()  # type: ignore[union-attr]
                if row["post_status"] == "publish"
            ]
        if args[:2] == ("post", "get"):
            row = STATE["posts"][args[2]]  # type: ignore[index]
            return dict(row)
        raise AssertionError(f"unexpected wp json: {args!r}")

    def eval_php(self, code: str, payload: object) -> object:
        if code is chrome.LEGACY_META_PHP:
            wanted = {str(i) for i in payload}  # type: ignore[union-attr]
            return {
                k: v
                for k, v in STATE["legacy"].items()  # type: ignore[union-attr]
                if k in wanted
            }
        if code is chrome.ALT_READ_PHP:
            return STATE["alts"]
        raise AssertionError("unexpected eval_php in the verify rehearsal")


def fake_seo_meta(wp: object, post_id: int | None = None) -> object:
    if post_id:
        return STATE["seo"].get(str(post_id), {})  # type: ignore[union-attr]
    return STATE["seo"]


def main() -> int:
    chrome.resolve = lambda wp: IDS  # type: ignore[assignment]
    chrome.seo_meta = fake_seo_meta  # type: ignore[assignment]
    return chrome.do_verify(FakeWP())  # type: ignore[arg-type]


if __name__ == "__main__":
    sys.exit(main())
