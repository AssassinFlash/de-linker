#!/usr/bin/env python3
"""One product: retrieve pages, generate EN/DE answers, independent review.

Does not write WooCommerce. Output: docs/faq/<slug>.json and docs/faq/<slug>.md.
Generation and review are separate HTTP calls (docs/specs/15-faq.md).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCS = ROOT / "docs" / "faq"
INDEX_DEFAULT = Path.home() / "de-linker-data/index/builds/20261010T082155Z/index.sqlite"
DEEPSEEK_JSON = Path.home() / ".config/terravolt-builder/deepseek.json"
AIHUBMIX_ENV = Path.home() / ".config/terravolt-builder/aihubmix.env"

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
# Model codes mix letters and digits (HS2-10K-T2-X, BU2-5.0-HV1/5, 1P32S).
# Their digits are identifiers, not figures to prove in the cited passage.
MODELISH = re.compile(
    r"\b(?=[A-Z0-9./-]*[A-Z])(?=[A-Z0-9./-]*\d)[A-Z0-9][A-Z0-9./-]{1,}\b",
    re.I,
)
AI_EN = (
    re.compile(r"\bnot\s+\w[\w\s-]{0,40}\s+but\b", re.I),
    re.compile(r"\bnot\s+just\b", re.I),
    re.compile(r"\bwhether\s+it'?s\b.{0,40}\bor\b", re.I),
)
AI_DE = (
    re.compile(r"nicht\s+\w[\w\s-]{0,40}\s+sondern\b", re.I),
    re.compile(r"\bkein(?:e[mnrs]?)?\s+\w[\w\s-]{0,40},\s+sondern\b", re.I),
)
DU_FORM = re.compile(
    r"(?:^|[^\w])(du|dich|dir|dein|deine|deinen|deinem|deiner|deines|euch|euer|eure)\b",
    re.I,
)


def load_deepseek() -> tuple[str, str, str]:
    """Key, endpoint, model. Key from DEEPSEEK_API_KEY, else the config file."""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    endpoint = "https://api.deepseek.com/chat/completions"
    model = "deepseek-v4-flash"
    if DEEPSEEK_JSON.is_file():
        cfg = json.loads(DEEPSEEK_JSON.read_text())
        endpoint = str(cfg.get("chat_completions_endpoint") or endpoint)
        model = str(cfg.get("chat_model") or model)
        if not key:
            key = str(cfg.get("api_key") or "").strip()
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set")
    return key, endpoint, model


def load_aihubmix() -> None:
    """Put AIHubMix credentials in the environment for the query encoder."""
    if os.environ.get("AIHUBMIX_API_KEY") and os.environ.get("AIHUBMIX_BASE_URL"):
        return
    if not AIHUBMIX_ENV.is_file():
        return
    for line in AIHUBMIX_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def chat(key: str, endpoint: str, model: str, system: str, user: str) -> dict[str, Any]:
    """One DeepSeek chat-completions call, JSON object. No conversation history."""
    body = {
        "model": model,
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
        "max_tokens": 8192,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            content = payload["choices"][0]["message"]["content"]
            if not content:
                raise RuntimeError("DeepSeek returned empty content")
            return json.loads(content)
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if isinstance(exc, urllib.error.HTTPError):
                last_error = RuntimeError(
                    f"DeepSeek HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:800]}"
                )
    assert last_error is not None
    raise last_error


_INDEX = None


def document_index():
    """One read-only index for the run (sqlite-vec allows check_same_thread=False)."""
    global _INDEX
    if _INDEX is None:
        sys.path.insert(0, str(ROOT / "services/genie/src"))
        sys.path.insert(0, str(ROOT / "services/genie"))
        from linker_genie.retrieval import DocumentIndex  # noqa: PLC0415

        load_aihubmix()
        path = Path(os.environ.get("GENIE_INDEX", str(INDEX_DEFAULT)))
        _INDEX = DocumentIndex(path)
    return _INDEX


def retrieve(product_id: int, questions: list[str]) -> list[list[dict[str, Any]]]:
    """Per question, k document hits from the #10 index (datasheet and manual first)."""
    index = document_index()
    out: list[list[dict[str, Any]]] = []
    for question in questions:
        hits = index.search(
            question,
            lang="en",
            product_ids=[product_id],
            doc_types=["datasheet", "manual"],
            k=8,
        )
        if not hits:
            hits = index.search(question, lang="en", product_ids=[product_id], k=8)
        out.append(
            [
                {
                    "chunk_id": hit.chunk_id,
                    "title": hit.title,
                    "doc_type": hit.doc_type,
                    "url": hit.doc_url,
                    "page": hit.page,
                    "section": hit.section,
                    "text": hit.text[:1800],
                }
                for hit in hits
            ]
        )
    return out


