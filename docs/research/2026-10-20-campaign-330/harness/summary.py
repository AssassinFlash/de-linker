"""Summarise a battery run: class x {cases, pass, defect} plus durations.

Usage: python3 summary.py [cases.jsonl]

Uses the hand grade when a case carries one (`grade`: pass | defect | obs);
otherwise the triage verdict stands in.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

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


def main() -> int:
    path = Path(
        sys.argv[1] if len(sys.argv) > 1
        else "~/de-linker-data/campaign-330/evidence/cases.jsonl"
    ).expanduser()
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_class[row["class"]].append(row)
    total = {"pass": 0, "defect": 0, "obs": 0}
    print("| class | EN | DE | pass | defect | obs |")
    print("|---|---|---|---|---|---|")
    for name, items in by_class.items():
        grades = []
        for item in items:
            grade = item.get("grade")
            if grade is None:
                verdict = item.get("verdict", "")
                grade = ("pass" if verdict == "TRIAGE_PASS"
                         else "defect" if verdict == "TRIAGE_ERROR" else "review")
            grades.append(grade)
            if grade in total:
                total[grade] += 1
        en = sum(1 for i in items if i["lang"] == "en")
        de = sum(1 for i in items if i["lang"] == "de")
        label = CLASS_NAMES.get(name, name)
        print(
            f"| {label} | {en} | {de} | {grades.count('pass')} "
            f"| {grades.count('defect')} | {grades.count('obs')} |"
        )
    durations = sorted(float(r.get("duration_s") or 0) for r in rows)
    if durations:
        p95 = durations[max(0, int(len(durations) * 0.95) - 1)]
        print(f"\n{len(rows)} turns; duration p50 "
              f"{statistics.median(durations):.1f}s, p95 {p95:.1f}s, "
              f"max {durations[-1]:.1f}s")
    print(f"graded: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
