"""Document questions with the search forced: issue #257's acceptance set, EN and DE.

    uv run --locked python eval/knowledge/documents.py --wp http://127.0.0.1:9060 \
        --index ~/de-linker-data/index/builds/20261016T072222Z/index.sqlite \
        --out ../../docs/acceptance/2026-10-17/257/eval

Each question is one Genie turn the way the service runs it (app.assistant_turn): the
understanding layer prepares it (product words from the instance's Store API, the
route and its calls, understand.py), the real chat model writes it (deepseek-flash,
official API), with the real query encoder (gemini-embedding-2 through OpenRouter)
and the given WordPress instance for the other tools. Only Jev's answer is pinned:
every question reads as a document question (intent `documents_specs`, confidence 1),
so the route calls `linker/search-knowledge` - narrowed to the products the question
names - before the model runs. The set measures how well Genie searches, reads and
cites documents; whether Jev takes a question for a document question is measured by
#233's evaluation, not here.

A row passes its automatic checks when the turn is grounded, not a fallback and not a
handoff, the answer links at least one retrieved chunk as a document, and the
answer's text matches every `expect.all` pattern and no `expect.none` pattern. The
verdict that counts is the reading against the hosted documents
(docs/research/2026-10-17-knocket/TRIAL.md §1), recorded beside these results; the
checks are the floor that reading starts from.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from linker_genie import knowledge
from linker_genie.abilities import AbilityClient
from linker_genie.agent import make_generate, model_name
from linker_genie.cycle import TurnResult, run
from linker_genie.jev import Reading
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import (
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnMessage,
    TurnRequest,
)
from linker_genie.storeapi import StoreVocabulary
from linker_genie.understand import Understander

QUESTIONS = Path(__file__).with_name("questions.json")


class DocumentQuestion:
    """Jev pinned: every message is a document question it is sure of."""

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        del message, page, history
        return Reading("documents_specs", 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def check(row: dict[str, Any], text: str, result: TurnResult) -> list[str]:
    """Why the row fails its automatic checks; empty when it passes."""
    failures: list[str] = []
    if result.fallback or not result.grounded:
        failures.append("fallback or ungrounded: " + "; ".join(result.failures))
    if any(isinstance(block, HandoffBlock) for block in result.output.blocks):
        failures.append("answered with a handoff")
    if not any(
        isinstance(block, DocumentBlock) and block.ref in result.facts.chunk_ids
        for block in result.output.blocks
    ):
        failures.append("no retrieved chunk cited")
    for pattern in row["expect"].get("all", []):
        if not re.search(pattern, text):
            failures.append(f"missing /{pattern}/")
    for pattern in row["expect"].get("none", []):
        if re.search(pattern, text):
            failures.append(f"must not match /{pattern}/")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--wp", required=True, help="WordPress base URL")
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", type=int, nargs="*", help="trial numbers")
    args = parser.parse_args()
    rows = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.only:
        rows = [row for row in rows if row["trial"] in args.only]
    index = DocumentIndex(args.index.expanduser())
    client = AbilityClient(args.wp)
    search: knowledge.Search = knowledge.KnowledgeSearch(lambda: index)
    understander = Understander(
        StoreVocabulary(args.wp).get, DocumentQuestion(), search=search
    )
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for number, row in enumerate(rows, start=1):
        request = TurnRequest(
            conversation_id=f"eval-257-{number}",
            messages=[TurnMessage(role="user", content=row["question"])],
            locale=row["lang"],
        )
        started = time.perf_counter()
        prepared = understander.prepare(request, client)
        generate = make_generate(client, prepared=prepared, search=search)
        result = run(request, generate, prepared.route, prepared.facts)
        seconds = round(time.perf_counter() - started, 1)
        text = "\n".join(
            block.text for block in result.output.blocks if isinstance(block, TextBlock)
        )
        failures = check(row, text, result)
        records.append(
            {
                **row,
                "seconds": seconds,
                "pass": not failures,
                "failures": failures,
                "answer": text,
                "blocks": result.output.model_dump()["blocks"],
                "grounded": result.grounded,
                "fallback": result.fallback,
                "attempts": result.attempts,
                "ground_failures": list(result.failures),
                "route": prepared.log,
                # The calls without their results: the chunks are in the index.
                "tool_calls": [
                    {key: value for key, value in call.items() if key != "result"}
                    for call in result.facts.tool_calls
                ],
                "model": model_name(),
            }
        )
        print(
            f"{row['trial']:>2} {row['lang']} {'PASS' if not failures else 'FAIL'} "
            f"{seconds}s {failures}",
            flush=True,
        )
    passed = sum(record["pass"] for record in records)
    summary = {
        "index": str(args.index),
        "index_version": index.version,
        "ranking": index.ranking,
        "encoder": index.encoder.model if index.encoder else None,
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
