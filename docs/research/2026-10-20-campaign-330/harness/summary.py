"""Summarise a battery run: class x {cases, pass, defect} plus durations.

Usage: python3 summary.py [cases.jsonl]

Uses the hand grade when a case carries one (`grade`: pass | defect | obs);
otherwise the triage verdict stands in.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

CLASS_NAMES = {
    "misspelling": "错拼/模糊拼写",
    "emoji": "emoji",
    "overlong": "超长输入",
    "mixed": "混合语言",
    "case-variants": "大小写/连字符/空格",
    "brand-conflict": "品牌+型号冲突",
    "fake-model": "不存在的型号",
    "multi-product": "多产品同句",
    "units": "数量/单位",
    "contradiction": "矛盾条件",
    "parts-boundary": "零件清单边界",
}


def grade_of(item: dict[str, Any]) -> str:
    """The hand grade, or the triage stand-in when nobody has graded the row."""
    grade = item.get("grade")
    if grade is None:
        verdict = item.get("verdict", "")
        if verdict == "TRIAGE_PASS":
            return "pass"
        if verdict == "TRIAGE_ERROR":
            return "defect"
        return "review"
    return str(grade)


def nearest_rank(durations: list[float], fraction: float) -> float:
    """Nearest-rank percentile: the ceil(fraction * n)-th sorted value.

    The same rule as services/genie/ops/turn_latency.py (`_percentile`).
    `values[int(n * fraction) - 1]` is one rank low whenever `n * fraction`
    is not an integer (111 turns at 0.95: index 104 instead of 105).
    """
    if not durations:
        return 0.0
    ordered = sorted(durations)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def render(rows: list[dict[str, Any]]) -> str:
    """Class x {EN, DE, pass, defect, parity, obs} plus the duration line."""
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_class[row["class"]].append(row)
    total = {"pass": 0, "defect": 0, "parity": 0, "obs": 0, "review": 0}
    lines = [
        "| class | EN | DE | pass | defect | parity | obs |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, items in by_class.items():
        grades = [grade_of(item) for item in items]
        for grade in grades:
            if grade in total:
                total[grade] += 1
        en = sum(1 for item in items if item["lang"] == "en")
        de = sum(1 for item in items if item["lang"] == "de")
        label = CLASS_NAMES.get(name, name)
        lines.append(
            f"| {label} | {en} | {de} | {grades.count('pass')} "
            f"| {grades.count('defect')} | {grades.count('parity')} "
            f"| {grades.count('obs')} |"
        )
    durations: list[float] = []
    for row in rows:
        value = row.get("duration_s")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        durations.append(float(value))
    durations.sort()
    if durations:
        p95 = nearest_rank(durations, 0.95)
        lines.append(
            f"\n{len(rows)} turns; duration p50 "
            f"{statistics.median(durations):.1f}s, p95 {p95:.1f}s, "
            f"max {durations[-1]:.1f}s"
        )
    lines.append(f"graded: {total}")
    return "\n".join(lines)


def main() -> int:
    path = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "~/de-linker-data/campaign-330/evidence/cases.jsonl"
    ).expanduser()
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
