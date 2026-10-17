"""Questions about the page the customer is on: issue #234's acceptance set, EN and DE.

    uv run --locked python eval/page/pages.py --wp http://127.0.0.1:9102 \
        --index ~/de-linker-data/index/builds/20261016T072222Z/index.sqlite \
        --mint "just wp g234 eval 'echo (new Linker\\Tools\\Genie\\UserContext())->mint();' \
            --user=857558227@qq.com" \
        --out ../../docs/acceptance/2026-10-18/234/eval

Each question is one Genie turn the way the service runs it (app.assistant_turn), with
nothing pinned: the page context the dock sends (type, address, title, IDs; the address
on the given instance), Jev on OpenRouter deciding whether the message is about the
page, the route reading the page from the instance (page.py) or the account's
inquiries, deepseek-flash (official API) writing the answer, the query encoder
(gemini-embedding-2 through OpenRouter) for the documents. A signed-in row gets a
fresh customer token from `--mint` (the shell's UserContext, valid 120 seconds).

A row passes when the turn is grounded, not a fallback and not a handoff; the route
made the call `expect.reads` names (Jev took the message as being about the page); the
answer cites the page when `expect.cites_page`; the products `expect.shows` names
are cited or shown as cards; and its text matches every
`expect.all` pattern and no `expect.none` pattern. The answers are read as well and
the reading is recorded beside the results.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from linker_genie import jev, knowledge
from linker_genie.abilities import AbilityClient
from linker_genie.agent import make_generate, model_name
from linker_genie.cycle import TurnResult, run
from linker_genie.page import PageReader
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    TextBlock,
    TurnRequest,
)
from linker_genie.storeapi import StoreVocabulary
from linker_genie.understand import Prepared, Understander

QUESTIONS = Path(__file__).with_name("questions.json")


def check(row: dict[str, Any], prepared: Prepared, result: TurnResult) -> list[str]:
    """Why the row fails; empty when it passes."""
    failures: list[str] = []
    expect = row["expect"]
    if result.fallback or not result.grounded:
        failures.append("fallback or ungrounded: " + "; ".join(result.failures))
    if any(isinstance(block, HandoffBlock) for block in result.output.blocks):
        failures.append("answered with a handoff")
    reads = expect.get("reads")
    if reads and not any(call.ability == reads for call in prepared.route.calls):
        failures.append(f"the route did not call {reads}")
    refs = {
        ref
        for block in result.output.blocks
        if isinstance(block, TextBlock)
        for ref in block.refs
    }
    if expect.get("cites_page") and "page" not in refs:
        failures.append("the answer does not cite the page")
    # A draft's products count as named when the text cites them or a card shows
    # them: the model writes no model code with digits in it (no numbers in text).
    shown = refs | {
        str(pid)
        for block in result.output.blocks
        if isinstance(block, CardsBlock)
        for pid in block.product_ids
    }
    for product_id in expect.get("shows", []):
        if str(product_id) not in shown:
            failures.append(f"product {product_id} is neither cited nor shown")
    text = answer_text(result)
    for pattern in expect.get("all", []):
        if not re.search(pattern, text):
            failures.append(f"missing /{pattern}/")
    for pattern in expect.get("none", []):
        if re.search(pattern, text):
            failures.append(f"must not match /{pattern}/")
    return failures


def answer_text(result: TurnResult) -> str:
    return "\n".join(
        block.text for block in result.output.blocks if isinstance(block, TextBlock)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--wp", required=True, help="WordPress base URL")
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--mint", required=True, help="command printing a token")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", nargs="*", help="row ids")
    args = parser.parse_args()
    rows = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.only:
        rows = [row for row in rows if row["id"] in args.only]
    reader = jev.from_env()
    if reader is None:
        raise SystemExit("no OpenRouter key for Jev")
    index = DocumentIndex(args.index.expanduser())
    client = AbilityClient(args.wp)
    search: knowledge.Search = knowledge.KnowledgeSearch(lambda: index)
    pages = PageReader(args.wp)
    understander = Understander(
        StoreVocabulary(args.wp).get, reader, search=search, pages=pages.read
    )
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for number, row in enumerate(rows, start=1):
        logged_in = bool(row.get("logged_in"))
        token = (
            subprocess.run(
                args.mint, shell=True, check=True, capture_output=True, text=True
            )
            .stdout.strip()
            .splitlines()[-1]
            if logged_in
            else None
        )
        page = {**row["page"], "url": args.wp.rstrip("/") + row["page"]["url"]}
        request = TurnRequest.model_validate(
            {
                "conversation_id": f"eval-234-{number}",
                "messages": [{"role": "user", "content": row["question"]}],
                "locale": row["lang"],
                "page_context": page,
                "user": {"logged_in": logged_in, "context": token},
            }
        )
        started = time.perf_counter()
        prepared = understander.prepare(request, client)
        generate = make_generate(
            client, prepared=prepared, search=search, pages=pages.read
        )
        result = run(request, generate, prepared.route, prepared.facts)
        seconds = round(time.perf_counter() - started, 1)
        failures = check(row, prepared, result)
        records.append(
            {
                **row,
                "seconds": seconds,
                "pass": not failures,
                "failures": failures,
                "answer": answer_text(result),
                "blocks": result.output.model_dump()["blocks"],
                "grounded": result.grounded,
                "fallback": result.fallback,
                "attempts": result.attempts,
                "ground_failures": list(result.failures),
                "understanding": prepared.log,
                # The calls without their results: the pages and chunks are re-read.
                "tool_calls": [
                    {key: value for key, value in call.items() if key != "result"}
                    for call in result.facts.tool_calls
                ],
                "model": model_name(),
            }
        )
        jev_log = prepared.log.get("jev") or {}
        print(
            f"{row['id']:<18} {row['lang']} {'PASS' if not failures else 'FAIL'} "
            f"{seconds}s route={prepared.route.name} "
            f"about_page={jev_log.get('about_this_page')} {failures}",
            flush=True,
        )
    passed = sum(record["pass"] for record in records)
    summary = {
        "wp": args.wp,
        "index_version": index.version,
        "chat_model": model_name(),
        "passed": passed,
        "total": len(records),
        "rows": records,
    }
    stamp = time.strftime("%Y%m%dT%H%M%S")
    path = args.out / f"run-{stamp}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{passed}/{len(records)} pass; {path}")
    if os.environ.get("EVAL_STRICT") and passed != len(records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
