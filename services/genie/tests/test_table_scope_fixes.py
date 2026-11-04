"""The #900 root causes: single-model tables, poisoned axes, shifted headers.

Every test names the production document whose failure mode it reproduces
(#900 report §4): GW ESA 261kWh EN/DE, BAT-C DS DE, SAJ HS3 DE, SEC3000C EN.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from test_chunking import Words
from test_publication import authority
from test_publication_columns import ESA, HCA, chunks, manifest

from index.chunking import Chunk
from index.extract import (
    _header_cell_spans,
    _recover_shifted_header_spans,
)
from index.publication import _table_columns, scope_proofs
from index.table_compiler import _author_contexts, compile_scopes
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import (
    author_scope_allows,
    authorize_chunk,
    table_header,
)
from linker_genie.source_models import family_labels, model_pattern, model_shapes
from linker_genie.source_roles import pack_model_row
from linker_genie.table_projection import SourceCell, SourceSpan

WORDS = Words()


def compile_all(selected: list[Chunk]) -> tuple[list[Chunk], dict[str, Any]]:
    raw = manifest()
    return compile_scopes(selected, raw, authority(raw), WORDS, 120)


def table_units(sha: str, output: list[Chunk], scopes: dict[str, Any]) -> list[Chunk]:
    return [
        chunk
        for chunk in output
        if chunk.kind == "table"
        and chunk.doc_sha256 == sha
        and chunk.id in scopes
        and scopes[chunk.id].get("basis")
        in {"table_single_model", "table_projection", "table_columns"}
    ]


def test_gw_esa_261_en_single_product_table_gets_its_own_projection() -> None:
    """#900 §4.1: a one-model 'property | value' table had no authorization path."""
    selected = chunks(ESA)
    output, scopes = compile_all(selected)
    units = table_units(ESA, output, scopes)
    assert units
    for unit in units:
        assert scopes[unit.id]["basis"] == "table_single_model"
        assert scopes[unit.id]["product_ids"] == [6321]
        assert unit.header.startswith("GW125/261-ESA-LCN-G10 | p. ")
        assert unit.text.startswith("| Battery Data | GW125/261-ESA-LCN-G10 |")


def test_gw_esa_261_single_model_proof_survives_the_runtime_validator() -> None:
    """The stored proof re-derives everything from cells at serving time."""
    selected = chunks(ESA)
    output, scopes = compile_all(selected)
    unit = next(iter(table_units(ESA, output, scopes)))
    proof = scopes[unit.id]
    raw = manifest()
    snapshot = Snapshot.read(raw)
    supported = authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=unit.id,
        text=unit.text,
    )
    assert [item["product_id"] for item in supported] == [6321]
    assert (
        authorize_chunk(
            unit.doc_sha256,
            proof["product_ids"],
            proof["associations"],
            proof,
            products=snapshot.products,
            documents=snapshot.documents,
            chunk_id=unit.id,
            text=unit.text + "\n| Forged | 1 |",
        )
        == []
    )


def test_sec3000c_style_declaration_without_technical_data_heading() -> None:
    """#900 §4.6: the declaration is the reading-order chain, not a heading."""
    selected = chunks(ESA)
    output, scopes = compile_all(selected)
    unit = next(iter(table_units(ESA, output, scopes)))
    declaration = scopes[unit.id]["single_model_projection"]["declaration"]
    assert declaration["chunk_id"] in scopes[unit.id]["source_chunk_ids"]
    assert "GW125/261-ESA-LCN-G10" in declaration["text"]


def test_not_yet_published_generation_denies_only_itself() -> None:
    """#900 §4.1: the unpublished G11 must not poison the published G10 axis."""
    selected = chunks(HCA)
    tables = [c for c in selected if c.kind == "table" and c.source_table]
    first = tables[0]
    anchor = next(
        cid
        for cid in first.preceding_text
        if "GW7K-HCA-20" in next(c.text for c in selected if c.id == cid)
    )
    poisoned = [
        replace(
            chunk,
            text=chunk.text + "\nGW125/261-ESA-LCN-G11"
            if chunk.id == anchor
            else chunk.text,
        )
        for chunk in selected
    ]
    scopes = scope_proofs(poisoned, manifest(), authority(manifest()))
    assert any(
        c.id in scopes and scopes[c.id].get("basis") == "table_columns"
        for c in poisoned
        if c.kind == "table"
    )


def test_german_pack_row_matches_and_stays_a_single_native_line() -> None:
    """#900 §4.3: 'Batteriepack-Typ / Modell' is the authored component row."""
    assert pack_model_row(
        "| Batteriepack-Typ / Modell | Batteriepack-Typ / Modell | GW10.2-PACK-ACI-G10 |"
    )
    assert pack_model_row("| Pack-Typ / Modell | | GW10.2-PACK-ACI-G10 |")
    assert pack_model_row("| Pack Type / model | | GW10.2-PACK-ACI-G10 |")
    assert not pack_model_row(
        "| Batteriepack-Typ / Modell Datenblatt | | GW10.2-PACK-ACI-G10 |"
    )
    assert not pack_model_row("Batteriepack-Typ / Modell")
    assert not pack_model_row(
        "| Zellentyp | Zellentyp | LFP (LiFePO4) |\n"
        "| Batteriepack-Typ / Modell | Batteriepack-Typ / Modell | GW10.2-PACK-ACI-G10 |"
    )


