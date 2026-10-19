#!/usr/bin/env python3
"""Summarize the turn log's passive timing records (#336): count/p50/p95/max.

Reads the `timing` JSON the service writes on each row of its turn log
(services/genie/src/linker_genie/log.py; the file the service writes is named by
GENIE_LOG) and prints one line per phase key plus `total`, in seconds.

    python3 ops/turn_latency.py [turns.sqlite] [--conversation ID] [--locale de]
                                [--since 2026-10-19] [--until 2026-10-20]

Standard library only, in the engine's feed-sync style
(services/engine/ops/sync-feed.py): it reads, it never writes.

Three shapes are counted apart, because only one of them may feed a percentile:

- **completed** — the turn's stream ended and its record carries `total`; the
  percentiles below are computed over these turns alone.
- **incomplete** — a `turns` row whose record has phases but no `total`: the
  stream never ran out (handler error, client gone, proxy timeout, restart). A
  short optimistic total must not enter p95, so the row is reported as a count,
  never as a fast turn.
- **unfinished** — a `turn_starts` note with no turn row after
  `GRACE_SECONDS`: a model hang, a killed process, a restart. The `turns` row is
  written only after the answer exists, so without the start note the worst of
  the tail would silently vanish from the p95. The grace window keeps a turn
  that is merely in flight out of the count (twice the shell's 60 s turn
  timeout, `prices.SHELL_TIMEOUT`). A log written before #336 has no start
  notes and reports unfinished=0.

Percentiles are nearest-rank: the p-th percentile is the ceil(p*n)-th value of
the sorted list — one real measured turn, never an interpolation between two. A
phase a completed turn skipped is absent from that turn, so a key's n is the
number of turns that ran it.

`total` here is the service's pipeline metric. What the customer waits also
includes what the service cannot see: the WordPress proxy buffers the whole SSE
body (its own 60 s timeout, `Proxy::post`) and the shell adds up to 1.2 s of
local progressive display (owner ruling 2026-10-18,
docs/research/2026-10-18-genie-reply-design/REFERENCES.md). The gate's
customer-visible p95 is measured client-side by the #336B baseline harness,
which reads each question's timing from the SSE meta; this summary is for
slicing the service's own records from one log.

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Keep in sync with app._log_path (#336): GENIE_LOG, else this file. This script
# runs without the service's venv (stdlib only), so it cannot import app.
DEFAULT_PATH = Path.home() / ".cache" / "linker-genie" / "turns.sqlite"

# A start note younger than this may be a turn still in flight; older than it,
# no turn can still be running (twice the shell's 60 s turn timeout,
# prices.SHELL_TIMEOUT = 60.0).
GRACE_SECONDS = 120


@dataclass(frozen=True)
class Filters:
    conversation: str | None = None
    locale: str | None = None
    since: str | None = None
    until: str | None = None

    def clauses(self) -> tuple[list[str], list[str]]:
        """The WHERE clauses and their arguments, all on `created_at`/columns the
        turn log and its start notes share."""
        clauses: list[str] = []
        args: list[str] = []
        if self.conversation:
            clauses.append("conversation_id = ?")
            args.append(self.conversation)
        if self.locale:
            clauses.append("locale = ?")
            args.append(self.locale)
        if self.since:
            clauses.append("created_at >= ?")
            args.append(self.since)
        if self.until:
            # Exclusive: `--until 2026-10-20` is "everything before that day".
            clauses.append("created_at < ?")
            args.append(self.until)
        return clauses, args


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _records(path: Path, filters: Filters) -> Iterator[dict[str, Any] | None]:
    """The parsed timing record of every turn that has one; a malformed or
    non-object record yields None (counted as incomplete, never raised — the
    summary is a person's read, not a gate)."""
    clauses, args = filters.clauses()
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    db = _connect(path)
    try:
        found = db.execute(f"SELECT timing FROM turns{where}", args).fetchall()
    finally:
        db.close()
    for (raw,) in found:
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            yield None
            continue
        yield record if isinstance(record, dict) else None


def _unfinished(path: Path, filters: Filters) -> int:
    """Start notes with no turn row old enough that no turn can still be in
    flight; a log from before #336 has no start notes."""
    clauses, args = filters.clauses()
    clauses.append("created_at < datetime('now', ?)")
    args.append(f"-{GRACE_SECONDS} seconds")
    db = _connect(path)
    try:
        row = db.execute(
            f"SELECT COUNT(*) FROM turn_starts WHERE {' AND '.join(clauses)}", args
        ).fetchone()
    except sqlite3.OperationalError:
        return 0
    finally:
        db.close()
    return int(row[0]) if row else 0


def _percentile(values: list[float], fraction: float) -> float:
    """The nearest-rank percentile: ceil(fraction*n)-th of the sorted values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def _is_seconds(value: object) -> bool:
    return isinstance(value, int | float)


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
    parser.add_argument("--locale", help="only the turns of this locale (en, de)")
    parser.add_argument(
        "--since",
        help="only turns created at or after this UTC time (YYYY-MM-DD or "
        "YYYY-MM-DD HH:MM:SS, the log's created_at form)",
    )
    parser.add_argument(
        "--until",
        help="only turns created before this UTC time (exclusive, same form)",
    )
    args = parser.parse_args(argv)
    filters = Filters(
        conversation=args.conversation,
        locale=args.locale,
        since=args.since,
        until=args.until,
    )

    records = list(_records(args.log, filters))
    completed = [
        record
        for record in records
        if record is not None and _is_seconds(record.get("total"))
    ]
    incomplete = len(records) - len(completed)
    unfinished = _unfinished(args.log, filters)

    print(
        f"{args.log}: completed={len(completed)} incomplete={incomplete} "
        f"unfinished={unfinished}"
    )
    if not completed:
        print("no completed turns")
        return 1

    phases: dict[str, list[float]] = {}
    for record in completed:
        for key, seconds in record.items():
            if _is_seconds(seconds):
                phases.setdefault(key, []).append(float(seconds))

    print("seconds, nearest-rank percentiles over completed turns")
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
