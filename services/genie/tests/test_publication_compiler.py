"""Current-model answer units from original H2/HS2/HS3 Docling provenance."""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from docling_core.types.doc.document import DoclingDocument
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Block, Page, enrich_model_axes, pages_of
from index.inventory import doc_type_of
from index.publication import ScopeProof, compile_publication, scope_proofs
from linker_genie.figures import tag
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.table_projection import cells_digest, projection_id

FIXTURES = Path(__file__).parent / "fixtures" / "publication-compiler"
H2_DE = "be488dc6630cddc8381e38c61c6bc7b41c50c711042cdb2547170bd85e68a752"


def manifest() -> dict[str, Any]:
    value = json.loads(gzip.decompress((FIXTURES / "manifest.json.gz").read_bytes()))
    assert isinstance(value, dict)
    return value


def chunks(prefix: str) -> list[Chunk]:
    raw = manifest()
    doc = next(d for d in raw["documents"] if d["blob_sha256"].startswith(prefix))
    sha = doc["blob_sha256"]
    document = DoclingDocument.model_validate_json(
        gzip.decompress((FIXTURES / f"{sha}.json.gz").read_bytes())
    )
    pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
    pdf = FIXTURES / f"{sha}.pdf"
    if pdf.is_file():
        pages = enrich_model_axes(pages, pdf)
    else:
        physical = json.loads(
            gzip.decompress((FIXTURES / "physical-header-spans.json.gz").read_bytes())
        ).get(sha, [])
        for page in pages:
            for i, block in enumerate(page.blocks):
                cells = deepcopy(block.source_cells)
                for cell in cells:
                    for original in physical:
                        if (
                            original["page"] == page.number
                            and original["table"] == block.source_id
                            and original["row_start"] == cell["row_start"]
                            and original["col_start"] == cell["col_start"]
                            and original["text"] == cell["text"]
                        ):
                            cell["model_spans"] = original["model_spans"]
                page.blocks[i] = replace(block, source_cells=cells)
    return chunk_document(
        DocumentMeta(
            sha,
            doc["title"],
            "",
            (),
            tuple(
                p["model"]
                for p in raw["products"]
                if p["product_id"] in doc["product_ids"]
            ),
            "datasheet",
            "de" if prefix == H2_DE[:12] else "en",
        ),
        pages,
        Words(),
        lambda _: "en",
    )


def product_ids(scopes: dict[str, ScopeProof], cid: str) -> list[int]:
    proof = scopes.get(cid)
    return proof["product_ids"] if proof is not None else []


@pytest.mark.parametrize(
    "prefix,pid",
    [("be488dc6630c", 1179), ("0abea746ac33", 1182), ("b4a653fd2c0b", 1185)],
)
def test_actual_current_product_has_authored_applicable_technical_passage(
    prefix: str, pid: int
) -> None:
    raw = manifest()
    selected = chunks(prefix)
    selected, scopes = compile_publication(selected, raw, authority(raw), Words())
    assert any(
        c.kind == "table"
        and pid in product_ids(scopes, c.id)
        and any(word in c.text for word in ["Power", "Leistung", "Current", "Strom"])
        for c in selected
    )


