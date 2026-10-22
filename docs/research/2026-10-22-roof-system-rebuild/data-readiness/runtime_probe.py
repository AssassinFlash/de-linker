"""Reproduce current-code selection against the captured, unmodified runtime feed.

Research only. No HTTP, product writes, weather calls, or application changes.
Use the engine's existing virtual environment; --engine-src can select another
checkout of the recorded code baseline without copying implementation here.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--engine-src", type=Path,
                    default=HERE.parents[3] / "services/engine/src")
args = parser.parse_args()
sys.path.insert(0, str(args.engine_src.resolve()))

from linker_engine import commercial  # noqa: E402
from linker_engine.compatibility import Compatibility  # noqa: E402
from linker_engine.engine import Engine  # noqa: E402
from linker_engine.products import Products  # noqa: E402

feed = json.loads((HERE / "source-feed.json").read_text())
# This particular existing function does not use the weather member.
engine = Engine(Products.from_feed(feed), Compatibility(feed["compatibility"]), None)
result = {}
for name, power, energy in (("battery_power", 75, 60), ("cabinet_parallel", 100, 600)):
    result[name] = {
        "required_power_kw": power,
        "required_energy_kwh": energy,
        "systems": [s.model_dump(mode="json")
                    for s in commercial.systems(engine, power, energy, "en")],
    }
(HERE / "runtime-feed-design-probes.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({"cases": len(result), "network_calls": 0,
                  "output": "runtime-feed-design-probes.json"}))
