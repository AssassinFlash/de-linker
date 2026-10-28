"""Model columns detached from a native table require original geometry."""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest
from docling_core.types.doc.document import DoclingDocument
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Page, enrich_model_axes, pages_of
from index.publication import ScopeProof, compile_publication
from linker_genie.figures import tag
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.table_projection import (
    cells_digest,
    projection_id,
    render_projection,
    unqualified_table_columns,
)

FIXTURES = Path(__file__).parent / "fixtures" / "external-model-axis"
SHA = "710d6f3d82664613f56bb72fd5898b5a1f9e5f7315cfc870a48822b1f3729e08"
ETR_SHA = "76df70ea8474531fb1f1d168b6faf3262cf2242358be9ba9d17b5f2fb5e75afd"
ETR_DE_SHA = "8ced72d8cec02f6b69f82f42097c8a206ed3a5bf298b52178849f74292090b81"
ESA_DE_SHA = "ce3e2552a6a21ff8b78988006f344619776c7cf01796cf172338040119569f9a"


def source() -> tuple[dict[str, Any], list[Chunk]]:
    """Replay the complete original Docling parse and SHA-named hosted PDF."""
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    document = DoclingDocument.model_validate_json(
        gzip.decompress((FIXTURES / f"{SHA}.json.gz").read_bytes())
    )
    pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
    pages = enrich_model_axes(pages, FIXTURES / f"{SHA}.pdf")
    meta = DocumentMeta(
        SHA,
        manifest["documents"][0]["title"],
        "",
        ("GoodWe",),
        ("GW208.9-BAT-LCD-G10",),
        "datasheet",
        "en",
    )
    return manifest, chunk_document(meta, pages, Words(), lambda _: "en")


def etr_source(lang: Literal["en", "de"] = "en") -> tuple[dict[str, Any], list[Chunk]]:
    sha = ETR_DE_SHA if lang == "de" else ETR_SHA
    manifest_file = "etr-de-manifest.json" if lang == "de" else "etr-manifest.json"
    manifest = json.loads((FIXTURES / manifest_file).read_text())
    document = DoclingDocument.model_validate_json(
        gzip.decompress((FIXTURES / f"{sha}.json.gz").read_bytes())
    )
    pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
    pages = enrich_model_axes(pages, FIXTURES / f"{sha}.pdf")
    meta = DocumentMeta(
        sha,
        manifest["documents"][0]["title"],
        "",
        ("GoodWe",),
        tuple(p["model"] for p in manifest["products"]),
        "datasheet",
        lang,
    )
    return manifest, chunk_document(meta, pages, Words(), lambda _: lang)


def esa_de_source() -> tuple[dict[str, Any], list[Chunk]]:
    manifest = json.loads((FIXTURES / "esa-de-manifest.json").read_text())
    document = DoclingDocument.model_validate_json(
        gzip.decompress((FIXTURES / f"{ESA_DE_SHA}.json.gz").read_bytes())
    )
    pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
    pages = enrich_model_axes(pages, FIXTURES / f"{ESA_DE_SHA}.pdf")
    meta = DocumentMeta(
        ESA_DE_SHA,
        manifest["documents"][0]["title"],
        "",
        ("GoodWe",),
        tuple(p["model"] for p in manifest["products"]),
        "datasheet",
        "de",
    )
    return manifest, chunk_document(meta, pages, Words(), lambda _: "de")


