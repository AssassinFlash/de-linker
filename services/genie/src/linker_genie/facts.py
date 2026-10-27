"""Facts collected from this turn's tool results, keyed for hydration and checks.

A fact ID is a stable string the model may put in `{fact:ID}` and in `refs`.
Product IDs come from search-products / get-product / compare-products.
Chunk IDs come from search-knowledge, and so do the figures of each chunk
(`CHUNK_ID.nK`, `figures.tag`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linker_genie.figures import swap_decimals
from linker_genie.stock import phrase
from linker_genie.tools import READ_ATTACHMENT, READ_PAGE, READ_PLANNING, READ_SOLUTION


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
    # Product ID → the commerce object a product ability returned for this
    # customer (price_visible, price, price_line, price_reason; #242), from which
    # the service fills the product cards' price lines (prices.fill).
    commerce: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Product ID → in_stock, only when the tool row is a real product
    # (_real_product). ProductCommerce::hidden is absent. A price line is
    # not this marker (#415).
    stock_flags: dict[int, bool] = field(default_factory=dict)

    def add(self, fact: Fact) -> None:
        self.facts[fact.id] = fact

    def configurator_link(self) -> Fact | None:
        """An owned project destination takes priority over a generic size hint."""
        return self.facts.get("planning.url") or self.facts.get("size.configurator_url")

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
    `locale` is the answer language: the question's language when that
    question is clearly one language, otherwise the page. It is not always
    the request locale. The abilities return both sides and the choice
    belongs to the turn.
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
        _from_inquiry(gathered, payload, locale)
    elif name.endswith("handoff-team"):
        _from_handoff(gathered, payload, locale)
    elif name == READ_PAGE:
        _from_page(gathered, payload)
    elif name == READ_SOLUTION:
        _from_solution(gathered, payload)
    elif name == READ_PLANNING:
        if "error" not in payload:
            gathered.add(
                Fact(
                    id="planning",
                    value=str(payload.get("title") or ""),
                    source="read-planning-project",
                )
            )
            if isinstance(payload.get("text"), str):
                gathered.add(
                    Fact(
                        id="planning.text",
                        value=payload["text"],
                        source="read-planning-project",
                    )
                )
            for figure, value in payload.get("figures", {}).items():
                if isinstance(figure, str) and isinstance(value, str):
                    gathered.add(
                        Fact(id=figure, value=value, source="read-planning-project")
                    )
            if isinstance(payload.get("workspace_url"), str):
                gathered.add(
                    Fact(
                        id="planning.url",
                        value=payload["workspace_url"],
                        source="read-planning-project",
                    )
                )
    elif name == READ_ATTACHMENT:
        _from_attachment(gathered, payload, locale)
    return gathered


# Verdicts a pairing tool cleared for a card. `_from_search` qualifies those
# batteries, and the card fill (#376) lists the same ones: one vocabulary.
RELEASED_VERDICTS = frozenset({"released", "released_with_accessory"})


def _as_product_id(value: Any) -> int | None:
    if isinstance(value, int) and value >= 1:
        return value
    return None


def pairing_entries(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The pairings on one qualified product, or None when the row has none.

    An empty list is not a pairing row. check-compatibility is a different
    tool and does not arrive as a `pairings` list.
    """
    pairings = item.get("pairings")
    if not isinstance(pairings, list) or not pairings:
        return None
    return [entry for entry in pairings if isinstance(entry, dict)]


def released_ids(item: dict[str, Any]) -> list[int] | None:
    """The searched product, then each battery `RELEASED_VERDICTS` cleared.

    Order is the tool's. None when `item` is not a pairing row. An id already
    listed is not repeated.
    """
    entries = pairing_entries(item)
    if entries is None:
        return None
    ids: list[int] = []
    product_id = _as_product_id(item.get("product_id"))
    if product_id is not None:
        ids.append(product_id)
    for entry in entries:
        if entry.get("verdict") not in RELEASED_VERDICTS:
            continue
        paired = _as_product_id(entry.get("product_id"))
        if paired is not None and paired not in ids:
            ids.append(paired)
    return ids or None


def pairing_sets_in_search(payload: dict[str, Any]) -> list[list[int]]:
    """One released-id list per qualified row that carries pairings."""
    sets: list[list[int]] = []
    for item in payload.get("qualified") or []:
        if not isinstance(item, dict):
            continue
        ids = released_ids(item)
        if ids:
            sets.append(ids)
    return sets


def released_pair(call: dict[str, Any]) -> list[int] | None:
    """The two products of one released check-compatibility call, argument order.

    None when the call is not that tool, or the verdict is not a released one.
    A pair that was not released is not a card set to fill.
    """
    name = str(call.get("name") or "")
    if not name.endswith("check-compatibility"):
        return None
    result = call.get("result")
    if not isinstance(result, dict) or result.get("verdict") not in RELEASED_VERDICTS:
        return None
    arguments = call.get("arguments")
    if not isinstance(arguments, dict):
        return None
    inverter = _as_product_id(arguments.get("inverter_id"))
    battery = _as_product_id(arguments.get("battery_id"))
    if inverter is not None and battery is not None and inverter != battery:
        return [inverter, battery]
    raw = arguments.get("product_ids")
    if not isinstance(raw, list) or len(raw) != 2:
        return None
    first = _as_product_id(raw[0])
    second = _as_product_id(raw[1])
    if first is None or second is None or first == second:
        return None
    return [first, second]


