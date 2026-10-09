"""`judges build | run | report | labels | bench` (uv run judges --help)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import build
from .dataset import (
    label_problems,
    load_construction,
    load_items,
    load_labels,
    read_jsonl,
)
from .registry import JUDGES
from .report import render
from .runner import run_judge


def _selected(
    items: dict[str, dict[str, object]], ids: str | None, labels_file: Path | None
) -> list[dict[str, object]]:
    if ids:
        wanted = [i.strip() for i in ids.split(",") if i.strip()]
    elif labels_file is not None:
        wanted = [row["id"] for row in read_jsonl(labels_file)]
    else:
        wanted = list(items)
    return [items[i] for i in wanted]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="judges", description="#33 judge bake-off")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "build",
        help="write pairs.jsonl and construction.jsonl from data/ and the hosted PDFs",
    )
    run = sub.add_parser(
        "run", help="call judges on items, append one JSON line per call"
    )
    run.add_argument(
        "--judges", required=True, help=f"comma-separated: {', '.join(JUDGES)}"
    )
    run.add_argument(
        "--runs", type=int, default=3, help="repetitions per item (default 3)"
    )
    run.add_argument(
        "--out", type=Path, required=True, help="run directory, one <judge>.jsonl each"
    )
    run.add_argument(
        "--ids", help="comma-separated item ids (default: all, or those in --labels)"
    )
    run.add_argument(
        "--labels", type=Path, help="a labels file; its ids select the items"
    )
    report = sub.add_parser("report", help="markdown tables for a run directory")
    report.add_argument("--runs", type=Path, required=True)
    report.add_argument(
        "--labels", type=Path, help="labels file (default: human_label in pairs.jsonl)"
    )
    report.add_argument(
        "--split", choices=("test", "calibration", "all"), default="test"
    )
    labels = sub.add_parser(
        "labels", help="check that every item has a valid human_label"
    )
    labels.add_argument("--labels", type=Path)
    bench = sub.add_parser("bench", help="latency and memory of one local judge server")
    bench.add_argument(
        "--judge",
        required=True,
        choices=sorted(n for n, j in JUDGES.items() if j.local),
    )
    bench.add_argument(
        "--pid", type=int, required=True, help="the llama.cpp server's process id"
    )
    bench.add_argument("--ids", required=True)
    bench.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "build":
        pairs, copy = build()
        print(f"pairs.jsonl: {pairs} answer pairs and {copy} copy items")
        return 0
    items = load_items()
    if args.command == "run":
        chosen = _selected(items, args.ids, args.labels)
        for name in args.judges.split(","):
            judge = JUDGES[name.strip()]
            count = run_judge(
                judge, chosen, args.runs, args.out / f"{judge.name}.jsonl"
            )
            print(f"{judge.name}: {count} calls")
        return 0
    if args.command == "report":
        print(
            render(
                args.runs,
                items,
                load_construction(),
                load_labels(items, args.labels),
                args.split,
            )
        )
        return 0
    if args.command == "labels":
        problems = label_problems(items, load_labels(items, args.labels))
        for problem in problems[:50]:
            print(problem)
        print(f"{len(problems)} problem(s) in {len(items)} items")
        return 1 if problems else 0
    if args.command == "bench":
        from .bench import bench as run_bench

        summary = run_bench(
            args.judge, _selected(items, args.ids, None), args.pid, args.out
        )
        print(json.dumps(summary, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
