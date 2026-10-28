"""Original policy rows remain conditional through the actual knowledge consumer."""

import gzip
import hashlib
import json
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
from linker_genie.facts import collect
from linker_genie.hydrate import hydrate
from linker_genie.knowledge import KnowledgeSearch
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import DocumentBlock, TextBlock, TurnOutput
from linker_genie.warranty_scope import exclusion_category


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
    raw, _, model, model_scope, procedures, proc_scopes, terms, term_scopes = _compile()
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
        [model, *procedures, *terms],
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