def compiled_index(
    path: Path, prefix: str, original: list[Chunk] | None = None
) -> DocumentIndex:
    raw = manifest()
    selected, scopes = compile_publication(
        original if original is not None else chunks(prefix),
        raw,
        authority(raw),
        Words(),
    )
    document = next(d for d in raw["documents"] if d["blob_sha256"].startswith(prefix))
    source = path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "source-compiler",
            None,
            None,
            "original Docling",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
            },
        ),
        [
            DocumentRow(
                document["blob_sha256"],
                (document["url"],),
                document["title"],
                "",
                (),
                (),
                doc_type_of(str(document["type"]), str(document.get("role", ""))),
                "en",
                max(c.page for c in selected),
                "indexed",
            )
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        selected,
    )
    target = path / "index.sqlite"
    store.export(source, target)
    return DocumentIndex(target, encoder=None)


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("neighbours", [False, True])
def test_h2_exact_current_column_reaches_real_retrieval_and_figure_hydration(
    tmp_path: Path, lang: str, neighbours: bool
) -> None:
    loaded = compiled_index(tmp_path, H2_DE[:12])
    try:
        hits = loaded.search(
            "Nennleistung AC",
            lang,
            [1179],
            neighbours=neighbours,
            publication=Snapshot.read(manifest()),
        )
        target = next(h for h in hits if "| Nennleistung AC [W] | 25000 |" in h.text)
        assert target.product_ids == (1179,)
        assert target.page == 2
        assert "| Ausgangs-Nennstrom [A]@230 V AC | 36.3 |" in target.text
        assert "25000 W" in tag(target.chunk_id, target.text).figures.values()
        assert all("H2-30K-T3" not in hit.text for hit in hits)
        assert all(
            "| 33000 |" not in hit.text and "| 43.5 |" not in hit.text for hit in hits
        )
        # Logical offsets in the native parse incorrectly pair warranty10 with
        # Gewicht[kg]. Original bbox ambiguity must exclude that individual row.
        assert all("| Gewicht [kg] | 10 |" not in hit.text for hit in hits)
        assert all("| Garantie [Jahre] | EN" not in hit.text for hit in hits)
        assert all(
            "Nenn-Eingangsfrequenz [Hz] Max. Eingangsstrom" not in hit.text
            for hit in hits
        )
    finally:
        loaded.close()


def test_prior_current_model_restriction_survives_projection_store_and_runtime(
    tmp_path: Path,
) -> None:
    original = chunks(H2_DE[:12])
    table_at = next(i for i, c in enumerate(original) if c.source_cells)
    table = original[table_at]
    restriction = replace(
        table,
        id="authored-current-restriction",
        kind="text",
        section="H2-25K-T3 only",
        source_headings=("H2-25K-T3 only",),
        text="These technical data apply only to H2-25K-T3.",
        source_table="",
        source_cells=(),
        source_rows=(),
        preceding_text=(),
    )
    original.insert(table_at, restriction)
    loaded = compiled_index(tmp_path, H2_DE[:12], original)
    current = Snapshot.read(manifest())
    try:
        hits = loaded.search(
            "Nennleistung AC", "de", [1179], publication=current, neighbours=True
        )
        other = loaded.search(
            "Nennleistung AC", "de", [4107], publication=current, neighbours=True
        )
        with sqlite3.connect(tmp_path / "index.sqlite") as db:
            proofs = [
                json.loads(row[0])
                for row in db.execute("SELECT proof FROM chunk_scopes")
                if json.loads(row[0]).get("table_projection")
            ]
        target = next(h for h in hits if "| Nennleistung AC [W] | 25000 |" in h.text)
        assert target.product_ids == (1179,)
        assert not other
        assert proofs
        assert all(proof["product_ids"] == [1179] for proof in proofs)
        assert all(
            restriction.id in proof["source_chunk_ids"]
            and {
                c.id for c in original if c.source_table == table.source_table
            }.issubset(proof["source_chunk_ids"])
            for proof in proofs
        )
    finally:
        loaded.close()


@pytest.mark.parametrize(
    "change", ["draft", "relation", "revision", "same_sha_other_url"]
)
def test_current_column_is_revoked_without_waiting_for_an_index_rebuild(
    tmp_path: Path, change: str
) -> None:
    loaded = compiled_index(tmp_path, H2_DE[:12])
    current = manifest()
    if change == "draft":
        current["products"] = [
            p for p in current["products"] if p["product_id"] != 1179
        ]
    elif change == "revision":
        next(p for p in current["products"] if p["product_id"] == 1179)[
            "product_revision"
        ] += "changed"
    else:
        for document in current["documents"]:
            if document["blob_sha256"] == H2_DE:
                document["product_ids"] = [
                    pid for pid in document["product_ids"] if pid != 1179
                ]
        if change == "same_sha_other_url":
            clone = deepcopy(
                next(d for d in current["documents"] if d["blob_sha256"] == H2_DE)
            )
            clone.update(
                document_id="other-permission-domain",
                document_revision="other-version",
                url="https://site.test/not-the-grant.pdf",
                product_ids=[1179],
            )
            current["documents"].append(clone)
    current["documents"] = [d for d in current["documents"] if d["product_ids"]]
    try:
        assert not loaded.search(
            "Nennleistung", "en", [1179], publication=Snapshot.read(current)
        )
    finally:
        loaded.close()


