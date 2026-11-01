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
from docling_core.types.doc.base import BoundingBox
from docling_core.types.doc.common.reference import ProvenanceItem
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.labels import DocItemLabel
from test_chunking import Words
from test_publication import authority
from test_publication import manifest as basic_manifest

from index import corpus, store
from index.chunking import Chunk, DocumentMeta, chunk_document
from index.corpus import DocumentRow
from index.extract import Block, Page, enrich_model_axes, pages_of
from index.inventory import doc_type_of
from index.publication import ScopeProof, _recognized, compile_publication, scope_proofs
from index.table_compiler import (
    _author_contexts,
    _series_cover_for_axis,
    external_axis_anchors,
)
from index.warranty import compile_procedures
from linker_genie.figures import tag
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.table_projection import (
    COMPATIBILITY_STATEMENT,
    OVERVIEW_ARM_NOTES,
    OVERVIEW_POWER_NOTES,
    cells_digest,
    projection_id,
    render_projection,
)

FIXTURES = Path(__file__).parent / "fixtures" / "publication-compiler"
H2_DE = "be488dc6630cddc8381e38c61c6bc7b41c50c711042cdb2547170bd85e68a752"


def test_picture_heading_does_not_restrict_a_later_authored_section() -> None:
    """A model printed in a figure is not a heading for subsequent chapters."""
    raw = basic_manifest()
    sha = raw["documents"][0]["blob_sha256"]

    def prov(page: int) -> ProvenanceItem:
        return ProvenanceItem(
            page_no=page,
            bbox=BoundingBox(l=0, t=0, r=100, b=100),
            charspan=(0, 1),
        )

    def compile_document(
        picture_heading: bool,
    ) -> tuple[list[Chunk], dict[str, ScopeProof]]:
        document = DoclingDocument(name="figure-scope")
        document.add_heading("2.2.3 Smart Meter", prov=prov(1))
        picture = document.add_picture(prov=prov(1))
        group = document.add_group(parent=picture)
        document.add_heading(
            "Only GM330", parent=group if picture_heading else None, prov=prov(1)
        )
        document.add_text(DocItemLabel.TEXT, "75 mm", parent=picture, prov=prov(1))
        document.add_heading("2.5 Features", prov=prov(2))
        document.add_text(
            DocItemLabel.TEXT, "MODEL-1 and MODEL-2 feature AFCI.", prov=prov(2)
        )
        pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
        meta = DocumentMeta(sha, "Test manual", "", (), (), "manual", "en")
        original = chunk_document(meta, pages, Words(), lambda _: "en")
        return compile_publication(
            original,
            raw,
            authority(raw, extra_models={"GM330": "unavailable"}),
            Words(),
        )

    selected, proofs = compile_document(picture_heading=True)
    figure = next(c for c in selected if "Only GM330" in c.text)
    dimensions = next(c for c in selected if "75 mm" in c.text)
    assert figure.source_picture and dimensions.source_picture == figure.source_picture
    target = next(c for c in selected if "feature AFCI" in c.text)
    proof = proofs[target.id]
    assert proof["product_ids"] == [1, 2]
    current = Snapshot.read(raw)
    assert authorize_chunk(
        sha,
        [1, 2],
        proof["associations"],
        proof,
        products=current.products,
        documents=current.documents,
        chunk_id=target.id,
        text=target.text,
    )
    assert not authorize_chunk(
        sha,
        [1, 2],
        proof["associations"][:1],
        proof,
        products=current.products,
        documents=current.documents,
        chunk_id=target.id,
        text=target.text,
    )

    selected, proofs = compile_document(picture_heading=False)
    target = next(c for c in selected if "feature AFCI" in c.text)
    assert target.id not in proofs


def test_picture_model_does_not_authorize_generic_body_text() -> None:
    raw = basic_manifest()
    sha = raw["documents"][0]["blob_sha256"]
    prov = ProvenanceItem(
        page_no=1, bbox=BoundingBox(l=0, t=0, r=100, b=100), charspan=(0, 1)
    )
    document = DoclingDocument(name="figure-origin")
    document.add_heading("Overview", prov=prov)
    picture = document.add_picture(prov=prov)
    document.add_heading("MODEL-1", parent=picture, prov=prov)
    document.add_text(
        DocItemLabel.TEXT, "MODEL-2 uses 75 mm.", parent=picture, prov=prov
    )
    document.add_text(DocItemLabel.TEXT, "Generic installation guidance.", prov=prov)
    pages = [Page(n, "docling", blocks) for n, blocks in pages_of(document).items()]
    original = chunk_document(
        DocumentMeta(sha, "Test datasheet", "", (), (), "datasheet", "en"),
        pages,
        Words(),
        lambda _: "en",
    )
    selected, proofs = compile_publication(original, raw, authority(raw), Words())
    target = next(c for c in selected if "Generic installation guidance" in c.text)
    assert target.id not in proofs
    figure_detail = next(c for c in selected if "MODEL-2 uses 75 mm" in c.text)
    assert figure_detail.id not in proofs


def test_picture_table_interrupts_a_prior_body_table_heading() -> None:
    sha = basic_manifest()["documents"][0]["blob_sha256"]
    figure_table = Block(
        "table",
        rows=(("unrelated", "table"),),
        source_id="figure-table",
        source_picture="#/pictures/0",
    )
    body_table = Block("table", rows=(("actual", "table"),), source_id="body-table")
    chunks = chunk_document(
        DocumentMeta(sha, "Test", "", (), (), "datasheet", "en"),
        [
            Page(
                1,
                "docling",
                [
                    Block("text", "Technical Data MODEL-1 MODEL-2"),
                    figure_table,
                    body_table,
                ],
            )
        ],
        Words(),
        lambda _: "en",
    )
    target = next(c for c in chunks if c.source_table.endswith("body-table"))
    assert target.preceding_text == ()


