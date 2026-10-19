"""Run the #330 input-boundary battery against a Genie service, record evidence.

Usage (from this directory):
    GENIE_URL=http://127.0.0.1:9164 GENIE_TOKEN=<token> \
        python3 run_battery.py [evidence_dir] [--ids A1-EN,...] [--workers 3]

One SSE turn per case, exactly as the shell sends it (schema.TurnRequest); the
raw stream, the parsed meta and blocks, product hits, number provenance and the
wall-clock duration go into cases.jsonl. The triage verdict (TRIAGE_*) is only
a first cut -- every answer is graded by hand afterwards against the answer's
own words (map #329 rule: no "it answered reasonably" passes).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cases as cases_mod
import xlsxgen

TURN_TIMEOUT = 180.0
GERMAN_MARKERS = re.compile(
    r"(?<![\w-])(?:der|die|das|und|für|mit|nicht|ist|auf|eine|einen|dem|den|von|"
    r"wird|werden|welche|haben|hat|bitte|Lager|Wechselrichter|Batterie)(?![\w-])",
    re.IGNORECASE,
)
ENGLISH_MARKERS = re.compile(
    r"(?<![\w-])(?:the|and|for|with|that|this|are|you|your|our|from|will|which|"
    r"have|please|stock|inverter|battery)(?![\w-])",
    re.IGNORECASE,
)


def parse_stream(stream: str) -> tuple[dict | None, list[dict]]:
    """SSE text -> (meta, blocks), the same way tests/e2e/lib/genie.ts reads it."""
    meta = None
    blocks: list[dict] = []
    for event in stream.split("\n\n"):
        found = re.search(r"^data: (.+)$", event, re.MULTILINE)
        if not found:
            continue
        try:
            payload = json.loads(found.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload.get("turn_id"), int):
            meta = payload
        elif isinstance(payload.get("type"), str):
            blocks.append(payload)
    return meta, blocks


def answer_text(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "handoff":
            parts.append(block.get("summary", ""))
    return "\n".join(parts)


def shown_ids(blocks: list[dict]) -> list[int]:
    ids: list[int] = []
    for block in blocks:
        if block.get("type") in ("cards", "compare"):
            ids.extend(block.get("product_ids", []))
    return ids


def action_args(blocks: list[dict], name: str) -> dict | None:
    for block in blocks:
        if block.get("type") == "action" and block.get("name") == name:
            return block.get("args") or {}
    return None


def numbers_in(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)?", text)


def triage(case: dict, meta: dict | None, blocks: list[dict], feed: dict,
           duration: float, http_status: int | None, error: str | None) -> dict:
    """Machine first cut; flags feed the hand review, they do not replace it."""
    flags: list[str] = []
    expect = case.get("expect", {})
    if error is not None:
        return {"verdict": "TRIAGE_ERROR", "flags": [error]}
    if http_status != 200:
        return {"verdict": "TRIAGE_DEFECT", "flags": [f"http {http_status}"]}
    assert meta is not None
    text = answer_text(blocks)
    ids = shown_ids(blocks)
    by_id = {p["id"]: p for p in feed["products"]}

    if meta.get("language") != case["lang"]:
        flags.append(f"language {meta.get('language')!r} != {case['lang']!r}")
    if meta.get("fallback"):
        flags.append(f"fallback turn ({meta.get('failures')})")
    if expect.get("min_chars") and len(case["request"]) < expect["min_chars"]:
        flags.append("case shorter than designed")

    for wanted in expect.get("expect_ids", []):
        if wanted not in ids:
            flags.append(f"missing expected product {wanted}")
    if expect.get("any_ids") and not any(i in ids for i in expect["any_ids"]):
        flags.append(f"no expected product among {expect['any_ids']}")
    for banned in expect.get("forbidden_ids", []):
        if banned in ids:
            flags.append(f"forbidden product {banned} shown")

    ask = any(b.get("type") == "ask" for b in blocks)
    other_block = any(
        b.get("type") in ("cards", "compare", "action", "document", "parts",
                          "handoff", "contact")
        for b in blocks
    )
    next_step = "?" in text or ask or other_block
    if not next_step and not text.strip():
        flags.append("empty answer")
    elif not next_step:
        flags.append("no next step (no question, card, action or document)")

    if expect.get("no_products") and ids:
        flags.append(f"products shown for small talk: {ids}")
    if "fake" in expect:
        fake = expect["fake"]
        for block in blocks:
            if block.get("type") == "cards":
                for pid in block.get("product_ids", []):
                    product = by_id.get(pid, {})
                    if fake.split("-")[-1].rstrip("X") in str(
                        product.get("model", "")
                    ) and fake in str(product.get("model", "")):
                        flags.append(f"fake model {fake} shown as {product.get('model')}")

    sizing = action_args(blocks, "open_configurator")
    if "sizing" in expect:
        wanted = expect["sizing"]
        if sizing is None:
            flags.append("sizing case without open_configurator action")
        else:
            for key, value in wanted.items():
                if key == "no_annual":
                    if "annual_load_kwh" in sizing:
                        flags.append(f"storage kWh bled into annual_load_kwh: {sizing}")
                elif sizing.get(key) != value:
                    flags.append(f"prefill {key}={sizing.get(key)!r}, want {value!r}")

    if "parts_rows" in expect:
        parts_blocks = [b for b in blocks if b.get("type") == "parts"]
        if not parts_blocks:
            flags.append("no parts block for a list file")
        else:
            rows = parts_blocks[0].get("rows", [])
            if len(rows) != expect["parts_rows"]:
                flags.append(f"{len(rows)} rows, want {expect['parts_rows']}")
    if expect.get("parts_truncated"):
        parts_blocks = [b for b in blocks if b.get("type") == "parts"]
        if not (parts_blocks and parts_blocks[0].get("truncated")):
            flags.append("no truncation flag on a 250-row list")

    # Number provenance: numbers of the answer that are neither the customer's
    # own, nor model names of shown products, nor their feed figures, nor
    # document pages, nor part quantities -> for the hand review.
    allowed = set(numbers_in(case["request"]))
    for pid in set(ids):
        product = by_id.get(pid, {})
        allowed |= set(numbers_in(str(product.get("model", ""))))
        for figure in (product.get("figures") or {}).values():
            allowed |= set(numbers_in(str(figure.get("value", ""))))
        allowed |= set(numbers_in(str(product.get("ac_power_kw", ""))))
        allowed |= set(numbers_in(str(product.get("pv_input_kw", ""))))
        allowed |= set(numbers_in(str(product.get("usable_kwh", ""))))
        allowed |= set(numbers_in(str(product.get("nominal_kwh", ""))))
        allowed |= set(numbers_in(str(product.get("phase", ""))))
        allowed |= set(numbers_in(str(product.get("series", ""))))
    for block in blocks:
        if block.get("type") == "document":
            allowed |= set(numbers_in(str(block.get("label", ""))))
        if block.get("type") == "parts":
            for row in block.get("rows", []):
                allowed.add(str(row.get("quantity", "")))
                allowed |= set(numbers_in(str(row.get("text", ""))))
    # Whole-number spellings the answer may legitimately restate.
    theirs = {n.rstrip(".,") for n in allowed}
    unexplained = []
    for number in numbers_in(text):
        forms = {number, number.replace(",", ".")}
        if not forms & theirs and number not in theirs:
            unexplained.append(number)
    if unexplained:
        flags.append("numbers to verify: " + ",".join(sorted(set(unexplained))[:12]))

    # A DE answer carrying English sentences (beyond product codes) or vice
    # versa is the mixed-language defect the class hunts.
    if case["lang"] == "de" and text:
        if ENGLISH_MARKERS.search(text) and not GERMAN_MARKERS.search(text):
            flags.append("answer looks English on a DE turn")
    if case["lang"] == "en" and text:
        if GERMAN_MARKERS.search(text) and not ENGLISH_MARKERS.search(text):
            flags.append("answer looks German on an EN turn")

    verdict = "TRIAGE_PASS" if not flags else "TRIAGE_REVIEW"
    return {"verdict": verdict, "flags": flags, "duration_s": round(duration, 1)}


def run_case(case: dict, genie: str, token: str, feed: dict) -> dict:
    body: dict = {
        "conversation_id": f"c330-{case['id']}-{int(time.time())}",
        "messages": [{"role": "user", "content": case["request"]}],
        "locale": case["lang"],
        "page_context": {"type": "other"},
        "user": {"logged_in": False},
    }
    if case.get("file"):
        name, data = xlsxgen.build(case["file"])
        body["attachments"] = [{
            "name": name,
            "type": xlsxgen.XLSX_TYPE,
            "data": base64.b64encode(data).decode("ascii"),
        }]
    request = urllib.request.Request(
        f"{genie}/turn",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-Linker-Service-Token": token,
        },
        method="POST",
    )
    started = time.monotonic()
    status: int | None = None
    error: str | None = None
    stream = ""
    try:
        with urllib.request.urlopen(request, timeout=TURN_TIMEOUT) as reply:
            status = reply.status
            stream = reply.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as failure:
        status = failure.code
        error = f"HTTP {failure.code}: {failure.read()[:300]!r}"
    except Exception as failure:  # noqa: BLE001 - recorded as evidence
        error = f"{type(failure).__name__}: {failure}"
    duration = time.monotonic() - started
    meta, blocks = (parse_stream(stream) if stream else (None, []))
    verdict = triage(case, meta, blocks, feed, duration, status, error)
    return {
        "case": case["id"],
        "class": case["class"],
        "lang": case["lang"],
        "request": case["request"],
        "request_chars": len(case["request"]),
        "http": status,
        "duration_s": round(duration, 1),
        "meta": meta,
        "blocks": blocks,
        "stream": stream if len(stream) < 20000 else stream[:20000] + "…",
        **verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", default=None)
    parser.add_argument("--ids", default=None, help="comma-separated case ids")
    parser.add_argument("--workers", type=int, default=3)
    arguments = parser.parse_args()
    genie = os.environ.get("GENIE_URL", "http://127.0.0.1:9164")
    token = os.environ.get("GENIE_TOKEN", "")
    if not token:
        print("GENIE_TOKEN is required (the instance's service token)", file=sys.stderr)
        return 2
    feed_path = Path(
        os.environ.get("FEED", "~/de-linker-data/campaign-330/feed.json")
    ).expanduser()
    feed = json.loads(feed_path.read_text())

    battery = list(cases_mod.CASES) + list(cases_mod.PARTS_CASES)
    if arguments.ids:
        wanted = {name.strip() for name in arguments.ids.split(",")}
        battery = [case for case in battery if case["id"] in wanted]
    evidence = Path(arguments.evidence or "~/de-linker-data/campaign-330/evidence").expanduser()
    evidence.mkdir(parents=True, exist_ok=True)

    print(f"{len(battery)} cases -> {evidence}", flush=True)
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=arguments.workers) as pool:
        for result in pool.map(
            lambda case: run_case(case, genie, token, feed), battery
        ):
            results.append(result)
            flag_text = "; ".join(result.get("flags", []))[:140]
            print(
                f"{result['case']:<8} {result.get('duration_s', '?'):>6}s "
                f"{result['verdict']:<14} {flag_text}",
                flush=True,
            )
    order = {case["id"]: index for index, case in enumerate(battery)}
    results.sort(key=lambda item: order.get(item["case"], 999))
    out = evidence / "cases.jsonl"
    with out.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    passed = sum(1 for r in results if r["verdict"] == "TRIAGE_PASS")
    print(f"\n{passed}/{len(results)} triage-pass; evidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
