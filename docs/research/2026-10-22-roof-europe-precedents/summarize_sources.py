"""Summarize saved Apify results without fetching source websites.

Keep public HTML hashes and task-relevant link/heading evidence; omit unrelated
forms from repository artifacts. Full originals remain in the cited datasets.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
LINK_TERMS = (
    "k2 base", "k2-base", "tool", "werkzeug", "roof", "sign up", "register",
    "login", "start planning", "auslegung", "battery", "load profile",
    "energy system", "peak load", "license", "licence", "licen", "cc-by", "cc by",
)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class LinkEvidence(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict] = []
        self.stack: list[tuple[str, dict]] = []
        self.current: dict | None = None
        self.heading: dict | None = None
        self.headings: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        if tag not in VOID_TAGS:
            self.stack.append((tag, attributes))
        if tag == "a":
            self.current = {
                "href": attributes.get("href"), "text": "",
                "ancestors": [t + ":" + str(a.get("class", ""))[:120] for t, a in self.stack[-6:]],
            }
        if re.fullmatch("h[1-6]", tag):
            self.heading = {"tag": tag, "text": ""}

    def handle_data(self, data: str) -> None:
        if self.current:
            self.current["text"] += data
        if self.heading:
            self.heading["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current:
            self.current["text"] = " ".join(self.current["text"].split())
            candidate = (self.current["text"] + " " + str(self.current["href"])).lower()
            if any(term in candidate for term in LINK_TERMS):
                self.links.append(self.current)
            self.current = None
        if self.heading and tag == self.heading["tag"]:
            self.heading["text"] = " ".join(self.heading["text"].split())
            self.headings.append(self.heading)
            self.heading = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break


def write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    sources = []
    collections = []
    for file in sorted(RAW.glob("*-items.json")):
        name = file.name.removesuffix("-items.json")
        metadata = json.loads((RAW / (name + "-run.json")).read_text())
        payload = json.loads((RAW / (name + "-input.json")).read_text())
        items = json.loads(file.read_text())
        source_urls = {item.get("url") for item in items}
        missing = [item["url"] for item in payload.get("startUrls", []) if item["url"] not in source_urls]
        collections.append({
            "collection": name, **metadata, "returnedItems": len(items),
            "missingRequestedUrls": missing,
        })
        extracts = []
        for index, item in enumerate(items, 1):
            content = item.get("markdown") or item.get("text") or ""
            sources.append({
                "collection": name, "item": index, "run": metadata["id"],
                "dataset": metadata["defaultDatasetId"], "url": item.get("url"),
                "query": item.get("searchQuery", {}).get("term"),
                "title": item.get("metadata", {}).get("title"),
                "http": item.get("crawl", {}).get("httpStatusCode"),
                "loadedAt": item.get("crawl", {}).get("loadedTime"),
                "characters": len(content),
            })
            html = item.get("html")
            if not html:
                continue
            parser = LinkEvidence()
            parser.feed(html)
            extracts.append({
                "url": item["url"], "crawl": item["crawl"],
                "htmlSha256": hashlib.sha256(html.encode()).hexdigest(),
                "navigationAndCtaLinks": parser.links, "headings": parser.headings,
                "note": "Public HTML parsed locally, not a rendered or logged-in test. Full original retained in the cited Apify dataset.",
            })
            item["html"] = None
            item["htmlOmittedForScope"] = True
            item.get("metadata", {}).get("headers", {}).pop("set-cookie", None)
        if extracts:
            write(RAW / (name + "-evidence.json"), extracts)
            write(file, items)
    write(ROOT / "sources.json", sources)
    write(ROOT / "collection-status.json", collections)


if __name__ == "__main__":
    main()
