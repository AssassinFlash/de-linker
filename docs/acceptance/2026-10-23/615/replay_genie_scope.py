"""Read-only replay of cached source scope, with a captured native Woo identity oracle.

No HTTP authority, Docling parser, OCR or model provider is called. Cached Docling
JSON and the already cached tokenizer supply exact matching chunk provenance.
The baseline report is a separately measured frozen comparison, not a new source
of publication permission. Run in the locked Genie environment.
"""

import argparse
import collections
import copy
import hashlib
import json
import re
import sqlite3
import sys
import time
from dataclasses import replace
from pathlib import Path

import httpx
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "services" / "genie"))

from index.chunking import Chunk, DocumentMeta, chunk_document
from index.extract import extract
from index.publication import _model_pattern, scope_proofs
from index.tokenizer import HFTokenizer
from linker_genie.publication import PublicationClient
from linker_genie.publication_scope import authorize_chunk, table_header
from linker_genie.retrieval import DocumentIndex, is_passage

parser = argparse.ArgumentParser(description=__doc__)
for name in (
    "manifest",
    "woo-identities",
    "cached-index",
    "parsed-root",
    "tokenizer",
    "baseline-report",
    "output",
):
    parser.add_argument("--" + name, required=True, type=Path)
args = parser.parse_args()
manifest_path = args.manifest
identity_path = args.woo_identities
cached_path = args.cached_index
raw = json.loads(manifest_path.read_text())
identities = json.loads(identity_path.read_text())
known = identities["models"]
db = sqlite3.connect(f"file:{cached_path}?mode=ro", uri=True)
chunks = [
    Chunk(*r)
    for r in db.execute(
        "SELECT id,doc_sha256,page,section,kind,header,text,lang,tokens FROM chunks"
    )
]
trace = collections.Counter()
source_shas = {d["blob_sha256"] for d in raw["documents"]}
by_id_for_trace = {chunk.id: chunk for chunk in chunks}
tokenizer = HFTokenizer(Tokenizer.from_file(str(args.tokenizer)))
traced = {}
trace_failures = []
trace_start = time.monotonic()
for sha in sorted(source_shas):
    parsed = args.parsed_root / sha
    if (
        not (parsed / "status.json").is_file()
        or not (parsed / "docling.json").is_file()
    ):
        trace["missing_cached_parse"] += 1
        continue
    status = json.loads((parsed / "status.json").read_text())
    row = db.execute(
        "SELECT title_en,title_de,brands,doc_type,lang FROM documents WHERE sha256=?",
        (sha,),
    ).fetchone()
    if row is None:
        trace["missing_cached_document"] += 1
        continue
    model_labels = tuple(
        r[0]
        for r in db.execute(
            "SELECT model FROM document_models WHERE doc_sha256=? ORDER BY model",
            (sha,),
        )
    )
    meta = DocumentMeta(
        sha, row[0], row[1], tuple(json.loads(row[2])), model_labels, row[3], row[4]
    )
    try:
        native = chunk_document(
            meta,
            extract(parsed, status["pages"], status["garbled_pages"]),
            tokenizer,
            lambda _: "en",
        )
        valid = {
            c.id
            for c in native
            if c.id in by_id_for_trace
            and c.text == by_id_for_trace[c.id].text
            and c.header == by_id_for_trace[c.id].header
            and c.section == by_id_for_trace[c.id].section
            and c.kind == by_id_for_trace[c.id].kind
        }
        for c in native:
            if c.id in valid and all(cid in valid for cid in c.preceding_text):
                old_chunk = by_id_for_trace[c.id]
                traced[c.id] = replace(
                    old_chunk,
                    source_table=c.source_table,
                    preceding_text=c.preceding_text,
                )
        trace["cached_parses_read"] += 1
        trace["native_chunks"] += len(native)
        trace["exactly_matched_chunks"] += len(valid)
    except (OSError, ValueError, KeyError, TypeError) as error:
        trace_failures.append({"blob_sha256": sha, "error": type(error).__name__})
    if trace["cached_parses_read"] % 25 == 0:
        print("cached-parse provenance", dict(trace), flush=True)
