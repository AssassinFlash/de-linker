"""The inquiry summary against the real model (#244).

    uv run python eval/summary/run.py out.json [repeats]

Runs each conversation of cases.json through summary.summarise() with deepseek-flash on
the official DeepSeek API (summary.deepseek(); the key from the environment or
~/.config/terravolt-builder/deepseek.env) `repeats` times (default 3) and scores each
answer: accepted or refused (and why), quantities exactly as expected, every expected
condition present, no price, the seconds the call took. Writes every answer to
`out.json`, prints one line per run and the totals, and exits 1 when a run carries a
price or a wrong quantity: those reach the customer's form or the team.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from linker_genie import summary

CASES: list[dict[str, Any]] = json.loads(
    (Path(__file__).resolve().parent / "cases.json").read_text(encoding="utf-8")
)


def score(case: dict[str, Any], complete: summary.Complete) -> dict[str, Any]:
    request = summary.SummaryRequest.model_validate(
        {k: case[k] for k in ("locale", "messages", "products")}
    )
    started = time.monotonic()
    try:
        result = summary.summarise(request, complete)
    except summary.SummaryError as error:
        return {
            "case": case["id"],
            "seconds": round(time.monotonic() - started, 2),
            "accepted": False,
            "reason": error.reason,
        }
    seconds = round(time.monotonic() - started, 2)
    expect = case["expect"]
    quantities = {str(q.product_id): q.quantity for q in result.quantities}
    conditions = " | ".join(result.conditions).lower()
    missing = [
        group[0]
        for group in expect["conditions"]
        if not any(option.lower() in conditions for option in group)
    ]
    text = " ".join([result.summary, *result.conditions, result.note])
    return {
        "case": case["id"],
        "seconds": seconds,
        "accepted": True,
        "quantities_ok": quantities == expect["quantities"],
        "quantities": quantities,
        "conditions_missing": missing,
        "price": bool(summary._PRICE.search(text)),
        "dropped": result.dropped,
        "answer": result.model_dump(),
    }


def main() -> int:
    out = Path(sys.argv[1])
    repeats = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    complete = summary.deepseek()
    runs = []
    for _ in range(repeats):
        for case in CASES:
            run = score(case, complete)
            runs.append(run)
            print(json.dumps({k: v for k, v in run.items() if k != "answer"}, ensure_ascii=False))
    out.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    accepted = [r for r in runs if r["accepted"]]
    seconds = sorted(r["seconds"] for r in runs)
    totals = {
        "runs": len(runs),
        "accepted": len(accepted),
        "refused": {r["case"]: r["reason"] for r in runs if not r["accepted"]},
        "quantities_ok": sum(r["quantities_ok"] for r in accepted),
        "conditions_complete": sum(not r["conditions_missing"] for r in accepted),
        "price": sum(r["price"] for r in accepted),
        "seconds_p50": seconds[len(seconds) // 2],
        "seconds_max": seconds[-1],
    }
    print(json.dumps(totals, ensure_ascii=False))
    bad = [r for r in accepted if r["price"] or not r["quantities_ok"]]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
