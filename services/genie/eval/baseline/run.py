"""Run the 100-question baseline against a Genie target (#336, campaign #329).

    cd services/genie && uv run --locked python eval/baseline/run.py \
        --wp http://127.0.0.1:9168 --out ../../docs/acceptance/2026-10-19/336/smoke \
        --limit 10

Each row is one real customer turn through the site's own path, the REST route
the Genie bubble uses (plugins/linker-tools Proxy: POST linker-ai/v1/genie/turn
→ the service → the WordPress abilities), nothing pinned: the page context the
dock sends, Jev on OpenRouter, deepseek-flash on the official API, the
documents from the index the service holds. The rows and the grading live
beside this script (baseline100.jsonl, grade.py); a run writes one JSON line
per row (question, seconds, meta, blocks, verdict) and prints the score per
category and language.

`--judge` adds the jev → deepseek-flash cascade (eval/judges, the same one the
quality worker runs) to the rows whose assertion is `judge`; without it they
are recorded as needing one, and `human-review` rows always are. The full
baseline (100 rows against live and local, with latency percentiles) is the
ticket's second half and follows the latency instrumentation PR.

Model routing is never touched: Jev stays on OpenRouter's /v1/systemone,
deepseek-flash on api.deepseek.com (AGENTS.md §5).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# This driver runs as a file (python eval/baseline/run.py) and as a module
# (-m baseline.run with eval/ on the path, the way the tests import it); the
# sibling package sits under eval/, which is on sys.path only in the second
# case. One line makes both work; mypy resolves baseline.grade without it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baseline.grade import (  # noqa: E402
    Turn,
    answer_text,
    check,
    parse_stream,
)

SET = Path(__file__).with_name("baseline100.jsonl")
ROUTE = "/wp-json/linker-ai/v1/genie/turn"
# The shell gives up on a turn after 60 s (SHELL_TIMEOUT); the trial's slowest
# answer was 27.5 s. Four minutes bounds a wedged turn without losing a slow
# honest one (the original trial script used 180).
TIMEOUT_SECONDS = 240
# WooCommerce Store API's page size ceiling, as the vocabulary reader uses it.
PAGE_SIZE = 100


def load_rows(
    limit: int | None = None,
    only: list[str] | None = None,
    lang: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """The set in file order (the smoke slice first), cut by the filters."""

    rows = [
        json.loads(line)
        for line in SET.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if only:
        wanted = set(only)
        rows = [row for row in rows if row["id"] in wanted]
    if lang:
        rows = [row for row in rows if row["lang"] == lang]
    if category:
        rows = [row for row in rows if row["category"] == category]
    return rows[:limit] if limit else rows


def catalog_of(wp: str) -> dict[str, str]:
    """Model and SKU tokens of the target's own catalogue (the reader the
    understanding layer uses, Store API): the numbers inside a model code are
    traceable because the model is that product's name."""

    tokens: dict[str, str] = {}
    page = 1
    while True:
        url = (
            f"{wp.rstrip('/')}/wp-json/wc/store/v1/products"
            f"?per_page={PAGE_SIZE}&page={page}"
        )
        with urllib.request.urlopen(url, timeout=30) as response:
            items = json.loads(response.read().decode())
        for item in items:
            for token in [item.get("sku"), item.get("name"), *model_terms(item)]:
                if token:
                    tokens[str(token)] = str(item.get("name", ""))
        if len(items) < PAGE_SIZE:
            return tokens
        page += 1


def model_terms(item: dict[str, Any]) -> list[str]:
    """The product's model attribute terms (pa_model), as the lexicon reads."""

    terms: list[str] = []
    for attribute in item.get("attributes") or []:
        if isinstance(attribute, dict) and attribute.get("taxonomy") == "pa_model":
            terms.extend(
                str(term.get("name", ""))
                for term in attribute.get("terms") or []
                if isinstance(term, dict)
            )
    return terms


