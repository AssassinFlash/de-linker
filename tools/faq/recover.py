#!/usr/bin/env python3
"""Recovery round for the FAQ corpus (PR #58 review ①/②, S7, unifications).

Buckets, read from docs/faq/<slug>.json:
- gate-withdrawn (58): re-run the fixed whole-page gate; survivors get an
  independent re-review whose input carries no gate, status or reason fields
  (S4 projection). A pass verdict recovers the item; a reject sends it to the
  rewrite flow; a withdraw keeps it withdrawn with the reviewer's basis.
- rejects (19): rewritten from the question's original angle against fresh
  retrieval (fixed pipeline, full chunk text), then re-gated and re-reviewed.
  Terminal state: pass, or withdrawn with the documented basis.
- named unifications: the six "Is the IOT dongle required?" answers get one
  wording (the guide's own "Muss konfiguriert werden" row, nothing more);
  GW125 "What does one cabinet contain?" is rewritten to answer containment.
- S7 (review ruling): a pass citation pointing at a DE document switches to
  the EN twin when the index holds one and one of its pages carries every
  number of the answer. Products without an indexed EN version keep the DE
  citation with EN answers.

Writes docs/faq/<slug>.{json,md} only with --write. Run inside the genie env:

  uv run --project services/genie python tools/faq/recover.py [--write]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCS = ROOT / "docs" / "faq"
sys.path.insert(0, str(HERE))
import generate as gen

GATE_REASON = "a number is not in the cited passage"

REWRITE_SYSTEM = """You repair one rejected product FAQ answer for Linker Technology GmbH (B2B solar/storage, Germany).
Output a JSON object only: {"question_en","question_de","answer_en","answer_de","status" ("pass"|"withdrawn"),"withdraw_reason","citation" {url, page, title}}.
Rules:
- Fix exactly the named problem. Keep the question's angle; answer the question asked, not a nearby one.
- Ground every sentence in the retrieved passages of THIS product. Every number in the answer must appear in the passage you cite (url and page from those passages).
- Do not extrapolate: no advice, framing or pairing the passages do not state. If the passages do not answer the question, status=withdrawn and withdraw_reason says precisely what the passages do and do not carry.
- English and German, same facts. German: Sie form (de_DE_formal). Never du/ihr.
- Forbidden: "not X but Y" / "nicht … sondern …", groups of three parallel clauses, em dashes as drama.
- Answers are for installers reading a product page: specific, short, no marketing fluff.
"""

# S7 (review ruling): EN FAQ cites the EN document. Pairs verified in the index
# this session (2026-10-10): same manual, both editions indexed chunk-per-page.
EN_TWINS = {
    "GW_ESA-261kWh_User-Manual-DE_V1.6.pdf": "GW_ESA-261kWh_User-Manual-EN_V1.6.pdf",
    "GW_BAT-C-208-261kWh_User-Manual-DE_V1.0.pdf": "GW_BAT-C-208-261kWh_User-Manual-EN.pdf",
    "GW_HCA-G2_User-Manual-DE.pdf": "GW_HCA-G2_User-Manual-EN.pdf",
    "SAJ_HS2_6-10K-T2_Datasheet_DE.pdf": "saj_hs2_5_10k_t2_x_datasheet_en.pdf",
    # hs2-as2-manual-en.pdf exists but holds 0 indexed chunks — the switcher
    # documents the keep-DE instead of switching blind.
    "SAJ_HS2-AS2_5-10K-T2_User-Manual_DE_V0.3.pdf": "hs2-as2-manual-en.pdf",
}
DONGLE_Q = "Is the IOT dongle required?"
GW125_SLUG = "goodwe-esa-gw125-261-esa-lcn-g10"
GW125_DRIFT = (
    "Angle drift: the question asks what the cabinet CONTAINS (scope of supply, "
    "what is in it), but the answer lists rated electrical figures instead. "
    "Answer the containment question from the manual's contents/packing/scope "
    "information; if the passages name no contents, withdraw with that basis."
)
DONGLE_INSTRUCTION = (
    "Unified corpus wording: the guide lists the EcoFlow IOT Dongle ESS as "
    "'Muss konfiguriert werden' (must be configured) during commissioning. "
    "State exactly that requirement in your own words with the German row quoted; "
    "do not claim anything beyond the guide's wording."
)
DONGLE_UNIFIED = (
    "Corpus unification: sibling products carry this exact answer — 'The installation guide "
    'lists the EcoFlow IOT Dongle ESS with the note "Muss konfiguriert werden" (must be '
    "configured).' State that, and nothing else: no page numbers, no references to other pages "
    "or documents, no other dongle models. Cite the page whose table carries the row."
)

_DB: sqlite3.Connection | None = None


def db() -> sqlite3.Connection:
    global _DB
    if _DB is None:
        path = gen.INDEX_DEFAULT
        _DB = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    return _DB


def doc(url_fragment: str) -> dict[str, Any] | None:
    row = (
        db()
        .execute(
            "SELECT sha256, url, title_en, doc_type, lang, pages FROM documents WHERE url LIKE ?",
            (f"%{url_fragment}%",),
        )
        .fetchone()
    )
    if not row:
        return None
    return {
        "sha256": row[0],
        "url": row[1],
        "title": row[2],
        "doc_type": row[3],
        "lang": row[4],
        "pages": row[5],
    }


def page_chunks(url: str, page: int) -> list[dict[str, Any]]:
    rows = (
        db()
        .execute(
            "SELECT c.text FROM chunks c JOIN documents d ON c.doc_sha256 = d.sha256"
            " WHERE d.url = ? AND c.page = ? ORDER BY c.rowid",
            (url, page),
        )
        .fetchall()
    )
    return [{"url": url, "page": page, "text": t} for (t,) in rows]


def page_passages(url: str, page: int) -> dict[tuple[str, int], str]:
    return gen.flatten_passages([[h] for h in page_chunks(url, page)])


def load_corpus() -> list[dict[str, Any]]:
    out = []
    for path in sorted(DOCS.glob("*.json")):
        if path.name in {"questions.json", "summary.json"}:
            continue
        out.append(json.loads(path.read_text()))
    return out


def item_of(payload: dict[str, Any], index: int) -> dict[str, Any]:
    return payload["items"][index]


def to_model_item(rec: dict[str, Any]) -> dict[str, Any]:
    """Record shape -> generator item shape (answer/answer_en naming)."""
    return {
        "question_en": rec["question"],
        "question_de": rec["question_de"],
        "answer_en": rec["answer"],
        "answer_de": rec["answer_de"],
        "citation": rec["citation"],
    }


def to_record(
    item: dict[str, Any], status: str, review: str, reason: str
) -> dict[str, Any]:
    return gen.to_record(item, status, review, reason)


def regate(rec: dict[str, Any], skip: tuple[str, ...]) -> tuple[str, str, list[str]]:
    """Fixed gate on the record's cited page. Returns (status, reason, missing numbers)."""
    cite = rec["citation"]
    passages = page_passages(cite["url"], int(cite["page"]))
    item = to_model_item(rec)
    item["status"] = "pass"
    status, reason = gen.gate_item(item, passages, skip)
    missing: list[str] = []
    if status == "withdrawn" and reason == GATE_REASON:
        text = passages.get((cite["url"], int(cite["page"])), "")
        hay = text.replace(",", ".")
        for ans in (rec["answer"], rec["answer_de"]):
            cleaned = gen.MODELISH.sub(" ", ans)
            for token in skip:
                if token:
                    cleaned = cleaned.replace(token, " ")
            for raw in gen.NUMBER.findall(cleaned):
                if (
                    raw.replace(",", ".") not in hay
                    and raw not in text
                    and raw not in missing
                ):
                    missing.append(raw)
    return status, reason, missing


