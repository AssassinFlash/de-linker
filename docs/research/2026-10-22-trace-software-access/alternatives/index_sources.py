"""Index local Apify results and omit unrelated HTML/session retrieval data.

This performs no network access. Original public responses remain in the cited
Apify datasets. Hashes describe the collected HTML before it was omitted here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "access_evidence", ROOT.parents[1] / "2026-10-22-roof-europe-precedents" / "summarize_sources.py"
)
assert spec and spec.loader
indexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexer)
indexer.ROOT = ROOT
indexer.RAW = ROOT / "raw"
indexer.LINK_TERMS = (
    "demo", "trial", "download", "free", "login", "log in", "register",
    "sign up", "guest", "anonymous", "preview", "start", "example",
    "sample", "report", "project", "pdf", "pvsol-online", "sunnydesignweb",
    "speedy-pv", "tutorial", "manual", "account", "base.k2", "youtube", "vimeo",
)


def scrub(value):
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        def unsigned(match):
            parsed = urlsplit(match.group(0))
            if re.search(r"(?:^|&)(?:signature|token)=", parsed.query):
                return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            return match.group(0)
        return re.sub(r'https://api\.apify\.com/[^\s"<>]+', unsigned, value)
    return value


def main():
    indexer.main()
    for path in (ROOT / "raw").glob("*.json"):
        value = scrub(json.loads(path.read_text()))
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    sources = json.loads((ROOT / "sources.json").read_text())
    rows = [
        "# Official source index",
        "",
        "Collected via Apify only, 2026-10-22. HTTP and text length describe collection, not browser execution. Search results are discovery records, not evidence that an app worked. Public HTML omitted after extracting links/headings and recording a SHA256; full originals remain in the indicated dataset. Signed Apify retrieval queries and response cookies are omitted. No accounts or projects were created.",
        "",
        "| Collection / item | Official source or search query | HTTP / text characters | Apify dataset |",
        "| --- | --- | --- | --- |",
    ]
    for source in sources:
        url = source.get("url")
        query = source.get("query")
        title = (query or source.get("title") or url or "Search").replace("|", "\\|")
        link = f"Search: `{title}`" if query else f"[{title}]({url})" if url else title
        rows.append(f"| `{source['collection']}` / {source['item']} | {link} | {source['http'] or 'search'} / {source['characters']} | `{source['dataset']}` |")
    rows += ["", "## Collection caveats", ""]
    for collection in json.loads((ROOT / "collection-status.json").read_text()):
        rows.append(f"- `{collection['collection']}`: run `{collection['id']}`; status `{collection['status']}`; {collection['returnedItems']} returned items.")
        for missing in collection["missingRequestedUrls"]:
            rows.append(f"  - Requested URL absent from saved dataset: {missing}. Do not count this as successfully read.")
    (ROOT / "source-index.md").write_text("\n".join(rows) + "\n")
    manifests = []
    for path in sorted((ROOT / "raw").glob("*.json")):
        manifests.append({"file": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (ROOT / "raw-sha256.json").write_text(json.dumps(manifests, indent=2) + "\n")


if __name__ == "__main__":
    main()
