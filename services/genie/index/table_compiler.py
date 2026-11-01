"""Compile native multi-model tables into current-model answer units."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import replace
from typing import Any, cast

from index.chunking import Chunk, Tokenizer
from index.inventory import document_kind_of
from index.publication import (
    ScopeProof,
    _recognized,
    compile_certificate_fragments,
    compile_certificate_subjects,
    scope_proofs,
)
from linker_genie.certificate_scope import has_explicit_exclusion
from linker_genie.family_scope import family_id
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.publication_scope import author_scope_allows
from linker_genie.source_models import (
    ENGINEERING,
    codes,
    family_labels,
    family_mentions,
    model_pattern,
    model_shapes,
    unknown_models,
)
from linker_genie.table_projection import (
    COMPATIBILITY_STATEMENT,
    OVERVIEW_SECTIONS,
    SourceCell,
    cells_digest,
    compatibility_batteries,
    compatibility_inverters,
    compatibility_pair_id,
    compatibility_pair_text,
    compatibility_row_in_source,
    model_axis,
    overview_id,
    overview_notes,
    overview_row,
    overview_row_in_source,
    overview_text,
    projection_id,
    read_cells,
    render_projection,
    row_footnotes,
    safe_rows,
)

SCOPE_DECLARATION = re.compile(
    r"\b(?:only|solely|exclusively|appl(?:y|ies|icable)|instructions?|procedures?"
    r"|models?|modelle?|nur|ausschließlich|gelten|gilt|anweisungen)\b",
    re.IGNORECASE,
)


def _author_contexts(
    chunks: list[Chunk], source: Snapshot, statuses: dict[str, str]
) -> dict[str, list[dict[str, Any]]]:
    """Keep narrower context until an explicit family-wide heading resets it.

    Docling's heading levels are not consistently available. A generic next
    heading therefore cannot prove that a narrow parent ended. This deliberately
    fails closed across that boundary instead of guessing a sibling hierarchy.
    """
    models = {str(p.get("model", "")).casefold() for p in source.products.values()}
    labels = models.union(statuses)
    families = family_labels(labels)
    shapes = model_shapes(labels)
    rating_range = (
        r"\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*"
        r"(?:kWh|MWh|Wh|kW|MW|W)"
    )
    ratings = re.compile(
        r"(?<![\w./-])"
        + rating_range
        + r"(?:\s*/\s*"
        + rating_range
        + r")*(?![\w./-])",
        re.IGNORECASE,
    )
    active: dict[str, list[dict[str, Any]]] = {}
    figure_active: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    previous: dict[str, str] = {}
    paths: dict[str, tuple[int, ...]] = {}
    output = {}
    for chunk in chunks:
        sha = chunk.doc_sha256
        boundaries = list(active.get(sha, []))
        headings = chunk.source_headings
        if not headings and chunk.section != previous.get(sha):
            headings = (chunk.section,) if chunk.section else ()
        previous[sha] = chunk.section
        outer: list[dict[str, Any]] | None = None
        for kind, text in [
            *(("heading", h) for h in headings),
            ("declaration", chunk.text),
        ]:
            if kind == "declaration":
                if chunk.source_picture:
                    # A figure's own labels can restrict its later fragments,
                    # but must never restrict the surrounding document.
                    outer = list(boundaries)
                    previous_figure = figure_active.get(sha)
                    if previous_figure and previous_figure[0] == chunk.source_picture:
                        boundaries.extend(previous_figure[1])
                elif chunk.kind != "text" or (
                    SCOPE_DECLARATION.search(text) is None
                    and not has_explicit_exclusion(text)
                ):
                    continue
            if kind == "heading":
                numbered = re.match(r"^\s*(\d+(?:\.\d+)*)(?:[.)]\s*|\s+)", text)
                if numbered is not None:
                    path = tuple(int(part) for part in numbered[1].split("."))
                    # Original chapter numbers prove a sibling/ancestor boundary.
                    # Missing/flat parser levels and unnumbered child titles do not.
                    boundaries = [
                        boundary
                        for boundary in boundaries
                        if not boundary.get("heading_path")
                        or path[: len(boundary["heading_path"])]
                        == tuple(boundary["heading_path"])
                    ]
                    paths[sha] = path
                else:
                    # An unnumbered narrower heading has no proven level. It
                    # must not borrow the previous chapter's path and later be
                    # cleared as though it were a numbered sibling's child.
                    paths.pop(sha, None)
            # Standalone original family headings are explicit broader resets.
            # A child title merely mentioning a family ('ports of H2') is not.
            plain = re.sub(r"^\s*[\d.]+\s*", "", text).strip()
            if kind == "heading" and any(
                re.fullmatch(
                    re.escape(family) + r"[-\s]+(?:series?|serie)", plain, re.IGNORECASE
                )
                for family in families
            ):
                boundaries = []
                continue
            broad_family = (
                kind == "heading"
                and not re.search(
                    r"\b(?:only|nur|solely|exclusively)\b", text, re.IGNORECASE
                )
                and re.search(
                    r"\b(?:series?|serie|solutions?|systems?|inverters?|wechselrichter)\b",
                    text,
                    re.IGNORECASE,
                )
                and any(
                    re.search(
                        r"(?<![\w./-])" + re.escape(f) + r"(?=[/\s]|$)",
                        text,
                        re.IGNORECASE,
                    )
                    for f in families
                )
                and all(
                    ENGINEERING.fullmatch(token)
                    or all(
                        re.fullmatch(r"[A-Za-z]+\d+", part) for part in token.split("/")
                    )
                    for token in codes(text)
                )
            )
            contained = {
                label for label in labels if label and model_pattern(label).search(text)
            }
            unknown = unknown_models(
                text, contained, shapes, section=kind == "heading", families=families
            )
            if contained or (not broad_family and unknown):
                boundary: dict[str, Any] = {
                    "kind": kind,
                    "quote": text,
                    "source_chunk_id": chunk.id,
                    "heading_path": list(paths.get(sha, ())),
                }
                # A generic cover's unit-bearing engineering range is not a
                # model identity. Keep it as a restriction on ordinary content;
                # only a separately proven original model axis can supersede it.
                if (
                    kind == "heading"
                    and chunk.page == 1
                    and not contained
                    and unknown
                    and re.search(r"\bAll[- ]in[- ]One\b", text, re.IGNORECASE)
                    and SCOPE_DECLARATION.search(text) is None
                    and ratings.search(text) is not None
                    and not unknown_models(
                        ratings.sub(" ", text),
                        contained,
                        shapes,
                        section=True,
                        families=families,
                    )
                ):
                    boundary["rating_cover"] = True
                boundaries.append(boundary)
        if chunk.source_picture:
            assert outer is not None
            figure_active[sha] = (chunk.source_picture, boundaries[len(outer) :])
            active[sha] = outer
        else:
            figure_active.pop(sha, None)
            active[sha] = boundaries
        if boundaries:
            output[chunk.id] = boundaries
    return output


def _constrain(proof: ScopeProof, boundaries: list[dict[str, Any]]) -> ScopeProof:
    return {
        **proof,
        "author_restrictions": boundaries,
        "source_chunk_ids": list(
            dict.fromkeys(
                [
                    *proof["source_chunk_ids"],
                    *(b["source_chunk_id"] for b in boundaries),
                ]
            )
        ),
    }


def _scope(source: Snapshot, sha: str, pid: int, *, manual: bool = False) -> ScopeProof:
    documents = [
        document
        for document in source.documents.values()
        if document["blob_sha256"] == sha
        and pid in document["product_ids"]
        and (
            not manual
            or document_kind_of(str(document["type"]), str(document.get("role", "")))
            == "manual"
        )
    ]
    return {
        "product_ids": [pid],
        "basis": "table_projection",
        "source_chunk_ids": [],
        "document_ids": sorted(d["document_id"] for d in documents),
        "associations": [
            {
                "document_id": document["document_id"],
                "document_revision": document["document_revision"],
                "blob_sha256": sha,
                "product_id": pid,
                "product_revision": source.products[pid]["product_revision"],
            }
            for document in documents
        ],
    }


def _family_units(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
    strict: dict[str, ScopeProof],
    contexts: dict[str, list[dict[str, Any]]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Literal family manual scope plus Woo associations, with finer overrides.

    A family title can support shared instructions, never an unnamed parameter
    table or another variant's explicit facts. Each current model gets its own
    answer unit so removing B does not revoke unchanged common instructions for A.
    """
    models = {
        pid: str(product.get("model", "")) for pid, product in source.products.items()
    }
    labels = {model.casefold() for model in models.values() if model}.union(statuses)
    families = family_labels(labels)
    shapes = model_shapes(labels)
    origins: dict[str, dict[str, tuple[str, str]]] = {}
    for chunk in chunks:
        named = family_mentions(chunk.section, families)
        if len(named) != 1 or unknown_models(
            chunk.section, set(), shapes, section=True, families=families
        ):
            continue
        family = next(iter(named))
        origins.setdefault(chunk.doc_sha256, {}).setdefault(
            family, (chunk.id, chunk.section)
        )
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for chunk in chunks:
        if chunk.kind != "text":
            continue
        if chunk.id in strict or chunk.id in contexts:
            # Existing finer authored evidence is authoritative. A generic
            # family pass never widens it, including same-section continuation.
            continue
        own = family_mentions(chunk.section, families)
        candidates = origins.get(chunk.doc_sha256, {})
        if len(own) == 1:
            family = next(iter(own))
            anchor = (chunk.id, chunk.section)
        elif own or len(candidates) != 1:
            continue
        else:
            family, anchor = next(iter(candidates.items()))
        if any(
            model_pattern(label).search(chunk.text) for label in labels
        ) or unknown_models(
            chunk.section + "\n" + chunk.text,
            set(),
            shapes,
            section=True,
            families=families,
        ):
            continue
        for pid, model in models.items():
            if not model.casefold().startswith(family + "-"):
                continue
            proof = _scope(source, chunk.doc_sha256, pid, manual=True)
            if not proof["associations"]:
                continue
            header = " | ".join(
                part
                for part in [model, family, chunk.section, f"p. {chunk.page}"]
                if part
            )
            tokens = tokenizer.count(header + "\n" + chunk.text)
            if tokens > max_tokens:
                continue
            cid = family_id(chunk.doc_sha256, chunk.page, model, chunk.id, chunk.text)
            output.append(replace(chunk, id=cid, header=header, tokens=tokens))
            scopes[cid] = {
                **proof,
                "basis": "family_manual",
                "source_chunk_ids": list(dict.fromkeys([anchor[0], chunk.id])),
                "family_scope": {
                    "family": family,
                    "quote": anchor[1],
                    "anchor_chunk_id": anchor[0],
                    "source_chunk_id": chunk.id,
                    "source_page": chunk.page,
                    "source_sha256": chunk.doc_sha256,
                    "product_id": pid,
                    "model": model,
                    "text_sha256": hashlib.sha256(chunk.text.encode()).hexdigest(),
                },
            }
    return output, scopes


