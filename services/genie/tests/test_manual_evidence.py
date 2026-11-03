"""Real cached manufacturer excerpts, current associations and retrieval fences."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_chunking import Words

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.manual_evidence import compile_manual_evidence
from index.table_compiler import _author_contexts
from linker_genie.manual_evidence import (
    evidence_id,
    subject_matches,
    valid_reviewed_manual,
)
from linker_genie.manual_evidence_records import RECORDS
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/reviewed-manual-evidence.json.gz"
)


def fixture() -> tuple[dict[str, Any], list[Chunk], dict[str, list[dict[str, Any]]]]:
    value = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    chunks = [Chunk(**item) for item in value["chunks"]]
    contexts = _author_contexts(chunks, Snapshot.read(value["manifest"]), {})
    return value["manifest"], chunks, contexts


def selected() -> tuple[dict[str, Any], list[Chunk], dict[str, Any]]:
    raw, original, contexts = fixture()
    units, proofs = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=contexts
    )
    for proof in proofs.values():
        proof["model_identity_revision"] = raw["model_identity_revision"]
    return raw, units, proofs


def test_reviewed_sources_obey_exact_model_and_finer_section_boundaries() -> None:
    raw, original, contexts = fixture()
    wrong = {
        "product_id": 999999,
        "product_revision": "foreign-revision",
        "model": "GW80K-ETR-G10",
        "documents": [],
    }
    raw["products"].append(wrong)
    german = next(d for d in raw["documents"] if d["blob_sha256"].startswith("26a505"))
    german["product_ids"].append(wrong["product_id"])
    units, proofs = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=contexts
    )
    assert any(
        proof["product_ids"] == [1946] and "Netz verbunden" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert not any(999999 in proof["product_ids"] for proof in proofs.values())
    assert any(
        proof["product_ids"] == [1185] and "elekeeper" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert any(
        proof["product_ids"] == [3573] and "fasten the hexagon nut" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )
    assert any(
        proof["product_ids"] == [6321] and "Locate the fault position" in unit.text
        for unit in units
        for proof in [proofs[unit.id]]
    )

    # Cover headings attached to a TOC table chunk (f4d53810d74c-p2-c0136c0d)
    # must survive across subsequent tables (docling:p3:#/tables/1) until p.16.
    esa_anchor = next(c for c in original if c.id == "f4d53810d74c-p2-c0136c0d")
    esa_toc_p3 = replace(
        esa_anchor,
        id="f4d53810d74c-p3-3db83bb6",
        page=3,
        source_table="docling:p3:#/tables/1",
        source_headings=(),
        text="| 5.6 Replacement of the Transformer |",
    )
    with_toc_p3 = [
        *original[:-1],
        esa_toc_p3,
        original[-1],
    ]
    toc_units, toc_proofs = compile_manual_evidence(
        with_toc_p3,
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts=_author_contexts(with_toc_p3, Snapshot.read(raw), {}),
    )
    assert any(
        proof["product_ids"] == [6321] and "Locate the fault position" in unit.text
        for unit in toc_units
        for proof in [toc_proofs[unit.id]]
    )

    # An unreviewed, finer author restriction cannot borrow a known reset.
    altered = deepcopy(contexts)
    altered["a470d6e1be68-p34-0abaea56"].append(
        {
            "kind": "declaration",
            "quote": "Only HS3-8K-T2-W/G-PX can use this procedure.",
            "source_chunk_id": "unreviewed-narrow-heading",
        }
    )
    _, constrained = compile_manual_evidence(
        original, Snapshot.read(raw), Words(), 512, restricted_contexts=altered
    )
    assert not any(
        proof["reviewed_manual"]["source_id"] == "a470d6e1be68-p34-0abaea56"
        for proof in constrained.values()
    )


def test_original_source_and_chapter_evidence_are_not_replaceable() -> None:
    raw, original, contexts = fixture()
    source = Snapshot.read(raw)
    source_id = "5cd104b9e006-p57-c749de81"
    altered = [
        replace(c, text=c.text + " Additional foreign-variant instruction.")
        if c.id == source_id
        else c
        for c in original
    ]
    _, scopes = compile_manual_evidence(
        altered, source, Words(), 512, restricted_contexts=contexts
    )
    assert not any(
        p["reviewed_manual"]["source_id"] == source_id for p in scopes.values()
    )
    altered = [
        replace(c, source_headings=("2.4 other subject",))
        if c.id == "5cd104b9e006-p57-3a05a42c"
        else c
        for c in original
    ]
    _, scopes = compile_manual_evidence(
        altered, source, Words(), 512, restricted_contexts=contexts
    )
    assert not any(
        p["reviewed_manual"]["source_id"] == source_id for p in scopes.values()
    )


def test_runtime_rejects_tampered_source_proof_and_revoked_association() -> None:
    raw, units, proofs = selected()
    unit = next(
        c
        for c in units
        if c.id.startswith("26a5052fc859") and "Netz verbunden" in c.text
    )
    proof = proofs[unit.id]
    source = Snapshot.read(raw)
    args = {
        "sha": unit.doc_sha256,
        "chunk_id": unit.id,
        "text": unit.text,
    }
    assert valid_reviewed_manual(proof, proof["product_ids"], source.products, **args)
    assert authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
    )
    altered = deepcopy(proof)
    altered["reviewed_manual"]["anchor_text"] += " GW80K-ETR-G10"
    assert not valid_reviewed_manual(
        altered, proof["product_ids"], source.products, **args
    )
    assert not authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        [],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
    )


def test_sqlite_search_returns_the_manual_passage_then_honours_withdrawal(
    tmp_path: Path,
) -> None:
    raw, units, proofs = selected()
    source_dir = tmp_path / "corpus"
    corpus.write(
        source_dir,
        corpus.Meta(
            "reviewed-manual",
            None,
            None,
            "cached manufacturer source",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {
                    cid: proof["product_ids"] for cid, proof in proofs.items()
                },
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
                (),
                "manual",
                "en",
                100,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        units,
    )
    target = tmp_path / "index.sqlite"
    store.export(source_dir, target)
    loaded = DocumentIndex(target, encoder=None)
    try:
        hits = loaded.search(
            "Netzeinspeisung Eigenverbrauch",
            "de",
            [1946],
            publication=Snapshot.read(raw),
        )
        assert any("Netz verbunden" in hit.text and hit.page == 7 for hit in hits)
        hits = loaded.search(
            "elekeeper monitoring", "en", [1185], publication=Snapshot.read(raw)
        )
        assert any("elekeeper" in hit.text and hit.page == 34 for hit in hits)
        hits = loaded.search(
            "fault localization alarm", "en", [6321], publication=Snapshot.read(raw)
        )
        assert any(
            "Locate the fault position" in hit.text and hit.page == 16 for hit in hits
        )
        revoked = deepcopy(raw)
        for document in revoked["documents"]:
            if document["blob_sha256"].startswith("26a5052fc859"):
                document["product_ids"].remove(1946)
        assert not loaded.search(
            "Netzeinspeisung Eigenverbrauch",
            "de",
            [1946],
            publication=Snapshot.read(revoked),
        )
    finally:
        loaded.close()


# The complete original chunks behind the GW112.6-BAT-AC-G10 (0ef4b1ccdcc4)
# and CB2-(57.3K-100.3K)-HV5 (a70cb4c39824) records; each text must hash to the
# digest pinned in RECORDS.
GW112_ANCHOR = "0ef4b1ccdcc4-p55-94f821cd"
GW112_SOURCE = "0ef4b1ccdcc4-p29-157fe376"
CB2_COVER = "a70cb4c39824-p1-954eb9fe"
CB2_SPACE = "a70cb4c39824-p1-632eb7c1"
CB2_SPACE_RESET = "a70cb4c39824-p1-baa186e3"
CB2_STARTUP = "a70cb4c39824-p20-c67a91ad"
ORIGINAL_TEXTS = {
    GW112_ANCHOR: (
        "| No. | Model | PACK Quantity | Rated Capacity (kWh) |\n"
        "| 1 | GW92.1-BAT-AC-G10 | 9 | 92.1 |\n"
        "| 2 | GW102.4-BAT-AC-G10 | 10 | 102.4 |\n"
        "| 3 | GW112.6-BAT-AC-G10 | 11 | 112.6 |"
    ),
    GW112_SOURCE: (
        "BAT-C 92.1-112.6kWh, BAT-C 208.9kWh ·\n"
        "The battery has a built-in Ezlink module. Each inverter is connected to the "
        "battery system through an intelligent communication stick, and the battery "
        "system transmits the parallel information to the smart energy control box. ○\n"
        "BAT-S 51.2-56.3kWh ·\n"
        "The battery does not have a built-in Ezlink module. Each inverter transmits "
        "the information of a single inverter to the smart energy control box through "
        "an intelligent communication stick. ○"
    ),
    CB2_COVER: (
        "This quick installation guide is applicable for the installation of "
        "CB2-(57.3K-100.3K)-HV5. For detailed instructions, refer to the User Manual."
    ),
    CB2_SPACE_RESET: "Dimensions of the CB2 battery cabinet:",
    CB2_SPACE: (
        "The cabinet can be installed either indoors or outdoors. Reserve at least "
        "the following space around the whole battery system to ensure good air "
        "circulation at the installation area:"
    ),
    CB2_STARTUP: (
        "Step 1. Turn ON the DC switches on the inverter.\n"
        "Step 2. Turn on the AC circuit breaker.\n"
        "Step 3. Rotate the main switch to the ON position.\n"
        "Step 4. Press and hold the START button for 3 seconds until the LED light "
        "flashes in green.\n"
        "Note: If the main switch suddenly trips while the machine is running, "
        "rotate the switch to OFF and then back to ON.\n"
        "5. Check the battery status on Elekeeper App\n"
        "Step 1. Log in to the Elekeeper App, and check the Battery Info at the "
        "Elekeeper App. Make sure that the numbers of battery clusters and battery "
        "modules are as expected for each battery group."
    ),
}
GW112_MODEL = "GW112.6-BAT-AC-G10"
CB2_MODELS = ("CB2-57.3-HV5", "CB2-71.6-HV5", "CB2-85.9-HV5", "CB2-100.3-HV5")
REVIEWED_PRODUCTS: dict[int, dict[str, Any]] = {
    1955: {"model": GW112_MODEL},
    **{
        pid: {"model": model}
        for pid, model in zip((4103, 4104, 4105, 4106), CB2_MODELS, strict=True)
    },
}


def reviewed_records() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bat_ac = next(r for r in RECORDS if r["source_id"] == GW112_SOURCE)
    cb2 = [r for r in RECORDS if r["sha256"].startswith("a70cb4c3")]
    assert len(cb2) == 2
    return bat_ac, cb2


def reviewed_scope(record: dict[str, Any], pid: int, model: str) -> dict[str, Any]:
    """Rebuild the runtime proof exactly as the compiler would serialize it."""
    proof: dict[str, Any] = {
        "product_id": pid,
        "model": model,
        "source_sha256": record["sha256"],
        "source_page": record["source_page"],
        "source_section": record["source_section"],
        "source_id": record["source_id"],
        "source_text": ORIGINAL_TEXTS[record["source_id"]],
        "anchor_id": record["anchor_id"],
        "anchor_text": ORIGINAL_TEXTS[record["anchor_id"]],
    }
    required = {record["anchor_id"], record["source_id"]}
    reset = record.get("reviewed_reset")
    if reset:
        proof["clearance"] = {
            "reset_id": reset["id"],
            "reset_text": ORIGINAL_TEXTS[reset["id"]],
            "cleared_texts": [
                ORIGINAL_TEXTS[item["boundary"]["source_chunk_id"]]
                for item in reset["cleared"]
            ],
        }
        required.add(reset["id"])
        required.update(
            item["boundary"]["source_chunk_id"] for item in reset["cleared"]
        )
    return {
        "product_ids": [pid],
        "basis": "reviewed_manual",
        "source_chunk_ids": sorted(required),
        "document_ids": [f"doc-{record['sha256'][:12]}"],
        "reviewed_manual": proof,
    }


def reviewed_valid(
    record: dict[str, Any], pid: int, model: str, candidate: dict[str, Any]
) -> bool:
    """Validate one candidate proof against its record's pinned identity."""
    text = str(record["excerpt"])
    cid = evidence_id(
        str(record["sha256"]),
        int(record["source_page"]),
        model,
        str(record["source_id"]),
        text,
    )
    return valid_reviewed_manual(
        candidate,
        [pid],
        REVIEWED_PRODUCTS,
        sha=str(record["sha256"]),
        chunk_id=cid,
        text=text,
    )