def test_range_title_is_not_mistaken_for_a_model_restriction() -> None:
    raw = basic_manifest()
    sha = raw["documents"][0]["blob_sha256"]
    title = "5-30kW/5-108kWh I Dreiphasig All-in-One (HV)"
    generic = Chunk(
        "generic",
        sha,
        1,
        title,
        "text",
        "",
        "System overview",
        "de",
        5,
        source_headings=(title,),
    )
    assert _author_contexts([generic], Snapshot.read(raw), {})["generic"][0][
        "rating_cover"
    ]

    # A real model-shaped prefix or an explicit narrower current model must
    # still constrain later content, even when a power range follows it.
    unknown = replace(
        generic,
        id="unknown",
        section="X5-30kW/5-108kWh only",
        source_headings=("X5-30kW/5-108kWh only",),
    )
    current = replace(
        generic,
        id="current",
        section="MODEL-1 only 5-30kW/5-108kWh",
        source_headings=("MODEL-1 only 5-30kW/5-108kWh",),
    )
    bounded = replace(
        generic,
        id="bounded",
        section="Only 5-30kW/5-108kWh models",
        source_headings=("Only 5-30kW/5-108kWh models",),
    )
    assert "unknown" in _author_contexts([unknown], Snapshot.read(raw), {})
    assert "current" in _author_contexts([current], Snapshot.read(raw), {})
    assert "bounded" in _author_contexts([bounded], Snapshot.read(raw), {})
    for chunk in (unknown, current, bounded):
        assert not any(
            boundary.get("rating_cover")
            for boundary in _author_contexts([chunk], Snapshot.read(raw), {})[chunk.id]
        )

    target = replace(
        generic,
        id="ordinary-model-passage",
        page=2,
        section="General information",
        source_headings=("General information",),
        text="MODEL-1 works.",
    )
    _, proof = compile_publication([generic, target], raw, authority(raw), Words())
    assert target.id not in proof


def warranty_fixture() -> tuple[dict[str, Any], list[Chunk], Chunk, ScopeProof]:
    value = json.loads(
        gzip.decompress((FIXTURES / "warranty-procedure.json.gz").read_bytes())
    )
    value["manifest"]["model_identity_revision"] = "fixture-identity-1"
    value["model_scope"]["model_identity_revision"] = "fixture-identity-1"
    return (
        value["manifest"],
        [Chunk(**c) for c in value["original"]],
        Chunk(**value["model_chunk"]),
        value["model_scope"],
    )


@pytest.mark.parametrize("lang", ["en", "de"])
def test_original_series_bound_claims_procedure_reaches_sqlite_and_revokes(
    tmp_path: Path, lang: str
) -> None:
    raw, original, model, model_scope = warranty_fixture()
    units, proofs = compile_procedures(
        original,
        [model],
        {model.id: model_scope},
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts=_author_contexts(
            original, Snapshot.read(raw), _recognized(original, authority(raw))
        ),
    )
    assert units and {c.lang for c in units} == {"en", "de"}
    assert all(
        c.page == 2 and "coverage and duration unverified" in c.header for c in units
    )
    all_scopes = {model.id: model_scope, **proofs}
    source = tmp_path / "corpus"
    corpus.write(
        source,
        corpus.Meta(
            "conditional-warranty",
            None,
            None,
            "original cached source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {
                    cid: p["product_ids"] for cid, p in all_scopes.items()
                },
                "chunk_scopes": all_scopes,
            },
        ),
        [
            DocumentRow(
                d["blob_sha256"],
                (d["url"],),
                d["title"],
                "",
                (),
                (),
                doc_type_of(d["type"], d.get("role", "")),
                d["lang"],
                6,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(6512, "GW5K-ETA-G20")],
        [model, *units],
    )
    target = tmp_path / "index.sqlite"
    store.export(source, target)
    loaded = DocumentIndex(target, encoder=None)
    try:
        query = (
            "distributor installer warranty claim"
            if lang == "en"
            else "Vertriebshändler Installateur Garantieantrag"
        )
        hits = loaded.search(query, lang, [6512], publication=Snapshot.read(raw))
        procedure = [h for h in hits if "-warranty-" in h.chunk_id]
        assert procedure and all(
            h.product_ids == (6512,) and h.page == 2 for h in procedure
        )
        assert all("does not establish coverage" in h.scope_note for h in procedure)
        assert all(
            "10 years" not in h.text and "10 Jahre" not in h.text for h in procedure
        )
        if lang == "en":
            # Distinct current-authority fences: the supporting original, its
            # bytes, the cited policy relationship, and role-first purpose.
            ds = next(
                d["document_id"] for d in raw["documents"] if d["type"] == "datasheet"
            )
            en = next(
                d["document_id"]
                for d in raw["documents"]
                if d["type"] == "warranty" and d["lang"].casefold() == "en"
            )
            revocations: list[tuple[str, Any, str]] = [
                ("remove", None, ds),
                ("blob_sha256", "0" * 64, ds),
                ("product_ids", [], en),
                ("role", "document", en),
            ]
            for field, value, did in revocations:
                changed = deepcopy(raw)
                if field == "remove":
                    changed["documents"] = [
                        d for d in changed["documents"] if d["document_id"] != did
                    ]
                else:
                    next(d for d in changed["documents"] if d["document_id"] == did)[
                        field
                    ] = value
                assert not any(
                    "-warranty-" in h.chunk_id and h.lang == "en"
                    for h in loaded.search(
                        query, "en", [6512], publication=Snapshot.read(changed)
                    )
                )
    finally:
        loaded.close()