def _pack_rows(
    cells: Sequence[SourceCell],
    column: int,
    rows: Sequence[int],
    header: str,
    tokenizer: Tokenizer,
    max_tokens: int,
) -> list[list[int]]:
    """Keep source row boundaries; an oversized field is never silently cut."""
    groups: list[list[int]] = []
    current: list[int] = []
    current_notes: tuple[str, ...] | None = None
    for row in rows:
        footnotes = row_footnotes(cells, row, column)
        assert footnotes is not None
        notes = tuple(sorted(note["text"] for note in footnotes))
        if current and notes != current_notes:
            groups.append(current)
            current = []
        text = render_projection(cells, column, [*current, row])
        assert text is not None
        if tokenizer.count(header + "\n" + text) > max_tokens:
            if current:
                groups.append(current)
                current = []
            text = render_projection(cells, column, [row])
            assert text is not None
            if tokenizer.count(header + "\n" + text) > max_tokens:
                continue
        current.append(row)
        current_notes = notes
    if current:
        groups.append(current)
    return groups


def _axis_source(
    table: Chunk, cells: Sequence[SourceCell], by_id: dict[str, Chunk]
) -> list[dict[str, str]] | None:
    """Consecutive same-page text chunks must end with the native header."""
    external = [cell["external_axis"] for cell in cells if "external_axis" in cell]
    if len(external) != 1:
        return None
    wanted = external[0]["source_text"]
    pieces: list[Chunk] = []
    for cid in reversed(table.preceding_text):
        origin = by_id.get(cid)
        if (
            origin is None
            or origin.page != table.page
            or origin.doc_sha256 != table.doc_sha256
            or origin.kind != "text"
        ):
            break
        pieces.insert(0, origin)
        joined = "\n".join(part.text for part in pieces)
        if len(joined) < len(wanted):
            continue
        if (
            joined.endswith(wanted)
            and joined.count(wanted) == 1
            and (len(joined) == len(wanted) or joined[-len(wanted) - 1] == "\n")
        ):
            return [{"chunk_id": part.id, "text": part.text} for part in pieces]
        break
    return None