def selected(
    manifest: dict[str, Any], chunks: list[Chunk]
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    return compile_publication(chunks, manifest, authority(manifest), Words())


def test_original_external_axis_projects_only_the_linked_model_column() -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    target = [
        chunk
        for chunk in compiled
        if (chunk.id in proofs and proofs[chunk.id]["basis"] == "table_projection")
        and proofs[chunk.id]["product_ids"] == [1957]
    ]
    text = "\n".join(chunk.text for chunk in target)
    assert "| Rated Energy (kWh) | 208.9 |" in text
    assert "| Operating Voltage Range (System) (V) | 700 ~ 1000 |" in text
    assert "| Max. Input / Output Power (kW) | 125.3 / 125.3 |" in text
    assert "596.96 ~ 750.88" not in text and "746.2 ~ 1000" not in text
    assert "| Rated Energy (kWh) | 261.2 |" not in text
    assert all(proof["product_ids"] != [1956] for proof in proofs.values())
    assert all(proof["product_ids"] != [1958] for proof in proofs.values())


@pytest.mark.parametrize(
    "sha,record_file",
    [
        (SHA, "source.json"),
        (ETR_SHA, "etr-source.json"),
        (ETR_DE_SHA, "etr-de-source.json"),
        (ESA_DE_SHA, "esa-de-source.json"),
    ],
)
def test_fixture_is_original_pdf_and_complete_cached_docling(
    sha: str, record_file: str
) -> None:
    record = json.loads((FIXTURES / record_file).read_text())
    raw = gzip.decompress((FIXTURES / f"{sha}.json.gz").read_bytes())
    assert hashlib.sha256((FIXTURES / f"{sha}.pdf").read_bytes()).hexdigest() == sha
    assert hashlib.sha256(raw).hexdigest() == record["docling_sha256"]


def test_wrapped_multiblock_axis_projects_all_six_original_model_columns() -> None:
    manifest, original = etr_source()
    compiled, proofs = selected(manifest, original)
    for pid, expected in [
        (6507, "80.0"),
        (6508, "99.99"),
        (6509, "100"),
        (6510, "110.0"),
        (6511, "124.99"),
        (3595, "125.0"),
    ]:
        text = "\n".join(
            chunk.text
            for chunk in compiled
            if (chunk.id in proofs and proofs[chunk.id]["basis"] == "table_projection")
            and proofs[chunk.id]["product_ids"] == [pid]
        )
        assert f"| Rated Power (kW) | {expected} |" in text
        assert "| Nominal Voltage (V) | 750 |" in text
        assert "*6: Battery-side parameters are only applicable" in text
        assert all(
            f"| Rated Power (kW) | {other} |" not in text
            for other in {"80.0", "99.99", "100", "110.0", "124.99", "125.0"}
            - {expected}
        )


def test_offset_property_columns_project_four_original_battery_models() -> None:
    manifest, original = esa_de_source()
    compiled, proofs = selected(manifest, original)
    for pid, expected in [(6519, "5.12"), (6520, "8.32"), (3611, "6.0"), (3612, "9.0")]:
        text = "\n".join(
            chunk.text
            for chunk in compiled
            if (chunk.id in proofs and proofs[chunk.id]["basis"] == "table_projection")
            and proofs[chunk.id]["product_ids"] == [pid]
            and chunk.page == 3
        )
        assert f"| Nenn-Energie (kWh) | {expected} |" in text
        assert all(
            f"| Nenn-Energie (kWh) | {other} |" not in text
            for other in {"5.12", "8.32", "6.0", "9.0"} - {expected}
        )


def test_battery_power_keeps_its_own_page_footnote_when_numbers_repeat() -> None:
    manifest, original = esa_de_source()
    compiled, proofs = selected(manifest, original)
    text = "\n".join(
        chunk.text
        for chunk in compiled
        if chunk.id in proofs
        and proofs[chunk.id]["basis"] == "table_projection"
        and proofs[chunk.id]["product_ids"] == [6519]
        and chunk.page == 3
    )
    assert "| Max. Eingangsleistung (System) (kW) *3 | 5.0 |" in text
    assert (
        "*3: Eine Leistungsreduzierung (Derating) der Max. Eingangsleistung / "
        "Max. Ausgangsleistung / Spitzen-Ausgangsleistung erfolgt in Abhängigkeit "
        "von Temperatur und SOC. (p. 3)"
    ) in text
    assert "*3: Gemäß den lokalen Netzvorschriften." not in text


@pytest.mark.parametrize("model", ["GW6.0-BAT-D-G20", "ZZ77-X1"])
def test_offset_axis_cannot_override_a_model_in_the_native_first_row(
    model: str,
) -> None:
    manifest, original = esa_de_source()
    table = next(c for c in original if c.page == 3 and c.source_cells)
    cells = deepcopy(table.source_cells)
    value = next(
        cell for cell in cells if cell["row_start"] == 0 and cell["col_start"] == 2
    )
    value["text"] = model
    changed = [
        replace(c, source_cells=cells) if c.id == table.id else c for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    assert not any(
        c.page == 3 and (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        for c in compiled
    )


def test_offset_axis_rejects_swapped_native_cell_positions() -> None:
    manifest, original = esa_de_source()
    table = next(c for c in original if c.page == 3 and c.source_cells)
    cells = deepcopy(table.source_cells)
    one, two = [
        cell for cell in cells if cell["row_start"] == 1 and cell["col_start"] in (2, 3)
    ]
    one["col_start"], two["col_start"] = two["col_start"], one["col_start"]
    one["col_end"], two["col_end"] = two["col_end"], one["col_end"]
    changed = [
        replace(c, source_cells=cells) if c.id == table.id else c for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    assert not any(
        "| Nenn-Energie (kWh) | 8.32 |" in c.text
        and (c.id in proofs and proofs[c.id]["product_ids"] == [6519])
        for c in compiled
    )


@pytest.mark.parametrize(
    "narrow_title",
    ["Only GW10K-ETA-G20", "Only 5-30kW/5-108kWh All-in-One models"],
)
def test_physical_axis_never_bypasses_an_explicit_cover_restriction(
    narrow_title: str,
) -> None:
    manifest, original = esa_de_source()
    title = next(
        c for c in original if any("All-in-One" in h for h in c.source_headings)
    )
    headings = tuple(
        narrow_title if "All-in-One" in heading else heading
        for heading in title.source_headings
    )
    changed = [
        replace(c, source_headings=headings, section=narrow_title)
        if c.id == title.id
        else c
        for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    assert not any(
        c.page == 3 and (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        for c in compiled
    )


def test_unproven_section_boundary_does_not_inherit_the_previous_context() -> None:
    manifest, original = etr_source()
    table = next(c for c in original if c.page == 2 and c.source_cells)
    cells = deepcopy(table.source_cells)
    axis = next(cell["external_axis"] for cell in cells if "external_axis" in cell)
    assert 18 in axis["section_rows"] and 18 in axis["section_barriers"]
    axis["section_rows"].remove(18)
    changed = [
        replace(c, source_cells=cells) if c.id == table.id else c for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    target = "\n".join(
        c.text
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        and proofs[c.id]["product_ids"] == [6507]
    )
    assert "| Max. Input Power (kW) | 160 |" in target
    assert "| Rated Power (kW) | 80.0 |" not in target


def test_battery_section_keeps_the_original_footnote_and_its_source_page() -> None:
    manifest, original = etr_source()
    compiled, proofs = selected(manifest, original)
    text = "\n".join(
        c.text
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        and proofs[c.id]["product_ids"] == [6507]
    )
    assert "| Max. Continuous Charging / Discharging Current (A) | 125.7 |" in text
    assert (
        "*6: Battery-side parameters are only applicable with proprietary battery systems "
        "or DC/DC-supported battery interface. (p. 3)"
    ) in text
    assert "| Nominal Voltage (V) | 750 |" in text


def test_merged_value_at_a_single_model_position_is_not_shared() -> None:
    manifest, original = etr_source()
    table = next(c for c in original if c.page == 2 and c.source_cells)
    cells = deepcopy(table.source_cells)
    axis = next(cell["external_axis"] for cell in cells if "external_axis" in cell)
    value = next(
        cell for cell in cells if cell["row_start"] == 2 and cell["text"] == "750"
    )
    first_box = axis["model_spans"][0]["bbox"]
    centre = (first_box[0] + first_box[2]) / 2
    box = value["bbox"]
    assert box is not None
    value["bbox"] = (centre - 5, box[1], centre + 5, box[3])
    changed = [
        replace(c, source_cells=cells) if c.id == table.id else c for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    text = "\n".join(
        c.text
        for c in compiled
        if c.id in proofs
        and proofs[c.id]["basis"] == "table_projection"
        and proofs[c.id]["product_ids"] == [6507]
    )
    assert "| Nominal Voltage (V) | 750 |" not in text
    assert "| Max. Continuous Charging / Discharging Current (A) | 125.7 |" in text


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "wrong_page", "changed_quote"]
)
def test_unproven_footnote_cannot_release_its_section(change: str) -> None:
    manifest, original = etr_source()
    table = next(c for c in original if c.page == 2 and c.source_cells)
    cells = deepcopy(table.source_cells)
    axis = next(cell["external_axis"] for cell in cells if "external_axis" in cell)
    note = next(note for note in axis["footnotes"] if note["text"].startswith("*6:"))
    if change == "missing":
        axis["footnotes"].remove(note)
    elif change == "duplicate":
        axis["footnotes"].append(deepcopy(note))
    elif change == "wrong_page":
        note["pdf_span"]["page"] = 2
    else:
        note["text"] += " Changed."
    changed = [
        replace(c, source_cells=cells) if c.id == table.id else c for c in original
    ]
    compiled, proofs = selected(manifest, changed)
    target = "\n".join(
        c.text
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        and proofs[c.id]["product_ids"] == [6507]
    )
    assert (
        "| Max. Continuous Charging / Discharging Current (A) | 125.7 |" not in target
    )
    if change in {"missing", "wrong_page"}:
        assert "| Rated Power (kW) | 80.0 |" in target


def test_each_physical_column_is_distinct_when_its_own_link_is_current() -> None:
    manifest, original = source()
    # A test-only publication change exercises all three original columns. The
    # captured Woo association itself grants only 1957; it remains untouched.
    manifest = deepcopy(manifest)
    document = manifest["documents"][0]
    document["product_ids"] = [1956, 1957, 1958]
    for product in manifest["products"]:
        product["documents"] = [document["document_id"]]
    compiled, proofs = selected(manifest, original)
    for pid, expected in [
        (1956, "596.96 ~ 750.88"),
        (1957, "700 ~ 1000"),
        (1958, "746.2 ~ 1000"),
    ]:
        target = [
            chunk
            for chunk in compiled
            if (chunk.id in proofs and proofs[chunk.id]["basis"] == "table_projection")
            and proofs[chunk.id]["product_ids"] == [pid]
        ]
        text = "\n".join(chunk.text for chunk in target)
        assert f"| Operating Voltage Range (System) (V) | {expected} |" in text
        assert all(
            other not in text
            for other in {"596.96 ~ 750.88", "700 ~ 1000", "746.2 ~ 1000"} - {expected}
        )
        # Native shared cells and footnoted rows remain unproved.
        assert "| Battery Type |" not in text
        assert "Max.Charging / Discharging Current (A) *1" not in text


@pytest.mark.parametrize(
    "change",
    [
        "no_spans",
        "wrong_page",
        "wrong_sha",
        "wrong_source_box",
        "table_above_header",
        "missing_native_characters",
        "missing_column",
        "source_not_adjacent",
    ],
)
def test_external_header_without_full_original_evidence_is_rejected(
    change: str,
) -> None:
    manifest, original = source()
    table = next(chunk for chunk in original if chunk.source_cells)
    cells = deepcopy(table.source_cells)
    axis = next(cell["external_axis"] for cell in cells if "external_axis" in cell)
    if change == "no_spans":
        axis["model_spans"] = []
    elif change == "wrong_page":
        for span in axis["model_spans"]:
            span["page"] += 1
    elif change == "wrong_sha":
        for span in axis["model_spans"]:
            span["source_sha256"] = "0" * 64
    elif change == "wrong_source_box":
        axis["source_spans"][-1]["bbox"] = (10.0, 10.0, 20.0, 20.0)
    elif change == "table_above_header":
        box = axis["table_bbox"]
        axis["table_bbox"] = (box[0], 1.0, box[2], box[3])
    elif change == "missing_native_characters":
        axis["source_spans"][-1]["char_end"] -= 1
    elif change == "missing_column":
        axis["model_spans"].pop()
    else:
        table = replace(table, preceding_text=())
    changed = [
        replace(table, source_cells=cells) if c.id == table.id else c for c in original
    ]
    _, proofs = selected(manifest, changed)
    assert not any(p["basis"] == "table_projection" for p in proofs.values())


def test_reordered_native_values_and_changed_proof_are_denied() -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    chunk = next(
        c
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
    )
    proof = deepcopy(proofs[chunk.id])
    projection = proof["table_projection"]
    cells = projection["source_cells"]
    label = next(
        c for c in cells if c["text"] == "Operating Voltage Range (System) (V)"
    )
    one, two = [
        c
        for c in cells
        if c["row_start"] == label["row_start"] and c["col_start"] in (1, 2)
    ]
    one["col_start"], two["col_start"] = two["col_start"], one["col_start"]
    one["col_end"], two["col_end"] = two["col_end"], one["col_end"]
    wrong = chunk.text.replace("700 ~ 1000", "596.96 ~ 750.88")
    projection["source_cells_sha256"] = cells_digest(cells)
    projection["text_sha256"] = hashlib.sha256(wrong.encode()).hexdigest()
    cid = projection_id(
        SHA, chunk.page, projection["source_table"], projection["model"], wrong
    )
    assert not authorize_chunk(
        SHA,
        [1957],
        proof["associations"],
        proof,
        products=Snapshot.read(manifest).products,
        chunk_id=cid,
        text=wrong,
    )


def write_index(
    tmp_path: Path,
    manifest: dict[str, Any],
    compiled: list[Chunk],
    proofs: dict[str, ScopeProof],
) -> Path:
    document = manifest["documents"][0]
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "external-axis-fixture",
            None,
            None,
            "original Docling and PDF text layer",
            512,
            publication={
                "manifest": manifest,
                "chunk_products": {cid: p["product_ids"] for cid, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                document["blob_sha256"],
                (document["url"],),
                document["title"],
                "",
                ("GoodWe",),
                (),
                "datasheet",
                str(document.get("lang", "en")).casefold(),
                max(c.page for c in compiled),
                "indexed",
            )
        ],
        [(p["product_id"], p["model"]) for p in manifest["products"]],
        compiled,
    )
    target = tmp_path / "index.sqlite"
    store.export(directory, target)
    return target


def forged_axis(
    chunk: Chunk, original_proof: ScopeProof
) -> tuple[str, str, ScopeProof]:
    """Recompute every derived field after swapping the physical model labels."""
    proof = deepcopy(original_proof)
    projection = proof["table_projection"]
    cells = projection["source_cells"]
    axis = next(cell["external_axis"] for cell in cells if "external_axis" in cell)
    first, second = axis["model_spans"][:2]
    first["bbox"], second["bbox"] = second["bbox"], first["bbox"]
    projection["model_column"] = 1
    projection["source_rows"] = [11]
    wrong = render_projection(cells, 1, [11])
    assert (
        wrong and "| Operating Voltage Range (System) (V) | 596.96 ~ 750.88 |" in wrong
    )
    projection["source_cells_sha256"] = cells_digest(cells)
    projection["text_sha256"] = hashlib.sha256(wrong.encode()).hexdigest()
    cid = projection_id(
        SHA, chunk.page, projection["source_table"], projection["model"], wrong
    )
    return cid, wrong, proof


@pytest.mark.parametrize("lang", ["en", "de"])
def test_original_column_reaches_sqlite_and_revokes(tmp_path: Path, lang: str) -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    target = write_index(tmp_path, manifest, compiled, proofs)
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Rated Energy", lang, [1957], publication=Snapshot.read(manifest)
        )
        hit = next(h for h in hits if "| Rated Energy (kWh) | 208.9 |" in h.text)
        assert hit.product_ids == (1957,) and hit.page == 2
        assert "208.9 kWh" in tag(hit.chunk_id, hit.text).figures.values()
        assert all("746.2 ~ 1000" not in h.text for h in hits)
        revoked = deepcopy(manifest)
        revoked["documents"][0]["product_ids"] = []
        next(p for p in revoked["products"] if p["product_id"] == 1957)[
            "documents"
        ] = []
        assert not loaded.search(
            "Rated Energy", lang, [1957], publication=Snapshot.read(revoked)
        )
    finally:
        loaded.close()


def test_runtime_rejects_forged_external_coordinates_with_recalculated_hashes(
    tmp_path: Path,
) -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    chunk = next(
        c
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
    )
    target = write_index(tmp_path, manifest, compiled, proofs)
    cid, wrong, proof = forged_axis(chunk, proofs[chunk.id])
    with sqlite3.connect(target) as db:
        db.execute(
            "UPDATE chunks SET id = ?, text = ? WHERE id = ?", (cid, wrong, chunk.id)
        )
        db.execute(
            "UPDATE chunk_products SET chunk_id = ? WHERE chunk_id = ?", (cid, chunk.id)
        )
        db.execute(
            "UPDATE chunk_scopes SET chunk_id = ?, proof = ? WHERE chunk_id = ?",
            (cid, json.dumps(proof), chunk.id),
        )
        db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Operating Voltage Range", "en", [1957], publication=Snapshot.read(manifest)
        )
        assert not any("596.96 ~ 750.88" in h.text for h in hits)
    finally:
        loaded.close()


def test_store_does_not_prepare_a_forged_external_axis(tmp_path: Path) -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    chunk = next(
        c
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
    )
    cid, wrong, proof = forged_axis(chunk, proofs[chunk.id])
    compiled = [
        replace(c, id=cid, text=wrong) if c.id == chunk.id else c for c in compiled
    ]
    proofs = {key: value for key, value in proofs.items() if key != chunk.id}
    proofs[cid] = proof
    target = write_index(tmp_path, manifest, compiled, proofs)
    with sqlite3.connect(target) as db:
        raw = db.execute(
            "SELECT value FROM meta WHERE key = 'unprepared_documents'"
        ).fetchone()
    assert raw is not None
    diagnostics = json.loads(raw[0])
    assert any(
        item["product_id"] == 1957 and item["reason"] == "no_proven_passage"
        for item in diagnostics
    )


@pytest.mark.parametrize("lost", ["anchor", "table", "header"])
def test_runtime_requires_both_native_chunks_and_the_independent_anchor(
    tmp_path: Path, lost: str
) -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    target = write_index(tmp_path, manifest, compiled, proofs)
    table = next(chunk for chunk in original if chunk.source_cells)
    with sqlite3.connect(target) as db:
        if lost == "anchor":
            db.execute("DELETE FROM meta WHERE key = 'external_axis_anchors'")
        else:
            cid = table.id if lost == "table" else table.preceding_text[-1]
            db.execute("DELETE FROM chunks WHERE id = ?", (cid,))
            db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Rated Energy", "en", [1957], publication=Snapshot.read(manifest)
        )
        assert not any("| Rated Energy (kWh) | 208.9 |" in h.text for h in hits)
    finally:
        loaded.close()


def test_qualified_original_note_reaches_sqlite_and_is_bound_to_page_three(
    tmp_path: Path,
) -> None:
    manifest, original = etr_source()
    compiled, proofs = selected(manifest, original)
    target = write_index(tmp_path, manifest, compiled, proofs)
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Max Continuous Charging Discharging Current",
            "en",
            [6507],
            publication=Snapshot.read(manifest),
        )
        hit = next(
            h
            for h in hits
            if "| Max. Continuous Charging / Discharging Current (A) | 125.7 |"
            in h.text
        )
        assert hit.product_ids == (6507,) and hit.page == 2
        assert (
            "only applicable with proprietary battery systems or DC/DC-supported battery interface. (p. 3)"
            in hit.text
        )
        assert len(hit.qualifications) == 1
        assert hit.qualification_required
        condition = hit.qualifications[0]
        assert condition["lang"] == "en" and condition["page"] == 3
        assert condition["quote"].startswith("*6: Battery-side parameters")
        assert condition["chunk_id"] in proofs[hit.chunk_id]["source_chunk_ids"]
        assert "125.7 A" in tag(hit.chunk_id, hit.text).figures.values()
        assert "142.8" not in hit.text
    finally:
        loaded.close()


@pytest.mark.parametrize("change", ["remove", "alter"])
def test_losing_the_footnote_source_only_revokes_qualified_units(
    tmp_path: Path,
    change: str,
) -> None:
    manifest, original = etr_source()
    compiled, proofs = selected(manifest, original)
    target = write_index(tmp_path, manifest, compiled, proofs)
    qualified = next(
        c
        for c in compiled
        if (c.id in proofs and proofs[c.id]["basis"] == "table_projection")
        and "| Max. Continuous Charging / Discharging Current (A) | 125.7 |" in c.text
    )
    source = next(
        item
        for item in proofs[qualified.id]["table_projection"]["footnote_sources"]
        if item["quote"].startswith("*6:")
    )
    with sqlite3.connect(target) as db:
        if change == "remove":
            db.execute("DELETE FROM chunks WHERE id = ?", (source["chunk_id"],))
        else:
            db.execute(
                "UPDATE chunks SET text = ? WHERE id = ?",
                ("altered", source["chunk_id"]),
            )
        db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Rated Power", "en", [6507], publication=Snapshot.read(manifest)
        )
        assert any("| Rated Power (kW) | 80.0 |" in h.text for h in hits)
        assert all(
            "| Max. Continuous Charging / Discharging Current (A) | 125.7 |"
            not in h.text
            for h in hits
        )
    finally:
        loaded.close()