def _batc_chunks() -> list[Chunk]:
    """BAT-C DS DE shape: one blocked 3-line fragment plus a clean one."""
    header = Chunk(
        id="batc-text",
        doc_sha256="2a76fb0815a2",
        page=2,
        section="Technische Daten",
        kind="text",
        header="",
        text="Technische Daten\nGW61.4-BAT-AC-G10\nGW112.6-BAT-AC-G10",
        lang="de",
        tokens=8,
    )
    blocked = Chunk(
        id="batc-blocked",
        doc_sha256="2a76fb0815a2",
        page=2,
        section="Technische Daten",
        kind="table",
        header="",
        text="\n".join(
            [
                "| Batteriesystem | Batteriesystem | Batteriesystem |",
                "| Zelltyp | Zelltyp | LFP (LiFePO4) |",
                "| Batteriepack-Typ / Modell | Batteriepack-Typ / Modell | GW10.2-PACK-ACI-G10 |",
            ]
        ),
        lang="de",
        tokens=20,
        source_table="docling:p2:#/tables/0",
        preceding_text=("batc-text",),
        source_rows=(0, 1, 2),
    )
    kept = Chunk(
        id="batc-kept",
        doc_sha256="2a76fb0815a2",
        page=2,
        section="Technische Daten",
        kind="table",
        header="",
        text="| Nennleistung (kWh) | 61.4 | 112.6 |\n| Nutzbare Energie (kWh) | 60 | 110 |",
        lang="de",
        tokens=16,
        source_table="docling:p2:#/tables/0",
        preceding_text=("batc-text",),
        source_rows=(3, 4),
    )
    return [header, blocked, kept]


def _batc_call(selected: list[Chunk]) -> tuple[dict[str, Any], set[str]]:
    models = {1954: "GW61.4-BAT-AC-G10", 1955: "GW112.6-BAT-AC-G10"}
    labels = {model.casefold() for model in models.values()}
    statuses = {label: "published" for label in labels}
    return _table_columns(
        selected,
        models,
        {label: model_pattern(label) for label in labels},
        statuses,
        model_shapes(labels),
        {
            "batc-text": (set(), False),
            "batc-blocked": (set(), True),
            "batc-kept": (set(), False),
        },
        family_labels(labels),
    )


def test_german_pack_row_inside_a_fragment_is_isolated_per_source_row() -> None:
    """#900 §4.3: isolation by row, not by the chunker's single-line split."""
    columns, conflicts = _batc_call(_batc_chunks())
    assert not conflicts
    assert "batc-kept" in columns
    own = columns["batc-kept"]
    assert own["product_ids"] == [1954, 1955]
    (anchor,) = own["excluded_role_rows"]
    assert anchor["source_chunk_id"] == "batc-blocked"
    assert anchor["source_rows"] == [2]
    assert anchor["quote"] == (
        "| Batteriepack-Typ / Modell | Batteriepack-Typ / Modell |"
        " GW10.2-PACK-ACI-G10 |"
    )
    kept = next(c for c in _batc_chunks() if c.id == "batc-kept")
    products = {
        1954: {"model": "GW61.4-BAT-AC-G10"},
        1955: {"model": "GW112.6-BAT-AC-G10"},
    }
    scope = {"table_columns": own, "source_chunk_ids": ["batc-text", "batc-kept"]}
    assert table_header(scope, [1954, 1955], products, chunk_id="batc-kept", text=kept.text)


def test_non_pack_unknown_row_still_refuses_the_whole_table() -> None:
    selected = _batc_chunks()
    poisoned = replace(
        selected[1],
        text=selected[1].text + "\n| Fremdmodell | GW99.99-XX-G99 | GW99.99-XX-G99 |",
        source_rows=(*selected[1].source_rows, 3),
    )
    columns, conflicts = _batc_call([selected[0], poisoned, selected[2]])
    assert "batc-kept" not in columns
    assert {"batc-kept", "batc-blocked"} <= conflicts