def test_withdrawing_another_column_does_not_revoke_current_model_answer_unit(
    tmp_path: Path,
) -> None:
    loaded = compiled_index(tmp_path, H2_DE[:12])
    current = manifest()
    current["products"] = [p for p in current["products"] if p["product_id"] != 1181]
    for document in current["documents"]:
        document["product_ids"] = [
            pid for pid in document["product_ids"] if pid != 1181
        ]
    current["documents"] = [d for d in current["documents"] if d["product_ids"]]
    try:
        hits = loaded.search(
            "Nennleistung", "en", [1179], publication=Snapshot.read(current)
        )
        assert any("| Nennleistung AC [W] | 25000 |" in h.text for h in hits)
        assert all("H2-30K" not in h.text for h in hits)
    finally:
        loaded.close()


def test_compiler_keeps_originals_and_uses_ordered_merged_native_axis() -> None:
    original = chunks("0f0e75ad3f31")
    raw = manifest()
    selected, scopes = compile_publication(original, raw, authority(raw), Words(), 120)
    assert selected[: len(original)] == original
    assert all(c.tokens <= 120 for c in selected[len(original) :])
    model_to_pid = {p["model"]: p["product_id"] for p in raw["products"]}
    for model, value in [
        ("H2-10K-T3", "10000"),
        ("H2-12K-T3", "12000"),
        ("H2-25K-T3", "25000"),
    ]:
        matching = [
            c for c in selected if product_ids(scopes, c.id) == [model_to_pid[model]]
        ]
        assert any(f"| Rated AC Power [W] | {value} |" in c.text for c in matching)
        assert all(
            "H2-15K-T2" not in c.text and "H2-20K-T2" not in c.text for c in matching
        )
    # The merged original list's count must equal its physical colspan.
    native = next(c for c in original if c.source_cells)
    bad_cells = deepcopy(native.source_cells)
    axis = next(
        cell for cell in bad_cells if cell["row_start"] == 0 and cell["col_start"] == 1
    )
    axis["text"] += " Z999"
    bad = [
        replace(c, source_cells=bad_cells) if c.id == native.id else c for c in original
    ]
    _, denied = compile_publication(bad, raw, authority(raw), Words())
    assert not any(p["basis"] == "table_projection" for p in denied.values())


@pytest.mark.parametrize(
    "change", ["column", "text", "cell", "bbox", "model", "row_order"]
)
def test_store_and_runtime_both_refuse_a_changed_projection_proof(change: str) -> None:
    raw = manifest()
    selected, scopes = compile_publication(
        chunks(H2_DE[:12]), raw, authority(raw), Words()
    )
    chunk = next(c for c in selected if product_ids(scopes, c.id) == [1179])
    scope = deepcopy(scopes[chunk.id])
    projection = scope["table_projection"]
    text = chunk.text
    if change == "column":
        projection["model_column"] += 1
    elif change == "text":
        text = text.replace("25000", "30000")
    elif change == "cell":
        projection["source_cells"][0]["text"] += " unknown"
    elif change == "bbox":
        projection["source_cells"][0]["bbox"] = [0, 0, 0, 0]
    elif change == "model":
        projection["model"] = "H2-30K-T3"
    else:
        projection["source_rows"] = list(reversed(projection["source_rows"]))
    assert not authorize_chunk(
        chunk.doc_sha256,
        [1179],
        scope["associations"],
        scope,
        products=Snapshot.read(raw).products,
        chunk_id=chunk.id,
        text=text,
    )


