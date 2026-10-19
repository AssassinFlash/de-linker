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

from linker_genie import contact, ground, inquiry, jev, page, parts, summary, timing
from linker_genie.abilities import AbilityClient
from linker_genie.agent import (
    deepseek_access,
    make_generate,
    model_name,
    provider_name,
)
from linker_genie.conversation import last_customer_message
from linker_genie.cycle import TurnResult, run
from linker_genie.facts import TurnFacts
from linker_genie.gate import Gate
from linker_genie.language import turn_language
from linker_genie.log import TurnLog
from linker_genie.prices import LOOKUP_DEADLINE, Lookup, commerce_lookup
from linker_genie.schema import (
    MAX_REQUEST_BYTES,
    TextBlock,
    TurnOutput,
    TurnRequest,
    VoteRequest,
)
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
    # The turn's passive phase timings (#336, timing.py): measurement only, no
    # decision reads them.
    clock = timing.Timing()
    # A start row before any wait: a model hang or a killed process leaves it
    # behind, so the unfinished turns the p95 tail must not silently omit are
    # countable (TurnLog.start; ops/turn_latency.py reports them).
    start_token = turn_log().start(body.conversation_id, body.locale)
    prepare = getattr(request.app.state, "prepare", None)
    with timing.phase(clock, timing.UNDERSTAND):
        prepared: Prepared = (
            prepare(body)
            if prepare is not None
            else understander().prepare(body, ability_client())
        )
    if prepared.timing is not None:
        clock.adopt(prepared.timing)
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
        result, service_block = _answer(body, prepared, request, commerce, clock)
    except Exception as error:  # noqa: BLE001 - logged, then re-raised
        with timing.phase(clock, timing.LOG):
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
                question=last_customer_message(body),
                page=body.page_context.model_dump(),
                understanding=prepared.log,
                approved=body.user.partner,
                # No stream will run: the record stays partial (no total) and is
                # reported as incomplete, never as a fast turn.
                timing=clock.as_log(complete=False),
            )
            turn_log().finish(start_token)
        raise
    if result.retried and result.attempts > 1:
        prepared.log["retried"] = list(result.retried)
    if result.price_failures:
        # A card whose price line could not be read shows none; the cause is
        # logged with the turn, never swallowed (prices.fill).
        prepared.log["price_failures"] = list(result.price_failures)
    shipped = result.output.model_dump()
    offer = None
    if service_block is not None:
        # A parts list's card (#251): code's block, never the model's. The inquiry
        # and contact cards are the model turns' shapes and do not apply here; the
        # customer can ask for either in a later turn.
        shipped["blocks"].append(service_block)
    else:
        # The inquiry confirmation card (#250): the model may ask for it, and an
        # explicit "send an inquiry" adds the action when the model did not
        # (inquiry.decide). Only the card's Send button writes the inquiry.
        if inquiry.decide(last_customer_message(body), shipped["blocks"]):
            shipped["blocks"].append(
                {"type": "action", "name": inquiry.ACTION, "args": {}}
            )
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
    # A request for a person, a parts list, and a short-code clarification are
    # answered by the service alone: no model ran (model-routing audits read
    # provider/model). The four model channels are unchanged; this route is a
    # sentence, not a channel.
    code_made = prepared.route.name in ("person", "parts", "clarify")
    with timing.phase(clock, timing.LOG):
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
            question=last_customer_message(body),
            page=body.page_context.model_dump(),
            understanding=prepared.log,
            approved=body.user.partner,
            contact=offer.reason if offer is not None else None,
            # Phases only: `total` and the first-event mark belong to the served
            # stream, written by _sse when it ends (a turn that never streams
            # stays partial and counts as incomplete, not as a fast turn).
            timing=clock.as_log(complete=False),
        )
        turn_log().finish(start_token)
    return StreamingResponse(
        _sse(result, shipped, turn_id, prepared, clock),
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
    body: TurnRequest,
    prepared: Prepared,
    request: Request,
    commerce: Lookup,
    clock: timing.Timing | None = None,
) -> tuple[TurnResult, dict[str, object] | None]:
    """The turn's answer: the model's; the service's own for a request for a person
    (contact.answer; #243); a short-code clarification (route.answer); or the parts
    list's (parts.answer; #251). With a service block, no model runs and none can
    claim it sent anything."""
    # A person request and a parts list are written by the service. Their
    # sentences follow the question, the same rule as a model answer.
    language = turn_language(body)
    if prepared.route.name == "person":
        return (
            TurnResult(
                output=TurnOutput(language=language, blocks=[contact.answer(language)]),
                facts=TurnFacts(),
                grounded=True,
                failures=(),
                fallback=False,
                attempts=0,
            ),
            None,
        )
    if prepared.route.name == "clarify" and prepared.route.answer:
        # The question is fixed in route.py. No tool call ran, and the model
        # does not invent one. Price lookup and inquiry send are untouched.
        return (
            TurnResult(
                output=TurnOutput(
                    language=language,
                    blocks=[TextBlock(text=prepared.route.answer)],
                ),
                facts=TurnFacts(),
                grounded=True,
                failures=(),
                fallback=False,
                attempts=0,
            ),
            None,
        )
    if prepared.parts_list is not None:
        output, block = parts.answer(prepared.parts_list, language)
        return (
            TurnResult(
                output=output,
                facts=TurnFacts(),
                grounded=True,
                failures=(),
                fallback=False,
                attempts=0,
            ),
            block.model_dump(),
        )
    generate = getattr(request.app.state, "generate", None) or make_generate(
        ability_client(), prepared=prepared, pages=page_reader().read, clock=clock
    )
    # The same list the model tools append to during `generate` (inside
    # `run`). A tuple taken here would miss a search-products 500 the model
    # hit, and the later handoff would ship (#410).
    recorded = _recorded_call_failures(prepared)
    try:
        result = run(
            body,
            generate,
            prepared.route,
            prepared.facts,
            commerce,
            clock,
            call_failures=recorded,
        )
    finally:
        # A turn with no tool failure does not grow an empty key, including
        # when `run` raises before it returns.
        if not recorded:
            prepared.log.pop("call_failures", None)
    return result, None