def test_cannot_downgrade_external_axis_to_forged_native_header(tmp_path: Path) -> None:
    manifest, original = source()
    compiled, proofs = selected(manifest, original)
    chunk = next(
        c
        for c in compiled
        if c.id in proofs and proofs[c.id]["basis"] == "table_projection"
    )
    proof = deepcopy(proofs[chunk.id])
    projection = proof["table_projection"]
    cells = projection["source_cells"]
    axis = next(cell.pop("external_axis") for cell in cells if "external_axis" in cell)
    spans = axis["model_spans"]
    spans[0]["bbox"], spans[1]["bbox"] = spans[1]["bbox"], spans[0]["bbox"]
    boxes = [span["bbox"] for span in spans]
    cells.append(
        {
            "row_start": 0,
            "row_end": 1,
            "col_start": 1,
            "col_end": 4,
            "text": " ".join(span["text"] for span in spans),
            "column_header": True,
            "row_header": False,
            "row_section": False,
            "bbox": (
                min(box[0] for box in boxes),
                min(box[1] for box in boxes),
                max(box[2] for box in boxes),
                max(box[3] for box in boxes),
            ),
            "bbox_origin": "TOPLEFT",
            "model_spans": spans,
        }
    )
    projection.pop("axis_source")
    projection.pop("footnote_sources", None)
    projection["model_column"] = 1
    projection["source_rows"] = [11]
    wrong = render_projection(cells, 1, [11])
    assert (
        wrong and "| Operating Voltage Range (System) (V) | 596.96 ~ 750.88 |" in wrong
    )
    projection["source_cells_sha256"] = cells_digest(cells)
    projection["text_sha256"] = hashlib.sha256(wrong.encode()).hexdigest()
    cid = projection_id(
        SHA, chunk.page, projection["source_table"], projection["model"], wrong
    )
    target = write_index(tmp_path, manifest, compiled, proofs)
    with sqlite3.connect(target) as db:
        db.execute(
            "UPDATE chunks SET id = ?, text = ? WHERE id = ?", (cid, wrong, chunk.id)
        )
        db.execute(
            "UPDATE chunk_products SET chunk_id = ? WHERE chunk_id = ?", (cid, chunk.id)
        )
        db.execute(
            "UPDATE chunk_scopes SET chunk_id = ?, proof = ? WHERE chunk_id = ?",
            (cid, json.dumps(proof), chunk.id),
        )
        db.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Operating Voltage Range", "en", [1957], publication=Snapshot.read(manifest)
        )
        assert all("596.96 ~ 750.88" not in hit.text for hit in hits)
    finally:
        loaded.close()