def test_family_prefix_classification_does_not_accept_a_real_unavailable_identity() -> (
    None
):
    raw = manifest()
    original = chunks(H2_DE[:12])
    client = authority(raw, extra_models={"H2": "unavailable"})
    assert not scope_proofs(original, raw, client)


def manual_chunks(prefix: str) -> list[Chunk]:
    raw = json.loads(
        gzip.decompress((FIXTURES / "family-manual-chunks.json.gz").read_bytes())
    )
    return [Chunk(**item) for item in raw if item["doc_sha256"].startswith(prefix)]


@pytest.mark.parametrize(
    "prefix,pid,query,phrase",
    [
        ("770ccafa080c", 1179, "Installationsumgebung", "frei von brennbaren"),
        (
            "a92c63a47dc0",
            1182,
            "Batterien Vorsicht",
            "Laden oder entladen Sie Batterien",
        ),
        ("2c1dd5c1e2f7", 1185, "blind-mate connector", "quick electrical connection"),
    ],
)
@pytest.mark.parametrize("lang", ["en", "de"])
def test_actual_family_manual_instructions_are_readable_for_current_associated_model(
    tmp_path: Path, prefix: str, pid: int, query: str, phrase: str, lang: str
) -> None:
    original = manual_chunks(prefix)
    loaded = compiled_index(tmp_path, prefix, original)
    try:
        hits = loaded.search(query, lang, [pid], publication=Snapshot.read(manifest()))
        assert any(phrase in h.text for h in hits)
        assert all(h.product_ids == (pid,) for h in hits)
        revoked = manifest()
        for document in revoked["documents"]:
            if document["blob_sha256"].startswith(prefix):
                document["product_ids"] = [
                    i for i in document["product_ids"] if i != pid
                ]
        revoked["documents"] = [d for d in revoked["documents"] if d["product_ids"]]
        assert not loaded.search(query, lang, [pid], publication=Snapshot.read(revoked))
    finally:
        loaded.close()


@pytest.mark.parametrize(
    "foreign", ["HS3-12K-T2-W-P", "Model: Z999", "HS3-8K-T2-W/G-PX"]
)
def test_family_manual_cannot_broadcast_a_finer_model_override(foreign: str) -> None:
    raw = manifest()
    original = manual_chunks("2c1dd5c1e2f7")
    target = replace(original[-1], id="foreign", text=f"{foreign} voltage is 1000V")
    selected, scopes = compile_publication(
        [*original, target], raw, authority(raw), Words()
    )
    assert not any(c.id != target.id and c.text == target.text for c in selected)
    assert not any(
        p.get("family_scope", {}).get("source_chunk_id") == "foreign"
        for p in scopes.values()
    )


def test_no_family_permission_from_generated_metadata_or_unrelated_same_pdf_model() -> (
    None
):
    raw = manifest()
    original = manual_chunks("2c1dd5c1e2f7")
    fake = replace(original[-1], id="metadata-only", section="", header="HS3 Series")
    _, scopes = compile_publication([fake], raw, authority(raw), Words())
    assert not any(p["basis"] == "family_manual" for p in scopes.values())
    _, actual = compile_publication(original, raw, authority(raw), Words())
    # The manual also has a Woo association to a BU3 battery. HS3's family
    # title does not prove BU3's own facts or authorize its separate identity.
    assert not any(
        p["basis"] == "family_manual" and 2093 in p["product_ids"]
        for p in actual.values()
    )


