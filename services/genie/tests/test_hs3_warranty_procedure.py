"""SAJ original policy and datasheet support a conditional claims procedure."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.publication import compile_publication
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
    assert not any(scope["basis"] == "warranty_terms" for scope in scopes.values())
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
        assert index.loaded()["preparation_complete"] is False

        for prefix in ("be0569", "fb371d"):
            revoked = deepcopy(raw)
            for document in revoked["documents"]:
                if document["blob_sha256"].startswith(prefix):
                    document["product_ids"].remove(1185)
            assert not procedures(revoked, 1185)
    finally:
        index.close()
