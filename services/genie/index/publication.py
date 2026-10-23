"""Manifest-only inventory and conservative chunk applicability proofs.

Content-addressed PDF/parse/vector caches are reused. Publication identity is stored
separately: equal bytes do not merge Woo document permissions or product relations.
"""

from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from index.chunking import Chunk
from linker_genie.embedding import sha256_of
from linker_genie.publication import PublicationClient, Snapshot

# Model-like words are candidates, never assumed to be products. Woo resolves exact
# supplied names. Unknown code-bearing text is kept unready (publication spec).
CODE = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9./-]*\b")


def codes(text: str) -> list[str]:
    return sorted(
        {
            token
            for token in CODE.findall(text)
            if any(c.isalpha() for c in token) and any(c.isdigit() for c in token)
        }
    )


def normalized(text: str) -> str:
    return "".join(c for c in text.casefold() if c.isalnum())


def inventory(
    client: Any, out: Path, pdf_dir: Path, manifest: dict[str, Any] | None = None
) -> list[Any]:
    from index.inventory import Document, Product

    raw = manifest
    if raw is None:
        raw, _, _ = client.get("/linker/v1/publication/manifest", {})
    current = Snapshot.read(raw)
    products = [
        Product(pid, "publish", str(p.get("brand", "")), str(p.get("model", "")))
        for pid, p in current.products.items()
    ]
    by_sha: dict[str, list[dict[str, Any]]] = {}
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for document in current.documents.values():
        sha = document["blob_sha256"]
        if not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("Woo document has no verified content SHA")
        target = pdf_dir / f"{sha}.pdf"
        # Never trust a same URL or cache filename without verifying its bytes.
        if not target.is_file() or sha256_of(target) != sha:
            with tempfile.NamedTemporaryFile(
                dir=pdf_dir, suffix=".part", delete=False
            ) as handle:
                part = Path(handle.name)
                try:
                    request = urllib.request.Request(
                        document["url"],
                        headers={
                            "User-Agent": "linker-genie-index",
                            "Cache-Control": "no-cache",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=300) as response:
                        for block in iter(lambda: response.read(1 << 20), b""):
                            handle.write(block)
                    handle.flush()
                    if sha256_of(part) != sha:
                        raise ValueError(
                            "downloaded document no longer matches Woo content revision"
                        )
                    part.replace(target)
                finally:
                    part.unlink(missing_ok=True)
        by_sha.setdefault(sha, []).append(document)
    documents = []
    for sha, relations in sorted(by_sha.items()):
        pids = sorted(
            {
                pid
                for d in relations
                for pid in d["product_ids"]
                if pid in current.products
            }
        )
        if not pids:
            continue
        documents.append(
            Document(
                sha256=sha,
                bytes=(pdf_dir / f"{sha}.pdf").stat().st_size,
                urls=sorted(
                    {
                        url
                        for d in relations
                        for url in [d["url"], *d.get("aliases", [])]
                    }
                ),
                media_ids=[],
                title_en=str(relations[0]["title"]),
                title_de="",
                brands=sorted(
                    {str(current.products[pid].get("brand", "")) for pid in pids}
                ),
                models=sorted(
                    {str(current.products[pid].get("model", "")) for pid in pids}
                ),
                product_ids=pids,
                doc_type=str(relations[0]["type"]),
                lang=str(relations[0]["lang"]),
                linked=True,
            )
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source": client.base,
                "publication_manifest": raw,
                "products": [asdict(p) for p in products],
                "documents": [asdict(d) for d in documents],
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return documents


def applicability(
    chunks: list[Chunk], manifest: dict[str, Any], authority: PublicationClient
) -> dict[str, list[int]]:
    """Prove explicit model scope; generic/mixed/unknown passages stay unready.

    Headers are deliberately excluded: the chunker prepends all document models,
    which is metadata about the file and cannot prove this passage applies to A.
    A foreign model in the same table blocks the whole table, preserving its meaning.
    """
    source = Snapshot.read(manifest)
    models = {
        pid: str(product.get("model", "")) for pid, product in source.products.items()
    }
    associated: dict[str, set[int]] = {}
    for document in source.documents.values():
        associated.setdefault(document["blob_sha256"], set()).update(
            document["product_ids"]
        )
    statuses = authority.identify(
        [code for chunk in chunks for code in codes(chunk.text + " " + chunk.section)]
    )
    result: dict[str, list[int]] = {}
    for chunk in chunks:
        passage = chunk.section + " " + chunk.text
        written = normalized(passage)
        matched = {
            pid
            for pid, model in models.items()
            if model and normalized(model) in written
        }
        known_codes = {
            code.casefold() for pid in matched for code in codes(models[pid])
        }
        unknown = [
            code
            for code in codes(passage)
            if code.casefold() not in known_codes
            and statuses.get(code.casefold()) != "published"
        ]
        # All contained model facts must be current AND supported by this document.
        if (
            matched
            and matched.issubset(associated.get(chunk.doc_sha256, set()))
            and not unknown
        ):
            result[chunk.id] = sorted(matched)
    return result