def _series_cover_for_axis(
    boundary: dict[str, Any], axis: Sequence[str], by_id: dict[str, Chunk]
) -> bool:
    """A generic cover can be narrower only if it conflicts with the source axis.

    The Lynx D G2 cover and its original D-G20 model columns establish the
    observed letter and generation pattern.  A different letter, generation,
    declaration, exclusion or explicit model stays a binding restriction.
    """
    quote = boundary.get("quote")
    origin = by_id.get(str(boundary.get("source_chunk_id", "")))
    if (
        boundary.get("kind") != "heading"
        or not isinstance(quote, str)
        or origin is None
        or origin.page != 1
        or quote not in origin.source_headings
        or has_explicit_exclusion(quote)
    ):
        return False
    match = re.fullmatch(
        r"[A-Za-z]+\s+([A-Za-z])\s+(G\d+)\s+Series", quote, re.IGNORECASE
    )
    return bool(
        match
        and axis
        and all(
            re.search(
                r"-" + re.escape(match[1]) + r"-" + re.escape(match[2]) + r"\d$",
                label,
                re.IGNORECASE,
            )
            for label in axis
        )
    )


def _footnote_sources(
    table: Chunk, cells: Sequence[SourceCell], by_id: dict[str, Chunk]
) -> list[dict[str, Any]]:
    """Resolve each complete note to its own original, same-document chunk."""
    external = next(
        (cell["external_axis"] for cell in cells if "external_axis" in cell), None
    )
    if external is None:
        return []
    sources = []
    for note in external["footnotes"]:
        matches = [
            chunk
            for chunk in by_id.values()
            if chunk.doc_sha256 == table.doc_sha256
            and chunk.page == note["pdf_span"]["page"]
            and chunk.kind == "text"
            and not chunk.source_picture
            and chunk.lang in {"en", "de"}
            and chunk.text.splitlines().count(note["text"]) == 1
        ]
        if len(matches) == 1:
            source = matches[0]
            sources.append(
                {
                    "chunk_id": source.id,
                    "page": source.page,
                    "text": source.text,
                    "source_id": note["source_id"],
                    "quote": note["text"],
                    "lang": source.lang,
                }
            )
    return sources


