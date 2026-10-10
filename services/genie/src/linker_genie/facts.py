"""Facts collected from this turn's tool results, keyed for hydration and checks.

A fact ID is a stable string the model may put in `{fact:ID}` and in `refs`.
Product IDs come from search-products / get-product / compare-products.
Chunk IDs come from search-knowledge.
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


@dataclass
class TurnFacts:
    """Everything this turn's tools returned that an answer may cite."""

    facts: dict[str, Fact] = field(default_factory=dict)
    product_ids: set[int] = field(default_factory=set)
    qualified_ids: set[int] = field(default_factory=set)
    chunk_ids: set[str] = field(default_factory=set)
    unknown_fields: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def add(self, fact: Fact) -> None:
        self.facts[fact.id] = fact

    def ids(self) -> set[str]:
        return set(self.facts) | {str(pid) for pid in self.product_ids} | self.chunk_ids


def collect(name: str, payload: Any) -> TurnFacts:
    """Facts and IDs from one ability JSON body."""
    gathered = TurnFacts()
    if not isinstance(payload, dict):
        return gathered
    if name.endswith("search-products"):
        _from_search(gathered, payload)
    elif name.endswith("get-product"):
        _from_product(gathered, payload)
    elif name.endswith("compare-products"):
        _from_compare(gathered, payload)
    elif name.endswith("check-compatibility"):
        _from_compatibility(gathered, payload)
    elif name.endswith("size-hint"):
        _from_size_hint(gathered, payload)
    elif name.endswith("search-knowledge"):
        _from_knowledge(gathered, payload)
    elif name.endswith("inquiry-status"):
        _from_inquiry(gathered, payload)
    elif name.endswith("handoff-team"):
        _from_handoff(gathered, payload)
    return gathered


def merge(parts: list[TurnFacts]) -> TurnFacts:
    combined = TurnFacts()
    for part in parts:
        combined.facts.update(part.facts)
        combined.product_ids.update(part.product_ids)
        combined.qualified_ids.update(part.qualified_ids)
        combined.chunk_ids.update(part.chunk_ids)
        combined.tool_calls.extend(part.tool_calls)
        for field_name in part.unknown_fields:
            if field_name not in combined.unknown_fields:
                combined.unknown_fields.append(field_name)
    return combined


def _from_search(gathered: TurnFacts, payload: dict[str, Any]) -> None:
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
                text = ""
                if isinstance(condition, dict):
                    text = str(condition.get("en") or condition.get("text") or "")
                elif isinstance(condition, str):
                    text = condition
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
                gathered.add(
                    Fact(
                        id=f"compat.document.{paired_id}.{document_index}",
                        value=value,
                        source="search-products",
                    )
                )
    unknown = payload.get("unknown_fields")
    if isinstance(unknown, list):
        gathered.unknown_fields = [str(item) for item in unknown]


def _from_product(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    product_id = payload.get("product_id")
    if isinstance(product_id, int) and product_id > 0:
        gathered.product_ids.add(product_id)
        raw_facts = payload.get("facts")
        facts = raw_facts if isinstance(raw_facts, dict) else {}
        _add_selection_facts(gathered, product_id, facts)


def _from_compare(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    for item in payload.get("products") or []:
        if isinstance(item, dict) and isinstance(item.get("product_id"), int):
            gathered.product_ids.add(item["product_id"])
            raw_facts = item.get("facts")
            facts = raw_facts if isinstance(raw_facts, dict) else {}
            _add_selection_facts(gathered, item["product_id"], facts)


def _from_compatibility(
    gathered: TurnFacts, payload: dict[str, Any], inverter: Any = None
) -> None:
    verdict = payload.get("verdict")
    if isinstance(verdict, str) and verdict:
        gathered.add(
            Fact(id="compat.verdict", value=verdict, source="check-compatibility")
        )
    # Conditions carry numbers (module counts, voltage windows); they become
    # placeholder-able facts, otherwise the model quotes digits raw.
    for index, condition in enumerate(payload.get("conditions") or []):
        text = ""
        if isinstance(condition, dict):
            text = str(condition.get("en") or condition.get("text") or "")
        elif isinstance(condition, str):
            text = condition
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
        gathered.add(
            Fact(
                id=f"compat.document.{index}",
                value=value,
                source="check-compatibility",
            )
        )


def _from_size_hint(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    url = payload.get("configurator_url")
    if isinstance(url, str) and url:
        gathered.add(Fact(id="size.configurator_url", value=url, source="size-hint"))


def _from_knowledge(gathered: TurnFacts, payload: dict[str, Any]) -> None:
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