def test_claims_chain_cannot_use_generated_cover_or_numeric_warranty_benefits() -> None:
    raw, original, model, model_scope = warranty_fixture()
    from linker_genie.warranty_scope import claims_procedure

    assert not claims_procedure(
        "Contact your distributor and installer to claim a 10 year warranty."
    )
    fake = [
        replace(c, section="", text="", header="ESA Series 5-30kW")
        if c.doc_sha256 == model.doc_sha256 and c.page == 1
        else c
        for c in original
    ]
    units, _ = compile_procedures(
        fake,
        [model],
        {model.id: model_scope},
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts=_author_contexts(
            fake, Snapshot.read(raw), _recognized(fake, authority(raw))
        ),
    )
    assert not units
    for heading in ["GW5K-ETA-G20 only", "Energy Cabinet Pro"]:
        restricted = [
            replace(c, section=heading, source_headings=(heading,))
            if claims_procedure(c.text)
            else c
            for c in original
        ]
        client = authority(raw, extra_models={"Energy Cabinet Pro": "unavailable"})
        contexts = _author_contexts(
            restricted, Snapshot.read(raw), _recognized(restricted, client)
        )
        units, _ = compile_procedures(
            restricted,
            [model],
            {model.id: model_scope},
            Snapshot.read(raw),
            Words(),
            512,
            restricted_contexts=contexts,
        )
        assert not units


def manifest() -> dict[str, Any]:
    value = json.loads(gzip.decompress((FIXTURES / "manifest.json.gz").read_bytes()))
    assert isinstance(value, dict)
    value["model_identity_revision"] = "fixture-identity-1"
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


def test_native_technical_heading_can_span_two_label_columns() -> None:
    """A wider label does not shift model values or permit a nearby variant."""
    original = chunks(H2_DE[:12])
    raw = manifest()
    native = next(c for c in original if c.source_cells)
    cells = deepcopy(native.source_cells)
    for cell in cells:
        if cell["col_start"] == 0:
            cell["col_end"] += 1
            if cell["row_start"] == 0:
                cell["text"] = "Technische Daten"
        else:
            cell["col_start"] += 1
            cell["col_end"] += 1
    widened = [
        replace(c, source_cells=cells) if c.id == native.id else c for c in original
    ]
    selected, scopes = compile_publication(widened, raw, authority(raw), Words())
    model = next(
        c
        for c in selected
        if product_ids(scopes, c.id) == [1179]
        and "| Nennleistung AC [W] | 25000 |" in c.text
    )
    scope = scopes[model.id]
    snapshot = Snapshot.read(raw)
    assert authorize_chunk(
        model.doc_sha256,
        [1179],
        scope["associations"],
        scope,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=model.id,
        text=model.text,
    )
    assert "| Nennleistung AC [W] | 30000 |" not in model.text
    assert not authorize_chunk(
        model.doc_sha256,
        [1181],
        scope["associations"],
        scope,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=model.id,
        text=model.text,
    )

    partial = deepcopy(cells)
    row = next(c["row_start"] for c in partial if c["text"] == "Nennleistung AC [W]")
    rated = next(c for c in partial if c["row_start"] == row and c["col_start"] == 4)
    rated["text"] = "25000 /"
    assert render_projection(partial, 3, [row]) is None
    rated["text"] = "25000"
    # A parser-merged value may have dropped words. Even if its remaining text
    # and logical span touch a column, it cannot become a model-specific fact.
    partial = [
        c
        for c in partial
        if c is rated or not (c["row_start"] == row and c["col_start"] == 5)
    ]
    rated["col_end"] += 1
    assert render_projection(partial, 3, [row]) is None

    changed = deepcopy(cells)
    header = next(c for c in changed if c["row_start"] == c["col_start"] == 0)
    header["text"] = "Different heading"
    denied = [
        replace(c, source_cells=changed) if c.id == native.id else c for c in original
    ]
    _, proofs = compile_publication(denied, raw, authority(raw), Words())
    assert not any(p["basis"] == "table_projection" for p in proofs.values())


def test_cover_series_must_match_the_complete_native_axis() -> None:
    chunk = chunks(H2_DE[:12])[0]
    heading = "Lynx D G2 Series"
    chunk = replace(chunk, page=1, source_headings=(heading,))
    origin = {chunk.id: chunk}
    boundary = {"kind": "heading", "quote": heading, "source_chunk_id": chunk.id}
    axis = ["GW5.1-BAT-D-G20", "GW9.0-BAT-D-G20"]
    assert _series_cover_for_axis(boundary, axis, origin)
    assert not _series_cover_for_axis(boundary, [*axis, "GW9.0-BAT-D-G30"], origin)
    assert not _series_cover_for_axis(boundary, [*axis, "GW9.0-BAT-LC-G20"], origin)
    assert not _series_cover_for_axis({**boundary, "kind": "declaration"}, axis, origin)
    assert not _series_cover_for_axis(
        {**boundary, "quote": "Lynx D G2 Series only"}, axis, origin
    )


