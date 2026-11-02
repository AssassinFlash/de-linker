"""SAJ original policy and datasheet support a conditional claims procedure."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.publication import ScopeProof, compile_publication
from index.table_compiler import external_axis_anchors
from linker_genie.compatibility_physical import translate_compatibility_condition
from linker_genie.hs3_warranty_terms import (
    BU3_NOTE_ITEMS,
    BU3_SOURCES,
    POLICY,
    valid_scope,
)
from linker_genie.hs3_warranty_terms import (
    anchors as warranty_anchors,
)
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex
from linker_genie.warranty_scope import procedure_series_matches, series_matches

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/hs3-conditional-warranty.json.gz"
)
HS3 = {1185, 1186, 1187, 2198, 2199}


def fixture() -> tuple[dict[str, Any], list[Chunk]]:
    value = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    return value["manifest"], [Chunk(**row) for row in value["chunks"]]


def test_saj_five_current_models_get_only_the_conditional_claims_procedure() -> None:
    raw, original = fixture()
    units, scopes = compile_publication(original, raw, authority(raw), Words())
    procedures = [
        (unit, scopes[unit.id])
        for unit in units
        if unit.id in scopes and scopes[unit.id]["basis"] == "warranty_procedure"
    ]
    assert {scope["product_ids"][0] for _, scope in procedures} == HS3
    assert len(procedures) == len(HS3)
    assert all(
        unit.page == 4
        and "distributor or installer" in unit.text
        and "10 years" not in unit.text
        and scope["warranty_scope"]["conditional"] is True
        for unit, scope in procedures
    )
    assert [
        scope["product_ids"]
        for scope in scopes.values()
        if scope["basis"] == "warranty_terms"
    ] == [[2093]]
    assert not any(scope["product_ids"] == [2093] for _, scope in procedures)


def test_series_exception_never_crosses_foreign_model_or_promotes_terms() -> None:
    assert procedure_series_matches(
        "HS3 Series", ("hs3", "5", "12"), "HS3-5K-T2-W/G-PX"
    )
    assert not series_matches("HS3 Series", ("hs3", "5", "12"))
    assert not procedure_series_matches(
        "HS3 Series", ("hs3", "5", "12"), "BU3-5.0-TV2-PRO"
    )
    assert not procedure_series_matches(
        "ESA Series", ("esa", "5", "30"), "GW10K-ETA-G20"
    )
    assert not procedure_series_matches(
        "AS3 Series", ("hs3", "5", "12"), "HS3-5K-T2-W/G-PX"
    )


def test_sqlite_claims_procedure_retrieval_and_two_source_withdrawals(
    tmp_path: Path,
) -> None:
    raw, original = fixture()
    units, scopes = compile_publication(original, raw, authority(raw), Words())
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "hs3-conditional-claims",
            None,
            None,
            "cached manufacturer source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in scopes.items()},
                "chunk_scopes": scopes,
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
                d["type"],
                "en",
                max(c.page for c in original if c.doc_sha256 == d["blob_sha256"]),
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        units,
    )
    index_path = tmp_path / "index.sqlite"
    store.export(directory, index_path)
    index = DocumentIndex(index_path, encoder=None)
    try:

        def procedures(snapshot: dict[str, Any], pid: int) -> list[Any]:
            return [
                hit
                for hit in index.search(
                    "distributor installer warranty claim",
                    "en",
                    [pid],
                    publication=Snapshot.read(snapshot),
                )
                if hit.warranty_procedure
            ]

        for pid in HS3:
            hits = procedures(raw, pid)
            assert hits and all(h.page == 4 and h.product_ids == (pid,) for h in hits)
            assert all("does not establish coverage" in h.scope_note for h in hits)
            assert all("10 years" not in h.text for h in hits)
        assert not procedures(raw, 2093)
        unprepared = index.loaded()["unprepared_documents"]
        policy = next(
            d for d in raw["documents"] if d["blob_sha256"].startswith("be0569")
        )
        assert all(
            any(
                row["document_id"] == policy["document_id"] and row["product_id"] == pid
                for row in unprepared
            )
            for pid in HS3
        )
        assert not any(
            row["document_id"] == policy["document_id"] and row["product_id"] == 2093
            for row in unprepared
        )
        assert index.loaded()["preparation_complete"] is False

        for prefix in ("be0569", "fb371d"):
            revoked = deepcopy(raw)
            for document in revoked["documents"]:
                if document["blob_sha256"].startswith(prefix):
                    document["product_ids"].remove(1185)
            assert not procedures(revoked, 1185)
    finally:
        index.close()


def bu3_unit(
    chunks: list[Chunk] | None = None, raw: dict[str, Any] | None = None
) -> tuple[Chunk, ScopeProof, Snapshot, list[Chunk], dict[str, dict[str, Any]]]:
    if chunks is None or raw is None:
        raw, chunks = fixture()
    source = Snapshot.read(raw)
    units, scopes = compile_publication(chunks, raw, authority(raw), Words())
    unit = next(
        c
        for c in units
        if c.id in scopes
        and scopes[c.id]["basis"] == "warranty_terms"
        and scopes[c.id]["product_ids"] == [2093]
    )
    proof = scopes[unit.id]
    external = external_axis_anchors(chunks)
    external.update(
        warranty_anchors((c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks)
    )
    return unit, proof, source, chunks, external


@pytest.mark.parametrize("tampered", list(BU3_SOURCES))
def test_bu3_terms_reject_tampered_policy_anchor_text(tampered: str) -> None:
    raw, original = fixture()
    unit, proof, source, _, external = bu3_unit(original, raw)
    assert valid_scope(
        proof,
        [2093],
        source.products,
        source.documents,
        sha=POLICY,
        chunk_id=unit.id,
        text=unit.text,
        external_axis_anchors=external,
    )
    altered = [
        replace(c, text=c.text + " altered") if c.id == tampered else c
        for c in original
    ]
    out, out_scopes = compile_publication(altered, raw, authority(raw), Words())
    assert not any(
        c.id in out_scopes
        and out_scopes[c.id]["basis"] == "warranty_terms"
        and out_scopes[c.id]["product_ids"] == [2093]
        for c in out
    ), tampered
    changed = external_axis_anchors(altered)
    changed.update(
        warranty_anchors((c.id, c.doc_sha256, c.page, c.kind, c.text) for c in altered)
    )
    assert not valid_scope(
        proof,
        [2093],
        source.products,
        source.documents,
        sha=POLICY,
        chunk_id=unit.id,
        text=unit.text,
        external_axis_anchors=changed,
    ), tampered


@pytest.mark.parametrize("change", ["association", "product_link", "revision", "role"])
def test_bu3_terms_reject_revoked_policy_association(change: str) -> None:
    raw, original = fixture()
    unit, proof, source, _, external = bu3_unit(original, raw)
    changed = deepcopy(raw)
    policy = next(d for d in changed["documents"] if d["blob_sha256"] == POLICY)
    product = next(p for p in changed["products"] if p["product_id"] == 2093)
    if change == "association":
        policy["product_ids"].remove(2093)
    elif change == "product_link":
        product["documents"].remove(policy["document_id"])
    elif change == "revision":
        policy["document_revision"] += "-changed"
    else:
        policy["role"] = "document"
    revoked = Snapshot.read(changed)
    assert not valid_scope(
        proof,
        [2093],
        revoked.products,
        revoked.documents,
        sha=POLICY,
        chunk_id=unit.id,
        text=unit.text,
        external_axis_anchors=external,
    ), change
    out, out_scopes = compile_publication(
        original, changed, authority(changed), Words()
    )
    if change == "revision":
        # A revision bump re-binds the proof to the current policy revision;
        # only the stale proof above is invalidated, not the fresh build.
        fresh = next(
            c
            for c in out
            if c.id in out_scopes
            and out_scopes[c.id]["basis"] == "warranty_terms"
            and out_scopes[c.id]["product_ids"] == [2093]
        )
        assert (
            out_scopes[fresh.id]["warranty_scope"]["source_documents"]["policy"][
                "document_revision"
            ]
            == policy["document_revision"]
        )
    else:
        assert not any(
            c.id in out_scopes
            and out_scopes[c.id]["basis"] == "warranty_terms"
            and out_scopes[c.id]["product_ids"] == [2093]
            for c in out
        ), change


def test_bu3_notes_translate_to_reviewed_german_conditions() -> None:
    for index, (cid, page, note) in enumerate(BU3_NOTE_ITEMS, 1):
        quote = f"*{index}: {note}"
        translated = translate_compatibility_condition(quote, cid, page, "en")
        assert translated is not None, index
        assert translate_compatibility_condition(quote + " ", cid, page, "en") is None
        assert translate_compatibility_condition(quote, cid, page + 1, "en") is None
        assert translate_compatibility_condition(quote, cid, page, "de") is None
    capacity = translate_compatibility_condition(
        f"*3: {BU3_NOTE_ITEMS[2][2]}", BU3_NOTE_ITEMS[2][0], 2, "en"
    )
    assert capacity is not None
    assert "60 % der Nennenergie" in capacity
    assert "6000 Lade-/Entladezyklen" in capacity
    minimum = translate_compatibility_condition(
        f"*6: {BU3_NOTE_ITEMS[5][2]}", BU3_NOTE_ITEMS[5][0], 3, "en"
    )
    assert minimum is not None
    assert minimum == "Für BU3 nennt die Tabelle N = 5,5 Jahre."