def _recorded_call_failures(prepared: Prepared) -> list[object]:
    """The live `call_failures` list, created when the route recorded none.

    A note is `{text, kind?}` (`failure.note`). An older row is a string.
    Model tools append to this same list during `generate` (#410).
    """
    logged = prepared.log.get("call_failures")
    recorded: list[object] = []
    if isinstance(logged, list):
        for item in logged:
            if isinstance(item, str) or (
                isinstance(item, dict) and isinstance(item.get("text"), str)
            ):
                recorded.append(item)
    prepared.log["call_failures"] = recorded
    return recorded


def _sse(
    result: TurnResult,
    shipped: dict[str, object],
    turn_id: int,
    prepared: Prepared,
    clock: timing.Timing,
) -> Iterator[str]:
    # The generator's first step is the earliest the response path can mark the
    # first SSE event (#336); the meta event is built here, so it can carry it.
    clock.mark_first_event()
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
        # The turn's passive phase timings (#336, timing.py): a deliberate
        # additive surface — the #336B baseline harness reads each question's
        # per-turn timing from here (no VPS log access needed), and the shell
        # ignores fields it does not know. `total` here is the wall clock to
        # this first event; the log's row gets its complete record at stream end.
        "timing": clock.as_log(),
    }
    try:
        yield _event("meta", meta)
        # This turn's files (#236): what the shell shows for each, and the reading
        # the proxy keeps with the conversation (and takes out of the stream it
        # stores).
        for card in prepared.cards:
            yield _event("attachment", card)
        for reading in prepared.readings:
            yield _event("reading", reading.model_dump())
        blocks = shipped.get("blocks")
        for block in blocks if isinstance(blocks, list) else []:
            yield _event("block", block)
        yield _event("done", {"ok": True})
    finally:
        # The stream ended — `done`, or the customer went away and the generator
        # is closed early: the row's timing is completed with the turn's true
        # wall clock, the wait the customer experienced (a passive second write,
        # one UPDATE of the same row; #336). Measurement never breaks the
        # stream, so a failed write is logged and let go.
        try:
            turn_log().set_timing(turn_id, clock.as_log())
        except Exception:  # noqa: BLE001 - passive by contract (timing.py)
            logger.warning("genie timing record could not be completed", exc_info=True)


def _event(name: str, payload: object) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