def test_unknown_starred_ratings_and_missing_merged_header_geometry_stay_closed() -> (
    None
):
    raw = manifest()
    selected, scopes = compile_publication(
        chunks("b4a653fd2c0b"), raw, authority(raw), Words()
    )
    target = [c for c in selected if product_ids(scopes, c.id) == [1185]]
    assert any(
        "| Max. Charging/Discharging Current [A] | 30/30 |" in c.text for c in target
    )
    assert any(
        "| AC Output [Back-up] |  |\n| Rated Output Power [W] | 12000 |" in c.text
        for c in target
    )
    assert not any("| Rated AC Power [W] | 12000* |" in c.text for c in target)
    original = chunks("0f0e75ad3f31")
    stripped = []
    for chunk in original:
        cells = deepcopy(chunk.source_cells)
        for cell in cells:
            cell.pop("model_spans", None)
        stripped.append(replace(chunk, source_cells=cells))
    _, unproven = compile_publication(stripped, raw, authority(raw), Words())
    assert not any(p["basis"] == "table_projection" for p in unproven.values())


def test_all_fifteen_affected_current_models_get_their_own_correct_original_column() -> (
    None
):
    raw = manifest()
    expected = {
        "0f0e75ad3f31": {
            4107: "| Rated AC Power [W] | 10000 |",
            4108: "| Rated AC Power [W] | 12000 |",
            2063: "| Rated AC Power [W] | 15000 |",
            2064: "| Rated AC Power [W] | 20000 |",
            1179: "| Rated AC Power [W] | 25000 |",
            1181: "| Rated AC Power [W] | 29999 |",
        },
        "0abea746ac33": {
            4109: "| Rated AC Power [W] | 5000 |",
            1183: "| Rated AC Power [W] | 6000 |",
            1184: "| Rated AC Power [W] | 8000 |",
            1182: "| Rated AC Power [W] | 10000 |",
        },
        "b4a653fd2c0b": {
            2198: "| Rated Output Power [W] | 5000 |",
            1186: "| Rated Output Power [W] | 6000 |",
            1187: "| Rated Output Power [W] | 8000 |",
            2199: "| Rated Output Power [W] | 10000 |",
            1185: "| Rated Output Power [W] | 12000 |",
        },
    }
    observed = set()
    for prefix, models in expected.items():
        selected, scopes = compile_publication(
            chunks(prefix), raw, authority(raw), Words()
        )
        for pid, line in models.items():
            matching = [c for c in selected if product_ids(scopes, c.id) == [pid]]
            assert any(line in c.text for c in matching), (pid, line)
            for chunk in matching:
                proof = scopes[chunk.id]
                assert all(a["product_id"] == pid for a in proof["associations"])
                assert all(
                    a["blob_sha256"].startswith(prefix) for a in proof["associations"]
                )
            observed.add(pid)
    assert len(observed) == 15


def test_native_regression_fixtures_are_unchanged_original_bytes() -> None:
    source = json.loads((FIXTURES / "source.json").read_text())
    for record in source["documents"]:
        sha = record["blob_sha256"]
        original = gzip.decompress((FIXTURES / f"{sha}.json.gz").read_bytes())
        assert hashlib.sha256(original).hexdigest() == record["docling_sha256"]
        pdf = FIXTURES / f"{sha}.pdf"
        if pdf.is_file():
            assert hashlib.sha256(pdf.read_bytes()).hexdigest() == sha
    physical = source["physical_headers"]
    assert (
        hashlib.sha256((FIXTURES / physical["file"]).read_bytes()).hexdigest()
        == physical["sha256"]
    )


def test_finer_manual_declaration_never_broadens_its_following_paragraph() -> None:
    raw = manifest()
    original = manual_chunks("2c1dd5c1e2f7")
    first = replace(
        original[-1],
        id="variant-intro",
        section="Installation",
        text="These instructions apply only to HS3-12K-T2-W/G-PX.",
    )
    second = replace(
        original[-1],
        id="variant-continuation",
        section="Installation",
        text="Set the charging limit to 42 A before connecting the battery.",
    )
    selected, scopes = compile_publication(
        [*original, first, second], raw, authority(raw), Words()
    )
    assert scopes[second.id]["product_ids"] == [1185]
    for chunk in selected:
        if chunk.text == second.text and chunk.id in scopes:
            proof = scopes[chunk.id]
            assert proof["product_ids"] == [1185]
            assert authorize_chunk(
                chunk.doc_sha256,
                proof["product_ids"],
                proof["associations"],
                proof,
                products=Snapshot.read(raw).products,
                chunk_id=chunk.id,
                text=chunk.text,
            )


