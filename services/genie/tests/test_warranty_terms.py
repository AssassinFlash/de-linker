"""Original policy rows remain conditional through the actual knowledge consumer."""

import gzip
import hashlib
import json
import re
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_build import document
from test_chunking import Words
from test_publication import authority
from test_publication_compiler import warranty_fixture

from index import build, corpus, parse, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.extract import Block, Page, pdf_series_cover
from index.inventory import doc_type_of
from index.table_compiler import external_axis_anchors
from index.warranty import _family_cover, compile_procedures, compile_terms
from linker_genie.cycle import run
from linker_genie.facts import collect, merge
from linker_genie.figures import localize
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch, model_view
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.route import Route
from linker_genie.schema import (
    AskBlock,
    DocumentBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.warranty_scope import exclusion_category, terms_id, terms_text


def _generation(output, facts):
    return lambda _request, _retry: (output, facts)


def _compile():
    raw, original, model, model_scope = warranty_fixture()
    source = Snapshot.read(raw)
    procedures, procedure_scopes = compile_procedures(
        original,
        [model],
        {model.id: model_scope},
        source,
        Words(),
        512,
        restricted_contexts={},
    )
    terms, term_scopes = compile_terms(
        original,
        procedures,
        procedure_scopes,
        Words(),
        512,
        restricted_contexts={},
    )
    return (
        raw,
        original,
        model,
        model_scope,
        procedures,
        procedure_scopes,
        terms,
        term_scopes,
    )


def test_cover_repeated_section_inherits_range_but_conflicting_range_fails() -> None:
    _, original, model, *_ = warranty_fixture()
    cover = next(
        c for c in original if c.doc_sha256 == model.doc_sha256 and c.page == 1
    )
    repetition = replace(cover, id="repeat", text="Silent Smart Secure Simple")
    assert _family_cover([cover, repetition]) == (cover, ("esa", "5", "3E+1"))
    conflict = replace(cover, id="conflict", text="3-10kW")
    assert _family_cover([cover, repetition, conflict]) is None
    other_title = replace(cover, id="other", section="ET Series", text="80-100kW")
    assert _family_cover([cover, other_title]) is None
    ambiguous = replace(cover, section="", text="ESA Series 3-10kW and 5-30kW")
    assert _family_cover([ambiguous]) is None
    et_with_battery = replace(
        cover,
        section="",
        text="Die ET-Serie 80-100kW kombiniert sich mit der BAT-Serie.",
    )
    assert _family_cover([et_with_battery])[1] == ("et", "8E+1", "1E+2")
    raw, original, model, model_scope = warranty_fixture()
    procedures, _ = compile_procedures(
        original,
        [model],
        {model.id: model_scope},
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts={cover.id: [{"kind": "heading", "quote": "other model"}]},
    )
    assert not procedures


@pytest.mark.parametrize(
    "title",
    ["ESA Series 3-10kW and 5-30kW", "ESA Series 5-30kW and 3-10kW"],
)
def test_conflicting_ranges_on_one_cover_do_not_compile_procedures(title: str) -> None:
    raw, original, model, model_scope = warranty_fixture()
    original = [
        replace(chunk, section="", text=title)
        if chunk.doc_sha256 == model.doc_sha256 and chunk.page == 1
        else chunk
        for chunk in original
    ]
    procedures, _ = compile_procedures(
        original,
        [model],
        {model.id: model_scope},
        Snapshot.read(raw),
        Words(),
        512,
        restricted_contexts={},
    )
    assert not procedures


def _pdf_fixture(tmp_path: Path, lines: list[tuple[int, str]]) -> Path:
    commands = "\n".join(
        f"BT /F1 12 Tf 40 {y} Td ({line}) Tj ET" for y, line in lines
    ).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 808] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(commands)).encode()
        + b" >>\nstream\n"
        + commands
        + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path = tmp_path / f"{hashlib.sha256(data).hexdigest()}.pdf"
    path.write_bytes(data)
    return path


def test_pdf_cover_recovery_requires_unique_visible_line_and_hash(
    tmp_path: Path,
) -> None:
    line = "ESA Series Residential Energy Storage System I 3-10kW / 5-108kWh"
    path = _pdf_fixture(tmp_path, [(40, line)])
    anchor = pdf_series_cover(path)
    assert anchor and anchor["text"] == line and anchor["source_sha256"] == path.stem
    assert pdf_series_cover(_pdf_fixture(tmp_path, [(40, line), (80, line)])) is None
    assert (
        pdf_series_cover(
            _pdf_fixture(
                tmp_path,
                [
                    (40, "ESA Series"),
                    (80, "Residential Energy Storage System I 3-10kW / 5-108kWh"),
                ],
            )
        )
        is None
    )
    wrong = tmp_path / "wrong.pdf"
    wrong.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="content identity"):
        pdf_series_cover(wrong)


def test_normal_chunk_preparation_persists_physical_cover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    line = "ESA Series Residential Energy Storage System I 3-10kW / 5-108kWh"
    pdf = _pdf_fixture(tmp_path, [(40, line)])
    parsed = tmp_path / "parsed" / pdf.stem
    parsed.mkdir(parents=True)
    (parsed / "docling.json").write_text("{}")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "publication_manifest": {},
                "products": [],
                "documents": [
                    document(
                        pdf.stem,
                        "https://site.test/owned.pdf",
                        ["MODEL-1"],
                        "datasheet",
                        "en",
                    )
                ],
            }
        )
    )
    monkeypatch.setattr(
        parse,
        "cached_status",
        lambda _: parse.ParseStatus(pdf.stem, "fixture", "ok", 1),
    )
    monkeypatch.setattr(
        build.extract,
        "extract",
        lambda *args, **kwargs: [
            Page(1, "docling", [Block(kind="text", text="Parsed content.")])
        ],
    )
    result = build.chunk_all(
        inventory, tmp_path, parsed.parent, Words(), lambda _: "en"
    )
    cover = next(c for c in result.chunks if "-pdf-cover-" in c.id)
    assert cover.text == line and cover.source_pdf_cover is not None
    assert external_axis_anchors(result.chunks)[cover.id] == cover.source_pdf_cover


