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
quality worker runs) to the rows whose assertion is `judge`. It does not waive
the row's content assertions: those failures still fail the row. Without
`--judge`, judge rows are `needs-judge` and `human-review` rows are
`needs-review`, both in the same table as the passes. They are not passes, so
the report cannot print 100/100 while any of them is still open.

The client p95 (request sent → last SSE event) is the gate: above 30 s fails
`--strict`. The target is 15 s. `meta.timing.first_event` is reported the same
way. `--qualitative` runs the Top-10 gap rows instead of the 100.

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
QUALITATIVE = Path(__file__).with_name("qualitative.jsonl")
ROUTE = "/wp-json/linker-ai/v1/genie/turn"
# Map #329: customer-visible p95 ≤ 30 s, target ≤ 15 s.
CLIENT_P95_GATE_SECONDS = 30
CLIENT_P95_TARGET_SECONDS = 15
# Below this many measured rows the p95 is not a distribution yet.
P95_MIN_ROWS = 20
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
    *,
    qualitative: bool = False,
) -> list[dict[str, Any]]:
    """The scored set in file order (the smoke slice first), or the qualitative
    Top-10 section. Cut by the filters."""

    source = QUALITATIVE if qualitative else SET
    rows = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
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


def messages_of(row: dict[str, Any]) -> list[dict[str, str]]:
    """The thread this row sends: an optional earlier history, then the question.

    Topic-switch rows carry the previous turn in `history`. The scored set
    does not, and sends the one customer message.
    """

    history = row.get("history") or []
    messages = [
        {"role": str(message["role"]), "content": str(message["content"])}
        for message in history
    ]
    messages.append({"role": "user", "content": str(row["question"])})
    return messages


