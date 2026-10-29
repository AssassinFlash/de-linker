"""Policy values and cover families must agree with the original sources."""

import gzip
import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_chunking import Words
from test_publication_compiler import warranty_fixture

from index.chunking import Chunk
from index.publication import ScopeProof
from index.table_compiler import external_axis_anchors
from index.warranty import _family_cover, compile_procedures, compile_terms
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.warranty_scope import terms_id


def _procedures(
    raw: dict[str, Any],
    original: list[Chunk],
    model: Chunk,
    model_scope: ScopeProof,
    restricted: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[list[Chunk], dict[str, ScopeProof]]:
    return compile_procedures(
        original,
        [model],
        {model.id: model_scope},
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts=restricted or {},
    )


def _allowed(
    chunk: Chunk,
    proof: ScopeProof,
    source: Snapshot,
    anchors: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return authorize_chunk(
        chunk.doc_sha256,
        proof["product_ids"],
        proof["associations"],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=chunk.id,
        text=chunk.text,
        external_axis_anchors=anchors,
        require_table_anchor=True,
    )


def test_policy_cell_must_match_whole_native_row_at_compile_and_authorization() -> None:
    raw, original, model, model_scope = warranty_fixture()
    source = Snapshot.read(raw)
    procedures, procedure_scopes = _procedures(raw, original, model, model_scope)
    terms, scopes = compile_terms(
        original, procedures, procedure_scopes, Words(), 512, restricted_contexts={}
    )
    legitimate = next(c for c in terms if c.lang == "en" and "10 years" in c.text)
    valid_proof = deepcopy(scopes[legitimate.id])
    original_anchors = external_axis_anchors(original)
    assert _allowed(legitimate, valid_proof, source, original_anchors)
    legacy = deepcopy(valid_proof)
    del legacy["warranty_scope"]["policy"]["term_row"]["fragments"]
    assert _allowed(legitimate, legacy, source, original_anchors)

    native = next(c for c in original if c.id == "a786dcf5aeef-p1-b113c4fc")
    cells = deepcopy(native.source_cells)
    period = next(c for c in cells if c["row_start"] == 1 and c["col_start"] == 0)
    assert period["text"] == "10 years *limited warranty"
    period["text"] = "0 years *limited warranty"
    changed = [
        replace(c, source_cells=cells) if c.id == native.id else c for c in original
    ]
    anchors = external_axis_anchors(changed)
    assert native.text == next(c for c in changed if c.id == native.id).text

    # The independent anchor is built from the same parsed cells; only the
    # unchanged native row reveals that the parser supplied a partial value.
    procedures, procedure_scopes = _procedures(raw, changed, model, model_scope)
    terms, scopes = compile_terms(
        changed, procedures, procedure_scopes, Words(), 512, restricted_contexts={}
    )
    assert not any("| Warranty / Garantie | 0 years" in c.text for c in terms)
    assert any(
        c.lang == "de" and _allowed(c, scopes[c.id], source, anchors) for c in terms
    )

    # Use the original valid proof, then update every derived value to the
    # parsed disagreement; authorization must also reject a stored projection.
    forged = valid_proof
    evidence = forged["warranty_scope"]
    policy = evidence["policy"]
    policy["term_row"]["cells"] = list(cells)
    policy["row_quote"] = policy["row_quote"].replace("10 years", "0 years", 1)
    wrong = legitimate.text.replace("10 years", "0 years", 1)
    evidence["text_sha256"] = hashlib.sha256(wrong.encode()).hexdigest()
    fake = replace(
        legitimate,
        text=wrong,
        id=terms_id(
            legitimate.doc_sha256,
            legitimate.page,
            evidence["model"],
            evidence["source_chunk_id"],
            wrong,
        ),
    )
    assert not _allowed(fake, forged, source, anchors)


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        (1, "on/after 1 st January 2026"),
        (2, "Different product category"),
        (
            3,
            "ESA 5-30k series with an additional unverified product",
        ),
    ],
)
def test_all_four_policy_columns_must_agree_with_native_row(
    column: int, replacement: str
) -> None:
    raw, original, model, model_scope = warranty_fixture()
    native = next(c for c in original if c.id == "a786dcf5aeef-p1-b113c4fc")
    cells = deepcopy(native.source_cells)
    next(c for c in cells if c["row_start"] == 1 and c["col_start"] == column)[
        "text"
    ] = replacement
    changed = [
        replace(c, source_cells=cells) if c.id == native.id else c for c in original
    ]
    procedures, procedure_scopes = _procedures(raw, changed, model, model_scope)
    terms, scopes = compile_terms(
        changed, procedures, procedure_scopes, Words(), 512, restricted_contexts={}
    )
    assert not any(c.lang == "en" for c in terms)
    source = Snapshot.read(raw)
    anchors = external_axis_anchors(changed)
    assert any(
        c.lang == "de" and _allowed(c, scopes[c.id], source, anchors) for c in terms
    )