def external_axis_anchors(chunks: list[Chunk]) -> dict[str, dict[str, Any]]:
    """Derive canonical table anchors from original chunks, not projections."""
    from linker_genie.table_projection import native_chunk_id_matches

    by_id = {chunk.id: chunk for chunk in chunks}
    anchors: dict[str, dict[str, Any]] = {}
    policy_shas: set[str] = set()
    for chunk in chunks:
        if chunk.source_pdf_cover:
            from linker_genie.warranty_scope import valid_pdf_cover

            if valid_pdf_cover(
                chunk.source_pdf_cover, chunk.doc_sha256, chunk.id, chunk.text
            ):
                anchors[chunk.id] = chunk.source_pdf_cover
        if chunk.kind != "table" or not chunk.source_table:
            continue
        cells = read_cells(chunk.source_cells)
        if cells is None:
            continue
        external = any("external_axis" in cell for cell in cells)
        origin = _axis_source(chunk, cells, by_id) if external else []
        if external and origin is None:
            continue
        anchors[chunk.id] = {
            "source_sha256": chunk.doc_sha256,
            "source_page": chunk.page,
            "source_table": chunk.source_table,
            "source_cells_sha256": cells_digest(cells),
            "axis_source": origin,
            "footnote_sources": _footnote_sources(chunk, cells, by_id)
            if external
            else [],
        }
        if (
            chunk.page == 1
            and chunk.section == COMPATIBILITY_STATEMENT
            and chunk.section in chunk.source_headings
        ):
            candidates = [
                other
                for other in chunks[: chunks.index(chunk)]
                if other.doc_sha256 == chunk.doc_sha256
                and other.page == chunk.page
                and other.kind == "text"
                and compatibility_batteries(other.text)
                and not has_explicit_exclusion(other.text)
            ]
            between = (
                chunks[chunks.index(candidates[0]) + 1 : chunks.index(chunk)]
                if len(candidates) == 1
                else []
            )
            if len(candidates) == 1 and not any(
                other.doc_sha256 == chunk.doc_sha256
                and (
                    (other.kind == "text" and other.text.strip())
                    or has_explicit_exclusion(other.text)
                )
                for other in between
            ):
                anchors[chunk.id]["axis_source"] = [
                    {"chunk_id": candidates[0].id, "text": candidates[0].text}
                ]
                anchors[chunk.id]["compatibility_section"] = chunk.section
                anchors[chunk.id]["compatibility_table_text"] = chunk.text
                anchors[chunk.id]["compatibility_source_rows"] = list(chunk.source_rows)
        if (
            chunk.section in OVERVIEW_SECTIONS
            and chunk.source_headings
            and chunk.source_headings[-1] == chunk.section
            and set(chunk.source_headings).issubset(
                {
                    chunk.section,
                    "Battery Compatibility Overview",
                    "Batteriekompatibilitätsübersicht",
                }
            )
        ):
            lang = OVERVIEW_SECTIONS[chunk.section]
            possible = [
                other
                for other in chunks
                if other.doc_sha256 == chunk.doc_sha256
                and other.page == chunk.page
                and other.kind == "text"
                and native_chunk_id_matches(
                    other.doc_sha256, other.page, "text", other.text, other.id
                )
            ]
            notes = overview_notes([other.text for other in possible], lang)
            if notes is not None:
                sources = [
                    other
                    for other in possible
                    if notes[0] in other.text.splitlines() or other.text == notes[1]
                ]
                if len(sources) == 2:
                    anchors[chunk.id]["axis_source"] = [
                        {"chunk_id": other.id, "text": other.text} for other in sources
                    ]
                    anchors[chunk.id]["overview_lang"] = lang
                    anchors[chunk.id]["overview_section"] = chunk.section
                    anchors[chunk.id]["overview_fragments"] = [
                        {
                            "chunk_id": other.id,
                            "text": other.text,
                            "rows": list(other.source_rows),
                        }
                        for other in chunks
                        if other.doc_sha256 == chunk.doc_sha256
                        and other.page == chunk.page
                        and other.kind == "table"
                        and other.source_table == chunk.source_table
                    ]
        headers = {
            c["col_start"]: re.sub(r"\s+", "", c["text"]).casefold()
            for c in cells
            if c["column_header"] and c["row_start"] == 0
        }
        if headers in (
            {0: "warrantyperiod", 1: "dateofmanufacture", 2: "product", 3: "series"},
            {
                0: "garantiezeitraum",
                1: "herstellungsdatum",
                2: "produktgruppe",
                3: "serien",
            },
        ):
            policy_shas.add(chunk.doc_sha256)
            anchors[chunk.id]["kind"] = "policy_table"
            anchors[chunk.id]["fragments"] = [
                {"chunk_id": c.id, "text": c.text, "rows": list(c.source_rows)}
                for c in chunks
                if c.doc_sha256 == chunk.doc_sha256
                and c.page == chunk.page
                and c.kind == "table"
                and c.source_table == chunk.source_table
                and native_chunk_id_matches(c.doc_sha256, c.page, "table", c.text, c.id)
            ]
    for chunk in chunks:
        if (
            chunk.doc_sha256 in policy_shas
            and chunk.kind == "text"
            and native_chunk_id_matches(
                chunk.doc_sha256, chunk.page, "text", chunk.text, chunk.id
            )
        ):
            anchors[chunk.id] = {
                "kind": "policy_text",
                "source_sha256": chunk.doc_sha256,
                "source_page": chunk.page,
                "text": chunk.text,
                "lang": chunk.lang,
                "section": chunk.section,
            }
    return anchors


