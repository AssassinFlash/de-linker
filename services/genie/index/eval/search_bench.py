"""Search benchmark on the serving host: the real retrieval path over a built index.

For each golden question (the set encoder_bench uses), one `DocumentIndex.search` -
query encoding, FTS5, vector KNN, chunk fetch - timed end to end, and the encoding
alone. Reports p50/p95, the process RSS after opening the index and its peak, the
host's MemAvailable, and, with --vectors-out / --compare, the query vectors and their
cosine to another host's (the index must be queried with the vectors it was built for).
On the VPS it ran from a throwaway uv environment under /tmp/bench-<date>/ with the
package on PYTHONPATH (docs/research/2026-10-09/embedding-bakeoff.md).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from index.eval.encoder_bench import mem_available, proc_mb
from linker_genie.retrieval import DocumentIndex


def percentile(values: Sequence[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, round(share * len(ordered)) - 1)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark search_documents on this host."
    )
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--vectors-out", type=Path)
    parser.add_argument(
        "--compare", type=Path, help="query vectors (.npy) from another host"
    )
    args = parser.parse_args(argv)
    questions: list[str] = json.loads(args.questions.read_text(encoding="utf-8"))
    before = mem_available()
    started = time.perf_counter()
    index = DocumentIndex(args.index)
    opened = time.perf_counter() - started
    encoder = index.encoder
    if encoder is None:
        raise SystemExit("this host has no query encoder for the index")
    rss_open = proc_mb("/proc/self/status", "VmRSS")
    index.search(questions[0], "en")
    searches, encodes, vectors = [], [], []
    for number, question in enumerate(questions):
        lang = "de" if number % 2 else "en"
        tick = time.perf_counter()
        vectors.append(np.frombuffer(encoder.embed_query(question), dtype="<f4"))
        encodes.append(time.perf_counter() - tick)
        tick = time.perf_counter()
        index.search(question, lang)
        searches.append(time.perf_counter() - tick)
    matrix = np.stack(vectors)
    report: dict[str, Any] = {
        "index": str(args.index),
        "model": index.embedding_model,
        "questions": len(questions),
        "open_seconds": round(opened, 2),
        "encode_p50_ms": round(statistics.median(encodes) * 1000, 1),
        "encode_p95_ms": round(percentile(encodes, 0.95) * 1000, 1),
        "search_p50_ms": round(statistics.median(searches) * 1000, 1),
        "search_p95_ms": round(percentile(searches, 0.95) * 1000, 1),
        "rss_open_mb": rss_open and round(rss_open),
        "rss_peak_mb": (peak := proc_mb("/proc/self/status", "VmHWM")) and round(peak),
        "mem_available_before_mb": before and round(before),
        "mem_available_after_mb": (after := mem_available()) and round(after),
    }
    if args.vectors_out:
        np.save(args.vectors_out, matrix)
    if args.compare:
        other = np.load(args.compare)
        cosines = (matrix * other).sum(axis=1) / (
            np.linalg.norm(matrix, axis=1) * np.linalg.norm(other, axis=1)
        )
        report["cosine_to_other_host_min"] = round(float(cosines.min()), 5)
        report["cosine_to_other_host_mean"] = round(float(cosines.mean()), 5)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
