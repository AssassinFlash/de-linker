"""Server-side hydration: replace `{fact:ID}` with values from this turn's tools.

The model must not write numbers. Placeholders are filled here (Rufus). There
is no rewriting of the rest of the text. Handoff summaries hydrate too: the
prompt routes out-of-scope turns through handoff-team and puts the team
mailbox sentence into the summary as `{fact:handoff.sentence}` — the
customer must see the real sentence, not a model paraphrase (review
2026-10-10, must-fix 1). The service picks the sentence of the answer
language, including when the model named `sentence_en` or `sentence_de`.

An answer that rests on documents links them, and the service adds those links
(#257, docs/specs/10-knowledge-index.md 引用与核验): every chunk a text block names
in `refs` or takes a figure from (`{fact:CHUNK_ID.nK}`) gets a document block when
the answer has none for it, so it becomes a link with its page like any other.
A document figure is written in the turn's language (`figures.localize`), and a
unit the model repeats after it is dropped.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from linker_genie.facts import (
    Document,
    Fact,
    Qualification,
    TurnFacts,
    pairing_card_sets,
)
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
# A handoff placeholder names the mailbox sentence. Whichever id the model
# wrote, the customer reads the sentence of the answer language.
_HANDOFF_IDS = frozenset(
    {"handoff.sentence", "handoff.sentence_en", "handoff.sentence_de"}
)
PAGE_WORD = {"en": "p.", "de": "S."}
PAGES_WORD = {"en": "pp.", "de": "S."}

PLACEHOLDER = re.compile(r"\{fact:([^}]+)\}")
# A placeholder and the word the model wrote right after it, to compare that word
# with the unit a document figure already ends with. Only unit-shaped characters:
# the word must not swallow the next placeholder of "{fact:…n1}–{fact:…n2}"
# (issue #257 trial run, a range lost its upper figure).
_PLACEHOLDER_AND_WORD = re.compile(r"\{fact:([^}]+)\}((?:\s?[A-Za-zÄÖÜäöü%°²µΩ℃]+)?)")
_UNIT_TAIL = re.compile(r"\d\s?([^\s\d]+)$")
# Routes whose tools the model may have chosen. `model` is the route when Jev
# reads a pairing and code does not prefetch (route.plan), so the model calls
# the tool itself. Any other route keeps the cards the model wrote.
_PAIRING_ROUTES = frozenset({"pairing", "model"})


def complete_pairing_cards(
    output: TurnOutput,
    facts: TurnFacts,
    route: Route | None,
    card_limit: int | None = None,
) -> TurnOutput:
    """Fill one pairing answer's cards from the single released set (#376).

    Campaign 331 `s4-repeat` asked the same question four times (DE turns
    62–65, EN 35–38). The route and the search stayed put. The cards did not:
    a German grounding retry, and a first attempt that simply left the
    inverter out, shipped the batteries alone. The c376 replay before this
    fill dropped product 4107 on `attempts=1` as well (rounds 1 and 3). No
    shopping assistant publishes a rule for what a repeated turn must keep;
    the evidence for the rule is that campaign.

    The set comes from `facts.pairing_card_sets`, which reads the same
    verdicts as `facts._from_search`. One search-products row with pairings
    is the qualified product, then each released battery, in the tool's
    order. One released check-compatibility call is the two products it was
    given, in argument order. A verdict that is not released does not make a
    set. The prose stays the model's. When the cards already are the set,
    their order is kept. When they are a narrower subset, the block becomes
    the set and the first text block cites every id in it.

    The fill runs on the first attempt and on a retry: the c376 rounds that
    dropped the inverter had not retried. It runs for a code route named
    `pairing` and for a `model` route. It does not run for any other route.
    Two pairing sets in one turn stay as the model wrote them. Independent
    searches are not merged into one block.

    `inquiry.login_required` outranks every shape (`template.fallback`): the
    login sentence is the whole answer, and this function does not add cards.
    A fallback passes `card_limit` of `route.SEARCH_LIMIT`. Trial question 11
    caps that template at six cards. The six are the front of this set, so
    the searched product is not sorted out of the window. A grounded answer
    is not capped; the campaign ships the whole set.
    """
    if "inquiry.login_required" in facts.facts:
        return output
    if route is None or route.no_cards or route.name not in _PAIRING_ROUTES:
        return output
    sets = pairing_card_sets(facts)
    if len(sets) != 1:
        return output
    released = sets[0] if card_limit is None else sets[0][:card_limit]
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


def hydrate(
    output: TurnOutput,
    facts: TurnFacts,
    language: str | None = None,
    *,
    qualified_mask: Callable[[str], str] | None = None,
) -> TurnOutput:
    """Return a copy whose text blocks and handoff summaries are filled.

    `language` is the answer language. It selects owned sentences (the mailbox
    sentence, the login sentence), document page labels and the decimal mark
    of a document figure. Callers that omit it keep the output's own language.

    Ordinary document blocks become one link per file, with cited pages joined.
    A used qualified figure's page and every original condition page keep
    separate links so each opens directly at the relevant source page.

    `qualified_mask` is used only during the final seal: it hides the exact
    qualified value and source quote at their hydration sites until the seal
    restores them. Other occurrences of the same value are not affected.
    """
    language = language or output.language
    blocks: list[Block] = []
    # Ordinary citations share one file link. A qualification on another page
    # needs its own link, so the reader can open the actual condition directly.
    links: dict[tuple[str, int | None], tuple[int, Document, list[int]]] = {}
    condition_refs = {
        note.chunk_id for notes in _used_qualifications(output, facts) for note in notes
    }
    parameter_refs = {
        chunk
        for block in output.blocks
        if isinstance(block, (TextBlock, HandoffBlock))
        for fact_id in PLACEHOLDER.findall(
            block.text if isinstance(block, TextBlock) else block.summary
        )
        if fact_id in facts.facts
        if (chunk := chunk_of(fact_id)) is not None
        if chunk in facts.qualifications
    }
    parameter_refs.update(
        ref
        for block in output.blocks
        if isinstance(block, TextBlock)
        for ref in block.refs
        if ref in facts.qualifications
    )
    emitted: set[tuple[str, str]] = set()
    for block in [*output.blocks, *cited_documents(output, facts)]:
        if isinstance(block, TextBlock):
            text = fill(
                block.text,
                facts,
                language,
                emitted=emitted,
                qualified_mask=qualified_mask,
                reference_chunks=block.refs,
            )
            blocks.append(block.model_copy(update={"text": text}))
        elif isinstance(block, HandoffBlock):
            blocks.append(
                block.model_copy(
                    update={
                        "summary": fill(
                            block.summary,
                            facts,
                            language,
                            emitted=emitted,
                            qualified_mask=qualified_mask,
                        )
                    }
                )
            )
        elif (
            isinstance(block, ActionBlock)
            and block.name == "open_configurator"
            and (project_link := facts.configurator_link()) is not None
        ):
            # The configurator link is the service's, like a document link: the
            # model copied size-hint's URL wrong twice in a row on trial question
            # 14 (2026-10-17, "action open_configurator url is not from this
            # turn's tools"), so it is filled here from the tool result.
            url = project_link.value
            blocks.append(block.model_copy(update={"args": {**block.args, "url": url}}))
        elif isinstance(block, DocumentBlock):
            document = facts.documents.get(block.ref)
            if document is None:
                continue
            key = (
                document.url,
                document.page if block.ref in condition_refs | parameter_refs else None,
            )
            if key in links:
                index, first, pages = links[key]
            else:
                index, first, pages = len(blocks), document, []
                blocks.append(block)
                links[key] = (index, first, pages)
            if document.page is not None and document.page not in pages:
                pages.append(document.page)
            blocks[index] = blocks[index].model_copy(
                update={
                    "label": document_label(first, language, pages),
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
        if isinstance(block, TextBlock):
            cited.extend(ref for ref in block.refs if ref in facts.chunk_ids)
            for ref in block.refs:
                cited.extend(facts.supporting_documents.get(ref, ()))
                cited.extend(
                    note.chunk_id for note in facts.qualifications.get(ref, ())
                )
            text = block.text
        elif isinstance(block, HandoffBlock):
            text = block.summary
        elif isinstance(block, DocumentBlock):
            cited.extend(facts.supporting_documents.get(block.ref, ()))
            continue
        else:
            continue
        for fact_id in PLACEHOLDER.findall(text):
            chunk = chunk_of(fact_id)
            if chunk is not None and chunk in facts.chunk_ids:
                cited.append(chunk)
                cited.extend(facts.supporting_documents.get(chunk, ()))
                cited.extend(
                    note.chunk_id for note in facts.qualifications.get(chunk, ())
                )
    return [
        DocumentBlock(ref=chunk)
        for chunk in dict.fromkeys(cited)
        if chunk not in linked and chunk in facts.documents
    ]


def _used_qualifications(
    output: TurnOutput, facts: TurnFacts
) -> list[tuple[Qualification, ...]]:
    """Conditions of figures actually requested by the answer's placeholders."""
    used: list[tuple[Qualification, ...]] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            text = block.text
            for ref in block.refs:
                notes = facts.qualifications.get(ref, ())
                if notes and all(_quote(note) is not None for note in notes):
                    used.append(notes)
        elif isinstance(block, HandoffBlock):
            text = block.summary
        else:
            continue
        for fact_id in PLACEHOLDER.findall(text):
            chunk = chunk_of(fact_id)
            if fact_id in facts.facts and chunk in facts.qualifications:
                notes = facts.qualifications[chunk]
                if all(_quote(note) is not None for note in notes):
                    used.append(notes)
    return used


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