chunks = [traced.get(c.id, c) for c in chunks]
trace["table_fragments_with_provenance"] = sum(
    bool(c.source_table and c.preceding_text) for c in chunks
)
trace_seconds = round(time.monotonic() - trace_start, 2)
print("provenance complete", dict(trace), "seconds", trace_seconds, flush=True)

baseline = json.loads(args.baseline_report.read_text())
assert (
    baseline["evidence"]["manifest_sha256"]
    == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
)
assert (
    baseline["evidence"]["woo_identity_sha256"]
    == hashlib.sha256(identity_path.read_bytes()).hexdigest()
)
requests = collections.Counter()


def authority(names):
    patterns = [
        (m, re.compile(r"(?<![^\W_])" + re.escape(m) + r"(?![^\W_])", re.IGNORECASE))
        for m in names
    ]

    def handle(request):
        body = json.loads(request.content)
        if "models" in body:
            requests["exact_batches"] += 1
            models = body["models"]
        else:
            requests["text_batches"] += 1
            text = re.sub(r"\s+", " ", body["text"])
            models = [m for m, p in patterns if p.search(text)]
        return httpx.Response(
            200,
            json={
                "models": [
                    {"model": m, "status": names.get(m.casefold(), "unknown")}
                    for m in models
                ]
            },
        )

    return PublicationClient(
        "https://native-woo-snapshot.test", httpx.MockTransport(handle)
    )


started = time.monotonic()
before = {}
after = scope_proofs(chunks, raw, authority(known))
documents = {d["document_id"]: d for d in raw["documents"]}
by_chunk = {c.id: c for c in chunks}
associated = {d["blob_sha256"] for d in raw["documents"]}


def covered(proof):
    out = collections.defaultdict(set)
    for cid, pids in proof.items():
        for pid in pids:
            out[pid].add(by_chunk[cid].doc_sha256)
    ready = []
    for p in raw["products"]:
        required = {
            documents[did]["blob_sha256"] for did in p["documents"] if did in documents
        }
        if required and required.issubset(out[p["product_id"]]):
            ready.append(p["product_id"])
    return out, ready


old_coverage, old_ready = covered(before)
new_coverage, new_ready = covered({cid: p["product_ids"] for cid, p in after.items()})
old_docs = {by_chunk[c].doc_sha256 for c in before}
new_docs = {by_chunk[c].doc_sha256 for c in after}
foreign_patterns = [
    _model_pattern(label) for label, status in known.items() if status == "unavailable"
]
foreign_cache = {}


def names_unavailable(c):
    if c.id not in foreign_cache:
        foreign_cache[c.id] = any(
            p.search(c.section + "\n" + c.text) for p in foreign_patterns
        )
    return foreign_cache[c.id]


foreign = {cid for cid in after if names_unavailable(by_chunk[cid])}
withdrawn = copy.deepcopy(raw)
withdrawn["products"] = [p for p in withdrawn["products"] if p["product_id"] != 4107]
for d in withdrawn["documents"]:
    d["product_ids"] = [pid for pid in d["product_ids"] if pid != 4107]
