"""Facts collected from this turn's tool results, keyed for hydration and checks.

A fact ID is a stable string the model may put in `{fact:ID}` and in `refs`.
Product IDs come from search-products / get-product / compare-products.
Chunk IDs come from search-knowledge, and so do the figures of each chunk
(`CHUNK_ID.nK`, `figures.tag`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    """One renderable value taken from a tool result."""

    id: str
    value: str
    source: str


@dataclass(frozen=True)
class Document:
    """A hosted document a tool of this turn returned, for a document block."""

    url: str
    title: str
    page: int | None


@dataclass
class TurnFacts:
    """Everything this turn's tools returned that an answer may cite."""

    facts: dict[str, Fact] = field(default_factory=dict)
    product_ids: set[int] = field(default_factory=set)
    qualified_ids: set[int] = field(default_factory=set)
    chunk_ids: set[str] = field(default_factory=set)
    unknown_fields: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    # Fact or chunk ID → the document it names (search-knowledge hits, pairing
    # documents), so a document block can link it instead of printing the URL.
    documents: dict[str, Document] = field(default_factory=dict)

    def add(self, fact: Fact) -> None:
        self.facts[fact.id] = fact

    def ids(self) -> set[str]:
        return (
            set(self.facts)
            | {str(pid) for pid in self.product_ids}
            | self.chunk_ids
            # A document of this turn may be cited like a chunk (trial question
            # 10 cited `p4106.document.0` in refs, 2026-10-17).
            | set(self.documents)
        )


def collect(name: str, payload: Any, locale: str = "en") -> TurnFacts:
    """Facts and IDs from one ability JSON body, in the turn's language.

    The compatibility contract writes its conditions in pairs (`{en, de}`,
    data/compatibility.json), and a German turn must read the German side:
    a condition a placeholder hydrates into the answer is customer-visible
    text, and an English sentence in a German answer fails the row the way
    `german_is_clean` fails a fallback line (R6-de, measured 2026-10-11).
    The locale is the request's, not the payload's; the abilities return
    both sides and the choice belongs to the turn.
    """
    gathered = TurnFacts()
    if not isinstance(payload, dict):
        return gathered
    if name.endswith("search-products"):
        _from_search(gathered, payload, locale)
    elif name.endswith("get-product"):
        _from_product(gathered, payload, locale)
    elif name.endswith("compare-products"):
        _from_compare(gathered, payload)
    elif name.endswith("check-compatibility"):
        _from_compatibility(gathered, payload, locale)
    elif name.endswith("size-hint"):
        _from_size_hint(gathered, payload)
    elif name.endswith("search-knowledge"):
        _from_knowledge(gathered, payload)
    elif name.endswith("inquiry-status"):
        _from_inquiry(gathered, payload)
    elif name.endswith("handoff-team"):
        _from_handoff(gathered, payload)
    elif name.endswith("read-page"):
        _from_page(gathered, payload)
    return gathered


def merge(parts: list[TurnFacts]) -> TurnFacts:
    combined = TurnFacts()
    for part in parts:
        combined.facts.update(part.facts)
        combined.product_ids.update(part.product_ids)
        combined.qualified_ids.update(part.qualified_ids)
        combined.chunk_ids.update(part.chunk_ids)
        combined.tool_calls.extend(part.tool_calls)
        combined.documents.update(part.documents)
        for field_name in part.unknown_fields:
            if field_name not in combined.unknown_fields:
                combined.unknown_fields.append(field_name)
    return combined


def _from_search(gathered: TurnFacts, payload: dict[str, Any], locale: str) -> None:
    for item in payload.get("qualified") or []:
        if not isinstance(item, dict):
            continue
        product_id = item.get("product_id")
        if not isinstance(product_id, int):
            continue
        gathered.product_ids.add(product_id)
        gathered.qualified_ids.add(product_id)
        raw_facts = item.get("facts")
        facts = raw_facts if isinstance(raw_facts, dict) else {}
        _add_selection_facts(gathered, product_id, facts)
        raw_commerce = item.get("commerce")
        commerce = raw_commerce if isinstance(raw_commerce, dict) else {}
        if commerce.get("price_visible") and commerce.get("price") not in (None, ""):
            gathered.add(
                Fact(
                    id=f"p{product_id}.price",
                    value=str(commerce["price"]),
                    source="search-products",
                )
            )
        # The pairings the tool itself annotated on this inverter: the battery
        # ids become citable, a released verdict qualifies the battery for
        # cards (the tool cleared it — same rank as search qualification),
        # and verdict plus conditions become placeholder-able facts.
        for _index, pairing in enumerate(item.get("pairings") or []):
            if not isinstance(pairing, dict):
                continue
            paired_id = pairing.get("product_id")
            if not isinstance(paired_id, int) or paired_id < 1:
                continue
            gathered.product_ids.add(paired_id)
            verdict = pairing.get("verdict")
            if verdict in ("released", "released_with_accessory"):
                gathered.qualified_ids.add(paired_id)
            if isinstance(verdict, str) and verdict:
                gathered.add(
                    Fact(
                        id=f"compat.verdict.{paired_id}",
                        value=verdict,
                        source="search-products",
                    )
                )
            for condition_index, condition in enumerate(
                pairing.get("conditions") or []
            ):
                text = _condition_text(condition, locale)
                if text:
                    gathered.add(
                        Fact(
                            id=f"compat.condition.{paired_id}.{condition_index}",
                            value=text,
                            source="search-products",
                        )
                    )
            for document_index, document in enumerate(pairing.get("documents") or []):
                if not isinstance(document, dict):
                    continue
                url = document.get("url")
                if not isinstance(url, str) or not url:
                    continue
                page = document.get("page")
                value = f"{url} · p.{page}" if isinstance(page, int) else url
                fact_id = f"compat.document.{paired_id}.{document_index}"
                gathered.add(Fact(id=fact_id, value=value, source="search-products"))
                gathered.documents[fact_id] = _document(document, url, page)
    unknown = payload.get("unknown_fields")
    if isinstance(unknown, list):
        gathered.unknown_fields = [str(item) for item in unknown]