def fill(
    text: str,
    facts: TurnFacts,
    locale: str = "en",
    *,
    emitted: set[tuple[str, str]] | None = None,
    qualified_mask: Callable[[str], str] | None = None,
    reference_chunks: list[str] | None = None,
) -> str:
    """Replace each `{fact:ID}` with the stored value; unknown IDs stay as-is
    so a later check can still see them.

    A product fact gets its unit (UNITS) unless the text writes it. A document
    figure carries its own unit ("1000 W") and is written in the turn's language;
    when the model wrote the unit after the placeholder as well, the repeat is
    dropped ("1000 W W", issue #257 trial run).
    """

    seen = emitted if emitted is not None else set()
    used: list[Qualification] = []
    translated_policy_chunks: set[str] = set()

    if locale.startswith("de"):
        from linker_genie.warranty_named_de import qualified_named_additions

        candidates = list(reference_chunks or []) + [
            chunk
            for fact_id in PLACEHOLDER.findall(text)
            if (chunk := chunk_of(fact_id)) is not None
        ]
        for chunk in dict.fromkeys(candidates):
            if chunk not in facts.warranty_translated_de:
                continue
            original = facts.facts.get(f"{chunk}.text")
            notes = facts.qualifications.get(chunk, ())
            allowed = facts.warranty_answers.get(chunk, {})
            if original is None:
                continue
            additions = qualified_named_additions(
                chunk, original.value, notes, allowed, text
            )
            if additions is None:
                continue
            translated_policy_chunks.add(chunk)
            if additions:
                text += "\n\nWeitere Garantiebedingungen (aus dem englischen Original übersetzt):\n"
                text += "\n\n".join(additions)

    for chunk in reference_chunks or []:
        if chunk in translated_policy_chunks:
            continue
        notes = facts.qualifications.get(chunk, ())
        if notes and all(_quote(note) is not None for note in notes):
            for note in notes:
                key = (note.lang, note.quote)
                if key not in seen:
                    seen.add(key)
                    used.append(note)

    def replace(match: re.Match[str]) -> str:
        fact = _render_fact(facts, match.group(1), locale)
        if fact is None:
            return match.group(0)
        # A source chunk's `.text` is internal grounding material, not a
        # customer-ready rendering of a qualified table.
        if fact.id.endswith(".text") and fact.id[:-5] in facts.qualifications:
            return "nicht verfügbar" if locale.startswith("de") else "unavailable"
        chunk = chunk_of(fact.id)
        notes = facts.qualifications.get(chunk, ()) if chunk is not None else ()
        if notes and any(_quote(note) is None for note in notes):
            return "nicht verfügbar" if locale.startswith("de") else "unavailable"
        for note in () if chunk in translated_policy_chunks else notes:
            key = (note.lang, note.quote)
            if key not in seen:
                seen.add(key)
                used.append(note)
        after = match.group(2)
        # A figure of a document chunk, of the customer's page (page.py, #234), of
        # their saved solution (solution.py, #496) or of a file the customer
        # attached (attachments.py, #236) carries its own unit, as the text
        # printed it.
        if (
            fact.source
            in (
                "search-knowledge",
                "read-page",
                "read-solution",
                "read-attachment",
                "read-planning-project",
            )
            and chunk_of(fact.id) is not None
        ):
            value = localize(fact.value, locale)
            unit = _UNIT_TAIL.search(value)
            if notes and qualified_mask is not None:
                value = qualified_mask(value)
            if unit and after and after.strip() == unit.group(1):
                return value
            return value + after
        unit_word = _unit(match.group(1)) if fact.source == "selection-facts" else None
        following = text[match.start(2) :].lstrip().lower()
        if unit_word and not following.startswith(unit_word.lower()):
            return f"{fact.value} {unit_word}{after}"
        return fact.value + after

    filled = _PLACEHOLDER_AND_WORD.sub(replace, text)
    for note in used:
        translated = None
        if locale.startswith("de"):
            from linker_genie.compatibility_physical import (
                translate_compatibility_condition,
            )

            translated = translate_compatibility_condition(
                note.quote, note.chunk_id, note.page, note.lang
            )
        rendered = translated if translated is not None else _quote(note)
        if rendered is not None:
            label = (
                "Herstellerbedingung (Übersetzung):"
                if translated is not None
                else _qualification_label(locale, note.lang)
            )
            if qualified_mask is not None:
                rendered = qualified_mask(rendered)
            filled += f"\n\n{label} {rendered}"
    return filled