def pairing_card_sets(facts: TurnFacts) -> list[list[int]]:
    """Each independent pairing set in this turn's tool calls, in call order.

    One search-products row with a pairings list is one set. One released
    check-compatibility call is one set. Card fill uses this only when the
    list holds a single set: two sets are two answers and are not merged.
    """
    sets: list[list[int]] = []
    for call in facts.tool_calls:
        if not isinstance(call, dict):
            continue
        name = str(call.get("name") or "")
        if name.endswith("search-products"):
            result = call.get("result")
            if isinstance(result, dict):
                sets.extend(pairing_sets_in_search(result))
            continue
        pair = released_pair(call)
        if pair is not None:
            sets.append(pair)
    return sets


def merge(parts: list[TurnFacts]) -> TurnFacts:
    combined = TurnFacts()
    for part in parts:
        combined.facts.update(part.facts)
        combined.product_ids.update(part.product_ids)
        combined.qualified_ids.update(part.qualified_ids)
        combined.chunk_ids.update(part.chunk_ids)
        combined.tool_calls.extend(part.tool_calls)
        combined.documents.update(part.documents)
        combined.commerce.update(part.commerce)
        combined.stock_flags.update(part.stock_flags)
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
        _add_commerce(
            gathered,
            product_id,
            item.get("commerce"),
            "search-products",
            locale,
            item,
        )
        # The pairings the tool itself annotated on this inverter: the battery
        # ids become citable, a released verdict qualifies the battery for
        # cards (the tool cleared it — same rank as search qualification),
        # and verdict plus conditions become placeholder-able facts. The row
        # and the verdict set are `pairing_entries` / `RELEASED_VERDICTS`, the
        # same ones the card fill reads.
        for pairing in pairing_entries(item) or []:
            paired_id = _as_product_id(pairing.get("product_id"))
            if paired_id is None:
                continue
            gathered.product_ids.add(paired_id)
            verdict = pairing.get("verdict")
            if verdict in RELEASED_VERDICTS:
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
    extreme = payload.get("extreme")
    if isinstance(extreme, dict):
        # The ability's aggregate (#368). The model names this product; grounding
        # refuses a different card. A hidden price records no winner.
        product_id = extreme.get("product_id")
        if extreme.get("applied") is True and isinstance(product_id, int):
            gathered.add(
                Fact(
                    id="search.extreme_product_id",
                    value=str(product_id),
                    source="search-products",
                )
            )
            model = extreme.get("model")
            if isinstance(model, str) and model:
                gathered.add(
                    Fact(
                        id="search.extreme_model",
                        value=model,
                        source="search-products",
                    )
                )
        elif extreme.get("reason") == "price_hidden":
            gathered.add(
                Fact(
                    id="search.extreme_price_hidden",
                    value="1",
                    source="search-products",
                )
            )
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
        _add_commerce(
            gathered,
            product_id,
            payload.get("commerce"),
            "get-product",
            locale,
            payload,
        )
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


# One product this turn can state stock for: its id, then the flag.
StockRow = tuple[int, bool]


def stock_rows(facts: TurnFacts) -> list[StockRow] | None:
    """Product ids and stock flags this turn can state, or None.

    Qualified ids win. Otherwise the products that carry a real flag.
    A missing flag is not false. `ProductCommerce::hidden` is not an
    out-of-stock product: the row has no title, URL or SKU.
    """
    chosen = sorted(facts.qualified_ids)
    if not chosen:
        chosen = sorted(facts.stock_flags)
    if not chosen:
        return None
    rows: list[StockRow] = []
    for product_id in chosen:
        flag = facts.stock_flags.get(product_id)
        if not isinstance(flag, bool):
            return None
        rows.append((product_id, flag))
    return rows