def test_empty_child_heading_does_not_erase_an_authored_narrower_parent() -> None:
    raw = manifest()
    document = next(
        d for d in raw["documents"] if d["blob_sha256"].startswith("770ccafa080c")
    )
    selected = chunk_document(
        DocumentMeta(
            document["blob_sha256"], document["title"], "", (), (), "manual", "en"
        ),
        [
            Page(
                1,
                "docling",
                [
                    Block("heading", text="H2 Series"),
                    Block(
                        "text",
                        text="The H2 series inverter manual gives operating and installation instructions for the products described here.",
                    ),
                ],
            ),
            Page(
                2,
                "docling",
                [
                    Block("heading", text="H2-10K-T3 only"),
                    Block("heading", text="Installation procedure"),
                    Block(
                        "text",
                        text="This variant requires a special bracket and a mounting clearance of 300 mm around the case.",
                    ),
                ],
            ),
        ],
        Words(),
        lambda _: "en",
    )
    compiled, scopes = compile_publication(selected, raw, authority(raw), Words())
    assert not any(
        "special bracket" in chunk.text and 1179 in product_ids(scopes, chunk.id)
        for chunk in compiled
    )


def test_logical_column_offsets_cannot_override_original_value_positions() -> None:
    raw = manifest()
    original = chunks("0f0e75ad3f31")
    native = next(c for c in original if c.source_cells)
    cells = deepcopy(native.source_cells)
    label = next(c for c in cells if c["text"] == "Rated AC Power [W]")
    rated = [
        c
        for c in cells
        if c["row_start"] == label["row_start"] and c["text"] in {"10000", "12000"}
    ]
    one, two = rated
    one["col_start"], two["col_start"] = two["col_start"], one["col_start"]
    one["col_end"], two["col_end"] = two["col_end"], one["col_end"]
    mutated = [
        replace(c, source_cells=cells) if c.id == native.id else c for c in original
    ]
    compiled, scopes = compile_publication(mutated, raw, authority(raw), Words())
    assert not any(
        "| Rated AC Power [W] | 12000 |" in c.text and 4107 in product_ids(scopes, c.id)
        for c in compiled
    )


@pytest.mark.parametrize("reset", ["family", "numbered_sibling"])
def test_only_a_proven_authored_scope_boundary_restores_family_instructions(
    reset: str,
) -> None:
    raw = manifest()
    document = next(
        d for d in raw["documents"] if d["blob_sha256"].startswith("770ccafa080c")
    )
    headings = [
        Block("heading", text="H2 Series"),
        Block(
            "text",
            text="The H2 series inverter manual describes installation and operation.",
        ),
        Block("heading", text="2.1. H2-10K-T3 only"),
        Block("heading", text="2.1.1. Installation procedure"),
        Block(
            "text",
            text="This variant requires a special bracket and a mounting clearance of 300 mm.",
        ),
        Block(
            "heading",
            text="H2 Series" if reset == "family" else "2.2. General installation",
        ),
        Block(
            "text",
            text="Keep the equipment away from children and from explosive materials during installation.",
        ),
    ]
    original = chunk_document(
        DocumentMeta(
            document["blob_sha256"], document["title"], "", (), (), "manual", "en"
        ),
        [Page(1, "docling", headings)],
        Words(),
        lambda _: "en",
    )
    compiled, scopes = compile_publication(original, raw, authority(raw), Words())
    assert not any(
        "special bracket" in c.text and 1179 in product_ids(scopes, c.id)
        for c in compiled
    )
    assert any(
        "explosive materials" in c.text and product_ids(scopes, c.id) == [1179]
        for c in compiled
    )