def ask(wp: str, row: dict[str, Any]) -> tuple[Turn, str | None]:
    """One turn through the site's own REST route; the error string is set when
    the route itself failed (no turn happened)."""

    page = dict(row.get("page") or {"type": "other"})
    if page.get("url"):
        page["url"] = wp.rstrip("/") + page["url"]
    body = {
        "messages": messages_of(row),
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


def grade_verdict(
    assertion: str,
    failures: list[str],
    *,
    judge: bool,
    judged: tuple[str, list[str]] | None = None,
) -> tuple[str, list[str]]:
    """The row's verdict.

    Content failures always fail the row. `--judge` adds the cascade on top of
    them; it does not turn a row that missed its assertions into a pass.
    Judge and human-review rows that clear the assertions stay `needs-judge`
    or `needs-review` until a judge or a person scores them. Those verdicts
    are not passes.
    """

    if failures:
        extra = judged[1] if judged is not None else []
        return "fail", failures + [item for item in extra if item not in failures]
    if assertion == "deterministic":
        return "pass", []
    if assertion == "human-review":
        return "needs-review", []
    if not judge or judged is None:
        return "needs-judge", []
    verdict, judge_failures = judged
    if verdict == "pass" and not judge_failures:
        return "pass", []
    if verdict == "needs-judge":
        return "needs-judge", judge_failures
    return "fail", judge_failures


def _latency_values(values: list[float]) -> str:
    """p50, p95 when there are enough rows, and the map's gate and target."""

    p50 = percentile(values, 0.5)
    p95 = percentile(values, 0.95) if len(values) >= P95_MIN_ROWS else None
    text = f"p50 {p50}"
    if p95 is not None:
        text += f" p95 {p95}"
    else:
        text += f" (p95 needs >= {P95_MIN_ROWS} rows)"
    text += f" max {max(values)}"
    text += (
        f"  [gate p95 <= {CLIENT_P95_GATE_SECONDS:g} s, "
        f"target <= {CLIENT_P95_TARGET_SECONDS:g} s]"
    )
    return text


def first_event_seconds(records: list[dict[str, Any]]) -> list[float]:
    """`meta.timing.first_event` from the rows whose meta carried it."""

    values = []
    for record in records:
        timing = record.get("timing")
        if not isinstance(timing, dict):
            continue
        value = timing.get("first_event")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values


def strict_status(records: list[dict[str, Any]]) -> tuple[int, str | None]:
    """Exit status for `--strict`: a failed row, or a client p95 over 30 s.

    The message names the 15 s target beside the gate. A run with fewer than
    20 measured rows has no p95 yet and is not failed for latency.
    """

    seconds = [
        float(record["seconds"])
        for record in records
        if record.get("seconds") is not None
    ]
    p95 = percentile(seconds, 0.95) if len(seconds) >= P95_MIN_ROWS else None
    message = None
    if p95 is not None and p95 > CLIENT_P95_GATE_SECONDS:
        message = (
            f"client p95 {p95} s exceeds the {CLIENT_P95_GATE_SECONDS:g} s gate "
            f"(target <= {CLIENT_P95_TARGET_SECONDS:g} s)"
        )
    failed = any(record["verdict"] == "fail" for record in records)
    if message is not None or failed:
        return 1, message
    return 0, None


def report(records: list[dict[str, Any]]) -> str:
    """The score per category and language, judge rows included.

    `needs-judge` and `needs-review` sit in the same table. They are counted
    by name, never folded into a pass, so a line of N/N cannot hide them.
    """

    lines = []
    counts = {name: 0 for name in ("pass", "fail", "needs-judge", "needs-review")}
    for record in records:
        if record["verdict"] in counts:
            counts[record["verdict"]] += 1
    lines.append(
        f"rows {len(records)}: {counts['pass']} pass, {counts['fail']} fail, "
        f"{counts['needs-judge']} needs-judge, {counts['needs-review']} needs-review"
    )
    marks = {"pass": ".", "fail": "!", "needs-judge": "J", "needs-review": "R"}
    categories = sorted({r["category"] for r in records})
    for category in categories:
        for lang in ("en", "de"):
            rows = [
                r for r in records if r["category"] == category and r["lang"] == lang
            ]
            if not rows:
                continue
            parts = [
                f"{sum(1 for r in rows if r['verdict'] == verdict)} {verdict}"
                for verdict in ("pass", "fail", "needs-judge", "needs-review")
                if any(r["verdict"] == verdict for r in rows)
            ]
            flags = "".join(marks.get(r["verdict"], "?") for r in rows)
            lines.append(f"  {category:<20} {lang}  {', '.join(parts)}  {flags}")
    hard = [r for r in records if r.get("hard") and r["verdict"] == "fail"]
    if hard:
        lines.append("HARD GATE FAILING: " + ", ".join(r["id"] for r in hard))
    seconds = [float(r["seconds"]) for r in records if r.get("seconds") is not None]
    if seconds:
        lines.append(
            "client seconds (gate number, request sent -> last event): "
            + _latency_values(seconds)
        )
    first = first_event_seconds(records)
    if first:
        lines.append(
            "first_event seconds (handler entry -> first SSE event): "
            + _latency_values(first)
        )
    else:
        lines.append("first_event: meta.timing absent")
    timings = [r["timing"] for r in records if isinstance(r.get("timing"), dict)]
    if timings:
        phases = phase_medians(timings)
        lines.append(
            "service phases (median s): "
            + ", ".join(f"{phase} {value:.2f}" for phase, value in phases.items())
        )
    else:
        lines.append("service timing: meta.timing absent")
    for record in records:
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
        "--qualitative",
        action="store_true",
        help="run the Top-10 qualitative section instead of the 100 scored rows",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when a row fails or the client p95 exceeds 30 s",
    )
    args = parser.parse_args(argv)

    rows = load_rows(
        args.limit, args.only, args.lang, args.category, qualitative=args.qualitative
    )
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
                judged: tuple[str, list[str]] | None = None
                # The cascade only runs once the content assertions hold. A miss
                # there already fails the row, judge rows included.
                if row["assertion"] == "judge" and args.judge and not failures:
                    judge_verdict, judge_failures, labels = judge_row(row, turn)
                    judged = (judge_verdict, judge_failures)
                    meta = {**meta, "judged": labels}
                verdict, failures = grade_verdict(
                    row["assertion"], failures, judge=args.judge, judged=judged
                )
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
                # The service's per-turn timing object from the SSE meta. Absent
                # when that event did not carry one; the runner never invents it.
                "timing": meta.get("timing")
                if isinstance(meta.get("timing"), dict)
                else None,
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
    if not args.strict:
        return 0
    code, message = strict_status(records)
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