def ask(wp: str, row: dict[str, Any]) -> tuple[Turn, str | None]:
    """One turn through the site's own REST route; the error string is set when
    the route itself failed (no turn happened)."""

    page = dict(row.get("page") or {"type": "other"})
    if page.get("url"):
        page["url"] = wp.rstrip("/") + page["url"]
    body = {
        "messages": [{"role": "user", "content": row["question"]}],
        "locale": row["lang"],
        "page": page,
    }
    request = urllib.request.Request(
        wp.rstrip("/") + ROUTE,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return Turn(), f"HTTP {error.code}: {error.read().decode()[:200]}"
    except (urllib.error.URLError, TimeoutError) as error:
        return Turn(), f"request failed: {error}"
    stream = payload.get("stream")
    if not isinstance(stream, str):
        return Turn(), f"no stream in the answer: {payload}"
    return parse_stream(stream), None


def judge_row(
    row: dict[str, Any], turn: Turn
) -> tuple[str, list[str], dict[str, Any] | None]:
    """The jev → deepseek-flash cascade on a judge row (#33's rubric).

    Returns the verdict (pass/fail/needs-judge), the failures and the labels
    the cascade settled on, for the record.
    """

    try:
        from linker_judges.cascade import run_cascade
        from linker_judges.registry import JUDGES
        from linker_judges.rubric import QA_QUESTIONS
        from linker_judges.turns import TURN_THRESHOLDS
    except ImportError as error:  # pragma: no cover - the dependency is locked
        return "needs-judge", [f"judges unavailable: {error}"], None
    item = {
        "question": row["question"],
        "answer": answer_text(turn.blocks),
        "reference": row.get("reference", ""),
        "cards": sorted(
            {
                int(pid)
                for block in turn.blocks
                if block.get("type") == "cards"
                for pid in block.get("product_ids") or []
            }
        ),
    }
    cascade = run_cascade(
        item, JUDGES["jev"], JUDGES["deepseek"], QA_QUESTIONS[:2], TURN_THRESHOLDS
    )
    labels = cascade.labels
    if cascade.error:
        return "needs-judge", [f"judge error: {cascade.error}"], labels
    failures = []
    if labels.get("grounded") != "2":
        failures.append(f"judge grounded: {labels.get('grounded')}")
    if labels.get("appropriate") != "yes":
        failures.append(f"judge appropriate: {labels.get('appropriate')}")
    return ("pass" if not failures else "fail"), failures, labels


def percentile(values: list[float], fraction: float) -> float | None:
    """The fraction-quantile (0.95 = p95), nearest-rank as numpy's default."""

    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(fraction * len(ordered)))
    return ordered[rank - 1]


