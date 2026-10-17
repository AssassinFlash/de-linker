"""Server-side hydration: replace `{fact:ID}` with values from this turn's tools.

The model must not write numbers. Placeholders are filled here (Rufus). There
is no rewriting of the rest of the text. Handoff summaries hydrate too: the
prompt routes out-of-scope turns through handoff-team and puts the team
mailbox sentence into the summary as `{fact:handoff.sentence_*}` — the
customer must see the real sentence, not a model paraphrase (review
2026-10-10, must-fix 1).
"""

from __future__ import annotations

import re

from linker_genie.facts import Document, Fact, TurnFacts
from linker_genie.schema import (
    Block,
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


def hydrate(output: TurnOutput, facts: TurnFacts) -> TurnOutput:
    """Return a copy whose text blocks and handoff summaries are filled.

    Document blocks become links, one per file: two refs to the same file (two
    batteries citing the same configuration instructions, trial question 4,
    2026-10-17) are one link, its cited pages joined ("pp. 3, 7").
    """
    blocks: list[Block] = []
    # File URL → (index of its link in `blocks`, the document, its cited pages).
    links: dict[str, tuple[int, Document, list[int]]] = {}
    for block in output.blocks:
        if isinstance(block, TextBlock):
            blocks.append(block.model_copy(update={"text": fill(block.text, facts)}))
        elif isinstance(block, HandoffBlock):
            blocks.append(
                block.model_copy(update={"summary": fill(block.summary, facts)})
            )
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


def fill(text: str, facts: TurnFacts) -> str:
    """Replace each `{fact:ID}` with the stored value; unknown IDs stay as-is
    so a later check can still see them."""

    def replace(match: re.Match[str]) -> str:
        fact = _lookup(facts, match.group(1))
        if fact is None:
            return match.group(0)
        unit = _unit(match.group(1)) if fact.source == "selection-facts" else None
        following = text[match.end() :].lstrip().lower()
        if unit and not following.startswith(unit.lower()):
            return f"{fact.value} {unit}"
        return fact.value

    return PLACEHOLDER.sub(replace, text)


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
