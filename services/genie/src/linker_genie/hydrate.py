"""Server-side hydration: replace `{fact:ID}` with values from this turn's tools.

The model must not write numbers. Placeholders are filled here (Rufus). There
is no rewriting of the rest of the text. Handoff summaries hydrate too: the
prompt routes out-of-scope turns through handoff-team and puts the team
mailbox sentence into the summary as `{fact:handoff.sentence_*}` — the
customer must see the real sentence, not a model paraphrase (review
2026-10-10, must-fix 1).

An answer that rests on documents links them, and the service adds those links
(#257, docs/specs/10-knowledge-index.md 引用与核验): every chunk a text block names
in `refs` or takes a figure from (`{fact:CHUNK_ID.nK}`) gets a document block when
the answer has none for it, so it becomes a link with its page like any other.
A document figure is written in the turn's language (`figures.localize`), and a
unit the model repeats after it is dropped.
"""

from __future__ import annotations

import re

from linker_genie.facts import Document, Fact, TurnFacts
from linker_genie.figures import chunk_of, localize
from linker_genie.route import Route
from linker_genie.schema import (
    ActionBlock,
    Block,
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnOutput,
)

# The page abbreviation of a document link, per language (copy review:
# docs/acceptance/2026-10-17/233/copy-review.md).
PAGE_WORD = {"en": "p.", "de": "S."}
PAGES_WORD = {"en": "pp.", "de": "S."}

PLACEHOLDER = re.compile(r"\{fact:([^}]+)\}")
# A placeholder and the word the model wrote right after it, to compare that word
# with the unit a document figure already ends with. Only unit-shaped characters:
# the word must not swallow the next placeholder of "{fact:…n1}–{fact:…n2}"
# (issue #257 trial run, a range lost its upper figure).
_PLACEHOLDER_AND_WORD = re.compile(r"\{fact:([^}]+)\}((?:\s?[A-Za-zÄÖÜäöü%°²µΩ℃]+)?)")
_UNIT_TAIL = re.compile(r"\d\s?([^\s\d]+)$")
# Verdicts the pairing tool cleared for a card (facts._from_search).
_RELEASED = frozenset({"released", "released_with_accessory"})


def released_pairing_ids(facts: TurnFacts) -> list[int]:
    """The searched product, then each battery the pairing search released.

    Order is the tool's. A search without a `pairings` list does not contribute:
    check-compatibility of two named products is not this set.
    """
    ids: list[int] = []
    seen: set[int] = set()
    for call in facts.tool_calls:
        name = str(call.get("name") or "")
        if not name.endswith("search-products"):
            continue
        result = call.get("result")
        if not isinstance(result, dict):
            continue
        for item in result.get("qualified") or []:
            if not isinstance(item, dict):
                continue
            pairings = item.get("pairings")
            if not isinstance(pairings, list) or not pairings:
                continue
            product_id = item.get("product_id")
            if (
                isinstance(product_id, int)
                and product_id >= 1
                and product_id not in seen
            ):
                ids.append(product_id)
                seen.add(product_id)
            for pairing in pairings:
                if not isinstance(pairing, dict):
                    continue
                if pairing.get("verdict") not in _RELEASED:
                    continue
                paired = pairing.get("product_id")
                if isinstance(paired, int) and paired >= 1 and paired not in seen:
                    ids.append(paired)
                    seen.add(paired)
    return ids


def complete_pairing_cards(
    output: TurnOutput, facts: TurnFacts, route: Route | None
) -> TurnOutput:
    """A pairing answer shows the tool's released set, not a narrower subset.

    The prose stays the model's. Cards are filled the way a cited document is
    linked: when the set already matches, the model's order is kept; when the
    model omitted a released product, the block becomes the tool's list and
    the first text block cites every id. Dossier 2026-10-19 §1.16 records no
    public rule for what a repeated turn keeps; the set is this tool result,
    so the same question cannot drop a product the search still returns.
    """
    if route is None or route.name != "pairing" or route.no_cards:
        return output
    released = released_pairing_ids(facts)
    if not released:
        return output
    blocks: list[Block] = list(output.blocks)
    card_at = [i for i, block in enumerate(blocks) if isinstance(block, CardsBlock)]
    shown: list[int] = []
    for index in card_at:
        block = blocks[index]
        if isinstance(block, CardsBlock):
            shown.extend(block.product_ids)
    if set(shown) == set(released) and len(shown) == len(released):
        return output
    cards = CardsBlock(product_ids=list(released))
    if card_at:
        blocks[card_at[0]] = cards
        for index in reversed(card_at[1:]):
            del blocks[index]
    else:
        after = next(
            (i + 1 for i, block in enumerate(blocks) if isinstance(block, TextBlock)),
            len(blocks),
        )
        blocks.insert(after, cards)
    for index, block in enumerate(blocks):
        if not isinstance(block, TextBlock):
            continue
        refs = list(block.refs)
        have = set(refs)
        for product_id in released:
            token = str(product_id)
            if token not in have and f"p{product_id}" not in have:
                refs.append(token)
                have.add(token)
        blocks[index] = block.model_copy(update={"refs": refs})
        break
    return output.model_copy(update={"blocks": blocks})


