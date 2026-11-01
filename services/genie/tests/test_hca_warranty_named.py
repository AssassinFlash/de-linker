"""Manufacturer Rev 1.2 parsed source; the Woo link here is simulated only."""

from __future__ import annotations

import gzip
import json
from copy import deepcopy
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from test_chunking import Words
from test_publication import authority

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.inventory import doc_type_of
from index.publication import compile_publication
from index.table_compiler import _author_contexts, external_axis_anchors
from index.warranty_named import compile_named_terms
from linker_genie.cycle import _hydrate_priced, _restore_qualified, run
from linker_genie.facts import TurnFacts, collect
from linker_genie.ground import check
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch
from linker_genie.language import language_failure
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.route import Route
from linker_genie.schema import (
    DocumentBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import _warranty_period_fallback, seal
from linker_genie.warranty_named import render_named_terms
from linker_genie.warranty_named_de import (
    EXCLUSIONS,
    german_named_answers,
    qualified_named_additions,
)

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/hca-rev12-simulated-association.json.gz"
)
NEW = "88a8a5bd9e70bc398fe990069272526c660c1731103ff113e53f93f7fd789307"
OLD = "9f5b0d2b24306f95fe7ac1f3892a98e0b4799f99b26508c063dc88be3d75aace"
PIDS = {3557, 3586, 3587}


def fixture() -> tuple[dict[str, Any], list[Chunk]]:
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    assert data["notice"].startswith("SIMULATED")
    return data["manifest"], [Chunk(**item) for item in data["chunks"]]


def compiled() -> tuple[dict[str, Any], list[Chunk], dict[str, Any]]:
    raw, original = fixture()
    chunks, scopes = compile_publication(original, raw, authority(raw), Words())
    return raw, chunks, scopes


def new_terms(chunks: list[Chunk], scopes: dict[str, Any]) -> list[Chunk]:
    return [
        chunk
        for chunk in chunks
        if chunk.doc_sha256 == NEW
        and scopes.get(chunk.id, {})
        .get("warranty_scope", {})
        .get("policy", {})
        .get("format")
        == "explicit_model_europe_policy"
    ]


def test_complete_source_conditions_and_all_thirteen_exclusions_are_model_bound() -> (
    None
):
    raw, chunks, scopes = compiled()
    units = new_terms(chunks, scopes)
    assert len(units) == 39
    for pid in PIDS:
        own = [c for c in units if scopes[c.id]["product_ids"] == [pid]]
        assert len(own) == 13
        selected = []
        for c in own:
            policy = scopes[c.id]["warranty_scope"]["policy"]
            source = next(
                s
                for s in policy["sources"]["exclusions"]
                if s["chunk_id"] == policy["exclusion_source_id"]
            )
            selected.append(source["text"].splitlines()[policy["exclusion_index"]])
        assert set(selected) == set(EXCLUSIONS)
        for chunk in own:
            assert "2 years" in chunk.text
            assert (
                "first installed" in chunk.text
                and "6 months after the date of production" in chunk.text
            )
            assert (
                "authorized by GOODWE" in chunk.text
                and "Norway and Switzerland" in chunk.text
            )
            assert (
                "For Europe, excluding UK" in chunk.text
                and "written confirmation/approval" in chunk.text
            )
            assert "sold and installed after November 2022" in chunk.text
            assert (
                "only the cost of hardware material" in chunk.text
                and "statutory" in chunk.text
                and "local distributor" in chunk.text
                and "may NOT be the latest" in chunk.text
            )
    assert len(raw["products"]) == 3