def phase_medians(timings: list[dict[str, Any]]) -> dict[str, float]:
    """The median of every numeric service phase across the run's turns.

    The service puts its per-turn phase breakdown in the SSE meta's `timing`
    object (the latency instrumentation PR); the runner only records and
    summarizes it. The service-side total is handler entry → stream end; the
    customer-visible wait always adds the WP proxy that buffers the whole body
    (its 60 s ceiling) plus the shell's presentation time, so the gate number
    is the client-side duration this runner measures.
    """

    collected: dict[str, list[float]] = {}
    for timing in timings:
        for phase, value in timing.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                collected.setdefault(str(phase), []).append(float(value))
    return {
        phase: sorted(values)[len(values) // 2]
        for phase, values in collected.items()
        if values
    }


def report(records: list[dict[str, Any]]) -> str:
    """The score per category and language, and the assertion split."""

    lines = []
    auto = [r for r in records if r["verdict"] in {"pass", "fail"}]
    passed = sum(1 for r in auto if r["verdict"] == "pass")
    lines.append(f"auto-graded {passed}/{len(auto)}")
    categories = sorted({r["category"] for r in records})
    for category in categories:
        for lang in ("en", "de"):
            rows = [
                r for r in records if r["category"] == category and r["lang"] == lang
            ]
            if not rows:
                continue
            ok = sum(1 for r in rows if r["verdict"] == "pass")
            flags = "".join("!" if r["verdict"] == "fail" else " " for r in rows)
            lines.append(f"  {category:<20} {lang}  {ok}/{len(rows)}  {flags}")
    for verdict in ("needs-judge", "needs-review"):
        count = sum(1 for r in records if r["verdict"] == verdict)
        if count:
            lines.append(f"{verdict}: {count} (not in the score)")
    hard = [r for r in records if r.get("hard") and r["verdict"] == "fail"]
    if hard:
        lines.append("HARD GATE FAILING: " + ", ".join(r["id"] for r in hard))
    seconds = [float(r["seconds"]) for r in records if r.get("seconds") is not None]
    if seconds:
        p50 = percentile(seconds, 0.5)
        p95 = percentile(seconds, 0.95) if len(seconds) >= 20 else None
        lines.append(
            "client seconds (gate number, request sent -> last event): "
            f"p50 {p50}"
            + (f" p95 {p95}" if p95 is not None else " (p95 needs >= 20 rows)")
            + f" max {max(seconds)}  [gate p95 <= 30 s, target <= 15 s]"
        )
    timings = [r["timing"] for r in records if isinstance(r.get("timing"), dict)]
    if timings:
        phases = phase_medians(timings)
        lines.append(
            "service phases (median s): "
            + ", ".join(f"{phase} {value:.2f}" for phase, value in phases.items())
        )
    else:
        lines.append("service timing: meta.timing absent (latency instrumentation PR)")
    for record in auto:
        if record["verdict"] == "fail":
            lines.append(f"FAIL {record['id']} {'; '.join(record['failures'])[:180]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--wp", required=True, help="WordPress base URL")
    parser.add_argument("--out", required=True, type=Path, help="results directory")
    parser.add_argument("--limit", type=int, help="only the first N rows (smoke)")
    parser.add_argument("--only", nargs="*", help="row ids")
    parser.add_argument("--lang", choices=("en", "de"))
    parser.add_argument("--category")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="run the judge cascade on judge rows (needs the model keys)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="exit 1 when any graded row fails"
    )
    args = parser.parse_args(argv)

    rows = load_rows(args.limit, args.only, args.lang, args.category)
    if not rows:
        print("no rows selected", file=sys.stderr)
        return 2
    catalog = catalog_of(args.wp)
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    path = args.out / f"baseline-{stamp}.jsonl"

    records: list[dict[str, Any]] = []
    with path.open("w", encoding="utf-8") as out:
        for number, row in enumerate(rows, start=1):
            started = time.perf_counter()
            turn, error = ask(args.wp, row)
            seconds = round(time.perf_counter() - started, 1)
            if error is not None:
                failures = [f"no turn: {error}"]
                verdict = "fail"
                meta: dict[str, Any] = {}
            else:
                failures = check(row, turn, catalog)
                meta = turn.meta
                if row["assertion"] == "deterministic":
                    verdict = "pass" if not failures else "fail"
                elif row["assertion"] == "human-review":
                    if failures:
                        verdict = "fail"
                    else:
                        verdict = "needs-review"
                        failures = []
                elif args.judge:
                    verdict, judge_failures, labels = judge_row(row, turn)
                    failures = failures + judge_failures
                    meta = {**meta, "judged": labels}
                else:
                    verdict = "needs-judge" if not failures else "fail"
            record = {
                "id": row["id"],
                "slot": row["slot"],
                "lang": row["lang"],
                "category": row["category"],
                "assertion": row["assertion"],
                "hard": bool(row.get("hard")),
                "trial": row.get("trial"),
                "question": row["question"],
                "page": row.get("page"),
                "seconds": seconds,
                # The service's own phase breakdown, when the SSE meta carries it
                # (latency instrumentation PR); the runner never invents one.
                "timing": meta.get("timing"),
                "verdict": verdict,
                "failures": failures,
                "meta": meta,
                "answer": answer_text(turn.blocks) if error is None else "",
                "blocks": turn.blocks if error is None else [],
                "wp": args.wp,
            }
            records.append(record)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            mark = {"pass": "PASS", "fail": "FAIL"}.get(verdict, verdict.upper())
            print(
                f"{number:>3}/{len(rows)} {row['id']:<8} {mark:<12} "
                f"{seconds}s {failures and failures[0] or ''}",
                flush=True,
            )

    print()
    print(report(records))
    print(f"rows: {path}")
    graded_fail = [r for r in records if r["verdict"] == "fail"]
    if args.strict and graded_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
