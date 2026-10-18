"""HTTP entry point: `uvicorn linker_genie.app:app`.

POST /assistant/turn and POST /turn (alias) stream one grounded turn as SSE: the
understanding layer prepares the turn (understand.py; it reads the turn's attached
files first, attachments.py), the agent writes it. The stream is `meta`, an
`attachment` and a `reading` event per file of the turn (the proxy keeps the readings
with the conversation and takes them out of what the browser gets), a `block` per
block, `done`.
POST /turn/{id}/vote and POST /assistant/turn/{id}/vote store a customer's
thumbs-up or thumbs-down for a logged turn. POST /summary writes the checked summary
of a conversation an inquiry carries (summary.py, #244). POST
/assistant/conversation/{id}/forget takes a deleted conversation's file readings out
of the turn log. Every POST carries the shell's shared token and a capped body
(gate.py). GET /health reports that the process is up.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from linker_genie import contact, ground, inquiry, jev, page, summary
from linker_genie.abilities import AbilityClient
from linker_genie.agent import (
    deepseek_access,
    make_generate,
    model_name,
    provider_name,
)
from linker_genie.cycle import TurnResult, run
from linker_genie.facts import TurnFacts
from linker_genie.gate import Gate
from linker_genie.log import TurnLog
from linker_genie.prices import LOOKUP_DEADLINE, Lookup, commerce_lookup
from linker_genie.schema import MAX_REQUEST_BYTES, TurnOutput, TurnRequest, VoteRequest
from linker_genie.storeapi import StoreVocabulary
from linker_genie.understand import Prepared, Understander
from linker_genie.vision import Vision

app = FastAPI(title="Genie - Linker's AI assistant")
logger = logging.getLogger(__name__)
# The shell's shared token and the body cap, before anything is parsed (gate.py).
app.add_middleware(Gate, limit=MAX_REQUEST_BYTES)

_log: TurnLog | None = None
_client: AbilityClient | None = None
_understander: Understander | None = None
_pages: page.PageReader | None = None
_vision: Vision | None = None


def _log_path() -> Path:
    return Path(
        os.environ.get(
            "GENIE_LOG", str(Path.home() / ".cache" / "linker-genie" / "turns.sqlite")
        )
    )


def turn_log() -> TurnLog:
    global _log
    if _log is None:
        _log = TurnLog(_log_path())
    return _log


def ability_client() -> AbilityClient:
    global _client
    if _client is None:
        # No service token, ever: the only identity is the customer's own
        # short-lived token, passed per call (linker_genie.abilities).
        _client = AbilityClient(_wp_url())
    return _client


def _wp_url() -> str:
    return os.environ.get("GENIE_WP_URL", "http://127.0.0.1")


def page_reader() -> page.PageReader:
    """The pages of the site this service serves (page.py, #234)."""
    global _pages
    if _pages is None:
        _pages = page.PageReader(_wp_url())
    return _pages


def vision() -> Vision | None:
    """deepseek-flash reading the customer's images (vision.py, #236), with the chat
    model's own key, address and name; None when no key is configured."""
    global _vision
    if _vision is None:
        access = deepseek_access()
        if access.key:
            _vision = Vision(access.key, access.base_url, model_name())
    return _vision


def understander() -> Understander:
    """Product words from the site's Store API, Jev on OpenRouter, the customer's
    page read from the site, and their files read by deepseek-flash (understand.py)."""
    global _understander
    if _understander is None:
        _understander = Understander(
            StoreVocabulary(_wp_url()).get,
            jev.from_env(),
            pages=page_reader().read,
            see=vision(),
        )
    return _understander


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}


