"""Runs judges over items and keeps every call as one JSON line."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .dataset import read_jsonl, state
from .judges import Judge, call
from .rubric import questions_for

# Parallel calls per judge: aihubmix accepted six at a time in the trial; a local
# llama.cpp server is called one request at a time so its latency is not queueing.
API_WORKERS = 6
LOCAL_WORKERS = 1


def run_judge(
    judge: Judge,
    items: Iterable[dict[str, Any]],
    runs: int,
    out: Path,
    progress: bool = True,
) -> int:
    """Calls `judge` on every item `runs` times. Resumes: an (item, run) already answered
    in `out` is skipped, one that failed is called again (the later record wins)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(out) if out.exists() else []
    done = {(row["item"], row["run"]) for row in rows if not row["error"]}
    todo = [
        (item, run)
        for run in range(1, runs + 1)
        for item in items
        if (item["id"], run) not in done
    ]
    lock = threading.Lock()
    finished = 0

    def one(task: tuple[dict[str, Any], int]) -> None:
        nonlocal finished
        item, run = task
        verdict = call(judge, state(item), questions_for(item["set"]))
        record = {
            "judge": judge.name,
            "item": item["id"],
            "run": run,
            **asdict(verdict),
        }
        with lock:
            with out.open("a") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            finished += 1
            if progress and (finished % 20 == 0 or finished == len(todo)):
                print(f"  {judge.name}: {finished}/{len(todo)}", flush=True)

    with ThreadPoolExecutor(LOCAL_WORKERS if judge.local else API_WORKERS) as pool:
        list(pool.map(one, todo))
    return len(todo)
