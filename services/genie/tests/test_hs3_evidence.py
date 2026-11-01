"""Three real SAJ originals bind a conditional statement to each Woo product."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest

from index.chunking import Chunk
from index.hs3_evidence import compile_hs3_evidence
from linker_genie.figures import tag
from linker_genie.hs3_evidence import (
    CERTIFICATE,
    DATA_MODELS,
    MANUAL_MODEL,
    SOURCES,
    conditional_answers,
    hs3_anchor_key,
    hs3_anchors,
    valid_hs3_scope,
    variants,
)
from linker_genie.publication import Snapshot

FIXTURE = (
    Path(__file__).parent / "fixtures/publication-compiler/hs3-conditional.json.gz"
)


class Words:
    def count(self, text: str) -> int:
        return len(text.split())

    def split(self, text: str, max_tokens: int) -> list[str]:
        return [text] if self.count(text) <= max_tokens else []


def inputs() -> tuple[list[Chunk], dict[str, Any], dict[str, str]]:
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as handle:
        fixture = json.load(handle)
    chunks = [Chunk(**row) for row in fixture["chunks"]]
    raw = fixture["manifest"]
    statuses = {p["model"].casefold(): "published" for p in raw["products"]}
    return chunks, raw, statuses


def anchors(chunks: list[Chunk]) -> dict[str, dict[str, Any]]:
    return hs3_anchors((c.id, c.doc_sha256, c.page, c.kind, c.text) for c in chunks)


def compiled() -> tuple[
    list[Chunk], dict[str, Any], Snapshot, dict[str, dict[str, Any]]
]:
    chunks, raw, statuses = inputs()
    snapshot = Snapshot.read(raw)
    units, scopes = compile_hs3_evidence(chunks, snapshot, statuses, Words(), 512)
    return units, scopes, snapshot, anchors(chunks)


def test_real_three_sources_prove_both_named_variants_conditionally() -> None:
    units, scopes, source, originals = compiled()
    assert len(units) == len(scopes) == 5
    assert len(originals) == 5
    for unit in units:
        scope = scopes[unit.id]
        pid = scope["product_ids"][0]
        model = source.products[pid]["model"]
        pair = variants(model)
        assert pair is not None
        assert all(variant in unit.text for variant in pair)
        assert model not in unit.text  # the DoC never literally lists W/G
        assert scope["basis"] == "hs3_conditional_certificate"
        assert valid_hs3_scope(
            scope,
            [pid],
            source.products,
            source.documents,
            sha=CERTIFICATE,
            chunk_id=unit.id,
            text=unit.text,
            anchors=originals,
        )
        tagged = tag(unit.id, unit.text)
        assert tagged.figures[unit.id + ".n1"] == "1"
        assert tagged.figures[unit.id + ".n8"] == "8"
        for lang, answer in conditional_answers(unit.id, model).items():
            assert lang in {"en", "de"}
            assert all(variant in answer for variant in pair)
            assert model not in answer
            assert "{fact:" + unit.id + ".n1}" in answer
            assert "{fact:" + unit.id + ".n8}" in answer
            assert "nameplate" in answer if lang == "en" else "Typenschild" in answer


@pytest.mark.parametrize("role", ["certificate", "datasheet", "manual"])
@pytest.mark.parametrize(
    "change", ["removed", "revision", "association", "product_link", "role"]
)
def test_each_original_and_current_product_association_is_required(
    role: str, change: str
) -> None:
    units, scopes, source, originals = compiled()
    unit = units[0]
    scope = scopes[unit.id]
    pid = scope["product_ids"][0]
    did = scope["hs3_conditional_certificate"]["source_documents"][role]["document_id"]
    docs = deepcopy(source.documents)
    products = deepcopy(source.products)
    if change == "removed":
        del docs[did]
    elif change == "revision":
        docs[did]["document_revision"] = "changed"
    elif change == "association":
        docs[did]["product_ids"].remove(pid)
    elif change == "role":
        docs[did]["role"] = "unrelated_purpose"
    else:
        products[pid]["documents"].remove(did)
    assert not valid_hs3_scope(
        scope,
        [pid],
        products,
        docs,
        sha=CERTIFICATE,
        chunk_id=unit.id,
        text=unit.text,
        anchors=originals,
    )


@pytest.mark.parametrize("missing", list(SOURCES))
def test_scope_snippet_without_any_original_chunk_fails(missing: str) -> None:
    units, scopes, source, originals = compiled()
    unit = units[0]
    scope = scopes[unit.id]
    pid = scope["product_ids"][0]
    del originals[hs3_anchor_key(missing)]
    assert not valid_hs3_scope(
        scope,
        [pid],
        source.products,
        source.documents,
        sha=CERTIFICATE,
        chunk_id=unit.id,
        text=unit.text,
        anchors=originals,
    )


def test_wrong_model_mutated_source_and_unavailable_identity_fail() -> None:
    chunks, raw, statuses = inputs()
    source = Snapshot.read(raw)
    bad = [
        replace(c, text=c.text.replace("W/G-PX", "W-PX")) if c.id == DATA_MODELS else c
        for c in chunks
    ]
    assert compile_hs3_evidence(bad, source, statuses, Words(), 512) == ([], {})
    wrong = deepcopy(raw)
    wrong["products"][0]["model"] = wrong["products"][0]["model"].replace(
        "-W/G-", "-W-"
    )
    out, _ = compile_hs3_evidence(chunks, Snapshot.read(wrong), statuses, Words(), 512)
    assert len(out) == 4
    pid = raw["products"][0]["product_id"]
    statuses[raw["products"][0]["model"].casefold()] = "unavailable"
    out, scopes = compile_hs3_evidence(chunks, source, statuses, Words(), 512)
    assert all(scopes[item.id]["product_ids"] != [pid] for item in out)
    assert variants("HS3-5K-T2-W/G-PX-BE") is None
    assert variants("HS3-50K-T2-W/G-PX") is None
    assert variants("HS3-5K-T2-W-PX") is None
    assert variants("HS3-5K-T2-G-PX") is None
    changed = [
        replace(c, text=c.text.replace("W: With a built-in", "G: With a built-in"))
        if c.id == MANUAL_MODEL
        else c
        for c in chunks
    ]
    assert compile_hs3_evidence(changed, source, statuses, Words(), 512) == ([], {})


def test_datasheet_model_column_requires_original_physical_span() -> None:
    chunks, raw, statuses = inputs()
    source = Snapshot.read(raw)
    original = next(chunk for chunk in chunks if chunk.id == DATA_MODELS)
    cells = deepcopy(original.source_cells)
    first = next(
        cell for cell in cells if cell["row_start"] == 0 and cell["col_start"] == 1
    )
    first["model_spans"][0]["char_start"] += 1
    changed = [
        replace(chunk, source_cells=cells) if chunk.id == DATA_MODELS else chunk
        for chunk in chunks
    ]
    units, scopes = compile_hs3_evidence(changed, source, statuses, Words(), 512)
    assert len(units) == 4
    assert all(scopes[unit.id]["product_ids"] != [2198] for unit in units)

    units, scopes, source, original_anchors = compiled()
    unit = next(item for item in units if scopes[item.id]["product_ids"] == [2198])
    forged = deepcopy(scopes[unit.id])
    forged["hs3_conditional_certificate"]["datasheet_axis"]["column"] = 2
    assert not valid_hs3_scope(
        forged,
        [2198],
        source.products,
        source.documents,
        sha=CERTIFICATE,
        chunk_id=unit.id,
        text=unit.text,
        anchors=original_anchors,
    )


def conditional_hit() -> tuple[dict[str, Any], str]:
    units, scopes, source, _ = compiled()
    unit = units[0]
    scope = scopes[unit.id]
    pid = scope["product_ids"][0]
    model = str(source.products[pid]["model"])
    tagged = tag(unit.id, unit.text)
    refs = scope["hs3_conditional_certificate"]["source_documents"]
    main = source.documents[refs["certificate"]["document_id"]]
    support = []
    for role, cid, page in (
        ("datasheet", DATA_MODELS, 2),
        ("manual", MANUAL_MODEL, 18),
    ):
        ref = refs[role]
        doc = source.documents[ref["document_id"]]
        support.append(
            {
                "chunk_id": cid,
                "document_id": ref["document_id"],
                "document_revision": ref["document_revision"],
                "doc_url": doc["url"],
                "title": doc["title"],
                "page": page,
            }
        )
    return {
        "chunk_id": unit.id,
        "doc_type": "certificate",
        "title": "EU Declaration of Conformity",
        "page": 1,
        "doc_url": main["url"],
        "document_id": main["document_id"],
        "document_revision": main["document_revision"],
        "product_ids": [pid],
        "product_models": [model],
        "text": tagged.text,
        "figures": tagged.figures,
        "supporting_documents": support,
        "conditional_certificate": True,
        "conditional_certificate_answers": conditional_answers(unit.id, model),
    }, unit.id


@pytest.mark.parametrize("language", ["en", "de"])
def test_only_used_unit_requires_complete_condition_and_three_source_links(
    language: Literal["en", "de"],
) -> None:
    from linker_genie.facts import collect
    from linker_genie.ground import check
    from linker_genie.hydrate import hydrate
    from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput

    hit, cid = conditional_hit()
    facts = collect("linker/search-knowledge", {"hits": [hit]})
    answer = hit["conditional_certificate_answers"][language]
    good = TurnOutput(
        language=language,
        blocks=[
            TextBlock(text=answer, refs=[cid]),
            TextBlock(text="A separate answer remains available.", refs=[]),
        ],
    )
    assert check(good, facts).ok
    result = hydrate(good, facts)
    assert isinstance(result.blocks[0], TextBlock)
    assert "{fact:" not in result.blocks[0].text
    links = [block for block in result.blocks if isinstance(block, DocumentBlock)]
    assert {block.url for block in links} == {
        hit["doc_url"] + "#page=1",
        *(s["doc_url"] + f"#page={s['page']}" for s in hit["supporting_documents"]),
    }
    wrong = good.model_copy(
        update={"blocks": [TextBlock(text="This model is certified.", refs=[cid])]}
    )
    assert not check(wrong, facts).ok
    support_only = good.model_copy(
        update={
            "blocks": [
                TextBlock(
                    text="This model is certified.",
                    refs=[hit["supporting_documents"][0]["chunk_id"]],
                )
            ]
        }
    )
    assert not check(support_only, facts).ok
    truncated = good.model_copy(
        update={"blocks": [TextBlock(text=answer.split(". ")[0] + ".", refs=[cid])]}
    )
    assert not check(truncated, facts).ok
    only_link = good.model_copy(update={"blocks": [DocumentBlock(ref=cid)]})
    assert not check(only_link, facts).ok
    unrelated = TurnOutput(
        language=language, blocks=[TextBlock(text="Another question can be answered.")]
    )
    assert check(unrelated, facts).ok


@pytest.mark.parametrize(
    "mutation",
    ["missing_flag", "missing_support", "edited_number", "edited_text", "bad_answer"],
)
def test_consumer_rejects_incomplete_or_changed_conditional_evidence(
    mutation: str,
) -> None:
    from linker_genie.facts import collect

    hit, cid = conditional_hit()
    if mutation == "missing_flag":
        del hit["conditional_certificate"]
    elif mutation == "missing_support":
        hit["supporting_documents"].pop()
    elif mutation == "edited_number":
        hit["figures"][cid + ".n8"] = "9"
    elif mutation == "edited_text":
        hit["text"] = hit["text"].replace("G-PX", "B-PX")
    else:
        hit["conditional_certificate_answers"]["en"] = "Unconditional certification."
    facts = collect("linker/search-knowledge", {"hits": [hit]})
    assert cid not in facts.chunk_ids
    assert cid not in facts.conditional_certificate_answers