def _quote(note: Qualification) -> str | None:
    """Keep the manufacturer's wording in an unambiguous quotation."""
    body = note.quote.split(":", 1)[1].strip()
    if '"' not in body:
        return f'"{body}"'
    if "“" not in body and "”" not in body:
        return f"„{body}“"
    return None


def _qualification_label(locale: str, source_language: str) -> str:
    if locale.startswith("de"):
        return (
            "Herstellerbedingung:"
            if source_language == "de"
            else "Herstellerbedingung (englisches Original):"
        )
    return (
        "Manufacturer's condition:"
        if source_language == "en"
        else "Manufacturer's condition (German original):"
    )


def _unit(fact_id: str) -> str | None:
    for ending, unit in UNITS:
        if fact_id.endswith(ending):
            return unit
    return None


def _render_fact(facts: TurnFacts, fact_id: str, locale: str) -> Fact | None:
    """The fact to print, with owned sentences forced to `locale`.

    `handoff.sentence`, `handoff.sentence_en` and `handoff.sentence_de` all
    print `handoff.sentence_<locale>` when that fact exists. `{fact:inquiry.login}`
    prints the login sentence of `locale`, so a fact collected for the page
    cannot leak the other language.
    """
    language = "de" if locale.startswith("de") else "en"
    if fact_id in _HANDOFF_IDS:
        preferred = facts.facts.get(f"handoff.sentence_{language}")
        if preferred is not None:
            return preferred
    if fact_id == "inquiry.login" and (
        "inquiry.login" in facts.facts or "inquiry.login_required" in facts.facts
    ):
        from linker_genie.template import LOGIN_REQUIRED

        return Fact(
            id="inquiry.login",
            value=LOGIN_REQUIRED[language],
            source="inquiry-status",
        )
    return _lookup(facts, fact_id)


def _lookup(facts: TurnFacts, fact_id: str) -> Fact | None:
    """The fact for an ID, tolerating a missing leading 'p' on a product fact."""
    fact = facts.facts.get(fact_id)
    if fact is None and not fact_id.startswith("p"):
        fact = facts.facts.get(f"p{fact_id}")
    return fact


def leftover_placeholders(text: str) -> list[str]:
    """Fact IDs still present as `{fact:ID}` after a fill attempt."""
    return PLACEHOLDER.findall(text)
