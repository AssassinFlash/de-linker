"""Jev's intent reading on the evaluation set, through the production client.

    uv run python eval/understanding/jev_eval.py out.json

Reads eval/understanding/jev_cases.json and asks Jev (typesafe/jev-1.13 on
OpenRouter /api/v1/systemone, jev.py — the four questions the service asks) about
each case, six at a time as the #260 measurement did. Scores intent, about_this_page
and wants_person (yes from 0.5, the measurement's cut), and the share Jev was
confident about (route.CONFIDENT). Runs on the VPS with its own key
(/root/.config/terravolt-builder/openrouter.env).
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
from pathlib import Path
from typing import Any

from linker_genie.jev import JevError, from_env
from linker_genie.route import CONFIDENT

CASES = json.loads((Path(__file__).resolve().parent / "jev_cases.json").read_text())[
    "cases"
]
# Six in parallel, as docs/research/2026-10-17-jev-intent/eval.py ran them.
WORKERS = 6


def right(row: dict[str, Any]) -> bool:
    """The expected intent, or a second one a two-part message allows ("also")."""
    return row["reading"]["intent"] in (row["intent"], *row.get("also", []))


def main() -> None:
    jev = from_env()
    if jev is None:
        raise SystemExit("OPENROUTER_API_KEY is not configured")

    def ask(case: dict[str, Any]) -> dict[str, Any]:
        try:
            reading = jev.read(case["message"], case["page"])
        except JevError as error:
            return {**case, "error": str(error)}
        return {**case, "reading": reading.as_log()}

    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(ask, CASES))
    Path(sys.argv[1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    read = [r for r in rows if "reading" in r]
    errors = [r for r in rows if "error" in r]
    hits = [r for r in read if right(r)]
    sure = [r for r in read if r["reading"]["confidence"] >= CONFIDENT]
    sure_hits = [r for r in sure if right(r)]
    page = sum(
        (r["reading"]["about_this_page"] >= 0.5) == r["about_this_page"] for r in read
    )
    person = sum(
        (r["reading"]["wants_person"] >= 0.5) == r["wants_person"] for r in read
    )
    print(f"answers {len(read)}/{len(rows)}, errors {len(errors)}")
    print(f"intent {len(hits)}/{len(read)} = {len(hits) / max(1, len(read)):.1%}")
    for source in sorted({r["source"] for r in read}):
        for lang in ("en", "de"):
            sub = [r for r in read if r["source"] == source and r["lang"] == lang]
            ok = sum(right(r) for r in sub)
            print(f"  {source} {lang}: {ok}/{len(sub)}")
    print(
        f"confident (>= {CONFIDENT}) {len(sure)}/{len(read)}, "
        f"right when confident {len(sure_hits)}/{len(sure)}"
    )
    print(f"about_this_page {page}/{len(read)}, wants_person {person}/{len(read)}")
    seconds = sorted(r["reading"]["seconds"] for r in read)
    cost = sum(r["reading"]["cost"] for r in read)
    if seconds:
        print(
            f"latency p50 {seconds[len(seconds) // 2]} s, "
            f"p90 {seconds[int(len(seconds) * 0.9)]} s; cost ${cost:.6f}"
        )
    for r in read:
        if not right(r):
            print(
                "  MISS",
                r["lang"],
                r["message"],
                r["intent"],
                "->",
                r["reading"]["intent"],
                r["reading"]["confidence"],
            )
    for r in errors:
        print("  ERROR", r["message"], r["error"])


if __name__ == "__main__":
    main()
