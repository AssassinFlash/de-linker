"""Exact three-original proof of SAJ's conditional HS3 standard warranty."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from linker_genie.hs3_evidence import (
    DATA_MODELS,
    DATASHEET,
    MANUAL,
    MANUAL_MODEL,
    axis_span_valid,
    has_purpose,
    hs3_anchor_key,
    hs3_anchors,
    variants,
)

POLICY = "be0569b4602ac48b2d4d267dea34318464b8c6eded691a34a750cd90209e2391"
FORMAT = "hs3_series_standard_warranty"
PREFIX = "be0569b4602a-p1-hs3-warranty-terms-"
GEO = "be0569b4602a-p1-119012f5"
SUPPLY = "be0569b4602a-p1-ce19ee86"
ROW = "be0569b4602a-p1-f0fd6349"
SPECS = "be0569b4602a-p2-a8cccabf"
INTERNET = "be0569b4602a-p3-192f0b56"
MINIMUM = "be0569b4602a-p3-d8a80e4b"
EXCLUSIONS = "be0569b4602a-p5-f335d95d"
SOURCES = {
    GEO: (
        1,
        "text",
        "da21bcdfc8c1aae68acb62d5d94bc800edfc006e9440c71afc9c45fcb4a038fd",
    ),
    SUPPLY: (
        1,
        "text",
        "f9a7aff5fc9bc2d57add19087df81f0896654751596fa4b373e1035f30abeec8",
    ),
    ROW: (
        1,
        "table",
        "680b91c7c3e13012daff6b893f032b5472b7fad6a246550a7ff0b0c8daf681cc",
    ),
    SPECS: (
        2,
        "text",
        "d88ce09f7194999ff1dfa947e4d769e9c7adbe79f4a42aad77a886d82c3bb782",
    ),
    INTERNET: (
        3,
        "text",
        "9a7a60f07038e4718ae94a724154e88932804de3dfe08181371a488ed4ee7d3c",
    ),
    MINIMUM: (
        3,
        "table",
        "d08be6c851f9c0d5a88753b2ed130334c1028cb19f4b4bab3c5274f10a41c2c7",
    ),
    EXCLUSIONS: (
        5,
        "text",
        "9b0d08e9f23331833e68944779f25fc8b6eb18a1fe536ebb380e1fcac4e80754",
    ),
}
NOTES = (
    (
        GEO,
        1,
        "This limited warranty applies to SAJ products (listed below) purchased and installed in the European market.",
    ),
    (
        SUPPLY,
        1,
        "This warranty applies only to SAJ inverters and batteries and EV chargers and accessories (including online monitoring equipment, CT/meters, etc.) that are manufactured and supplied directly by SAJ or supplied through its authorized partners (distributors, installers, etc). All external and auxiliary parts and equipment installed by third parties (such as monitoring/communication equipment, batteries, hardware/software controllers, etc.) are not covered by the warranty.",
    ),
    (
        ROW,
        1,
        "Ten years standard warranty, starting from the earlier one of the following two dates: · 1. The date on which the product was first installed; · 2. Six months after the date of production.",
    ),
    (
        SPECS,
        2,
        "The product must comply with the specifications provided by SAJ and the operating conditions in the user manual.",
    ),
    (
        INTERNET,
        3,
        "It is required that all the storage systems have internet connection for SAJ monitoring and remote firmware upgrades. If the storage system is not connected to internet, or has not been registered with SAJ, SAJ may not be able to honor the full ten year warranty, but we will always honor the warranty for at least N (refer to below table) years from the date of product shipment from SAJ.",
    ),
    (MINIMUM, 3, "| HS3 | 5.5 |"),
    (
        EXCLUSIONS,
        5,
        "Product problems caused by the following conditions are not covered by the warranty.",
    ),
)


def anchor_key(cid: str) -> str:
    return "hs3-warranty:" + cid


def anchors(
    rows: Iterable[tuple[str, str, int, str, str]],
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    duplicates: set[str] = set()
    for cid, sha, page, kind, text in rows:
        expected = SOURCES.get(cid)
        if expected is None:
            continue
        if cid in seen:
            duplicates.add(cid)
            continue
        seen.add(cid)
        if (
            sha == POLICY
            and (page, kind, hashlib.sha256(text.encode()).hexdigest()) == expected
        ):
            found[anchor_key(cid)] = {
                "source_sha256": sha,
                "page": page,
                "kind": kind,
                "text": text,
            }
    for cid in duplicates:
        found.pop(anchor_key(cid), None)
    return found


def rendered(model: str) -> tuple[str, list[dict[str, Any]]] | None:
    if variants(model) is None:
        return None
    notes = [
        {"chunk_id": cid, "page": page, "lang": "en", "quote": f"*{i}: {quote}"}
        for i, (cid, page, quote) in enumerate(NOTES, 1)
    ]
    text = (
        f"| Model / Modell | {model} |\n"
        "| Warranty / Garantie | Ten years |\n"
        "| Production / Herstellung | Six months |\n"
        + "\n".join(f"{note['quote']} (p. {note['page']})" for note in notes)
    )
    return text, notes


def evidence_id(model: str, did: str, text: str) -> str:
    digest = hashlib.sha256(f"{model}\0{did}\0{text}".encode()).hexdigest()[:16]
    return PREFIX + digest


def render_terms(
    value: Mapping[str, Any], source_ids: Sequence[str]
) -> tuple[str, list[dict[str, Any]]] | None:
    policy, model = value.get("policy"), value.get("model")
    if (
        not isinstance(policy, dict)
        or policy.get("format") != FORMAT
        or not isinstance(model, str)
    ):
        return None
    sources = policy.get("sources")
    if (
        not isinstance(sources, dict)
        or set(sources) != set(SOURCES)
        or not set(SOURCES).issubset(source_ids)
    ):
        return None
    rows = []
    for cid in SOURCES:
        item = sources.get(cid)
        if not isinstance(item, dict):
            return None
        sha, page, kind, text = (
            item.get("source_sha256"),
            item.get("page"),
            item.get("kind"),
            item.get("text"),
        )
        if (
            not isinstance(sha, str)
            or type(page) is not int
            or not isinstance(kind, str)
            or not isinstance(text, str)
        ):
            return None
        rows.append((cid, sha, page, kind, text))
    checked = anchors(rows)
    if len(checked) != len(SOURCES):
        return None
    for cid, _, quote in NOTES:
        if quote not in checked[anchor_key(cid)]["text"]:
            return None
    return rendered(model)


def valid_scope(
    scope: Mapping[str, Any],
    ids: Sequence[int],
    products: Mapping[int, Mapping[str, Any]],
    documents: Mapping[str, Mapping[str, Any]],
    *,
    sha: str,
    chunk_id: str,
    text: str,
    external_axis_anchors: Mapping[str, Any] | None,
) -> bool:
    value = scope.get("warranty_scope")
    if (
        scope.get("basis") != "warranty_terms"
        or not isinstance(value, dict)
        or not isinstance(external_axis_anchors, Mapping)
    ):
        return False
    pid = value.get("product_id")
    product = products.get(pid) if type(pid) is int else None
    if (
        product is None
        or list(ids) != [pid]
        or scope.get("product_ids") != [pid]
        or sha != POLICY
    ):
        return False
    model = str(product.get("model", ""))
    if (
        variants(model) is None
        or value.get("model") != model
        or value.get("product_revision") != product.get("product_revision")
    ):
        return False
    refs = value.get("source_documents")
    if not isinstance(refs, dict) or set(refs) != {"policy", "datasheet", "manual"}:
        return False
    for role, expected_sha in (
        ("policy", POLICY),
        ("datasheet", DATASHEET),
        ("manual", MANUAL),
    ):
        ref = refs[role]
        if not isinstance(ref, dict) or not isinstance(ref.get("document_id"), str):
            return False
        doc = documents.get(ref["document_id"])
        expected_role = "warranty" if role == "policy" else role
        if (
            doc is None
            or not has_purpose(doc, expected_role)
            or doc.get("blob_sha256") != expected_sha
            or ref.get("blob_sha256") != expected_sha
            or ref.get("document_revision") != doc.get("document_revision")
            or pid not in doc.get("product_ids", [])
            or ref["document_id"] not in product.get("documents", [])
        ):
            return False
    if scope.get("document_ids") != [
        refs["policy"]["document_id"]
    ] or not axis_span_valid(model, value.get("datasheet_axis")):
        return False
    source_ids = scope.get("source_chunk_ids")
    if not isinstance(source_ids, list) or set(source_ids) != {
        *SOURCES,
        DATA_MODELS,
        MANUAL_MODEL,
    }:
        return False
    policy = value.get("policy")
    if not isinstance(policy, dict) or not isinstance(policy.get("sources"), dict):
        return False
    for cid in SOURCES:
        if external_axis_anchors.get(anchor_key(cid)) != policy["sources"].get(cid):
            return False
    supporting_rows = []
    for cid in (DATA_MODELS, MANUAL_MODEL):
        item = external_axis_anchors.get(hs3_anchor_key(cid))
        if not isinstance(item, dict):
            return False
        sha_, page, kind, body = (
            item.get("source_sha256"),
            item.get("page"),
            item.get("kind"),
            item.get("text"),
        )
        if (
            not isinstance(sha_, str)
            or type(page) is not int
            or not isinstance(kind, str)
            or not isinstance(body, str)
        ):
            return False
        supporting_rows.append((cid, sha_, page, kind, body))
    if len(hs3_anchors(supporting_rows)) != 2:
        return False
    data = external_axis_anchors[hs3_anchor_key(DATA_MODELS)]["text"]
    manual = external_axis_anchors[hs3_anchor_key(MANUAL_MODEL)]["text"]
    if (
        model not in data
        or "HS3: Product model series." not in manual
        or "P: Professional model" not in manual
        or "X: Quantity of the battery modules, ranging from 1 to 8." not in manual
    ):
        return False
    result = render_terms(value, source_ids)
    return bool(
        result
        and result[0] == text
        and chunk_id == evidence_id(model, refs["policy"]["document_id"], text)
    )


def answers(hit: dict[str, Any], notes: Sequence[Any]) -> dict[str, str]:
    """Only the exact validated original conditions authorize the period answer."""
    cid, text, models, language = (
        hit.get("chunk_id"),
        hit.get("text"),
        hit.get("product_models"),
        hit.get("answer_language"),
    )
    if (
        not isinstance(cid, str)
        or not cid.startswith(PREFIX)
        or not isinstance(text, str)
        or not isinstance(models, list)
        or len(models) != 1
        or language not in {"en", "de"}
    ):
        return {}
    expected = rendered(str(models[0]))
    if (
        expected is None
        or len(notes) != len(expected[1])
        or any(
            (
                getattr(note, "chunk_id", None),
                getattr(note, "page", None),
                getattr(note, "lang", None),
                getattr(note, "quote", None),
            )
            != (item["chunk_id"], item["page"], item["lang"], item["quote"])
            for note, item in zip(notes, expected[1], strict=True)
        )
    ):
        return {}
    original = re.sub(r"\[n[1-9]\d*=([^\[\]\n]+)\]", r"\1", text)
    if original != expected[0]:
        return {}
    period = re.search(r"\| Warranty / Garantie \| \[n([1-9]\d*)=Ten years\] \|", text)
    months = re.search(
        r"\| Production / Herstellung \| \[n([1-9]\d*)=Six months\] \|", text
    )
    if period is None or months is None:
        return {}
    duration = f"{{fact:{cid}.n{period.group(1)}}}"
    six = f"{{fact:{cid}.n{months.group(1)}}}"
    answer = (
        f"SAJ's standard HS3 warranty is {duration}. It starts on the earlier of the first installation date or {six} after production. "
        "The policy applies to products purchased and installed in Europe and supplied by SAJ or its authorized partners. "
        "The product must meet SAJ specifications and the manual's operating conditions. Internet connection and registration can affect the full term. Other exclusions apply."
        if language == "en"
        else f"Die Standardgarantie von SAJ für HS3 beträgt {duration}. Sie beginnt mit der ersten Installation oder {six} nach der Herstellung, je nachdem, welcher Zeitpunkt früher liegt. "
        "Die Regelung gilt für Produkte, die in Europa gekauft und installiert sowie von SAJ oder autorisierten Partnern geliefert wurden. "
        "Das Produkt muss die SAJ-Spezifikationen und die Betriebsbedingungen im Handbuch erfüllen. Internetverbindung und Registrierung können die volle Laufzeit beeinflussen. Weitere Ausschlüsse gelten."
    )
    return {"period": answer, "start": answer, "general": answer}
