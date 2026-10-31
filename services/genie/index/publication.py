"""Manifest-only inventory and conservative chunk applicability proofs.

Content-addressed PDF/parse/vector caches are reused. Publication identity is stored
separately: equal bytes do not merge Woo document permissions or product relations.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.request
from collections.abc import Iterator
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from index.chunking import MAX_TOKENS, Chunk, Tokenizer
from index.inventory import doc_type_of, document_kind_of, lang_of
from linker_genie.certificate_scope import (
    certificate_boundaries_allow,
    certificate_document,
    certificate_fragment_id,
    certificate_fragment_text,
    certificate_id,
    certificate_registration,
    certificate_text,
    lcie_declaration,
    lcie_limitation,
    split_declaration,
    valid_certificate_scope,
)
from linker_genie.embedding import sha256_of
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.source_models import (
    family_labels as _family_labels,
)
from linker_genie.source_models import (
    model_pattern as _model_pattern,
)
from linker_genie.source_models import (
    model_shapes,
)
from linker_genie.source_models import (
    unknown_models as _unknown_models,
)
from linker_genie.source_roles import (
    manual_scope_models,
    meter_references,
    pack_model_row,
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
TECHNICAL_DATA = re.compile(
    r"\b(?:Technical\s+Data|Technische\s+Daten)\b", re.IGNORECASE
)


class TableColumns(TypedDict):
    """Original ordered column labels for one native parsed TableItem."""

    source_table: str
    header_chunk_ids: list[str]
    product_ids: list[int]
    labels: list[str]
    heading: str
    source_rows: NotRequired[list[int]]
    source_chunk_id: NotRequired[str]
    text_sha256: NotRequired[str]
    excluded_role_rows: NotRequired[list[dict[str, Any]]]


class NativeTable(TypedDict):
    """All original fragments of one native table, in source order."""

    source_table: str
    source_chunk_ids: list[str]


class ScopeProof(TypedDict):
    """The authored or explicit Woo document scope behind an allowed passage."""

    product_ids: list[int]
    basis: str
    source_chunk_ids: list[str]
    document_ids: list[str]
    associations: list[dict[str, Any]]
    table_columns: NotRequired[TableColumns]
    native_table: NotRequired[NativeTable]
    referenced_products: NotRequired[list[dict[str, Any]]]
    manual_scope: NotRequired[dict[str, Any]]
    table_projection: NotRequired[dict[str, Any]]
    family_scope: NotRequired[dict[str, Any]]
    author_restrictions: NotRequired[list[dict[str, Any]]]
    warranty_scope: NotRequired[dict[str, Any]]
    certificate_scope: NotRequired[dict[str, Any]]
    certificate_fragment: NotRequired[dict[str, Any]]
    model_identity_revision: NotRequired[str]


def _table_columns(
    chunks: list[Chunk],
    models: dict[int, str],
    patterns: dict[str, re.Pattern[str]],
    statuses: dict[str, str],
    shapes: set[str],
    observed: dict[str, tuple[set[int], bool]],
    families: set[str],
) -> tuple[dict[str, TableColumns], set[str]]:
    """A source column heading authorizes only the immediately following TableItem.

    The chunker records native reading-order provenance. No page radius, generated
    header or repeated generic section name can join independent tables together.
    All fragments of this table retain all columns in their original order.
    """
    by_id = {chunk.id: chunk for chunk in chunks}
    positions = {chunk.id: i for i, chunk in enumerate(chunks)}
    groups: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in chunks:
        if chunk.kind == "table" and chunk.source_table:
            groups.setdefault((chunk.doc_sha256, chunk.source_table), []).append(chunk)
    labels_to_ids = {model.casefold(): pid for pid, model in models.items() if model}
    output: dict[str, TableColumns] = {}
    conflicts: set[str] = set()
    for (_, table_id), parts in groups.items():
        first = parts[0]
        preceding = [by_id[cid] for cid in first.preceding_text if cid in by_id]
        if (
            len(preceding) != len(first.preceding_text)
            or any(
                part.preceding_text != first.preceding_text
                or part.section != first.section
                for part in parts
            )
            or any(
                chunk.kind != "text"
                or chunk.doc_sha256 != first.doc_sha256
                or chunk.section != first.section
                or positions[chunk.id] >= positions[first.id]
                for chunk in preceding
            )
        ):
            conflicts.update(part.id for part in parts)
            continue
        excluded = [part for part in parts if observed[part.id][1]]
        # An explicit component property is not a replacement model-column
        # axis. It remains denied. Only independent native rows with traceable
        # indices can use the already-proven, complete current system columns.
        if excluded and (
            any(not pack_model_row(part.text) for part in excluded)
            or any(
                not part.source_rows
                or len(part.source_rows) != len(part.text.splitlines())
                or part.source_rows != tuple(sorted(set(part.source_rows)))
                or any(row < 0 for row in part.source_rows)
                for part in parts
            )
        ):
            # This is a rejected TableItem, not merely absent column inheritance.
            # Explicit current models in its first fragment must not bypass the
            # group's failure through scope_proofs' direct passage branch.
            conflicts.update(part.id for part in parts)
            continue
        text = "\n".join(chunk.text for chunk in preceding)
        headings = list(TECHNICAL_DATA.finditer(text))
        if not headings:
            continue
        heading = headings[-1]
        tail = text[heading.end() :]
        written = sorted(
            (match.start(), label, match.group())
            for label, pattern in patterns.items()
            for match in pattern.finditer(tail)
        )
        labels = {label for _, label, _ in written}
        if (
            any(statuses.get(label) != "published" for label in labels)
            or not labels.issubset(labels_to_ids)
            # This is an explicit model-column axis; unresolved codes here are
            # model candidates even when their family is absent from Woo.
            or _unknown_models(tail, labels, shapes, section=True, families=families)
        ):
            conflicts.update(part.id for part in parts)
            continue
        if len(labels) < 2:
            continue
        ordered = list(dict.fromkeys(label for _, label, _ in written))
        ids = [labels_to_ids[label] for label in ordered]
        if any(
            not observed[part.id][0].issubset(ids)
            for part in parts
            if part not in excluded
        ):
            conflicts.update(part.id for part in parts)
            continue
        rows = [line for part in parts for line in part.text.splitlines()]
        if not rows or any(
            not line.startswith("|")
            or not line.endswith("|")
            or len(line.split("|")) - 2 != len(ids) + 1
            for line in rows
        ):
            conflicts.update(part.id for part in parts)
            continue
        # A native table's own model axis cannot be overwritten by the preceding
        # text. Equal sets do not prove equal column order. Refuse the complete
        # TableItem when a local axis is partial, different or reversed.
        local_conflict = False
        for line in rows:
            if excluded and pack_model_row(line):
                continue
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            local = [
                [label for label, pattern in patterns.items() if pattern.search(cell)]
                for cell in cells[1:]
            ]
            if any(local) and (
                any(len(labels) != 1 for labels in local)
                or [labels_to_ids.get(labels[0]) for labels in local if labels] != ids
            ):
                local_conflict = True
                break
        if local_conflict:
            conflicts.update(part.id for part in parts)
            continue
        offset = 0
        sources = []
        for chunk in preceding:
            if offset + len(chunk.text) > heading.start():
                sources.append(chunk.id)
            offset += len(chunk.text) + 1
        columns: TableColumns = {
            "source_table": table_id,
            "header_chunk_ids": sources,
            "product_ids": ids,
            "labels": [
                next(value for _, key, value in written if key == label)
                for label in ordered
            ],
            "heading": " ".join(heading.group().split()),
        }
        for part in parts:
            if part in excluded:
                continue
            own_columns: TableColumns = {**columns}
            if excluded:
                own_columns["source_rows"] = list(part.source_rows)
                own_columns["source_chunk_id"] = part.id
                own_columns["text_sha256"] = hashlib.sha256(
                    part.text.encode()
                ).hexdigest()
                own_columns["excluded_role_rows"] = [
                    {
                        "role": "pack_model",
                        "source_chunk_id": p.id,
                        "source_rows": list(p.source_rows),
                        "quote": p.text,
                    }
                    for p in excluded
                ]
            output[part.id] = own_columns
    return output, conflicts


def _manual_scopes(
    chunks: list[Chunk],
    documents: dict[str, list[dict[str, Any]]],
    models: dict[int, str],
) -> dict[str, dict[str, Any]]:
    """The manufacturer's literal declaration, not a generated file header.

    A declaration may also list unavailable models. Its positive, exact current
    subjects retain only their own Woo manual associations; those other models
    acquire no facts or permission (609, shared original A/B).
    """
    output: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        listed = (
            manual_scope_models(chunk.text)
            if chunk.kind == "text" and not chunk.source_picture
            else set()
        )
        if not listed:
            continue
        associated = {
            pid
            for doc in documents[chunk.doc_sha256]
            if document_kind_of(str(doc["type"]), str(doc.get("role", ""))) == "manual"
            for pid in doc["product_ids"]
        }
        subjects = sorted(pid for pid in associated if models[pid].casefold() in listed)
        if not subjects:
            continue
        # Competing declarations require a more specific source structure.
        if chunk.doc_sha256 in output:
            output[chunk.doc_sha256]["conflict"] = True
        else:
            output[chunk.doc_sha256] = {
                "product_ids": subjects,
                "source_chunk_ids": [chunk.id],
                "quote": chunk.text,
            }
    return {sha: scope for sha, scope in output.items() if not scope.get("conflict")}


def _manual_peripheral(
    chunk: Chunk,
    previous: list[Chunk],
    declaration: dict[str, Any] | None,
    source: Snapshot,
    patterns: dict[str, re.Pattern[str]],
    shapes: set[str],
    families: set[str],
) -> list[dict[str, Any]]:
    """A literal meter role can support host compatibility, never meter facts."""
    if (
        declaration is None
        or chunk.kind != "text"
        or PARAMETER_PROSE.search(chunk.text)
    ):
        return []
    written = meter_references(chunk.text)
    if not written:
        return []
    by_model = {
        str(p.get("model", "")).casefold(): pid for pid, p in source.products.items()
    }
    references = []
    for label, quote in written:
        pid = by_model.get(label.casefold())
        if pid is None or pid in declaration["product_ids"]:
            return []
        references.append(
            {
                "product_id": pid,
                "product_revision": source.products[pid]["product_revision"],
                "model": str(source.products[pid]["model"]),
                "role": "meter",
                "source_chunk_id": chunk.id,
                "quote": quote,
            }
        )
    reference_labels = {ref["model"].casefold() for ref in references}
    # The same sentence explicitly labels METER.485 as a port, rather than a
    # product. Preserve its literal text; this role only classifies that token.
    port_labels = {
        match.casefold()
        for match in re.findall(
            r"\b([A-Za-z][A-Za-z0-9.]*\d[A-Za-z0-9.]*)\s+port\b",
            chunk.text,
            re.IGNORECASE,
        )
    }
    # No local product/model override, other model reference or unknown external
    # device may inherit this compatibility statement's document-wide scope.
    if any(
        pattern.search(chunk.section + "\n" + chunk.text)
        for label, pattern in patterns.items()
        if label not in reference_labels
    ) or _unknown_models(
        chunk.section + "\n" + chunk.text,
        reference_labels.union(port_labels),
        shapes,
        section=True,
        families=families,
    ):
        return []
    for prior in previous:
        if prior.id == chunk.id:
            break
        if prior.doc_sha256 != chunk.doc_sha256 or prior.section != chunk.section:
            continue
        if any(
            pattern.search(prior.text) for pattern in patterns.values()
        ) or _unknown_models(
            prior.text, set(), shapes, section=True, families=families
        ):
            return []
    return references


def _mentions(text: str, label: str) -> bool:
    return _model_pattern(label).search(text) is not None


def _authored_text_parts(chunk: Chunk) -> Iterator[str]:
    """Bound original heading events and passage text for Woo identification."""
    # Woo's exact-text endpoint allows 16,000 UTF-8 bytes. Its exact model-label
    # contract allows 200 bytes; overlap preserves a label crossing a text window.
    limit, overlap = 16000, 200
    for text in (*chunk.source_headings, chunk.section + "\n" + chunk.text):
        if not text.strip():
            continue
        data = text.encode()
        start = 0
        while start < len(data):
            end = min(start + limit, len(data))
            # Byte offsets may land inside an original UTF-8 code point.
            while end < len(data) and data[end] & 0xC0 == 0x80:
                end -= 1
            yield data[start:end].decode()
            if end == len(data):
                break
            start = end - overlap
            while data[start] & 0xC0 == 0x80:
                start -= 1


def _recognized(
    chunks: list[Chunk], authority: PublicationClient, revision: str = ""
) -> dict[str, str]:
    """Woo recognizes original bounded text, including multi-word draft labels.

    A build must not infer an unknown code's permission from an old index. The
    16,000-byte limit is the existing Woo exact-text endpoint's request contract.
    Original empty ancestor headings retain scope; generated headers are excluded.
    """
    # Preserve the existing 16k request windows. A batch transports up to
    # twenty of those windows, rather than making every short heading its own
    # window or creating a new boundary-spanning match between requests.
    windows: list[str] = []
    batch = ""
    seen = set()
    for chunk in chunks:
        for text in _authored_text_parts(chunk):
            if text in seen:
                continue
            seen.add(text)
            joined = batch + "\n" + text if batch else text
            if len(joined.encode()) > 16000:
                windows.append(batch)
                batch = text
            else:
                batch = joined
    if batch:
        windows.append(batch)
    return authority.identify_texts(windows, revision)


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
        # Preserve the original metadata in publication_manifest; only the build
        # metadata is normalized. Reject unknown vocabulary before any download.
        doc_type_of(str(document["type"]), str(document.get("role", "")))
        lang_of(str(document["lang"]))
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
                doc_type=doc_type_of(
                    str(relations[0]["type"]), str(relations[0].get("role", ""))
                ),
                lang=lang_of(str(relations[0]["lang"])),
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
    chunks: list[Chunk],
    manifest: dict[str, Any],
    authority: PublicationClient,
    *,
    _statuses: dict[str, str] | None = None,
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
    native_tables: dict[tuple[str, str], list[str]] = {}
    for chunk in relevant:
        if chunk.kind == "table" and chunk.source_table:
            native_tables.setdefault((chunk.doc_sha256, chunk.source_table), []).append(
                chunk.id
            )
    statuses = (
        _recognized(relevant, authority, source.model_identity_revision)
        if _statuses is None
        else _statuses
    )
    labels = set(statuses).union(current_labels)
    families = _family_labels(labels)
    patterns = {label: _model_pattern(label) for label in labels}
    shapes = model_shapes(labels)
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
            or _unknown_models(passage, contained, shapes, families=families)
            or _unknown_models(
                chunk.section, contained, shapes, section=True, families=families
            )
        )
        observed[chunk.id] = matched, blocked
        # A model written inside a diagram can prove that diagram's own text;
        # it does not establish the subject of unrelated body or document text.
        positive = (
            matched.intersection(associated) if not chunk.source_picture else set()
        )
        doc_models.setdefault(chunk.doc_sha256, set()).update(positive)
        section_key = chunk.doc_sha256, chunk.section
        sections.setdefault(section_key, set()).update(positive)
        if positive:
            origins.setdefault(chunk.doc_sha256, []).append(chunk.id)
            section_origins.setdefault(section_key, []).append(chunk.id)
        if not chunk.source_picture and COMMON_SCOPE.search(chunk.text):
            common.setdefault(chunk.doc_sha256, []).append(chunk.id)
        if blocked:
            ambiguous.add(chunk.doc_sha256)
            ambiguous_sections.add(section_key)
    columns, table_conflicts = _table_columns(
        relevant, models, patterns, statuses, shapes, observed, families
    )
    manual_scopes = _manual_scopes(relevant, documents, models)
    result: dict[str, ScopeProof] = {}
    for chunk in relevant:
        matched, blocked = observed[chunk.id]
        relations = documents[chunk.doc_sha256]
        general = [
            doc
            for doc in relations
            if document_kind_of(str(doc["type"]), str(doc.get("role", "")))
            in {"warranty", "certificate"}
        ]
        basis, origin = "passage", [chunk.id]
        declaration = manual_scopes.get(chunk.doc_sha256)
        references = _manual_peripheral(
            chunk, relevant, declaration, source, patterns, shapes, families
        )
        if references:
            assert declaration is not None
            matched = set(declaration["product_ids"])
            relations = [
                doc
                for doc in relations
                if document_kind_of(str(doc["type"]), str(doc.get("role", "")))
                == "manual"
            ]
            basis = "manual_peripheral"
            origin = [*declaration["source_chunk_ids"], chunk.id]
        elif blocked or chunk.id in table_conflicts:
            continue
        elif matched:
            if not any(
                patterns[models[pid].casefold()].search(chunk.text) for pid in matched
            ):
                basis = "section"
        elif chunk.id in columns:
            matched = set(columns[chunk.id]["product_ids"])
            if not matched.issubset(
                pid for doc in relations for pid in doc["product_ids"]
            ):
                continue
            basis, origin = "table_columns", columns[chunk.id]["header_chunk_ids"]
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
                "associations": [
                    {
                        "document_id": doc["document_id"],
                        "document_revision": doc["document_revision"],
                        "blob_sha256": doc["blob_sha256"],
                        "product_id": pid,
                        "product_revision": source.products[pid]["product_revision"],
                    }
                    for doc in relations
                    for pid in sorted(matched)
                    if pid in doc["product_ids"]
                ],
            }
            if basis == "table_columns":
                result[chunk.id]["table_columns"] = columns[chunk.id]
            if chunk.kind == "table" and chunk.source_table:
                result[chunk.id]["native_table"] = {
                    "source_table": chunk.source_table,
                    "source_chunk_ids": native_tables[
                        (chunk.doc_sha256, chunk.source_table)
                    ],
                }
            if basis == "manual_peripheral":
                assert declaration is not None
                result[chunk.id]["referenced_products"] = references
                result[chunk.id]["manual_scope"] = declaration
    for scope in result.values():
        scope["model_identity_revision"] = source.model_identity_revision
    return result


def compile_certificate_subjects(
    chunks: list[Chunk],
    source: Snapshot,
    tokenizer: Tokenizer,
    max_tokens: int,
    contexts: dict[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Bind a safe certificate excerpt to one current document/model relation."""
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    covered: set[tuple[str, int, str]] = set()
    originals = {chunk.id: chunk for chunk in chunks}
    certificates: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for did, document in source.documents.items():
        if certificate_document(document):
            certificates.setdefault(document["blob_sha256"], []).append((did, document))
    for chunk in chunks:
        if (
            chunk.kind != "text"
            or chunk.source_picture
            or chunk.doc_sha256 not in certificates
        ):
            continue
        boundaries = []
        for boundary in contexts.get(chunk.id, []):
            prior = originals.get(boundary.get("source_chunk_id", ""))
            if (
                prior is None
                or prior.doc_sha256 != chunk.doc_sha256
                or prior.kind != "text"
            ):
                break
            boundaries.append(
                {
                    "kind": boundary.get("kind"),
                    "quote": boundary.get("quote"),
                    "source_chunk_id": prior.id,
                    "source_page": prior.page,
                    "source_text": prior.text,
                    "source_section": prior.section,
                    "source_headings": list(prior.source_headings),
                }
            )
        else:
            for did, document in certificates[chunk.doc_sha256]:
                for pid in document["product_ids"]:
                    product = source.products.get(pid)
                    if product is None or (did, pid, chunk.lang) in covered:
                        continue
                    model = str(product.get("model", ""))
                    text = certificate_text(chunk.text, model)
                    if text is None or not certificate_boundaries_allow(
                        boundaries,
                        sha=chunk.doc_sha256,
                        page=chunk.page,
                        original=chunk.id,
                        source_text=chunk.text,
                        model=model,
                    ):
                        continue
                    cid = certificate_id(
                        chunk.doc_sha256, chunk.page, model, chunk.id, did, text
                    )
                    header = f"{model} | {document['title']} | p. {chunk.page}"
                    tokens = tokenizer.count(header + "\n" + text)
                    if tokens > max_tokens:
                        continue
                    proof: ScopeProof = {
                        "product_ids": [pid],
                        "basis": "certificate_subject",
                        "source_chunk_ids": list(
                            dict.fromkeys(
                                [
                                    chunk.id,
                                    *(
                                        cast(str, b["source_chunk_id"])
                                        for b in boundaries
                                    ),
                                ]
                            )
                        ),
                        "document_ids": [did],
                        "associations": [
                            {
                                "document_id": did,
                                "document_revision": document["document_revision"],
                                "blob_sha256": chunk.doc_sha256,
                                "product_id": pid,
                                "product_revision": product["product_revision"],
                            }
                        ],
                        "certificate_scope": {
                            "product_id": pid,
                            "document_id": did,
                            "model": model,
                            "source_sha256": chunk.doc_sha256,
                            "source_page": chunk.page,
                            "source_chunk_id": chunk.id,
                            "source_text": chunk.text,
                            "author_boundaries": boundaries,
                            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        },
                    }
                    if not valid_certificate_scope(
                        proof,
                        [pid],
                        source.products,
                        source.documents,
                        sha=chunk.doc_sha256,
                        chunk_id=cid,
                        text=text,
                    ):
                        continue
                    output.append(
                        replace(
                            chunk,
                            id=cid,
                            header=header,
                            text=text,
                            tokens=tokens,
                            source_headings=(),
                            preceding_text=(),
                            source_cells=(),
                            source_rows=(),
                        )
                    )
                    scopes[cid] = proof
                    covered.add((did, pid, chunk.lang))
    return output, scopes