@pytest.mark.parametrize("provenance", ["legacy", "mixed", "unscoped"])
def test_old_column_sections_keep_their_condition_across_chunk_boundaries(
    provenance: str,
) -> None:
    sha = "a" * 64
    first = (
        "| Input | | |\n| Nominal Current (A) | 32 | 16 |\n| | 11 | 22 |\n"
        "| Safe Power (kW) | 20 | 30 |\n| Battery Side *6 | | |"
    )
    second = "| Nominal Voltage (V) | 400 | 400 |\n| Grid Side | | |\n| Rated Power (kW) | 80 | 100 |"

    def cid(text: str) -> str:
        digest = hashlib.sha256(f"table\0{text}".encode()).hexdigest()[:8]
        return f"{sha[:12]}-p2-{digest}"

    independent = (
        "| Grid Side | | |\n| Rated Power (kW) | 125 | 150 |\n"
        "| Dimension (W*D*H mm) | 950*1300*2480 | 950*1300*2480 |\n"
        "| Dimensions | 500*600*700*1 | 500*600*700*1 |\n"
        "| Working Temperature Range | -25-50* | -25-50* |\n"
        "| Ingress Protection Rating | IP66*2 | IP66*2 |"
    )
    chunks = [
        (sha, 2, "table", cid(text), text) for text in (first, second, independent)
    ]
    scopes: dict[str, dict[str, Any]] = {
        cid(first): {"basis": "passage"},
        cid(second): {"basis": "section"},
        cid(independent): {"basis": "passage"},
    }
    if provenance != "legacy":
        for name in (cid(first), cid(second)):
            scopes[name]["native_table"] = {
                "source_table": "first",
                "source_chunk_ids": [cid(first), cid(second)],
            }
        scopes[cid(independent)]["native_table"] = {
            "source_table": "second",
            "source_chunk_ids": [cid(independent)],
        }
        if provenance == "unscoped":
            del scopes[cid(first)]
    safe = unqualified_table_columns(chunks, scopes)
    assert "Nominal Current (A)" in safe[cid(first)]
    assert "Safe Power (kW)" in safe[cid(first)]
    assert "Battery Side *6" not in safe[cid(first)]
    assert "Nominal Voltage" not in safe[cid(second)]
    # Legacy whole-table fragments have no physical proof that "Grid Side"
    # is a real section rather than a parameter whose values were omitted.
    assert "Rated Power (kW)" not in safe[cid(second)]
    assert ("125 | 150" in safe[cid(independent)]) is (provenance != "legacy")
    assert ("950*1300*2480" in safe[cid(independent)]) is (provenance != "legacy")
    assert "500*600*700*1" not in safe[cid(independent)]
    assert "-25-50*" not in safe[cid(independent)]
    assert "IP66*2" not in safe[cid(independent)]


