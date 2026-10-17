"""Re-judge production turns and the price fixtures with this tree's judges.

Live calls through the worker's own cascade (`linker_genie.quality.worker.
judge_turn`): Jev `typesafe/jev-1.13` via OpenRouter /api/v1/systemone, the
escalation deepseek-flash via api.deepseek.com (AGENTS.md §5). Keys come from
the environment or ~/.config/terravolt-builder, as the worker reads them.

    uv run --project services/genie python docs/research/2026-10-18-judge-remit/rejudge.py \
        <scratch>/turns.json services/genie/tests/fixtures/quality/production-flags.json \
        <out.json>

`turns.json` is `fetch_turns.py`'s output. The summary holds ids, labels,
confidences, flags and the production verdict beside the new one: no question,
answer or reason text.
"""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from typing import Any

from linker_judges.registry import JUDGES
from linker_judges.rubric import REMIT

from linker_genie.quality.turns import LoggedTurn
from linker_genie.quality.worker import judge_turn

KEYS = ("labels", "confidence", "flags", "citations", "escalation")


def logged(row: dict[str, Any]) -> LoggedTurn:
    def load(value: Any, default: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value) if value else default
        return value if value is not None else default

    return LoggedTurn(
        id=row["id"],
        conversation_id=str(row["conversation_id"]),
        created_at=row["created_at"],
        locale=row["locale"],
        fallback=bool(row["fallback"]),
        tool_calls=load(row["tool_calls"], []),
        output=load(row["output"], {}),
        question=row["question"],
        page=load(row["page"], {}),
        approved=bool(row.get("approved", False)),
    )


def price_variants(fixtures: dict[str, Any]) -> dict[str, LoggedTurn]:
    """The priced answer under each combination of the remit's two gates, and a
    guest answer that withholds the price and points to sign-in or an inquiry."""
    priced = logged(fixtures["price_approved"])
    withheld = copy.deepcopy(priced.tool_calls)
    withheld[0]["result"]["qualified"][0]["commerce"] = {
        "price_visible": False,
        "in_stock": True,
        "rfq_only": False,
    }
    pointer = {
        "language": "en",
        "blocks": [
            {
                "type": "text",
                "text": "Prices are shown to approved partner accounts after "
                "sign-in. You can also send an inquiry for the HS2-5K-T2-X and "
                "receive a Proforma.",
                "refs": ["4109"],
            },
            {"type": "cards", "product_ids": [4109]},
        ],
    }
    return {
        "price: visible, approved": priced,
        "price: visible, not approved": replace(priced, approved=False),
        "price: withheld, approved": replace(priced, tool_calls=withheld),
        "price: withheld, guest points to sign-in or inquiry": replace(
            priced, approved=False, tool_calls=withheld, output=pointer
        ),
    }


def main() -> None:
    turns = json.load(open(sys.argv[1], encoding="utf-8"))
    fixtures = json.load(open(sys.argv[2], encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for row in turns:
        _, record = judge_turn(logged(row), JUDGES["jev"], JUDGES["deepseek"])
        old = row["judgment"]
        rows.append(
            {
                "turn": row["id"],
                "production": {key: old.get(key) for key in KEYS},
                "now": {key: record.get(key) for key in KEYS},
            }
        )
        print(row["id"], old.get("flags"), "->", record.get("flags"), flush=True)
    cases = {name: logged(fixtures[name]) for name in ("t27", "t33", "t36")}
    cases.update(price_variants(fixtures))
    for name, turn in cases.items():
        _, record = judge_turn(turn, JUDGES["jev"], JUDGES["deepseek"])
        rows.append({"fixture": name, "now": {key: record.get(key) for key in KEYS}})
        print(name, record.get("flags"), record.get("labels"), flush=True)
    summary = {
        "remit": REMIT,
        "judges": {"first": "typesafe/jev-1.13 (OpenRouter /api/v1/systemone)",
                   "escalation": "deepseek-flash (api.deepseek.com)"},
        "rows": rows,
    }
    with open(sys.argv[3], "w", encoding="utf-8") as out:
        json.dump(summary, out, ensure_ascii=False, indent=1)


main()