@app.post("/assistant/turn")
@app.post("/turn")
def assistant_turn(body: TurnRequest, request: Request) -> StreamingResponse:
    """One conversation turn, grounded and hydrated, as SSE."""
    started = time.monotonic()
    prepare = getattr(request.app.state, "prepare", None)
    prepared: Prepared = (
        prepare(body)
        if prepare is not None
        else understander().prepare(body, ability_client())
    )
    # Which earlier turns of this conversation offered the team's contact, newest
    # first: one per customer message is all the repeat rule can look back on.
    offers = turn_log().offers(
        body.conversation_id, sum(1 for m in body.messages if m.role == "user")
    )
    # The cards' price lookups end LOOKUP_DEADLINE s after the turn began, so the
    # turn stays inside the shell's timeout (prices.py).
    commerce = getattr(request.app.state, "commerce", None) or commerce_lookup(
        ability_client(), body, started + LOOKUP_DEADLINE
    )
    try:
        result = _answer(body, prepared, request, commerce)
    except Exception as error:  # noqa: BLE001 - logged, then re-raised
        turn_log().record(
            conversation_id=body.conversation_id,
            locale=body.locale,
            grounded=False,
            failures=(f"internal: {error}",),
            fallback=True,
            provider=provider_name(),
            model=model_name(),
            tool_calls=[],
            output={},
            question=_question(body),
            page=body.page_context.model_dump(),
            understanding=prepared.log,
            approved=body.user.partner,
        )
        raise
    if result.retried and result.attempts > 1:
        prepared.log["retried"] = list(result.retried)
    if result.price_failures:
        # A card whose price line could not be read shows none; the cause is
        # logged with the turn, never swallowed (prices.fill).
        prepared.log["price_failures"] = list(result.price_failures)
    shipped = result.output.model_dump()
    # The inquiry confirmation card (#250): the model may ask for it, and an
    # explicit "send an inquiry" adds the action when the model did not
    # (inquiry.decide). Only the card's Send button writes the inquiry.
    if inquiry.decide(_question(body), shipped["blocks"]):
        shipped["blocks"].append({"type": "action", "name": inquiry.ACTION, "args": {}})
        prepared.log["inquiry"] = True
    offer = contact.decide(prepared.route, prepared.reading, body.messages, offers)
    if offer is not None:
        # The offer follows the answer; the model never writes it (contact.py).
        shipped["blocks"].append(offer.block().model_dump())
        problems = ground.shipped(shipped, prepared.route, offer.reason)
        if problems:
            # The service's own mistake: the answer ships without the card.
            shipped["blocks"] = [
                b for b in shipped["blocks"] if b.get("type") != "contact"
            ]
            prepared.log["contact_failures"] = problems
            offer = None
        else:
            prepared.log["contact"] = offer.reason
    code_made = prepared.route.name == "person"
    turn_id = turn_log().record(
        conversation_id=body.conversation_id,
        locale=body.locale,
        grounded=result.grounded,
        failures=result.failures,
        fallback=result.fallback,
        # A request for a person is answered by the service alone: no model ran.
        provider="service" if code_made else provider_name(),
        # "none": no model wrote this turn (model-routing audits read the field).
        model="none" if code_made else model_name(),
        tool_calls=result.facts.tool_calls,
        output=shipped,
        question=_question(body),
        page=body.page_context.model_dump(),
        understanding=prepared.log,
        approved=body.user.partner,
        contact=offer.reason if offer is not None else None,
    )
    return StreamingResponse(
        _sse(result, shipped, turn_id, prepared),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/turn/{turn_id}/vote")
@app.post("/assistant/turn/{turn_id}/vote")
def turn_vote(turn_id: int, body: VoteRequest) -> dict[str, bool]:
    """Store the customer's vote on one logged turn."""
    if not turn_log().vote(turn_id, body.vote):
        raise HTTPException(status_code=404, detail="unknown turn")
    return {"ok": True}


@app.post("/summary")
def conversation_summary(
    body: summary.SummaryRequest, request: Request
) -> JSONResponse:
    """The checked summary of a conversation for an inquiry (#244), or 422 with the
    reason it was refused; WordPress then assembles its own by rule."""
    complete = getattr(request.app.state, "summary_model", None) or summary.deepseek()
    try:
        result = summary.summarise(body, complete)
    except summary.SummaryError as error:
        # Never silent: the reason is logged here and recorded with the inquiry.
        logger.warning("summary refused: %s", error.reason)
        return JSONResponse(status_code=422, content={"error": error.reason})
    if result.dropped:
        logger.info("summary dropped quantities: %s", ", ".join(result.dropped))
    return JSONResponse(content={**result.model_dump(), "model": model_name()})


@app.post("/assistant/conversation/{conversation_id}/forget")
def forget(conversation_id: str) -> dict[str, int]:
    """The customer deleted the conversation, or Retention did: the reading text of
    its files leaves the turn log too (log.TurnLog.forget, #236)."""
    return {"purged": turn_log().forget(conversation_id)}


def _answer(
    body: TurnRequest, prepared: Prepared, request: Request, commerce: Lookup
) -> TurnResult:
    """The turn's answer: the model's, or the service's own for a request for a person
    (contact.answer; #243 — no model runs, and none can claim it sent anything)."""
    if prepared.route.name == "person":
        return TurnResult(
            output=TurnOutput(
                language=body.locale, blocks=[contact.answer(body.locale)]
            ),
            facts=TurnFacts(),
            grounded=True,
            failures=(),
            fallback=False,
            attempts=0,
        )
    generate = getattr(request.app.state, "generate", None) or make_generate(
        ability_client(), prepared=prepared, pages=page_reader().read
    )
    return run(body, generate, prepared.route, prepared.facts, commerce)


def _question(body: TurnRequest) -> str:
    """The customer message this turn answers: the thread's last user message."""
    for message in reversed(body.messages):
        if message.role == "user":
            return message.content
    return ""


def _sse(
    result: TurnResult, shipped: dict[str, object], turn_id: int, prepared: Prepared
) -> Iterator[str]:
    meta = {
        "turn_id": turn_id,
        "grounded": result.grounded,
        "fallback": result.fallback,
        "attempts": result.attempts,
        "failures": list(result.failures),
        "language": result.output.language,
        # The understanding layer's decision, so a degraded turn is visible to
        # whatever reads the stream (Jev unavailable → route "model").
        "route": prepared.route.name,
        "intent": (prepared.log.get("jev") or {}).get("intent"),
        "jev_error": prepared.log.get("jev_error"),
    }
    yield _event("meta", meta)
    # This turn's files (#236): what the shell shows for each, and the reading the
    # proxy keeps with the conversation (and takes out of the stream it stores).
    for card in prepared.cards:
        yield _event("attachment", card)
    for reading in prepared.readings:
        yield _event("reading", reading.model_dump())
    blocks = shipped.get("blocks")
    for block in blocks if isinstance(blocks, list) else []:
        yield _event("block", block)
    yield _event("done", {"ok": True})


def _event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