def _real_product(record: dict[str, Any]) -> bool:
    """Whether this tool row is a product that exists.

    A published product has a title, a URL or a SKU (search-products' card,
    get-product's record). get-product's empty record, the one that carries
    `ProductCommerce::hidden`, has none of them. `price_line` is the page's
    price sentence, not this marker.
    """
    for key in ("title", "url", "sku"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _stock_flag(commerce: Any, real: bool) -> bool | None:
    """The stock flag of a real product, or None."""
    if not real or not isinstance(commerce, dict):
        return None
    flag = commerce.get("in_stock")
    if isinstance(flag, bool):
        return flag
    return None


def _add_commerce(
    gathered: TurnFacts,
    product_id: int,
    raw: Any,
    source: str,
    locale: str,
    record: dict[str, Any],
) -> None:
    """The product's commerce object for this customer (#242).

    The price stays a fact (`pID.price`) only so the quality check can tell a
    price the site let this turn see (`quality/citations.py`): the model never
    writes it (ground.py), the product card shows it (prices.fill). The stock
    flag becomes `pID.stock` as the page's status sentence (#415), and only
    for a real product (`_real_product`).
    """
    if not isinstance(raw, dict):
        return
    gathered.commerce[product_id] = raw
    if raw.get("price_visible") and raw.get("price") not in (None, ""):
        gathered.add(
            Fact(id=f"p{product_id}.price", value=str(raw["price"]), source=source)
        )
    flag = _stock_flag(raw, _real_product(record))
    if flag is None:
        return
    gathered.stock_flags[product_id] = flag
    gathered.add(
        Fact(
            id=f"p{product_id}.stock",
            value=phrase(locale, flag),
            source=source,
        )
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
            # The cart quantity, so `{fact:PRODUCTID.quantity}` hydrates. The
            # page figure (`page.nK`) is the citation the model is already told
            # to use; this is the same number, not a guess of 1.
            quantity = item.get("quantity")
            if isinstance(quantity, int) and quantity >= 0:
                gathered.add(
                    Fact(
                        id=f"p{item['product_id']}.quantity",
                        value=str(quantity),
                        source="read-page",
                    )
                )


def _from_solution(gathered: TurnFacts, payload: dict[str, Any]) -> None:
    """The saved solution the customer asks about (`solution.py`, #496): the ref
    `solution`, its text and figures (`solution.nK`), and the saved products.

    The products of the saved solution are this turn's products, so the answer may
    show them as cards (ground.py: card IDs ⊆ this turn's tool results). A refused
    login (`{"error": "login_required"}`) is not a solution: no fact, no products.
    """
    if payload.get("error") == "login_required":
        return
    gathered.add(
        Fact(
            id="solution",
            value=str(payload.get("title") or ""),
            source="read-solution",
        )
    )
    text = payload.get("text")
    if isinstance(text, str) and text:
        gathered.add(Fact(id="solution.text", value=text, source="read-solution"))
    figures = payload.get("figures")
    for figure, value in (figures if isinstance(figures, dict) else {}).items():
        if isinstance(figure, str) and isinstance(value, str) and value:
            gathered.add(Fact(id=figure, value=value, source="read-solution"))
    for item in payload.get("products") or []:
        if isinstance(item, dict) and isinstance(item.get("product_id"), int):
            gathered.product_ids.add(item["product_id"])


def _from_attachment(gathered: TurnFacts, payload: dict[str, Any], locale: str) -> None:
    """A file the customer attached (`attachments.py`, #236): the ref `attN` (its
    name), its text and its figures (`attN.nK`), as a page's are.

    The text is the customer's file read by deepseek-flash or from the PDF's text
    layer: an answer may cite it and state its figures, and only those. A figure is
    written with the turn's decimal mark (`figures.swap_decimals`; "bei 12.5" in a
    German answer, review round 1 of PR #309, item 9).
    """
    reading_id = payload.get("id")
    if not isinstance(reading_id, str) or not reading_id:
        return
    gathered.add(
        Fact(
            id=reading_id,
            value=str(payload.get("name") or ""),
            source="read-attachment",
        )
    )
    text = payload.get("text")
    if isinstance(text, str) and text:
        gathered.add(
            Fact(id=f"{reading_id}.text", value=text, source="read-attachment")
        )
    figures = payload.get("figures")
    # "" when the reading wrote no decimal number: its separators are thousands
    # marks, and swapping them blind would misplace the decimal (figures.py).
    mark = str(payload.get("decimal") or "")
    for figure, value in (figures if isinstance(figures, dict) else {}).items():
        if isinstance(figure, str) and isinstance(value, str) and value:
            gathered.add(
                Fact(
                    id=figure,
                    value=swap_decimals(value, mark, locale),
                    source="read-attachment",
                )
            )


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


def _from_inquiry(
    gathered: TurnFacts, payload: dict[str, Any], locale: str = "en"
) -> None:
    if payload.get("error") == "login_required":
        gathered.add(
            Fact(
                id="inquiry.login_required",
                value="login_required",
                source="inquiry-status",
            )
        )
        # The sentence the placeholder `{fact:inquiry.login}` names. Imported
        # here: template imports hydrate, which imports this module.
        from linker_genie.template import LOGIN_REQUIRED

        side = "de" if locale.startswith("de") else "en"
        gathered.add(
            Fact(
                id="inquiry.login", value=LOGIN_REQUIRED[side], source="inquiry-status"
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


def _from_handoff(
    gathered: TurnFacts, payload: dict[str, Any], locale: str = "en"
) -> None:
    for key in ("sentence_en", "sentence_de", "mailto"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            gathered.add(Fact(id=f"handoff.{key}", value=value, source="handoff-team"))
    # `{fact:handoff.sentence}` is the id both prompts write. The side is the
    # answer language, with the other side as a fallback when one is missing.
    side = "de" if locale.startswith("de") else "en"
    other = "en" if side == "de" else "de"
    chosen = payload.get(f"sentence_{side}")
    if not isinstance(chosen, str) or not chosen:
        chosen = payload.get(f"sentence_{other}")
    if isinstance(chosen, str) and chosen:
        gathered.add(Fact(id="handoff.sentence", value=chosen, source="handoff-team"))


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