def test_new_association_is_mandatory_wrong_model_and_unreviewed_context_fail() -> None:
    raw, original = fixture()
    missing = deepcopy(raw)
    missing["documents"] = [d for d in missing["documents"] if d["blob_sha256"] != NEW]
    for product in missing["products"]:
        product["documents"] = [
            did for did in product["documents"] if did != "doc-simulated-new-hca-policy"
        ]
    chunks, scopes = compile_publication(original, missing, authority(missing), Words())
    assert not new_terms(chunks, scopes)
    assert not any(
        c.doc_sha256 == OLD
        and c.id in scopes
        and scopes[c.id]["basis"] == "warranty_terms"
        for c in chunks
    )

    wrong = deepcopy(raw)
    product = deepcopy(wrong["products"][0])
    product.update(
        product_id=999999, model="GW11K-HCA-G30", product_revision="SIMULATED-wrong"
    )
    wrong["products"].append(product)
    next(d for d in wrong["documents"] if d["blob_sha256"] == NEW)[
        "product_ids"
    ].append(999999)
    chunks, scopes = compile_publication(original, wrong, authority(wrong), Words())
    assert not any(
        999999 in p["product_ids"]
        for p in scopes.values()
        if p.get("basis") == "warranty_terms"
    )

    source = Snapshot.read(raw)
    contexts = _author_contexts(original, source, {})
    overview = next(
        c for c in original if c.doc_sha256 == NEW and c.section == "OVERVIEW"
    )
    changed = [
        replace(c, text=c.text + "\nOnly GW22K-HCA-20 has this warranty.")
        if c.id == overview.id
        else c
        for c in original
    ]
    units, _ = compile_named_terms(
        changed, source, Words(), 512, restricted_contexts=contexts
    )
    assert not units


def test_runtime_checks_native_paragraphs_current_document_and_revision() -> None:
    raw, chunks, scopes = compiled()
    unit = new_terms(chunks, scopes)[0]
    proof = scopes[unit.id]
    source = Snapshot.read(raw)
    anchors = external_axis_anchors(chunks)
    pid = proof["product_ids"][0]
    association = proof["associations"]
    permitted = partial(
        authorize_chunk,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
        external_axis_anchors=anchors,
    )
    assert permitted(NEW, [pid], association, proof)
    altered = deepcopy(proof)
    altered["warranty_scope"]["policy"]["sources"]["geography"]["text"] += (
        " UK is included."
    )
    assert not permitted(NEW, [pid], association, altered)
    assert not permitted(NEW, [pid], [], proof)
    bad_anchors = deepcopy(anchors)
    del bad_anchors[
        proof["warranty_scope"]["policy"]["sources"]["exclusions"][0]["chunk_id"]
    ]
    assert not permitted(
        NEW,
        [pid],
        association,
        proof,
        external_axis_anchors=bad_anchors,
    )


def test_all_reviewed_exclusions_have_german_wording_and_missing_fragments_fail() -> (
    None
):
    raw, chunks, scopes = compiled()
    units = [
        c for c in new_terms(chunks, scopes) if scopes[c.id]["product_ids"] == [3557]
    ]
    translations = set()
    for unit in units:
        proof = scopes[unit.id]
        rendered = render_named_terms(
            proof["warranty_scope"], proof["source_chunk_ids"]
        )
        assert rendered is not None
        notes = [SimpleNamespace(**note) for note in rendered[1]]
        pieces = ["{fact:sample.n1}"] * 11
        translated = german_named_answers("sample", pieces, notes, "2")
        assert translated is not None
        translations.add(translated["coverage"])
    assert len(translations) == 13
    original_raw, original = fixture()
    source = Snapshot.read(original_raw)
    contexts = _author_contexts(original, source, {})
    for section, text in (
        ("WARRANTY EXCEPTIONS", "Accidents and external influences."),
        ("LIMITATION OF GOODWE's LIABILITY", "may NOT be the latest version"),
    ):
        missing = [
            c
            for c in original
            if not (c.doc_sha256 == NEW and c.section == section and text in c.text)
        ]
        compiled_units, _ = compile_named_terms(
            missing, source, Words(), 512, restricted_contexts=contexts
        )
        assert not compiled_units