@pytest.mark.parametrize(
    "change", ["missing", "native_outside", "span_outside", "reverse_offsets"]
)
def test_single_model_header_requires_visible_physical_provenance(change: str) -> None:
    raw = manifest()
    original = chunks(H2_DE[:12])
    native = next(c for c in original if c.source_cells)
    cells = deepcopy(native.source_cells)
    headers = [c for c in cells if c["row_start"] == 0 and c["col_start"] > 0]
    if change == "missing":
        headers[0].pop("model_spans", None)
    elif change == "native_outside":
        headers[0]["bbox"] = (-1000, -1000, -900, -900)
    elif change == "span_outside":
        headers[0]["model_spans"][0]["bbox"] = (-1000, -1000, -900, -900)
    else:
        a, b = headers[:2]
        a["col_start"], b["col_start"] = b["col_start"], a["col_start"]
        a["col_end"], b["col_end"] = b["col_end"], a["col_end"]
    selected = [
        replace(c, source_cells=cells) if c.id == native.id else c for c in original
    ]
    _, scopes = compile_publication(selected, raw, authority(raw), Words())
    assert not any(p["basis"] == "table_projection" for p in scopes.values())


def test_runtime_independently_refuses_a_family_grant_outside_its_author_restriction() -> (
    None
):
    raw = manifest()
    selected, scopes = compile_publication(
        manual_chunks("2c1dd5c1e2f7"), raw, authority(raw), Words()
    )
    chunk = next(c for c in selected if product_ids(scopes, c.id) == [1186])
    proof = deepcopy(scopes[chunk.id])
    proof["author_restrictions"] = [
        {
            "kind": "declaration",
            "quote": "These instructions apply only to HS3-12K-T2-W/G-PX.",
            "source_chunk_id": proof["source_chunk_ids"][0],
        }
    ]
    assert not authorize_chunk(
        chunk.doc_sha256,
        [1186],
        proof["associations"],
        proof,
        products=Snapshot.read(raw).products,
        chunk_id=chunk.id,
        text=chunk.text,
    )


def test_runtime_rejects_column_swap_even_with_self_consistent_hashes_and_id() -> None:
    raw = manifest()
    selected, scopes = compile_publication(
        chunks("0f0e75ad3f31"), raw, authority(raw), Words()
    )
    chunk = next(c for c in selected if product_ids(scopes, c.id) == [4107])
    proof = deepcopy(scopes[chunk.id])
    projection = proof["table_projection"]
    cells = projection["source_cells"]
    label = next(c for c in cells if c["text"] == "Rated AC Power [W]")
    one, two = [
        c
        for c in cells
        if c["row_start"] == label["row_start"] and c["text"] in {"10000", "12000"}
    ]
    one["col_start"], two["col_start"] = two["col_start"], one["col_start"]
    one["col_end"], two["col_end"] = two["col_end"], one["col_end"]
    wrong = chunk.text.replace(
        "| Rated AC Power [W] | 10000 |", "| Rated AC Power [W] | 12000 |"
    )
    projection["source_cells_sha256"] = cells_digest(cells)
    projection["text_sha256"] = hashlib.sha256(wrong.encode()).hexdigest()
    cid = projection_id(
        chunk.doc_sha256,
        chunk.page,
        projection["source_table"],
        projection["model"],
        wrong,
    )
    assert not authorize_chunk(
        chunk.doc_sha256,
        [4107],
        proof["associations"],
        proof,
        products=Snapshot.read(raw).products,
        chunk_id=cid,
        text=wrong,
    )


