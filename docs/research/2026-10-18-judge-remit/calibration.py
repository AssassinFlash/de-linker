"""The `appropriate` threshold check after a remit change, on the #33 calibration split.

1. The ids: every QA pair of the calibration split (`pairs.jsonl`), one per line:

    python3 docs/research/2026-10-18-judge-remit/calibration.py ids > <scratch>/ids.jsonl

2. Jev on them with this tree's rubric, one run (OpenRouter /api/v1/systemone):

    cd services/genie/eval/judges
    uv run --locked judges run --judges jev --runs 1 --labels <scratch>/ids.jsonl --out <scratch>/run

3. The summary against the human labels, beside the formal run's (old remit):

    python3 docs/research/2026-10-18-judge-remit/calibration.py summary <scratch>/run/jev.jsonl > calibration-summary.json

Thresholds come from `linker_judges.turns.TURN_THRESHOLDS` (appropriate 0.5,
the #33 formal calibration). The summary holds pair ids, labels and
confidences; the pairs themselves are constructed from hosted datasheets
(docs/specs/33-judge-bakeoff.md, 数据集), not from customer text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
JUDGES = ROOT / "services" / "genie" / "eval" / "judges"
PAIRS = JUDGES / "pairs.jsonl"
FORMAL = JUDGES / "runs" / "formal-20261010" / "jev.jsonl"
# linker_judges.turns.TURN_THRESHOLDS["appropriate"]: the #33 formal calibration.
THRESHOLD = 0.5


def pairs() -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    return [row for row in rows if row["set"] == "qa" and row["split"] == "calibration"]


def summarize(path: Path, labels: dict[str, str]) -> dict[str, Any]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records = [r for r in records if r["item"] in labels and r["run"] == 1 and not r.get("error")]
    items = []
    for record in sorted(records, key=lambda r: r["item"]):
        answer = record["answers"]["appropriate"]
        items.append(
            {
                "id": record["item"],
                "human": labels[record["item"]],
                "jev": answer["label"],
                "confidence": answer["confidence"],
            }
        )
    agree = [item for item in items if item["jev"] == item["human"]]
    standing = [item for item in items if (item["confidence"] or 0) >= THRESHOLD]
    return {
        "items": len(items),
        "agree": len(agree),
        "standing_at_threshold": len(standing),
        "agree_among_standing": sum(item["jev"] == item["human"] for item in standing),
        "min_confidence": min(item["confidence"] for item in items),
        "out_of_remit_items": sum(item["human"] == "no" for item in items),
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in records), 4),
        "per_item": items,
    }


def main() -> None:
    calibration = pairs()
    if sys.argv[1] == "ids":
        for row in calibration:
            print(json.dumps({"id": row["id"]}))
        return
    labels = {row["id"]: row["human_label"]["appropriate"] for row in calibration}
    summary = {
        "threshold": THRESHOLD,
        "this_remit": summarize(Path(sys.argv[2]), labels),
        "formal_run_old_remit": summarize(FORMAL, labels),
    }
    print(json.dumps(summary, indent=1))


main()
