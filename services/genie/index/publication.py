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
from typing import Any, TypedDict

from index.chunking import Chunk
from linker_genie.embedding import sha256_of
from linker_genie.publication import PublicationClient, Snapshot

# Tokens are supplied to Woo for recognition; having letters and digits does not
# by itself make a frequency, ingress rating, standard or report number a model.
CODE = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9./-]*\b")
MODEL_FIELD = re.compile(
    r"\b(?:models?|product\s+model|model/type|type\s+designation|modell(?:e)?|typ)\b"
    r"|型号(?:规格)?",
    re.IGNORECASE,
)
ENGINEERING = re.compile(
    r"(?:IP\d{2}[A-Z]?|(?:IEC|ISO|IEEE|VDE|EN|DIN|UN|UL)\d[\dA-Z./-]*"
    r"|(?:RS|MPPT|PV|COM|DI|DO|AI|AO)\d+"
    r"|[\d./-]+(?:[kmunMGT]?(?:Hz|Wh|W|VA|V|Ah|A|Ohm)|Vac|Vdc|Vd\.c|Ad\.c))",
    re.IGNORECASE,
)
COMMON_SCOPE = re.compile(
    r"(?:covered\s+by|subject\s+to).{0,80}(?:these|this)\s+warranty"
    r"|warranty\s+terms\s+and\s+conditions.{0,80}(?:apply|cover)"
    r"|(?:certificate|declaration).{0,100}(?:refers\s+to|above.mentioned|listed\s+(?:models|products))"
    r"|Garantiebedingungen.{0,80}(?:gelten|umfassen)"
    r"|(?:Zertifikat|Erklärung).{0,100}(?:oben|genannt|aufgeführten)",
    re.IGNORECASE | re.DOTALL,
)
PARAMETER_PROSE = re.compile(
    r"\b(?:nominal|rated|capacity|voltage|frequency|efficiency|dimensions|weight|MPPT)\b"
    r"|\b(?:technical\s+(?:data|parameters)|Nennleistung|Kapazität|Spannung|Frequenz)\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:[kmunMGT]?(?:Hz|Wh|W|VA|V|Ah|A)|kg|mm|cm)\b"
    r"|\d\s*[°℃]",
    re.IGNORECASE,
)


class ScopeProof(TypedDict):
    """The authored or explicit Woo document scope behind an allowed passage."""

    product_ids: list[int]
    basis: str
    source_chunk_ids: list[str]
    document_ids: list[str]


def codes(text: str) -> list[str]:
    return sorted(
        {
            token
            for token in CODE.findall(text)
            if any(c.isalpha() for c in token) and any(c.isdigit() for c in token)
        }
    )


def _model_pattern(label: str) -> re.Pattern[str]:
    # A shorter published model must not authorize the ratings of a suffix variant.
    written = r"\s+".join(re.escape(part) for part in label.split())
    pattern = r"(?<![\w./-])" + written + r"(?![\w/-]|\.(?=\w))"
    return re.compile(pattern, re.IGNORECASE)


def _mentions(text: str, label: str) -> bool:
    return _model_pattern(label).search(text) is not None


def _recognized(chunks: list[Chunk], authority: PublicationClient) -> dict[str, str]:
    """Woo recognizes original bounded text, including multi-word draft labels.

    A build must not infer an unknown code's permission from an old index. The
    16,000-byte limit is the existing Woo exact-text endpoint's request contract.
    Chunk text is bounded by the chunker's 512-token contract; headers are excluded.
    """
    result: dict[str, str] = {}
    batch = ""
    seen = set()
    for chunk in chunks:
        text = chunk.section + "\n" + chunk.text
        if text in seen:
            continue
        seen.add(text)
        if len(text.encode()) > 16000:
            raise ValueError("authored chunk exceeds Woo identification text limit")
        if len((batch + "\n" + text).encode()) > 16000:
            result.update(authority.identify_text(batch))
            batch = ""
        batch += "\n" + text
    if batch:
        result.update(authority.identify_text(batch))
    return result


def _unknown_models(
    text: str, labels: set[str], shapes: set[str], *, section: bool = False
) -> bool:
    """Reject unresolved model references, not ordinary engineering tokens.

    Model families come from Woo's supplied-label recognition and current models.
    Author-written Model/Type axes and conjunctions beside a model also provide
    model context; this keeps a foreign Z999 column out of a shared ratings table.
    """
    known_tokens = {token.casefold() for label in labels for token in codes(label)}
    declared = {
        token.casefold()
        for line in text.splitlines()
        if MODEL_FIELD.search(line)
        for token in codes(line)
    }
    residual = text
    for label in sorted(labels, key=len, reverse=True):
        residual = re.sub(re.escape(label), " @MODEL@ ", residual, flags=re.IGNORECASE)
    coupled = {
        token.casefold()
        for token in re.findall(
            r"@MODEL@\s*(?:[,/&|]|and\b|or\b|und\b|oder\b)\s*([A-Za-z0-9][A-Za-z0-9./-]*)",
            residual,
            re.IGNORECASE,
        )
    }
    for line in text.splitlines():
        amendments = {s.casefold() for s in re.findall(r"\+\s*([A-Z]\d+)\b", line)}
        for token in codes(line):
            if (
                token.casefold() in known_tokens
                or token.casefold() in amendments
                or ENGINEERING.fullmatch(token)
            ):
                continue
            prefix = re.match(r"[A-Za-z]+", token)
            if (
                (prefix is not None and prefix[0].casefold() in shapes)
                or any(
                    token.casefold() == shape
                    or token.casefold().startswith(shape + "-")
                    for shape in shapes
                    if any(c.isdigit() for c in shape)
                )
                or token.casefold() in declared
                or token.casefold() in coupled
                or section
            ):
                return True
    return False


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
    """Compatibility view of the complete scope proof written by a new build."""
    return {
        cid: proof["product_ids"]
        for cid, proof in scope_proofs(chunks, manifest, authority).items()
    }


