"""Two-stage retrieval on the golden set (ticket #16; #10's ruling follow-up).

Stage 1 ranks chunks densely (the production path, by product when the model
maps to one); the chunks fold into an ordered page list - the candidate pool.
Stage 2 re-ranks the first `--depth` pages into the top 5 - with the DeepSeek
escalation judge as the listwise re-ranker (`--judge deepseek`), or never
(`--judge none`, the pool ceiling only).

Prints, per setting: the pool ceiling (a gold page among the candidates), the
recall@5 and the citation page accuracy after the re-rank, and the measured
token cost of the re-rank calls. `--sample N` runs the first N questions per
language instead of all; the numbers then describe the sample.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from index.eval.goldset import GOLDEN_PATH, Question, load
from index.eval.metrics import Score, score
from linker_genie import retrieval
from linker_genie.embedding import DEEPSEEK_FILE, credentials, gemini_from_env
from linker_genie.retrieval import DocumentHit, DocumentIndex

# The re-rank prompt: the pool as a numbered list, the answer as the five best
# numbers. One call per question; the snippets are the pages' chunk texts,
# trimmed to keep one call near 15k input tokens at depth 50.
PROMPT = (
    "You re-rank document pages for a product question. Pick the 5 pages that "
    'answer the question best. Reply with JSON {{"best": [numbers]}} - exactly '
    "five numbers, best first, no others.\n\nQuestion: {query}\n\nPages:\n{pages}"
)


def product_ids_by_model(index_path: Path) -> dict[str, list[int]]:
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    try:
        found: dict[str, list[int]] = {}
        for product_id, model in db.execute("SELECT product_id, model FROM products"):
            found.setdefault(str(model).casefold(), []).append(int(product_id))
        return found
    finally:
        db.close()


def candidates(
    index: DocumentIndex,
    question: Question,
    products: dict[str, list[int]],
    vectors: dict[str, bytes],
    depth: int,
) -> list[DocumentHit]:
    """The production path's dense ranking, folded to unique pages, to `depth`."""
    ids = products.get(question.model.casefold())
    query_vector = vectors.get(question.question)
    scopes: list[Sequence[int] | None] = [ids] if ids else []
    scopes.append(None)  # the scoped-empty fallback the production path has
    for scope_ids in scopes:
        scope = index.scope(scope_ids, None)
        ranked = index.vector_ranking(question.question, scope, query_vector)
        if not ranked:
            continue
        scored = [(rowid, -position) for position, rowid in enumerate(ranked)][
            : depth * 4
        ]
        hits = index.hits(scored, question.lang)
        pages: list[DocumentHit] = []
        seen: set[tuple[str, int]] = set()
        for hit in hits:
            key = (hit.doc_sha256, hit.page)
            if key in seen:
                continue
            seen.add(key)
            pages.append(hit)
            if len(pages) == depth:
                return pages
        return pages
    return []


def pool_ceiling(pages: Sequence[DocumentHit], question: Question) -> bool:
    gold = {(item.doc_sha256, item.page) for item in question.evidence}
    return any((page.doc_sha256, page.page) in gold for page in pages)


def snippet(hit: DocumentHit, limit: int = 1200) -> str:
    text = re.sub(r"\s+", " ", hit.text).strip()
    return f"[{hit.doc_sha256[:12]} p.{hit.page}] {text[:limit]}"