def test_compatibility_pair_binds_both_exact_subjects_and_original_statement() -> None:
    raw = basic_manifest()
    raw["documents"][0]["type"] = "compatibility"
    sha = raw["documents"][0]["blob_sha256"]
    battery_text = (
        "Product: Rechargeable Li-ion Battery System\n"
        "Model(s): MODEL-1, MODEL-11\nDescription: Battery system."
    )
    table_text = (
        "| Inverter Manufacture | Product | Model |\n"
        "| Manufacturer | Series | MODEL-2 / MODEL-20 |"
    )

    def native_id(kind: str, text: str) -> str:
        digest = hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()[:8]
        return f"{sha[:12]}-p1-{digest}"

    def cell(row: int, col: int, value: str) -> dict[str, Any]:
        return {
            "row_start": row,
            "row_end": row + 1,
            "col_start": col,
            "col_end": col + 1,
            "text": value,
            "column_header": row == 0,
            "row_header": False,
            "row_section": False,
            "bbox": (col * 40 + 1, row * 20 + 1, col * 40 + 30, row * 20 + 15),
            "bbox_origin": "TOPLEFT",
        }

    source = Chunk(
        native_id("text", battery_text), sha, 1, "", "text", "", battery_text, "en", 20
    )
    table = Chunk(
        native_id("table", table_text),
        sha,
        1,
        COMPATIBILITY_STATEMENT,
        "table",
        "",
        table_text,
        "en",
        20,
        source_table="docling:p1:#/tables/0",
        source_rows=(0, 1),
        source_cells=tuple(
            cell(r, c, text)
            for r, row in enumerate(
                [
                    ("Inverter Manufacture", "Product", "Model"),
                    ("Manufacturer", "Series", "MODEL-2 / MODEL-20"),
                ]
            )
            for c, text in enumerate(row)
        ),
        source_headings=(COMPATIBILITY_STATEMENT,),
    )
    original = [source, table]
    compiled, scopes = compile_publication(original, raw, authority(raw), Words())
    result = [
        c
        for c in compiled
        if c.id in scopes and scopes[c.id]["basis"] == "compatibility_pair"
    ]
    assert len(result) == 1
    match = result[0]
    proof = scopes[match.id]
    assert proof["product_ids"] == [1, 2]
    assert "MODEL-11" not in match.text and "MODEL-20" not in match.text
    snapshot = Snapshot.read(raw)
    kwargs = dict(
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=match.id,
        text=match.text,
        external_axis_anchors=external_axis_anchors(original),
        require_table_anchor=True,
    )
    assert authorize_chunk(sha, [1, 2], proof["associations"], proof, **kwargs)
    assert not authorize_chunk(sha, [1, 2], proof["associations"][:1], proof, **kwargs)
    assert not authorize_chunk(sha, [1], proof["associations"], proof, **kwargs)
    assert not authorize_chunk(
        sha,
        [1, 2],
        proof["associations"],
        proof,
        **{**kwargs, "external_axis_anchors": {}},
    )
    forged = deepcopy(proof)
    forged["compatibility_pair"]["inverter"] = "MODEL-20"
    assert not authorize_chunk(sha, [1, 2], proof["associations"], forged, **kwargs)
    intervening = replace(
        source,
        id=native_id("text", "A different product is described here."),
        text="A different product is described here.",
    )
    _, blocked = compile_publication(
        [source, intervening, table], raw, authority(raw), Words()
    )
    assert not any(p["basis"] == "compatibility_pair" for p in blocked.values())


def test_overview_series_proves_exact_battery_and_keeps_the_condition() -> None:
    raw = basic_manifest()
    raw["documents"][0]["type"] = "compatibility"
    raw["products"][0]["model"] = "GW208.9-BAT-LC-G10"
    raw["products"][1]["model"] = "GW208.9-BAT-LCD-G10"
    sha = raw["documents"][0]["blob_sha256"]
    section = "3) Commercial and Industrial Energy Storage Systems"
    lines = [
        "| Battery | Battery | Battery | Inverter Series | Inverter Series | Inverter Series | Inverter Series | Inverter Series |",
        "| Brand | Series | Model | ETC | BTC | ET(40-50kW) | ET (80-100kW) | ETR 80-125kW |",
        "| GOODWE | BAT *3 | GW208.9-BAT-LC-G10 |  |  | ● |  |  |",
    ]

    def chunk(kind: str, text: str, **kwargs: Any) -> Chunk:
        digest = hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()[:8]
        return Chunk(
            f"{sha[:12]}-p1-{digest}",
            sha,
            1,
            section,
            kind,
            "",
            text,
            "en",
            30,
            **kwargs,
        )  # type: ignore[arg-type]

    def cell(row: int, col: int, value: str) -> dict[str, Any]:
        return {
            "row_start": row,
            "row_end": row + 1,
            "col_start": col,
            "col_end": col + 1,
            "text": value,
            "column_header": row < 2,
            "row_header": False,
            "row_section": False,
            "bbox": (col * 40 + 1, row * 20 + 1, col * 40 + 30, row * 20 + 15),
            "bbox_origin": "TOPLEFT",
        }

    header = (
        "Brand",
        "Series",
        "Model",
        "ETC",
        "BTC",
        "ET(40-50kW)",
        "ET (80-100kW)",
        "ETR 80-125kW",
    )
    cells = [cell(1, col, value) for col, value in enumerate(header)]
    cells += [cell(2, 2, "GW208.9-BAT-LC-G10"), cell(2, 5, "●")]
    table = chunk(
        "table",
        "\n".join(lines),
        source_table="docling:p1:#/tables/0",
        source_rows=(0, 1, 2),
        source_cells=tuple(cells),
        source_headings=(section,),
    )
    arm = chunk("text", OVERVIEW_ARM_NOTES["en"])
    power = chunk("text", OVERVIEW_POWER_NOTES["en"])
    original = [table, arm, power]
    compiled, proofs = compile_publication(original, raw, authority(raw), Words())
    found = [
        c
        for c in compiled
        if c.id in proofs and proofs[c.id]["basis"] == "compatibility_series"
    ]
    assert len(found) == 1
    result = found[0]
    proof = proofs[result.id]
    assert proof["product_ids"] == [1] and OVERVIEW_ARM_NOTES["en"] in result.text
    assert "GW208.9-BAT-LCD-G10" not in result.text
    snap = Snapshot.read(raw)
    kw = dict(
        products=snap.products,
        documents=snap.documents,
        chunk_id=result.id,
        text=result.text,
        external_axis_anchors=external_axis_anchors(original),
        require_table_anchor=True,
    )
    assert authorize_chunk(sha, [1], proof["associations"], proof, **kw)
    assert not authorize_chunk(sha, [2], proof["associations"], proof, **kw)
    assert not authorize_chunk(sha, [1], [], proof, **kw)
    assert not authorize_chunk(
        sha, [1], proof["associations"], proof, **{**kw, "external_axis_anchors": {}}
    )
    changed_note = replace(power, text=power.text.replace("cannot", "can"))
    _, changed_proofs = compile_publication(
        [table, arm, changed_note], raw, authority(raw), Words()
    )
    assert not any(
        p["basis"] == "compatibility_series" for p in changed_proofs.values()
    )
    narrow_table = replace(table, source_headings=("GW208.9-BAT-LCD-G10 only", section))
    _, changed_proofs = compile_publication(
        [narrow_table, arm, power], raw, authority(raw), Words()
    )
    assert not any(
        p["basis"] == "compatibility_series" for p in changed_proofs.values()
    )
    changed_cells = deepcopy(table.source_cells)
    next(cell for cell in changed_cells if cell["text"] == "●")["text"] = ""
    _, changed_proofs = compile_publication(
        [replace(table, source_cells=changed_cells), arm, power],
        raw,
        authority(raw),
        Words(),
    )
    assert not any(
        p["basis"] == "compatibility_series" for p in changed_proofs.values()
    )


