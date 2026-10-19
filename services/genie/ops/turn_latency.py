#!/usr/bin/env python3
"""Summarize the turn log's passive timing records (#336): count/p50/p95/max.

Reads the `timing` JSON the service writes on each row of its turn log
(services/genie/src/linker_genie/log.py; the file the service writes is named by
GENIE_LOG) and prints one line per phase key plus `total`, in seconds. A phase a
turn skipped is absent from that turn, so a key's count is the number of turns
that ran it; rows without a record (turns logged before #336, or a turn whose
stream never ended) are not counted. Standard library only, in the engine's
feed-sync style (services/engine/ops/sync-feed.py): it reads, it never writes.

Percentiles are nearest-rank: the p-th percentile is the ceil(p*n)-th value of
the sorted list — one real measured turn, never an interpolation between two.

    python3 ops/turn_latency.py [turns.sqlite] [--conversation ID]

The gate this feeds is #329's map line: p95 ≤ 30 s, target ≤ 15 s
(docs/specs/13-genie.md; no public competitor SLO exists, the numbers and the
phases are our own design — docs/research/2026-10-19-genie-campaign-gaps/
DOSSIER.md §1.14). On the VPS, pass the path the service's GENIE_LOG names
(/etc/linker-genie.env, ops/linker-genie-judge.service reads the same file).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

DEFAULT_PATH = Path.home() / ".cache" / "linker-genie" / "turns.sqlite"


def _rows(path: Path, conversation: str | None) -> Iterator[dict[str, float]]:
    """The parsed timing record of every turn that has one; a malformed record
    is skipped, never raised (the summary is a person's read, not a gate)."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if conversation is None:
            found = db.execute("SELECT timing FROM turns").fetchall()
        else:
            found = db.execute(
                "SELECT timing FROM turns WHERE conversation_id = ?", (conversation,)
            ).fetchall()
    finally:
        db.close()
    for (raw,) in found:
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if isinstance(record, dict):
            yield record


def _percentile(values: list[float], fraction: float) -> float:
    """The nearest-rank percentile: ceil(fraction*n)-th of the sorted values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="count/p50/p95/max of the turn log's timing records (#336)"
    )
    parser.add_argument(
        "log",
        nargs="?",
        type=Path,
        default=Path(os.environ.get("GENIE_LOG", str(DEFAULT_PATH))),
        help="the service's turns.sqlite (default: $GENIE_LOG or ~/.cache/linker-genie)",
    )
    parser.add_argument("--conversation", help="only the turns of this conversation id")
    args = parser.parse_args(argv)

    phases: dict[str, list[float]] = {}
    turns = 0
    for record in _rows(args.log, args.conversation):
        turns += 1
        for key, seconds in record.items():
            if isinstance(seconds, int | float):
                phases.setdefault(key, []).append(float(seconds))

    if not turns:
        print(f"no timing records in {args.log}")
        return 1

    print(f"{args.log}: {turns} timed turns, seconds, nearest-rank percentiles")
    order = ["total"] + sorted(key for key in phases if key != "total")
    for key in order:
        values = phases[key]
        # 34 holds the longest stable key (model.tool.<ability>,
        # understand.call.<ability>); a per-tool name longer than that only pushes
        # its own line's columns right.
        print(
            f"{key:<34} n={len(values):<5} p50={_percentile(values, 0.50):7.3f} "
            f"p95={_percentile(values, 0.95):7.3f} max={max(values):7.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