def _from_product(
    gathered: TurnFacts, payload: dict[str, Any], locale: str = "en"
) -> None:
    product_id = payload.get("product_id")
    if isinstance(product_id, int) and product_id > 0:
        gathered.product_ids.add(product_id)
        raw_facts = payload.get("facts")
        facts = raw_facts if isinstance(raw_facts, dict) else {}
        _add_selection_facts(gathered, product_id, facts)
        raw_figures = payload.get("figures")
        if isinstance(raw_figures, dict):
            _add_figures(gathered, product_id, raw_figures, locale)
        # The product's hosted documents (datasheet, manual): linkable as
        # document blocks `pID.document.N`, never as a URL in the text (#233).
        for index, document in enumerate(payload.get("documents") or []):
            if not isinstance(document, dict):
                continue
            url = document.get("url")
            if isinstance(url, str) and url:
                gathered.documents[f"p{product_id}.document.{index}"] = _document(
                    document, url, document.get("page")
                )


def _from_compare(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    for item in payload.get("products") or []:
        if isinstance(item, dict) and isinstance(item.get("product_id"), int):
            gathered.product_ids.add(item["product_id"])
            raw_facts = item.get("facts")
            facts = raw_facts if isinstance(raw_facts, dict) else {}
            _add_selection_facts(gathered, item["product_id"], facts)


def _from_compatibility(
    gathered: TurnFacts, payload: dict[str, Any], locale: str = "en"
) -> None:
    verdict = payload.get("verdict")
    if isinstance(verdict, str) and verdict:
        gathered.add(
            Fact(id="compat.verdict", value=verdict, source="check-compatibility")
        )
    # Conditions carry numbers (module counts, voltage windows); they become
    # placeholder-able facts, otherwise the model quotes digits raw.
    for index, condition in enumerate(payload.get("conditions") or []):
        text = _condition_text(condition, locale)
        if text:
            gathered.add(
                Fact(
                    id=f"compat.condition.{index}",
                    value=text,
                    source="check-compatibility",
                )
            )
    # Documents become placeholder-able facts: a hosted URL in plain text
    # would leak its digits past the no-numbers check.
    for index, document in enumerate(payload.get("documents") or []):
        if not isinstance(document, dict):
            continue
        url = document.get("url")
        if not isinstance(url, str) or not url:
            continue
        page = document.get("page")
        value = f"{url} · p.{page}" if isinstance(page, int) else url
        fact_id = f"compat.document.{index}"
        gathered.add(Fact(id=fact_id, value=value, source="check-compatibility"))
        gathered.documents[fact_id] = _document(document, url, page)


def _from_size_hint(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    url = payload.get("configurator_url")
    if isinstance(url, str) and url:
        gathered.add(Fact(id="size.configurator_url", value=url, source="size-hint"))


def _from_page(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    """The page the customer is on (`page.py`, #234): the ref `page`, its text and
    figures (`page.nK`), and a solution draft's products.

    The products of a draft are this turn's products, so the answer may show them as
    cards (ground.py: card IDs ⊆ this turn's tool results).
    """
    gathered.add(
        Fact(id="page", value=str(payload.get("title") or ""), source="read-page")
    )
    text = payload.get("text")
    if isinstance(text, str) and text:
        gathered.add(Fact(id="page.text", value=text, source="read-page"))
    figures = payload.get("figures")
    for figure, value in (figures if isinstance(figures, dict) else {}).items():
        if isinstance(figure, str) and isinstance(value, str) and value:
            gathered.add(Fact(id=figure, value=value, source="read-page"))
    for item in payload.get("products") or []:
        if isinstance(item, dict) and isinstance(item.get("product_id"), int):
            gathered.product_ids.add(item["product_id"])


def _from_knowledge(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    """Chunk IDs, the documents they stand in, and their figures.

    A chunk is linked as a document (`documents`, a document block, #233);
    `{fact:CHUNK_ID.nK}` renders a figure as the chunk prints it (`figures.tag`,
    #257); `CHUNK_ID.text` keeps the chunk's text for the check that a hydrated
    document number stands in a chunk of this turn.
    """
    for hit in payload.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        chunk_id = hit.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            continue
        gathered.chunk_ids.add(chunk_id)
        page = hit.get("page")
        title = hit.get("title") or ""
        if isinstance(page, int):
            gathered.add(
                Fact(
                    id=chunk_id,
                    value=f"{title} · p.{page}" if title else f"p.{page}",
                    source="search-knowledge",
                )
            )
        text = hit.get("text")
        if isinstance(text, str) and text:
            gathered.add(
                Fact(id=f"{chunk_id}.text", value=text, source="search-knowledge")
            )
        url = hit.get("doc_url")
        if isinstance(url, str) and url:
            gathered.documents[chunk_id] = Document(
                url=url,
                title=str(title) or _file_name(url),
                page=page if isinstance(page, int) else None,
            )
        figures = hit.get("figures")
        for figure, value in (figures if isinstance(figures, dict) else {}).items():
            if isinstance(figure, str) and isinstance(value, str) and value:
                gathered.add(Fact(id=figure, value=value, source="search-knowledge"))


def _from_inquiry(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    if payload.get("error") == "login_required":
        gathered.add(
            Fact(
                id="inquiry.login_required",
                value="login_required",
                source="inquiry-status",
            )
        )
        return
    for item in payload.get("inquiries") or []:
        if not isinstance(item, dict):
            continue
        inquiry_id = item.get("id")
        status = item.get("status")
        if isinstance(inquiry_id, int) and isinstance(status, str):
            gathered.add(
                Fact(
                    id=f"inquiry.{inquiry_id}.status",
                    value=status,
                    source="inquiry-status",
                )
            )


def _from_handoff(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    for key in ("sentence_en", "sentence_de", "mailto"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            gathered.add(Fact(id=f"handoff.{key}", value=value, source="handoff-team"))


def _add_figures(
    gathered: TurnFacts, product_id: int, figures: dict[str, Any], locale: str
) -> None:
    """The datasheet figures get-product returns (n_mppt, max_pv_input_v, …).

    Each is a cited value of the hosted datasheet (Products/SelectionFacts figures
    meta); without them the model had no placeholder for "how many MPPT" (trial
    question 3, 2026-10-17) and wrote the digit, which grounding refused. A German
    turn reads `value_de` where the figure has one. A selection fact of the same
    key stays: it is the one search-products filters on.
    """
    for key, figure in figures.items():
        if not isinstance(figure, dict):
            continue
        fact_id = f"p{product_id}.{key}"
        if fact_id in gathered.facts:
            continue
        value = figure.get("value")
        german = figure.get("value_de")
        if locale.startswith("de") and isinstance(german, str) and german:
            value = german
        if not isinstance(value, str) or not value:
            continue
        unit = figure.get("unit")
        rendered = f"{value} {unit}" if isinstance(unit, str) and unit else value
        gathered.add(Fact(id=fact_id, value=rendered, source="datasheet-figures"))


def _document(document: dict[str, Any], url: str, page: Any) -> Document:
    title = document.get("title")
    return Document(
        url=url,
        title=title if isinstance(title, str) and title else _file_name(url),
        page=page if isinstance(page, int) else None,
    )


def _file_name(url: str) -> str:
    """The document's file name without extension, for a document with no title."""
    name = url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
    return name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ") or url


def _condition_text(condition: Any, locale: str) -> str:
    """A compatibility condition in the turn's language.

    The contract's conditions are written as `{en, de}` pairs and the data is
    written English-first: a German turn reads the German side, falling back
    to the English one when the pair is half-written (`TradeRules::word`
    reads the data the same way), while an English turn reads the English
    side only - an English answer must not carry a German sentence any more
    than the reverse. The older plain-string or `text` shapes stay readable;
    an empty return means the condition is skipped.
    """
    if isinstance(condition, str):
        return condition
    if not isinstance(condition, dict):
        return ""
    sides = ("de", "en") if locale.startswith("de") else ("en",)
    for side in sides:
        value = condition.get(side)
        if isinstance(value, str) and value:
            return value
    text = condition.get("text")
    return str(text) if isinstance(text, str) else ""


def _add_selection_facts(
    gathered: TurnFacts, product_id: int, facts: dict[str, Any]
) -> None:
    for key, value in facts.items():
        if value in (None, "", "unknown"):
            continue
        if isinstance(value, dict) and "min" in value and "max" in value:
            rendered = f"{value['min']}–{value['max']}"
        else:
            rendered = str(value)
        gathered.add(
            Fact(
                id=f"p{product_id}.{key}",
                value=rendered,
                source="selection-facts",
            )
        )
