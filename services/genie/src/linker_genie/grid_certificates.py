"""List the product's published certificates whose titles name the requested country."""

from __future__ import annotations

import re
from dataclasses import replace

from linker_genie.facts import Fact, TurnFacts
from linker_genie.route import Route
from linker_genie.schema import Block, DocumentBlock, Locale, TextBlock, TurnOutput
from linker_genie.source_models import model_pattern

_COUNTRIES = (
    (
        re.compile(r"\b(?:german(?:y)?|deutsch(?:land|e[nrsm]?)?)\b", re.I),
        "Germany",
        "Deutschland",
    ),
    (
        re.compile(r"\b(?:poland|polish|polen|polnisch(?:e[nrsm]?)?)\b", re.I),
        "Poland",
        "Polen",
    ),
)
_DOCUMENT = re.compile(
    r"\b(?:certificat(?:es?|ions?)|documents?|evidence|proofs?|"
    r"(?:netzanschluss|einheiten|geräte)?(?:nachweis(?:e|en)?|zertifikat(?:e|en)?))\b"
)
_FRAME = set(
    "which what where can i find get show me please list provide available published are is "
    "there the for of does have has and on in under its grid connection gridcode code compliance "
    "inverter welche welchen was wo gibt es liegen vor hat der die das den dem des "
    "für und in von zum zur sind verfügbar vorliegend vorliegenden vorhandenen veröffentlicht "
    "nach netzanschluss netzanbindung wechselrichter".split()
)


def grid_certificate_listing(
    facts: TurnFacts, route: Route, question: str, language: Locale
) -> TurnOutput | None:
    if route.show_products or len(route.named_models) != 1:
        return None
    subject = route.named_models[0]
    if (
        subject.is_conflict
        or not subject.searched_known
        or len(subject.product_ids) != 1
    ):
        return None
    words, mentions = model_pattern(subject.code).subn(" ", question.casefold())
    if not mentions or not _DOCUMENT.search(words):
        return None
    (pid,) = subject.product_ids
    product = next(
        (
            call["result"]
            for call in facts.tool_calls
            if call["name"] == "linker/get-product"
            and call["ok"]
            and call["result"].get("product_id") == pid
            and call["result"].get("model") == subject.code
        ),
        None,
    )
    if product is None:
        return None
    words = _DOCUMENT.sub(" ", words)
    if brand := product.get("brand"):
        words = re.sub(rf"\b{re.escape(brand.casefold())}\b", " ", words)
    countries = []
    for wording, en, de in _COUNTRIES:
        words, count = wording.subn(" ", words)
        if count:
            countries.append(
                (
                    re.compile(rf"\b(?:{en}|{de})\b", re.I),
                    de if language == "de" else en,
                )
            )
    if not countries or set(re.findall(r"\w+", words)) - _FRAME:
        return None

    sources = []
    for country, label in countries:
        matched = []
        for index, row in enumerate(product["documents"]):
            ref = f"p{pid}.document.{index}"
            document = facts.documents.get(ref)
            title = row.get("title_de") if language == "de" else None
            title = title or row.get("title")
            if (
                row.get("type") == "certificate"
                and title
                and document
                and document.evidence
                and country.search(title)
            ):
                matched.append((ref, replace(document, title=title, page=1), label))
        if not matched:
            return None
        sources.extend(matched)
    blocks: list[Block] = []
    for ref, document, label in sources:
        key = ref + ".title"
        facts.add(Fact(id=key, value=document.title, source="get-product"))
        facts.documents[ref] = document
        title = f"„{{fact:{key}}}“" if language == "de" else f"“{{fact:{key}}}”"
        blocks.extend(
            [
                TextBlock(text=f"{label} · {title}", refs=[str(pid), ref]),
                DocumentBlock(ref=ref),
            ]
        )
    return TurnOutput(language=language, blocks=blocks)
