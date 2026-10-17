"""Route-call time of the page questions, sequential against concurrent, cold page cache.

    uv run --locked python eval/page/latency.py

The review of PR #295 (item 6) asked the page read to run beside the route's other
calls; this measures the calls alone (Jev runs before them either way) on the rows of
questions.json whose route reads the page and makes another call. Local instance
http://127.0.0.1:9102, the index of 20261016T072222Z.
"""

import json
import statistics
import time
from dataclasses import replace
from pathlib import Path

from linker_genie import jev, knowledge, understand
from linker_genie.abilities import AbilityClient
from linker_genie.page import PageReader
from linker_genie.retrieval import DocumentIndex
from linker_genie.schema import TurnRequest
from linker_genie.storeapi import StoreVocabulary
from linker_genie.tools import READ_PAGE

WP = "http://127.0.0.1:9102"
rows = [
    r for r in json.load(open("eval/page/questions.json")) if not r.get("logged_in")
]
index = DocumentIndex(
    Path("~/de-linker-data/index/builds/20261016T072222Z/index.sqlite").expanduser()
)
search = knowledge.KnowledgeSearch(lambda: index)
client = AbilityClient(WP)
vocab = StoreVocabulary(WP)
reader = jev.from_env()
out: dict[str, list[tuple[str, str, float]]] = {"sequential": [], "concurrent": []}
for row in rows:
    request = TurnRequest.model_validate(
        {
            "conversation_id": "latency",
            "messages": [{"role": "user", "content": row["question"]}],
            "locale": row["lang"],
            "page_context": {**row["page"], "url": WP + row["page"]["url"]},
        }
    )
    route = (
        understand.Understander(
            vocab.get, reader, search=search, pages=PageReader(WP).read
        )
        .prepare(request, client)
        .route
    )
    if len(route.calls) < 2 or not any(c.ability == READ_PAGE for c in route.calls):
        continue
    # Sequential: one call after the other, each on a cold page cache.
    pages = PageReader(WP)
    started = time.perf_counter()
    for call in route.calls:
        single = understand.Prepared(route=replace(route, calls=(call,)))
        understand._run_calls(single, request, client, search, pages.read)
    out["sequential"].append(
        (row["id"], row["lang"], round(time.perf_counter() - started, 2))
    )
    # Concurrent: the route's calls side by side, as the service runs them.
    pages = PageReader(WP)
    started = time.perf_counter()
    understand._run_calls(
        understand.Prepared(route=route), request, client, search, pages.read
    )
    out["concurrent"].append(
        (row["id"], row["lang"], round(time.perf_counter() - started, 2))
    )
for mode, times in out.items():
    print(mode, times, "mean", round(statistics.mean(t for *_, t in times), 2))