def deepseek_rerank(
    query: str, pages: Sequence[DocumentHit], base: str, key: str, model: str
) -> tuple[list[int], dict[str, int]]:
    """The five best positions (1-based into `pages`) per the DeepSeek judge."""
    import urllib.request

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT.format(
                        query=query,
                        pages="\n".join(
                            f"{number}. {snippet(hit)}"
                            for number, hit in enumerate(pages, start=1)
                        ),
                    ),
                }
            ],
            "response_format": {"type": "json_object"},
        }
    ).encode()
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    usage = {"in": 0, "out": 0}
    with urllib.request.urlopen(request, timeout=120) as reply:
        payload = json.loads(reply.read())
    usage["in"] = int(payload.get("usage", {}).get("prompt_tokens", 0))
    usage["out"] = int(payload.get("usage", {}).get("completion_tokens", 0))
    content = payload["choices"][0]["message"]["content"]
    picked = json.loads(content).get("best", [])
    valid = [
        int(number)
        for number in picked
        if isinstance(number, int) or (isinstance(number, str) and number.isdigit())
    ]
    return [number for number in valid if 1 <= number <= len(pages)], usage


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Two-stage rerank on the golden set.")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--depth", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--sample", type=int, default=0, help="questions per language")
    parser.add_argument(
        "--judge",
        choices=("none", "deepseek"),
        default="none",
        help="none: the pool ceiling only; deepseek: listwise re-rank, then score",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="texts per embedding request (0: the embedder's default)",
    )
    args = parser.parse_args(argv)

    questions = load(args.golden)
    if args.sample:
        by_lang: dict[str, list[Question]] = {}
        for question in questions:
            by_lang.setdefault(question.lang, []).append(question)
        questions = [
            item for lang in sorted(by_lang) for item in by_lang[lang][: args.sample]
        ]

    encoder = gemini_from_env()
    if encoder is None:
        raise SystemExit(
            "gemini-embedding-2 needs OPENROUTER_API_KEY/OPENROUTER_BASE_URL "
            "(env or ~/.config/terravolt-builder/openrouter.env); AIHubMix serves "
            "only behind LINKER_EMBEDDING_PROVIDER=aihubmix"
        )
    if args.batch:
        from linker_genie import embedding as embedding_mod

        embedding_mod.GEMINI_BATCH = args.batch
    index = DocumentIndex(args.index)
    # The production candidate stage stops at 30 chunks; the pool here measures
    # what a deeper first stage would hand the re-ranker, so the stage-1 limit
    # follows this run's depth (four chunks per page before folding).
    retrieval.CANDIDATES = max(retrieval.CANDIDATES, args.depth * 4)
    products = product_ids_by_model(args.index)

    texts = list(dict.fromkeys(question.question for question in questions))
    print(f"encoding {len(texts)} queries…", file=sys.stderr, flush=True)
    vectors = dict(zip(texts, encoder.embed_queries(texts), strict=True))

    # The escalation endpoint's credentials: the environment, else the owner's
    # file — the same rule, through the same reader, as the query encoder above.
    auth = credentials(
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
        DEEPSEEK_FILE,
    )
    if auth is None:
        if args.judge == "deepseek":
            raise SystemExit(
                "DEEPSEEK_API_KEY is not set and "
                "~/.config/terravolt-builder/deepseek.env has none"
            )
        base, key = "", ""
    else:
        base, key = auth
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")

    pools: dict[str, list[DocumentHit]] = {}
    ceiling_hits = 0
    tokens = {"in": 0, "out": 0}
    scores: list[Score] = []
    started = time.monotonic()
    for number, question in enumerate(questions, start=1):
        pages = candidates(index, question, products, vectors, args.depth)
        pools[question.id] = pages
        if pool_ceiling(pages, question):
            ceiling_hits += 1
        if args.judge == "deepseek" and pages:
            order, usage = deepseek_rerank(question.question, pages, base, key, model)
            tokens["in"] += usage["in"]
            tokens["out"] += usage["out"]
            top = [pages[number - 1] for number in order[: args.top_k]]
            if not top:  # an unparseable reply falls back to the pool's own order
                top = pages[: args.top_k]
            scores.append(score(top, question.evidence))
        else:
            scores.append(Score(rank=None, cited_page_correct=None))
        if number % 100 == 0:
            print(
                f"{number}/{len(questions)} … ceiling {ceiling_hits / number:.1%}",
                file=sys.stderr,
                flush=True,
            )

    total = len(questions)
    summary: dict[str, Any] = {
        "index": str(args.index),
        "depth": args.depth,
        "judge": args.judge,
        "questions": total,
        "pool_ceiling": ceiling_hits / total if total else 0.0,
        "seconds": round(time.monotonic() - started, 1),
    }
    if args.judge == "deepseek":
        found = sum(1 for item in scores if item.rank is not None)
        summary["recall@5"] = found / total if total else 0.0
        summary["mrr"] = (
            sum(1 / item.rank for item in scores if item.rank is not None) / total
            if total
            else 0.0
        )
        cited = [
            item.cited_page_correct
            for item in scores
            if item.cited_page_correct is not None
        ]
        summary["cited"] = len(cited)
        summary["page_accuracy"] = sum(cited) / len(cited) if cited else 0.0
        price = 0.30 / 1_000_000  # deepseek-flash input, peak tier (registry.py)
        summary["rerank_cost_usd"] = round(tokens["in"] * price, 4)
        summary["rerank_tokens"] = tokens
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
