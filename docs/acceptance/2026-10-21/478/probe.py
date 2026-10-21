"""Engine-side facts behind the #478 walk, from the same data the instance's engine reads.

The walk (`walk.mjs`) records what the browser asked and what the engine
answered. This probe opens the data the answer cannot show:

1. C44's manufacturer DC/AC cap: `pv_input_kw / ac_power_kw` per inverter, with
   the datasheet figure and page each number is cited to (engineering feed and
   `plugins/linker-commerce/data/compatibility.json`), plus each inverter's
   application and phase.
2. C53's allowed stacking configurations and the pick at the HTW upper limit.
3. C56's matching release entries for named pairs, including a pair the live
   contract covers with two entries of different strictness (min wins) and a
   pair nobody covers (unknown).
4. C54's meter requirements per inverter (included or beside the box, phase).

The feed is re-read from the site over HTTP. The engine read a copy that
`just serve` fetched earlier (`tools/local/src/linker_local/services.py`), so
`feed_generated_at` here is the probe's read time; the walk's responses are
the engine's own snapshot of the same public feed.

Run from the worktree root:
  PYTHONPATH=services/engine/src uv run --locked --project services/engine \\
    python docs/acceptance/2026-10-21/478/probe.py
The site defaults to `http://127.0.0.1:9255`; override with `LINKER_SITE`.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from linker_engine.compatibility import Compatibility, PairResult
from linker_engine.products import Product
from linker_engine.stacking import configurations, pick

CHECKOUT = Path(__file__).resolve().parents[4]
SITE = os.environ.get("LINKER_SITE", "http://127.0.0.1:9255")
FEED_URL = f"{SITE}/wp-json/linker/v1/engineering-feed"
COMPATIBILITY = CHECKOUT / "plugins/linker-commerce/data/compatibility.json"
OUT = Path(__file__).resolve().parent / "probe.json"

# The two device classes residential.py treats as home batteries
# (residential.BATTERY_CLASSES).
BATTERY_CLASSES = ("home-storage", "battery-systems")


def feed() -> dict:
    with urllib.request.urlopen(FEED_URL, timeout=60) as reply:
        return json.loads(reply.read())


def figure(product: Product, key: str) -> dict | None:
    found = product.figures.get(key)
    if not found:
        return None
    return {
        "value": found.value,
        "unit": found.unit,
        "citation": {"url": found.citation.url, "page": found.citation.page},
    }


def dc_ac_cap(product: Product) -> dict | None:
    if not product.ac_power_kw or product.pv_input_kw is None:
        return None
    return {
        "model": product.model,
        "application": product.application,
        "phase": product.phase,
        "ac_power_kw": product.ac_power_kw,
        "pv_input_kw": product.pv_input_kw,
        "cap": round(product.pv_input_kw / product.ac_power_kw, 2),
        "ac_figure": figure(product, "ac_output_kw_nominal"),
        "pv_figure": figure(product, "max_pv_input_power_w"),
    }


def entries(compatibility: Compatibility, inverter: str, battery: str) -> list[dict]:
    # `_pairs` is the loaded contract list; the class exposes no public
    # iteration and the probe must show which entries matched, not just the
    # merged verdict. A private rename would fail this record loudly.
    return [
        {
            "verdict": pair["verdict"],
            "inverter": pair["inverter"],
            "battery": pair["battery"],
        }
        for pair in compatibility._pairs
        if re.search(pair["inverter"], inverter) and re.search(pair["battery"], battery)
    ]


def pair_facts(compatibility: Compatibility, inverter: str, battery: str) -> dict:
    result = compatibility.pair(inverter, battery)
    return {
        "inverter": inverter,
        "battery": battery,
        "verdict": result.verdict,
        "released": result.released,
        "modules": result.modules,
        "accessories": [
            {
                "model": accessory.model,
                "quantity": accessory.quantity,
                "per": accessory.per,
            }
            for accessory in result.accessories
        ],
        "documents": [document.url for document in result.documents],
        "matching_entries": entries(compatibility, inverter, battery),
    }


def stacking_facts(
    inverter: Product, battery: Product, pair: PairResult, upper: float
) -> dict:
    allowed = configurations(inverter, battery, pair)
    chosen = pick(allowed, upper)
    return {
        "inverter": inverter.model,
        "battery": battery.model,
        "upper_kwh": upper,
        "allowed": [
            {
                "quantity": config.quantity,
                "stacks": config.stacks,
                "usable_kwh": config.usable_kwh,
            }
            for config in allowed
        ],
        "pick": None
        if chosen is None
        else {
            "quantity": chosen[0].quantity,
            "stacks": chosen[0].stacks,
            "usable_kwh": chosen[0].usable_kwh,
            "above_upper_limit": chosen[1],
        },
    }


def main() -> int:
    data = feed()
    products = [Product.from_feed(raw) for raw in data["products"]]
    by_model = {product.model: product for product in products}
    compatibility = Compatibility.load(COMPATIBILITY)

    inverters = [p for p in products if p.device_class == "inverters"]
    batteries = [p for p in products if p.device_class in BATTERY_CLASSES]

    caps = [dc_ac_cap(product) for product in inverters]
    caps = [cap for cap in caps if cap]

    backup_capable = [
        product.model for product in inverters if product.backup_power_kva
    ]
    # `_requirements` is the loaded contract list; the public accessor needs an
    # inverter model and this count is about the whole file.
    backup_requirements = [
        requirement
        for requirement in compatibility._requirements
        if requirement["kind"] == "backup"
    ]

    meters = {}
    for model in ["GW10K-ETA-G20", "H2-10K-T3", "HS2-10K-T2-X", "HS2-5K-T2-X"]:
        requirements = compatibility.requirements(model, "meter")
        meters[model] = [
            {
                "included": requirement.included,
                "phase": requirement.phase,
                "accessories": [a.model for a in requirement.accessories],
            }
            for requirement in requirements
        ]

    # The walked `stack` scenario (annual 12,000 kWh) selected this pair; 15.0
    # is that response's `storage.upper_kwh` (1.5 kWh/MWh × 12 MWh, capped by
    # 1.5 kWh/kWp × 10 kWp).
    chosen_stack_inverter = by_model["GW10K-ETA-G20"]
    chosen_stack_battery = by_model["GW5.1-BAT-D-G20"]
    stack_pair = compatibility.pair(
        chosen_stack_inverter.model, chosen_stack_battery.model
    )
    # The walked `small` scenario (4 kWp / 600 kWh) selected this pair; 0.9 is
    # that response's `storage.upper_kwh` (1.5 kWh/MWh × 0.6 MWh, below the
    # 1.5 kWh/kWp cap of 6 kWh).
    small_inverter = by_model["HS2-5K-T2-X"]
    small_battery = by_model["BU2-5.0-HV1"]
    small_pair = compatibility.pair(small_inverter.model, small_battery.model)

    # The walk's selected models and their batteries: the H2 and HS2 swaps,
    # the base pair, and the battery that carries the two-entry strictness
    # example (EF BD-5.1-S1 is not published; it is absent from the feed).
    named_pairs = [
        ("H2-10K-T3", "B2-5.0-HV1"),
        ("H2-10K-T3", "BU2-5.0-HV1"),
        ("HS2-10K-T2-X", "BU2-5.0-HV1"),
        ("HS2-10K-T2-X", "B2-5.0-HV1"),
        ("HS2-10K-T2-X", "EF BD-5-S2"),
        ("GW10K-ETA-G20", "GW6.0-BAT-D-G20"),
        ("EF HD-P1-10K0-S2", "EF BD-5.1-S1"),
        ("EF HD-P1-10K0-S2", "EF BD-5-S2"),
    ]

    published_batteries = [
        {
            "model": battery.model,
            "device_class": battery.device_class,
            "usable_kwh": battery.usable_kwh,
            "pair_with_h2": compatibility.pair("H2-10K-T3", battery.model).verdict,
            "pair_with_hs2": compatibility.pair("HS2-10K-T2-X", battery.model).verdict,
        }
        for battery in batteries
    ]

    # C56's stricter-of-two branch needs one published pair with two matching
    # entries of different verdicts; enumerate the whole published cross
    # product so the record can say whether any exists.
    conflicts = []
    for inverter in inverters:
        for battery in batteries:
            matched = entries(compatibility, inverter.model, battery.model)
            verdicts = {entry["verdict"] for entry in matched}
            if len(matched) > 1 and len(verdicts) > 1:
                conflicts.append(
                    {
                        "inverter": inverter.model,
                        "battery": battery.model,
                        "verdict": compatibility.pair(
                            inverter.model, battery.model
                        ).verdict,
                        "entries": matched,
                    }
                )

    report = {
        "ticket": 478,
        "instance": "w478",
        "feed_generated_at": data["generated_at"],
        "compatibility_version": data["compatibility_version"],
        "compatibility_file": str(COMPATIBILITY.relative_to(CHECKOUT)),
        "c44_dc_ac_caps": caps,
        "c17_backup_capable_inverters": backup_capable,
        "c17_backup_requirements_in_contract": len(backup_requirements),
        "c53_stack_within": stacking_facts(
            chosen_stack_inverter, chosen_stack_battery, stack_pair, 15.0
        ),
        "c53_smallest_above": stacking_facts(
            small_inverter, small_battery, small_pair, 0.9
        ),
        "c54_meter_requirements": meters,
        "c56_pairs": [
            pair_facts(compatibility, inverter, battery)
            for inverter, battery in named_pairs
        ],
        "c56_published_batteries": published_batteries,
        "c56_published_conflicts": conflicts,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