def review_batch(
    key: str,
    endpoint: str,
    model: str,
    payload: dict[str, Any],
    batch: list[tuple[int, dict[str, Any]]],
) -> dict[int, dict[str, Any]]:
    """One independent review call for the batch; input is the S4 projection."""
    items = [item for _, item in batch]
    hits = []
    for _, item in batch:
        cite = item["citation"]
        hits.append(page_chunks(cite["url"], int(cite["page"])))
    verdicts = gen.review_items(key, endpoint, model, payload, items, hits)
    by_index = {}
    for v in verdicts:
        if not isinstance(v, dict):
            continue
        raw = v.get("index")
        idx = (
            raw
            if isinstance(raw, int)
            else int(str(raw))
            if str(raw).isdigit()
            else None
        )
        if idx is not None:
            by_index[idx] = v
    return by_index


def rewrite(
    key: str,
    endpoint: str,
    model: str,
    payload: dict[str, Any],
    rec: dict[str, Any],
    problem: str,
    skip: tuple[str, ...],
    instruction: str = "",
) -> tuple[dict[str, Any], str, str]:
    """Rewrite one record against fresh retrieval; gate-clean or withdrawn.

    Returns (model item, gate status, gate reason). Retries only on
    deterministic copy-tell rejections, naming the tell.
    """
    question = rec["question"]
    hits = gen.retrieve(payload["id"], [question])
    cite = rec["citation"]
    have = {(h["url"], int(h["page"])) for group in hits for h in group}
    if (cite["url"], int(cite["page"])) not in have:
        hits.append(page_chunks(cite["url"], int(cite["page"])))
    passages = gen.flatten_passages(hits)
    user = json.dumps(
        {
            "product": {
                "id": payload["id"],
                "slug": payload["slug"],
                "model": payload.get("model"),
            },
            "question": question,
            "question_de": rec["question_de"],
            "rejected_answer_en": rec["answer"],
            "rejected_answer_de": rec["answer_de"],
            "reviewer_problem": problem,
            "instruction": instruction,
            "passages": hits,
        },
        ensure_ascii=False,
    )
    tell = ""
    for attempt in range(3):
        extra = (
            f"Your previous wording was rejected by the deterministic copy check: {tell}. Rephrase."
            if tell
            else ""
        )
        data = gen.chat(key, endpoint, model, REWRITE_SYSTEM, user + extra)
        item = data if isinstance(data, dict) else {}
        item.setdefault("citation", cite)
        item["question_en"] = item.get("question_en") or question
        item["question_de"] = item.get("question_de") or rec["question_de"]
        if str(item.get("status")) == "withdrawn":
            return item, "withdrawn", str(item.get("withdraw_reason") or "unsupported")
        # Gate against the whole page the answer cites: retrieval may have
        # sliced only some chunks of that page, and judging the numbers on a
        # slice re-creates the original defect inside the recovery itself.
        item_cite = (
            item.get("citation") if isinstance(item.get("citation"), dict) else cite
        )
        try:
            item_page = int(item_cite.get("page") or 0)
        except (TypeError, ValueError):
            item_page = 0
        gate_passages = dict(passages)
        if item_page >= 1 and item_cite.get("url"):
            gate_passages.update(page_passages(item_cite["url"], item_page))
        gate_status, gate_reason = gen.gate_item(item, gate_passages, skip)
        if gate_status == "pass":
            return item, gate_status, gate_reason
        if gate_status == "reject":
            tell = gate_reason
            continue
        return item, gate_status, gate_reason  # withdrawn: number not carried
    return item, "reject", f"copy tell persists after 3 attempts: {tell}"