@pytest.mark.parametrize(
    "change", ["column", "text", "cell", "bbox", "model", "row_order"]
)
def test_store_and_runtime_both_refuse_a_changed_projection_proof(change: str) -> None:
    raw = manifest()
    selected, scopes = compile_publication(
        chunks(H2_DE[:12]), raw, authority(raw), Words()
    )
    chunk = next(c for c in selected if product_ids(scopes, c.id) == [1179])
    assert authorize_chunk(
        chunk.doc_sha256,
        [1179],
        scopes[chunk.id]["associations"],
        scopes[chunk.id],
        products=Snapshot.read(raw).products,
        documents=Snapshot.read(raw).documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
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
        documents=Snapshot.read(raw).documents,
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
                documents=Snapshot.read(raw).documents,
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
    assert authorize_chunk(
        chunk.doc_sha256,
        [1186],
        scopes[chunk.id]["associations"],
        scopes[chunk.id],
        products=Snapshot.read(raw).products,
        documents=Snapshot.read(raw).documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
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
        documents=Snapshot.read(raw).documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )


def test_runtime_rejects_column_swap_even_with_self_consistent_hashes_and_id() -> None:
    raw = manifest()
    selected, scopes = compile_publication(
        chunks("0f0e75ad3f31"), raw, authority(raw), Words()
    )
    chunk = next(c for c in selected if product_ids(scopes, c.id) == [4107])
    assert authorize_chunk(
        chunk.doc_sha256,
        [4107],
        scopes[chunk.id]["associations"],
        scopes[chunk.id],
        products=Snapshot.read(raw).products,
        documents=Snapshot.read(raw).documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
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
        documents=Snapshot.read(raw).documents,
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

    def capture(text: str, *, expected_revision: str = "") -> dict[str, str]:
        assert 0 < len(text.encode()) <= 16000
        supplied.append(text)
        return identify(text, expected_revision=expected_revision)

    monkeypatch.setattr(client, "identify_text", capture)
    compiled, scopes = compile_publication(original, raw, client, Words())
    assert any("Energy Cabinet Pro" in text for text in supplied)
    assert all("GeneratedSecretModel" not in text for text in supplied)
    assert not any(
        "special bracket" in c.text and 1179 in product_ids(scopes, c.id)
        for c in compiled
    )


def test_actual_eta_certificate_subjects_are_bounded_and_revocable(
    tmp_path: Path,
) -> None:
    """Five live-source originals cover their exact models without their ratings."""
    fixture = json.loads(
        gzip.decompress((FIXTURES / "eta-certificates.json.gz").read_bytes())
    )
    raw = fixture["manifest"]
    raw["model_identity_revision"] = "fixture-identity-1"
    original = [Chunk(**row) for row in fixture["chunks"]]
    selected, proofs = compile_publication(original, raw, authority(raw), Words())
    source = Snapshot.read(raw)
    subjects = [
        chunk
        for chunk in selected
        if chunk.id in proofs and proofs[chunk.id]["basis"] == "certificate_subject"
    ]
    pairs = {
        (proofs[chunk.id]["document_ids"][0], proofs[chunk.id]["product_ids"][0])
        for chunk in subjects
    }
    expected = {
        (document["document_id"], pid)
        for document in raw["documents"]
        for pid in document["product_ids"]
    }
    assert len(expected) == len(pairs) == 55
    assert pairs == expected
    assert {chunk.lang for chunk in subjects} == {"en", "de"}
    issued = next(d for d in raw["documents"] if d["title"].startswith("EN 50549-2"))
    issued_units = [c for c in subjects if c.doc_sha256 == issued["blob_sha256"]]
    assert issued_units and all(
        "does not imply assessment of the production" in c.text for c in issued_units
    )

    iec = next(d for d in raw["documents"] if "IEC 62109" in d["title"])
    iec_original = next(c for c in original if c.doc_sha256 == iec["blob_sha256"])
    assert "1000" in iec_original.text and "Rated Output Power" in iec_original.text
    assert iec_original.id not in proofs
    iec_units = [c for c in subjects if c.doc_sha256 == iec["blob_sha256"]]
    assert len(iec_units) == 11
    assert all(
        "1000" not in c.text and "Rated Output Power" not in c.text for c in iec_units
    )

    corpus_dir = tmp_path / "corpus"
    corpus.write(
        corpus_dir,
        corpus.Meta(
            "eta-certificates",
            None,
            None,
            "actual indexed originals",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {k: p["product_ids"] for k, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                d["blob_sha256"],
                (d["url"],),
                d["title"],
                "",
                (),
                tuple(
                    p["model"]
                    for p in raw["products"]
                    if p["product_id"] in d["product_ids"]
                ),
                "certificate",
                d["lang"],
                3,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        selected,
    )
    index = tmp_path / "index.sqlite"
    store.export(corpus_dir, index)
    db = sqlite3.connect(index)
    try:
        meta = dict(db.execute("SELECT key,value FROM meta"))
        assert json.loads(meta["unprepared_documents"]) == []
        assert meta["preparation_complete"] == "true"
    finally:
        db.close()

    pid = next(
        p["product_id"] for p in raw["products"] if p["model"] == "GW10K-ETA-G20"
    )
    loaded = DocumentIndex(index, encoder=None)
    try:
        hits = loaded.search(
            "GW10K-ETA-G20 certificate",
            "en",
            [pid],
            k=20,
            neighbours=False,
            publication=source,
        )
        cert_hits = [h for h in hits if "-certificate-" in h.chunk_id]
        assert cert_hits and all(h.product_ids == (pid,) for h in cert_hits)
        assert all(
            "Vmax" not in h.text and "Rated Output Power" not in h.text for h in hits
        )
        assert all(
            "Firmware Version" not in h.text and "010101" not in h.text for h in hits
        )
        revoked = deepcopy(raw)
        for d in revoked["documents"]:
            d["product_ids"] = [value for value in d["product_ids"] if value != pid]
        assert not loaded.search(
            "GW10K-ETA-G20 certificate",
            "en",
            [pid],
            k=20,
            neighbours=False,
            publication=Snapshot.read(revoked),
        )
    finally:
        loaded.close()


def test_certificate_subject_rejects_unrelated_model_role_and_tampering() -> None:
    from linker_genie.certificate_scope import certificate_text

    fixture = json.loads(
        gzip.decompress((FIXTURES / "eta-certificates.json.gz").read_bytes())
    )
    raw = fixture["manifest"]
    raw["model_identity_revision"] = "fixture-identity-1"
    original = [Chunk(**row) for row in fixture["chunks"]]
    selected, proofs = compile_publication(original, raw, authority(raw), Words())
    chunk = next(
        c
        for c in selected
        if c.id in proofs and proofs[c.id]["basis"] == "certificate_subject"
    )
    proof = proofs[chunk.id]
    source = Snapshot.read(raw)
    pid = proof["product_ids"][0]
    assert authorize_chunk(
        chunk.doc_sha256,
        [pid],
        proof["associations"],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
    assert not authorize_chunk(
        chunk.doc_sha256,
        [pid],
        [],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
    changed = deepcopy(proof)
    changed["certificate_scope"]["source_text"] += " altered"
    assert not authorize_chunk(
        chunk.doc_sha256,
        [pid],
        proof["associations"],
        changed,
        products=source.products,
        documents=source.documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
    changed = deepcopy(raw)
    next(
        d for d in changed["documents"] if d["document_id"] == proof["document_ids"][0]
    )["role"] = "datasheet"
    changed_source = Snapshot.read(changed)
    assert not authorize_chunk(
        chunk.doc_sha256,
        [pid],
        proof["associations"],
        proof,
        products=changed_source.products,
        documents=changed_source.documents,
        chunk_id=chunk.id,
        text=chunk.text,
    )
    finite = next(c for c in original if "GWxxK-ETA-G20" in c.text)
    assert certificate_text(finite.text, "GW7K-ETA-G20") is None
    assert certificate_text(finite.text, "GW5K-ETA-G20-EXTRA") is None
    assert (
        certificate_text(
            finite.text + " The certificate does not cover GW5K-ETA-G20.",
            "GW5K-ETA-G20",
        )
        is None
    )
    eu = next(d for d in raw["documents"] if d["title"].startswith("EU declaration"))
    en = next(
        c for c in original if c.doc_sha256 == eu["blob_sha256"] and c.lang == "en"
    )
    de = next(
        c for c in original if c.doc_sha256 == eu["blob_sha256"] and c.lang == "de"
    )
    # The English page omits a hyphen in this model; the separate German
    # declaration is literal proof only for its own source page.
    assert certificate_text(en.text, "GW12K-ETA-G20") is None
    assert certificate_text(de.text, "GW12K-ETA-G20") is not None
    misleading = "The certificate of conformity refers to the above mentioned product. Product: GW5K-ETA-G20. For comparison GW8K-ETA-G20 is shown."
    assert certificate_text(misleading, "GW8K-ETA-G20") is None
    ambiguous_axes = (
        "Certificate No.: R 123 456 Product: GW5K-ETA-G20 Product: GW8K-ETA-G20"
    )
    assert certificate_text(ambiguous_axes, "GW8K-ETA-G20") is None

    limited = "Only GW8K-ETA-G20 models apply."
    digest = hashlib.sha256(f"text\0{limited}".encode()).hexdigest()[:8]
    prior = replace(
        finite,
        id=f"{finite.doc_sha256[:12]}-p1-{digest}",
        page=1,
        section="Only GW8K-ETA-G20",
        text=limited,
        source_headings=(),
    )
    _, limited_proofs = compile_publication(
        [prior, finite], raw, authority(raw), Words()
    )
    by_model = {
        p["certificate_scope"]["model"]
        for p in limited_proofs.values()
        if p.get("basis") == "certificate_subject"
        and p["certificate_scope"]["source_chunk_id"] == finite.id
    }
    assert "GW5K-ETA-G20" not in by_model
    assert "GW8K-ETA-G20" in by_model


@pytest.mark.parametrize(
    ("mixed_line", "forbidden"),
    [
        ("IEC 62109-1:2010, frequency 50 Hz", "50 Hz"),
        ("IEC 62109-1:2010/50Hz", "50Hz"),
        ("EN 50549-1:2019/5KW", "5KW"),
        ("IEC 62109-1:2010/12KG", "12KG"),
    ],
)
def test_certificate_mixed_standard_line_cannot_return_technical_values(
    tmp_path: Path,
    mixed_line: str,
    forbidden: str,
) -> None:
    """A standards line with a rating is not a certificate-only source excerpt."""
    fixture = json.loads(
        gzip.decompress((FIXTURES / "eta-certificates.json.gz").read_bytes())
    )
    raw = deepcopy(fixture["manifest"])
    raw["model_identity_revision"] = "fixture-identity-1"
    document = next(d for d in raw["documents"] if d["title"].startswith("EN 50549-2"))
    product = next(p for p in raw["products"] if p["model"] == "GW10K-ETA-G20")
    pid, did = product["product_id"], document["document_id"]
    raw["documents"] = [document]
    raw["products"] = [product]
    document["product_ids"] = [pid]
    product["documents"] = [did]
    chunk = next(
        Chunk(**c)
        for c in fixture["chunks"]
        if c["doc_sha256"] == document["blob_sha256"]
    )
    text = chunk.text.replace("EN 50549-2:2019+A1 EN 50549-10:2022", mixed_line)
    assert text != chunk.text
    digest = hashlib.sha256(f"text\0{text}".encode()).hexdigest()[:8]
    chunk = replace(
        chunk, id=f"{chunk.doc_sha256[:12]}-p{chunk.page}-{digest}", text=text
    )
    selected, proofs = compile_publication([chunk], raw, authority(raw), Words())
    units = [
        c
        for c in selected
        if c.id in proofs and proofs[c.id]["basis"] == "certificate_subject"
    ]
    assert units and all(forbidden not in c.text for c in units)

    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "mixed-standard",
            None,
            None,
            "synthetic certificate source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {k: p["product_ids"] for k, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                document["blob_sha256"],
                (document["url"],),
                document["title"],
                "",
                (),
                (product["model"],),
                "certificate",
                "en",
                1,
                "indexed",
            )
        ],
        [(pid, product["model"])],
        selected,
    )
    index = tmp_path / "index.sqlite"
    store.export(directory, index)
    loaded = DocumentIndex(index, encoder=None)
    try:
        hits = loaded.search(
            "GW10K-ETA-G20 certificate",
            "en",
            [pid],
            k=20,
            neighbours=False,
            publication=Snapshot.read(raw),
        )
        certificate_hits = [h for h in hits if "-certificate-" in h.chunk_id]
        assert certificate_hits
        assert all(forbidden not in h.text for h in hits)
    finally:
        loaded.close()


@pytest.mark.parametrize(
    ("language", "notice"),
    [
        ("en", "This certificate excludes GW5K-ETA-G20."),
        ("de", "Dieses Zertifikat gilt nicht für GW5K-ETA-G20."),
        ("de", "GW5K-ETA-G20 ist von diesem Zertifikat ausgenommen."),
        ("de", "GW5K-ETA-G20 ist nicht zertifiziert."),
        ("de", "GW5K-ETA-G20 ist nicht enthalten."),
        ("de", "GW5K-ETA-G20 ist nicht abgedeckt."),
    ],
)
def test_prior_certificate_exclusion_cannot_become_subject_proof(
    tmp_path: Path,
    language: str,
    notice: str,
) -> None:
    """An exclusion in an earlier authored chunk stays a denying boundary."""
    fixture = json.loads(
        gzip.decompress((FIXTURES / "eta-certificates.json.gz").read_bytes())
    )
    raw = deepcopy(fixture["manifest"])
    raw["model_identity_revision"] = "fixture-identity-1"
    document = next(
        d
        for d in raw["documents"]
        if d["title"].startswith("EU declaration" if language == "de" else "EN 50549-2")
    )
    product = next(p for p in raw["products"] if p["model"] == "GW5K-ETA-G20")
    pid, did = product["product_id"], document["document_id"]
    raw["documents"], raw["products"] = [document], [product]
    document["product_ids"], product["documents"] = [pid], [did]
    original = next(
        Chunk(**c)
        for c in fixture["chunks"]
        if c["doc_sha256"] == document["blob_sha256"] and c["lang"] == language
    )
    text = notice
    digest = hashlib.sha256(f"text\0{text}".encode()).hexdigest()[:8]
    prior = replace(
        original,
        id=f"{original.doc_sha256[:12]}-p1-{digest}",
        page=1,
        section="Notice",
        text=text,
        source_headings=(),
    )
    selected, proofs = compile_publication(
        [prior, original], raw, authority(raw), Words()
    )
    assert not any(p.get("basis") == "certificate_subject" for p in proofs.values())
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "excluded-subject",
            None,
            None,
            "synthetic certificate source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {k: p["product_ids"] for k, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                document["blob_sha256"],
                (document["url"],),
                document["title"],
                "",
                (),
                (product["model"],),
                "certificate",
                "en",
                1,
                "indexed",
            )
        ],
        [(pid, product["model"])],
        selected,
    )
    index = tmp_path / "index.sqlite"
    store.export(directory, index)
    loaded = DocumentIndex(index, encoder=None)
    try:
        hits = loaded.search(
            "GW5K-ETA-G20 certificate",
            "en",
            [pid],
            k=20,
            neighbours=False,
            publication=Snapshot.read(raw),
        )
        assert hits == []
    finally:
        loaded.close()


def test_certificate_ordinary_proof_cannot_expose_technical_rating(
    tmp_path: Path,
) -> None:
    """Generic certificate proof is not a path around the subject-only excerpt."""
    fixture = json.loads(
        gzip.decompress((FIXTURES / "eta-certificates.json.gz").read_bytes())
    )
    raw = deepcopy(fixture["manifest"])
    raw["model_identity_revision"] = "fixture-identity-1"
    document = next(d for d in raw["documents"] if d["title"].startswith("EN 50549-2"))
    product = next(p for p in raw["products"] if p["model"] == "GW5K-ETA-G20")
    pid, did = product["product_id"], document["document_id"]
    raw["documents"], raw["products"] = [document], [product]
    document["product_ids"], product["documents"] = [pid], [did]
    original = next(
        Chunk(**c)
        for c in fixture["chunks"]
        if c["doc_sha256"] == document["blob_sha256"]
    )
    text = (
        "Certificate No.: R 12345 0001 Product: GW5K-ETA-G20 Rated Output Power: 5 kW"
    )
    digest = hashlib.sha256(f"text\0{text}".encode()).hexdigest()[:8]
    original = replace(
        original,
        id=f"{original.doc_sha256[:12]}-p1-{digest}",
        page=1,
        text=text,
        source_headings=(),
    )
    selected, proofs = compile_publication([original], raw, authority(raw), Words())
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "certificate-rating",
            None,
            None,
            "synthetic certificate source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {k: p["product_ids"] for k, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                document["blob_sha256"],
                (document["url"],),
                document["title"],
                "",
                (),
                (product["model"],),
                "certificate",
                "en",
                1,
                "indexed",
            )
        ],
        [(pid, product["model"])],
        selected,
    )
    index = tmp_path / "index.sqlite"
    store.export(directory, index)
    loaded = DocumentIndex(index, encoder=None)
    try:
        hits = loaded.search(
            "GW5K-ETA-G20 certificate",
            "en",
            [pid],
            k=20,
            neighbours=False,
            publication=Snapshot.read(raw),
        )
        assert any("-certificate-" in hit.chunk_id for hit in hits)
        assert all(
            "5 kW" not in hit.text and "Rated Output Power" not in hit.text
            for hit in hits
        )
    finally:
        loaded.close()