def test_split_policy_row_requires_each_original_fragment_in_order() -> None:
    path = (
        Path(__file__).parent / "fixtures/publication-compiler/warranty-current.json.gz"
    )
    fixture = json.loads(gzip.decompress(path.read_bytes()))
    raw = fixture["manifest"]
    original = [Chunk(**item) for item in fixture["original"]]
    compiled = [Chunk(**item) for item in fixture["compiled"]]
    source = Snapshot.read(raw)
    procedures, procedure_scopes = compile_procedures(
        original,
        compiled,
        fixture["scopes"],
        source,
        Words(),
        512,
        restricted_contexts={},
    )
    terms, scopes = compile_terms(
        original, procedures, procedure_scopes, Words(), 512, restricted_contexts={}
    )
    anchors = external_axis_anchors(original)
    assert {(scopes[c.id]["product_ids"][0], c.lang) for c in terms} == {
        (pid, lang) for pid in source.products for lang in ("en", "de")
    }
    assert all(_allowed(c, scopes[c.id], source, anchors) for c in terms)
    term = next(
        c
        for c in terms
        if c.lang == "en"
        and scopes[c.id]["product_ids"] == [1946]
        and "produced before" in c.text
    )
    proof = scopes[term.id]
    fragments = proof["warranty_scope"]["policy"]["term_row"]["fragments"]
    assert len(fragments) == 2
    assert _allowed(term, proof, source, anchors)
    changed = deepcopy(proof)
    changed["warranty_scope"]["policy"]["term_row"]["fragments"].pop()
    assert not _allowed(term, changed, source, anchors)
    changed = deepcopy(proof)
    changed["warranty_scope"]["policy"]["term_row"]["fragments"][1]["rows"][1] = 4
    assert not _allowed(term, changed, source, anchors)
    changed = deepcopy(proof)
    del changed["warranty_scope"]["policy"]["term_row"]["fragments"]
    assert not _allowed(term, changed, source, anchors)


def _cover_fragment(cover: Chunk, text: str) -> Chunk:
    digest = hashlib.sha256(("text\0" + text).encode()).hexdigest()[:8]
    return replace(
        cover,
        id=f"{cover.doc_sha256[:12]}-p1-{digest}",
        section="",
        text=text,
        source_pdf_cover=None,
    )


@pytest.mark.parametrize(
    "text",
    [
        "ESA Series 3-10kW combined with BAT Series battery",
        "BAT Series battery combined with ESA Series 3-10kW",
        "ESA Series Residential Energy Storage System 3-10kW and BAT Series battery",
    ],
)
@pytest.mark.parametrize("restricted", [False, True])
def test_mixed_family_conflict_across_cover_chunks_rejects_procedure(
    text: str, restricted: bool
) -> None:
    raw, original, model, model_scope = warranty_fixture()
    cover = next(
        c for c in original if c.doc_sha256 == model.doc_sha256 and c.page == 1
    )
    conflict = _cover_fragment(cover, text)
    assert _family_cover([cover, conflict]) is None
    contexts = (
        {conflict.id: [{"kind": "heading", "quote": "other model"}]}
        if restricted
        else {}
    )
    procedures, _ = _procedures(
        raw, [*original, conflict], model, model_scope, contexts
    )
    assert not procedures


@pytest.mark.parametrize(
    "text",
    [
        "ESA Series 5-30kW combined with BAT Series battery",
        "ESA Series 5-30kW combined with BAT Series 3-10kW battery",
        "BAT Series 3-10kW battery combined with ESA Series 5-30kW",
    ],
)
def test_unrelated_family_does_not_create_a_conflict(text: str) -> None:
    raw, original, model, model_scope = warranty_fixture()
    cover = next(
        c for c in original if c.doc_sha256 == model.doc_sha256 and c.page == 1
    )
    addition = _cover_fragment(cover, text)
    family = _family_cover([cover, addition])
    assert family is not None
    assert family[1] == ("esa", "5", "3E+1")
    procedures, _ = _procedures(raw, [*original, addition], model, model_scope)
    assert {c.lang for c in procedures} == {"en", "de"}