def test_simulated_woo_link_through_sqlite_knowledge_hydration_and_withdrawal(
    tmp_path: Path,
) -> None:
    raw, chunks, scopes = compiled()
    root = tmp_path / "corpus"
    corpus.write(
        root,
        corpus.Meta(
            "simulated-hca-only",
            None,
            None,
            "manufacturer Docling 2.136.0",
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
                doc_type_of(d["type"], d.get("role", "")),
                d["lang"],
                3,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        chunks,
    )
    db = tmp_path / "index.sqlite"
    store.export(root, db)
    index = DocumentIndex(db, encoder=None)
    try:
        search = KnowledgeSearch(lambda: index, publication=authority(raw))
        for pid in sorted(PIDS):
            for lang in ("en", "de"):
                result = search(
                    {
                        "query": "warranty period conditions",
                        "lang": lang,
                        "product_ids": [pid],
                    }
                )
                hit = next(
                    h
                    for h in result["hits"]
                    if h.get("warranty_terms") and h["chunk_id"].startswith(NEW[:12])
                )
                assert (
                    hit["qualification_required"] and len(hit["qualifications"]) == 11
                )
                if lang == "en":
                    assert (
                        "For Europe, excluding UK"
                        in hit["warranty_answers"]["geography"]
                    )
                    assert "statutory" in hit["warranty_answers"]["geography"]
                else:
                    assert (
                        "Europa mit Ausnahme des Vereinigten Königreichs"
                        in hit["warranty_answers"]["geography"]
                    )
                    assert "gesetzlichen Rechte" in hit["warranty_answers"]["geography"]
                    assert "Ausschluss" in hit["warranty_answers"]["coverage"]
                facts = collect("linker/search-knowledge", {"hits": [hit]}, lang)
                if pid == 3557 and lang == "de":
                    # The real customer turn found this policy but the model
                    # twice failed its source-derived-answer grounding gate.
                    # Its fallback must still answer the period and start.
                    question = (
                        "Wie lange gilt die Herstellergarantie für den GoodWe "
                        "GW11K-HCA-20 in Deutschland, und wann beginnt sie? "
                        "Bitte nennen Sie die zugrunde liegende Garantieunterlage."
                    )
                    request = TurnRequest(
                        conversation_id="hca-period-fallback",
                        messages=[TurnMessage(role="user", content=question)],
                        locale="de",
                    )
                    rejected = TurnOutput(
                        language="de",
                        blocks=[
                            TextBlock(
                                text="Die Garantie gilt lebenslang.",
                                refs=[hit["chunk_id"]],
                            )
                        ],
                    )

                    def generate(
                        _request: TurnRequest,
                        _retry: str | None,
                        *,
                        output: TurnOutput = rejected,
                    ) -> tuple[TurnOutput, TurnFacts]:
                        return output, TurnFacts()

                    turn = run(
                        request,
                        generate,
                        Route("documents"),
                        facts,
                    )
                    assert turn.fallback and turn.attempts == 2
                    text = "\n".join(
                        b.text for b in turn.output.blocks if isinstance(b, TextBlock)
                    )
                    assert "2 Jahre" in text
                    assert "ersten Installation" in text and "Herstellungsdatum" in text
                    assert "Herstellerbedingung (englisches Original)" not in text
                    assert any(
                        isinstance(b, DocumentBlock) and b.url and "#page=1" in b.url
                        for b in turn.output.blocks
                    )
                    # A nearby model, an unrelated question, a second model or
                    # an independently requested technical fact must never be
                    # replaced wholesale by this single warranty answer.
                    route = Route("documents")
                    for wording in (
                        "Wie viele Jahre Garantie hat der GW11K-HCA-20?",
                        "Wieviele Jahre gilt die Garantie für GW11K-HCA-20?",
                        "Wann beginnt die Garantie für den GW11K-HCA-20?",
                        "Ab welchem Datum gilt die Garantie für GW11K-HCA-20?",
                    ):
                        assert (
                            _warranty_period_fallback(facts, "de", route, wording, None)
                            is not None
                        )
                    assert (
                        _warranty_period_fallback(
                            facts,
                            "de",
                            route,
                            question.replace("HCA-20", "HCA-20A"),
                            None,
                        )
                        is None
                    )
                    assert (
                        _warranty_period_fallback(
                            facts,
                            "de",
                            route,
                            "Zeigen Sie die Unterlage für GW11K-HCA-20.",
                            None,
                        )
                        is None
                    )
                    mixed = deepcopy(facts)
                    mixed.technical_chunks.add("manual-technical-fact")
                    assert (
                        _warranty_period_fallback(mixed, "de", route, question, None)
                        is None
                    )
                    missing = deepcopy(facts)
                    missing.warranty_answers.clear()
                    assert (
                        _warranty_period_fallback(missing, "de", route, question, None)
                        is None
                    )
                if pid == 3557 and lang == "en":
                    for wording in (
                        "How many years is the GW11K-HCA-20 warranty?",
                        "When does the warranty for GW11K-HCA-20 start?",
                        "From what date is the GW11K-HCA-20 warranty valid?",
                    ):
                        assert (
                            _warranty_period_fallback(
                                facts, "en", Route("documents"), wording, None
                            )
                            is not None
                        )
                draft = TurnOutput(
                    language=lang,
                    blocks=[
                        TextBlock(
                            text=hit["warranty_answers"]["general"],
                            refs=[hit["chunk_id"]],
                        )
                    ],
                )
                verdict = check(draft, facts, question="warranty guarantee")
                assert verdict.ok, verdict.failures
                answer = hydrate(draft, facts)
                block = next(b for b in answer.blocks if isinstance(b, TextBlock))
                if lang == "en":
                    assert (
                        "first installed" in block.text and "production" in block.text
                    )
                    assert (
                        "Norway and Switzerland" in block.text
                        and "excluding UK" in block.text
                    )
                else:
                    assert (
                        "ersten Installation" in block.text
                        and "Herstellungsdatum" in block.text
                    )
                    assert (
                        "Norwegen oder der Schweiz" in block.text
                        and "Vereinigten Königreichs" in block.text
                    )
                assert any(
                    isinstance(b, DocumentBlock) and b.url and b.url.endswith("#page=1")
                    for b in answer.blocks
                )
                assert {
                    b.url.rsplit("#page=", 1)[-1]
                    for b in answer.blocks
                    if isinstance(b, DocumentBlock) and b.url
                } >= {"1", "2", "3"}
                if lang == "de":
                    assert "Herstellerbedingung (englisches Original)" not in block.text
                    assert "channels authorized by GOODWE" not in block.text
                    for topic in (
                        "period",
                        "production",
                        "overview",
                        "start",
                        "effective",
                        "geography",
                        "coverage",
                        "general",
                    ):
                        specific = TurnOutput(
                            language="de",
                            blocks=[
                                TextBlock(
                                    text=hit["warranty_answers"][topic],
                                    refs=[hit["chunk_id"]],
                                )
                            ],
                        )
                        specific_check = check(specific, facts, question="Garantie")
                        assert specific_check.ok, specific_check.failures
                        filled = hydrate(specific, facts)
                        content = next(
                            b.text for b in filled.blocks if isinstance(b, TextBlock)
                        )
                        assert "2 Jahre" in content and "ersten Installation" in content
                        assert "6 Monate" in content and "Herstellungsdatum" in content
                        assert "autorisierten Vertriebspartner" in content
                        assert "Norwegen oder der Schweiz" in content
                        assert "Vereinigten Königreichs" in content
                        assert "schriftliche Bestätigung" in content
                        assert "nach November 2022" in content
                        assert "gesetzlichen Rechte" in content
                        assert "mindestens gleichwertige" in content
                        assert "Materialkosten" in content and "Ausschluss" in content
                        assert "neuere Fassung" in content
                        assert "englisches Original):" not in content
                        assert content.count("autorisierten Vertriebspartner") == 1
                        assert content.count("ersten Installation") == 1
                        if topic in {"period", "coverage"}:
                            priced, priced_facts, _missed, protected, replacements = (
                                _hydrate_priced(
                                    specific,
                                    facts,
                                    None,
                                    "de",
                                    None,
                                    None,
                                    "Wie lange gilt die Garantie?",
                                )
                            )
                            sealed = _restore_qualified(
                                seal(
                                    protected,
                                    priced_facts,
                                    None,
                                    "Wie lange gilt die Garantie?",
                                    "product",
                                    original=specific,
                                ),
                                replacements,
                            )
                            assert sealed == priced
                            assert language_failure(sealed, "de") is None
                    masked = hydrate(draft, facts, qualified_mask=lambda _: "[MASKED]")
                    masked_text = next(
                        b.text for b in masked.blocks if isinstance(b, TextBlock)
                    )
                    assert "[MASKED]" in masked_text and "2022" not in masked_text
                else:
                    assert "Manufacturer's condition:" in block.text
                    assert "For Europe, excluding UK" in block.text
        # A broad real retrieval can return policies for more than one HCA
        # model. Select an explicitly requested model before deciding whether
        # its verified policy is unambiguous.
        own_hits = [
            h
            for h in search(
                {"query": "warranty period", "lang": "de", "product_ids": [3557]}
            )["hits"]
            if h.get("warranty_terms")
        ][:2]
        other_hit = next(
            h
            for h in search(
                {"query": "warranty period", "lang": "de", "product_ids": [3586]}
            )["hits"]
            if h.get("warranty_terms")
        )
        assert len(own_hits) == 2
        mixed_hits = [*own_hits, other_hit]
        mixed_facts = collect("linker/search-knowledge", {"hits": mixed_hits}, "de")
        full_question = (
            "Wie lange gilt die Herstellergarantie für die GoodWe HCA Wallbox "
            "GW11K-HCA-20, und ab welchem Datum beginnt sie?"
        )
        incomplete_question = full_question.replace("GW11K-HCA-20", "GW11K-HCA")
        for question, should_answer in (
            (full_question, True),
            (incomplete_question, False),
            (full_question.replace("HCA-20", "HCA-20A"), False),
            (full_question + " Und GW7K-HCA-20?", False),
        ):
            request = TurnRequest(
                conversation_id="hca-mixed-policy-fallback",
                messages=[TurnMessage(role="user", content=question)],
                locale="de",
            )
            rejected = TurnOutput(
                language="de",
                blocks=[
                    TextBlock(
                        text="Unbelegte Garantie.", refs=[mixed_hits[0]["chunk_id"]]
                    )
                ],
            )

            def invalid_answer(
                _request: TurnRequest,
                _retry: str | None,
                *,
                output: TurnOutput = rejected,
            ) -> tuple[TurnOutput, TurnFacts]:
                return output, TurnFacts()

            turn = run(request, invalid_answer, Route("documents"), mixed_facts)
            assert turn.fallback
            text = "\n".join(
                block.text
                for block in turn.output.blocks
                if isinstance(block, TextBlock)
            )
            assert "Herstellerbedingung (englisches Original)" not in text
            if should_answer:
                assert "2 Jahre" in text and "ersten Installation" in text
                assert "6 Monate" in text and "Herstellungsdatum" in text
                assert any(
                    isinstance(block, DocumentBlock)
                    and block.url
                    and block.url.endswith("#page=1")
                    for block in turn.output.blocks
                )
            else:
                assert "vollständige Modellbezeichnung" in text
                assert "2 Jahre" not in text

        conflicting = deepcopy(mixed_facts)
        other_chunk = own_hits[1]["chunk_id"]
        conflicting.warranty_answers[other_chunk]["period"] = "A different period."
        assert (
            _warranty_period_fallback(
                conflicting, "de", Route("documents"), full_question, None
            )
            is None
        )
        conflicting = deepcopy(mixed_facts)
        conflicting.documents[other_chunk] = replace(
            conflicting.documents[other_chunk],
            url="https://example.invalid/other-policy.pdf",
        )
        assert (
            _warranty_period_fallback(
                conflicting, "de", Route("documents"), full_question, None
            )
            is None
        )
        one_model = collect("linker/search-knowledge", {"hits": own_hits}, "de")
        assert (
            _warranty_period_fallback(
                one_model,
                "de",
                Route("documents"),
                "Wie lange gilt die Garantie?",
                3557,
            )
            is not None
        )
        assert (
            _warranty_period_fallback(
                one_model, "de", Route("documents"), incomplete_question, 3557
            )
            is None
        )

        de_hit = search(
            {"query": "warranty period", "lang": "de", "product_ids": [3557]}
        )["hits"][0]
        de_facts = collect("linker/search-knowledge", {"hits": [de_hit]}, "de")
        cid = de_hit["chunk_id"]
        original_notes = de_facts.qualifications[cid]
        forged_notes = list(original_notes)
        forged_notes[4] = replace(forged_notes[4], chunk_id="aaaaaaaaaaaa-p3-12345678")
        assert (
            qualified_named_additions(
                cid,
                de_facts.facts[f"{cid}.text"].value,
                forged_notes,
                de_facts.warranty_answers[cid],
                de_hit["warranty_answers"]["period"],
            )
            is None
        )
        forged_notes[4] = replace(
            original_notes[4], quote=original_notes[4].quote + " changed"
        )
        assert (
            qualified_named_additions(
                cid,
                de_facts.facts[f"{cid}.text"].value,
                forged_notes,
                de_facts.warranty_answers[cid],
                de_hit["warranty_answers"]["period"],
            )
            is None
        )
        reporting = search(
            {
                "query": "Product failure is not reported to GOODWE within one month",
                "lang": "de",
                "product_ids": [3557],
            }
        )
        reporting_hit = next(
            h
            for h in reporting["hits"]
            if any(
                "Product failure is not reported" in n["quote"]
                for n in h.get("qualifications", [])
            )
        )
        reporting_facts = collect(
            "linker/search-knowledge", {"hits": [reporting_hit]}, "de"
        )
        reporting_draft = TurnOutput(
            language="de",
            blocks=[
                TextBlock(
                    text=reporting_hit["warranty_answers"]["reporting"],
                    refs=[reporting_hit["chunk_id"]],
                )
            ],
        )
        verdict = check(reporting_draft, reporting_facts, question="Garantie")
        assert verdict.ok, verdict.failures
        reporting_answer = hydrate(reporting_draft, reporting_facts)
        reporting_text = next(
            b.text for b in reporting_answer.blocks if isinstance(b, TextBlock)
        )
        assert "innerhalb von 1 Monat" in reporting_text
        assert "2 Jahre" in reporting_text and "gesetzlichen Rechte" in reporting_text
        assert "Herstellerbedingung (englisches Original)" not in reporting_text
        priced, priced_facts, _missed, protected, replacements = _hydrate_priced(
            reporting_draft,
            reporting_facts,
            None,
            "de",
            None,
            None,
            "Wann muss ein Fehler gemeldet werden?",
        )
        sealed = _restore_qualified(
            seal(
                protected,
                priced_facts,
                None,
                "Wann muss ein Fehler gemeldet werden?",
                "product",
                original=reporting_draft,
            ),
            replacements,
        )
        assert sealed == priced and language_failure(sealed, "de") is None
        revoked = deepcopy(raw)
        new = next(d for d in revoked["documents"] if d["blob_sha256"] == NEW)
        new["product_ids"].remove(3586)
        result = KnowledgeSearch(lambda: index, publication=authority(revoked))(
            {"query": "warranty period conditions", "lang": "en", "product_ids": [3586]}
        )
        assert not any(h["chunk_id"].startswith(NEW[:12]) for h in result["hits"])
        assert not any(
            h["chunk_id"].startswith(OLD[:12]) and h.get("warranty_terms")
            for h in result["hits"]
        )
    finally:
        index.close()
