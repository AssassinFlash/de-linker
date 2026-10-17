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
from dataclasses import dataclass, field
from typing import Any, Protocol

from linker_genie import knowledge
from linker_genie.abilities import AbilityClient, AbilityError
from linker_genie.embedding import EmbeddingError
from linker_genie.facts import TurnFacts, merge
from linker_genie.jev import JevError, Reading, page_state
from linker_genie.lexicon import Match, Vocabulary
from linker_genie.route import Route, Subject, plan
from linker_genie.schema import TurnRequest
from linker_genie.storeapi import VocabularyError

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
    ) -> None:
        self._vocabulary = vocabulary
        self._jev = jev
        self._jev_missing = jev_missing
        self._search = search or knowledge.SEARCH

    def prepare(self, request: TurnRequest, client: AbilityClient) -> Prepared:
        message = _last_customer_message(request)
        log: dict[str, Any] = {}
        vocabulary = self._load_vocabulary(log)
        matches = vocabulary.match(message) if vocabulary else []
        log["matches"] = [
            {"kind": m.kind, "value": m.value, "words": m.words} for m in matches
        ]
        subject = _subject(request, matches, vocabulary)
        reading = self._read(request, message, vocabulary, log)
        # Jev's yes/no answers count from 0.5, the cut the measurement scored
        # about_this_page by (59 of 60 right, docs/research/2026-10-17-jev-intent/).
        about_page = reading is not None and reading.about_this_page >= 0.5
        if about_page and request.page_context.product_id:
            subject = _with_page_product(subject, request, vocabulary)
        bare = vocabulary.bare(message) if vocabulary else False
        route = plan(message, matches, reading, subject, request.locale, bare)
        log.update(route.as_log())
        prepared = Prepared(route=route, log=log)
        _run_calls(prepared, request, client, self._search)
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
                message, page_state(request.page_context.type, name), history
            )
        except JevError as error:
            log["jev_error"] = str(error)
            logger.warning(
                "genie jev failed, deepseek-flash decides this turn: %s", error
            )
            return None
        log["jev"] = reading.as_log()
        return reading


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


def _run_calls(
    prepared: Prepared,
    request: TurnRequest,
    client: AbilityClient,
    search: knowledge.Search = knowledge.SEARCH,
) -> None:
    parts: list[TurnFacts] = []
    failures: list[str] = []
    for call in prepared.route.calls:
        try:
            if call.ability == knowledge.NAME:
                # The document search runs in this process (knowledge.py, #257).
                payload, gathered = knowledge.record(
                    search, call.arguments, request.locale
                )
            else:
                payload, gathered = client.record(
                    call.ability,
                    call.arguments,
                    request.user.context,
                    request.locale,
                )
        except (EmbeddingError, knowledge.KnowledgeUnavailable) as error:
            failures.append(f"{call.ability}: {error}")
            prepared.knowledge_error = f"{call.ability}: {error}"
            logger.error("genie document search failed: %s", error)
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
