"""Build the engine's test fixtures: an engineering feed and a compatibility file.

The real inputs (`GET /wp-json/linker/v1/engineering-feed` and
`data/compatibility.json`) arrive with ticket #8. Until then the engine is
developed and tested against fixtures in exactly the shape of
`schemas/feed.schema.json` and `schemas/compatibility.schema.json`, built here
from read-only sources:

- the published WooCommerce products of the live site, read with
  `GET /wp-json/wc/v3/products?status=publish` (attributes, categories and the
  `_tv_b2b_figures` meta), saved as JSON by the caller;
- facts of the old repository at `refs/landed/chain-tip` (read with
  `git show`, never imported): the document host map and evidence manifest
  (cited file name -> the URL we host), the compatibility contract (cells,
  families, documents, delivery contents), the material registry (family ids)
  and the manual decisions (the reference PV module's datasheet values).

What the fixture does the way #7 and #8 specify it:

- top-level facts follow the #7 SelectionFacts table (category slug,
  `pa_application`, `pa_phase` or the normalised figure, power and energy keys
  in #7's priority order, unit conversion by `unit` only);
- the three #7 data rulings are applied: EcoFlow 6480-6488 `home`, P1 single
  and P3 three phase; 1959 CHS2-29.9K-T4-X at 29 999 W (datasheet p. 2);
- a figure enters the feed only with a citation that resolves to a document we
  host (#8: "无引用的值不进 feed"); the dropped figures are counted in the summary;
- #8's engine keys are added where the live meta holds the same fact under an
  older key (`max_input_current_per_mppt_a` -> `mppt_max_current_a`, ...), with
  the same citation.

Run from services/engine:

    uv run python scripts/build_fixtures.py --products <wc-products.json> \
        --old-repo ~/Documents/de-linker-project
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

OLD_REF = "refs/landed/chain-tip"
HOST = "https://de-linker.com/"


def publication_envelope(
    feed: dict[str, Any], compatibility: dict[str, Any]
) -> dict[str, Any]:
    enriched = {
        **feed,
        "figure_projection_version": 2,
        "compatibility_origin": "woocommerce",
        "compatibility": compatibility,
        "compatibility_revision": hashlib.sha256(
            json.dumps(
                compatibility, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest(),
    }
    enriched["source_revision"] = hashlib.sha256(
        json.dumps(
            enriched, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return enriched


# #482: the old contract's H2 delivery text cites section 4.1.2 and PDF p. 12,
# which the hosted manual does not have. Its section 2.2 Unpacking (PDF p. 36
# English / p. 7 German) lists the smart meter, three current transformers and
# the 10 m cable. A regeneration must keep that fact, not the old citation.
DELIVERY_OVERRIDES: dict[str, dict[str, Any]] = {
    "saj-h2-t3": {
        "en": "The H2 T3 ships with a smart meter, three current transformers and a 10 m meter communication cable (H2 manual, section 2.2 Unpacking, PDF p. 36 English / p. 7 German).",
        "de": "Der H2 T3 wird mit einem Smart Meter, drei Stromwandlern und einem 10 m langen Zähler-Kommunikationskabel geliefert (H2-Handbuch, Abschnitt 2.2 Auspacken, PDF-S. 36 englisch / S. 7 deutsch).",
        "page": 36,
    }
}

# #7 table: phase spellings found in `pa_phase` and the figures.
PHASE_THREE = (
    "three-phase",
    "three phase",
    "3l+n+pe",
    "3/n/pe",
    "3+n+pe",
    "3l/n/pe",
    "3p4w",
)
PHASE_ONE = ("single-phase", "single phase", "1/n/pe", "l+n+pe", "1p2w")
AC_POWER_KEYS = (
    "ac_output_kw_nominal",
    "ac_output_w_nominal",
    "rated_ac_power_kw",
    "nominal_ac_power_kw",
    "rated_power_kw",
    "power_kw",
)
USABLE_KEYS = (
    "module_energy_kwh_usable",
    "system_usable_energy_kwh",
    "usable_energy_kwh",
)
NOMINAL_KEYS = (
    "module_energy_kwh_nominal",
    "system_capacity_kwh_nominal",
    "system_nominal_energy_kwh",
    "system_energy_kwh_nominal",
    "rated_energy",
    "energy_kwh",
    "battery_rated_energy",
)
# #8's engine keys that the live meta still holds under an older name.
ENGINE_KEY_ALIASES = {
    "mppt_max_current_a": "max_input_current_per_mppt_a",
    "mppt_max_isc_a": "max_isc_per_mppt_a",
    "phases": "phase",
}
# #7 ruling 1: the nine EcoFlow inverters created on 2026-10-07.
ECOFLOW_FILLED = range(6480, 6489)
# #7 ruling 2: 1959 at 29 999 W, SAJ CHS2 datasheet p. 2.
CHS2_ID = 1959
CHS2_DOC = "saj_chs2_datasheet_eu_en.pdf"


def git_show(repo: Path, path: str) -> Any:
    out = subprocess.run(
        ["git", "-C", str(repo), "show", f"{OLD_REF}:{path}"],
        check=True,
        capture_output=True,
    ).stdout
    return json.loads(out)


def normalise_name(name: str) -> str:
    base = os.path.basename(name).lower()
    base = re.sub(r"^(ev_|rec_)?[0-9a-f]{12,16}__", "", base)
    return re.sub(r"[^a-z0-9.]+", "", base)


class DocumentIndex:
    """Cited file name -> the URL we host, joined through the evidence sha256."""

    def __init__(self, host_map: dict[str, Any], evidence: dict[str, Any]) -> None:
        self._by_name: dict[str, str] = {}
        by_sha: dict[str, str] = {}
        for url, entry in host_map["files"].items():
            by_sha.setdefault(entry["sha256"], url)
            for key in (url, entry.get("file") or ""):
                if key:
                    self._by_name.setdefault(normalise_name(key), url)
        for evidence_id, entry in evidence["evidence"].items():
            url = entry.get("hosted_url") or by_sha.get(entry.get("sha256", ""))
            if not url:
                continue
            for key in [entry["file"], *(entry.get("also_cited_as") or [])]:
                self._by_name.setdefault(normalise_name(key), url)
            self._by_name.setdefault(evidence_id, url)

    def url(self, cited: str) -> str | None:
        if cited.startswith(HOST):
            return cited
        return self._by_name.get(normalise_name(cited)) or self._by_name.get(cited)


def citation_of(figure: dict[str, Any], docs: DocumentIndex) -> dict[str, Any] | None:
    raw = figure.get("citation")
    name: str | None = None
    page: int | None = None
    if isinstance(raw, dict) and raw.get("doc"):
        name, page = str(raw["doc"]), raw.get("page")
    elif figure.get("evidence_refs"):
        ref = str(figure["evidence_refs"][0])
        match = re.match(r"(.+?):p(\d+)$", ref)
        name, page = (match.group(1), int(match.group(2))) if match else (ref, None)
    if not name:
        return None
    url = docs.url(name)
    if not url:
        return None
    citation: dict[str, Any] = {"url": url}
    if isinstance(page, int):
        citation["page"] = page
    return citation


def first_number(text: str) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    return float(match.group(0).replace(",", ".")) if match else None


def is_range(text: str) -> bool:
    return bool(re.search(r"\d\s*[-–~]\s*\d", text))


def to_kw(value: str, unit: str) -> float | None:
    number = first_number(value)
    if number is None:
        return None
    unit = unit.strip().lower()
    if unit in ("w", "wp"):
        return round(number / 1000, 4)
    if unit in ("kw", "kwp"):
        return number
    return None


def to_kwh(value: str, unit: str) -> float | None:
    number = first_number(value)
    if number is None:
        return None
    unit = unit.strip().lower()
    if unit == "wh":
        return round(number / 1000, 4)
    if unit == "kwh":
        return number
    return None


def phase_of(text: str) -> int | None:
    lowered = text.lower()
    if any(token in lowered for token in PHASE_THREE):
        return 3
    if any(token in lowered for token in PHASE_ONE):
        return 1
    return None


def attribute(product: dict[str, Any], slug: str) -> str | None:
    for item in product["attributes"]:
        if item["slug"] == slug and item["options"]:
            return str(item["options"][0])
    return None


def meta_value(product: dict[str, Any], key: str) -> Any:
    for item in product["meta_data"]:
        if item["key"] == key:
            return item["value"]
    return None


def selection_facts(product: dict[str, Any], figures: dict[str, Any]) -> dict[str, Any]:
    pid = int(product["id"])
    model = attribute(product, "pa_model") or ""
    application = (attribute(product, "pa_application") or "").lower() or "unknown"
    if pid in ECOFLOW_FILLED:
        application = "home"
    phase: int | str | None = None
    raw_phase = attribute(product, "pa_phase")
    if raw_phase:
        phase = phase_of(raw_phase)
    if phase is None:
        for key in ("phases", "phase"):
            if key in figures:
                phase = phase_of(str(figures[key].get("value") or ""))
                if phase:
                    break
    if phase is None and pid in ECOFLOW_FILLED:
        phase = 1 if "-P1-" in model else 3 if "-P3-" in model else None
    ac_kw: float | None = None
    for key in AC_POWER_KEYS:
        if key in figures:
            ac_kw = to_kw(
                str(figures[key]["value"]), str(figures[key].get("unit") or "")
            )
            break
    if pid == CHS2_ID:
        ac_kw = 29.999
    pv_kw = None
    if "max_pv_input_power_w" in figures:
        pv = figures["max_pv_input_power_w"]
        pv_kw = to_kw(str(pv["value"]), str(pv.get("unit") or ""))
    usable = nominal = None
    kwh_range: dict[str, float] | None = None
    for keys, slot in ((USABLE_KEYS, "usable"), (NOMINAL_KEYS, "nominal")):
        for key in keys:
            if key not in figures:
                continue
            value = str(figures[key]["value"])
            unit = str(figures[key].get("unit") or "")
            if is_range(value):
                numbers = [
                    float(n)
                    for n in re.findall(r"\d+(?:\.\d+)?", value.replace(",", "."))
                ]
                if kwh_range is None and len(numbers) >= 2 and unit.lower() == "kwh":
                    kwh_range = {"min": min(numbers), "max": max(numbers)}
                continue
            parsed = to_kwh(value, unit)
            if slot == "usable" and usable is None:
                usable = parsed
            if slot == "nominal" and nominal is None:
                nominal = parsed
            break

    def known(value: float | int | str | None) -> float | int | str:
        return "unknown" if value is None else value

    return {
        "device_class": product["categories"][0]["slug"]
        if product["categories"]
        else "unknown",
        "application": application
        if application in ("home", "commercial")
        else "unknown",
        "phase": known(phase),
        "ac_power_kw": known(ac_kw),
        "pv_input_kw": known(pv_kw),
        "usable_kwh": known(usable),
        "nominal_kwh": known(nominal),
        "kwh_range": kwh_range,
    }


def cited_figures(
    figures: dict[str, Any], docs: DocumentIndex, dropped: Counter[str]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, figure in figures.items():
        citation = citation_of(figure, docs)
        if citation is None:
            dropped[key] += 1
            continue
        entry: dict[str, Any] = {
            "value": str(figure.get("value")),
            "unit": figure.get("unit") or None,
            "citation": citation,
        }
        if figure.get("value_de"):
            entry["value_de"] = str(figure["value_de"])
        out[key] = entry
    for target, source in ENGINE_KEY_ALIASES.items():
        if target not in out and source in out:
            out[target] = dict(out[source])
    return out


def documents_of(product: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for key, kind in (
        ("_delinker_datasheet_url", "datasheet"),
        ("_delinker_manual_url", "manual"),
        ("_delinker_warranty_url", "warranty"),
    ):
        url = meta_value(product, key)
        if isinstance(url, str) and url.startswith(HOST):
            name = os.path.basename(url)
            lang = "de" if re.search(r"[-_](DE|de)[-_.]", name) else "en"
            out.append({"url": url, "title": name, "type": kind, "lang": lang})
    return out


def series_index(registry: dict[str, Any]) -> dict[int, str]:
    materials = registry["materials"]
    entries = materials.values() if isinstance(materials, dict) else materials
    out: dict[int, str] = {}
    for material in entries:
        family = (material.get("identity") or {}).get("family_id")
        for pid in (material.get("bindings") or {}).get("woo_product_ids") or []:
            if family:
                out.setdefault(int(pid), str(family))
    return out


def strip_brand(pattern: str) -> str:
    return re.sub(r"^\^(GoodWe|SAJ|EcoFlow|Pylontech) ", "^", pattern)


def family_pattern(patterns: list[str]) -> str:
    stripped = [strip_brand(p) for p in patterns]
    return stripped[0] if len(stripped) == 1 else "|".join(f"(?:{p})" for p in stripped)


def doc_refs(contract: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for doc_id in ids:
        doc = contract["documents"].get(doc_id)
        if doc and str(doc.get("url", "")).startswith(HOST):
            out.append({"url": doc["url"]})
    return out


def text(en: str, de: str) -> dict[str, str]:
    return {"en": en, "de": de}


def build_compatibility(contract: dict[str, Any]) -> dict[str, Any]:
    inverters = {f["id"]: f for f in contract["inverter_families"]}
    batteries = {f["id"]: f for f in contract["battery_families"]}
    pairs: list[dict[str, Any]] = []
    verdicts = {
        "listed": "released",
        "one_way": "not_released",
        "not_listed": "not_released",
    }
    for key, cell in contract["cells"].items():
        inverter_id, battery_id = key.split("|")
        inverter = family_pattern(inverters[inverter_id]["patterns"])
        battery = family_pattern(cell.get("scope") or batteries[battery_id]["patterns"])
        conditions = [text(cell["constraint"], cell["constraint_de"])]
        if cell.get("warranty"):
            conditions.append(text(cell["warranty"], cell["warranty_de"]))
        pair: dict[str, Any] = {
            "inverter": inverter,
            "battery": battery,
            "verdict": verdicts[cell["status"]],
            "conditions": conditions,
            "documents": doc_refs(contract, cell["docs"]),
        }
        if cell.get("stack_range"):
            low, high = cell["stack_range"]
            pair["modules"] = {"min": low, "max": high}
        pairs.append(pair)
        for narrower in cell.get("model_constraints") or []:
            sub = {
                "inverter": strip_brand(narrower.get("inverter_pattern") or "")
                or inverter,
                "battery": strip_brand(narrower.get("battery_pattern") or "")
                or battery,
                "verdict": "not_released"
                if narrower.get("conclusion")
                else pair["verdict"],
                "conditions": [text(narrower["constraint"], narrower["constraint_de"])],
                "documents": pair["documents"],
            }
            if narrower.get("conclusion"):
                sub["conditions"].append(
                    text(narrower["conclusion"], narrower["conclusion_de"])
                )
            pairs.append(sub)
    pairs.extend(documented_extras(contract))
    return {
        "schema_version": 1,
        "version": f"contract-{contract['verified_on']}",
        "pairs": pairs,
        "requirements": requirements(contract) + documented_requirements(contract),
    }


def documented_extras(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Pairs that need a part of our range, as the cited documents state it."""
    s12 = doc_refs(contract, ["S12"])
    return [
        {
            # B2 datasheet: B2-5.0 to B2-25.0 are one to five BU2-5.0 modules with
            # one BC2-HV1 control module; sold apart, the modules need the BC2.
            "inverter": family_pattern(
                next(
                    f for f in contract["inverter_families"] if f["id"] == "saj-h2-t3"
                )["patterns"]
            ),
            "battery": "^BU2-5\\.0-HV[15]$",
            "verdict": "released_with_accessory",
            "conditions": [
                text(
                    "SAJ's B2 datasheet builds a B2 system from one to five BU2-5.0 modules "
                    "and one BC2-HV1 control module; modules ordered singly need the BC2-HV1.",
                    "Das SAJ-Datenblatt der B2 baut ein B2-System aus ein bis fünf "
                    "BU2-5.0-Modulen und einem BC2-HV1-Steuermodul auf; einzeln bestellte "
                    "Module benötigen das BC2-HV1.",
                )
            ],
            "documents": [{"url": d["url"], "page": 2} for d in s12],
            "modules": {"min": 2, "max": 5},
            "accessories": [{"model": "^BC2-HV1$", "quantity": 1, "per": "stack"}],
        },
        {
            # HS2/AS2 manual V0.3, PDF p. 12: the HS2 takes two to five BU2-5.0 modules.
            "inverter": family_pattern(
                next(f for f in contract["inverter_families"] if f["id"] == "saj-hs2")[
                    "patterns"
                ]
            ),
            "battery": "^BU2-5\\.0-HV[15]$",
            "verdict": "released",
            "conditions": [
                text(
                    "The HS2 takes two to five BU2-5.0 battery modules (HS2/AS2 manual V0.3, PDF p. 12).",
                    "Das HS2 nimmt zwei bis fünf BU2-5.0-Batteriemodule auf (HS2/AS2-Handbuch V0.3, PDF-S. 12).",
                )
            ],
            "documents": [
                {"url": d["url"], "page": 12} for d in doc_refs(contract, ["S14"])
            ],
            "modules": {"min": 2, "max": 5},
        },
        {
            # OCEAN 2 installation guides (three-phase V1.5 p. 7): one C1 base per
            # floor-standing tower.
            "inverter": family_pattern(
                [
                    pattern
                    for family in contract["inverter_families"]
                    if family["id"]
                    in ("eco-ocean2-p1std", "eco-ocean2-p1", "eco-ocean2-p3")
                    for pattern in family["patterns"]
                ]
            ),
            "battery": "^EF BD-(5|8)-S2$",
            "verdict": "released_with_accessory",
            "conditions": [
                text(
                    "A floor-standing OCEAN 2 battery tower stands on one OCEAN 2 LFP "
                    "Battery Base (installation guide V1.5, p. 7). A wall-mounted tower "
                    "needs the separate wall-mounted base, which is not in our range.",
                    "Ein bodenstehender OCEAN 2 Batterieturm steht auf einer OCEAN 2 LFP "
                    "Battery Base (Installationsanleitung V1.5, S. 7). Ein wandmontierter "
                    "Turm benötigt den separaten Wandsockel, der nicht in unserem Sortiment ist.",
                )
            ],
            "documents": [
                {
                    "url": HOST
                    + "wp-content/uploads/2026/09/ecoflow-ocean2-p3-s2-installation-guide-v1-5.pdf",
                    "page": 7,
                }
            ],
            "accessories": [
                {"model": "^OCEAN 2 LFP Battery Base$", "quantity": 1, "per": "stack"}
            ],
        },
    ]