def test_unnumbered_narrow_heading_cannot_borrow_a_previous_chapter_for_reset() -> None:
    raw = manifest()
    document = next(
        d for d in raw["documents"] if d["blob_sha256"].startswith("770ccafa080c")
    )
    original = chunk_document(
        DocumentMeta(
            document["blob_sha256"], document["title"], "", (), (), "manual", "en"
        ),
        [
            Page(
                1,
                "docling",
                [
                    Block("heading", text="H2 Series"),
                    Block(
                        "text",
                        text="The H2 series manual describes installation and operation.",
                    ),
                    Block("heading", text="1. Overview"),
                    Block(
                        "text",
                        text="General equipment information for the described products.",
                    ),
                    Block("heading", text="H2-10K-T3 only"),
                    Block("heading", text="2. Installation"),
                    Block(
                        "text",
                        text="This variant requires a special bracket and a mounting clearance of 300 mm.",
                    ),
                ],
            )
        ],
        Words(),
        lambda _: "en",
    )
    compiled, scopes = compile_publication(original, raw, authority(raw), Words())
    assert not any(
        "special bracket" in c.text and 1179 in product_ids(scopes, c.id)
        for c in compiled
    )


@pytest.mark.parametrize("withdrawn", ["Energy Cabinet Pro", "CABINET"])
def test_empty_unavailable_plain_woo_heading_is_identified_before_generic_child(
    withdrawn: str,
) -> None:
    raw = manifest()
    document = next(
        d for d in raw["documents"] if d["blob_sha256"].startswith("770ccafa080c")
    )
    original = chunk_document(
        DocumentMeta(
            document["blob_sha256"], document["title"], "", (), (), "manual", "en"
        ),
        [
            Page(
                1,
                "docling",
                [
                    Block("heading", text="H2 Series"),
                    Block(
                        "text",
                        text="The H2 series manual describes installation and operation.",
                    ),
                    Block("heading", text=withdrawn),
                    Block("heading", text="Installation procedure"),
                    Block(
                        "text",
                        text="This variant requires a special bracket and a mounting clearance of 300 mm.",
                    ),
                ],
            )
        ],
        Words(),
        lambda _: "en",
    )
    compiled, scopes = compile_publication(
        original, raw, authority(raw, extra_models={withdrawn: "unavailable"}), Words()
    )
    assert not any(
        "special bracket" in c.text and 1179 in product_ids(scopes, c.id)
        for c in compiled
    )


@pytest.mark.parametrize("prefix_repeats", [5330, 5400])
def test_long_native_heading_is_identified_in_bounded_utf8_requests(
    prefix_repeats: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = manifest()
    document = next(
        d for d in raw["documents"] if d["blob_sha256"].startswith("770ccafa080c")
    )
    # Exercise a model crossing byte 16,000 and a cut inside a UTF-8 code point.
    heading = "ä " * prefix_repeats + "Energy Cabinet Pro"
    original = chunk_document(
        DocumentMeta(
            document["blob_sha256"], document["title"], "", (), (), "manual", "en"
        ),
        [
            Page(
                1,
                "docling",
                [
                    Block("heading", text="H2 Series"),
                    Block(
                        "text",
                        text="The H2 series manual describes installation and operation.",
                    ),
                    Block("heading", text=heading),
                    Block("heading", text="Installation procedure"),
                    Block(
                        "text",
                        text="This variant requires a special bracket and a mounting clearance of 300 mm.",
                    ),
                ],
            )
        ],
        Words(),
        lambda _: "en",
    )
    # Generated metadata is not source evidence and must never be identified.
    original = [replace(c, header=c.header + " GeneratedSecretModel") for c in original]
    client = authority(raw, extra_models={"Energy Cabinet Pro": "unavailable"})
    identify = client.identify_text
    supplied: list[str] = []

    def capture(text: str) -> dict[str, str]:
        assert 0 < len(text.encode()) <= 16000
        supplied.append(text)
        return identify(text)

    monkeypatch.setattr(client, "identify_text", capture)
    compiled, scopes = compile_publication(original, raw, client, Words())
    assert any("Energy Cabinet Pro" in text for text in supplied)
    assert all("GeneratedSecretModel" not in text for text in supplied)
    assert not any(
        "special bracket" in c.text and 1179 in product_ids(scopes, c.id)
        for c in compiled
    )