def test_actual_legacy_certificates_keep_only_bound_safe_facts(tmp_path: Path) -> None:
    """Replay original certificates and their existing Woo associations."""
    fixture = json.loads(
        gzip.decompress((FIXTURES / "legacy-certificates.json.gz").read_bytes())
    )
    raw = fixture["manifest"]
    raw["model_identity_revision"] = "fixture-identity-1"
    originals = [Chunk(**row) for row in fixture["chunks"]]
    selected, proofs = compile_publication(originals, raw, authority(raw), Words())
    snapshot = Snapshot.read(raw)
    expected = {
        (document["document_id"], pid)
        for document in raw["documents"]
        for pid in document["product_ids"]
    }
    projected = {
        (p["document_ids"][0], p["product_ids"][0])
        for p in proofs.values()
        if p["basis"] in {"certificate_subject", "certificate_fragment"}
    }
    assert len(expected) == 29
    assert projected == expected

    # The DEKRA fragment is anchored to its actual same-page model list.
    fragment = next(
        c
        for c in selected
        if c.doc_sha256.startswith("2fa451ad7aae")
        and c.id in proofs
        and proofs[c.id]["basis"] == "certificate_fragment"
    )
    proof = proofs[fragment.id]
    pid = proof["product_ids"][0]
    assert authorize_chunk(
        fragment.doc_sha256,
        [pid],
        proof["certificate_fragment"]["origin_scope"]["associations"],
        proof,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=fragment.id,
        text=fragment.text,
    )
    changed = deepcopy(proof)
    changed["certificate_fragment"]["subject_anchor"]["text"] += " altered"
    assert not authorize_chunk(
        fragment.doc_sha256,
        [pid],
        proof["certificate_fragment"]["origin_scope"]["associations"],
        changed,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=fragment.id,
        text=fragment.text,
    )
    # Both SAJ language pages independently name the product; the LCIE
    # statement is linked to the model page by the same source certificate ID.
    emanager = [
        c
        for c in selected
        if c.doc_sha256.startswith("ced067135172")
        and c.id in proofs
        and proofs[c.id]["basis"] == "certificate_fragment"
    ]
    assert {c.lang for c in emanager} == {"en", "de"}
    assert all("eManager-C1 Pro" in c.text and "IP 65" not in c.text for c in emanager)
    lcie = next(
        c
        for c in selected
        if c.doc_sha256.startswith("00c7f5ee7b9f")
        and c.id in proofs
        and proofs[c.id]["basis"] == "certificate_fragment"
    )
    assert "validity of the present certificate is limited" in lcie.text
    lcie_proof = proofs[lcie.id]
    changed = deepcopy(lcie_proof)
    changed["certificate_fragment"]["registration_anchor"]["text"] += " altered"
    assert not authorize_chunk(
        lcie.doc_sha256,
        lcie_proof["product_ids"],
        lcie_proof["certificate_fragment"]["origin_scope"]["associations"],
        changed,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=lcie.id,
        text=lcie.text,
    )

    # An original legacy proof cannot authorize the technical source itself.
    original = next(c for c in originals if c.id == "d7b7f3908f84-p1-6d3f6d9f")
    original_proof = fixture["legacy_proof"]
    assert "Firmware Version : 010101" in original.text
    assert not authorize_chunk(
        original.doc_sha256,
        original_proof["product_ids"],
        original_proof["associations"],
        original_proof,
        products=snapshot.products,
        documents=snapshot.documents,
        chunk_id=original.id,
        text=original.text,
    )

    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "legacy-certificates",
            None,
            None,
            "actual indexed originals",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {k: p["product_ids"] for k, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                d["blob_sha256"],
                (d["url"],),
                d["title"],
                "",
                (),
                tuple(
                    p["model"]
                    for p in raw["products"]
                    if p["product_id"] in d["product_ids"]
                ),
                "certificate",
                d["lang"],
                4,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        selected,
    )
    index = tmp_path / "index.sqlite"
    store.export(directory, index)
    with sqlite3.connect(index) as db:
        meta = dict(db.execute("SELECT key,value FROM meta"))
        assert json.loads(meta["unprepared_documents"]) == []
    loaded = DocumentIndex(index, encoder=None)
    try:
        for model in ("GW5K-ETA-G20", "GM330", "GMK330", "GW125K-STS-G10"):
            target = next(p for p in raw["products"] if p["model"] == model)
            hits = loaded.search(
                f"{model} certificate",
                "en",
                [target["product_id"]],
                k=20,
                neighbours=False,
                publication=snapshot,
            )
            assert hits
            assert all(
                "Rated Output Power" not in hit.text
                and "Firmware Version" not in hit.text
                and "204.8V" not in hit.text
                for hit in hits
            )
        sts = next(p for p in raw["products"] if p["model"] == "GW125K-STS-G10")
        hits = loaded.search(
            "GW125K-STS-G10 Low Voltage",
            "en",
            [sts["product_id"]],
            k=20,
            neighbours=False,
            publication=snapshot,
        )
        assert any(
            "tested sample" in hit.text and "series-production" in hit.text
            for hit in hits
        )
        emanager_pid = next(
            p["product_id"] for p in raw["products"] if p["model"] == "eManager-C1 Pro"
        )
        for language, term in (("en", "responsibility"), ("de", "Verantwortung")):
            hits = loaded.search(
                "eManager-C1 Pro",
                language,
                [emanager_pid],
                k=20,
                neighbours=False,
                publication=snapshot,
            )
            assert any(term in hit.text and "IP 65" not in hit.text for hit in hits)
        lcie_pid = lcie_proof["product_ids"][0]
        hits = loaded.search(
            "EzManager3000 LCIE",
            "en",
            [lcie_pid],
            k=20,
            neighbours=False,
            publication=snapshot,
        )
        assert any(
            "validity of the present certificate is limited" in hit.text for hit in hits
        )
    finally:
        loaded.close()