@pytest.mark.parametrize("lang", ["en", "de"])
def test_original_policy_row_conditions_reach_consumer_and_revoke(
    tmp_path: Path, lang: str
) -> None:
    raw, original, model, model_scope, procedures, proc_scopes, terms, term_scopes = (
        _compile()
    )
    assert {c.lang for c in terms} == {"en", "de"}
    target = next(c for c in terms if c.lang == lang)
    assert "ESA 5-30k" in target.text
    assert ("10 years" if lang == "en" else "10 Jahre") in target.text
    assert ("produced on/after" if lang == "en" else "ab 1. Januar") in target.text
    assert (
        "before 1 st January" not in target.text and "vor 1. Januar" not in target.text
    )
    proof = term_scopes[target.id]
    source = Snapshot.read(raw)

    def allowed(candidate, current=source):
        return authorize_chunk(
            target.doc_sha256,
            [6512],
            candidate["associations"],
            candidate,
            products=current.products,
            documents=current.documents,
            chunk_id=target.id,
            text=target.text,
            external_axis_anchors=external_axis_anchors(original),
            require_table_anchor=True,
        )

    assert allowed(proof)
    for mutation in ("row", "start", "model"):
        altered = deepcopy(proof)
        evidence = altered["warranty_scope"]
        if mutation == "row":
            evidence["policy"]["term_row"]["row"] = 2
        elif mutation == "start":
            evidence["policy"]["term_sources"]["start"]["text"] = "No conditions."
        else:
            evidence["model"] = "GW6K-ETA-G20"
        assert not allowed(altered)
    changed = deepcopy(raw)
    policy_id = proof["document_ids"][0]
    next(d for d in changed["documents"] if d["document_id"] == policy_id)[
        "product_ids"
    ] = []
    assert not allowed(proof, Snapshot.read(changed))

    all_scopes = {model.id: model_scope, **proc_scopes, **term_scopes}
    root = tmp_path / "corpus"
    corpus.write(
        root,
        corpus.Meta(
            "warranty-test",
            None,
            None,
            "original source",
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
        [*original, model, *procedures, *terms],
    )
    db = tmp_path / "index.sqlite"
    store.export(root, db)
    index = DocumentIndex(db, encoder=None)
    try:
        payload = KnowledgeSearch(lambda: index, publication=authority(raw))(
            {
                "query": "warranty period conditions"
                if lang == "en"
                else "Garantie Zeitraum Bedingungen",
                "lang": lang,
                "product_ids": [6512],
            }
        )
        hit = next(h for h in payload["hits"] if h["chunk_id"] == target.id)
        assert hit["qualification_required"] is True
        assert len(hit["qualifications"]) == 6
        figures = hit["figures"]
        period = next(
            key for key, value in figures.items() if value in {"10 years", "10 Jahre"}
        )
        facts = collect("linker/search-knowledge", payload, lang)
        text = (
            f"The period is {{fact:{period}}}."
            if lang == "en"
            else f"Die Frist beträgt {{fact:{period}}}."
        )
        answer = hydrate(
            TurnOutput(language=lang, blocks=[TextBlock(text=text, refs=[target.id])]),
            facts,
        )
        output = answer.blocks[0]
        assert isinstance(output, TextBlock)
        for phrase in (
            (
                "produced on/after",
                "first installed",
                "installed on or after",
                "Normal wear",
                "authorized",
            )
            if lang == "en"
            else (
                "ab 1. Januar",
                "installiert",
                "5. März",
                "Normaler Verschleiß",
                "autorisierten",
            )
        ):
            assert phrase in output.text
        links = [b.url for b in answer.blocks if isinstance(b, DocumentBlock)]
        assert any("#page=3" in link for link in links)
        assert any(("#page=5" if lang == "en" else "#page=6") in link for link in links)
        # Conditions remain attached even when a nonnumeric statement cites a row.
        ref_only = hydrate(
            TurnOutput(
                language=lang, blocks=[TextBlock(text="Details.", refs=[target.id])]
            ),
            facts,
        )
        assert (
            "first installed" if lang == "en" else "Herstellungsdatum"
        ) in ref_only.blocks[0].text
    finally:
        index.close()


def test_procedure_alone_is_not_complete_policy_preparation(tmp_path: Path) -> None:
    raw, _, model, model_scope, procedures, proc_scopes, _, _ = _compile()
    all_scopes = {model.id: model_scope, **proc_scopes}
    root = tmp_path / "corpus"
    corpus.write(
        root,
        corpus.Meta(
            "procedure-only",
            None,
            None,
            "fixture",
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
        [model, *procedures],
    )
    db = tmp_path / "index.sqlite"
    store.export(root, db)
    index = DocumentIndex(db, encoder=None)
    try:
        missing = index.loaded()["unprepared_documents"]
        for policy in (d for d in raw["documents"] if d["type"] == "warranty"):
            assert {
                "document_id": policy["document_id"],
                "product_id": 6512,
                "reason": "no_proven_passage",
            } in missing
        for lang in ("en", "de"):
            payload = KnowledgeSearch(lambda: index, publication=authority(raw))(
                {
                    "query": "contact distributor installer warranty claim"
                    if lang == "en"
                    else "Vertriebshändler Installateur Garantieantrag",
                    "lang": lang,
                    "product_ids": [6512],
                }
            )
            procedure = next(
                hit for hit in payload["hits"] if hit.get("warranty_procedure")
            )
            facts = collect("linker/search-knowledge", payload, lang)
            request = TurnRequest(
                conversation_id="procedure-only",
                locale=lang,
                messages=[
                    TurnMessage(
                        role="user",
                        content="How do I make a warranty claim?"
                        if lang == "en"
                        else "Wie stelle ich einen Garantieantrag?",
                    )
                ],
                page_context=PageContext(type="product", product_id=6512),
            )
            sentence = procedure["text"].split(".", 1)[0] + "."
            answer = TurnOutput(
                language=lang,
                blocks=[TextBlock(text=sentence, refs=[procedure["chunk_id"]])],
            )
            result = run(request, _generation(answer, facts), Route("documents"))
            assert result.grounded and not result.fallback
            invented = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text="All damage is covered by the warranty."
                        if lang == "en"
                        else "Alle Schäden sind durch die Garantie abgedeckt.",
                        refs=[procedure["chunk_id"]],
                    ),
                    DocumentBlock(ref=procedure["chunk_id"]),
                ],
            )
            assert run(
                request, _generation(invented, facts), Route("documents")
            ).fallback
            empty = collect("linker/search-knowledge", {"hits": []}, lang)
            assert run(
                request, _generation(invented, empty), Route("documents")
            ).fallback
            unreferenced = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text="All damage is covered by the warranty."
                        if lang == "en"
                        else "Alle Schäden sind durch die Garantie abgedeckt.",
                        refs=[],
                    )
                ],
            )
            assert run(
                request, _generation(unreferenced, empty), Route("documents")
            ).fallback
    finally:
        index.close()