def s7_switch(
    payload: dict[str, Any], rec: dict[str, Any], skip: tuple[str, ...]
) -> str:
    """Point a DE citation at the EN twin page that carries every number.

    Returns a ledger line; leaves the record untouched when no EN page
    verifies (stays DE per the ruling: no usable EN version).
    """
    cite = rec["citation"]
    de_name = cite["url"].rsplit("/", 1)[-1]
    en_name = EN_TWINS.get(de_name)
    if not en_name:
        return f"S7 keep-DE {payload['slug'][:36]:36s} no indexed EN twin for {de_name}"
    en = doc(en_name)
    if not en or not en["pages"]:
        return f"S7 keep-DE {payload['slug'][:36]:36s} EN twin not indexed: {en_name}"
    want = int(cite["page"])
    candidates: list[tuple[int, int]] = []  # (order distance, page)
    for p in range(1, int(en["pages"]) + 1):
        passages = page_passages(en["url"], p)
        text = passages.get((en["url"], p), "")
        if not text:
            continue
        item = {
            "status": "pass",
            "answer_en": rec["answer"],
            "answer_de": rec["answer_de"],
            "citation": {"url": en["url"], "page": p},
        }
        if gen.gate_item(item, passages, skip)[0] == "pass":
            candidates.append((abs(p - want), p))
    if not candidates:
        return f"S7 keep-DE {payload['slug'][:36]:36s} no EN page of {en_name} carries the answer's numbers"
    candidates.sort()
    new_page = candidates[0][1]
    rec["citation"] = {"url": en["url"], "page": new_page, "title": en["title"]}
    return f"S7 switch  {payload['slug'][:36]:36s} {de_name} p.{want} -> {en_name} p.{new_page}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Write docs/faq/<slug>.{json,md}"
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Round 2: rewrite only current rejects plus the not-yet-unified dongle withdrawals; named buckets are terminal.",
    )
    parser.add_argument(
        "--pointed",
        type=Path,
        help="Round 3+: rewrite exactly the listed items (slug, question, instruction with ground truth transcribed from the index).",
    )
    args = parser.parse_args()
    key, endpoint, model = gen.load_deepseek()
    gen.load_aihubmix()
    index = gen.document_index()
    print(
        f"retrieval encoder available: {getattr(index, 'encoder', None) is not None}",
        flush=True,
    )

    corpus = load_corpus()
    ledger: list[str] = []
    counts: Counter[str] = Counter()

    # ---- classify work ----------------------------------------------------
    regate_work: list[tuple[dict[str, Any], int]] = []
    rewrite_work: list[
        tuple[dict[str, Any], int, str, str]
    ] = []  # payload, idx, problem, instruction
    for payload in corpus:
        skip = tuple(
            t
            for t in (
                payload.get("model") or "",
                payload.get("sku") or "",
                payload.get("title") or "",
            )
            if t
        )
        if args.retry:
            for i, rec in enumerate(payload["items"]):
                if rec["status"] == "reject":
                    rewrite_work.append((payload, i, rec["reason"], ""))
                elif rec["status"] == "withdrawn" and rec["question"] == DONGLE_Q:
                    rewrite_work.append(
                        (
                            payload,
                            i,
                            "verdict not yet unified with sibling products",
                            DONGLE_UNIFIED,
                        )
                    )
            continue
        if args.pointed:
            wanted = {
                (e["slug"], e["question"]): e["instruction"]
                for e in json.loads(args.pointed.read_text())
            }
            for i, rec in enumerate(payload["items"]):
                instruction = wanted.get((payload["slug"], rec["question"]))
                if instruction:
                    rewrite_work.append(
                        (
                            payload,
                            i,
                            "pointed fix with ground truth from the index",
                            instruction,
                        )
                    )
            continue
        for i, rec in enumerate(payload["items"]):
            if rec["status"] == "withdrawn" and rec["reason"] == GATE_REASON:
                regate_work.append((payload, i))
            elif rec["status"] == "reject" and rec["question"] == DONGLE_Q:
                rewrite_work.append(
                    (
                        payload,
                        i,
                        DONGLE_INSTRUCTION,
                        "",
                    )
                )
            elif rec["status"] == "reject":
                rewrite_work.append((payload, i, rec["reason"], ""))
            elif rec["status"] == "pass" and rec["question"] == DONGLE_Q:
                rewrite_work.append(
                    (
                        payload,
                        i,
                        DONGLE_INSTRUCTION,
                        "",
                    )
                )
            elif (
                rec["status"] == "pass"
                and payload["slug"] == GW125_SLUG
                and rec["question"].startswith("What does one")
            ):
                rewrite_work.append((payload, i, GW125_DRIFT, ""))
    print(
        f"regate bucket: {len(regate_work)}  rewrite bucket: {len(rewrite_work)}",
        flush=True,
    )

    # ---- pass 1: re-gate the 58 -------------------------------------------
    review_queue: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for payload, i in regate_work:
        skip = tuple(
            t
            for t in (
                payload.get("model") or "",
                payload.get("sku") or "",
                payload.get("title") or "",
            )
            if t
        )
        rec = item_of(payload, i)
        status, reason, missing = regate(rec, skip)
        if status == "withdrawn":
            basis = (
                f"{reason} — the cited page does not contain: {', '.join(missing)}"
                if missing
                else reason
            )
            payload["items"][i] = to_record(
                to_model_item(rec), "withdrawn", "withdrawn", basis
            )
            counts["gate-still-withdrawn"] += 1
            ledger.append(
                f"REGATE   {payload['slug'][:36]:36s} stays withdrawn :: {basis[:80]}"
            )
        else:
            review_queue.setdefault(payload["slug"], []).append((i, to_model_item(rec)))
            counts["gate-pass-to-review"] += 1
    print(f"pass 1 done: {dict(counts)}", flush=True)

    # ---- pass 2: rewrites (19 rejects + named) -----------------------------
    rewrite_review_queue: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for payload, i, problem, instruction in rewrite_work:
        skip = tuple(
            t
            for t in (
                payload.get("model") or "",
                payload.get("sku") or "",
                payload.get("title") or "",
            )
            if t
        )
        rec = item_of(payload, i)
        try:
            item, status, reason = rewrite(
                key, endpoint, model, payload, rec, problem, skip, instruction
            )
        except Exception as exc:  # noqa: BLE001 — one failed item must not stop the round.
            counts["rewrite-error"] += 1
            ledger.append(f"REWRITE  {payload['slug'][:36]:36s} ERROR {str(exc)[:80]}")
            continue
        if status == "pass":
            rewrite_review_queue.setdefault(payload["slug"], []).append((i, item))
            counts["rewrite-to-review"] += 1
            ledger.append(f"REWRITE  {payload['slug'][:36]:36s} gated pass, to review")
        elif status == "reject":
            payload["items"][i] = to_record(
                item,
                "withdrawn",
                "withdrawn",
                f"answer wording rejected by the copy gate, stays out: {reason}",
            )
            counts["rewrite-copy-reject"] += 1
            ledger.append(
                f"REWRITE  {payload['slug'][:36]:36s} copy-reject, withdrawn :: {reason[:80]}"
            )
        else:
            payload["items"][i] = to_record(item, "withdrawn", "withdrawn", reason)
            counts["rewrite-withdrawn"] += 1
            ledger.append(
                f"REWRITE  {payload['slug'][:36]:36s} withdrawn :: {reason[:80]}"
            )
        print(
            f"  rewrite {payload['slug'][:30]} [{rec['question'][:36]}] -> {status}",
            flush=True,
        )

    # ---- pass 3: independent re-review of all survivors ---------------------
    key2, endpoint2, model2 = (
        key,
        endpoint,
        model,
    )  # one fresh call per batch; no shared history
    for queue, origin in ((review_queue, "recover"), (rewrite_review_queue, "rewrite")):
        for slug, batch in queue.items():
            payload = next(p for p in corpus if p["slug"] == slug)
            try:
                verdicts = review_batch(key2, endpoint2, model2, payload, batch)
            except Exception as exc:  # noqa: BLE001
                ledger.append(f"REVIEW   {slug[:36]:36s} ERROR {str(exc)[:80]}")
                counts["review-error"] += 1
                continue
            for j, (i, item) in enumerate(batch):
                v = verdicts.get(j, {})
                verdict = str(v.get("verdict") or "reject")
                vreason = str(v.get("reason") or "")
                if verdict == "pass":
                    payload["items"][i] = to_record(item, "pass", "pass", "")
                    counts[f"{origin}-recovered"] += 1
                    ledger.append(
                        f"REVIEW   {slug[:36]:36s} PASS :: {item['question_en'][:52]}"
                    )
                elif verdict == "withdraw":
                    payload["items"][i] = to_record(
                        item, "withdrawn", "withdrawn", vreason or "unsupported"
                    )
                    counts[f"{origin}-withdrawn"] += 1
                    ledger.append(
                        f"REVIEW   {slug[:36]:36s} withdrawn :: {vreason[:80]}"
                    )
                else:
                    payload["items"][i] = to_record(
                        item, "reject", "reject", vreason or "review reject"
                    )
                    counts[f"{origin}-rejected"] += 1
                    ledger.append(f"REVIEW   {slug[:36]:36s} reject :: {vreason[:80]}")
            print(f"  reviewed {slug[:36]} batch={len(batch)}", flush=True)

    # ---- pass 4: S7 citation language on every pass record ------------------
    for payload in corpus:
        skip = tuple(
            t
            for t in (
                payload.get("model") or "",
                payload.get("sku") or "",
                payload.get("title") or "",
            )
            if t
        )
        for rec in payload["items"]:
            if rec["status"] != "pass":
                continue
            name = rec["citation"]["url"].rsplit("/", 1)[-1]
            if name in EN_TWINS:
                ledger.append(s7_switch(payload, rec, skip))

    # ---- write --------------------------------------------------------------
    touched = 0
    for payload in corpus:
        path = DOCS / f"{payload['slug']}.json"
        if args.write:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            (DOCS / f"{payload['slug']}.md").write_text(
                gen.markdown(payload, payload["items"])
            )
        touched += 1
    print("\n".join(ledger))
    print(f"\nledger: {dict(counts)}")
    print(f"products in corpus: {touched}; --write={'on' if args.write else 'off'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