def test_saj_header_cell_recovers_from_the_sibling_ink_band() -> None:
    """#900 §4.5: the shifted c5 box misses its own ink by 4.6 pt."""

    def span(text: str, x: float, y0: float, y1: float, index: int) -> SourceSpan:
        return SourceSpan(
            text=text,
            bbox=(x, y0, x + 60.0, y1),
            char_start=index,
            char_end=index + len(text),
            page=2,
            source_sha256="e0" * 32,
            page_size=(600.0, 800.0),
        )

    def cell(col: int, text: str, y0: float, y1: float) -> SourceCell:
        return SourceCell(
            row_start=0,
            row_end=1,
            col_start=col,
            col_end=col + 1,
            column_header=True,
            row_header=False,
            row_section=False,
            text=text,
            bbox=(100.0 + (col - 1) * 100.0, y0, 200.0 + (col - 1) * 100.0, y1),
            bbox_origin="TOPLEFT",
        )

    cells = [
        cell(1, "HS3-5-12K-T2-W/G-P1", 27.7, 65.5),
        cell(2, "HS3-5-12K-T2-W/G-P2", 27.7, 78.4),
        # SAJ HS3 DE p.2: the sixth cell's Docling box starts below its ink.
        cell(5, "HS3-5-12K-T2-W/G-P5", 32.6, 89.7),
    ]
    spans = [
        span("HS3-5-12K-T2-W/G-P1", 110.0, 27.4, 32.0, 0),
        span("HS3-5-12K-T2-W/G-P2", 210.0, 27.4, 32.0, 20),
        span("HS3-5-12K-T2-W/G-P5", 510.0, 27.4, 32.0, 40),
    ]
    matches = {0: _header_cell_spans(cells[0], spans), 1: _header_cell_spans(cells[1], spans)}
    assert _header_cell_spans(cells[2], spans) == []
    corrections = _recover_shifted_header_spans(cells, {**matches, 2: []}, spans)
    assert corrections[2] == (500.0, 27.4, 600.0, 89.7)
    assert matches[0] and matches[1]


def test_author_scope_empty_restrictions_allow_but_boundaries_still_bind() -> None:
    """#900 §5.1: an empty restriction list is no restriction at all."""
    products = {6326: {"model": "GW125/261-ESA-LCN-G10"}}
    assert author_scope_allows({"author_restrictions": []}, {6326}, products)
    assert not author_scope_allows({"author_restrictions": "x"}, {6326}, products)
    # A capacity cover still binds ordinary passages (empty subject set vetoes);
    # only a physically proven table axis supersedes it, at compile time.
    cover = {
        "kind": "heading",
        "quote": "ESA Series 125kW/261kWh",
        "source_chunk_id": "h1",
        "rating_cover": True,
    }
    assert not author_scope_allows(
        {"author_restrictions": [cover], "source_chunk_ids": ["h1"]}, {6326}, products
    )
    naming = {
        "kind": "heading",
        "quote": "GW125/261-ESA-LCN-G10 only",
        "source_chunk_id": "h1",
    }
    assert author_scope_allows(
        {"author_restrictions": [naming], "source_chunk_ids": ["h1"]}, {6326}, products
    )


def _contexts_snapshot() -> Snapshot:
    return Snapshot.read(
        {
            "schema_version": 1,
            "source_revision": "fixture",
            "products": [
                {
                    "product_id": 6321,
                    "product_revision": "r1",
                    "model": "GW125/261-ESA-LCN-G10",
                }
            ],
            "documents": [
                {
                    "document_id": "d1",
                    "document_revision": "r1",
                    "blob_sha256": "a" * 64,
                    "url": "https://site.test/a.pdf",
                    "title": "manual",
                    "type": "manual",
                    "lang": "en",
                    "product_ids": [6321],
                }
            ],
        }
    )


def _heading_chunk(heading: str, page: int = 94) -> Chunk:
    return Chunk(
        id=f"heading-{page}",
        doc_sha256="a" * 64,
        page=page,
        section=heading,
        kind="text",
        header="",
        text="body",
        lang="en",
        tokens=1,
        source_headings=(heading,),
    )


def test_capacity_heading_on_any_page_is_a_rating_cover() -> None:
    statuses = {"gw125/261-esa-lcn-g10": "published"}
    contexts = _author_contexts([_heading_chunk("ESA Series 125kW/261kWh")], _contexts_snapshot(), statuses)
    (boundary,) = next(iter(contexts.values()))
    assert boundary["rating_cover"] is True


def test_accessory_heading_is_no_restriction_but_real_codes_stay_closed() -> None:
    statuses = {"gw125/261-esa-lcn-g10": "published"}
    snapshot = _contexts_snapshot()
    accessory = _author_contexts(
        [_heading_chunk("WiFi/LAN Kit-20 ·", page=311)], snapshot, statuses
    )
    assert not accessory
    # A fused unknown code (the real meter model 'DTSU666' seen with no known
    # shape) and an unrecognized generation keep their fail-closed boundary.
    meter = _author_contexts([_heading_chunk("DTSU666")], snapshot, {})
    assert meter
    fail_closed = _author_contexts(
        [_heading_chunk("GW125/261-ESA-LCN-G12 Series")], snapshot, statuses
    )
    (boundary,) = next(iter(fail_closed.values()))
    assert "rating_cover" not in boundary