def test_current_goodwe_policy_cohort_and_physical_anchor_reach_sqlite(
    tmp_path: Path,
) -> None:
    # Read-only capture from Woo revision 36c5b21f... and the corresponding
    # loaded index. The EHA cover anchor is from the SHA-matched original PDF
    # on physical page 1; this local corpus is not a production activation.
    path = (
        Path(__file__).parent / "fixtures/publication-compiler/warranty-current.json.gz"
    )
    data = json.loads(gzip.decompress(path.read_bytes()))
    raw = data["manifest"]
    original = [Chunk(**item) for item in data["original"]]
    compiled = [Chunk(**item) for item in data["compiled"]]
    source = Snapshot.read(raw)
    procedures, procedures_scope = compile_procedures(
        original, compiled, data["scopes"], source, Words(), 512, restricted_contexts={}
    )
    terms, term_scopes = compile_terms(
        original, procedures, procedures_scope, Words(), 512, restricted_contexts={}
    )
    pairs = {(term_scopes[c.id]["product_ids"][0], c.lang) for c in terms}
    assert pairs == {(pid, lang) for pid in source.products for lang in ("en", "de")}
    assert len(pairs) == 44
    for lang in ("en", "de"):
        categories = {
            exclusion_category(extra["text"].splitlines()[extra["line"]])
            for c in terms
            if term_scopes[c.id]["product_ids"] == [6528] and c.lang == lang
            if (
                extra := term_scopes[c.id]["warranty_scope"]["policy"].get(
                    "additional_exclusion"
                )
            )
        }
        assert categories == {
            "modification",
            "force_majeure",
            "battery_compatibility",
            "reporting",
        }
    anchors = external_axis_anchors(original)
    for c in terms:
        proof = term_scopes[c.id]
        pid = proof["product_ids"][0]
        assert authorize_chunk(
            c.doc_sha256,
            [pid],
            proof["associations"],
            proof,
            products=source.products,
            documents=source.documents,
            chunk_id=c.id,
            text=c.text,
            external_axis_anchors=anchors,
            require_table_anchor=True,
        )
        model = source.products[pid]["model"]
        if "ETA" in model or "EHA" in model:
            assert ("10 years" if c.lang == "en" else "10 Jahre") in c.text
            assert ("produced on/after" if c.lang == "en" else "ab 1. Januar") in c.text
        elif "STS" in model:
            assert (
                "regardless of production"
                if c.lang == "en"
                else "unabhängig vom Herstellungs"
            ) in c.text
        else:
            assert ("5 years" if c.lang == "en" else "5 Jahre") in c.text
    for pid in (1946, 1947, 1948):
        for lang in ("en", "de"):
            rows = [
                c.text
                for c in terms
                if term_scopes[c.id]["product_ids"] == [pid]
                and c.lang == lang
                and "additional_exclusion"
                not in term_scopes[c.id]["warranty_scope"]["policy"]
            ]
            assert len(rows) == 2
            assert any(
                "before" in row if lang == "en" else "vor 1. Januar" in row
                for row in rows
            )
            assert any(
                "on/after" in row if lang == "en" else "ab 1. Januar" in row
                for row in rows
            )

    eha = next(
        c
        for c in terms
        if term_scopes[c.id]["product_ids"] == [6528] and c.lang == "en"
    )
    proof = term_scopes[eha.id]
    cover_id = proof["warranty_scope"]["datasheet"]["cover_chunk_id"]
    assert "-pdf-cover-" in cover_id and cover_id in anchors

    def allowed(candidate, current_anchors):
        return authorize_chunk(
            eha.doc_sha256,
            [6528],
            candidate["associations"],
            candidate,
            products=source.products,
            documents=source.documents,
            chunk_id=eha.id,
            text=eha.text,
            external_axis_anchors=current_anchors,
            require_table_anchor=True,
        )

    assert allowed(proof, anchors)
    changed = deepcopy(proof)
    del changed["warranty_scope"]["datasheet"]["cover_pdf"]
    assert not allowed(changed, anchors)
    changed = deepcopy(proof)
    changed["warranty_scope"]["datasheet"]["cover_pdf"]["power"]["bbox"][1] += 100
    assert not allowed(changed, anchors)
    altered_anchors = deepcopy(anchors)
    altered_anchors[cover_id] = changed["warranty_scope"]["datasheet"]["cover_pdf"]
    assert not allowed(changed, altered_anchors)
    assert not allowed(proof, {k: v for k, v in anchors.items() if k != cover_id})
    changed = deepcopy(proof)
    changed["warranty_scope"]["policy"]["term_row"]["cells"][4]["text"] = "5 years"
    assert not allowed(changed, anchors)
    changed = deepcopy(proof)
    cells = changed["warranty_scope"]["policy"]["term_row"]["cells"]
    date_cell = next(c for c in cells if c["col_start"] == 1 and c["row_start"] == 1)
    date_cell["text"] = "produced before 1 st January 2026"
    assert not allowed(changed, anchors)

    # Recompute every self-asserted ID and hash around a fabricated native row.
    # The independent original table and text chunks must still defeat it.
    forged = deepcopy(proof)
    evidence = forged["warranty_scope"]
    row = evidence["policy"]["term_row"]
    row["cells"][4]["text"] = "99 years *limited warranty"
    old_id = row["source"]["chunk_id"]
    row["source"]["text"] = row["source"]["text"].replace("10 years", "99 years", 1)
    fake_id = f"{eha.doc_sha256[:12]}-p{row['source']['page']}-{hashlib.sha256(('table' + chr(0) + row['source']['text']).encode()).hexdigest()[:8]}"
    row["source"]["chunk_id"] = fake_id
    evidence["source_chunk_id"] = fake_id
    evidence["policy"]["row_chunk_id"] = fake_id
    evidence["policy"]["row_quote"] = evidence["policy"]["row_quote"].replace(
        "10 years", "99 years", 1
    )
    forged["source_chunk_ids"] = list(
        dict.fromkeys([*forged["source_chunk_ids"], old_id, fake_id])
    )
    forged_text = terms_text(evidence, forged["source_chunk_ids"])
    assert forged_text is not None
    fake_text = forged_text[0]
    evidence["text_sha256"] = hashlib.sha256(fake_text.encode()).hexdigest()
    fake_chunk = terms_id(
        eha.doc_sha256, eha.page, evidence["model"], fake_id, fake_text
    )
    assert not authorize_chunk(
        eha.doc_sha256,
        [6528],
        forged["associations"],
        forged,
        products=source.products,
        documents=source.documents,
        chunk_id=fake_chunk,
        text=fake_text,
        external_axis_anchors=anchors,
        require_table_anchor=True,
    )

    all_scopes = {**data["scopes"], **procedures_scope, **term_scopes}
    chunks = {c.id: c for c in [*original, *compiled, *procedures, *terms]}
    root = tmp_path / "current-corpus"
    corpus.write(
        root,
        corpus.Meta(
            "current-policy-fixture",
            None,
            None,
            "original source",
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
        [(p["product_id"], p["model"]) for p in raw["products"]],
        list(chunks.values()),
    )
    db = tmp_path / "current.sqlite"
    store.export(root, db)
    index = DocumentIndex(db, encoder=None)
    try:
        policy_ids = {
            d["document_id"] for d in raw["documents"] if d["type"] == "warranty"
        }
        assert not any(
            item["document_id"] in policy_ids
            for item in index.loaded()["unprepared_documents"]
        )
        search = KnowledgeSearch(lambda: index, publication=authority(raw))
        for pid in (1948, 6514, 6528, 6530):
            for lang in ("en", "de"):
                result = search(
                    {
                        "query": "warranty period conditions"
                        if lang == "en"
                        else "Garantie Zeitraum Bedingungen",
                        "lang": lang,
                        "product_ids": [pid],
                    }
                )
                hits = [
                    hit
                    for hit in result["hits"]
                    if "-warranty-terms-" in hit["chunk_id"]
                ]
                assert hits and all(hit["qualification_required"] for hit in hits)
        for lang in ("en", "de"):
            result = search(
                {
                    "query": "inverter damage battery pack not compatible warranty"
                    if lang == "en"
                    else "Wechselrichterschaden Batteriepack nicht kompatibel Garantie",
                    "lang": lang,
                    "product_ids": [6528],
                }
            )
            battery = next(
                hit
                for hit in result["hits"]
                if any(
                    exclusion_category(note["quote"]) == "battery_compatibility"
                    and note["lang"] == lang
                    for note in hit.get("qualifications", [])
                )
            )
            facts = collect("linker/search-knowledge", result, lang)
            answer = hydrate(
                TurnOutput(
                    language=lang,
                    blocks=[TextBlock(text="Details.", refs=[battery["chunk_id"]])],
                ),
                facts,
            )
            assert (
                "not compatible"
                if lang == "en"
                else "nicht mit dem GOODWE-Wechselrichter kompatibel"
            ) in answer.blocks[0].text
            assert (
                "first installed" if lang == "en" else "Herstellungsdatum"
            ) in answer.blocks[0].text
            claim = (
                "GoodWe may treat inverter damage caused by an incompatible battery as not covered."
                if lang == "en"
                else "GoodWe kann den Wechselrichterschaden bei einer inkompatiblen Batterie als nicht abgedeckt behandeln."
            )
            request = TurnRequest(
                conversation_id="warranty-fixture",
                locale=lang,
                messages=[
                    TurnMessage(
                        role="user",
                        content=(
                            "Does the warranty cover inverter damage from an incompatible battery?"
                            if lang == "en"
                            else "Deckt die Garantie Wechselrichterschäden durch eine inkompatible Batterie?"
                        ),
                    )
                ],
                page_context=PageContext(type="product", product_id=6528),
            )
            route = Route("documents")
            bad = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(text=claim, refs=[]),
                    DocumentBlock(ref=battery["chunk_id"]),
                ],
            )
            denied = run(request, _generation(bad, facts), route)
            assert denied.fallback and not denied.grounded
            assert all(
                not isinstance(block, TextBlock) or block.text != claim
                for block in denied.output.blocks
            )
            good = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=battery["warranty_answers"]["battery_compatibility"],
                        refs=[battery["chunk_id"]],
                    ),
                    DocumentBlock(ref=battery["chunk_id"]),
                ],
            )
            shipped = run(request, _generation(good, facts), route)
            assert shipped.grounded and not shipped.fallback
            assert (
                "not compatible"
                if lang == "en"
                else "nicht mit dem GOODWE-Wechselrichter kompatibel"
            ) in shipped.output.blocks[0].text
            # A valid but unrelated policy row, or another model's policy, is
            # not a citation for this particular battery exclusion.
            base = next(
                hit
                for hit in result["hits"]
                if hit.get("warranty_terms")
                and hit["qualifications"][0]["lang"] == lang
                and not any(
                    exclusion_category(note["quote"]) == "battery_compatibility"
                    for note in hit["qualifications"]
                )
            )
            wrong = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(text=claim, refs=[base["chunk_id"]]),
                    DocumentBlock(ref=battery["chunk_id"]),
                ],
            )
            assert run(request, _generation(wrong, facts), route).fallback
            summary_request = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content="Explain the warranty."
                            if lang == "en"
                            else "Erklären Sie die Garantie.",
                        )
                    ]
                }
            )
            summary = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=base["warranty_answers"]["general"],
                        refs=[base["chunk_id"]],
                    )
                ],
            )
            shipped_summary = run(summary_request, _generation(summary, facts), route)
            assert shipped_summary.grounded and not shipped_summary.fallback
            direct = shipped_summary.output.blocks[0].text.split("\n\n", 1)[0]
            for phrase in (
                ("10 years", "non-transferable", "first installed", "manufacturing")
                if lang == "en"
                else ("10 Jahre", "nicht übertragbar", "installiert", "Herstellungs-")
            ):
                assert phrase in direct
            coverage = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=base["warranty_answers"]["coverage"],
                        refs=[base["chunk_id"]],
                    )
                ],
            )
            coverage_request = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content="What damage does the warranty cover?"
                            if lang == "en"
                            else "Welche Schäden deckt die Garantie ab?",
                        )
                    ]
                }
            )
            coverage_result = run(coverage_request, _generation(coverage, facts), route)
            assert coverage_result.grounded and not coverage_result.fallback
            direct_coverage = coverage_result.output.blocks[0].text.split("\n\n", 1)[0]
            assert (
                "manufacturing and material defects"
                if lang == "en"
                else "Herstellungs- und Materialfehler"
            ) in direct_coverage
            other_result = search(
                {
                    "query": "inverter damage battery pack not compatible warranty"
                    if lang == "en"
                    else "Wechselrichterschaden Batteriepack nicht kompatibel Garantie",
                    "lang": lang,
                    "product_ids": [6527],
                }
            )
            other = next(
                hit
                for hit in other_result["hits"]
                if any(
                    exclusion_category(note["quote"]) == "battery_compatibility"
                    and note["lang"] == lang
                    for note in hit.get("qualifications", [])
                )
            )
            mixed = merge(
                [facts, collect("linker/search-knowledge", other_result, lang)]
            )
            wrong_model = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=other["warranty_answers"]["battery_compatibility"],
                        refs=[other["chunk_id"]],
                    ),
                    DocumentBlock(ref=battery["chunk_id"]),
                ],
            )
            assert run(request, _generation(wrong_model, mixed), route).fallback
            explicit_model = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content=(
                                "Does the warranty for GW10K-EHA-G20 cover inverter damage from an incompatible battery?"
                                if lang == "en"
                                else "Deckt die Garantie für GW10K-EHA-G20 Wechselrichterschäden durch eine inkompatible Batterie?"
                            ),
                        )
                    ],
                    "page_context": PageContext(type="other"),
                }
            )
            assert run(explicit_model, _generation(wrong_model, mixed), route).fallback
            only_wrong = collect("linker/search-knowledge", other_result, lang)
            only_wrong_output = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=other["warranty_answers"]["battery_compatibility"],
                        refs=[other["chunk_id"]],
                    ),
                    DocumentBlock(ref=other["chunk_id"]),
                ],
            )
            assert run(
                explicit_model, _generation(only_wrong_output, only_wrong), route
            ).fallback
            lower_case_model = explicit_model.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content="Does the warranty for gw10k-eha-g20 cover the battery?",
                        )
                    ]
                }
            )
            assert run(
                lower_case_model, _generation(only_wrong_output, only_wrong), route
            ).fallback
            mismatched_document = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=battery["warranty_answers"]["battery_compatibility"],
                        refs=[battery["chunk_id"]],
                    ),
                    DocumentBlock(ref=other["chunk_id"]),
                ],
            )
            assert run(request, _generation(mismatched_document, mixed), route).fallback
            categorical = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text="An incompatible battery always voids the warranty."
                        if lang == "en"
                        else "Eine inkompatible Batterie lässt die Garantie immer erlöschen.",
                        refs=[battery["chunk_id"]],
                    )
                ],
            )
            assert run(request, _generation(categorical, facts), route).fallback
            reversed_condition = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=(
                            "GoodWe may cover inverter damage caused by an incompatible battery under warranty."
                            if lang == "en"
                            else "GoodWe kann Wechselrichterschäden durch eine inkompatible Batterie unter Garantie abdecken."
                        ),
                        refs=[battery["chunk_id"]],
                    )
                ],
            )
            assert run(request, _generation(reversed_condition, facts), route).fallback
            unsupported_claims = (
                [
                    "All damage is covered by the warranty.",
                    "The warranty is automatically transferable.",
                    "The warranty has no exclusions.",
                    f"The warranty lasts {{fact:{next(key for key, value in battery['figures'].items() if value == '12 months')}}}.",
                    f"The warranty starts exactly {{fact:{next(key for key, value in battery['figures'].items() if value == '12 months')}}} after production.",
                    f"The warranty starts {{fact:{next(key for key, value in battery['figures'].items() if value == '12 months')}}} after installation.",
                ]
                if lang == "en"
                else [
                    "Die Garantie deckt alle Schäden ab.",
                    "Die Garantie ist automatisch übertragbar.",
                    "Die Garantie hat keine Ausschlüsse.",
                    f"Die Garantie dauert {{fact:{next(key for key, value in battery['figures'].items() if value == '12 Monate')}}}.",
                    f"Die Garantie beginnt genau {{fact:{next(key for key, value in battery['figures'].items() if value == '12 Monate')}}} nach der Herstellung.",
                    f"Die Garantie beginnt {{fact:{next(key for key, value in battery['figures'].items() if value == '12 Monate')}}} nach der Installation.",
                ]
            )
            for statement in unsupported_claims:
                unsafe = TurnOutput(
                    language=lang,
                    blocks=[TextBlock(text=statement, refs=[battery["chunk_id"]])],
                )
                general_request = request.model_copy(
                    update={
                        "messages": [
                            TurnMessage(
                                role="user",
                                content="Explain the warranty."
                                if lang == "en"
                                else "Erklären Sie die Garantie.",
                            )
                        ]
                    }
                )
                assert run(general_request, _generation(unsafe, facts), route).fallback
            raw_number = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text="The warranty lasts 99 years."
                        if lang == "en"
                        else "Die Garantie dauert 99 Jahre.",
                        refs=[battery["chunk_id"]],
                    )
                ],
            )
            assert run(request, _generation(raw_number, facts), route).fallback

            figures = battery["figures"]
            falsified = deepcopy(battery)
            month_value = "12 months" if lang == "en" else "12 Monate"
            month_id = next(
                key for key, value in figures.items() if value == month_value
            )
            falsified["figures"][month_id] = month_value.replace("12", "13")
            falsified["text"] = falsified["text"].replace(
                month_value, month_value.replace("12", "13")
            )
            assert not collect(
                "linker/search-knowledge", {"hits": [falsified]}, lang
            ).chunk_ids
            unshown = deepcopy(battery)
            unshown["figures"][f"{battery['chunk_id']}.n999"] = "99 years"
            assert not collect(
                "linker/search-knowledge", {"hits": [unshown]}, lang
            ).chunk_ids
            changed_answer = deepcopy(battery)
            changed_answer["warranty_answers"]["coverage"] = "All damage is covered."
            assert not collect(
                "linker/search-knowledge", {"hits": [changed_answer]}, lang
            ).chunk_ids
            exposed = model_view({"hits": [battery]})["hits"][0]
            assert exposed["warranty_answers"] == battery["warranty_answers"]
            cases = (
                [
                    (
                        "10 years",
                        "How long is the product warranty?",
                        "The limited warranty is {value}.",
                    ),
                    (
                        "1 st January 2026",
                        "Which production date does the warranty require?",
                        "The warranty row applies to products made on or after {value}.",
                    ),
                    (
                        "12 months",
                        "When does the warranty start?",
                        "It starts at the earlier of first installation or {value} after production.",
                    ),
                    (
                        "March 05, 2026",
                        "When does this warranty policy apply to installations?",
                        "This policy applies to installations on or after {value}, unless a newer policy applies.",
                    ),
                ]
                if lang == "en"
                else [
                    (
                        "10 Jahre",
                        "Wie lange gilt die Produktgarantie?",
                        "Die eingeschränkte Garantie beträgt {value}.",
                    ),
                    (
                        "1. Januar 2026",
                        "Welches Herstellungsdatum verlangt die Garantie?",
                        "Die Garantiezeile gilt für Produkte, die ab {value} hergestellt wurden.",
                    ),
                    (
                        "12 Monate",
                        "Wann beginnt die Garantie?",
                        "Sie beginnt zum früheren Zeitpunkt der Erstinstallation oder {value} nach der Herstellung.",
                    ),
                    (
                        "5. März 2026",
                        "Ab wann gilt diese Garantie für Installationen?",
                        "Diese Garantie gilt für Installationen ab {value}, sofern keine neuere Regelung gilt.",
                    ),
                ]
            )
            for (value, question, _response), topic in zip(
                cases, ("period", "production", "start", "effective"), strict=True
            ):
                numeric = TurnOutput(
                    language=lang,
                    blocks=[
                        TextBlock(
                            text=battery["warranty_answers"][topic],
                            refs=[battery["chunk_id"]],
                        )
                    ],
                )
                question_request = request.model_copy(
                    update={"messages": [TurnMessage(role="user", content=question)]}
                )
                numeric_result = run(
                    question_request, _generation(numeric, facts), route
                )
                assert numeric_result.grounded and not numeric_result.fallback, (
                    lang,
                    value,
                    question,
                    topic,
                    numeric_result.failures,
                )
                assert value in numeric_result.output.blocks[0].text
                direct = numeric_result.output.blocks[0].text.split("\n\n", 1)[0]
                assert localize(value, lang) in direct
                if topic == "start":
                    assert (
                        "first installed"
                        if lang == "en"
                        else "zum ersten Mal installiert"
                    ) in direct
                    assert (
                        "shipment" if lang == "en" else "Produktlieferung"
                    ) in direct
                if topic == "period":
                    assert (
                        "1 January 2026" if lang == "en" else "1. Januar 2026"
                    ) in direct
                    threshold_question = request.model_copy(
                        update={
                            "messages": [
                                TurnMessage(
                                    role="user",
                                    content="How long is the warranty if manufactured after the cutoff?"
                                    if lang == "en"
                                    else "Wie lange gilt die Garantie bei Herstellung nach dem Stichtag?",
                                )
                            ]
                        }
                    )
                    assert run(
                        threshold_question, _generation(numeric, facts), route
                    ).grounded
            production_value, production_question, production_response = cases[1]
            effective_value, effective_question, effective_response = cases[3]
            production_id = next(
                key for key, actual in figures.items() if actual == production_value
            )
            effective_id = next(
                key for key, actual in figures.items() if actual == effective_value
            )
            for question, response, wrong_id in (
                (production_question, production_response, effective_id),
                (effective_question, effective_response, production_id),
            ):
                swapped = TurnOutput(
                    language=lang,
                    blocks=[
                        TextBlock(
                            text=response.format(value=f"{{fact:{wrong_id}}}"),
                            refs=[battery["chunk_id"]],
                        )
                    ],
                )
                swapped_request = request.model_copy(
                    update={"messages": [TurnMessage(role="user", content=question)]}
                )
                assert run(swapped_request, _generation(swapped, facts), route).fallback
            mixed_dates = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=(
                            f"The production cutoff is {{fact:{effective_id}}}; the installation policy date is {{fact:{production_id}}}."
                            if lang == "en"
                            else f"Der Herstellungsstichtag ist {{fact:{effective_id}}}; das Installationsdatum ist {{fact:{production_id}}}."
                        ),
                        refs=[battery["chunk_id"]],
                    )
                ],
            )
            mixed_request = request.model_copy(
                update={
                    "messages": [TurnMessage(role="user", content=production_question)]
                }
            )
            assert run(mixed_request, _generation(mixed_dates, facts), route).fallback
            reporting = next(
                hit
                for hit in result["hits"]
                if any(
                    exclusion_category(note["quote"]) == "reporting"
                    and note["lang"] == lang
                    for note in hit.get("qualifications", [])
                )
            )
            report_value = "1 month" if lang == "en" else "eines Monats"
            assert report_value in reporting["figures"].values(), (
                lang,
                reporting["figures"],
                reporting["qualifications"][-1],
            )
            report_request = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content=(
                                "How soon must I report a warranty defect?"
                                if lang == "en"
                                else "Wie schnell muss ich einen Garantiefall melden?"
                            ),
                        )
                    ]
                }
            )
            report_answer = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(
                        text=reporting["warranty_answers"]["reporting"],
                        refs=[reporting["chunk_id"]],
                    )
                ],
            )
            shipped_report = run(
                report_request, _generation(report_answer, facts), route
            )
            assert shipped_report.grounded and not shipped_report.fallback
            assert report_value in shipped_report.output.blocks[0].text
            assert (
                report_value in shipped_report.output.blocks[0].text.split("\n\n", 1)[0]
            )
            wrong_deadline = next(
                key
                for key, value in reporting["figures"].items()
                if value == ("12 months" if lang == "en" else "12 Monate")
            )
            deadline_swap = report_answer.model_copy(
                update={
                    "blocks": [
                        TextBlock(
                            text=(
                                f"Report the defect within {{fact:{wrong_deadline}}}."
                                if lang == "en"
                                else f"Melden Sie den Mangel innerhalb {{fact:{wrong_deadline}}}."
                            ),
                            refs=[reporting["chunk_id"]],
                        )
                    ]
                }
            )
            assert run(
                report_request, _generation(deadline_swap, facts), route
            ).fallback
            manual_text = (
                "Wireless coverage depends on the installation environment."
                if lang == "en"
                else "Die Funkabdeckung hängt von der Installationsumgebung ab."
            )
            manual_id = "independent-wireless-manual"
            distance_source = (
                "The antenna range is [n1=30 m]."
                if lang == "en"
                else "Die Reichweite der Antenne beträgt [n1=30 m]."
            )
            manual_facts = collect(
                "linker/search-knowledge",
                {
                    "hits": [
                        {
                            "chunk_id": manual_id,
                            "product_ids": [6528],
                            "title": "Wireless manual",
                            "doc_type": "manual",
                            "page": 1,
                            "doc_url": "https://example.test/manual.pdf",
                            "text": manual_text + "\n" + distance_source,
                            "figures": {f"{manual_id}.n1": "30 m"},
                        }
                    ]
                },
                lang,
            )
            joined = merge([facts, manual_facts])
            wireless_request = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content="What affects wireless coverage?"
                            if lang == "en"
                            else "Wovon hängt die Funkabdeckung ab?",
                        )
                    ]
                }
            )
            wireless = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(text=manual_text, refs=[manual_id]),
                    DocumentBlock(ref=manual_id),
                ],
            )
            assert run(wireless_request, _generation(wireless, joined), route).grounded
            mixed_request = request.model_copy(
                update={
                    "messages": [
                        TurnMessage(
                            role="user",
                            content="What affects wireless coverage, and what is the warranty?"
                            if lang == "en"
                            else "Wovon hängt die Funkabdeckung ab und wie lautet die Garantie?",
                        )
                    ]
                }
            )
            mixed_answer = TurnOutput(
                language=lang,
                blocks=[
                    TextBlock(text=manual_text, refs=[manual_id]),
                    TextBlock(
                        text=battery["warranty_answers"]["period"],
                        refs=[battery["chunk_id"]],
                    ),
                ],
            )
            mixed_result = run(mixed_request, _generation(mixed_answer, joined), route)
            assert mixed_result.grounded and not mixed_result.fallback
            assert mixed_result.output.blocks[0].text == (
                f"Technical source excerpt: “{manual_text}”"
                if lang == "en"
                else f"Technischer Quellenauszug: „{manual_text}“"
            )
            assert (
                "10 years" if lang == "en" else "10 Jahre"
            ) in mixed_result.output.blocks[1].text
            distance_text = (
                f"The antenna range is {{fact:{manual_id}.n1}}."
                if lang == "en"
                else f"Die Reichweite der Antenne beträgt {{fact:{manual_id}.n1}}."
            )
            numeric_mixed = mixed_answer.model_copy(
                update={
                    "blocks": [
                        TextBlock(text=distance_text, refs=[manual_id]),
                        mixed_answer.blocks[1],
                    ]
                }
            )
            numeric_result = run(
                mixed_request, _generation(numeric_mixed, joined), route
            )
            assert numeric_result.grounded and not numeric_result.fallback
            assert "30 m" in numeric_result.output.blocks[0].text
            wrong_manual = deepcopy(manual_facts)
            wrong_manual.knowledge_products[manual_id] = (6527,)
            assert run(
                mixed_request,
                _generation(mixed_answer, merge([facts, wrong_manual])),
                route,
            ).fallback
            untyped_manual = deepcopy(manual_facts)
            untyped_manual.technical_chunks.clear()
            assert run(
                mixed_request,
                _generation(mixed_answer, merge([facts, untyped_manual])),
                route,
            ).fallback
            # The same source-type marker must also come from the real index
            # and its current product authorization, not just a caller fixture.
            technical_payload = search(
                {
                    "query": "rated output power voltage current",
                    "lang": lang,
                    "product_ids": [6528],
                }
            )
            technical_hit = next(
                (
                    hit
                    for hit in technical_payload["hits"]
                    if hit.get("doc_type") in {"manual", "datasheet"}
                ),
                None,
            )
            assert technical_hit is not None, technical_payload["hits"]
            technical_facts = collect(
                "linker/search-knowledge", technical_payload, lang
            )
            assert technical_hit["chunk_id"] in technical_facts.technical_chunks
            technical_line = next(
                line
                for line in technical_hit["text"].splitlines()
                if line.strip().startswith("|") and "[n" in line
            )
            technical_quote = re.sub(
                r"\[n([1-9]\d*)=[^\[\]\n]+\]",
                lambda match, cid=technical_hit["chunk_id"]: (
                    f"{{fact:{cid}.n{match.group(1)}}}"
                ),
                technical_line,
            )
            real_mixed = mixed_answer.model_copy(
                update={
                    "blocks": [
                        TextBlock(
                            text=technical_quote, refs=[technical_hit["chunk_id"]]
                        ),
                        mixed_answer.blocks[1],
                    ]
                }
            )
            real_facts = merge([facts, technical_facts])
            real_result = run(mixed_request, _generation(real_mixed, real_facts), route)
            assert real_result.grounded and not real_result.fallback, (
                real_result.failures
            )
            assert real_result.output.blocks[0].text.startswith(
                "Technical source excerpt:"
                if lang == "en"
                else "Technischer Quellenauszug:"
            )
            assert any(
                isinstance(block, DocumentBlock)
                and block.url
                and block.url.startswith(technical_hit["doc_url"])
                for block in real_result.output.blocks
            )
            for statement, topic, question in (
                (
                    "It starts immediately." if lang == "en" else "Sie beginnt sofort.",
                    "start",
                    "When does the warranty start?"
                    if lang == "en"
                    else "Wann beginnt die Garantie?",
                ),
                (
                    "Every purchaser is eligible."
                    if lang == "en"
                    else "Alle Käufer sind anspruchsberechtigt.",
                    "overview",
                    "Who is eligible for the warranty?"
                    if lang == "en"
                    else "Wer hat Anspruch auf die Garantie?",
                ),
                (
                    "The policy applies to subsequent owners."
                    if lang == "en"
                    else "Die Regelung gilt für spätere Eigentümer.",
                    "overview",
                    "Can the warranty be transferred?"
                    if lang == "en"
                    else "Ist die Garantie übertragbar?",
                ),
            ):
                false_lead = TurnOutput(
                    language=lang,
                    blocks=[
                        TextBlock(text=statement, refs=[manual_id]),
                        TextBlock(
                            text=battery["warranty_answers"][topic],
                            refs=[battery["chunk_id"]],
                        ),
                    ],
                )
                policy_request = request.model_copy(
                    update={"messages": [TurnMessage(role="user", content=question)]}
                )
                result_with_false_lead = run(
                    policy_request, _generation(false_lead, joined), route
                )
                assert result_with_false_lead.fallback
                assert all(
                    not isinstance(block, TextBlock) or block.text != statement
                    for block in result_with_false_lead.output.blocks
                )
            stray_claim = mixed_answer.model_copy(
                update={
                    "blocks": [
                        *mixed_answer.blocks,
                        TextBlock(
                            text="It is fully covered."
                            if lang == "en"
                            else "Es ist vollständig abgedeckt.",
                            refs=[manual_id],
                        ),
                    ]
                }
            )
            assert run(mixed_request, _generation(stray_claim, joined), route).fallback
            for extra in (
                HandoffBlock(
                    summary="All damage is covered by the warranty."
                    if lang == "en"
                    else "Die Garantie deckt alle Schäden ab."
                ),
                AskBlock(
                    field="application",
                    options=[
                        "All damage is covered"
                        if lang == "en"
                        else "Alle Schäden sind abgedeckt"
                    ],
                ),
            ):
                hidden = mixed_answer.model_copy(
                    update={"blocks": [*mixed_answer.blocks, extra]}
                )
                assert run(mixed_request, _generation(hidden, joined), route).fallback
        changed_source = deepcopy(raw)
        sheet = proof["warranty_scope"]["datasheet"]["document_id"]
        next(d for d in changed_source["documents"] if d["document_id"] == sheet)[
            "product_ids"
        ] = []
        revoked = KnowledgeSearch(lambda: index, publication=authority(changed_source))(
            {"query": "warranty period conditions", "lang": "en", "product_ids": [6528]}
        )
        assert not any("-warranty-" in hit["chunk_id"] for hit in revoked["hits"])
    finally:
        index.close()
    for changed_id in (
        proof["warranty_scope"]["policy"]["term_row"]["source"]["chunk_id"],
        proof["warranty_scope"]["policy"]["term_sources"]["start"]["chunk_id"],
    ):
        with sqlite3.connect(db) as connection:
            old_text = connection.execute(
                "SELECT text FROM chunks WHERE id=?", (changed_id,)
            ).fetchone()[0]
            connection.execute(
                "UPDATE chunks SET text=? WHERE id=?",
                (old_text + " altered", changed_id),
            )
        index = DocumentIndex(db, encoder=None)
        try:
            result = KnowledgeSearch(
                lambda index=index: index, publication=authority(raw)
            )(
                {
                    "query": "warranty period conditions",
                    "lang": "en",
                    "product_ids": [6528],
                }
            )
            assert not any(
                "-warranty-terms-" in hit["chunk_id"]
                and hit["document_id"] == proof["document_ids"][0]
                for hit in result["hits"]
            )
        finally:
            index.close()
        with sqlite3.connect(db) as connection:
            connection.execute(
                "UPDATE chunks SET text=? WHERE id=?", (old_text, changed_id)
            )
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT value FROM meta WHERE key='external_axis_anchors'"
        ).fetchone()
        saved = json.loads(row[0])
        del saved[cover_id]
        connection.execute(
            "UPDATE meta SET value=? WHERE key='external_axis_anchors'",
            (json.dumps(saved),),
        )
    index = DocumentIndex(db, encoder=None)
    try:
        result = KnowledgeSearch(lambda: index, publication=authority(raw))(
            {"query": "warranty period conditions", "lang": "en", "product_ids": [6528]}
        )
        assert not any("-warranty-" in hit["chunk_id"] for hit in result["hits"])
    finally:
        index.close()