def compile_certificate_fragments(
    chunks: list[Chunk],
    source: Snapshot,
    proofs: dict[str, ScopeProof],
    tokenizer: Tokenizer,
    max_tokens: int,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Retain positive certificate facts only when their original proof holds."""
    from linker_genie.publication_scope import authorize_chunk

    originals = {chunk.id: chunk for chunk in chunks}
    positions = {chunk.id: position for position, chunk in enumerate(chunks)}
    links = [
        {
            "document_id": did,
            "document_revision": document["document_revision"],
            "blob_sha256": document["blob_sha256"],
            "product_id": pid,
            "product_revision": source.products[pid]["product_revision"],
        }
        for did, document in source.documents.items()
        for pid in document["product_ids"]
        if pid in source.products
    ]
    output: list[Chunk] = []
    result: dict[str, ScopeProof] = {}
    for original_id, origin in proofs.items():
        chunk = originals.get(original_id)
        if (
            chunk is None
            or chunk.source_picture
            or origin["basis"]
            not in {
                "passage",
                "section",
                "section_model",
                "document_model",
                "common_terms",
            }
        ):
            continue
        for did in origin["document_ids"]:
            document = source.documents.get(did)
            if document is None or not certificate_document(document):
                continue
            for pid in origin["product_ids"]:
                product = source.products.get(pid)
                if product is None or pid not in document["product_ids"]:
                    continue
                model = str(product.get("model", ""))
                anchors = [
                    originals[anchor_id]
                    for anchor_id in origin["source_chunk_ids"]
                    if anchor_id in originals
                    and originals[anchor_id].doc_sha256 == chunk.doc_sha256
                    and _model_pattern(model).search(originals[anchor_id].text)
                ]
                anchors.sort(key=lambda anchor: anchor.page != chunk.page)
                if not anchors:
                    continue
                anchor = anchors[0]
                middle: list[Chunk] = []
                if split_declaration(chunk.text):
                    distance = positions[anchor.id] - positions[chunk.id]
                    middle = chunks[positions[chunk.id] + 1 : positions[anchor.id]]
                    if (
                        anchor.page != chunk.page
                        or anchor.lang != chunk.lang
                        or distance not in (1, 2)
                        or any(
                            c.doc_sha256 != chunk.doc_sha256
                            or c.page != chunk.page
                            or not re.fullmatch(r"[A-Za-z]{1,8}", c.text.strip())
                            for c in middle
                        )
                    ):
                        continue
                registration = None
                if anchor.page != chunk.page:
                    number = certificate_registration(anchor.text)
                    registration = next(
                        (
                            candidate
                            for candidate in chunks
                            if candidate.doc_sha256 == chunk.doc_sha256
                            and candidate.page == chunk.page
                            and number
                            and certificate_registration(candidate.text) == number
                        ),
                        None,
                    )
                    if registration is None:
                        continue
                limitation = None
                if lcie_declaration(chunk.text):
                    limitation = next(
                        (
                            candidate
                            for candidate in chunks
                            if candidate.doc_sha256 == chunk.doc_sha256
                            and candidate.page == chunk.page
                            and lcie_limitation(candidate.text)
                        ),
                        None,
                    )
                    if limitation is None:
                        continue
                text = certificate_fragment_text(
                    chunk.text,
                    model,
                    subject_text=anchor.text,
                    limitation_text=limitation.text if limitation else "",
                )
                if text is None:
                    continue

                def anchor_evidence(item: Chunk) -> dict[str, Any]:
                    return {
                        "page": item.page,
                        "chunk_id": item.id,
                        "kind": item.kind,
                        "text": item.text,
                        "lang": item.lang,
                    }

                cid = certificate_fragment_id(
                    chunk.doc_sha256, chunk.page, model, chunk.id, did, text
                )
                header = f"{model} | {document['title']} | p. {chunk.page}"
                tokens = tokenizer.count(header + "\n" + text)
                if tokens > max_tokens:
                    continue
                proof: ScopeProof = {
                    "product_ids": [pid],
                    "basis": "certificate_fragment",
                    "source_chunk_ids": list(
                        dict.fromkeys(
                            [
                                chunk.id,
                                *origin["source_chunk_ids"],
                                *(c.id for c in middle),
                                *([registration.id] if registration else []),
                                *([limitation.id] if limitation else []),
                            ]
                        )
                    ),
                    "document_ids": [did],
                    "associations": [
                        {
                            "document_id": did,
                            "document_revision": document["document_revision"],
                            "blob_sha256": chunk.doc_sha256,
                            "product_id": pid,
                            "product_revision": product["product_revision"],
                        }
                    ],
                    "certificate_fragment": {
                        "product_id": pid,
                        "document_id": did,
                        "model": model,
                        "source_sha256": chunk.doc_sha256,
                        "source_page": chunk.page,
                        "source_chunk_id": chunk.id,
                        "source_kind": chunk.kind,
                        "source_text": chunk.text,
                        "origin_scope": origin,
                        "subject_anchor": anchor_evidence(anchor),
                        "registration_anchor": (
                            anchor_evidence(registration) if registration else None
                        ),
                        "limitation_anchor": (
                            anchor_evidence(limitation) if limitation else None
                        ),
                        "between_anchors": [anchor_evidence(c) for c in middle],
                        "source_lang": chunk.lang,
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    },
                }
                if not authorize_chunk(
                    chunk.doc_sha256,
                    [pid],
                    links,
                    proof,
                    products=source.products,
                    documents=source.documents,
                    chunk_id=cid,
                    text=text,
                ):
                    continue
                output.append(
                    replace(
                        chunk,
                        id=cid,
                        kind="text",
                        header=header,
                        text=text,
                        tokens=tokens,
                        source_table="",
                        source_headings=(),
                        preceding_text=(),
                        source_cells=(),
                        source_rows=(),
                    )
                )
                result[cid] = proof
    return output, result


def compile_publication(
    chunks: list[Chunk],
    manifest: dict[str, Any],
    authority: PublicationClient,
    tokenizer: Tokenizer,
    max_tokens: int = MAX_TOKENS,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Original strict passages plus automatic per-model source answer units.

    Run before embedding: the model must see the selected current column's
    text, never the old multi-model text with merely narrower permission IDs.
    """
    from index.table_compiler import compile_scopes

    revision = Snapshot.read(manifest).model_identity_revision
    output, scopes = compile_scopes(chunks, manifest, authority, tokenizer, max_tokens)
    for scope in scopes.values():
        scope["model_identity_revision"] = revision
    return output, scopes