withdrawn["documents"] = [d for d in withdrawn["documents"] if d["product_ids"]]
revoked_known = {**known, "h2-10k-t3": "unavailable"}
revoked = scope_proofs(chunks, withdrawn, authority(revoked_known))
withdrawn_pattern = _model_pattern("H2-10K-T3")
specific_revoked = {
    c.id for c in chunks if withdrawn_pattern.search(c.section + "\n" + c.text)
}
rowids = dict(db.execute("SELECT id,rowid FROM chunks"))
revisions = {p["product_id"]: p["product_revision"] for p in raw["products"]}
links = [
    {
        "document_id": d["document_id"],
        "document_revision": d["document_revision"],
        "blob_sha256": d["blob_sha256"],
        "url": d["url"],
        "product_id": pid,
        "product_revision": revisions[pid],
    }
    for d in documents.values()
    for pid in d["product_ids"]
    if pid in revisions
]
permitted = {}
covered_links = collections.defaultdict(set)
for cid, proof in after.items():
    c = by_chunk[cid]
    authorized = authorize_chunk(c.doc_sha256, proof["product_ids"], links, proof)
    if authorized:
        restored_header = table_header(
            proof, proof["product_ids"], {p["product_id"]: p for p in raw["products"]}
        )
        if restored_header is None:
            continue
        d = authorized[0]
        permitted[rowids[cid]] = {
            "document_id": d["document_id"],
            "document_revision": d["document_revision"],
            "url": d["url"],
            "product_ids": proof["product_ids"],
            "table_header": restored_header,
        }
        if is_passage(c.text):
            for a in authorized:
                covered_links[a["product_id"]].add(a["document_id"])
row_chunks = {rowids[c.id]: c for c in chunks}
usable_ids = {
    pid
    for row, p in permitted.items()
    for pid in p["product_ids"]
    if is_passage(row_chunks[row].text)
}


class ProofIndex(DocumentIndex):
    def permissions(self, snapshot, requested):
        wanted = (
            set(snapshot.products)
            if requested is None
            else {snapshot.canonical(pid) for pid in requested}
        )
        return {
            row: p
            for row, p in permitted.items()
            if wanted.intersection(p["product_ids"])
            and set(p["product_ids"]).issubset(snapshot.products)
        }


by_model = {
    p["model"].casefold(): p["product_id"] for p in raw["products"] if p.get("model")
}
golden = []
for line in (
    (Path(__file__).resolve().parents[4] / "services/genie/index/eval/golden.jsonl")
    .read_text()
    .splitlines()
):
    q = json.loads(line)
    pid = by_model.get(q["model"].casefold())
    if pid is not None and any(
        e["doc_sha256"]
        in {d["blob_sha256"] for d in documents.values() if pid in d["product_ids"]}
        for e in q["evidence"]
    ):
        golden.append((q, pid))


def evidence_eligible(proof, q, pid):
    return any(
        pid in ids
        and any(
            e["doc_sha256"] == by_chunk[cid].doc_sha256
            and e["page"] == by_chunk[cid].page
            for e in q["evidence"]
        )
        for cid, ids in proof.items()
    )


eligibility = {
    "current_associated_goldens": len(golden),
    "before_with_evidence": sum(evidence_eligible(before, q, pid) for q, pid in golden),
    "after_with_evidence": sum(
        evidence_eligible({cid: p["product_ids"] for cid, p in after.items()}, q, pid)
        for q, pid in golden
    ),
}
failures = collections.Counter()
page_chunks = collections.defaultdict(list)
for c in chunks:
    page_chunks[(c.doc_sha256, c.page)].append(c)
for q, pid in golden:
    expected = [
        c for e in q["evidence"] for c in page_chunks[(e["doc_sha256"], e["page"])]
    ]
    released = [
        c
        for c in expected
        if rowids[c.id] in permitted and pid in permitted[rowids[c.id]]["product_ids"]
    ]
    if released:
        failures["expected_page_available"] += 1
        continue
    if not expected:
        failures["cached_expected_page_absent"] += 1
        continue
    scoped = [
        c for c in expected if c.id in after and pid in after[c.id]["product_ids"]
    ]
    if scoped:
        failures["scoped_page_without_complete_association_group"] += 1
        continue
    if any(names_unavailable(c) for c in expected):
        failures["expected_page_contains_unavailable_model"] += 1
        continue
    model_pattern = _model_pattern(q["model"])
    if not any(model_pattern.search(c.section + "\n" + c.text) for c in expected):
        failures["unnamed_or_variant_page_without_proven_scope"] += 1
    else:
        failures["current_model_page_has_unknown_or_unassociated_scope"] += 1
