"""Research: compare the captured runtime feed, its Woo source, and test inputs.

This measures data availability, not factual correctness or engineering release.
Run from this directory's repository root with Python 3.12+.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
feed = json.loads((HERE / "source-feed.json").read_text())
meta = json.loads((HERE / "source-meta.json").read_text())
fixture = json.loads((REPO / "services/engine/tests/fixtures/feed.json").read_text())
raw_by_id = {p["id"]: p for p in meta["products"]}
fixture_by_id = {p["id"]: p for p in fixture["products"]}


def provenance_kind(v):
    c = v.get("citation")
    if isinstance(c, dict) and c.get("url"):
        return "url"
    if isinstance(c, dict) and c.get("doc"):
        return "document_name_only"
    if v.get("evidence_refs"):
        return "evidence_refs_only"
    return "missing"


comparison = []
for p in feed["products"]:
    raw = raw_by_id[p["id"]]["figures"]
    projected = p["figures"]
    test = fixture_by_id.get(p["id"], {}).get("figures", {})
    dropped = {k: provenance_kind(v) for k, v in raw.items() if k not in projected}
    qualifiers = [k for k, v in raw.items() if v.get("qualifier")]
    comparison.append({
        "id": p["id"], "model": p["model"], "class": p["device_class"],
        "application": p["application"],
        "source_figures": len(raw), "runtime_figures": len(projected),
        "fixture_figures": len(test), "dropped_keys": dropped,
        "source_qualifier_keys": qualifiers,
        "runtime_qualifiers_retained": [k for k in qualifiers if projected.get(k, {}).get("qualifier")],
        "fixture_keys_not_in_runtime": sorted(set(test) - set(projected)),
    })

classes = {}
for cls in sorted({p["device_class"] for p in feed["products"]}):
    rows = [p for p in feed["products"] if p["device_class"] == cls]
    raw_rows = [raw_by_id[p["id"]] for p in rows]
    keys = sorted({k for p in raw_rows for k in p["figures"]})
    relevant = [k for k in keys if any(w in k for w in (
        "power", "current", "efficien", "usable", "energy", "capacity", "soc",
        "voltage", "mppt", "backup", "parallel", "temperature", "temp_c",
    ))]
    classes[cls] = {
        "products": len(rows),
        "source_figures": sum(len(p["figures"]) for p in raw_rows),
        "runtime_figures": sum(len(p["figures"]) for p in rows),
        "no_runtime_figures": [p["model"] for p in rows if not p["figures"]],
        "key_coverage": {k: {
            "source": sum(k in p["figures"] for p in raw_rows),
            "runtime": sum(k in p["figures"] for p in rows),
        } for k in relevant},
    }

all_raw = [v for p in meta["products"] for v in p["figures"].values()]
all_runtime = [v for p in feed["products"] for v in p["figures"].values()]
dropped_kinds = Counter(v for p in comparison for v in p["dropped_keys"].values())
result = {
    "scope": "captured r549 snapshot only; presence is not fact verification",
    "feed_generated_at": feed["generated_at"],
    "meta_captured_at": meta["captured_at"],
    "inputs": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
               for name in ("source-feed.json", "source-meta.json")},
    "product_count": len(feed["products"]),
    "languages": dict(Counter(p["language"] for p in meta["products"])),
    "source_figures": len(all_raw), "runtime_figures": len(all_runtime),
    "dropped_citation_forms": dict(dropped_kinds),
    "source_qualified_values": sum(bool(v.get("qualifier")) for v in all_raw),
    "runtime_qualified_values": sum(bool(v.get("qualifier")) for v in all_runtime),
    "classes": classes, "product_comparison": comparison,
}
assert result["source_figures"] - result["runtime_figures"] == sum(dropped_kinds.values())
assert len(comparison) == len(raw_by_id) == 106
(HERE / "coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: result[k] for k in (
    "product_count", "source_figures", "runtime_figures", "dropped_citation_forms",
    "source_qualified_values", "runtime_qualified_values",
)}, ensure_ascii=False, indent=2))
for cls in ("inverters", "home-storage", "battery-systems", "all-in-one-systems"):
    c = classes[cls]
    print(json.dumps({"class": cls, "products": c["products"],
                      "source_figures": c["source_figures"], "runtime_figures": c["runtime_figures"],
                      "empty_models": c["no_runtime_figures"],
                      "power_fields": {k:v for k,v in c["key_coverage"].items()
                                       if any(w in k for w in ("power", "current", "efficien", "usable"))}},
                     ensure_ascii=False))