def numbers_supported(answer: str, text: str, skip: tuple[str, ...] = ()) -> bool:
    """Every measured number in the answer appears in the cited passage.

    Digits inside model codes (HS2-10K-T2-X) and the product's own name/SKU
    are identifiers, not figures. Commas and dots in decimals are equivalent.
    """
    cleaned = MODELISH.sub(" ", answer)
    for token in skip:
        if token:
            cleaned = cleaned.replace(token, " ")
    haystack = text.replace(",", ".")
    for raw in NUMBER.findall(cleaned):
        if raw.replace(",", ".") not in haystack and raw not in text:
            return False
    return True


def banned_copy(en: str, de: str) -> str:
    """Empty when the copy has no listed AI tell; otherwise the tell."""
    for pattern in AI_EN:
        if pattern.search(en):
            return f"EN AI pattern {pattern.pattern}"
    for pattern in AI_DE:
        if pattern.search(de):
            return f"DE AI pattern {pattern.pattern}"
    if DU_FORM.search(de):
        return "German du/ihr form"
    return ""


GENERATE_SYSTEM = """You write product FAQ answers for Linker Technology GmbH (B2B solar/storage, Germany).
Output a JSON object only: {"items":[...]}.
Each item: question_en, question_de, answer_en, answer_de, status ("pass"|"withdrawn"),
withdraw_reason (string, empty when pass), citation {url, page, title, chunk_id}.
Rules:
- Keep the existing question angle. You may rephrase the question, not the topic.
- Answer only from the retrieved passages of THIS product. Do not use other models or general knowledge.
- Every pass item must cite one retrieved passage (url and page from that passage). Every number in the answer must appear in that passage.
- If the passages do not support the question, status=withdrawn and say why. Do not invent.
- English and German, same facts. German: Sie form (de_DE_formal). Never du/ihr.
- Forbidden: "not X but Y" / "nicht … sondern …", groups of three parallel clauses, em dashes as drama, "In short:", "It's important to note".
- No company promises (delivery, warranty length, certifications Linker holds) unless the passage states them for this model.
- Answers are for installers reading a product page: specific, short, no marketing fluff.
"""

REVIEW_SYSTEM = """You are a marketing director reviewing FAQ copy for a German B2B trade site (Ahrefs-quality: specific, useful, no fluff).
This is a new conversation. You did not write the answers.
Output JSON only: {"items":[{"index":0,"verdict":"pass"|"reject"|"withdraw","reason":"..."}]}.
Reject when: AI sentence patterns (not X but Y, stacked triples, empty intensifiers); vague or interchangeable with a sibling model; a number not in the cited passage; German du/ihr; a claim the citation does not carry.
Withdraw when the question cannot be answered from the cited document.
Pass only when the answer is grounded, specific to this model, and readable.
"""


