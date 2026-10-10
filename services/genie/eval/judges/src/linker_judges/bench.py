"""Latency and memory of an open judge where it would run (the VPS) or on the Mac.

Calls go one at a time, as the background worker would make them. The server's
resident memory is read from /proc on Linux (VmRSS, and VmHWM for the peak) or from
`ps` on macOS; MemAvailable is the host's, read from /proc/meminfo on Linux.
"""

from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .dataset import state
from .judges import call
from .metrics import latency
from .registry import JUDGES
from .rubric import questions_for


def _proc_kib(path: str, field: str) -> int | None:
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith(field + ":"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def rss_mib(pid: int) -> tuple[float | None, float | None]:
    """(current, peak) resident set size of `pid` in MiB; peak is Linux-only."""
    if platform.system() == "Linux":
        now = _proc_kib(f"/proc/{pid}/status", "VmRSS")
        peak = _proc_kib(f"/proc/{pid}/status", "VmHWM")
        return (now / 1024 if now else None, peak / 1024 if peak else None)
    result = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True
    )
    text = result.stdout.strip()
    return (int(text) / 1024 if text else None, None)


def mem_available_mib() -> float | None:
    kib = _proc_kib("/proc/meminfo", "MemAvailable")
    return kib / 1024 if kib else None


def bench(
    judge_name: str, items: list[dict[str, Any]], pid: int, out: Path
) -> dict[str, Any]:
    judge = JUDGES[judge_name]
    records = []
    rss_seen: list[float] = []
    available: list[float] = []
    for item in items:
        verdict = call(judge, state(item), questions_for(item["set"]))
        records.append(
            {"judge": judge.name, "item": item["id"], "run": 1, **asdict(verdict)}
        )
        now, _ = rss_mib(pid)
        if now:
            rss_seen.append(now)
        if (free := mem_available_mib()) is not None:
            available.append(free)
    _, peak = rss_mib(pid)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    timing = latency(records)
    summary = {
        "judge": judge.name,
        "weights": judge.weights,
        "host": platform.node(),
        "machine": platform.machine(),
        "calls": len(records),
        "errors": sum(1 for r in records if r["error"]),
        "p50_s": timing[0] if timing else None,
        "p95_s": timing[1] if timing else None,
        "max_s": max((r["seconds"] for r in records if not r["error"]), default=None),
        "rss_peak_mib": peak if peak is not None else max(rss_seen, default=None),
        "rss_last_mib": rss_seen[-1] if rss_seen else None,
        "mem_available_min_mib": min(available) if available else None,
    }
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=1))
    return summary