def _compatibility_units(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
    anchors: dict[str, dict[str, Any]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Make a two-product unit only from an explicit statement and exact row."""
    models = {
        str(p.get("model", "")).casefold(): pid for pid, p in source.products.items()
    }
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for table in chunks:
        anchor = anchors.get(table.id, {})
        origins = anchor.get("axis_source", [])
        if (
            anchor.get("compatibility_section") != COMPATIBILITY_STATEMENT
            or len(origins) != 1
        ):
            continue
        cells = read_cells(table.source_cells)
        if cells is None:
            continue
        batteries = compatibility_batteries(origins[0]["text"])
        for row in sorted({c["row_start"] for c in cells if c["row_start"] > 0}):
            if not compatibility_row_in_source(
                cells, row, table.text, table.source_rows
            ):
                continue
            for inverter in compatibility_inverters(cells, row):
                for battery in batteries:
                    bid, iid = (
                        models.get(battery.casefold()),
                        models.get(inverter.casefold()),
                    )
                    if (
                        bid is None
                        or iid is None
                        or bid == iid
                        or statuses.get(battery.casefold()) != "published"
                        or statuses.get(inverter.casefold()) != "published"
                    ):
                        continue
                    for did, doc in source.documents.items():
                        if (
                            doc["blob_sha256"] != table.doc_sha256
                            or document_kind_of(
                                str(doc["type"]), str(doc.get("role", ""))
                            )
                            != "compatibility"
                            or not {bid, iid}.issubset(doc["product_ids"])
                            or did not in source.products[bid]["documents"]
                            or did not in source.products[iid]["documents"]
                        ):
                            continue
                        battery_model = str(source.products[bid]["model"])
                        inverter_model = str(source.products[iid]["model"])
                        text = compatibility_pair_text(battery_model, inverter_model)
                        header = f"{battery_model} | {inverter_model} | p. {table.page}"
                        tokens = tokenizer.count(header + "\n" + text)
                        if tokens > max_tokens:
                            continue
                        cid = compatibility_pair_id(
                            table.doc_sha256, table.page, table.source_table, text
                        )
                        if cid in scopes:
                            continue
                        ids = sorted([bid, iid])
                        proof: dict[str, Any] = {
                            "product_ids": ids,
                            "basis": "compatibility_pair",
                            "source_chunk_ids": [origins[0]["chunk_id"], table.id],
                            "document_ids": [did],
                            "associations": [
                                {
                                    "document_id": did,
                                    "document_revision": doc["document_revision"],
                                    "blob_sha256": table.doc_sha256,
                                    "product_id": pid,
                                    "product_revision": source.products[pid][
                                        "product_revision"
                                    ],
                                }
                                for pid in ids
                            ],
                            "compatibility_pair": {
                                "battery_id": bid,
                                "inverter_id": iid,
                                "battery": battery_model,
                                "inverter": inverter_model,
                                "source_sha256": table.doc_sha256,
                                "source_page": table.page,
                                "source_table": table.source_table,
                                "source_row": row,
                                "source_cells": list(cells),
                                "source_cells_sha256": cells_digest(cells),
                                "table_chunk_id": table.id,
                                "battery_source": origins[0],
                            },
                        }
                        output.append(
                            replace(
                                table,
                                id=cid,
                                kind="text",
                                header=header,
                                text=text,
                                tokens=tokens,
                                source_table="",
                                source_cells=(),
                                source_rows=(),
                                source_headings=(),
                                preceding_text=(),
                            )
                        )
                        scopes[cid] = cast(ScopeProof, proof)
    return output, scopes


def _overview_units(
    chunks: list[Chunk],
    source: Snapshot,
    statuses: dict[str, str],
    tokenizer: Tokenizer,
    max_tokens: int,
    anchors: dict[str, dict[str, Any]],
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    models = {
        str(p.get("model", "")).casefold(): pid for pid, p in source.products.items()
    }
    output: list[Chunk] = []
    scopes: dict[str, ScopeProof] = {}
    for table in chunks:
        anchor = anchors.get(table.id, {})
        lang = anchor.get("overview_lang")
        origins, fragments = (
            anchor.get("axis_source", []),
            anchor.get("overview_fragments", []),
        )
        if lang not in ("en", "de") or len(origins) != 2:
            continue
        cells = read_cells(table.source_cells)
        if cells is None:
            continue
        for row in sorted({c["row_start"] for c in cells if c["row_start"] >= 2}):
            for col in (5, 6, 7):
                native = overview_row(cells, row, col, lang)
                if native is None:
                    continue
                model, series = native
                pid = models.get(model.casefold())
                if pid is None or statuses.get(model.casefold()) != "published":
                    continue
                matches = [
                    f for f in fragments if overview_row_in_source(model, col, row, f)
                ]
                if len(matches) != 1:
                    continue
                text = overview_text(model, series, lang, [o["text"] for o in origins])
                if text is None:
                    continue
                proof = _scope(source, table.doc_sha256, pid)
                proof["basis"] = "compatibility_series"
                proof["associations"] = [
                    a
                    for a in proof["associations"]
                    if document_kind_of(
                        str(source.documents[a["document_id"]]["type"]),
                        str(source.documents[a["document_id"]].get("role", "")),
                    )
                    == "compatibility"
                ]
                proof["document_ids"] = sorted(
                    {a["document_id"] for a in proof["associations"]}
                )
                if not proof["associations"]:
                    continue
                header = f"{model} | p. {table.page}"
                tokens = tokenizer.count(header + "\n" + text)
                if tokens > max_tokens:
                    continue
                cid = overview_id(
                    table.doc_sha256, table.page, table.source_table, text
                )
                if cid in scopes:
                    continue
                proof["source_chunk_ids"] = list(
                    dict.fromkeys(
                        [
                            table.id,
                            matches[0]["chunk_id"],
                            *(o["chunk_id"] for o in origins),
                        ]
                    )
                )
                extended: dict[str, Any] = {
                    **proof,
                    "compatibility_series": {
                        "product_id": pid,
                        "model": model,
                        "lang": lang,
                        "source_sha256": table.doc_sha256,
                        "source_page": table.page,
                        "source_table": table.source_table,
                        "source_row": row,
                        "source_column": col,
                        "source_cells": list(cells),
                        "source_cells_sha256": cells_digest(cells),
                        "table_chunk_id": table.id,
                        "fragment_chunk_id": matches[0]["chunk_id"],
                    },
                }
                output.append(
                    replace(
                        table,
                        id=cid,
                        kind="text",
                        header=header,
                        text=text,
                        tokens=tokens,
                        source_table="",
                        source_cells=(),
                        source_rows=(),
                        source_headings=(),
                        preceding_text=(),
                    )
                )
                scopes[cid] = cast(ScopeProof, extended)
    return output, scopes


def compile_scopes(
    chunks: list[Chunk],
    manifest: dict[str, Any],
    authority: PublicationClient,
    tokenizer: Tokenizer,
    max_tokens: int,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    """Reuse original parses, binding each derived unit to its own Woo links."""
    source = Snapshot.read(manifest)
    shas = {document["blob_sha256"] for document in source.documents.values()}
    relevant = [chunk for chunk in chunks if chunk.doc_sha256 in shas]
    statuses = _recognized(relevant, authority, source.model_identity_revision)
    result = scope_proofs(chunks, manifest, authority, _statuses=statuses)
    contexts = _author_contexts(relevant, source, statuses)
    for cid in list(result):
        if cid not in contexts:
            continue
        constrained = _constrain(result[cid], contexts[cid])
        if author_scope_allows(
            constrained, set(constrained["product_ids"]), source.products
        ):
            result[cid] = constrained
        else:
            del result[cid]
    output = list(chunks)
    by_id = {chunk.id: chunk for chunk in relevant}
    groups: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in relevant:
        if chunk.kind == "table" and chunk.source_table:
            groups.setdefault((chunk.doc_sha256, chunk.source_table), []).append(chunk)
    current = {
        str(product.get("model", "")).casefold(): pid
        for pid, product in source.products.items()
        if product.get("model")
    }
    for (sha, table), parts in groups.items():
        first = parts[0]
        cells = read_cells(first.source_cells)
        if (
            cells is None
            or any(part.source_cells for part in parts[1:])
            or any(part.page != first.page for part in parts)
        ):
            continue
        if any(
            span["source_sha256"] != sha or span["page"] != first.page
            for cell in cells
            for span in [
                *cell.get("model_spans", []),
                *cell.get("external_axis", {}).get("model_spans", []),
            ]
        ):
            continue
        if any(
            note["pdf_span"]["source_sha256"] != sha
            for cell in cells
            for note in cell.get("external_axis", {}).get("footnotes", [])
        ):
            continue
        axis = model_axis(cells)
        if axis is None:
            continue
        external = [cell["external_axis"] for cell in cells if "external_axis" in cell]
        axis_source: list[dict[str, str]] | None = None
        if external:
            # The physical header is the original native text immediately before
            # this table, not a matching model string elsewhere in the document.
            axis_source = _axis_source(first, cells, by_id)
            if axis_source is None:
                continue
        note_sources = _footnote_sources(first, cells, by_id) if external else []
        source_quotes = {note["quote"] for note in note_sources}
        # Keep proven legacy whole passages in place. A projection does not
        # weaken their all-column current-association rule or reuse their IDs.
        known = [*current, *statuses, *axis]
        native_rows = sorted(
            {
                row
                for cell in cells
                for row in range(cell["row_start"], cell["row_end"])
                if row > 0 or (external and external[0]["first_row_is_data"])
            }
        )
        for column, label in enumerate(axis, 1):
            pid = current.get(label.casefold())
            if (
                pid is None
                or statuses.get(label.casefold(), "published") != "published"
            ):
                continue
            proof = _scope(source, sha, pid)
            if not proof["associations"]:
                continue
            if first.id in contexts:
                # The exact, physically proven table axis is narrower than an
                # unqualified engineering-range cover heading. Other authored
                # model restrictions remain authoritative.
                boundaries = [
                    boundary
                    for boundary in contexts[first.id]
                    if boundary.get("rating_cover") is not True
                    and not _series_cover_for_axis(boundary, axis, by_id)
                ]
                if boundaries:
                    proof = _constrain(proof, boundaries)
                    if not author_scope_allows(proof, {pid}, source.products):
                        continue
            model = str(source.products[pid]["model"])
            header = f"{model} | p. {first.page}"
            safe = [
                row
                for row in native_rows
                if render_projection(cells, column, [row]) is not None
                and safe_rows(cells, column, [row], model, known)
                and all(
                    note["text"] in source_quotes
                    for note in row_footnotes(cells, row, column) or []
                )
            ]
            for rows in _pack_rows(cells, column, safe, header, tokenizer, max_tokens):
                text = render_projection(cells, column, rows)
                assert text is not None
                used_quotes = {
                    note["text"]
                    for row in rows
                    for note in row_footnotes(cells, row, column) or []
                }
                used_sources = [
                    note for note in note_sources if note["quote"] in used_quotes
                ]
                cid = projection_id(sha, first.page, table, model, text)
                output.append(
                    replace(
                        first,
                        id=cid,
                        header=header,
                        text=text,
                        tokens=tokenizer.count(header + "\n" + text),
                        source_rows=tuple(rows),
                        source_cells=(),
                    )
                )
                result[cid] = {
                    **proof,
                    "source_chunk_ids": list(
                        dict.fromkeys(
                            [
                                *proof["source_chunk_ids"],
                                *(part["chunk_id"] for part in axis_source or []),
                                *(note["chunk_id"] for note in used_sources),
                                *(part.id for part in parts),
                            ]
                        )
                    ),
                    "table_projection": {
                        "source_sha256": sha,
                        "source_table": table,
                        "source_page": first.page,
                        "source_cells": list(cells),
                        "source_cells_sha256": cells_digest(cells),
                        "source_rows": rows,
                        "model_column": column,
                        "product_id": pid,
                        "model": model,
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        **({"axis_source": axis_source} if axis_source else {}),
                        **({"footnote_sources": used_sources} if used_sources else {}),
                    },
                }
    source_anchors = external_axis_anchors(relevant)
    compatibility, compatibility_scopes = _compatibility_units(
        relevant, source, statuses, tokenizer, max_tokens, source_anchors
    )
    output.extend(compatibility)
    result.update(compatibility_scopes)
    overviews, overview_scopes = _overview_units(
        relevant, source, statuses, tokenizer, max_tokens, source_anchors
    )
    output.extend(overviews)
    result.update(overview_scopes)
    manual_units, manual_scopes = _family_units(
        relevant, source, statuses, tokenizer, max_tokens, result, contexts
    )
    output.extend(manual_units)
    result.update(manual_scopes)
    from index.manual_evidence import compile_manual_evidence

    reviewed_manuals, reviewed_scopes = compile_manual_evidence(
        relevant, source, tokenizer, max_tokens, restricted_contexts=contexts
    )
    output.extend(reviewed_manuals)
    result.update(reviewed_scopes)
    from index.warranty import compile_procedures, compile_terms

    procedures, procedure_scopes = compile_procedures(
        relevant,
        output,
        result,
        source,
        tokenizer,
        max_tokens,
        restricted_contexts=contexts,
    )
    output.extend(procedures)
    result.update(procedure_scopes)
    terms, term_scopes = compile_terms(
        relevant,
        procedures,
        procedure_scopes,
        tokenizer,
        max_tokens,
        restricted_contexts=contexts,
    )
    output.extend(terms)
    result.update(term_scopes)
    certificates, certificate_scopes = compile_certificate_subjects(
        relevant, source, tokenizer, max_tokens, contexts
    )
    output.extend(certificates)
    result.update(certificate_scopes)
    fragments, fragment_scopes = compile_certificate_fragments(
        relevant, source, result, tokenizer, max_tokens
    )
    output.extend(fragments)
    result.update(fragment_scopes)
    for scope in result.values():
        scope["model_identity_revision"] = source.model_identity_revision
    return output, result