def hydrate(output: TurnOutput, facts: TurnFacts) -> TurnOutput:
    """Return a copy whose text blocks and handoff summaries are filled.

    Document blocks become links, one per file: two refs to the same file (two
    batteries citing the same configuration instructions, trial question 4,
    2026-10-17) are one link, its cited pages joined ("pp. 3, 7").
    """
    blocks: list[Block] = []
    # File URL → (index of its link in `blocks`, the document, its cited pages).
    links: dict[str, tuple[int, Document, list[int]]] = {}
    for block in [*output.blocks, *cited_documents(output, facts)]:
        if isinstance(block, TextBlock):
            text = fill(block.text, facts, output.language)
            blocks.append(block.model_copy(update={"text": text}))
        elif isinstance(block, HandoffBlock):
            blocks.append(
                block.model_copy(update={"summary": fill(block.summary, facts)})
            )
        elif (
            isinstance(block, ActionBlock)
            and block.name == "open_configurator"
            and "size.configurator_url" in facts.facts
        ):
            # The configurator link is the service's, like a document link: the
            # model copied size-hint's URL wrong twice in a row on trial question
            # 14 (2026-10-17, "action open_configurator url is not from this
            # turn's tools"), so it is filled here from the tool result.
            url = facts.facts["size.configurator_url"].value
            blocks.append(block.model_copy(update={"args": {**block.args, "url": url}}))
        elif isinstance(block, DocumentBlock):
            document = facts.documents.get(block.ref)
            if document is None:
                continue
            if document.url in links:
                index, first, pages = links[document.url]
            else:
                index, first, pages = len(blocks), document, []
                blocks.append(block)
                links[document.url] = (index, first, pages)
            if document.page is not None and document.page not in pages:
                pages.append(document.page)
            blocks[index] = blocks[index].model_copy(
                update={
                    "label": document_label(first, output.language, pages),
                    "url": document_url(first, pages),
                }
            )
        else:
            blocks.append(block)
    return output.model_copy(update={"blocks": blocks})


def cited_documents(output: TurnOutput, facts: TurnFacts) -> list[DocumentBlock]:
    """Document blocks for the chunks the answer rests on and does not link yet."""
    linked = {block.ref for block in output.blocks if isinstance(block, DocumentBlock)}
    cited: list[str] = []
    for block in output.blocks:
        if not isinstance(block, TextBlock):
            continue
        cited.extend(ref for ref in block.refs if ref in facts.chunk_ids)
        for fact_id in PLACEHOLDER.findall(block.text):
            chunk = chunk_of(fact_id)
            if chunk is not None and chunk in facts.chunk_ids:
                cited.append(chunk)
    return [
        DocumentBlock(ref=chunk)
        for chunk in dict.fromkeys(cited)
        if chunk not in linked and chunk in facts.documents
    ]


def document_label(
    document: Document, language: str, pages: list[int] | None = None
) -> str:
    """ "SAJ H2 user manual · p. 42" — the title and, when known, the cited pages.

    Several pages of one file read "pp. 3, 7" in English and "S. 3, 7" in German
    (German keeps "S." for more than one page).
    """
    cited = sorted(
        set(
            pages
            if pages is not None
            else [document.page]
            if document.page is not None
            else []
        )
    )
    if not cited:
        return document.title
    word = PAGE_WORD.get(language, "p.")
    if len(cited) > 1:
        word = PAGES_WORD.get(language, "pp.")
    # A no-break space keeps "S." and its number on one line at 390 px.
    return f"{document.title} · {word}\u00a0{', '.join(str(page) for page in cited)}"


def document_url(document: Document, pages: list[int] | None = None) -> str:
    """The document URL, opening a PDF at its first cited page.

    `#page=N` is the PDF open parameter (Adobe, "Parameters for Opening PDF Files")
    that the browsers' PDF viewers honor; any other document keeps its URL.
    """
    cited = (
        sorted(pages)
        if pages
        else ([document.page] if document.page is not None else [])
    )
    if cited and document.url.lower().split("?", 1)[0].endswith(".pdf"):
        return f"{document.url}#page={cited[0]}"
    return document.url


# The unit a selection fact is stated in, by the end of its key (the keys of
# Products/SelectionFactSet.php: ac_power_kw, pv_input_kw, usable_kwh, nominal_kwh,
# kwh_range). A value without its unit read "starts at 3 with 9 of PV input" in
# trial question 8 (2026-10-17); the unit is added when the text does not already
# follow the placeholder with it.
UNITS = (("_kwh", "kWh"), ("kwh_range", "kWh"), ("_kw", "kW"))


def fill(text: str, facts: TurnFacts, locale: str = "en") -> str:
    """Replace each `{fact:ID}` with the stored value; unknown IDs stay as-is
    so a later check can still see them.

    A product fact gets its unit (UNITS) unless the text writes it. A document
    figure carries its own unit ("1000 W") and is written in the turn's language;
    when the model wrote the unit after the placeholder as well, the repeat is
    dropped ("1000 W W", issue #257 trial run).
    """

    def replace(match: re.Match[str]) -> str:
        fact = _lookup(facts, match.group(1))
        if fact is None:
            return match.group(0)
        after = match.group(2)
        # A figure of a document chunk, of the customer's page (page.py, #234) or of
        # a file the customer attached (attachments.py, #236) carries its own unit,
        # as the text printed it.
        if (
            fact.source in ("search-knowledge", "read-page", "read-attachment")
            and chunk_of(fact.id) is not None
        ):
            value = localize(fact.value, locale)
            unit = _UNIT_TAIL.search(value)
            if unit and after and after.strip() == unit.group(1):
                return value
            return value + after
        unit_word = _unit(match.group(1)) if fact.source == "selection-facts" else None
        following = text[match.start(2) :].lstrip().lower()
        if unit_word and not following.startswith(unit_word.lower()):
            return f"{fact.value} {unit_word}{after}"
        return fact.value + after

    return _PLACEHOLDER_AND_WORD.sub(replace, text)


def _unit(fact_id: str) -> str | None:
    for ending, unit in UNITS:
        if fact_id.endswith(ending):
            return unit
    return None


def _lookup(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' on a product fact."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def leftover_placeholders(text: str) -> list[str]:
    """Fact IDs still present as `{fact:ID}` after a fill attempt."""
    return PLACEHOLDER.findall(text)
