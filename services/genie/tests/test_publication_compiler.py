"""Current-model answer units from original H2/HS2/HS3 Docling provenance."""

from __future__ import annotations

import gzip
import hashlib
import json
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
from index.extract import Page, enrich_model_axes, pages_of
from index.inventory import doc_type_of
from index.publication import ScopeProof, compile_publication, scope_proofs
from linker_genie.figures import tag
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex

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