def test_note_in_value_only_continuation_revokes_prior_fragment_row() -> None:
    sha = "a" * 64
    first = "| Safe (A) | 1 | 2 |\n| Qualified (V) | 10 | 20 |"
    second = "| | *4 | *4 |\n| Unknown (W) | 30 | 40 |"

    def cid(text: str) -> str:
        digest = hashlib.sha256(f"table\0{text}".encode()).hexdigest()[:8]
        return f"{sha[:12]}-p2-{digest}"

    chunks = [(sha, 2, "table", cid(text), text) for text in (first, second)]
    safe = unqualified_table_columns(chunks, {})
    assert "Safe (A)" in safe[cid(first)]
    assert "Qualified (V)" not in safe[cid(first)]
    assert not safe[cid(second)]


def test_old_schema_native_projection_remains_retrievable(tmp_path: Path) -> None:
    from test_publication_compiler import H2_DE, compiled_index, manifest

    index = compiled_index(tmp_path, H2_DE[:12])
    index.close()
    with sqlite3.connect(tmp_path / "index.sqlite") as db:
        db.execute("UPDATE meta SET value = '2' WHERE key = 'schema_version'")
        db.execute("DELETE FROM meta WHERE key = 'external_axis_anchors'")
    loaded = DocumentIndex(tmp_path / "index.sqlite", encoder=None)
    try:
        hits = loaded.search(
            "Nennleistung AC", "de", [1179], publication=Snapshot.read(manifest())
        )
        assert any("| Nennleistung AC [W] | 25000 |" in hit.text for hit in hits)
    finally:
        loaded.close()