def test_gw112_and_cb2_records_match_their_published_subjects() -> None:
    bat_ac, cb2 = reviewed_records()
    assert subject_matches(bat_ac, GW112_MODEL)
    assert subject_matches(bat_ac, "GW92.1-BAT-AC-G10")
    assert not subject_matches(bat_ac, "GW208.9-BAT-LC-G10")
    for record in cb2:
        for model in CB2_MODELS:
            assert subject_matches(record, model)
        assert not subject_matches(record, "CB2-100.4-HV5")
        assert not subject_matches(record, "BU3-5.0-TV2-PRO")


@pytest.mark.parametrize(
    "pid,model",
    [
        (1955, GW112_MODEL),
        *zip((4103, 4104, 4105, 4106), CB2_MODELS, strict=True),
    ],
)
def test_reviewed_manual_validates_and_rejects_tampering(pid: int, model: str) -> None:
    bat_ac, cb2 = reviewed_records()
    for record in [bat_ac] if model == GW112_MODEL else cb2:
        scope = reviewed_scope(record, pid, model)

        def validates(
            candidate: dict[str, Any], *, proof: dict[str, Any] = record
        ) -> bool:
            return reviewed_valid(proof, pid, model, candidate)

        assert validates(scope)
        anchor = deepcopy(scope)
        anchor["reviewed_manual"]["anchor_text"] += " GW80K-ETR-G10"
        assert not validates(anchor)
        source = deepcopy(scope)
        source["reviewed_manual"]["source_text"] += " Extra unreviewed sentence."
        assert not validates(source)
        if "clearance" in scope["reviewed_manual"]:
            reset = deepcopy(scope)
            reset["reviewed_manual"]["clearance"]["reset_text"] += " changed"
            assert not validates(reset)
            cleared = deepcopy(scope)
            cleared["reviewed_manual"]["clearance"]["cleared_texts"][0] += " changed"
            assert not validates(cleared)
            without = deepcopy(scope)
            del without["reviewed_manual"]["clearance"]
            assert not validates(without)
        else:
            forged = deepcopy(scope)
            forged["reviewed_manual"]["clearance"] = {
                "reset_id": CB2_SPACE_RESET,
                "reset_text": ORIGINAL_TEXTS[CB2_SPACE_RESET],
                "cleared_texts": [ORIGINAL_TEXTS[CB2_COVER]],
            }
            assert not validates(forged)
        foreign = deepcopy(scope)
        foreign["reviewed_manual"]["model"] = "BU3-5.0-TV2-PRO"
        foreign["product_ids"] = [999999]
        assert not reviewed_valid(record, 999999, "BU3-5.0-TV2-PRO", foreign)