def requirements(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Inverter-level parts the cited documents name: meters in or beside the box."""
    out: list[dict[str, Any]] = []
    for family in contract["inverter_families"]:
        pattern = family_pattern(family["patterns"])
        delivery = family.get("delivery_contents")
        if delivery and delivery.get("meter_included"):
            override = DELIVERY_OVERRIDES.get(family["id"])
            documents = doc_refs(contract, delivery["docs"])
            if override:
                condition = text(override["en"], override["de"])
                if documents:
                    documents = [
                        {**documents[0], "page": override["page"]},
                        *documents[1:],
                    ]
            else:
                condition = text(delivery["en"], delivery["de"])
            out.append(
                {
                    "inverter": pattern,
                    "kind": "meter",
                    "included": True,
                    "conditions": [condition],
                    "documents": documents,
                }
            )
            continue
        documented = family.get("meter_documented")
        if documented and documented.get("material_id") == "mat_chint_dtsu666":
            out.append(
                {
                    "inverter": pattern,
                    "kind": "meter",
                    "included": False,
                    "accessories": [
                        {"model": "^DTSU666$", "quantity": 1, "per": "system"}
                    ],
                    "phase": 3,
                    "conditions": [text(documented["en"], documented["de"])],
                    "documents": doc_refs(contract, documented["docs"]),
                }
            )
    return out


def documented_requirements(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Parallel controllers and backup transfer switches of our range, from their datasheets."""

    def family(family_id: str) -> str:
        return family_pattern(
            next(f for f in contract["inverter_families"] if f["id"] == family_id)[
                "patterns"
            ]
        )

    goodwe_et = "|".join(f"(?:{family(i)})" for i in ("gw-et-75-100", "gw-et-75k"))
    goodwe_etr = "|".join(f"(?:{family(i)})" for i in ("gw-etr-80-124", "gw-etr-125k"))
    et_manual = (
        HOST + "wp-content/uploads/2026/09/GW_ET-50-100kW_User-Manual-EN_V1.3.pdf"
    )
    etr_datasheet = (
        HOST + "wp-content/uploads/2026/09/GW_ETR_Datasheet_EMEA-EN_V1.1.pdf"
    )
    emanager_c1 = (
        HOST + "wp-content/uploads/2026/10/SAJ_eManager-C1-Pro_Datasheet_DE.pdf"
    )
    sts125 = (
        HOST + "wp-content/uploads/2026/07/goodwe_sts_125kw_datasheet_emea_en-1.pdf"
    )
    ats1 = HOST + "wp-content/uploads/2026/10/SAJ_ATS1_Datasheet_EN-BEU.pdf"
    sec3000c = [{"model": "^SEC3000C$", "quantity": 1, "per": "system"}]
    return [
        {
            "inverter": goodwe_et,
            "kind": "parallel_controller",
            "included": False,
            "max_units": 15,
            "accessories": sec3000c,
            "conditions": [
                text(
                    "GoodWe's ET 50-100 kW solution manual allows up to 15 grid-connected inverters in "
                    "parallel, 6 when they also run off-grid, coordinated by an SEC3000C.",
                    "Das GoodWe-Lösungshandbuch ET 50-100 kW erlaubt bis zu 15 netzgekoppelte "
                    "Wechselrichter parallel, 6 im Ersatzstrombetrieb, koordiniert von einem SEC3000C.",
                )
            ],
            "documents": [
                {"url": et_manual, "page": 11},
                {"url": et_manual, "page": 16},
            ],
        },
        {
            "inverter": goodwe_etr,
            "kind": "parallel_controller",
            "included": False,
            "max_units": 15,
            "accessories": sec3000c,
            "conditions": [
                text(
                    "GoodWe's ETR datasheet allows up to 15 units in parallel, coordinated by an SEC3000C.",
                    "Das GoodWe-Datenblatt ETR erlaubt bis zu 15 Geräte parallel, koordiniert von einem SEC3000C.",
                )
            ],
            "documents": [{"url": etr_datasheet}],
        },
        {
            "inverter": family("saj-chs2-cm2"),
            "kind": "parallel_controller",
            "included": False,
            "max_units": 10,
            "accessories": [
                {"model": "^eManager-C1 Pro$", "quantity": 1, "per": "system"}
            ],
            "conditions": [
                text(
                    "SAJ names the eManager-C1 Pro for two to ten CHS2 systems in parallel.",
                    "SAJ nennt den eManager-C1 Pro für zwei bis zehn parallel geschaltete "
                    "CHS2-Systeme.",
                )
            ],
            "documents": [{"url": emanager_c1}],
        },
        {
            "inverter": "^GW(80K|99\\.99K|100K)-ET-G10$",
            "kind": "backup",
            "included": False,
            "accessories": [
                {"model": "^GW125K-STS-G10$", "quantity": 1, "per": "unit"}
            ],
            "conditions": [
                text(
                    "The GW125K-STS-G10 static transfer switch serves the backup path of the "
                    "ET 80, 99.99 and 100 kW.",
                    "Der statische Umschalter GW125K-STS-G10 bedient den Backup-Pfad der "
                    "ET 80, 99,99 und 100 kW.",
                )
            ],
            "documents": [{"url": sts125, "page": 1}],
        },
        {
            "inverter": "^(H2-(15|20|25|30)K-T3(-DE)?|HS2-(5|6|8|10)K-T2-X|HS3-(5|6|8|10|12)K-T2-W/G-PX)$",
            "kind": "backup",
            "included": False,
            "accessories": [{"model": "^ATS1-T63-A$", "quantity": 1, "per": "system"}],
            "conditions": [
                text(
                    "The ATS1-T63-A switches whole-home backup loads between the grid and "
                    "the inverter's backup output; its datasheet lists the H2 T3 15 to 30 kW, "
                    "the HS2 and the HS3.",
                    "Der ATS1-T63-A schaltet die Lasten der Hausversorgung zwischen Netz und "
                    "Backup-Ausgang des Wechselrichters um; sein Datenblatt nennt den H2 T3 "
                    "15 bis 30 kW, den HS2 und den HS3.",
                )
            ],
            "documents": [{"url": ats1, "page": 2}],
        },
    ]


def overlay(decisions: dict[str, Any], docs: DocumentIndex) -> list[dict[str, Any]]:
    module = decisions["manual_materials"]["mat_trina_solar_tsm_460neg9r_28"]
    dropped: Counter[str] = Counter()
    figures = cited_figures(module["technical"]["specifications"], docs, dropped)
    return [
        {
            "id": module["material_id"],
            "kind": "pv_module",
            "brand": module["identity"]["manufacturer"],
            "model": module["identity"]["model"],
            "figures": figures,
            "documents": [
                {
                    "url": d["url"],
                    "title": d["title"],
                    "type": "datasheet",
                    "lang": lang,
                }
                for d, lang in zip(
                    module["technical"]["documents"], ("en", "de"), strict=True
                )
            ],
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--old-repo", type=Path, required=True)
    parser.add_argument("--generated-at", default="2026-10-09T00:00:00Z")
    parser.add_argument("--out", type=Path, default=Path("tests/fixtures"))
    args = parser.parse_args()

    repo = args.old_repo.expanduser()
    docs = DocumentIndex(
        git_show(repo, "knowledge/document-host-map.json"),
        git_show(repo, "knowledge/evidence-manifest.json"),
    )
    contract = git_show(repo, "contracts/compatibility-lists.json")
    series = series_index(
        git_show(repo, "plugins/terravolt-b2b-core/data/material-registry.json")
    )
    decisions = git_show(repo, "knowledge/materials/manual-decisions.json")

    dropped: Counter[str] = Counter()
    products = []
    for product in sorted(
        json.loads(args.products.read_text()), key=lambda p: int(p["id"])
    ):
        raw = json.loads(meta_value(product, "_tv_b2b_figures") or "{}")
        figures = cited_figures(raw, docs, dropped)
        if int(product["id"]) == CHS2_ID:
            url = docs.url(CHS2_DOC)
            assert url, CHS2_DOC
            figures["ac_output_kw_nominal"] = {
                "value": "29999",
                "unit": "W",
                "citation": {"url": url, "page": 2},
            }
        facts = selection_facts(product, raw)
        products.append(
            {
                "id": int(product["id"]),
                "sku": product["sku"],
                "model": attribute(product, "pa_model") or product["name"],
                "brand": attribute(product, "pa_brand") or "",
                "series": series.get(int(product["id"])),
                **facts,
                "figures": figures,
                "documents": documents_of(product),
            }
        )
    compatibility = build_compatibility(contract)
    feed = publication_envelope(
        {
            "schema_version": 1,
            "generated_at": args.generated_at,
            "compatibility_version": compatibility["version"],
            "products": products,
            "overlay": overlay(decisions, docs),
        },
        compatibility,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in (("feed.json", feed), ("compatibility.json", compatibility)):
        (args.out / name).write_text(
            json.dumps(data, ensure_ascii=False, indent="\t") + "\n"
        )
    print(
        f"{len(products)} products, {len(compatibility['pairs'])} pairs, "
        f"{len(compatibility['requirements'])} requirements; "
        f"figures dropped for lack of a hosted citation: {sum(dropped.values())}"
    )


if __name__ == "__main__":
    main()