replays = []
seen = set()
before_index = DocumentIndex(cached_path, encoder=None)
after_index = ProofIndex(cached_path, encoder=None)
from linker_genie.publication import Snapshot

for q, pid in golden:
    group = q["model"], q["code"].split("-")[0]
    if q["lang"] != "en" or group in seen:
        continue
    seen.add(group)
    initial = before_index.search(q["question"], "en", [pid])
    checked = after_index.search(
        q["question"], "en", [pid], publication=Snapshot.read(raw)
    )
    expected = {(e["doc_sha256"], e["page"]) for e in q["evidence"]}
    replays.append(
        {
            "id": q["id"],
            "model": q["model"],
            "question": q["question"],
            "before_page_hit": bool(
                expected.intersection((h.doc_sha256, h.page) for h in initial)
            ),
            "after_page_hit": bool(
                expected.intersection((h.doc_sha256, h.page) for h in checked)
            ),
            "after_hits": len(checked),
        }
    )
    if len(replays) == 12:
        break
before_index.close()
after_index.close()
examples = []
for c in chunks:
    if c.id in after and c.id not in before and ("IP65" in c.text or "50Hz" in c.text):
        examples.append(
            {
                "chunk_id": c.id,
                "page": c.page,
                "basis": after[c.id]["basis"],
                "product_ids": after[c.id]["product_ids"],
                "text": c.text[:500],
            }
        )
        if len(examples) == 3:
            break
report = {
    "evidence": {
        "cached_index": str(cached_path),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "woo_identity_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "woo_captured_at_utc": identities["captured_at_utc"],
        "mode": "read-only cached corpus with native Woo identity snapshot; HTTP transport simulated from that snapshot, not live HTTP acceptance",
    },
    "scope": {
        "products": len(raw["products"]),
        "documents": len(raw["documents"]),
        "unique_shas": len(associated),
        "all_cached_chunks": len(chunks),
        "associated_chunks": sum(c.doc_sha256 in associated for c in chunks),
        "no_synthetic_records": all(p["product_id"] < 8000 for p in raw["products"]),
    },
    "before": baseline["before"],
    "trace": {**dict(trace), "failures": trace_failures, "seconds": trace_seconds},
    "after": {
        "proven_chunks": len(after),
        "covered_document_shas": len(new_docs),
        "products_with_any_passage": len(new_coverage),
        "ready_products_under_old_all_documents_rule": len(new_ready),
        "available_products_under_new_safe_passage_rule": len(usable_ids),
        "preparation_complete": len(new_ready) == len(raw["products"]),
        "basis": dict(collections.Counter(p["basis"] for p in after.values())),
    },
    "isolation": {
        "passages_naming_native_unavailable_model": baseline["isolation"][
            "passages_naming_native_unavailable_model"
        ],
        "those_released": len(foreign.intersection(after)),
        "unassociated_chunks_released": sum(
            by_chunk[c].doc_sha256 not in associated for c in after
        ),
        "withdraw_H2_10K_T3": {
            "still_authorized_ids": sum(
                4107 in p["product_ids"] for p in revoked.values()
            ),
            "explicit_withdrawn_passages_released": len(
                specific_revoked.intersection(revoked)
            ),
        },
    },
    "golden": {
        **eligibility,
        "before_with_evidence": baseline["golden"]["before_with_evidence"],
        "failure_distribution": dict(failures),
        "ranker": "offline BM25, no provider calls; page retrieval, not generated-answer acceptance",
        "limited_replay": replays,
        "limited_before_page_hits": sum(r["before_page_hit"] for r in replays),
        "limited_after_page_hits": sum(r["after_page_hit"] for r in replays),
    },
    "examples": examples,
    "oracle_fixture_requests": dict(requests),
    "elapsed_seconds": round(time.monotonic() - started, 2),
}
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
