"""The understanding layer of one turn: product words, Jev, the route, its calls.

`Understander.prepare()` runs before the model: it matches the last customer message
against the product vocabulary (lexicon), asks Jev its four questions, lets the router
choose the route, and makes the route's ability calls. The model then writes the answer
from those results (agent.py), and grounding holds it to what the route requires
(ground.py).

Every failure here is logged on the turn and by the `linker_genie` logger, and the turn
goes on with what is left: without product words when the Store API cannot be read,
and with deepseek-flash deciding alone when Jev cannot answer — the one degradation
ticket #233 allows. None of them is silent. A document search that fails does not go
on: it is kept as `knowledge_error` and ends the turn in the cycle's fallback, because
an answer without the documents it needed must not ship (#257).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Protocol

from linker_genie import attachments, contact, knowledge, page
from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.embedding import EmbeddingError
from linker_genie.facts import TurnFacts, merge
from linker_genie.jev import JevError, Reading, page_state
from linker_genie.lexicon import Match, Vocabulary
from linker_genie.nameplate import Identified, card, identify
from linker_genie.route import Call, Route, Subject, nameplate, person, plan, with_page
from linker_genie.schema import (
    MAX_READINGS,
    AttachmentReading,
    PageContext,
    TurnRequest,
)
from linker_genie.storeapi import VocabularyError
from linker_genie.vision import See

logger = logging.getLogger("linker_genie")


class Reader(Protocol):
    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading: ...


@dataclass
class Prepared:
    """What code did before the model: the route, its results and their facts."""

    route: Route
    facts: TurnFacts = field(default_factory=TurnFacts)
    # [{name, arguments, result}] of the calls that answered, for the model's prompt.
    results: list[dict[str, Any]] = field(default_factory=list)
    log: dict[str, Any] = field(default_factory=dict)
    # The document search of the route failed (the encoder or the index): the
    # generation raises it (agent.make_generate), no answer is written without it.
    knowledge_error: str | None = None
    # Jev's answers, None when Jev did not run or failed: the contact offer reads
    # its "asks for a person or is frustrated" (contact.decide, #243).
    reading: Reading | None = None
    # The files read this turn (#236): the proxy keeps them with the conversation.
    readings: list[AttachmentReading] = field(default_factory=list)
    # Every reading of the conversation as a tool result, for the model's prompt.
    attachments: list[dict[str, Any]] = field(default_factory=list)
    # What the shell shows for each file of this turn (nameplate.card).
    cards: list[dict[str, Any]] = field(default_factory=list)

    @property
    def calls_made(self) -> int:
        return len(self.route.calls)


def nothing(request: TurnRequest) -> Prepared:
    """No understanding: the model decides alone (tests that bypass the layer)."""
    del request
    return Prepared(route=Route("model"))


class Understander:
    """The layer, with its two sources injected (both may be absent)."""

    def __init__(
        self,
        vocabulary: Callable[[], Vocabulary] | None,
        jev: Reader | None,
        jev_missing: str = "OPENROUTER_API_KEY is not configured",
        search: knowledge.Search | None = None,
        pages: page.Reader | None = None,
        see: See | None = None,
    ) -> None:
        self._vocabulary = vocabulary
        self._jev = jev
        self._jev_missing = jev_missing
        self._search = search or knowledge.SEARCH
        self._pages = pages or no_pages
        # deepseek-flash reading an image (vision.py); None without a key, and then
        # every file of a turn is logged as not read.
        self._see = see

    def prepare(self, request: TurnRequest, client: AbilityClient) -> Prepared:
        message = _last_customer_message(request)
        log: dict[str, Any] = {}
        phrase = contact.asks_for_person(message)
        if phrase is not None:
            # A request for a person is answered in code, before Jev and the model
            # (#243): the turn is contact.answer() and the contact card.
            log["person_phrase"] = phrase
            route = person([f"person phrase: {phrase}"])
            log.update(route.as_log())
            return Prepared(route=route, log=log)
        vocabulary = self._load_vocabulary(log)
        matches = vocabulary.match(message) if vocabulary else []
        log["matches"] = [
            {"kind": m.kind, "value": m.value, "words": m.words} for m in matches
        ]
        subject = _subject(request, matches, vocabulary)
        # This turn's files are read first (#236): a nameplate decides the route.
        fresh = (
            attachments.read(request.attachments, len(request.readings), self._see)
            if request.attachments
            else []
        )
        plate = _first_nameplate(fresh, vocabulary)
        reading: Reading | None = None
        if plate is not None:
            # A nameplate is confirmed before anything else is answered about it, so
            # Jev is not asked: the route is the nameplate's (route.nameplate).
            route = nameplate(plate, request.locale, subject, [])
        else:
            reading = self._read(request, message, vocabulary, log)
            # Jev's yes/no answers count from 0.5, the cut the measurement scored
            # about_this_page by (59 of 60 right, docs/research/2026-10-17-jev-intent/).
            about_page = reading is not None and reading.about_this_page >= 0.5
            if about_page and request.page_context.product_id:
                subject = _with_page_product(subject, request, vocabulary)
            bare = vocabulary.bare(message) if vocabulary else False
            route = plan(message, matches, reading, subject, request.locale, bare)
            # Jev's answer decides when the page's own content is read (#234).
            route = with_page(
                route,
                request.page_context,
                about_page,
                request.user.logged_in,
                subject,
                message,
            )
        log.update(route.as_log())
        prepared = Prepared(route=route, log=log, reading=reading, readings=fresh)
        _run_calls(prepared, request, client, self._search, self._pages)
        _add_readings(prepared, [*request.readings, *fresh], fresh, plate, vocabulary)
        return prepared

    def _load_vocabulary(self, log: dict[str, Any]) -> Vocabulary | None:
        if self._vocabulary is None:
            return None
        try:
            return self._vocabulary()
        except VocabularyError as error:
            log["vocabulary_error"] = str(error)
            logger.warning("genie vocabulary unavailable: %s", error)
            return None

    def _read(
        self,
        request: TurnRequest,
        message: str,
        vocabulary: Vocabulary | None,
        log: dict[str, Any],
    ) -> Reading | None:
        if self._jev is None:
            log["jev_error"] = self._jev_missing
            logger.warning("genie jev unavailable: %s", self._jev_missing)
            return None
        product_id = request.page_context.product_id
        name = vocabulary.names.get(product_id) if vocabulary and product_id else None
        history = [(m.role, m.content) for m in request.messages[:-1]]
        try:
            reading = self._jev.read(
                message,
                page_state(request.page_context.type, name, request.page_context.title),
                history,
            )
        except JevError as error:
            log["jev_error"] = str(error)
            logger.warning(
                "genie jev failed, deepseek-flash decides this turn: %s", error
            )
            return None
        log["jev"] = reading.as_log()
        return reading


def _first_nameplate(
    fresh: list[AttachmentReading], vocabulary: Vocabulary | None
) -> Identified | None:
    for reading in fresh:
        found = identify(reading, vocabulary)
        if found is not None:
            return found
    return None


def _add_readings(
    prepared: Prepared,
    readings: list[AttachmentReading],
    fresh: list[AttachmentReading],
    plate: Identified | None,
    vocabulary: Vocabulary | None,
) -> None:
    """Every reading of the conversation as this turn's facts; a card per new file.

    The conversation keeps the latest `MAX_READINGS` (the proxy cuts the same way).
    """
    parts = [prepared.facts]
    for item in readings[-MAX_READINGS:]:
        payload, gathered = attachments.record(item)
        parts.append(gathered)
        prepared.attachments.append(payload)
    prepared.facts = merge(parts)
    shown = [
        pid
        for result in prepared.results
        if result["name"] == "linker/search-products"
        for pid in _qualified(result["result"])
    ]
    labels = dict(vocabulary.labels) if vocabulary else {}
    for item in fresh:
        identified = (
            plate if plate is not None and plate.reading_id == item.id else None
        )
        if identified is None and item.kind == "nameplate":
            identified = identify(item, vocabulary)
        prepared.cards.append(card(item, identified, shown, labels))
    if fresh:
        prepared.log["attachments"] = [
            {
                "id": item.id,
                "kind": item.kind,
                "failed": item.failed,
                "match": c.get("match"),
            }
            for item, c in zip(fresh, prepared.cards, strict=True)
        ]


def _qualified(result: Any) -> list[int]:
    found: list[int] = []
    for item in (
        (result or {}).get("qualified") or [] if isinstance(result, dict) else []
    ):
        pid = item.get("product_id") if isinstance(item, dict) else None
        if isinstance(pid, int) and pid not in found:
            found.append(pid)
    return found


def _last_customer_message(request: TurnRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return ""


def _subject(
    request: TurnRequest, matches: list[Match], vocabulary: Vocabulary | None
) -> Subject:
    ids: list[int] = []
    for match in matches:
        if match.kind == "model":
            for product_id in sorted(match.product_ids):
                if product_id not in ids:
                    ids.append(product_id)
    if not ids and request.page_context.type == "product":
        # A product page's question without a model word is about that product
        # ("datasheet please" on the H2-10K-T3 page).
        if request.page_context.product_id:
            ids.append(request.page_context.product_id)
    if not ids and request.page_context.type == "draft":
        # On the solution draft, "do these work together?" is about its products.
        ids.extend(dict.fromkeys(request.page_context.draft_ids or []))
    return Subject(
        ids=tuple(ids),
        device_class=dict(vocabulary.device_class) if vocabulary else {},
        labels=dict(vocabulary.labels) if vocabulary else {},
        phase=dict(vocabulary.phase) if vocabulary else {},
        series_members=dict(vocabulary.series_members) if vocabulary else {},
    )


def _with_page_product(
    subject: Subject, request: TurnRequest, vocabulary: Vocabulary | None
) -> Subject:
    product_id = request.page_context.product_id
    if product_id is None or product_id in subject.ids:
        return subject
    return Subject(
        ids=(product_id, *subject.ids),
        device_class=subject.device_class,
        labels=subject.labels,
        phase=subject.phase,
        series_members=subject.series_members,
    )


def no_pages(context: PageContext, question: str, logged_in: bool) -> dict[str, Any]:
    """The page reader of a service that has none configured: every read fails."""
    del context, question, logged_in
    raise page.PageUnavailable("no page reader is configured")


def _run_calls(
    prepared: Prepared,
    request: TurnRequest,
    client: AbilityClient,
    search: knowledge.Search = knowledge.SEARCH,
    pages: page.Reader = no_pages,
) -> None:
    """Run the route's calls side by side; results and facts keep the route's order.

    The calls do not depend on each other (route.py makes them from the message, the
    page and the subject alone), so the page read runs while the abilities and the
    document search do (review of PR #295: the page read added its time to every
    page question when it ran first).
    """
    question = _last_customer_message(request)

    def one(call: Call) -> tuple[dict[str, Any], TurnFacts]:
        if call.ability == page.NAME:
            # The page is read in this process from the site (page.py, #234).
            return page.record(
                pages, request.page_context, question, request.user.logged_in
            )
        if call.ability == knowledge.NAME:
            # The document search runs in this process (knowledge.py, #257).
            return knowledge.record(search, call.arguments, request.locale)
        return client.record(
            call.ability, call.arguments, request.user.context, request.locale
        )

    calls = prepared.route.calls
    if not calls:
        prepared.facts = merge([])
        return
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(one, call) for call in calls]
    parts: list[TurnFacts] = []
    failures: list[str] = []
    for call, future in zip(calls, futures, strict=True):
        try:
            payload, gathered = future.result()
        except (EmbeddingError, knowledge.KnowledgeUnavailable) as error:
            failures.append(f"{call.ability}: {error}")
            prepared.knowledge_error = f"{call.ability}: {error}"
            logger.error("genie document search failed: %s", error)
            continue
        except page.PageUnavailable as error:
            # The answer goes on without the page; the hint tells the model to say
            # it could not read it (route.PAGE_HINT), and the log keeps the cause.
            failures.append(f"{call.ability}: {error}")
            prepared.log["page_error"] = str(error)
            logger.warning("genie page read failed: %s", error)
            continue
        except AbilityError as error:
            failures.append(f"{call.ability}: {error}")
            logger.warning("genie route call failed: %s: %s", call.ability, error)
            continue
        parts.append(gathered)
        prepared.results.append(
            {"name": call.ability, "arguments": call.arguments, "result": payload}
        )
    prepared.facts = merge(parts)
    if failures:
        prepared.log["call_failures"] = failures