def scope_proofs(
    chunks: list[Chunk], manifest: dict[str, Any], authority: PublicationClient
) -> dict[str, ScopeProof]:
    """Prove authored model scope or a truly model-free Woo document purpose.

    Headers are deliberately excluded: the chunker prepends all document models,
    which is metadata about the file and cannot prove this passage applies to A.
    Mixed documents cannot assign an unnamed B table to remaining published A.
    """
    source = Snapshot.read(manifest)
    models = {
        pid: str(product.get("model", "")) for pid, product in source.products.items()
    }
    current_labels = {model.casefold() for model in models.values() if model}
    documents: dict[str, list[dict[str, Any]]] = {}
    for document in source.documents.values():
        documents.setdefault(document["blob_sha256"], []).append(document)
    relevant = [chunk for chunk in chunks if chunk.doc_sha256 in documents]
    statuses = _recognized(relevant, authority)
    labels = set(statuses).union(current_labels)
    patterns = {label: _model_pattern(label) for label in labels}
    shapes = set()
    for label in labels:
        leading = re.match(r"[A-Za-z]+", label)
        if leading is not None and len(leading[0]) >= 2:
            shapes.add(leading[0].casefold())
        else:
            first = re.split(r"[\s./-]", label)[0]
            if len(first) >= 2:
                shapes.add(first.casefold())
    observed: dict[str, tuple[set[int], bool]] = {}
    doc_models: dict[str, set[int]] = {}
    ambiguous: set[str] = set()
    origins: dict[str, list[str]] = {}
    common: dict[str, list[str]] = {}
    sections: dict[tuple[str, str], set[int]] = {}
    section_origins: dict[tuple[str, str], list[str]] = {}
    ambiguous_sections: set[tuple[str, str]] = set()
    for chunk in relevant:
        passage = chunk.section + "\n" + chunk.text
        matched = {
            pid
            for pid, model in models.items()
            if model and patterns[model.casefold()].search(passage)
        }
        contained = {
            label for label, pattern in patterns.items() if pattern.search(passage)
        }
        associated = {
            pid for doc in documents[chunk.doc_sha256] for pid in doc["product_ids"]
        }
        blocked = (
            any(
                statuses.get(label) != "published"
                for label in contained
                if label in statuses
            )
            or any(label not in current_labels for label in contained)
            or not matched.issubset(associated)
            or _unknown_models(passage, contained, shapes)
            or _unknown_models(chunk.section, contained, shapes, section=True)
        )
        observed[chunk.id] = matched, blocked
        positive = matched.intersection(associated)
        doc_models.setdefault(chunk.doc_sha256, set()).update(positive)
        section_key = chunk.doc_sha256, chunk.section
        sections.setdefault(section_key, set()).update(positive)
        if positive:
            origins.setdefault(chunk.doc_sha256, []).append(chunk.id)
            section_origins.setdefault(section_key, []).append(chunk.id)
        if COMMON_SCOPE.search(chunk.text):
            common.setdefault(chunk.doc_sha256, []).append(chunk.id)
        if blocked:
            ambiguous.add(chunk.doc_sha256)
            ambiguous_sections.add(section_key)
    result: dict[str, ScopeProof] = {}
    for chunk in relevant:
        matched, blocked = observed[chunk.id]
        relations = documents[chunk.doc_sha256]
        general = [
            doc for doc in relations if doc["type"] in {"warranty", "certificate"}
        ]
        basis, origin = "passage", [chunk.id]
        if blocked:
            continue
        if matched:
            if not any(
                patterns[models[pid].casefold()].search(chunk.text) for pid in matched
            ):
                basis = "section"
        elif (
            chunk.section
            and (chunk.doc_sha256, chunk.section) not in ambiguous_sections
            and len(sections[(chunk.doc_sha256, chunk.section)]) == 1
        ):
            matched = sections[(chunk.doc_sha256, chunk.section)]
            basis = "section_model"
            origin = section_origins[(chunk.doc_sha256, chunk.section)]
        elif (
            chunk.kind == "text"
            and not PARAMETER_PROSE.search(chunk.text)
            and common.get(chunk.doc_sha256)
            and doc_models.get(chunk.doc_sha256)
            and general
        ):
            # The manufacturer explicitly declares shared terms for the named
            # products. Only model-free non-parameter prose inherits that scope;
            # an unnamed B table/technical value cannot borrow current A's name.
            relations = general
            matched = doc_models[chunk.doc_sha256].intersection(
                pid for doc in general for pid in doc["product_ids"]
            )
            basis = "common_terms"
            origin = sorted(set(common[chunk.doc_sha256] + origins[chunk.doc_sha256]))
        elif chunk.doc_sha256 not in ambiguous:
            explicit = doc_models.get(chunk.doc_sha256, set())
            if len(explicit) == 1:
                matched = explicit
                basis, origin = "document_model", origins[chunk.doc_sha256]
            elif not explicit:
                # Only explicit general document purposes can authorize model-free
                # terms. A nameless technical datasheet/table is not inferred.
                if general:
                    relations = general
                    matched = {
                        pid
                        for doc in general
                        for pid in doc["product_ids"]
                        if pid in models
                    }
                    basis, origin = "woo_document", []
        if matched:
            result[chunk.id] = {
                "product_ids": sorted(matched),
                "basis": basis,
                "source_chunk_ids": origin,
                "document_ids": sorted(doc["document_id"] for doc in relations),
            }
    return result