def generate_items(
    key: str,
    endpoint: str,
    model: str,
    product: dict[str, Any],
    hits: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """One generation call for this product."""
    questions = product["questions"]
    user = json.dumps(
        {
            "product": {
                "id": product["id"],
                "slug": product["slug"],
                "sku": product.get("sku"),
                "title": product.get("title"),
                "brand": product.get("brand"),
                "model": product.get("model"),
                "series": product.get("series"),
            },
            "questions": questions,
            "passages": hits,
        },
        ensure_ascii=False,
    )
    data = chat(key, endpoint, model, GENERATE_SYSTEM, user)
    items = data.get("items")
    if not isinstance(items, list):
        raise RuntimeError("generate: no items[]")
    return items


def review_items(
    key: str,
    endpoint: str,
    model: str,
    product: dict[str, Any],
    items: list[dict[str, Any]],
    hits: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Independent review call; no generation history."""
    user = json.dumps(
        {
            "product": {
                "id": product["id"],
                "slug": product["slug"],
                "model": product.get("model"),
            },
            "items": items,
            "passages": hits,
        },
        ensure_ascii=False,
    )
    data = chat(key, endpoint, model, REVIEW_SYSTEM, user)
    verdicts = data.get("items")
    if not isinstance(verdicts, list):
        raise RuntimeError("review: no items[]")
    return verdicts


def flatten_passages(hits: list[list[dict[str, Any]]]) -> dict[tuple[str, int], str]:
    """(url, page) -> text, last write wins."""
    out: dict[tuple[str, int], str] = {}
    for group in hits:
        for hit in group:
            out[(hit["url"], int(hit["page"]))] = hit["text"]
    return out


def gate_item(
    item: dict[str, Any],
    passages: dict[tuple[str, int], str],
    skip: tuple[str, ...] = (),
) -> tuple[str, str]:
    """pass / withdrawn / reject from deterministic checks."""
    status = str(item.get("status") or "")
    if status == "withdrawn":
        return "withdrawn", str(item.get("withdraw_reason") or "unsupported")
    citation = item.get("citation") if isinstance(item.get("citation"), dict) else {}
    url = str(citation.get("url") or "")
    try:
        page = int(citation.get("page") or 0)
    except (TypeError, ValueError):
        page = 0
    text = passages.get((url, page), "")
    if not url or page < 1 or not text:
        return "withdrawn", "citation is not a retrieved page"
    en = str(item.get("answer_en") or "")
    de = str(item.get("answer_de") or "")
    if not en or not de:
        return "withdrawn", "missing EN or DE answer"
    if not numbers_supported(en, text, skip) or not numbers_supported(de, text, skip):
        return "withdrawn", "a number is not in the cited passage"
    tell = banned_copy(en, de)
    if tell:
        return "reject", tell
    return "pass", ""


def _page(value: Any) -> int:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return 0
    return page if page >= 1 else 0


def to_record(
    item: dict[str, Any], status: str, review: str, reason: str
) -> dict[str, Any]:
    """The stored shape import.py writes."""
    citation = item.get("citation") if isinstance(item.get("citation"), dict) else {}
    return {
        "question": str(item.get("question_en") or ""),
        "answer": str(item.get("answer_en") or ""),
        "question_de": str(item.get("question_de") or ""),
        "answer_de": str(item.get("answer_de") or ""),
        "citation": {
            "url": str(citation.get("url") or ""),
            "page": _page(citation.get("page")),
            "title": str(citation.get("title") or ""),
        },
        "status": status,
        "review": review,
        "reason": reason,
    }


def markdown(product: dict[str, Any], records: list[dict[str, Any]]) -> str:
    """Per-product review record."""
    lines = [
        f"# {product.get('title') or product['slug']}",
        "",
        f"- id: {product['id']}",
        f"- slug: `{product['slug']}`",
        f"- sku: `{product.get('sku') or ''}`",
        f"- model: {product.get('model') or ''}",
        "",
    ]
    if not records:
        lines.append("No existing FAQ questions. Nothing generated.")
        lines.append("")
        return "\n".join(lines)
    for i, rec in enumerate(records, start=1):
        cite = rec["citation"]
        lines.extend(
            [
                f"## {i}. {rec['question'] or '(withdrawn)'}",
                "",
                f"**Status:** {rec['status']}",
                f"**Review:** {rec['review']}" + (f" — {rec['reason']}" if rec["reason"] else ""),
                "",
                f"**EN Q:** {rec['question']}",
                "",
                rec["answer"] or "_(withdrawn)_",
                "",
                f"**DE Q:** {rec['question_de']}",
                "",
                rec["answer_de"] or "_(zurückgezogen)_",
                "",
                f"**Citation:** {cite.get('title') or cite.get('url')} · p.{cite.get('page')} · {cite.get('url')}",
                "",
            ]
        )
    return "\n".join(lines)


def run_product(product: dict[str, Any], key: str, endpoint: str, model: str) -> dict[str, Any]:
    """Generate + review one product; write json and md."""
    questions = [q["question_en"] for q in product.get("questions") or [] if q.get("question_en")]
    records: list[dict[str, Any]] = []
    if questions:
        hits = retrieve(product["id"], questions)
        generated = generate_items(key, endpoint, model, product, hits)
        passages = flatten_passages(hits)
        skip = tuple(
            t
            for t in (
                str(product.get("model") or ""),
                str(product.get("sku") or ""),
                str(product.get("title") or ""),
            )
            if t
        )
        gated: list[dict[str, Any]] = []
        for item in generated:
            status, reason = gate_item(item, passages, skip)
            item["_gate"] = status
            item["_gate_reason"] = reason
            gated.append(item)
        verdicts = review_items(key, endpoint, model, product, generated, hits)
        by_index = {
            int(v["index"]): v
            for v in verdicts
            if isinstance(v, dict)
            and (
                isinstance(v.get("index"), int)
                or str(v.get("index", "")).isdigit()
            )
        }
        for i, item in enumerate(gated):
            gate_status, gate_reason = item["_gate"], item["_gate_reason"]
            verdict = by_index.get(i, {})
            review_verdict = str(verdict.get("verdict") or "reject")
            review_reason = str(verdict.get("reason") or "")
            if gate_status == "withdrawn" or review_verdict == "withdraw":
                status = "withdrawn"
                reason = gate_reason or review_reason or "unsupported"
                review = "withdrawn"
            elif gate_status == "reject" or review_verdict != "pass":
                status = "reject"
                reason = gate_reason or review_reason or "review reject"
                review = "reject"
            else:
                status = "pass"
                reason = ""
                review = "pass"
            records.append(to_record(item, status, review, reason))
    payload = {
        "id": product["id"],
        "slug": product["slug"],
        "sku": product.get("sku"),
        "title": product.get("title"),
        "model": product.get("model"),
        "items": records,
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f"{product['slug']}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    (DOCS / f"{product['slug']}.md").write_text(markdown(product, records))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DOCS / "questions.json")
    parser.add_argument("--slug", help="Run one product by slug")
    parser.add_argument("--id", type=int, help="Run one product by id")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even when docs/faq/<slug>.json already exists",
    )
    args = parser.parse_args()
    bundle = json.loads(args.questions.read_text())
    products = bundle["products"] if isinstance(bundle, dict) else bundle
    key, endpoint, model = load_deepseek()
    selected = products
    if args.slug:
        selected = [p for p in products if p["slug"] == args.slug]
    elif args.id:
        selected = [p for p in products if p["id"] == args.id]
    if not selected:
        sys.exit("no matching product")
    failed: list[str] = []
    for product in selected:
        existing = DOCS / f"{product['slug']}.json"
        if existing.is_file() and not args.force:
            print(f"{product['id']} {product['slug']} skip (exists)", flush=True)
            continue
        try:
            result = run_product(product, key, endpoint, model)
        except Exception as exc:  # noqa: BLE001 — a failed product must not stop the 106.
            failed.append(product["slug"])
            print(f"{product['id']} {product['slug']} ERROR {exc}", flush=True)
            continue
        n_pass = sum(1 for i in result["items"] if i["status"] == "pass")
        n_w = sum(1 for i in result["items"] if i["status"] == "withdrawn")
        n_r = sum(1 for i in result["items"] if i["status"] == "reject")
        print(
            f"{product['id']} {product['slug']} pass={n_pass} withdrawn={n_w} reject={n_r}",
            flush=True,
        )
    if failed:
        print(f"{len(failed)} failed: {', '.join(failed)}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
