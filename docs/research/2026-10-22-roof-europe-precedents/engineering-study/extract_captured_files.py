"""Read official documents already captured by Apify, never their source host.

Signed retrieval URLs are removed from saved datasets; API credentials stay in
memory and headers. PDFs are retained as read-only evidence and text-extracted
with installed Poppler. This does not create or alter document content.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("roof_apify_collector", ROOT.parent / "collect_sources.py")
assert spec and spec.loader
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
FILES = ROOT / "captured-files"
FILES.mkdir(exist_ok=True)


def omit_retrieval_signatures(value):
    if isinstance(value, dict):
        return {key: omit_retrieval_signatures(item) for key, item in value.items()}
    if isinstance(value, list):
        return [omit_retrieval_signatures(item) for item in value]
    if isinstance(value, str):
        def unsigned(match):
            parsed = urlsplit(match.group(0))
            if re.search(r"(?:^|&)(?:signature|token)=", parsed.query):
                return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            return match.group(0)
        return re.sub(r'https://api\.apify\.com/[^\s"<>]+', unsigned, value)
    return value


def main() -> None:
    documents = []
    for dataset in sorted((ROOT / "raw").glob("*-items.json")):
        items = omit_retrieval_signatures(json.loads(dataset.read_text()))
        for item in items:
            if item.get("fileUrl"):
                parsed = urlsplit(item["fileUrl"])
                item["fileUrl"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
                item["signedRetrievalQueryOmitted"] = True
        dataset.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
        for item in items:
            captured = item.get("fileUrl")
            if not captured:
                continue
            parsed = urlsplit(captured)
            if parsed.hostname != "api.apify.com":
                raise RuntimeError("Captured file is not on the Apify API")
            unsigned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            name = re.sub(r"[^a-zA-Z0-9_-]", "-", parsed.path.rsplit("/", 1)[-1])
            target = FILES / (name.removesuffix("-pdf") + ".pdf")
            text_target = FILES / (name + ".txt")
            if not target.exists() and text_target.exists():
                target = text_target
            if not target.exists():
                request = Request(unsigned, headers={"Authorization": "Bearer " + collector.token()})
                for attempt in range(3):
                    try:
                        with urlopen(request, timeout=50) as response:
                            content = response.read()
                        break
                    except (URLError, TimeoutError):
                        if attempt == 2:
                            raise
                        time.sleep(attempt + 1)
                if not content.startswith(b"%PDF"):
                    # text/plain licenses use this actor output path as well.
                    target = text_target
                target.write_bytes(content)
            content = target.read_bytes()
            info = ""
            if target.suffix == ".pdf":
                text_path = target.with_suffix(".txt")
                extraction = subprocess.run(
                    ["pdftotext", "-layout", str(target), str(text_path)],
                    check=True, capture_output=True, text=True,
                )
                if extraction.stderr:
                    target.with_suffix(".extraction-warnings.txt").write_text(extraction.stderr)
                info = subprocess.run(["pdfinfo", str(target)], check=True, capture_output=True, text=True).stdout
            documents.append({
                "sourceUrl": item["url"], "datasetFile": dataset.name,
                "apifyRecordUrl": unsigned, "localFile": str(target.relative_to(ROOT)),
                "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                "pdfInfo": info,
            })
            item["fileUrl"] = unsigned
            item["signedRetrievalQueryOmitted"] = True
        for item in items:
            item.get("metadata", {}).get("headers", {}).pop("set-cookie", None)
        dataset.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "captured-files.json").write_text(json.dumps(documents, ensure_ascii=False, indent=2) + "\n")
    for document in documents:
        print(document["sourceUrl"], document["localFile"], document["bytes"])


if __name__ == "__main__":
    main()
